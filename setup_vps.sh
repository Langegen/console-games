#!/bin/bash
# ============================================================
# Универсальная установка парсера console-games на VPS
# Debian/Ubuntu, x86_64. Запуск: bash setup_vps.sh
# ============================================================
set -e

INSTALL_DIR="${INSTALL_DIR:-/root/console-games-bot}"

log()  { echo -e "\n\033[1;32m[setup]\033[0m $1"; }
warn() { echo -e "\n\033[1;33m[!]\033[0m $1"; }
ask()  { read -r -p "$1" "$2" < /dev/tty; }

# ---------- 0. Проверки ----------
if [ "$(id -u)" != "0" ]; then
    echo "Запустите от root: sudo bash setup_vps.sh"
    exit 1
fi
if [ "$(uname -m)" != "x86_64" ]; then
    echo "Нужен VPS с архитектурой x86_64 (Google Chrome не поддерживает $(uname -m))"
    exit 1
fi
export DEBIAN_FRONTEND=noninteractive

# ---------- 1. Системные пакеты ----------
log "Установка системных пакетов (git, python3, xvfb, cron)..."
apt-get update -qq -o Acquire::Retries=3 || warn "apt-get update неполный — продолжаем со старыми индексами"
apt-get install -y -qq --no-install-recommends git python3 python3-venv wget cron xvfb >/dev/null

# ---------- 2. Google Chrome ----------
if command -v google-chrome >/dev/null 2>&1; then
    log "Google Chrome уже установлен: $(google-chrome --version)"
else
    log "Установка Google Chrome..."
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    apt-get install -y -qq /tmp/chrome.deb >/dev/null
    rm -f /tmp/chrome.deb
fi

# ---------- 3. CloudflareBypassForScraping (Docker) ----------
if [ -z "${SKIP_CF_BYPASS:-}" ] && ! command -v docker >/dev/null 2>&1; then
    log "Установка Docker..."
    apt-get install -y -qq docker.io >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker >/dev/null 2>&1 || true
fi

if [ -z "${SKIP_CF_BYPASS:-}" ]; then
    log "Запуск сервиса обхода Cloudflare (cf-bypass)..."
    if docker ps -a --format '{{.Names}}' | grep -q '^cf-bypass$'; then
        docker restart cf-bypass >/dev/null
    else
        docker run -d --name cf-bypass --restart unless-stopped -p 8000:8000 \
            ghcr.io/sarperavci/cloudflarebypassforscraping:latest >/dev/null
    fi
fi

# ---------- 4. Клонирование / Настройка репозитория ----------
if [ ! -d "$INSTALL_DIR" ]; then
    log "Создание директории $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$(dirname "$0")"/* "$INSTALL_DIR/" 2>/dev/null || true
fi

cd "$INSTALL_DIR"

log "Настройка Python venv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

# ---------- 5. Настройка .env ----------
if [ ! -f ".env" ]; then
    log "Создание .env..."
    cat > .env <<'EOF'
RUTRACKER_CF_BYPASS=http://localhost:8000
EOF
    chmod 600 .env
fi

# ---------- 6. Настройка прав ----------
chmod +x run.sh || true

log "Установка console-games завершена успешно!"
echo "Для авторизации на RuTracker выполните:"
echo "  ./venv/bin/python3 login_rutracker.py ЛОГИН ПАРОЛЬ"
echo "Для запуска обновления:"
echo "  bash run.sh"
