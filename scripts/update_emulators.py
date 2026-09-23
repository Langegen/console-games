#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
update_emulators.py
-------------------
Автоматизированный скрипт для формирования и обновления манифеста эмуляторов
`data/emulators.json` для TorrentShopNX (Nintendo Switch).

Функционал:
1. Запрашивает GitHub Releases API для получения актуальных версий, тегов, ссылок и размеров файлов.
2. Подтягивает актуальные размеры и даты ночных сборок ядер RetroArch с Libretro Buildbot.
3. Валидирует схему согласно строгим требованиям TorrentShopNX (20 консолей, 14 полей C++ структуры).
4. Атомарно форматирует и сохраняет `data/emulators.json`.
"""

from __future__ import annotations

import argparse
import email.utils
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DEFAULT_OUTPUT = os.path.join(DATA_DIR, "emulators.json")

# Ровно 20 разрешенных консолей (без arcade, pico8, scummvm)
ALLOWED_CONSOLES = {
    "3ds", "ps2", "gamecube", "wii", "psvita", "wiiu", "nds", "ps1", "psp",
    "dreamcast", "snes", "nes", "sega_md", "sega_ms", "sega_gg", "sega_cd",
    "gba", "gbc", "n64", "sega_32x"
}

ALLOWED_CATEGORIES = {"nintendo", "sony", "sega", "retroarch"}

# Конфигурация 17 пакетов эмуляторов
EMULATOR_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "id": "dekopon",
        "name": "Dekopon (Citra)",
        "author": "PalindromicBreadLoaf",
        "category": "nintendo",
        "description": "Порт эмулятора Nintendo 3DS (Citra) для Switch от PalindromicBreadLoaf. Поддержка Horizon OS, аппаратного ускорения и стабильной кадровой частоты.",
        "repo": "PalindromicBreadLoaf/dekopon",
        "asset_pattern": r"^dekopon\.nro$",
        "target_filename": "dekopon.nro",
        "install_path": "sdmc:/switch/dekopon/dekopon.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["3ds"],
        "color": [230, 0, 18, 255],
    },
    {
        "id": "nethersx2",
        "name": "NetherSX2-nx",
        "author": "NaGaa95",
        "category": "sony",
        "description": "Порт эмулятора Sony PlayStation 2 для Switch от NaGaa95. Высокая производительность при разгоне, поддержка widescreen-патчей и кастомных текстур.",
        "repo": "NaGaa95/NetherSX2_nx",
        "asset_pattern": r"^NetherSX2\.nro$",
        "target_filename": "NetherSX2.nro",
        "install_path": "sdmc:/switch/NetherSX2/NetherSX2.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["ps2"],
        "color": [0, 67, 156, 255],
    },
    {
        "id": "dolphin",
        "name": "Dolphin-nx",
        "author": "NaGaa95",
        "category": "nintendo",
        "description": "Порт эмулятора Nintendo GameCube и Wii для Switch от NaGaa95. Поддержка графики Vulkan, эмуляции контроллеров и высокого разрешения.",
        "repo": "NaGaa95/dolphin-nx",
        "asset_pattern": r"^dolphin\.nro$",
        "target_filename": "dolphin.nro",
        "install_path": "sdmc:/switch/dolphin/dolphin.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["gamecube", "wii"],
        "color": [85, 71, 163, 255],
    },
    {
        "id": "vita3k",
        "name": "Vita3K-nx",
        "author": "NaGaa95",
        "category": "sony",
        "description": "Экспериментальный порт эмулятора PlayStation Vita для Switch от NaGaa95. Запуск коммерческих игр формата VPK и NoNpDrm с рендерингом Vulkan.",
        "repo": "NaGaa95/Vita3K-nx",
        "asset_pattern": r"^Vita3K\.nro$",
        "target_filename": "Vita3K.nro",
        "install_path": "sdmc:/switch/Vita3K/Vita3K.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["psvita"],
        "color": [0, 150, 214, 255],
    },
    {
        "id": "cemu",
        "name": "Cemu-nx",
        "author": "NaGaa95",
        "category": "nintendo",
        "description": "Порт эмулятора Nintendo Wii U для Switch от NaGaa95. Требует максимального разгона (OC) CPU/GPU, воспроизводит нетребовательные игры и 2D-хиты.",
        "repo": "NaGaa95/Cemu-nx",
        "asset_pattern": r"^cemu\.nro$",
        "target_filename": "cemu.nro",
        "install_path": "sdmc:/switch/cemu/cemu.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["wiiu"],
        "color": [0, 158, 219, 255],
    },
    {
        "id": "drasticds",
        "name": "DraSticDS-nx",
        "author": "NaGaa95",
        "category": "nintendo",
        "description": "Нативный порт легендарного эмулятора DraStic Nintendo DS от NaGaa95. Стабильные 60 FPS на базовых частотах, поддержка сенсорного экрана.",
        "repo": "NaGaa95/DrasticDS_nx",
        "asset_pattern": r"^DrasticDS\.nro$",
        "target_filename": "DrasticDS.nro",
        "install_path": "sdmc:/switch/DrasticDS/DrasticDS.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["nds"],
        "color": [231, 76, 60, 255],
    },
    {
        "id": "melonds",
        "name": "melonDS",
        "author": "ArcDelta",
        "category": "nintendo",
        "description": "Точный опенсорсный эмулятор Nintendo DS и DSi. Сенсорное управление, качественный звук, эмуляция микрофона и поддержка разгона.",
        "repo": "ArcDelta/melonDS",
        "asset_pattern": r"^melonDS\.nro$",
        "target_filename": "melonDS.nro",
        "install_path": "sdmc:/switch/melonds/melonDS.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["nds"],
        "color": [243, 156, 18, 255],
    },
    {
        "id": "duckstation",
        "name": "DuckStation",
        "author": "shooterspps",
        "category": "sony",
        "description": "Высокоточный эмулятор Sony PlayStation 1 для Switch. PGXP для устранения дрожания полигонов, масштабирование внутреннего разрешения и шейдеры.",
        "repo": "shooterspps/duckstation",
        "asset_pattern": r"duckstation_switch.*\.zip$",
        "target_filename": "duckstation_switch.zip",
        "install_path": "sdmc:/switch/duckstation/duckstation.nro",
        "extract_dir": "sdmc:/switch/duckstation",
        "is_archive": True,
        "supported_console_ids": ["ps1"],
        "color": [41, 128, 185, 255],
    },
    {
        "id": "ppsspp",
        "name": "PPSSPP-nx",
        "author": "NaGaa95",
        "category": "sony",
        "description": "Порт эмулятора Sony PlayStation Portable для Switch от NaGaa95. Высокая производительность, апскейлинг разрешения, поддержка шейдеров и читов.",
        "repo": "NaGaa95/ppsspp-nx",
        "asset_pattern": r"^PPSSPP\.nro$",
        "target_filename": "PPSSPP.nro",
        "install_path": "sdmc:/switch/ppsspp/PPSSPP.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["psp"],
        "color": [33, 74, 135, 255],
    },
    {
        "id": "flycast",
        "name": "Flycast",
        "author": "flyinghead",
        "category": "sega",
        "description": "Нативный мультисистемный эмулятор Sega Dreamcast, Naomi и Atomiswave. Высокая производительность, поддержка широкоформатных хаков и 60 FPS.",
        "repo": "flyinghead/flycast",
        "asset_pattern": r"flycast.*\.nro$",
        "target_filename": "flycast.nro",
        "install_path": "sdmc:/switch/flycast/flycast.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["dreamcast"],
        "color": [230, 100, 20, 255],
    },
    {
        "id": "psnes",
        "name": "pSNES",
        "author": "Cpasjuste",
        "category": "nintendo",
        "description": "Порт эмулятора Super Nintendo (Snes9x) на базе оболочки pemu. Удобный графический интерфейс, фильтры изображения, предпросмотр обложек и перемотка.",
        "repo": "Cpasjuste/pemu",
        "asset_pattern": r"^psnes\.nro$",
        "target_filename": "psnes.nro",
        "install_path": "sdmc:/switch/pSNES/psnes.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["snes"],
        "color": [142, 68, 173, 255],
    },
    {
        "id": "pnes",
        "name": "pNES",
        "author": "Cpasjuste",
        "category": "nintendo",
        "description": "Эмулятор NES и Dendy на базе pemu. Поддержка Famicom Disk System, быстрое сохранение, настраиваемые фильтры и идеальная скорость.",
        "repo": "Cpasjuste/pemu",
        "asset_pattern": r"^pnes\.nro$",
        "target_filename": "pnes.nro",
        "install_path": "sdmc:/switch/pNES/pnes.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["nes"],
        "color": [192, 57, 43, 255],
    },
    {
        "id": "pgen",
        "name": "pGEN",
        "author": "Cpasjuste",
        "category": "sega",
        "description": "Эмулятор Sega Mega Drive, Master System, Game Gear и Sega CD на базе Genesis Plus GX. Высокая точность звука и синхронизации.",
        "repo": "Cpasjuste/pemu",
        "asset_pattern": r"^pgen\.nro$",
        "target_filename": "pgen.nro",
        "install_path": "sdmc:/switch/pGEN/pgen.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["sega_md", "sega_ms", "sega_gg", "sega_cd"],
        "color": [0, 102, 204, 255],
    },
    {
        "id": "mgba",
        "name": "mGBA",
        "author": "mgba-emu",
        "category": "nintendo",
        "description": "Один из самых точных и быстрых эмуляторов Game Boy Advance, Game Boy и Game Boy Color. Богатый выбор цветовых палитр и оверкварца.",
        "repo": "mgba-emu/mgba",
        "asset_pattern": r"mGBA-.*-switch\.7z$",
        "target_filename": "mGBA-switch.7z",
        "install_path": "sdmc:/switch/mGBA/mGBA.nro",
        "extract_dir": "sdmc:/switch/mGBA",
        "is_archive": True,
        "supported_console_ids": ["gba", "gbc"],
        "color": [102, 51, 153, 255],
    },
    {
        "id": "pgba",
        "name": "pGBA",
        "author": "Cpasjuste",
        "category": "nintendo",
        "description": "Эмулятор Game Boy Advance на базе pemu. Интуитивный интерфейс с предпросмотром скриншотов, сохранение состояний и поддержка читов.",
        "repo": "Cpasjuste/pemu",
        "asset_pattern": r"^pgba\.nro$",
        "target_filename": "pgba.nro",
        "install_path": "sdmc:/switch/pGBA/pgba.nro",
        "extract_dir": "",
        "is_archive": False,
        "supported_console_ids": ["gba"],
        "color": [44, 62, 80, 255],
    },
    {
        "id": "mupen64plus_next",
        "name": "Mupen64Plus-Next (RetroArch Core)",
        "author": "Libretro",
        "category": "retroarch",
        "description": "Высокопроизводительное ядро эмулятора Nintendo 64 для RetroArch на Nintendo Switch. Отличная совместимость с популярными 3D-играми N64.",
        "direct_url": "https://buildbot.libretro.com/nightly/nintendo/switch/libnx/latest/mupen64plus_next_libretro_libnx.nro.zip",
        "target_filename": "mupen64plus_next_libretro_libnx.nro.zip",
        "install_path": "sdmc:/retroarch/cores/mupen64plus_next_libretro_libnx.nro",
        "extract_dir": "sdmc:/retroarch/cores",
        "is_archive": True,
        "supported_console_ids": ["n64"],
        "color": [46, 204, 113, 255],
    },
    {
        "id": "picodrive",
        "name": "PicoDrive (RetroArch Core)",
        "author": "Libretro",
        "category": "retroarch",
        "description": "Быстрое ядро эмулятора Sega 32X и Mega Drive для RetroArch на Nintendo Switch с поддержкой специфического чипсета 32X.",
        "direct_url": "https://buildbot.libretro.com/nightly/nintendo/switch/libnx/latest/picodrive_libretro_libnx.nro.zip",
        "target_filename": "picodrive_libretro_libnx.nro.zip",
        "install_path": "sdmc:/retroarch/cores/picodrive_libretro_libnx.nro",
        "extract_dir": "sdmc:/retroarch/cores",
        "is_archive": True,
        "supported_console_ids": ["sega_32x"],
        "color": [52, 73, 94, 255],
    },
]


class ReleaseFetcher:
    """Загрузчик информации о релизах из GitHub API и Libretro Buildbot."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.headers = {
            "User-Agent": "TorrentShopNX-Manifest-Builder/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        self._repo_cache: Dict[str, Any] = {}

    def fetch_github_release(self, repo: str) -> Optional[Dict[str, Any]]:
        """Запрашивает последний релиз репозитория (с фоллбэком на /releases)."""
        if repo in self._repo_cache:
            return self._repo_cache[repo]

        # 1. Сначала пробуем /releases/latest
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._repo_cache[repo] = data
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Фоллбэк: если репозиторий использует только pre-releases (например DuckStation)
                url_all = f"https://api.github.com/repos/{repo}/releases"
                req_all = urllib.request.Request(url_all, headers=self.headers)
                try:
                    with urllib.request.urlopen(req_all, timeout=15) as resp_all:
                        releases = json.loads(resp_all.read().decode("utf-8"))
                        if releases:
                            self._repo_cache[repo] = releases[0]
                            return releases[0]
                except Exception as inner_err:
                    print(f"[-] Error fetching releases list for {repo}: {inner_err}", file=sys.stderr)
            elif e.code == 403 and "rate limit" in str(e).lower():
                print(f"[!] GitHub API rate limit exceeded while querying {repo}", file=sys.stderr)
            else:
                print(f"[-] HTTP {e.code} for {repo}: {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f"[-] Network error querying {repo}: {e}", file=sys.stderr)

        return None

    def fetch_buildbot_info(self, url: str) -> Tuple[int, str]:
        """Запрашивает заголовки файла ядра Libretro Buildbot (размер и дата сборки)."""
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "curl/7.88.1"})
        file_size = 0
        version = "nightly"
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    file_size = int(cl)
                lm = resp.headers.get("Last-Modified")
                if lm:
                    parsed_date = email.utils.parsedate_to_datetime(lm)
                    version = f"nightly-{parsed_date.strftime('%Y.%m.%d')}"
        except Exception as e:
            print(f"[!] Warning: Failed HEAD request for buildbot {url}: {e}", file=sys.stderr)
        return file_size, version


def clean_version_tag(tag: str) -> str:
    """Удаляет ведущие 'v'/'V' или нормализует тег."""
    if tag.startswith(("v", "V")) and len(tag) > 1 and tag[1].isdigit():
        return tag[1:]
    return tag


def find_best_asset(assets: List[Dict[str, Any]], pattern: str) -> Optional[Dict[str, Any]]:
    """Находит наиболее подходящий ассет по регулярному выражению."""
    regex = re.compile(pattern, re.IGNORECASE)
    matched = [a for a in assets if regex.search(a.get("name", ""))]
    if not matched:
        return None
    matched.sort(key=lambda a: a.get("name", ""))
    return matched[-1]


def build_emulator_entry(
    definition: Dict[str, Any],
    fetcher: ReleaseFetcher,
    existing_entry: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Формирует готовый объект эмулятора согласно C++ спецификации TorrentShopNX."""
    entry = {
        "id": definition["id"],
        "name": definition["name"],
        "author": definition["author"],
        "version": existing_entry.get("version", "1.0.0") if existing_entry else "1.0.0",
        "description": definition["description"],
        "category": definition["category"],
        "download_url": existing_entry.get("download_url", "") if existing_entry else "",
        "filename": definition.get("target_filename", ""),
        "install_path": definition["install_path"],
        "extract_dir": definition["extract_dir"],
        "is_archive": definition["is_archive"],
        "file_size": existing_entry.get("file_size", 0) if existing_entry else 0,
        "supported_console_ids": definition["supported_console_ids"],
        "color": definition["color"],
    }

    # Для ядер Libretro Buildbot
    if "direct_url" in definition:
        direct_url = definition["direct_url"]
        entry["download_url"] = direct_url
        size, version = fetcher.fetch_buildbot_info(direct_url)
        if size > 0:
            entry["file_size"] = size
        if version:
            entry["version"] = version
        return entry

    # Для GitHub Releases
    repo = definition.get("repo")
    if not repo:
        return entry

    release_data = fetcher.fetch_github_release(repo)
    if not release_data:
        if existing_entry:
            print(f"[*] Preserving existing cached release data for {definition['id']}")
            return existing_entry
        return entry

    raw_tag = release_data.get("tag_name", "")
    entry["version"] = clean_version_tag(raw_tag)

    assets = release_data.get("assets", [])
    pattern = definition.get("asset_pattern", r"\.nro$")
    asset = find_best_asset(assets, pattern)

    if asset:
        entry["download_url"] = asset.get("browser_download_url", "")
        entry["file_size"] = asset.get("size", 0)
        if not entry["filename"]:
            entry["filename"] = asset.get("name", "")
    else:
        print(f"[!] Warning: No matching asset found for {definition['id']} in repo {repo} (pattern: {pattern})", file=sys.stderr)

    return entry


def validate_manifest(manifest: List[Dict[str, Any]]) -> List[str]:
    """Проверяет соответствие манифеста строгой C++ JSON-схеме и ограничениям задачи."""
    errors = []

    if not isinstance(manifest, list):
        return ["Manifest root must be a JSON array [ ... ]"]

    if len(manifest) != len(EMULATOR_DEFINITIONS):
        errors.append(f"Manifest must contain exactly {len(EMULATOR_DEFINITIONS)} emulators, got {len(manifest)}")

    seen_ids = set()
    covered_consoles = set()

    for idx, emu in enumerate(manifest):
        prefix = f"Emulator [{idx}]:"

        if not isinstance(emu, dict):
            errors.append(f"{prefix} must be a JSON object")
            continue

        emu_id = emu.get("id")
        if not emu_id or not isinstance(emu_id, str):
            errors.append(f"{prefix} invalid or missing 'id'")
        elif emu_id in seen_ids:
            errors.append(f"{prefix} duplicate id '{emu_id}'")
        else:
            seen_ids.add(emu_id)
            prefix = f"Emulator '{emu_id}':"

        # Проверка обязательных строковых полей
        for str_field in ["name", "author", "version", "description", "category", "download_url", "filename", "install_path"]:
            val = emu.get(str_field)
            if not isinstance(val, str) or not val.strip():
                errors.append(f"{prefix} field '{str_field}' must be a non-empty string")

        # Категория
        category = emu.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{prefix} category '{category}' not in {sorted(ALLOWED_CATEGORIES)}")

        # URL скачивания
        dl_url = emu.get("download_url", "")
        if not dl_url.startswith("https://"):
            errors.append(f"{prefix} download_url must start with 'https://', got '{dl_url}'")

        # Пути на SD-карте
        inst_path = emu.get("install_path", "")
        if not inst_path.startswith("sdmc:/"):
            errors.append(f"{prefix} install_path must start with 'sdmc:/', got '{inst_path}'")

        is_archive = emu.get("is_archive")
        if not isinstance(is_archive, bool):
            errors.append(f"{prefix} is_archive must be a boolean")

        extract_dir = emu.get("extract_dir")
        if not isinstance(extract_dir, str):
            errors.append(f"{prefix} extract_dir must be a string")
        elif is_archive and not extract_dir.startswith("sdmc:/"):
            errors.append(f"{prefix} extract_dir must start with 'sdmc:/' when is_archive=true, got '{extract_dir}'")
        elif not is_archive and extract_dir != "":
            errors.append(f"{prefix} extract_dir must be empty string '' when is_archive=false, got '{extract_dir}'")

        # Размер файла
        file_size = emu.get("file_size")
        if not isinstance(file_size, int) or file_size <= 0:
            errors.append(f"{prefix} file_size must be a positive integer, got {file_size}")

        # Поддерживаемые консоли
        supported = emu.get("supported_console_ids")
        if not isinstance(supported, list) or not supported:
            errors.append(f"{prefix} supported_console_ids must be a non-empty list of strings")
        else:
            for cid in supported:
                if not isinstance(cid, str):
                    errors.append(f"{prefix} console id '{cid}' must be a string")
                elif cid not in ALLOWED_CONSOLES:
                    errors.append(f"{prefix} unsupported console id '{cid}'! Must be in {sorted(ALLOWED_CONSOLES)}")
                else:
                    covered_consoles.add(cid)

        # Цвет плашки UI
        color = emu.get("color")
        if not isinstance(color, list) or len(color) != 4:
            errors.append(f"{prefix} color must be an array of 4 integers [R, G, B, A]")
        else:
            for c in color:
                if not isinstance(c, int) or not (0 <= c <= 255):
                    errors.append(f"{prefix} color components must be integers in [0, 255], got {color}")
                    break

        # Проверка ключевых требований из ТЗ
        if emu_id == "dekopon":
            if emu.get("author") != "PalindromicBreadLoaf":
                errors.append(f"{prefix} author must be 'PalindromicBreadLoaf'")
            if "3ds" not in (supported or []):
                errors.append(f"{prefix} must support '3ds'")

    # Проверка покрытия всех 20 консолей
    missing_consoles = ALLOWED_CONSOLES - covered_consoles
    if missing_consoles:
        errors.append(f"Manifest does not cover all 20 consoles! Missing: {sorted(missing_consoles)}")

    # Проверка отсутствия запрещенных платформ
    forbidden = {"arcade", "pico8", "scummvm"}
    overlap = covered_consoles.intersection(forbidden)
    if overlap:
        errors.append(f"Forbidden console IDs found in manifest: {sorted(overlap)}")

    return errors


def update_manifest(output_path: str = DEFAULT_OUTPUT, check_only: bool = False, token: Optional[str] = None) -> bool:
    """Генерирует и сохраняет манифест эмуляторов."""
    print(f"[*] Starting emulator manifest update -> target: {output_path}")

    existing_manifest: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "id" in item:
                            existing_manifest[item["id"]] = item
            print(f"[*] Loaded {len(existing_manifest)} existing entries from {output_path}")
        except Exception as e:
            print(f"[!] Could not read existing manifest: {e}", file=sys.stderr)

    fetcher = ReleaseFetcher(token=token)
    new_manifest: List[Dict[str, Any]] = []

    for defn in EMULATOR_DEFINITIONS:
        eid = defn["id"]
        print(f"[*] Processing {eid} ({defn['name']})...")
        existing_item = existing_manifest.get(eid)
        entry = build_emulator_entry(defn, fetcher, existing_item)
        new_manifest.append(entry)

    # Валидация схемы
    print("[*] Validating manifest schema and constraints...")
    errors = validate_manifest(new_manifest)
    if errors:
        print("[!] Validation failed with errors:", file=sys.stderr)
        for err in errors:
            print(f"    - {err}", file=sys.stderr)
        return False

    print(f"[+] Validation successful! Total {len(new_manifest)} emulators, 20 platforms covered.")

    if check_only:
        print("[*] Check-only flag passed, skipping writing to disk.")
        return True

    # Сохраняем в файл
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_path = f"{output_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(new_manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Атомарная замена
    if os.path.exists(output_path):
        os.replace(temp_path, output_path)
    else:
        os.rename(temp_path, output_path)

    print(f"[+] Manifest successfully updated and saved to {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Update TorrentShopNX emulator manifest (data/emulators.json)")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help=f"Path to output JSON (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--check-only", action="store_true", help="Validate without writing to file")
    parser.add_argument("--token", "-t", default=None, help="GitHub Personal Access Token for higher API rate limits")
    args = parser.parse_args()

    success = update_manifest(output_path=args.output, check_only=args.check_only, token=args.token)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
