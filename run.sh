#!/bin/bash
# Ежедневное обновление игровых баз console-games: pull -> парсер -> git push
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd "$(dirname "$0")"

# Загружаем переменные окружения из .env, если есть
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
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
git add data/*_games.json changes.txt scraper.py .gitignore 2>/dev/null || true

if git diff --staged --quiet; then
    echo "[$(date)] Изменений нет — коммит не требуется."
else
    echo "[$(date)] Выгрузка изменений на GitHub..."
    git commit -m "Auto-update console-games: $(date +'%Y-%m-%d %H:%M:%S')"
    git pull --rebase origin main || true
    git push origin main
    echo "[$(date)] Успешно завершено!"
fi
