"""Авторизация на RuTracker для получения сессионных кук (bb_session, bb_guid).

Использование:
  python login_rutracker.py ЛОГИН ПАРОЛЬ
"""
import os
import sys
import time
import urllib.parse
from core.cf_utils import click_turnstile, inject_cookies, wait_page

LOGIN_URL = 'https://rutracker.org/forum/login.php'

PROXY_URL = os.environ.get("RUTRACKER_PROXY", "").strip()
UA_OVERRIDE = os.environ.get("RUTRACKER_UA", "").strip()
CF_BYPASS_URL = os.environ.get("RUTRACKER_CF_BYPASS", "").strip().rstrip('/')


def _save_cookies_to_env(cookie_str):
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    existing_lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            existing_lines = [l for l in f if not l.startswith('RUTRACKER_COOKIES=')]

    existing_lines.append(f"RUTRACKER_COOKIES='{cookie_str}'\n")
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(existing_lines)

    try:
        os.chmod(env_file, 0o600)
    except Exception:
        pass
    print("[+] Куки успешно сохранены в .env")


def _cp1251_quote(s):
    return urllib.parse.quote(s.encode('cp1251', errors='replace'))


def login_with_curl(username, password):
    """Быстрый логин POST-запросом через curl_cffi."""
    try:
        from curl_cffi import requests as cf_requests
    except ImportError:
        return None

    body = (
        f"login_username={_cp1251_quote(username)}"
        f"&login_password={_cp1251_quote(password)}"
        f"&login={_cp1251_quote('Вход')}"
    ).encode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": UA_OVERRIDE or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://rutracker.org",
        "Referer": LOGIN_URL,
    }
    kwargs = {"impersonate": "chrome120", "timeout": 20}
    if PROXY_URL:
        kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}

    try:
        print("[*] Попытка быстрого входа через curl_cffi...")
        resp = cf_requests.post(LOGIN_URL, data=body, headers=headers, **kwargs)
        cookies = resp.cookies
        cookie_dict = {k: v for k, v in cookies.items()}
        if 'bb_session' in cookie_dict or 'bb_data' in cookie_dict:
            cookie_str = '; '.join(f"{k}={v}" for k, v in cookie_dict.items())
            print(f"[+] Быстрый логин успешен: {list(cookie_dict.keys())}")
            return cookie_str
    except Exception as e:
        print(f"[~] Быстрый вход не удался ({e}), пробуем через браузер...")
    return None


def login_with_browser(username, password):
    """Логин через undetected_chromedriver с решением Turnstile."""
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By

    print("[*] Запуск Chrome для авторизации...")
    options = uc.ChromeOptions()
    if os.environ.get("HEADLESS") == "1":
        options.add_argument('--headless')
    if UA_OVERRIDE:
        options.add_argument(f'--user-agent={UA_OVERRIDE}')
    if PROXY_URL:
        options.add_argument(f'--proxy-server={PROXY_URL}')
    if os.environ.get("CHROME_NO_SANDBOX") == "1" or (hasattr(os, 'geteuid') and os.geteuid() == 0):
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get(LOGIN_URL)
        time.sleep(3)

        wait_page(driver, timeout=90)

        user_input = driver.find_element(By.NAME, 'login_username')
        pass_input = driver.find_element(By.NAME, 'login_password')
        user_input.clear()
        user_input.send_keys(username)
        pass_input.clear()
        pass_input.send_keys(password)

        submit = driver.find_element(By.NAME, 'login')
        submit.click()
        time.sleep(5)

        wait_page(driver, timeout=60)

        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        if 'bb_session' in cookies or 'bb_data' in cookies:
            cookie_str = '; '.join(f"{k}={v}" for k, v in cookies.items())
            print(f"[+] Авторизация через браузер успешна: {list(cookies.keys())}")
            return cookie_str
        else:
            print(f"[!] Сессионные куки не найдены среди {list(cookies.keys())}")
    except Exception as e:
        print(f"[!] Ошибка авторизации через браузер: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    return None


def main():
    if len(sys.argv) < 3:
        print("Использование: python login_rutracker.py <логин> <пароль>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    cookie_str = login_with_curl(username, password)
    if not cookie_str:
        cookie_str = login_with_browser(username, password)

    if cookie_str:
        _save_cookies_to_env(cookie_str)
    else:
        print("[!] Не удалось получить куки. Проверьте правильность логина и пароля.")
        sys.exit(1)


if __name__ == '__main__':
    main()
