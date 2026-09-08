"""Диагностика доступа к RuTracker (curl / Chrome / Cloudflare bypass).

Запуск:
  python test_connection.py
  (на сервере: xvfb-run -a python test_connection.py)
"""
import os
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.network import BASE_URL, init_env, PROXY_URL, CF_BYPASS_URL, USER_AGENT, SESSION_COOKIES

TEST_URL = 'https://rutracker.org/forum/index.php'


def res_info():
    print("\n=== Ресурсы машины ===")
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith(('MemTotal', 'MemAvailable', 'SwapTotal')):
                    print(' ', line.strip())
    except OSError:
        pass
    try:
        n = os.cpu_count()
        print(f'  CPU: {n} ядер')
    except OSError:
        pass


def test_curl():
    print("\n=== Проверка curl_cffi (TLS impersonation) ===")
    from curl_cffi import requests as cf
    kwargs = {"timeout": 15}
    if PROXY_URL:
        kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}

    for imp in ("chrome120", "chrome119", "safari15_5"):
        try:
            r = cf.get(TEST_URL, impersonate=imp, headers={"User-Agent": USER_AGENT}, cookies=SESSION_COOKIES, **kwargs)
            is_cf = ('Just a moment' in r.text or 'Один момент' in r.text)
            status = "CF challenge" if is_cf else f"OK ({len(r.text)} байт)"
            print(f"  {imp}: HTTP {r.status_code} — {status}")
        except Exception as e:
            print(f"  {imp}: ошибка ({e})")


def test_cf_bypass():
    print(f"\n=== Проверка CloudflareBypass (URL: {CF_BYPASS_URL or 'не задан'}) ===")
    if not CF_BYPASS_URL:
        print("  [~] RUTRACKER_CF_BYPASS не настроен в .env")
        return
    from curl_cffi import requests as cf
    try:
        mirror_url = f"{CF_BYPASS_URL}/forum/index.php"
        headers = {"User-Agent": USER_AGENT, "x-hostname": "rutracker.org"}
        r = cf.get(mirror_url, headers=headers, impersonate="chrome120", timeout=30)
        is_cf = ('Just a moment' in r.text or 'Один момент' in r.text)
        status = "CF challenge" if is_cf else f"OK ({len(r.text)} байт)"
        print(f"  Bypass статус: HTTP {r.status_code} — {status}")
    except Exception as e:
        print(f"  Ошибка CF Bypass: {e}")


def main():
    init_env()
    res_info()
    test_curl()
    test_cf_bypass()
    print("\n=== Диагностика завершена ===")


if __name__ == '__main__':
    main()
