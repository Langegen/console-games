"""Парсинг Atom-лент RuTracker для ежедневного отслеживания новых и обновлённых раздач."""
import xml.etree.ElementTree as ET
from curl_cffi import requests as cf_requests

from core.network import BASE_URL, PROXY_URL, fetch_url, is_valid_html

ATOM_BASE_URL = "https://feed.rutracker.cc/atom/f/{forum_id}.atom"


def fetch_atom_feed(forum_id):
    """Получает последние 50 раздач из Atom-ленты раздела RuTracker.

    Возвращает:
        list of dict: [{"topic_id": str, "raw_title": str, "url": str}, ...]
    """
    url = ATOM_BASE_URL.format(forum_id=forum_id)
    print(f"[*] Получение Atom-ленты для f={forum_id} ({url})...")
    try:
        kwargs = {"impersonate": "chrome120", "timeout": 20}
        if PROXY_URL:
            kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}
        resp = cf_requests.get(url, **kwargs)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content.decode('utf-8'))
            entries = []
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
                title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                link_elem = entry.find('{http://www.w3.org/2005/Atom}link')

                if id_elem is None or title_elem is None:
                    continue

                topic_id = id_elem.text.split('/')[-1]
                raw_title = title_elem.text or ""
                topic_url = (
                    link_elem.attrib.get('href', f"{BASE_URL}viewtopic.php?t={topic_id}")
                    if link_elem is not None
                    else f"{BASE_URL}viewtopic.php?t={topic_id}"
                )

                entries.append({
                    "topic_id": str(topic_id),
                    "raw_title": raw_title,
                    "url": topic_url
                })

            print(f"[+] Из Atom-ленты f={forum_id} получено {len(entries)} последних раздач.")
            return entries
    except Exception as e:
        print(f"[!] Ошибка получения Atom-ленты f={forum_id}: {e}")

    return []
