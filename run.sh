#!/bin/bash
# Ежедневное обновление игровых баз console-games: pull -> парсер -> git push
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd "$(dirname "$0")"

# Защита от параллельного запуска нескольких копий
LOCK_FILE="/tmp/console-games.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date)] Процесс console-games уже выполняется (lockfile: $LOCK_FILE). Выход."
    exit 0
fi

# Загружаем переменные окружения из .env, если есть
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

# Проверяем и включаем sparse-checkout, чтобы обложки (covers/) не занимали диск VPS
if [ -d .git ] && ! git sparse-checkout list >/dev/null 2>&1; then
    echo "[$(date)] Настройка sparse-checkout (исключение covers/ с диска VPS)..."
    git sparse-checkout init --cone 2>/dev/null || true
    git sparse-checkout set core data platforms scripts tests 2>/dev/null || true
fi

echo "[$(date)] Обновление кода из репозитория..."
git pull --rebase origin main || true

echo "[$(date)] Запуск парсера консольных игр..."
PYTHON_EXEC="./venv/bin/python3"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi

if command -v xvfb-run >/dev/null 2>&1; then
    xvfb-run -a $PYTHON_EXEC scraper.py "$@"
else
    $PYTHON_EXEC scraper.py "$@"
fi

echo "[$(date)] Проверка изменений..."
git add data/*_games.json changes.txt scraper.py run.sh .gitignore 2>/dev/null || true

if git diff --staged --quiet; then
    echo "[$(date)] Изменений нет — коммит не требуется."
else
    echo "[$(date)] Выгрузка изменений на GitHub..."
    git commit -m "Auto-update console-games: $(date +'%Y-%m-%d %H:%M:%S')"
    git pull --rebase origin main || true
    git push origin main
    echo "[$(date)] Успешно завершено!"
fi

# Ротация лога: оставляем последние 3000 строк
LOG_FILE="$(pwd)/cron_log.txt"
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt 4000 ]; then
    tail -n 3000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi
