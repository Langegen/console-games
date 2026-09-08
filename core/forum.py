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

    Возвращает:
        list of dict: [{"topic_id": str, "raw_title": str, "url": str, "is_sticky": bool}, ...]
    """
    start = page_num * 50
    forum_url = f"{BASE_URL}viewforum.php?f={forum_id}&start={start}"
    print(f"\n--- Форум f={forum_id}, Страница {page_num + 1} ({forum_url}) ---")

    html = fetch_url(forum_url, forum_url=True)
    if not html:
        print(f"[!] Не удалось загрузить страницу {page_num + 1} для f={forum_id}.")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('tr.hl-tr')
    if not rows:
        print(f"[*] Тем не найдено на странице {page_num + 1}.")
        return []

    topics = []
    skipped_sticky = 0
    for row in rows:
        link_tag = row.select_one('a.tt-text')
        if not link_tag:
            continue

        href = link_tag.get('href', '')
        if 't=' not in href:
            continue
        topic_id = href.split('t=')[-1].split('&')[0]
        if not topic_id:
            continue

        # На первой странице определяем и пропускаем закрепленные темы
        if page_num == 0 and is_sticky_topic(row):
            skipped_sticky += 1
            continue

        raw_title = link_tag.get_text().strip()
        topics.append({
            "topic_id": str(topic_id),
            "raw_title": raw_title,
            "url": f"{BASE_URL}viewtopic.php?t={topic_id}",
            "is_sticky": False
        })

    if page_num == 0 and skipped_sticky > 0:
        print(f"[*] Пропущено закреплённых тем (правила/объявления): {skipped_sticky}. Обычных тем: {len(topics)}")

    return topics
