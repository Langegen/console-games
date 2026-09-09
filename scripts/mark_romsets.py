"""Скрипт пакетной маркировки ромсетов во всех 20 базах данных."""
import json
import sys
from pathlib import Path

# Установка UTF-8 для вывода
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.romset_utils import tag_game_entry

DATA_DIR = ROOT_DIR / "data"


def mark_all_databases():
    """Проставляет is_romset: bool и content_type: 'romset'|'game' во всех базах."""
    print("=" * 65)
    print("Маркировка ромсетов и коллекций во всех базах данных")
    print("=" * 65)

    total_games = 0
    total_romsets = 0

    header = f"{'Платформа':<14} | {'Всего игр':>10} | {'Ромсетов':>10} | {'Обычных игр':>12} | {'% Ромсетов':>10}"
    print(header)
    print("-" * 65)

    for json_file in sorted(DATA_DIR.glob("*_games.json")):
        plat = json_file.stem.replace("_games", "")
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                games = json.load(f)
        except Exception as e:
            print(f"[!] Ошибка чтения {json_file}: {e}")
            continue

        plat_romsets = 0
        updated_games = []
        for g in games:
            tagged = tag_game_entry(g)
            if tagged.get("is_romset"):
                plat_romsets += 1
            updated_games.append(tagged)

        # Сохраняем обновленный JSON
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(updated_games, f, ensure_ascii=False, indent=2)

        n = len(updated_games)
        single_games = n - plat_romsets
        pct = (plat_romsets / n * 100) if n else 0
        line = f"{plat:<14} | {n:>10} | {plat_romsets:>10} | {single_games:>12} | {pct:>9.1f}%"
        print(line)

        total_games += n
        total_romsets += plat_romsets

    print("=" * 65)
    total_single = total_games - total_romsets
    tot_pct = (total_romsets / total_games * 100) if total_games else 0
    summary = f"{'ИТОГО':<14} | {total_games:>10} | {total_romsets:>10} | {total_single:>12} | {tot_pct:>9.1f}%"
    print(summary)
    print("=" * 65)


if __name__ == "__main__":
    mark_all_databases()
