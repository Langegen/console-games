"""Сетевой слой для взаимодействия с RuTracker через Cloudflare.

Поддерживает 3 уровня доступа:
1. Локальный сервис CloudflareBypassForScraping (mirror mode через Docker)
2. curl_cffi с TLS-отпечатком Chrome
3. Fallback на undetected_chromedriver с автоматическим решением Turnstile
"""
import copy
import os
import sys
import time
import urllib.parse
from html import unescape as html_unescape

from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests
import undetected_chromedriver as uc

from core.cf_utils import click_turnstile

BASE_URL = "https://rutracker.org/forum/"

# Куки сессии (заполняются при инициализации или из .env)
SESSION_COOKIES = {}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

UA_OVERRIDE = os.environ.get("RUTRACKER_UA", "").strip()
if UA_OVERRIDE:
    USER_AGENT = UA_OVERRIDE

ENV_COOKIES_RAW = os.environ.get("RUTRACKER_COOKIES", "").strip()
if ENV_COOKIES_RAW:
    for _item in ENV_COOKIES_RAW.split(';'):
        if '=' in _item:
            _k, _v = _item.strip().split('=', 1)
            SESSION_COOKIES[_k.strip()] = _v.strip()

CF_SESSION_INITIALIZED = False
PROXY_URL = os.environ.get("RUTRACKER_PROXY", "").strip()
CF_BYPASS_URL = os.environ.get("RUTRACKER_CF_BYPASS", "").strip().rstrip('/')
CURL_DISABLED = os.environ.get("RUTRACKER_NO_CURL", "").strip() == "1"
_curl_fail_streak = 0
GLOBAL_DRIVER = None


def init_env(env_path=None):
    """Загрузка переменных окружения из .env файла."""
    global USER_AGENT, SESSION_COOKIES, PROXY_URL, CF_BYPASS_URL, CURL_DISABLED
    if env_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        os.environ[k] = v
                        if k == 'RUTRACKER_COOKIES':
                            for item in v.split(';'):
                                if '=' in item:
                                    ck, cv = item.strip().split('=', 1)
                                    SESSION_COOKIES[ck.strip()] = cv.strip()
                        elif k == 'RUTRACKER_UA':
                            USER_AGENT = v
                        elif k == 'RUTRACKER_PROXY':
                            PROXY_URL = v
                        elif k == 'RUTRACKER_CF_BYPASS':
                            CF_BYPASS_URL = v.rstrip('/')
                        elif k == 'RUTRACKER_NO_CURL':
                            CURL_DISABLED = (v == '1')
        except Exception as e:
            print(f"[!] Ошибка загрузки .env: {e}")


def is_cf_challenge(html):
    """Признак страницы-челленджа Cloudflare."""
    if not html:
        return False
    return ('Just a moment' in html or 'cf-browser-verification' in html
            or 'Один момент' in html)


def is_valid_html(html, keywords=('post_body', 'attach_link', 'hl-tr', 'forumtable', 'viewtopic')):
    """Проверяем, что страница содержит ожидаемый контент RuTracker."""
    if not html:
        return False
    if is_cf_challenge(html):
        return False
    return any(kw in html for kw in keywords)


def _fetch_with_curl(url, wait_keywords=None, is_post=False, post_data=None):
    """Запрос через curl_cffi с текущими SESSION_COOKIES."""
    global CURL_DISABLED, _curl_fail_streak
    if CURL_DISABLED:
        return _fetch_with_chrome(url, wait_keywords, is_post, post_data)
    headers = {"User-Agent": USER_AGENT}
    if is_post:
        headers["X-Requested-With"] = "XMLHttpRequest"
    kwargs = {"impersonate": "chrome120", "timeout": 20}
    if PROXY_URL:
        kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}
    try:
        if is_post:
            resp = cf_requests.post(url, data=post_data, headers=headers, cookies=SESSION_COOKIES, **kwargs)
        else:
            resp = cf_requests.get(url, headers=headers, cookies=SESSION_COOKIES, **kwargs)

        if resp.status_code == 200:
            _curl_fail_streak = 0
            return resp.text
    except Exception as e:
        print(f"    [!] curl_cffi ошибка: {e}")

    _curl_fail_streak += 1
    if _curl_fail_streak >= 3:
        CURL_DISABLED = True
        print("[~] curl_cffi не проходит Cloudflare на этом хосте — переключаемся на Chrome.")

    print("    [!] curl_cffi не смог получить страницу, переключаемся на Chrome...")
    return _fetch_with_chrome(url, wait_keywords, is_post, post_data)


def _kill_stale_chrome():
    """Убираем осиротевшие процессы Chrome после прерванных запусков (Linux)."""
    if sys.platform.startswith('linux'):
        try:
            import subprocess
            subprocess.run(['pkill', '-f', 'remote-debugging-port'],
                           capture_output=True, timeout=5)
        except Exception:
            pass


def _safe_get(driver, url):
    """Навигация с таймаутом."""
    try:
        driver.get(url)
    except Exception:
        try:
            driver.execute_script('window.stop();')
        except Exception:
            pass


def get_chrome_version_main():
    """Detects installed Chrome major version to prevent chromedriver mismatch."""
    try:
        if sys.platform == "win32":
            import subprocess
            cmd = ['powershell', '-NoProfile', '-Command', '(Get-Item "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe").VersionInfo.ProductVersion']
            out = subprocess.check_output(cmd, encoding='utf-8', stderr=subprocess.DEVNULL).strip()
            if out and out[0].isdigit():
                return int(out.split('.')[0])
        elif sys.platform.startswith("linux"):
            import subprocess
            out = subprocess.check_output(['google-chrome', '--version'], encoding='utf-8', stderr=subprocess.DEVNULL).strip()
            for p in out.split():
                if '.' in p and p[0].isdigit():
                    return int(p.split('.')[0])
    except Exception:
        pass
    return None


def _fetch_with_chrome(url, wait_keywords=None, is_post=False, post_data=None):
    """Запрос через undetected_chromedriver (Cloudflare fallback)."""
    global SESSION_COOKIES, USER_AGENT, CF_SESSION_INITIALIZED, GLOBAL_DRIVER
    print("[*] Инициализация Chrome (Cloudflare fallback)...")
    page_html = None
    if wait_keywords is None:
        wait_keywords = ('post_body', 'attach_link', 'hl-tr', 'forumtable', 'viewtopic')
    try:
        if GLOBAL_DRIVER is None:
            _kill_stale_chrome()
            print("[*] Запуск Chrome...")
            options = uc.ChromeOptions()
            if os.environ.get("HEADLESS") == "1":
                options.add_argument('--headless')
            if UA_OVERRIDE:
                options.add_argument(f'--user-agent={UA_OVERRIDE}')
            if os.environ.get("CHROME_NO_SANDBOX") == "1" or (hasattr(os, 'geteuid') and os.geteuid() == 0):
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
            if PROXY_URL:
                options.add_argument(f'--proxy-server={PROXY_URL}')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-first-run')
            chrome_ver = get_chrome_version_main()
            GLOBAL_DRIVER = uc.Chrome(options=options, version_main=chrome_ver)
            GLOBAL_DRIVER.set_script_timeout(30)
            GLOBAL_DRIVER.set_page_load_timeout(25)
            print(f"[*] Chrome запущен (версия {chrome_ver or 'default'})")

        if is_post:
            _safe_get(GLOBAL_DRIVER, "https://rutracker.org/forum/index.php")
        else:
            _safe_get(GLOBAL_DRIVER, url)
        time.sleep(2)

        if SESSION_COOKIES:
            for k, v in SESSION_COOKIES.items():
                try:
                    GLOBAL_DRIVER.add_cookie({'name': k, 'value': v, 'domain': '.rutracker.org'})
                except Exception as e:
                    print(f"    [!] Ошибка установки куки {k}: {e}")
            if is_post:
                _safe_get(GLOBAL_DRIVER, "https://rutracker.org/forum/index.php")
            else:
                _safe_get(GLOBAL_DRIVER, url)

        for i in range(90):
            try:
                src = GLOBAL_DRIVER.page_source
                title = GLOBAL_DRIVER.title
            except Exception:
                src, title = '', ''
            if 'Just a moment' not in title and 'Один момент' not in title:
                if is_post or any(kw in src for kw in wait_keywords):
                    page_html = src
                    break
            if i % 20 == 0 and i > 0:
                print(f"    [~] Ожидание страницы... title={title!r} ({i} сек)")
            try:
                click_turnstile(GLOBAL_DRIVER)
            except Exception:
                pass
            time.sleep(1)

        if is_post:
            body_str = urllib.parse.urlencode(post_data or {})
            script = f"""
            var done = arguments[arguments.length - 1];
            fetch('{url}', {{
                method: 'POST',
                headers: {{ 
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }},
                body: '{body_str}'
            }}).then(response => response.text()).then(text => done(text)).catch(err => done(''));
            """
            print(f"    [~] Выполнение POST запроса через JS fetch к {url}")
            page_html = GLOBAL_DRIVER.execute_async_script(script)

        if not page_html:
            page_html = GLOBAL_DRIVER.page_source

        new_cookies = {c['name']: c['value'] for c in GLOBAL_DRIVER.get_cookies()}
        SESSION_COOKIES.update(new_cookies)

        try:
            real_ua = GLOBAL_DRIVER.execute_script("return navigator.userAgent;")
            if real_ua:
                USER_AGENT = real_ua
        except Exception:
            pass

        if ENV_COOKIES_RAW:
            for item in ENV_COOKIES_RAW.split(';'):
                if '=' in item:
                    kk, vv = item.strip().split('=', 1)
                    if kk.strip() != 'cf_clearance':
                        SESSION_COOKIES[kk.strip()] = vv.strip()

        CF_SESSION_INITIALIZED = True
        print(f"[+] Chrome cookies получены: {list(new_cookies.keys())}")

    except Exception as e:
        print(f"[!] Chrome ошибка: {e}")

    return page_html


def _bypass_request(url, is_post=False, post_data=None):
    """Запрос через локальный CloudflareBypassForScraping (mirror mode)."""
    if not CF_BYPASS_URL:
        return None
    try:
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path + (('?' + parsed.query) if parsed.query else '')
        mirror_url = CF_BYPASS_URL + path
        headers = {
            'User-Agent': USER_AGENT,
            'x-hostname': parsed.netloc,
        }
        if is_post:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        if SESSION_COOKIES:
            headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in SESSION_COOKIES.items())
        kwargs = {'impersonate': 'chrome120', 'timeout': 60}
        if is_post:
            resp = cf_requests.post(mirror_url, data=post_data, headers=headers, **kwargs)
        else:
            resp = cf_requests.get(mirror_url, headers=headers, **kwargs)
        if resp.status_code == 200 and resp.text:
            return resp.text
        print(f"    [!] CF-bypass статус {resp.status_code}")
    except Exception as e:
        print(f"    [!] CF-bypass ошибка: {e}")
    return None


def fetch_url(url, forum_url=False, is_post=False, post_data=None, wait_keywords=None):
    """Основная функция получения страницы.

    1. Пробуем CloudflareBypassForScraping (если настроен).
    2. Пробуем curl_cffi с cookies.
    3. При ошибке/challenge — Chrome fallback (undetected_chromedriver).
    """
    keywords = ('hl-tr', 'forumtable') if forum_url else ('post_body', 'attach_link')
    wait_kw = wait_keywords or (('hl-tr', 'forumtable') if forum_url else ('post_body', 'attach_link', 'viewtopic'))

    if CF_BYPASS_URL:
        html = _bypass_request(url, is_post=is_post, post_data=post_data)
        if html and (is_post or is_valid_html(html, keywords)):
            return html
        print("    [!] CF-bypass не вернул страницу, пробуем другие способы...")

    html = _fetch_with_curl(url, wait_keywords=wait_kw, is_post=is_post, post_data=post_data)
    if html and (is_post or is_valid_html(html, keywords)):
        return html

    if html:
        status = 'CF challenge' if is_cf_challenge(html) else 'нет нужных элементов'
        print(f"    [!] curl_cffi вернул {status}, переключаемся на Chrome...")
    else:
        print(f"    [!] curl_cffi не смог получить страницу, переключаемся на Chrome...")

    chrome_html = _fetch_with_chrome(url, wait_keywords=wait_kw, is_post=is_post, post_data=post_data)
    if chrome_html and (is_post or is_valid_html(chrome_html, keywords)):
        return chrome_html

    if not CURL_DISABLED:
        html = _fetch_with_curl(url, wait_keywords=wait_kw, is_post=is_post, post_data=post_data)
        if html and (is_post or is_valid_html(html, keywords)):
            return html

    if chrome_html and len(chrome_html) > 500:
        print(f"    [~] Возвращаем неполный Chrome ответ для {url}")
        return chrome_html

    print(f"    [!] Не удалось получить страницу: {url}")
    return None


def close_driver():
    """Завершение работы глобального экземпляра браузера Chrome."""
    global GLOBAL_DRIVER
    if GLOBAL_DRIVER is not None:
        try:
            GLOBAL_DRIVER.quit()
        except Exception:
            pass
        GLOBAL_DRIVER = None


# Инициализируем окружение при загрузке модуля
init_env()
