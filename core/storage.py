"""Управление хранилищем данных (JSON), дообогащение и логирование изменений."""
import json
import os
import tempfile
import time

from core.topic_parser import get_topic_data, merge_topic_details
from core.id_extractors import fetch_filelist_id
from platforms.registry import get_platform_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGES_FILE = os.path.join(BASE_DIR, 'changes.txt')
ENRICH_STATE_FILE = os.path.join(BASE_DIR, 'enrich_state.json')

# Список полей, которые должны быть заполнены
REQUIRED_FIELDS = (
    'size', 'year', 'genre', 'developer', 'publisher',
    'image_format', 'interface_lang', 'voice_lang', 'performance',
    'multiplayer', 'cover', 'screenshots', 'description', 'magnet'
)


def load_json(filepath):
    """Загружает базу данных игр из JSON файла."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    except Exception as e:
        print(f"[!] Ошибка чтения {filepath}: {e}")
    return []


def save_json(data, filepath):
    """Атомарное сохранение JSON файла (через временный файл с заменой)."""
    try:
        target_dir = os.path.dirname(filepath) or '.'
        os.makedirs(target_dir, exist_ok=True)
        # Пишем во временный файл в той же директории
        tmp_fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix='.tmp')
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # Атомарная замена
        os.replace(tmp_path, filepath)
    except Exception as e:
        print(f"[!] Ошибка записи {filepath}: {e}")


def load_enrich_state():
    """Загрузка состояния дообогащения."""
    try:
        if os.path.exists(ENRICH_STATE_FILE):
            with open(ENRICH_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_enrich_state(state):
    """Сохранение состояния дообогащения."""
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=BASE_DIR, suffix='.tmp')
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, ENRICH_STATE_FILE)
    except Exception as e:
        print(f"[!] Ошибка сохранения enrich_state: {e}")


def enrich_incomplete(data, platform_key, limit=100):
    """Дообогащает неполные записи в базе (первые limit элементов).

    - Проверяет отсутствие метаданных (обложка, скриншоты, описание, размер и т.д.)
    - Для дисковых платформ пытается добрать title_id через viewtorrent
    - Если данные так и не найдены — не трогает запись неделю (state cache).
    """
    state = load_enrich_state()
    now = time.time()

    def _missing(item):
        missing = [
            k for k in REQUIRED_FIELDS
            if not item.get(k) or item.get(k) in ('Unknown', '', None)
            or (k == 'screenshots' and not item.get(k))
        ]
        # Проверяем title_id для платформ, где он обязателен
        cfg = get_platform_config(platform_key)
        if cfg and cfg.get('has_title_id'):
            if not item.get('title_id'):
                missing.append('title_id')
        return missing

    candidates = []
    for idx, item in enumerate(data[:limit]):
        tid = str(item.get('topic_id', ''))
        if not tid:
            continue
        missing = _missing(item)
        if not missing:
            continue
        # Если пробовали менее 7 дней назад — пропускаем
        if state.get(tid) and now - state.get(tid, 0) < 7 * 86400:
            continue
        candidates.append((len(missing), idx, tid, missing, item))

    candidates.sort(key=lambda x: (-x[0], x[1]))

    done = 0
    enriched_titles = []
    for _, _, tid, missing, item in candidates[:limit]:
        only_tid = set(missing) <= {'title_id'}
        if only_tid:
            title_id = fetch_filelist_id(tid, platform_key)
            if title_id:
                item['title_id'] = title_id
                done += 1
                enriched_titles.append(str(item.get('title'))[:80])
                state.pop(tid, None)
            else:
                state[tid] = now
            continue

        print(f"  [*] ДООБОГАЩАЕМ [{platform_key}] [{tid}] {str(item.get('title'))[:50]}...")
        details = get_topic_data(tid, platform_key=platform_key)
        changed = False
        for k in missing:
            v = details.get(k)
            if v not in (None, 'Unknown', '', []):
                item[k] = v
                changed = True
            elif k not in item:
                item[k] = v
                changed = True

        if _missing(item):
            state[tid] = now
        else:
            state.pop(tid, None)

        if changed:
            done += 1
            enriched_titles.append(str(item.get('title'))[:80])

    save_enrich_state(state)
    return done, enriched_titles


def refresh_stale_magnets(data, platform_key, skip_ids=None, limit=20):
    """Круговой проход: перечитать magnet у записей вне сегодняшней Atom-ленты.

    skip_ids — topic_id, которые уже качали из Atom. Курсор хранится в enrich_state.json.
    """
    skip_ids = skip_ids or set()
    state = load_enrich_state()
    n = len(data)
    if not n:
        return 0, []
    cursor_key = f"_magnet_cursor_{platform_key}"
    try:
        cursor = int(state.get(cursor_key, 0) or 0) % n
    except (TypeError, ValueError):
        cursor = 0

    refreshed = []
    fetched = 0
    steps = 0
    while steps < n and fetched < limit:
        idx = (cursor + steps) % n
        steps += 1
        item = data[idx]
        tid = str(item.get('topic_id', ''))
        if not tid or tid in skip_ids:
            continue
        print(f"  [*] MAGNET [{platform_key}] [{tid}] {str(item.get('title'))[:50]}...")
        details = get_topic_data(tid, platform_key=platform_key)
        fetched += 1
        if merge_topic_details(item, details, platform_key=platform_key):
            refreshed.append(str(item.get('title'))[:80])
        time.sleep(0.2)

    state[cursor_key] = (cursor + steps) % n
    save_enrich_state(state)
    return len(refreshed), refreshed


def write_changes_log(platform_changes_map):
    """Формирует и записывает итоговый лог changes.txt для всех платформ.

    platform_changes_map: dict вида
    {
        "psp": {"total": 1200, "added": [...], "updated": [...], "enriched": [...], "magnets": [...]},
        ...
    }
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = [f"=== Обновление баз console-games: {timestamp} ===", ""]

    has_any_change = False
    for plat_key, stats in platform_changes_map.items():
        total = stats.get("total", 0)
        added = stats.get("added", [])
        updated = stats.get("updated", [])
        enriched = stats.get("enriched", [])
        magnets = stats.get("magnets", [])

        if added or updated or enriched or magnets:
            has_any_change = True

        lines.append(f"[{plat_key.upper()}] Всего в базе: {total}")
        if added:
            lines.append(f"  + Добавлено ({len(added)}):")
            lines += [f"    + {t}" for t in added]
        if updated:
            lines.append(f"  ~ Обновлено ({len(updated)}):")
            lines += [f"    ~ {t}" for t in updated]
        if enriched:
            lines.append(f"  * Дообогащено ({len(enriched)}):")
            lines += [f"    * {t}" for t in enriched]
        if magnets:
            lines.append(f"  # Перезалит magnet ({len(magnets)}):")
            lines += [f"    # {t}" for t in magnets]
        lines.append("")

    if not has_any_change:
        lines.append("Изменений по всем платформам нет.")

    try:
        with open(CHANGES_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception as e:
        print(f"[!] Ошибка записи changes.txt: {e}")
