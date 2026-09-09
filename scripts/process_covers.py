#!/usr/bin/env python3
"""
Game Cover Pipeline & Normalizer for console-games
Scans all platform JSONs in data/, verifies cover links, fetches missing/broken
covers from Libretro Thumbnails / GameTDB, standardizes dimensions, converts
to JPEG/WebP, and saves uniform boxarts for Nintendo Switch and frontend display.
"""

import os
import sys
import re
import io
import json
import time
import argparse
import logging
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / ".cache"
COVERS_DIR = ROOT_DIR / "covers"

# Dead or defunct image hosting domains that are guaranteed to fail
DEAD_DOMAINS = {
    "radikal.ru",
    "radikal.ua",
    "lostpic.net",
    "savepic.ru",
    "savepic.net",
    "savepic.org",
    "picshare.ru",
    "hostingkartinok.com",
    "imgload.ru",
    "screenshoter.net",
    "keep4u.ru",
    "firepic.org",
    "uploads.ru",
}

# Mapping of platform key to Libretro Thumbnails repository name
LIBRETRO_REPOS: Dict[str, str] = {
    "3ds": "Nintendo_-_Nintendo_3DS",
    "dreamcast": "Sega_-_Dreamcast",
    "gamecube": "Nintendo_-_GameCube",
    "gba": "Nintendo_-_Game_Boy_Advance",
    "gbc": "Nintendo_-_Game_Boy_Color",
    "n64": "Nintendo_-_Nintendo_64",
    "nds": "Nintendo_-_Nintendo_DS",
    "nes": "Nintendo_-_Nintendo_Entertainment_System",
    "ps1": "Sony_-_PlayStation",
    "ps2": "Sony_-_PlayStation_2",
    "psp": "Sony_-_PlayStation_Portable",
    "psvita": "Sony_-_PlayStation_Vita",
    "sega_32x": "Sega_-_32X",
    "sega_cd": "Sega_-_Mega-CD_-_Sega_CD",
    "sega_gg": "Sega_-_Game_Gear",
    "sega_md": "Sega_-_Mega_Drive_-_Genesis",
    "sega_ms": "Sega_-_Master_System_-_Mark_III",
    "snes": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "wii": "Nintendo_-_Wii",
    "wiiu": "Nintendo_-_Wii_U",
}

# Mapping of platform key to GameTDB system name
GAMETDB_SYSTEMS: Dict[str, str] = {
    "wii": "wii",
    "gamecube": "wii",
    "nds": "ds",
    "3ds": "3ds",
    "ps3": "ps3",
}

# Console accent colors for placeholders
PLATFORM_COLORS: Dict[str, Tuple[int, int, int]] = {
    "ps1": (0, 67, 156),
    "ps2": (0, 48, 135),
    "psp": (20, 20, 20),
    "psvita": (0, 55, 145),
    "nes": (180, 20, 20),
    "snes": (117, 76, 172),
    "n64": (16, 124, 65),
    "gamecube": (88, 37, 130),
    "wii": (0, 158, 219),
    "wiiu": (0, 158, 227),
    "gba": (70, 30, 120),
    "gbc": (160, 40, 90),
    "nds": (100, 100, 100),
    "3ds": (210, 0, 0),
    "sega_md": (0, 0, 0),
    "sega_ms": (180, 0, 0),
    "sega_gg": (30, 30, 30),
    "sega_cd": (0, 80, 160),
    "sega_32x": (190, 140, 20),
    "dreamcast": (235, 106, 0),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cover_pipeline")


def is_dead_domain(url: Optional[str]) -> bool:
    """Check if URL belongs to known dead/closed image hosts."""
    if not url or not isinstance(url, str):
        return True
    url_lower = url.lower()
    return any(d in url_lower for d in DEAD_DOMAINS)


def clean_title_for_matching(title: str) -> str:
    """Normalize a RuTracker torrent title to clean Romanized game title."""
    if not title:
        return ""
    t = str(title)
    # Remove leading dump numbers e.g. '2541 - ', '0041 - '
    t = re.sub(r"^\s*\d{3,5}\s*[-–—]\s*", "", t)
    # Remove content in brackets and parentheses [RUS/ENG], (v1.1), [NTSC]
    t = re.sub(r"\[.*?\]", " ", t)
    t = re.sub(r"\(.*?\)", " ", t)
    # Replace punctuation with space
    t = re.sub(r"[:|/\\_–—\-+*#]", " ", t)
    # Normalize common grammatical articles
    words = t.lower().split()
    if words and words[-1] == "the":
        words = ["the"] + words[:-1]
    return " ".join(words)


class LibretroIndex:
    """Fetches, caches and searches Libretro Thumbnails index for a platform."""

    def __init__(self, platform: str, github_token: Optional[str] = None):
        self.platform = platform
        self.repo = LIBRETRO_REPOS.get(platform)
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.entries: List[Tuple[str, str]] = []  # [(clean_title, raw_path)]
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.cache_file = CACHE_DIR / f"libretro_{platform}.json"
        if self.repo:
            self._load_or_fetch()

    def _load_or_fetch(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entries = [(item["clean"], item["path"]) for item in data]
                return
            except Exception as e:
                logger.warning(f"Failed to read cache {self.cache_file}: {e}")

        logger.info(f"Fetching Libretro index for {self.platform} ({self.repo})...")
        url = f"https://api.github.com/repos/libretro-thumbnails/{self.repo}/git/trees/master?recursive=1"
        headers = dict(HEADERS)
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                tree = resp.json().get("tree", [])
                items = []
                for node in tree:
                    path = node.get("path", "")
                    if path.startswith("Named_Boxarts/") and path.lower().endswith(".png"):
                        filename = path[len("Named_Boxarts/") : -4]
                        clean_name = clean_title_for_matching(filename)
                        items.append({"clean": clean_name, "path": path})
                        self.entries.append((clean_name, path))

                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False)
                logger.info(f"Cached {len(self.entries)} boxart entries for {self.platform}")
            else:
                logger.warning(f"GitHub API returned {resp.status_code} for {self.repo}")
        except Exception as e:
            logger.warning(f"Error fetching Libretro tree for {self.platform}: {e}")

    def find_cover_url(self, title: str) -> Optional[str]:
        if not self.entries or not self.repo:
            return None

        clean_search = clean_title_for_matching(title)
        if not clean_search:
            return None

        candidates = []
        for clean_name, raw_path in self.entries:
            if clean_name == clean_search:
                candidates.append((0, raw_path))
            elif clean_name.startswith(clean_search) or clean_search.startswith(clean_name):
                candidates.append((1, raw_path))

        if not candidates:
            return None

        # Regional preference weighting
        def score(item):
            match_type, path = item
            pref = 5
            p_lower = path.lower()
            if "(europe)" in p_lower or "(russia)" in p_lower or "(en,ru)" in p_lower:
                pref = 1
            elif "(usa, europe)" in p_lower:
                pref = 2
            elif "(usa)" in p_lower:
                pref = 3
            elif "(world)" in p_lower:
                pref = 4
            return (match_type, pref, len(path))

        candidates.sort(key=score)
        best_path = candidates[0][1]
        quoted_path = urllib.parse.quote(best_path)
        return f"https://raw.githubusercontent.com/libretro-thumbnails/{self.repo}/master/{quoted_path}"


def fetch_gametdb_cover(platform: str, title_id: Optional[str], session: requests.Session) -> Optional[bytes]:
    """Attempts to fetch boxart from GameTDB using game serial / title_id."""
    if not title_id or platform not in GAMETDB_SYSTEMS:
        return None

    # Clean title_id e.g. SLUS-20062 -> SLUS20062 or RMCE01
    clean_id = re.sub(r"[^A-Za-z0-9]", "", str(title_id)).upper()
    if len(clean_id) < 4:
        return None

    sys_name = GAMETDB_SYSTEMS[platform]
    regions = ["US", "EN", "RU", "JA", "FR", "DE", "ES", "IT"]

    for reg in regions:
        url = f"https://art.gametdb.com/{sys_name}/cover/{reg}/{clean_id}.png"
        try:
            resp = session.get(url, headers=HEADERS, timeout=5)
            if resp.status_code == 200 and len(resp.content) > 1000 and "image" in resp.headers.get("Content-Type", ""):
                return resp.content
        except Exception:
            continue
    return None


def fetch_url_image(url: str, session: requests.Session, timeout: int = 7) -> Optional[bytes]:
    """Downloads an image from a URL, validating content type."""
    if not url or is_dead_domain(url):
        return None
    try:
        resp = session.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200 and len(resp.content) > 1000:
            ctype = resp.headers.get("Content-Type", "").lower()
            if "image" in ctype or resp.content[:4] in (b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"\x89PNG", b"RIFF"):
                return resp.content
    except Exception:
        pass
    return None


def generate_placeholder(
    title: str, platform: str, target_width: int = 300, target_height: int = 400
) -> bytes:
    """Generates a stylish, clean dark-themed placeholder boxart with platform pill and title."""
    accent_color = PLATFORM_COLORS.get(platform, (40, 40, 45))
    canvas = Image.new("RGB", (target_width, target_height), (18, 18, 22))
    draw = ImageDraw.Draw(canvas)

    # Subtle inner border
    draw.rectangle(
        [(8, 8), (target_width - 9, target_height - 9)],
        outline=(38, 38, 44),
        width=1,
    )

    # Top platform pill
    pill_height = 36
    draw.rectangle([(16, 16), (target_width - 17, 16 + pill_height)], fill=accent_color)

    font = ImageFont.load_default()

    plat_label = platform.upper().replace("_", " ")
    draw.text((26, 28), plat_label, fill=(255, 255, 255), font=font)

    # Clean title text wrapping
    clean_text = clean_title_for_matching(title)
    if not clean_text:
        clean_text = title[:30]

    words = clean_text.title().split()
    lines = []
    curr = []
    for w in words:
        if len(" ".join(curr + [w])) <= 22:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    # Center title vertically
    y_start = 140
    for line in lines[:5]:
        draw.text((24, y_start), line, fill=(220, 220, 225), font=font)
        y_start += 24

    # Bottom badge
    draw.text((24, target_height - 35), "NO COVER ART", fill=(120, 120, 130), font=font)

    out_io = io.BytesIO()
    canvas.save(out_io, format="JPEG", quality=85, optimize=True)
    return out_io.getvalue()


def process_image(
    image_bytes: bytes,
    target_width: int = 300,
    target_height: int = 400,
    img_format: str = "JPEG",
    quality: int = 85,
    style: str = "blur",
) -> bytes:
    """Resizes and centers the image on a standardized canvas preserving aspect ratio with optional ambient blur."""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert transparency or palletized modes to RGB on dark background
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg = Image.new("RGBA", img.size, (20, 20, 24, 255))
        bg.paste(img, (0, 0), img.convert("RGBA"))
        img = bg.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if style == "blur":
        # 1. Background: full-bleed crop + gaussian blur + dark tint
        bg = ImageOps.fit(img, (target_width, target_height), method=Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=18))
        dark_overlay = Image.new("RGB", (target_width, target_height), (16, 16, 22))
        canvas = Image.blend(bg, dark_overlay, alpha=0.45)

        # 2. Foreground: fit maintaining aspect ratio with neat margin
        max_w, max_h = target_width - 16, target_height - 16
        ratio = min(max_w / img.size[0], max_h / img.size[1])
        fg_w, fg_h = max(1, int(img.size[0] * ratio)), max(1, int(img.size[1] * ratio))
        fg = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

        ox = (target_width - fg_w) // 2
        oy = (target_height - fg_h) // 2

        # Draw subtle border / shadow around foreground
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(ox - 2, oy - 2), (ox + fg_w + 1, oy + fg_h + 1)], outline=(10, 10, 15), width=2)
        canvas.paste(fg, (ox, oy))
    else:
        # Standard dark canvas #141418
        orig_w, orig_h = img.size
        ratio = min(target_width / orig_w, target_height / orig_h)
        new_w = max(1, int(orig_w * ratio))
        new_h = max(1, int(orig_h * ratio))

        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_width, target_height), (20, 20, 24))
        offset_x = (target_width - new_w) // 2
        offset_y = (target_height - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))

    out_io = io.BytesIO()
    save_fmt = "JPEG" if img_format.upper() in ("JPG", "JPEG") else img_format.upper()
    canvas.save(out_io, format=save_fmt, quality=quality, optimize=True)
    return out_io.getvalue()


def process_single_game(
    game: dict,
    platform: str,
    libretro_index: LibretroIndex,
    session: requests.Session,
    output_dir: Path,
    target_width: int,
    target_height: int,
    img_format: str,
    quality: int,
    force: bool,
    source_priority: str,
    flat_naming: bool,
    style: str = "blur",
) -> Tuple[str, str, Optional[str]]:
    """
    Processes a single game:
    Returns (status: 'cached'|'tracker'|'gametdb'|'libretro'|'placeholder'|'error', details, relative_path)
    """
    topic_id = str(game.get("topic_id") or "")
    if not topic_id:
        url = game.get("url", "")
        m = re.search(r"[?&]t=(\d+)", url)
        topic_id = m.group(1) if m else str(abs(hash(game.get("title", ""))))

    ext = "jpg" if img_format.lower() in ("jpg", "jpeg") else img_format.lower()
    if flat_naming:
        out_file = output_dir / f"{platform}_{topic_id}.{ext}"
        rel_path = f"covers/{platform}_{topic_id}.{ext}"
    else:
        out_dir = output_dir / platform
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{topic_id}.{ext}"
        rel_path = f"covers/{platform}/{topic_id}.{ext}"

    if out_file.exists() and not force:
        return ("cached", "Already exists", rel_path)

    title = game.get("title", "Unknown")
    raw_cover_url = game.get("cover")
    title_id = game.get("title_id")

    raw_bytes = None
    source_used = None

    # Strategy 1: Prioritize tracker or clean
    if source_priority == "clean_first":
        # 1. GameTDB
        raw_bytes = fetch_gametdb_cover(platform, title_id, session)
        if raw_bytes:
            source_used = "gametdb"

        # 2. Libretro
        if not raw_bytes:
            libretro_url = libretro_index.find_cover_url(title)
            if libretro_url:
                raw_bytes = fetch_url_image(libretro_url, session, timeout=8)
                if raw_bytes:
                    source_used = "libretro"

        # 3. RuTracker live cover
        if not raw_bytes and raw_cover_url and not is_dead_domain(raw_cover_url):
            raw_bytes = fetch_url_image(raw_cover_url, session, timeout=6)
            if raw_bytes:
                source_used = "tracker"
    else:
        # Default: tracker_first (keep Russian/custom cover if live, fallback if dead)
        if raw_cover_url and not is_dead_domain(raw_cover_url):
            raw_bytes = fetch_url_image(raw_cover_url, session, timeout=6)
            if raw_bytes:
                source_used = "tracker"

        # Fallback to GameTDB
        if not raw_bytes:
            raw_bytes = fetch_gametdb_cover(platform, title_id, session)
            if raw_bytes:
                source_used = "gametdb"

        # Fallback to Libretro
        if not raw_bytes:
            libretro_url = libretro_index.find_cover_url(title)
            if libretro_url:
                raw_bytes = fetch_url_image(libretro_url, session, timeout=8)
                if raw_bytes:
                    source_used = "libretro"

    # Fallback to stylish placeholder
    if not raw_bytes:
        raw_bytes = generate_placeholder(title, platform, target_width, target_height)
        source_used = "placeholder"

    # Standardize image dimensions
    try:
        final_bytes = process_image(
            raw_bytes,
            target_width=target_width,
            target_height=target_height,
            img_format=img_format,
            quality=quality,
            style=style,
        )
        with open(out_file, "wb") as f:
            f.write(final_bytes)
        return (source_used, f"Saved from {source_used}", rel_path)
    except Exception as e:
        logger.error(f"Error processing {title}: {e}")
        # Save placeholder on processing error
        try:
            ph = generate_placeholder(title, platform, target_width, target_height)
            with open(out_file, "wb") as f:
                f.write(ph)
            return ("placeholder", f"Fallback placeholder ({e})", rel_path)
        except Exception:
            return ("error", str(e), None)


def process_platform(
    platform: str,
    args: argparse.Namespace,
    session: requests.Session,
) -> Dict[str, int]:
    """Processes all games for a single platform."""
    json_path = DATA_DIR / f"{platform}_games.json"
    if not json_path.exists():
        logger.warning(f"File not found: {json_path}")
        return {}

    with open(json_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    if not isinstance(games, list):
        logger.warning(f"Invalid format in {json_path}")
        return {}

    if args.limit:
        games = games[: args.limit]

    logger.info(f"[{platform.upper()}] Processing {len(games)} games...")
    libretro_index = LibretroIndex(platform)

    stats = {
        "total": len(games),
        "cached": 0,
        "tracker": 0,
        "gametdb": 0,
        "libretro": 0,
        "placeholder": 0,
        "error": 0,
    }

    updated_games = []
    output_dir = Path(args.output_dir)

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        future_to_game = {
            executor.submit(
                process_single_game,
                game,
                platform,
                libretro_index,
                session,
                output_dir,
                args.width,
                args.height,
                args.format,
                args.quality,
                args.force,
                args.source_priority,
                args.flat,
                args.style,
            ): game
            for game in games
        }

        for future in as_completed(future_to_game):
            game = future_to_game[future]
            try:
                status, msg, rel_path = future.result()
                stats[status] = stats.get(status, 0) + 1
                if args.update_json and rel_path:
                    if args.base_url:
                        base = args.base_url.rstrip("/")
                        game["cover"] = f"{base}/{rel_path}"
                    else:
                        game["cover"] = rel_path
                updated_games.append(game)
            except Exception as e:
                stats["error"] += 1
                updated_games.append(game)

    if args.update_json and updated_games:
        # Preserve original order by matching topic_id or title
        order_map = {g.get("topic_id"): idx for idx, g in enumerate(games)}
        updated_games.sort(key=lambda g: order_map.get(g.get("topic_id"), 999999))
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_games, f, ensure_ascii=False, indent=4)
        logger.info(f"[{platform.upper()}] Updated cover paths in {json_path.name}")

    logger.info(
        f"[{platform.upper()}] Done: {stats['total']} total | "
        f"{stats['tracker']} tracker | {stats['gametdb']} GameTDB | "
        f"{stats['libretro']} Libretro | {stats['placeholder']} placeholders | "
        f"{stats['cached']} cached | {stats['error']} errors"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Unified Cover Pipeline & Normalizer for console-games"
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="all",
        help="Platform key (e.g. ps2, wii, snes) or 'all' to process all 20 platforms",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="jpg",
        choices=["jpg", "jpeg", "webp", "png"],
        help="Output image format (default: jpg for maximum Nintendo Switch compatibility)",
    )
    parser.add_argument(
        "--style",
        type=str,
        default="blur",
        choices=["blur", "dark"],
        help="Visual style: 'blur' (modern ambient blur matching game colors) or 'dark' (minimalist dark background)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=300,
        help="Target canvas width in pixels (default: 300)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=400,
        help="Target canvas height in pixels (default: 400)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="JPEG / WebP quality (1-100, default: 85)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(COVERS_DIR),
        help="Output folder for standardized covers (default: covers/)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=8,
        help="Parallel download threads (default: 8)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of games to process per platform (useful for testing)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download and re-process even if file already exists",
    )
    parser.add_argument(
        "--source-priority",
        type=str,
        default="clean_first",
        choices=["clean_first", "tracker_first"],
        help="Source priority: 'clean_first' (default) prefers official Libretro/GameTDB boxarts; 'tracker_first' keeps original live RuTracker art",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Save all covers flat in covers/{platform}_{id}.jpg instead of covers/{platform}/{id}.jpg",
    )
    parser.add_argument(
        "--update-json",
        action="store_true",
        help="Update the 'cover' field in data/*_games.json with standardized cover paths",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Base URL prefix for JSON cover updates (e.g. 'https://raw.githubusercontent.com/user/repo/main')",
    )

    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    if args.platform == "all":
        platforms = sorted(LIBRETRO_REPOS.keys())
    else:
        if args.platform not in LIBRETRO_REPOS:
            logger.error(
                f"Unknown platform '{args.platform}'. Supported: {', '.join(sorted(LIBRETRO_REPOS.keys()))}"
            )
            sys.exit(1)
        platforms = [args.platform]

    logger.info(
        f"Starting cover pipeline for {len(platforms)} platform(s): "
        f"target={args.width}x{args.height} {args.format.upper()}, "
        f"priority={args.source_priority}, threads={args.threads}"
    )

    total_stats = {
        "total": 0,
        "cached": 0,
        "tracker": 0,
        "gametdb": 0,
        "libretro": 0,
        "placeholder": 0,
        "error": 0,
    }

    start_time = time.time()
    for plat in platforms:
        plat_stats = process_platform(plat, args, session)
        for k, v in plat_stats.items():
            total_stats[k] = total_stats.get(k, 0) + v

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Cover pipeline completed in {elapsed:.1f}s")
    logger.info(
        f"Total: {total_stats['total']} games | "
        f"Live Tracker: {total_stats['tracker']} | "
        f"GameTDB: {total_stats['gametdb']} | "
        f"Libretro: {total_stats['libretro']} | "
        f"Placeholders: {total_stats['placeholder']} | "
        f"Cached: {total_stats['cached']} | "
        f"Errors: {total_stats['error']}"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
