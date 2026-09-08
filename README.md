# console-games

Мультиплатформенный парсер раздач консольных и ретро-игр с трекера RuTracker. Автоматически собирает базы данных игр в формате JSON (названия, размеры, magnet-ссылки, обложки, скриншоты, описания, коды дисков и Title ID), ежедневно отслеживает новые и обновлённые раздачи через Atom-ленты и выгружает изменения на GitHub.

Создан на основе проверенной архитектуры `switch-games` с модульным расширением для поддержки смешанных разделов и различных поколений игровых систем.

---

## Поддерживаемые игровые платформы и разделы

| Консоль / Система | Файл базы данных | Раздел RuTracker | Особенности и Title ID / Serial |
|---|---|---|---|
| **Sony PS2** | `data/ps2_games.json` | [f=357](https://rutracker.org/forum/viewforum.php?f=357) | Код диска: `SLES-xxxxx`, `SLUS-xxxxx`, `SCES-xxxxx`, `SLPM-xxxxx` |
| **Sony PS1 (PSX)** | `data/ps1_games.json` | [f=908](https://rutracker.org/forum/viewforum.php?f=908) | Код диска: `SLUS-xxxxx`, `SLES-xxxxx`, `SCES-xxxxx` |
| **Sony PSP** | `data/psp_games.json` | [f=1352](https://rutracker.org/forum/viewforum.php?f=1352) | Код диска: `ULES-xxxxx`, `ULUS-xxxxx`, `NPJH-xxxxx` |
| **Sony PS Vita** | `data/psvita_games.json` | [f=595](https://rutracker.org/forum/viewforum.php?f=595) | Код игры: `PCSB-xxxxx`, `PCSE-xxxxx`, `PCSA-xxxxx`, `PCSG-xxxxx` |
| **Sega Dreamcast** | `data/dreamcast_games.json` | [f=968](https://rutracker.org/forum/viewforum.php?f=968) | Код диска: `T-xxxxx`, `MK-xxxxx`, `HDR-xxxxx` |
| **Nintendo 3DS** | `data/3ds_games.json` | [f=774](https://rutracker.org/forum/viewforum.php?f=774) | 16-значный Title ID (`00040000...`) или Product Code `CTR-P-xxxx` |
| **Nintendo DS (NDS)** | `data/nds_games.json` | [f=774](https://rutracker.org/forum/viewforum.php?f=774) | Код картриджа: `NTR-xxxx`, `NTR-P-xxxx`, `TWL-P-xxxx` |
| **Nintendo Wii U** | `data/wiiu_games.json` | [f=773](https://rutracker.org/forum/viewforum.php?f=773) | Title ID: `00050000...` или код `WUP-P-xxxx` |
| **Nintendo Wii** | `data/wii_games.json` | [f=773](https://rutracker.org/forum/viewforum.php?f=773) | 6-значный ID диска: `RMCE01`, `SB4E01` |
| **Nintendo GameCube** | `data/gamecube_games.json` | [f=773](https://rutracker.org/forum/viewforum.php?f=773) | 6-значный ID диска: `GMSE01`, `GALP01` |
| **NES / Dendy** | `data/nes_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Ромсеты (No-Intro, GoodNES) и отдельные игры |
| **Super Nintendo (SNES)** | `data/snes_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Ромсеты и отдельные образы SNES/SFC |
| **Nintendo 64 (N64)** | `data/n64_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Образы картриджей N64 |
| **Game Boy Advance (GBA)** | `data/gba_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Коллекции и одиночные игры GBA |
| **Game Boy & GBC** | `data/gbc_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Классический Game Boy (GB/DMG) + Game Boy Color |
| **Sega Mega Drive / Genesis** | `data/sega_md_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | 16-битные SMD / Genesis ромсеты и хаки |
| **Sega Master System** | `data/sega_ms_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | 8-битная домашняя консоль SMS |
| **Sega Game Gear** | `data/sega_gg_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Портативная приставка Game Gear |
| **Sega CD / Mega CD** | `data/sega_cd_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Дисковые образы Sega CD |
| **Sega 32X** | `data/sega_32x_games.json` | [f=129](https://rutracker.org/forum/viewforum.php?f=129) | Расширение Sega 32X |

> [!NOTE]
> В смешанных разделах `f=774`, `f=773` и `f=129` парсинг осуществляется **за один проход**: каждая тема анализируется классификатором и маршрутизируется в соответствующий JSON-файл в папке `data/`. Мультиплатформенные сборники (например, `[NES, SNES, Sega]` или `[3DS / DS]`) автоматически включаются во все подходящие базы.

---

## Архитектура проекта

```
console-games/
├── data/                    # Базы данных JSON (20 платформ, 8 200+ игр)
│   ├── ps2_games.json
│   ├── ps1_games.json
│   ├── psp_games.json
│   ├── psvita_games.json
│   ├── dreamcast_games.json
│   ├── 3ds_games.json
│   ├── nds_games.json
│   └── ...
├── core/                    # Ядро парсера и сетевой слой
│   ├── network.py           # Запросы, Cloudflare bypass, fallback на Chrome, cookies
│   ├── cf_utils.py          # Автоматический клик по чекбоксу Cloudflare Turnstile
│   ├── forum.py             # Парсинг страниц форума, динамический пропуск закреплённых тем
│   ├── atom.py              # Универсальное чтение Atom-лент разделов RuTracker
│   ├── topic_parser.py      # Извлечение magnet, BTIH, описания, обложки, скриншотов
│   ├── id_extractors.py     # Поиск серийных номеров (PS2, PS1, PSP, Vita, 3DS, DS, Wii, GC)
│   └── storage.py           # Атомарная запись JSON, дообогащение, sweep магнетов, changes.txt
├── platforms/               # Конфигурации и классификаторы консолей
│   ├── configs.py           # Конфигурации всех 20 платформ (пути data/, теги очистки)
│   ├── classifiers.py       # Классификаторы тем для f=774, f=773 и f=129
│   └── registry.py          # Реестр платформ и маппинг на форумы
├── scripts/                 # Вспомогательные скрипты
│   └── test_connection.py   # Диагностика сети, Cloudflare и TLS
├── tests/                   # Набор модульных тестов (unittest)
│   ├── test_classifiers.py
│   ├── test_id_extractors.py
│   └── test_parser.py
├── .env.example             # Шаблон конфигурации окружения
├── changes.txt              # Лог последних изменений баз
├── scraper.py               # Главный CLI-парсер
├── login_rutracker.py       # Авторизация на RuTracker (curl / Chrome)
├── setup_vps.sh             # Интерактивный установщик для VPS
├── run.sh                   # Скрипт для cron: pull -> парсер -> git commit -> git push
├── requirements.txt         # Зависимости Python
└── README.md
```

---

## Быстрый старт

### Требования
- Python 3.10+
- Google Chrome (для первичного решения Cloudflare)
- Зависимости из `requirements.txt`

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Настройка авторизации (.env)
Куки RuTracker требуются для доступа к магнет-ссылкам и спискам файлов раздач:
```bash
python login_rutracker.py ВАШ_ЛОГИН ВАШ_ПАРОЛЬ
```
Скрипт автоматически пройдёт авторизацию и запишет сессионные куки в файл `.env`.

---

## Использование `scraper.py`

### 1. Ежедневное обновление (Atom-ленты)
Проверяет свежие раздачи по всем целевым форумам, классифицирует их по консолям, обновляет JSON-файлы и пишет лог в `changes.txt`:
```bash
python scraper.py
```

### 2. Запуск для конкретной консоли
```bash
python scraper.py --platform psp
python scraper.py --platform ps1
python scraper.py --platform wiiu
python scraper.py --platform nes
```

### 3. Запуск для конкретного форума
```bash
python scraper.py --forum 773      # Проверит ленту Wii, Wii U и GameCube
python scraper.py --forum 129      # Проверит ленту ретро-платформ
```

### 4. Полный сбор раздела (Full Scrape)
Если JSON-файл отсутствует, полный сбор запустится автоматически. Для принудительного повторного сбора:
```bash
python scraper.py --full --platform psp
python scraper.py --full --forum 773 --max-pages 5   # Пробный сбор 5 страниц
```

---

## Формат записи в базе (`*_games.json`)

Формат полностью совместим с форматом `switch_games.json`:

```json
{
  "title": "Silent Hill [RUS]",
  "size": "480.2 MB",
  "magnet": "magnet:?xt=urn:btih:...",
  "topic_id": "1234567",
  "url": "https://rutracker.org/forum/viewtopic.php?t=1234567",
  "year": "1999",
  "genre": "Survival Horror, Action",
  "developer": "Team Silent",
  "publisher": "Konami",
  "image_format": "BIN/CUE",
  "interface_lang": "Русский",
  "voice_lang": "Английский",
  "performance": "Да",
  "multiplayer": "нет",
  "cover": "https://...",
  "screenshots": [
    "https://...",
    "https://..."
  ],
  "description": "Первая часть культовой серии...",
  "title_id": "SLES-01514"
}
```

---

## Развёртывание на VPS

Скрипт `setup_vps.sh` автоматизирует установку на Debian/Ubuntu x86_64:
- Устанавливает Chrome, xvfb, Docker
- Разворачивает контейнер `cf-bypass` (порт 8000) для прозрачного обхода Cloudflare
- Настраивает виртуальное окружение и cron

```bash
sudo bash setup_vps.sh
```
