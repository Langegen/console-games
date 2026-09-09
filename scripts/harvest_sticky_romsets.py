"""Сбор закреплённых раздач ромсетов из всех целевых форумов RuTracker."""
import json
import re
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.network import fetch_url, BASE_URL, close_driver
from core.topic_parser import get_topic_data, clean_title
from core.romset_utils import is_romset_title, is_non_game_tool, tag_game_entry
from platforms.registry import FORUM_TO_PLATFORMS, get_platforms_for_forum
from platforms.classifiers import classify_topic

DATA_DIR = ROOT_DIR / "data"

# Поддерживаемые платформы
SUPPORTED_PLATFORMS = set(
    ['3ds', 'dreamcast', 'gamecube', 'gba', 'gbc', 'n64', 'nds', 'nes',
     'ps1', 'ps2', 'psp', 'psvita', 'sega_32x', 'sega_cd', 'sega_gg',
     'sega_md', 'sega_ms', 'snes', 'wii', 'wiiu']
)

# Специальные мультиплатформенные маршруты
MULTI_PLATFORM_MAP = {
    "4219186": ["nes", "gbc", "snes", "gba", "gamecube", "nds", "wii"],  # Metroid Anthology
    "582544": ["nes", "snes", "gbc", "gba", "n64", "gamecube"],          # Zelda Anthology
    "4252995": ["sega_md", "sega_32x"],                                  # GoodGen Genesis/32X
    "5129888": ["wii", "gamecube"],                                      # Сборник русскоязычных Wii + GC
    "6707891": ["nes", "snes", "gbc", "gba", "nds", "ps1", "ps2"],       # Dragon Quest Anthology
    "1468341": ["nes", "snes", "gba", "ps1", "ps2"],                     # Final Fantasy Ultimate
    "4628170": ["sega_md", "snes", "ps1", "saturn"],                     # Langrisser Collection
}


def load_existing_topic_ids():
    """Загружает существующие topic_id по всем платформам."""
    platform_ids = {}
    for p in SUPPORTED_PLATFORMS:
        fpath = DATA_DIR / f"{p}_games.json"
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                games = json.load(f)
                platform_ids[p] = {str(g.get("topic_id")): g for g in games}
        else:
            platform_ids[p] = {}
    return platform_ids


def get_sticky_torrents_from_forum(forum_id):
    """Находит все реальные закреплённые торренты на странице форума."""
    url = f"{BASE_URL}viewforum.php?f={forum_id}"
    print(f"\n[*] Сканирование закреплённой секции f={forum_id}...")
    html = fetch_url(url, forum_url=True)
    if not html:
        print(f"[!] Не удалось загрузить f={forum_id}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.vf-table, table.forumline") or soup
    rows = table.find_all("tr", recursive=False) or table.select("tr")

    sticky_torrents = []
    for r in rows:
        tds = r.find_all("td", recursive=False)
        if len(tds) == 1 and "Темы" in tds[0].text:
            break

        link = r.select_one("a.tt-text")
        dl_link = r.select_one("a.f-dl, a[href^=\"dl.php?t=\"]")
        if link and dl_link:
            href = link.get("href", "")
            t_id = href.split("t=")[-1].split("&")[0] if "t=" in href else ""
            raw_title = link.get_text().strip()
            sz = dl_link.get_text().strip()

            # Исключаем неигровые утилиты и инструкции
            if is_non_game_tool(raw_title):
                print(f"  [-] Пропуск утилиты/FAQ: t={t_id} | {raw_title[:60]}")
                continue

            sticky_torrents.append({
                "topic_id": t_id,
                "raw_title": raw_title,
                "size": sz,
                "forum_id": forum_id
            })

    print(f"[+] Найдено {len(sticky_torrents)} закреплённых раздач в f={forum_id}")
    return sticky_torrents


def route_sticky_topic(topic_id, raw_title, forum_id):
    """Определяет целевые платформы для закреплённой темы."""
    # 1. Проверяем мультиплатформенный маппинг
    if topic_id in MULTI_PLATFORM_MAP:
        return [p for p in MULTI_PLATFORM_MAP[topic_id] if p in SUPPORTED_PLATFORMS]

    # 2. Форумы с одной платформой
    forum_str = str(forum_id)
    if forum_str == "1352":
        return ["psp"]
    elif forum_str == "908":
        return ["ps1"]
    elif forum_str == "357":
        return ["ps2"]
    elif forum_str == "595":
        return ["psvita"]
    elif forum_str == "968":
        return ["dreamcast"]

    # 3. Форумы со смешанными платформами: f=773, f=774, f=129
    matched = classify_topic(raw_title, forum_id)
    valid = [p for p in matched if p in SUPPORTED_PLATFORMS]
    if valid:
        return valid

    # 4. Фолбэк по ключевым словам в заголовке
    t_lower = raw_title.lower()
    fallback_plats = []
    if any(k in t_lower for k in ["nes", "dendy", "famicom", "goodnes"]):
        fallback_plats.append("nes")
    if any(k in t_lower for k in ["snes", "super nintendo", "goodsnes"]):
        fallback_plats.append("snes")
    if any(k in t_lower for k in ["n64", "nintendo 64", "goodn64"]):
        fallback_plats.append("n64")
    if any(k in t_lower for k in ["gba", "game boy advance"]):
        fallback_plats.append("gba")
    if any(k in t_lower for k in ["game boy", "gbc", "goodgbx"]):
        fallback_plats.append("gbc")
    if any(k in t_lower for k in ["sega genesis", "mega drive", "goodgen", "sega md"]):
        fallback_plats.append("sega_md")
    if any(k in t_lower for k in ["32x", "sega 32x"]):
        fallback_plats.append("sega_32x")
    if any(k in t_lower for k in ["sega cd", "mega cd"]):
        fallback_plats.append("sega_cd")
    if any(k in t_lower for k in ["gamecube", "gc"]):
        fallback_plats.append("gamecube")
    if any(k in t_lower for k in ["wii u", "wiiu"]):
        fallback_plats.append("wiiu")
    elif "wii" in t_lower:
        fallback_plats.append("wii")
    if "3ds" in t_lower:
        fallback_plats.append("3ds")
    if "nds" in t_lower or "nintendo ds" in t_lower:
        fallback_plats.append("nds")

    return fallback_plats


def harvest_all_sticky_romsets():
    """Собирает и добавляет закреплённые ромсеты во все базы."""
    print("=" * 65)
    print("Сбор закреплённых ромсетов со всех форумов RuTracker")
    print("=" * 65)

    platform_data = load_existing_topic_ids()
    added_counts = {p: 0 for p in SUPPORTED_PLATFORMS}

    try:
        for forum_id in sorted(FORUM_TO_PLATFORMS.keys(), key=int):
            torrents = get_sticky_torrents_from_forum(forum_id)

            for tor in torrents:
                tid = tor["topic_id"]
                raw_title = tor["raw_title"]
                size_str = tor["size"]

                target_plats = route_sticky_topic(tid, raw_title, forum_id)
                if not target_plats:
                    print(f"  [~] Платформа вне списка поддерживаемых консолей: {raw_title[:65]}")
                    continue

                # Проверяем, нужно ли скачивать тему (если хотя бы в одной платформе её нет)
                needs_fetch = any(tid not in platform_data[p] for p in target_plats)
                if not needs_fetch:
                    # Уже есть во всех базах, просто проверяем маркировку
                    for p in target_plats:
                        existing = platform_data[p][tid]
                        if not existing.get("is_romset"):
                            existing["is_romset"] = True
                            existing["content_type"] = "romset"
                    continue

                print(f"\n  [+] Загрузка ромсета: t={tid} -> {target_plats} | {raw_title[:60]}")
                details = get_topic_data(tid)
                if not details or not details.get("magnet"):
                    print(f"      [!] Не удалось получить данные темы t={tid}")
                    continue

                # Формируем запись игры
                clean_t = clean_title(raw_title)
                game_entry = {
                    "title": clean_t,
                    "size": details.get("size") or size_str,
                    "magnet": details.get("magnet"),
                    "topic_id": str(tid),
                    "url": f"{BASE_URL}viewtopic.php?t={tid}",
                    "year": details.get("year", "Unknown"),
                    "genre": details.get("genre", "Unknown"),
                    "developer": details.get("developer", "Unknown"),
                    "publisher": details.get("publisher", "Unknown"),
                    "image_format": details.get("image_format", "Unknown"),
                    "interface_lang": details.get("interface_lang", "Unknown"),
                    "voice_lang": details.get("voice_lang", "Unknown"),
                    "performance": details.get("performance", "Unknown"),
                    "multiplayer": details.get("multiplayer", "Unknown"),
                    "cover": details.get("cover"),
                    "screenshots": details.get("screenshots", []),
                    "description": details.get("description", ""),
                    "title_id": details.get("title_id"),
                    "is_romset": True,
                    "content_type": "romset",
                }

                for p in target_plats:
                    if tid not in platform_data[p]:
                        platform_data[p][tid] = game_entry
                        added_counts[p] += 1
                        print(f"      -> Добавлено в {p.upper()}")

                time.sleep(1.5)  # Вежливая пауза между загрузками тем

    finally:
        close_driver()

    # Сохраняем обновленные базы
    print("\n" + "=" * 65)
    print("Сохранение обновленных баз данных:")
    print("=" * 65)
    for p in sorted(SUPPORTED_PLATFORMS):
        games_list = list(platform_data[p].values())
        fpath = DATA_DIR / f"{p}_games.json"
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(games_list, f, ensure_ascii=False, indent=2)
        added = added_counts[p]
        print(f"  {p:<12}: всего={len(games_list):4}, добавлено новых ромсетов={added}")

    print("=" * 65)
    print(f"ИТОГО добавлено новых записей ромсетов: {sum(added_counts.values())}")
    print("=" * 65)


if __name__ == "__main__":
    harvest_all_sticky_romsets()
