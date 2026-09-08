"""Парсинг страниц форума RuTracker с динамическим пропуском закреплённых тем."""
import time
from bs4 import BeautifulSoup

from core.network import fetch_url, BASE_URL


def is_sticky_topic(row):
    """Определяет, является ли строка форума объявлением или закреплённой темой (Sticky/Announcement).

    Признаки на RuTracker:
    - Иконка темы содержит folder_announce / folder_sticky / folder_lock
    - Наличие класса темы или заголовка, характерного для правил/навигатора
    - Отсутствие размера торрента или сидов/личей в соответствующих колонках
    """
    # 1. Проверяем иконку темы (td.topic_icon)
    icon_td = row.select_one('td.topic_icon, td.t-ico')
    if icon_td:
        img = icon_td.find('img')
        if img:
            src = img.get('src', '').lower()
            if any(marker in src for marker in ('announce', 'sticky', 'folder_announce', 'folder_sticky')):
                return True

    # 2. Проверяем класс строки или заголовка
    classes = row.get('class', [])
    if any('sticky' in c.lower() or 'announce' in c.lower() for c in classes):
        return True

    # 3. Проверяем наличие ключевых слов в названии темы (правила, навигатор, FAQ)
    link = row.select_one('a.tt-text')
    if link:
        title_text = link.get_text().strip().lower()
        if any(kw in title_text for kw in (
            'правила раздела', 'навигатор по разделу', 'список раздач раздела',
            'важная информация', 'поиск и заказ игр', 'правила подраздела'
        )):
            return True

    return False


def scrape_forum_page(forum_id, page_num=0):
    """Загружает страницу форума и возвращает список найденных тем.

    На первой странице (page_num == 0) на RuTracker темы разделены секциями:
    Правила -> Объявления -> Прилеплены -> Темы.
    Все раздачи до строки-разделителя 'Темы' автоматически пропускаются.

    Возвращает:
        list of dict: [{"topic_id": str, "raw_title": str, "url": str}, ...]
    """
    start = page_num * 50
    forum_url = f"{BASE_URL}viewforum.php?f={forum_id}&start={start}"
    print(f"\n--- Форум f={forum_id}, Страница {page_num + 1} ({forum_url}) ---")

    html = fetch_url(forum_url, forum_url=True)
    if not html:
        print(f"[!] Не удалось загрузить страницу {page_num + 1} для f={forum_id}.")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.select_one('table.vf-table, table.forumline') or soup
    rows = table.find_all('tr', recursive=False) or table.select('tr')
    if not rows:
        print(f"[*] Тем не найдено на странице {page_num + 1}.")
        return []

    topics = []
    skipped_sticky = 0

    # Проверяем наличие разделителя "Темы" на странице
    has_temy_separator = any(
        len(r.find_all('td', recursive=False)) == 1 and 'Темы' in r.text
        for r in rows
    )
    in_regular_topics = (page_num > 0) or (not has_temy_separator)

    for row in rows:
        tds = row.find_all('td', recursive=False)
        if len(tds) == 1:
            sep_text = tds[0].text.strip()
            if 'Темы' in sep_text:
                in_regular_topics = True
                continue
            elif not in_regular_topics:
                continue

        link_tag = row.select_one('a.tt-text')
        if not link_tag:
            continue

        if not in_regular_topics:
            skipped_sticky += 1
            continue

        # Проверяем, что это не закрепленная тема по иконке
        img = row.select_one('img.topic_icon')
        if img:
            src = img.get('src', '').lower()
            if 'folder_sticky' in src or 'folder_announce' in src:
                skipped_sticky += 1
                continue

        href = link_tag.get('href', '')
        if 't=' not in href:
            continue
        topic_id = href.split('t=')[-1].split('&')[0]
        if not topic_id:
            continue

        raw_title = link_tag.get_text().strip()
        topics.append({
            "topic_id": str(topic_id),
            "raw_title": raw_title,
            "url": f"{BASE_URL}viewtopic.php?t={topic_id}"
        })

    if page_num == 0 and skipped_sticky > 0:
        print(f"[*] Пропущено закреплённых тем (до разделителя 'Темы'): {skipped_sticky}. Найдено обычных раздач: {len(topics)}")

    return topics
