"""Главный CLI-парсер игровых баз RuTracker для консольных систем.

Поддерживаемые разделы:
- f=1352 -> PSP (psp_games.json)
- f=908  -> PS1 (ps1_games.json)
- f=773  -> Wii U, Wii, GameCube (разделяются по отдельным базам)
- f=129  -> NES, SNES, N64, GBA, GBC (GB+GBC), Sega (MD, MS, GG, CD, 32X)

Использование:
  python scraper.py                  # Инкрементальное обновление всех систем через Atom-ленты
  python scraper.py --platform psp   # Обновление только PSP
  python scraper.py --forum 773      # Обновление всех систем раздела f=773
  python scraper.py --full --platform ps1 # Полный парсинг PS1
  python scraper.py --full --forum 129 --max-pages 5 # Пробный сбор 5 страниц ретро-форума
"""
import argparse
import os
import sys
import time

# Принудительно UTF-8 для Windows консоли
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core.network import BASE_URL, fetch_url, close_driver, init_env
from core.topic_parser import get_topic_data, clean_title, parse_feed_title
from core.forum import scrape_forum_page
from core.atom import fetch_atom_feed
from core.storage import (
    load_json,
    save_json,
    enrich_incomplete,
    write_changes_log,
    BASE_DIR
)
from platforms.registry import (
    FORUM_TO_PLATFORMS,
    get_all_platforms,
    get_all_forum_ids,
    get_platforms_for_forum,
    get_forum_for_platform,
    get_platform_config
)
from platforms.classifiers import classify_topic


def get_game_entry(topic_id, title, details, raw_title=""):
    """Формирует стандартный словарь записи игры."""
    return {
        "title": title,
        "size": details.get("size", "Unknown"),
        "magnet": details.get("magnet"),
        "topic_id": str(topic_id),
        "url": f"{BASE_URL}viewtopic.php?t={topic_id}",
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
    }


def scrape_full_forum(forum_id, target_platforms=None, max_pages=None, limit=None):
    """Полный парсинг раздела форума с автоматической маршрутизацией тем по базам данных."""
    all_forum_plats = get_platforms_for_forum(forum_id)
    if not all_forum_plats:
        print(f"[!] Неизвестный форум f={forum_id}")
        return {}

    active_plats = target_platforms if target_platforms else all_forum_plats
    print(f"\n=======================================================")
    print(f"[*] ПОЛНЫЙ ПАРСИНГ форума f={forum_id}")
    print(f"[*] Активные платформы: {', '.join(active_plats)}")
    if limit:
        print(f"[*] Лимит тем: {limit}")
    print(f"=======================================================")

    # Загружаем существующие данные или создаем новые списки
    plat_data = {}
    plat_maps = {}
    for p in active_plats:
        cfg = get_platform_config(p)
        items = load_json(cfg['filename'])
        plat_data[p] = items
        plat_maps[p] = {str(item.get('topic_id')): item for item in items if item.get('topic_id')}
        print(f"  [{p}] Загружено существующих записей: {len(items)}")

    seen_ids = set()
    for p in active_plats:
        seen_ids.update(plat_maps[p].keys())

    page_num = 0
    total_new = 0

    while True:
        if max_pages is not None and page_num >= max_pages:
            print(f"[*] Достигнут лимит страниц ({max_pages}).")
            break
        if limit is not None and total_new >= limit:
            print(f"[*] Достигнут лимит тем ({limit}).")
            break

        topics = scrape_forum_page(forum_id, page_num=page_num)
        if not topics:
            print(f"[*] На странице {page_num + 1} нет тем. Конец форума.")
            break

        new_on_page = 0
        for top in topics:
            if limit is not None and total_new >= limit:
                break
            tid = top["topic_id"]
            raw_title = top["raw_title"]

            # Классифицируем тему
            matched_platforms = classify_topic(forum_id, raw_title)
            # Оставляем только те, которые активны для текущего запуска
            matched_active = [p for p in matched_platforms if p in active_plats]

            if not matched_active:
                continue

            # Проверяем, есть ли тема уже во всех подходящих базах
            all_exist = all(tid in plat_maps[p] for p in matched_active)
            if all_exist:
                continue

            print(f"  [{tid}] -> [{', '.join(matched_active)}] {raw_title[:65]}...")

            # Загружаем детали темы один раз
            first_plat = matched_active[0]
            details = get_topic_data(tid, platform_key=first_plat)

            for p in matched_active:
                if tid in plat_maps[p]:
                    continue
                cfg = get_platform_config(p)
                clean_t = clean_title(raw_title, cfg.get('strip_tags_re'))
                p_details = dict(details)
                # Если у второй платформы требуется свой title_id
                if p != first_plat and cfg.get('has_title_id'):
                    p_details["title_id"] = details.get("title_id")

                entry = get_game_entry(tid, clean_t, p_details, raw_title=raw_title)
                plat_data[p].append(entry)
                plat_maps[p][tid] = entry
                total_new += 1
                new_on_page += 1

                # Промежуточное сохранение
                if len(plat_data[p]) % 10 == 0:
                    save_json(plat_data[p], cfg['filename'])

            time.sleep(0.2)

        # Сохраняем все затронутые базы после страницы
        for p in active_plats:
            cfg = get_platform_config(p)
            save_json(plat_data[p], cfg['filename'])

        if len(topics) < 50:
            print("[*] Последняя страница форума достигнута.")
            break

        page_num += 1
        time.sleep(0.5)

    print(f"\n[+] Полный парсинг f={forum_id} завершён. Добавлено новых раздач: {total_new}")
    return plat_data


def update_forum_via_atom(forum_id, target_platforms=None):
    """Инкрементальное обновление баз форума через Atom-ленту (последние 50 раздач)."""
    all_forum_plats = get_platforms_for_forum(forum_id)
    active_plats = [p for p in target_platforms if p in all_forum_plats] if target_platforms else all_forum_plats

    if not active_plats:
        return {}

    print(f"\n[*] Проверка Atom-ленты для f={forum_id} (платформы: {', '.join(active_plats)})...")

    # Загружаем базы
    plat_data = {}
    plat_maps = {}
    for p in active_plats:
        cfg = get_platform_config(p)
        items = load_json(cfg['filename'])
        plat_data[p] = items
        plat_maps[p] = {str(item.get('topic_id')): item for item in items if item.get('topic_id')}

    atom_entries = fetch_atom_feed(forum_id)
    if not atom_entries:
        print(f"[!] Не удалось получить Atom-ленту для f={forum_id}")
        return {}

    changes_stats = {
        p: {"added": [], "updated": [], "enriched": [], "total": len(plat_data[p])}
        for p in active_plats
    }

    for item in atom_entries:
        tid = item["topic_id"]
        raw_title = item["raw_title"]

        matched_platforms = classify_topic(forum_id, raw_title)
        matched_active = [p for p in matched_platforms if p in active_plats]

        if not matched_active:
            continue

        cached_details = None

        for p in matched_active:
            cfg = get_platform_config(p)
            clean_t, feed_sz = parse_feed_title(raw_title, cfg.get('strip_tags_re'))

            if tid in plat_maps[p]:
                old_item = plat_maps[p][tid]
                needs_update = (
                    old_item.get('title') != clean_t
                    or (feed_sz != "Unknown" and old_item.get('size') != feed_sz)
                    or (cfg.get('has_title_id') and not old_item.get('title_id'))
                    or old_item.get('year') in ('Unknown', '', None)
                )
                if needs_update:
                    print(f"  [~] ОБНОВЛЕНИЕ [{p}] [{tid}] {clean_t[:55]}...")
                    if cached_details is None:
                        cached_details = get_topic_data(tid, platform_key=p)
                    details = dict(cached_details)

                    old_item['title'] = clean_t
                    if details['size'] != 'Unknown':
                        old_item['size'] = details['size']
                    elif feed_sz != 'Unknown':
                        old_item['size'] = feed_sz

                    for k, v in details.items():
                        if k == 'size':
                            continue
                        if v not in (None, "Unknown", [], ""):
                            old_item[k] = v
                        elif k not in old_item:
                            old_item[k] = v

                    changes_stats[p]["updated"].append(clean_t[:80])
            else:
                print(f"  [+] НОВАЯ игра [{p}] [{tid}] {clean_t[:55]}...")
                if cached_details is None:
                    cached_details = get_topic_data(tid, platform_key=p)
                details = dict(cached_details)

                if details['size'] == 'Unknown' and feed_sz != 'Unknown':
                    details['size'] = feed_sz

                new_entry = get_game_entry(tid, clean_t, details, raw_title=raw_title)
                plat_data[p].insert(0, new_entry)
                plat_maps[p][tid] = new_entry
                changes_stats[p]["added"].append(clean_t[:80])

    # Дообогащение первых 100 записей каждой базы
    for p in active_plats:
        cfg = get_platform_config(p)
        done_enr, enr_titles = enrich_incomplete(plat_data[p], p, limit=100)
        changes_stats[p]["enriched"] = enr_titles
        changes_stats[p]["total"] = len(plat_data[p])

        # Сохраняем обновленный JSON
        added_cnt = len(changes_stats[p]["added"])
        updated_cnt = len(changes_stats[p]["updated"])
        if added_cnt > 0 or updated_cnt > 0 or done_enr > 0:
            save_json(plat_data[p], cfg['filename'])
            print(f"[+] База {cfg['name']} сохранена: +{added_cnt}, ~{updated_cnt}, *{done_enr}. Всего: {len(plat_data[p])}")

    return changes_stats


def run(target_platforms=None, target_forums=None, full=False, max_pages=None, enrich_only=False, limit=None):
    """Главная точка входа парсера."""
    init_env()

    # Определяем список целевых форумов
    if target_forums:
        forums_to_run = [str(f) for f in target_forums if str(f) in FORUM_TO_PLATFORMS]
    elif target_platforms:
        forums_to_run = list({get_forum_for_platform(p) for p in target_platforms if get_forum_for_platform(p)})
    else:
        forums_to_run = get_all_forum_ids()

    all_stats = {}

    try:
        for fid in forums_to_run:
            forum_plats = get_platforms_for_forum(fid)
            active_plats = [p for p in target_platforms if p in forum_plats] if target_platforms else forum_plats

            if enrich_only:
                for p in active_plats:
                    cfg = get_platform_config(p)
                    data = load_json(cfg['filename'])
                    print(f"[*] Дообогащение для {cfg['name']} ({len(data)} записей)...")
                    done, titles = enrich_incomplete(data, p, limit=100)
                    save_json(data, cfg['filename'])
                    all_stats[p] = {"added": [], "updated": [], "enriched": titles, "total": len(data)}
                continue

            # Проверяем, существует ли хотя бы одна база этого раздела
            any_missing = any(not os.path.exists(get_platform_config(p)['filename']) for p in active_plats)

            if full or any_missing:
                print(f"[*] Запуск полного парсинга для f={fid} (full={full}, missing={any_missing})...")
                scrape_full_forum(fid, target_platforms=active_plats, max_pages=max_pages, limit=limit)
                # После полного сбора обновляем счетчики
                for p in active_plats:
                    cfg = get_platform_config(p)
                    data = load_json(cfg['filename'])
                    all_stats[p] = {"added": [f"Полный парсинг ({len(data)} записей)"], "updated": [], "enriched": [], "total": len(data)}
            else:
                stats = update_forum_via_atom(fid, target_platforms=active_plats)
                all_stats.update(stats)

        # Записываем общий лог изменений
        write_changes_log(all_stats)
        print("\n[+] Обновление завершено. Лог записан в changes.txt")

    finally:
        close_driver()


def main():
    parser = argparse.ArgumentParser(description="Мультиплатформенный парсер раздач RuTracker")
    parser.add_argument('--platform', type=str, choices=get_all_platforms(), help="Запустить для конкретной платформы")
    parser.add_argument('--forum', type=str, choices=get_all_forum_ids(), help="Запустить для конкретного форума")
    parser.add_argument('--full', action='store_true', help="Принудительный полный парсинг всех страниц")
    parser.add_argument('--max-pages', type=int, default=None, help="Максимальное количество страниц при полном парсинге")
    parser.add_argument('--limit', type=int, default=None, help="Ограничить количество обрабатываемых тем для тестового прогона")
    parser.add_argument('--enrich-only', action='store_true', help="Только дообогащение метаданных существующих баз")
    args = parser.parse_args()

    target_plats = [args.platform] if args.platform else None
    target_forums = [args.forum] if args.forum else None

    run(
        target_platforms=target_plats,
        target_forums=target_forums,
        full=args.full,
        max_pages=args.max_pages,
        enrich_only=args.enrich_only,
        limit=args.limit
    )


if __name__ == '__main__':
    main()
