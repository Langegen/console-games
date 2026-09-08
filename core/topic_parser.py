"""Парсинг тем раздач RuTracker и извлечение структурированных метаданных."""
import copy
import re
from html import unescape as html_unescape
from bs4 import BeautifulSoup

from core.network import fetch_url, BASE_URL
from core.id_extractors import extract_platform_id, fetch_filelist_id


def clean_magnet(url):
    """Очистка magnet-ссылки: декодирование HTML-entities и удаление лишних параметров."""
    if not url:
        return url
    url = html_unescape(url).strip()
    url = re.sub(r'[?&]dn=[^&]*', '', url)
    return url


def post_text(post_body):
    """Корректное извлечение текста поста с сохранением переводов строк без разрыва инлайн-тегов."""
    if not post_body:
        return ""
    pb = copy.deepcopy(post_body)
    for br in pb.find_all('br'):
        br.replace_with('\n')
    for block in pb.find_all(['div', 'ul', 'ol', 'li', 'tr', 'table']):
        block.insert_before('\n')
        block.insert_after('\n')
    return pb.get_text()


def clean_title(title, platform_regex=None):
    """Очистка названия темы: удаление тегов платформ в квадратных скобках."""
    clean = title.strip()
    if platform_regex:
        clean = platform_regex.sub('', clean).strip()

    # Очищаем стандартные префиксы в скобках в начале названия, кроме информативных
    while re.match(r'^\[(?!RUS|ENG|Multi|Обновлен|RePack|Rip)[^\]]+\]\s*', clean, re.IGNORECASE):
        # Проверяем, не является ли это полезным тегом
        m = re.match(r'^\[([^\]]+)\]\s*', clean)
        if m:
            tag = m.group(1).lower()
            if any(k in tag for k in ('psp', 'ps1', 'psx', 'wii', 'gamecube', 'nes', 'snes', 'sega', 'n64', 'gba', 'gbc', 'dendy')):
                clean = clean[m.end():].strip()
            else:
                break
        else:
            break

    return clean.replace('"', "'")


def parse_feed_title(raw_title, platform_regex=None):
    """Разбор заголовка из Atom-ленты: извлечение чистого названия и размера в скобках [xx MB]."""
    clean = raw_title.strip()
    if platform_regex:
        clean = platform_regex.sub('', clean).strip()

    size = "Unknown"
    m = re.search(r'\s*\[([0-9.,]+\s*(?:B|KB|MB|GB|TB|КБ|МБ|ГБ|ТБ))\]$', clean, re.IGNORECASE)
    if m:
        size = m.group(1)
        clean = clean[:m.start()].strip()

    clean = clean_title(clean, platform_regex)
    return clean, size


def get_topic_data(topic_id, platform_key=None, html=None):
    """Получает и парсит страницу темы по topic_id."""
    url = f"{BASE_URL}viewtopic.php?t={topic_id}"
    data = {
        "magnet": None,
        "size": "Unknown",
        "title_id": None,
        "year": "Unknown",
        "genre": "Unknown",
        "developer": "Unknown",
        "publisher": "Unknown",
        "image_format": "Unknown",
        "interface_lang": "Unknown",
        "voice_lang": "Unknown",
        "performance": "Unknown",
        "multiplayer": "Unknown",
        "cover": None,
        "screenshots": [],
        "description": ""
    }

    if not html:
        html = fetch_url(url, forum_url=False)
    if not html:
        return data

    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text()

    # 1. Извлечение Title ID / Serial
    if platform_key:
        data["title_id"] = extract_platform_id(platform_key, page_text) or extract_platform_id(platform_key, html)
        if not data["title_id"]:
            data["title_id"] = fetch_filelist_id(topic_id, platform_key)

    # 2. Magnet ссылка
    mag_link = soup.find('a', class_='magnet-link')
    if mag_link and mag_link.get('href'):
        data["magnet"] = clean_magnet(mag_link.get('href'))

    if not data["magnet"]:
        mag_match = re.search(r'(magnet:\?xt=urn:btih:[^\s\"\'<>]+)', html, re.IGNORECASE)
        if mag_match:
            data["magnet"] = clean_magnet(mag_match.group(1))

    # 3. Размер раздачи
    size_el = soup.find(id='tor-size-humn')
    if size_el:
        data["size"] = size_el.get_text(' ', strip=True).replace('\xa0', ' ').strip()

    if data["size"] == "Unknown":
        attach_div = soup.find('div', class_='attach_link')
        if attach_div:
            for li in attach_div.find_all('li'):
                li_text = li.get_text(' ', strip=True).replace('\xa0', ' ').strip()
                if re.search(r'\d[0-9.,]*\s*(?:B|KB|MB|GB|TB|КБ|МБ|ГБ|ТБ)\b', li_text, re.IGNORECASE):
                    data["size"] = li_text
                    break

    # 4. Метаданные из тела поста
    post_body = soup.find('div', class_='post_body')
    if post_body:
        text_content = post_text(post_body)

        patterns = {
            "year": r'(?:Год выпуска|Дата выхода|Год выхода)\s*:\s*([^\n]+)',
            "genre": r'Жанр\s*:\s*([^\n]+)',
            "developer": r'Разработчик\s*:\s*([^\n]+)',
            "publisher": r'Издатель\s*:\s*([^\n]+)',
            "image_format": r'(?:Формат образа|Тип издания|Формат)\s*:\s*([^\n]+)',
            "interface_lang": r'Язык интерфейса\s*:\s*([^\n]+)',
            "voice_lang": r'(?:Язык озвучки|Озвучка)\s*:\s*([^\n]+)',
            "performance": r'(?:Работоспособность проверена|Прошивка|Тестировалось)\s*:\s*([^\n]+)',
            "multiplayer": r'Мультиплеер\s*:\s*([^\n]+)',
        }

        for key, pat in patterns.items():
            m = re.search(pat, text_content, re.IGNORECASE)
            if m:
                data[key] = m.group(1).strip()

        # Fallback для размера
        if data["size"] == "Unknown":
            sz_match = re.search(r'(?:Размер|Объем|Size)\s*(?:раздачи|игры)?\s*:\s*(\d+[,.]\d+\s*(?:MB|GB|МБ|ГБ|KB|КБ))', text_content, re.IGNORECASE)
            if sz_match:
                data["size"] = sz_match.group(1).strip()

        # Обложка и скриншоты
        post_body_html = str(post_body)
        img_urls = []
        for el in post_body.find_all(['var', 'img'], class_='postImg'):
            src_url = (el.get('title') or el.get('src') or '').strip()
            if src_url.startswith('http') and 'rutracker.cc/smiles' not in src_url and src_url not in img_urls:
                img_urls.append(src_url)

        if not img_urls:
            for pattern in [
                r'init-src=["\']?(https://[^"\'>\s]+)',
                r'data-src=["\']?(https://[^"\'>\s]+)',
                r'<img[^>]+src=["\']?(https://[^"\'>\s]+)'
            ]:
                for m in re.finditer(pattern, post_body_html, re.IGNORECASE):
                    src_url = m.group(1).rstrip('/')
                    if 'rutracker.cc/smiles' not in src_url and src_url not in img_urls:
                        img_urls.append(src_url)

        if img_urls:
            data["cover"] = img_urls[0]
            data["screenshots"] = img_urls[1:10]

        # Описание
        desc_match = re.search(
            r'Описание\s*:\s*([\s\S]+?)(?=\n\s*(?:Доп\. информация|Скриншоты|Трейлер|Список файлов|FAQ|Системные требования)|$)',
            text_content, re.IGNORECASE
        )
        if desc_match:
            data["description"] = desc_match.group(1).strip()
        else:
            data["description"] = text_content[:500].strip()

    return data
