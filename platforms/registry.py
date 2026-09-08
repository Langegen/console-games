"""Реестр игровых платформ и сопоставление с форумами RuTracker."""
from platforms.configs import PLATFORM_CONFIGS

FORUM_TO_PLATFORMS = {
    '1352': ['psp'],
    '908': ['ps1'],
    '773': ['wiiu', 'wii', 'gamecube'],
    '129': ['nes', 'snes', 'n64', 'gba', 'gbc',
            'sega_md', 'sega_ms', 'sega_gg', 'sega_cd', 'sega_32x'],
}


def get_all_platforms():
    """Возвращает список всех ключей платформ."""
    return list(PLATFORM_CONFIGS.keys())


def get_all_forum_ids():
    """Возвращает список всех ID форумов."""
    return list(FORUM_TO_PLATFORMS.keys())


def get_platforms_for_forum(forum_id):
    """Возвращает список платформ, относящихся к форуму."""
    return FORUM_TO_PLATFORMS.get(str(forum_id), [])


def get_forum_for_platform(platform_key):
    """Возвращает ID форума для платформы."""
    cfg = PLATFORM_CONFIGS.get(platform_key)
    return cfg['forum_id'] if cfg else None


def get_platform_config(platform_key):
    """Возвращает конфигурационный словарь платформы."""
    return PLATFORM_CONFIGS.get(platform_key)
