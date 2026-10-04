"""Сбор статистики раздач (сиды, личи, загрузки, дата добавления) для консольных игр.

3-фазная архитектура для достижения 100% покрытия баз:
- Фаза 1: Быстрый сбор через срезы tracker.php (сиды, загрузки, дата, размер, название, личи).
- Фаза 2: Точечный обход оставшихся раздач через viewtopic.php для 100% покрытия.
- Фаза 3: Контрольный повторный проход первых 3 страниц tracker.php.
"""
import datetime
import json
import os
import re
import time
import urllib.parse
from bs4 import BeautifulSoup

from core.network import BASE_URL, fetch_url
from core.storage import save_json, load_json, BASE_DIR
from platforms.registry import (
    FORUM_TO_PLATFORMS,
    get_all_forum_ids,
    get_platforms_for_forum,
    get_platform_config
)

DATA_DIR = os.path.join(BASE_DIR, 'data')
STATS_FILE = os.path.join(DATA_DIR, 'console_games_stats.json')


def normalize_rutracker_date(dt_str):
    """Приводит строковую дату RuTracker (15-Сен-24 14:20) к стандартному формату YYYY-MM-DD HH:MM:SS."""
    if not dt_str:
        return None
    months = {
        'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04', 'май': '05', 'июн': '06',
        'июл': '07', 'авг': '08', 'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    m = re.match(r'(\d{1,2})-([А-Яа-яA-Za-z]{3})-(\d{2,4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?', dt_str.strip())
    if m:
        d, mon, y, h, mi, s = m.groups()
        mon_num = months.get(mon.lower(), '01')
        if len(y) == 2:
            y = f'20{y}' if int(y) < 70 else f'19{y}'
        s = s or '00'
        return f'{y}-{mon_num}-{int(d):02d} {int(h):02d}:{mi}:{s}'
    return dt_str.strip()


def parse_tracker_page(html):
    """Парсит страницу tracker.php (поиск/список раздач трекера).
    
    Возвращает список словарей:
    [
        {
            "topic_id": "6890951",
            "seeds": 15,
            "leeches": 2,
            "downloads": 450,
            "registered_at": "2024-09-15 14:20:00"
        },
        ...
    ]
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    results = []

    rows = soup.select('#tor-tbl tr[id^="trs-tr-"]')
    if not rows:
        rows = soup.select('table.forumline tr.hl-tr')
    if not rows:
        rows = soup.select('tr.hl-tr')

    for row in rows:
        # 1. Topic ID
        topic_id = None
        link = row.select_one('a[data-topic_id]')
        if link and link.get('data-topic_id'):
            topic_id = link['data-topic_id'].strip()
        else:
            link = row.select_one('a.tt-text, a[href*="viewtopic.php?t="]')
            if link and link.get('href'):
                m = re.search(r't=(\d+)', link['href'])
                if m:
                    topic_id = m.group(1)

        if not topic_id:
            continue

        # 2. Leeches (класс leechmed)
        leeches = 0
        leech_td = row.select_one('td.leechmed, span.leechmed, u.leechmed, td[class*="leech"]')
        if leech_td:
            b_tag = leech_td.find('b')
            leech_txt = b_tag.get_text(strip=True) if b_tag else leech_td.get_text(strip=True)
            m = re.search(r'\d+', leech_txt)
            if m:
                leeches = int(m.group(0))
            else:
                ts = leech_td.get('data-ts_text')
                if ts and ts.isdigit():
                    leeches = int(ts)

        # 3. Seeds (колонка непосредственно перед leech_td)
        seeds = 0
        seed_td = None
        if leech_td and leech_td.name == 'td':
            seed_td = leech_td.find_previous_sibling('td')
        elif leech_td:
            parent_td = leech_td.find_parent('td')
            if parent_td:
                seed_td = parent_td.find_previous_sibling('td')

        if not seed_td:
            seed_td = row.select_one('td.seedmed, b.seedmed, span.seedmed, u.seedmed, td[class*="seed"]')

        if seed_td:
            b_tag = seed_td.find('b')
            seed_txt = b_tag.get_text(strip=True) if b_tag else seed_td.get_text(strip=True)
            m = re.search(r'\d+', seed_txt)
            if m:
                seeds = int(m.group(0))
            else:
                ts = seed_td.get('data-ts_text')
                if ts and ts.lstrip('-').isdigit():
                    seeds = max(0, int(ts))

        # 4. Downloads
        downloads = 0
        downloads_td = None
        if leech_td and leech_td.name == 'td':
            downloads_td = leech_td.find_next_sibling('td')
        elif leech_td:
            parent_td = leech_td.find_parent('td')
            if parent_td:
                downloads_td = parent_td.find_next_sibling('td')

        if downloads_td:
            ts = downloads_td.get('data-ts_text')
            if ts and ts.isdigit():
                downloads = int(ts)
            else:
                raw_dl = re.sub(r'\D', '', downloads_td.get_text(strip=True))
                if raw_dl:
                    downloads = int(raw_dl)

        # 5. Registered At
        registered_at = None
        reg_td = None
        if downloads_td:
            reg_td = downloads_td.find_next_sibling('td')

        if reg_td:
            ts = reg_td.get('data-ts_text')
            if ts and ts.isdigit():
                try:
                    dt = datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc)
                    registered_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
            if not registered_at:
                txt = reg_td.get_text(' ', strip=True)
                if txt:
                    registered_at = normalize_rutracker_date(txt)

        results.append({
            "topic_id": str(topic_id),
            "seeds": seeds,
            "leeches": leeches,
            "downloads": downloads,
            "registered_at": registered_at
        })

    return results


def parse_topic_stats(html):
    """Парсит сиды, личи, количество скачиваний и дату регистрации из страницы темы (viewtopic.php)."""
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    stats = {'seeds': 0, 'leeches': 0, 'downloads': 0, 'registered_at': None}

    # 1. Сиды
    seed_el = soup.select_one('span.seed, b.seed, span.seedmed, td.seedmed')
    if seed_el:
        m = re.search(r'\d+', seed_el.get_text())
        if m:
            stats['seeds'] = int(m.group(0))
    if stats['seeds'] == 0:
        m = re.search(r'Сиды\s*:\s*(?:<[^>]+>)*\s*(\d+)', html, re.IGNORECASE)
        if m:
            stats['seeds'] = int(m.group(1))

    # 2. Личи
    leech_el = soup.select_one('span.leech, b.leech, span.leechmed, td.leechmed')
    if leech_el:
        m = re.search(r'\d+', leech_el.get_text())
        if m:
            stats['leeches'] = int(m.group(0))
    if stats['leeches'] == 0:
        m = re.search(r'(?:Личи|Пиры)\s*:\s*(?:<[^>]+>)*\s*(\d+)', html, re.IGNORECASE)
        if m:
            stats['leeches'] = int(m.group(1))

    # 3. Скачивания
    dl_el = soup.select_one('#tor-completed, span.tor-completed')
    if dl_el:
        raw_dl = re.sub(r'\D', '', dl_el.get_text())
        if raw_dl:
            stats['downloads'] = int(raw_dl)
    if stats['downloads'] == 0:
        m = re.search(r'Скачан\s*:\s*(?:<[^>]+>)*\s*([0-9\s,]+)\s*раз', html, re.IGNORECASE)
        if m:
            raw_dl = re.sub(r'\D', '', m.group(1))
            if raw_dl:
                stats['downloads'] = int(raw_dl)

    # 4. Дата регистрации
    reg_m = re.search(r'Зарегистрирован\s*:\s*(?:<[^>]+>)*\s*([0-9]{1,2}-[А-Яа-яA-Za-z]{3}-[0-9]{2,4}\s+[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?|[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)', html, re.IGNORECASE)
    if reg_m:
        stats['registered_at'] = normalize_rutracker_date(reg_m.group(1))
    if not stats['registered_at']:
        for td in soup.find_all(['td', 'th', 'div', 'span']):
            txt = td.get_text().strip()
            if 'зарегистрирован' in txt.lower():
                next_td = td.find_next_sibling('td')
                if next_td:
                    val = next_td.get_text(strip=True)
                    if val and len(val) < 40:
                        stats['registered_at'] = normalize_rutracker_date(val)
                        break

    return stats


def _crawl_tracker_query(base_tracker_url, stats_data, max_pages=None, now_str=None, refreshed_ids=None):
    """Обходит страницы tracker.php для заданного URL."""
    if now_str is None:
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    page_num = 0
    total_found = 0

    while True:
        if max_pages is not None and page_num >= max_pages:
            break

        start = page_num * 50
        sep = '&' if '?' in base_tracker_url else '?'
        tracker_url = f"{base_tracker_url}{sep}start={start}"

        html = fetch_url(tracker_url, forum_url=True, wait_keywords=('tor-tbl', 'hl-tr', 'tracker'))
        if not html:
            break

        if 'слишком коротк' in html.lower() or 'too short' in html.lower():
            return -2

        if 'не найдено' in html.lower() or 'not found' in html.lower():
            break

        if 'login_username' in html or ('login.php' in html and 'profile.php' not in html and 'tor-tbl' not in html):
            print("[!] tracker.php требует авторизации. Проверьте RUTRACKER_COOKIES (bb_session, bb_guid) в .env.")
            return -1

        page_entries = parse_tracker_page(html)
        if not page_entries:
            break

        new_on_page = 0
        for entry in page_entries:
            tid = str(entry["topic_id"])
            stats_data[tid] = {
                "seeds": entry["seeds"],
                "leeches": entry["leeches"],
                "downloads": entry["downloads"],
                "registered_at": entry["registered_at"],
                "updated_at": now_str
            }
            if refreshed_ids is not None:
                refreshed_ids.add(tid)
            new_on_page += 1
            total_found += 1

        if len(page_entries) < 50:
            break

        page_num += 1
        time.sleep(0.3)

    return total_found


def scrape_torrents_stats(output_file=None, target_forums=None, target_platforms=None, max_pages=None, full_scan=True):
    """3-фазный сбор и поддержание актуальности статистики раздач (сиды, личи, загрузки, дата добавления)
    по 100% консольных игр из баз data/*_games.json.

    - Фаза 1: Быстрый сбор через срезы tracker.php по каждому форуму (сиды, загрузки, дата, размер, названия, личи).
    - Фаза 2: Точечный обход оставшихся раздач через viewtopic.php?t=ID для достижения 100% покрытия
              всех тем соответствующих разделов. Прогресс сохраняется на диск каждые 25 тем.
    - Фаза 3: Контрольный повторный обход первых 3 страниц трекера (tracker.php) для гарантированной свежести
              самых новых и динамичных раздач после завершения Фазы 2.
    """
    if output_file is None:
        output_file = STATS_FILE

    print("[*] Сбор статистики раздач (3-фазный режим для 100% покрытия)...")

    # Загружаем существующую статистику
    stats_data = {}
    if os.path.exists(output_file):
        try:
            loaded = load_json(output_file)
            if isinstance(loaded, dict):
                stats_data = loaded
            elif isinstance(loaded, list):
                stats_data = {str(item['topic_id']): item for item in loaded if item.get('topic_id')}
            print(f"[*] Загружена существующая статистика: {len(stats_data)} раздач в {os.path.basename(output_file)}.")
        except Exception as e:
            print(f"(!) Ошибка чтения {output_file}: {e}")

    # Определяем целевые форумы и платформы
    if target_forums:
        forums_to_scan = [str(f) for f in target_forums]
    elif target_platforms:
        forums_to_scan = list({get_platform_config(p)['forum_id'] for p in target_platforms if get_platform_config(p)})
    else:
        forums_to_scan = get_all_forum_ids()

    # Собираем список всех уникальных topic_id для выбранных платформ/форумов
    relevant_platforms = []
    if target_platforms:
        relevant_platforms = list(target_platforms)
    else:
        for fid in forums_to_scan:
            relevant_platforms.extend(get_platforms_for_forum(fid))
    relevant_platforms = list(dict.fromkeys(relevant_platforms))

    all_game_topics = []
    seen_topics = set()
    for p in relevant_platforms:
        cfg = get_platform_config(p)
        if cfg and os.path.exists(cfg['filename']):
            items = load_json(cfg['filename'])
            for it in items:
                tid = str(it.get('topic_id', '')).strip()
                if tid and tid not in seen_topics:
                    seen_topics.add(tid)
                    all_game_topics.append(tid)

    print(f"[*] Найдено тем для сбора статистики: {len(all_game_topics)} по {len(relevant_platforms)} платформам ({len(forums_to_scan)} форумов).")

    now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    refreshed_ids = set()

    # ──────────────────────────────────────────────────────────
    # Фаза 1: Быстрый сбор через срезы tracker.php для всех форумов
    # ──────────────────────────────────────────────────────────
    print(f"\n--- Фаза 1: Сбор активных раздач через срезы tracker.php ({len(forums_to_scan)} форумов) ---")
    for fid in forums_to_scan:
        plats_str = ', '.join(get_platforms_for_forum(fid))
        print(f"\n  [*] Форум f={fid} [{plats_str}]:")
        sort_slices = [
            ("сиды (убыв.)", f"{BASE_URL}tracker.php?f={fid}&o=10&s=2"),
            ("скачивания (убыв.)", f"{BASE_URL}tracker.php?f={fid}&o=4&s=2"),
            ("дата (свежие)", f"{BASE_URL}tracker.php?f={fid}&o=1&s=2"),
            ("дата (старые)", f"{BASE_URL}tracker.php?f={fid}&o=1&s=1"),
            ("размер (крупные)", f"{BASE_URL}tracker.php?f={fid}&o=7&s=2"),
            ("название (A-Z)", f"{BASE_URL}tracker.php?f={fid}&o=2&s=1"),
            ("название (Z-A)", f"{BASE_URL}tracker.php?f={fid}&o=2&s=2"),
            ("личи (убыв.)", f"{BASE_URL}tracker.php?f={fid}&o=11&s=2"),
        ]

        for label, slice_url in sort_slices:
            print(f"    [*] Срез: {label}...")
            res = _crawl_tracker_query(slice_url, stats_data, max_pages=max_pages, now_str=now_str, refreshed_ids=refreshed_ids)
            if res == -1:
                print(f"    [!] Остановка Фазы 1 для форума f={fid} из-за ошибки авторизации.")
                break
            print(f"        Получено: {max(0, res)} (уникально обновлено в сессии: {len(refreshed_ids)})")
            time.sleep(0.4)

    save_json(stats_data, output_file)
    print(f"\n[+] Фаза 1 завершена: {len(refreshed_ids)} раздач обновлено (всего в базе статистики: {len(stats_data)})")

    # ──────────────────────────────────────────────────────────
    # Фаза 2: Точечный обход оставшихся тем через viewtopic.php
    # ──────────────────────────────────────────────────────────
    if full_scan and all_game_topics:
        missing_ids = [tid for tid in all_game_topics if tid not in stats_data]
        stale_ids = [tid for tid in all_game_topics if tid in stats_data and tid not in refreshed_ids]
        remaining_ids = missing_ids + stale_ids

        total_remaining = len(remaining_ids)
        print(f"\n--- Фаза 2: Обход оставшихся тем через viewtopic.php ({total_remaining} тем) ---")
        print(f"  * Новых тем без статистики: {len(missing_ids)}")
        print(f"  * Старых/не обновлённых в фазе 1 тем: {len(stale_ids)}")

        if max_pages is not None:
            phase2_limit = max_pages * 50 if max_pages > 1 else max_pages
            remaining_ids = remaining_ids[:phase2_limit]
            print(f"  [*] Установлен лимит Фазы 2: {len(remaining_ids)} тем.")

        phase2_processed = 0
        phase2_saved = 0
        for tid in remaining_ids:
            topic_url = f"{BASE_URL}viewtopic.php?t={tid}"
            html = fetch_url(topic_url, forum_url=False, wait_keywords=('post_body', 'attach', 'viewtopic'))
            if html:
                parsed = parse_topic_stats(html)
                if parsed:
                    stats_data[tid] = {
                        "seeds": parsed["seeds"],
                        "leeches": parsed["leeches"],
                        "downloads": parsed["downloads"],
                        "registered_at": parsed["registered_at"],
                        "updated_at": now_str
                    }
                    refreshed_ids.add(tid)
                    phase2_processed += 1
            else:
                print(f"  [!] Не удалось получить тему {tid}")

            phase2_saved += 1
            if phase2_saved % 25 == 0:
                save_json(stats_data, output_file)
                print(f"  [~] Фаза 2: обработано {phase2_saved}/{len(remaining_ids)} тем (всего в stats: {len(stats_data)}/{len(all_game_topics)})")

            time.sleep(0.3)

        save_json(stats_data, output_file)
        print(f"[+] Фаза 2 завершена: успешно обработано {phase2_processed} тем.")

    # ──────────────────────────────────────────────────────────
    # Фаза 3: Повторный обход первых 3 страниц трекера
    # ──────────────────────────────────────────────────────────
    print(f"\n--- Фаза 3: Контрольный повторный проход первых 3 страниц tracker.php ({len(forums_to_scan)} форумов) ---")
    for fid in forums_to_scan:
        base_url = f"{BASE_URL}tracker.php?f={fid}"
        p3_res = _crawl_tracker_query(base_url, stats_data, max_pages=3, now_str=now_str, refreshed_ids=refreshed_ids)
        print(f"  [+] Форум f={fid}: свежие раздачи актуализированы ({max(0, p3_res)} записей).")

    # Итоговое сохранение и вычисление статистики
    save_json(stats_data, output_file)
    print(f"\n[+] Сбор статистики полностью завершён. Сохранено {len(stats_data)} записей в {output_file}")

    total_seeds = sum(item.get('seeds', 0) for item in stats_data.values())
    total_downloads = sum(item.get('downloads', 0) for item in stats_data.values())
    relevant_in_stats = [tid for tid in all_game_topics if tid in stats_data]
    coverage_pct = (len(relevant_in_stats) / len(all_game_topics) * 100) if all_game_topics else 100

    print(f"    * Покрытие текущей выборки: {len(relevant_in_stats)} / {len(all_game_topics)} ({coverage_pct:.1f}%)")
    print(f"    * Активных сидов: {total_seeds}")
    print(f"    * Суммарно скачиваний: {total_downloads}")

    return {
        "total": len(stats_data),
        "total_seeds": total_seeds,
        "total_downloads": total_downloads,
        "coverage_pct": coverage_pct,
        "covered_topics": len(relevant_in_stats),
        "target_topics": len(all_game_topics)
    }
