"""Конфигурации платформ и сопоставление с разделами RuTracker."""
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PLATFORM_CONFIGS = {
    # ─── Форум 1352: Sony PSP ───
    'psp': {
        'name': 'Sony PlayStation Portable',
        'forum_id': '1352',
        'filename': os.path.join(BASE_DIR, 'psp_games.json'),
        'strip_tags_re': re.compile(r'\[(PSP|PlayStation\s*Portable)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },

    # ─── Форум 908: Sony PlayStation 1 ───
    'ps1': {
        'name': 'Sony PlayStation 1',
        'forum_id': '908',
        'filename': os.path.join(BASE_DIR, 'ps1_games.json'),
        'strip_tags_re': re.compile(r'\[(PS1|PSX|PS|PlayStation\s*1|PlayStation)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },

    # ─── Форум 773: Nintendo Wii / Wii U / GameCube ───
    'wiiu': {
        'name': 'Nintendo Wii U',
        'forum_id': '773',
        'filename': os.path.join(BASE_DIR, 'wiiu_games.json'),
        'strip_tags_re': re.compile(r'\[(Wii[\s_-]*U|WiiU)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },
    'wii': {
        'name': 'Nintendo Wii',
        'forum_id': '773',
        'filename': os.path.join(BASE_DIR, 'wii_games.json'),
        'strip_tags_re': re.compile(r'\[Wii\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },
    'gamecube': {
        'name': 'Nintendo GameCube',
        'forum_id': '773',
        'filename': os.path.join(BASE_DIR, 'gamecube_games.json'),
        'strip_tags_re': re.compile(r'\[(GameCube|Game\s*Cube|NGC|GC)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },

    # ─── Форум 129: Ретро-платформы ───
    'nes': {
        'name': 'NES / Dendy / Famicom',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'nes_games.json'),
        'strip_tags_re': re.compile(r'\[(NES|Dendy|Famicom|FC|Денди)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'snes': {
        'name': 'Super Nintendo Entertainment System',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'snes_games.json'),
        'strip_tags_re': re.compile(r'\[(SNES|SFC|Super[\s_-]*Nintendo|Super[\s_-]*Famicom)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'n64': {
        'name': 'Nintendo 64',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'n64_games.json'),
        'strip_tags_re': re.compile(r'\[(N64|Nintendo[\s_-]*64)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'gba': {
        'name': 'Game Boy Advance',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'gba_games.json'),
        'strip_tags_re': re.compile(r'\[(GBA|Game[\s_-]*Boy[\s_-]*Advance)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'gbc': {
        'name': 'Game Boy / Game Boy Color',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'gbc_games.json'),
        'strip_tags_re': re.compile(r'\[(GBC|Game[\s_-]*Boy[\s_-]*Color|GB|Game[\s_-]*Boy)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'sega_md': {
        'name': 'Sega Mega Drive / Genesis',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'sega_md_games.json'),
        'strip_tags_re': re.compile(r'\[(SMD|Sega[\s_-]*Mega[\s_-]*Drive|Mega[\s_-]*Drive|Genesis|Sega[\s_-]*Genesis|Sega)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'sega_ms': {
        'name': 'Sega Master System',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'sega_ms_games.json'),
        'strip_tags_re': re.compile(r'\[(SMS|Master[\s_-]*System|Sega[\s_-]*Master[\s_-]*System)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'sega_gg': {
        'name': 'Sega Game Gear',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'sega_gg_games.json'),
        'strip_tags_re': re.compile(r'\[(GG|Game[\s_-]*Gear|Sega[\s_-]*Game[\s_-]*Gear)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'sega_cd': {
        'name': 'Sega CD / Mega CD',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'sega_cd_games.json'),
        'strip_tags_re': re.compile(r'\[(Sega[\s_-]*CD|Mega[\s_-]*CD)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },
    'sega_32x': {
        'name': 'Sega 32X',
        'forum_id': '129',
        'filename': os.path.join(BASE_DIR, 'sega_32x_games.json'),
        'strip_tags_re': re.compile(r'\[(32X|Sega[\s_-]*32X|Mega[\s_-]*32X)\]\s*', re.IGNORECASE),
        'has_title_id': False,
    },

    # ─── Форум 357: Sony PlayStation 2 ───
    'ps2': {
        'name': 'Sony PlayStation 2',
        'forum_id': '357',
        'filename': os.path.join(BASE_DIR, 'ps2_games.json'),
        'strip_tags_re': re.compile(r'\[(PS2|PlayStation\s*2)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },

    # ─── Форум 595: Sony PlayStation Vita ───
    'psvita': {
        'name': 'Sony PlayStation Vita',
        'forum_id': '595',
        'filename': os.path.join(BASE_DIR, 'psvita_games.json'),
        'strip_tags_re': re.compile(r'\[(PSV|PS\s*Vita|PlayStation\s*Vita|PSVita)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },

    # ─── Форум 968: Sega Dreamcast ───
    'dreamcast': {
        'name': 'Sega Dreamcast',
        'forum_id': '968',
        'filename': os.path.join(BASE_DIR, 'dreamcast_games.json'),
        'strip_tags_re': re.compile(r'\[(DC|Dreamcast|Sega\s*Dreamcast)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },

    # ─── Форум 774: Nintendo 3DS / Nintendo DS ───
    '3ds': {
        'name': 'Nintendo 3DS',
        'forum_id': '774',
        'filename': os.path.join(BASE_DIR, '3ds_games.json'),
        'strip_tags_re': re.compile(r'\[(3DS|Nintendo\s*3DS|N3DS)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },
    'nds': {
        'name': 'Nintendo DS',
        'forum_id': '774',
        'filename': os.path.join(BASE_DIR, 'nds_games.json'),
        'strip_tags_re': re.compile(r'\[(NDS|DS|Nintendo\s*DS)\]\s*', re.IGNORECASE),
        'has_title_id': True,
    },
}
