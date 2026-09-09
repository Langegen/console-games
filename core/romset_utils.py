"""Утилиты для классификации и маркировки ромсетов, коллекций и антологий."""
import re
from typing import Dict, Any

ROMSET_KEYWORDS = [
    r'\bромсет\b',
    r'\bромсета\b',
    r'\bромсеты\b',
    r'\bромсетов\b',
    r'\bromset\b',
    r'\bromsets\b',
    r'\brom-set\b',
    r'\bполный\s*с[еэ]т\b',
    r'\bfull\s*set\b',
    r'\bcomplete\s*set\b',
    r'\bfullset\b',
    r'\bno-intro\b',
    r'\bgoodnes\b',
    r'\bgoodsnes\b',
    r'\bgoodgen\b',
    r'\bgoodn64\b',
    r'\bgoodgbx\b',
    r'\btosec\b',
    r'\bredump\b',
    r'\btrurip\b',
    r'\bnon-goodgen\b',
    r'\bnon-goodnes\b',
    r'\bnon\s*trurip\b',
    r'\bсборник\s*игр\b',
    r'\bколлекция\s*игр\b',
    r'\bсборник\s*ромов\b',
    r'\bколлекция\s*ромов\b',
    r'\bантология\b',
    r'\banthology\b',
    r'\bultimate\s*collection\b',
    r'\bmega\s*pack\b',
    r'\bcia\s*mega\s*pack\b',
    r'\bscene\s*releases\s*collection\b',
    r'\bundub\s*project\b',
    r'\bvirtual\s*console\s*(?:games|collection)\b',
    r'\bвсе\s*выходившие\s*игры\b',
    r'\b(?:1000\+|500\+|100\+)\s*(?:nes|snes|sega|gb|gba|injectors)\b',
    r'\b\d{2,5}\s*(?:в|in)\s*1\b',
    r'\b\d{3,5}\s*шт\b',
    r'\b\d{4}-\d{4}-mega\s*pack\b',
]

ROMSET_PATTERN = re.compile('|'.join(ROMSET_KEYWORDS), re.IGNORECASE)

NON_GAME_PATTERNS = [
    r'правила\s*раздела',
    r'навигатор\s*по\s*разделу',
    r'список\s*раздач',
    r'поиск\s*и\s*заказ',
    r'важная\s*информация',
    r'книга\s*жалоб',
    r'установка\s*чипа',
    r'инструкция',
    r'калькулятор',
    r'f\.a\.q\.',
    r'руководство',
    r'как\s*записать',
    r'как\s*подключится',
]
NON_GAME_REGEX = re.compile('|'.join(NON_GAME_PATTERNS), re.IGNORECASE)


def is_non_game_tool(title: str) -> bool:
    """Проверяет, является ли тема служебной утилитой, мануалом или правилами."""
    if not title:
        return False
    return bool(NON_GAME_REGEX.search(title))


def is_romset_title(title: str, is_sticky: bool = False) -> bool:
    """Определяет, является ли тема ромсетом, полным сетом, коллекцией или антологией."""
    if not title:
        return False
    if is_sticky and not is_non_game_tool(title):
        return True
    return bool(ROMSET_PATTERN.search(title))


def tag_game_entry(game: Dict[str, Any], is_sticky: bool = False) -> Dict[str, Any]:
    """Добавляет поля маркировки is_romset и content_type в запись игры."""
    title = game.get('title', '')
    is_rom = is_romset_title(title, is_sticky=is_sticky)
    game['is_romset'] = is_rom
    game['content_type'] = 'romset' if is_rom else 'game'
    return game
