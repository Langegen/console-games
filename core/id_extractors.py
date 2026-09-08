"""Извлечение идентификаторов игр (Title ID, Serial, Game ID) для разных консолей.

Поддерживаемые форматы:
- PSP: ULES-xxxxx, ULUS-xxxxx, UCES-xxxxx, UCUS-xxxxx, NPJH-xxxxx, NPEH-xxxxx, NPUZ-xxxxx и др.
- PS1: SLUS-xxxxx, SLES-xxxxx, SCUS-xxxxx, SCES-xxxxx, SLPS-xxxxx, SLPM-xxxxx, SLED-xxxxx и др.
- Wii: 6-значный ID диска (напр. RMCE01, SB4E01)
- GameCube: 6-значный ID диска (напр. GMSE01, GALP01)
- Wii U: 16-значный Title ID (начинается с 00050000) или Product Code (WUP-P-xxxx)
- Ретро (NES, SNES, Sega, N64, GBA, GBC): None
"""
import re
from core.network import fetch_url, BASE_URL


# Регулярные выражения для кодов дисков Sony
PSP_SERIAL_RE = re.compile(r'(?<![A-Z0-9])(UL[A-Z]{2}|UC[A-Z]{2}|NP[A-Z]{2})[-_ ]?([0-9]{5})(?![0-9a-zA-Z])', re.IGNORECASE)
PS1_SERIAL_RE = re.compile(r'(?<![A-Z0-9])(SL[A-Z]{2}|SC[A-Z]{2}|P[AB]PX)[-_ ]?([0-9]{3}[._]?[0-9]{2}|[0-9]{5})(?![0-9a-zA-Z])', re.IGNORECASE)
PS2_SERIAL_RE = re.compile(r'(?<![A-Z0-9])(SL[A-Z]{2}|SC[A-Z]{2}|P[AB]PX)[-_ ]?([0-9]{3}[._]?[0-9]{2}|[0-9]{5})(?![0-9a-zA-Z])', re.IGNORECASE)
VITA_SERIAL_RE = re.compile(r'(?<![A-Z0-9])(PCS[A-Z0-9])[-_ ]?([0-9]{5})(?![0-9a-zA-Z])', re.IGNORECASE)

# Регулярные выражения для Sega Dreamcast
DC_ID_RE = re.compile(r'(?<![A-Z0-9])((?:T|MK|HDR)[-_ ]?[0-9]{4,5}[A-Z0-9]?)(?![0-9a-zA-Z])', re.IGNORECASE)

# Регулярные выражения для Nintendo
WII_ID_RE = re.compile(r'\b([RS][A-Z0-9]{2}[EPJKW][0-9A-Z]{2})\b', re.IGNORECASE)
GAMECUBE_ID_RE = re.compile(r'\b([GDP][A-Z0-9]{2}[EPJKW][0-9A-Z]{2})\b', re.IGNORECASE)
WIIU_TITLE_ID_RE = re.compile(r'\b(0005000[0-9A-Fa-f]{9})\b', re.IGNORECASE)
WIIU_CODE_RE = re.compile(r'\b(WUP-[A-Z]-[A-Z0-9]{4})\b', re.IGNORECASE)
N3DS_TITLE_ID_RE = re.compile(r'\b(0004000[0-9A-Fa-f]{9})\b', re.IGNORECASE)
N3DS_CODE_RE = re.compile(r'\b(CTR-[A-Z]-[A-Z0-9]{4})\b', re.IGNORECASE)
NDS_CODE_RE = re.compile(r'\b((?:NTR|TWL)(?:-[A-Z])?-[A-Z0-9]{4})\b', re.IGNORECASE)


def extract_psp_id(text):
    """Извлекает код диска PSP (например, ULES-00123)."""
    if not text:
        return None
    m = PSP_SERIAL_RE.search(text)
    if m:
        prefix = m.group(1).upper()
        number = m.group(2)
        return f"{prefix}-{number}"
    return None


def extract_ps1_id(text):
    """Извлекает код диска PS1 (например, SLUS-00123, SLES-00123)."""
    if not text:
        return None
    m = PS1_SERIAL_RE.search(text)
    if m:
        prefix = m.group(1).upper()
        raw_num = m.group(2).replace('.', '').replace('_', '')
        return f"{prefix}-{raw_num}"
    return None


def extract_wii_id(text):
    """Извлекает 6-значный Game ID для Nintendo Wii (например, RMCE01)."""
    if not text:
        return None
    # Сначала ищем контекстные совпадения (Код диска / Game ID / ID)
    ctx_match = re.search(r'(?:код(?:\s*диска|\s*игры)?|id(?:\s*диска|\s*игры)?|title\s*id|game\s*id)\s*[:=-]\s*([A-Z0-9]{4,6})\b', text, re.IGNORECASE)
    if ctx_match:
        val = ctx_match.group(1).upper()
        if len(val) == 6:
            return val
    m = WII_ID_RE.search(text)
    if m:
        return m.group(1).upper()
    return None


def extract_gamecube_id(text):
    """Извлекает 6-значный Game ID для GameCube (например, GMSE01)."""
    if not text:
        return None
    ctx_match = re.search(r'(?:код(?:\s*диска|\s*игры)?|id(?:\s*диска|\s*игры)?|title\s*id|game\s*id)\s*[:=-]\s*([A-Z0-9]{4,6})\b', text, re.IGNORECASE)
    if ctx_match:
        val = ctx_match.group(1).upper()
        if len(val) == 6:
            return val
    m = GAMECUBE_ID_RE.search(text)
    if m:
        return m.group(1).upper()
    return None


def extract_wiiu_id(text):
    """Извлекает Title ID (16 hex) или Product Code (WUP-P-xxxx) для Wii U."""
    if not text:
        return None
    m_tid = WIIU_TITLE_ID_RE.search(text)
    if m_tid:
        val = m_tid.group(1).upper()
        # Нормализуем к base game (00050000...)
        if val.startswith('0005000E') or val.startswith('0005000C'):
            val = '00050000' + val[8:]
        return val
    m_code = WIIU_CODE_RE.search(text)
    if m_code:
        return m_code.group(1).upper()
    return None


def extract_ps2_id(text):
    """Извлекает код диска PS2 (например, SLES-50361, SLUS-20002)."""
    if not text:
        return None
    m = PS2_SERIAL_RE.search(text)
    if m:
        prefix = m.group(1).upper()
        raw_num = m.group(2).replace('.', '').replace('_', '')
        return f"{prefix}-{raw_num}"
    return None


def extract_psvita_id(text):
    """Извлекает код игры PS Vita (например, PCSB-00245, PCSE-00120)."""
    if not text:
        return None
    m = VITA_SERIAL_RE.search(text)
    if m:
        prefix = m.group(1).upper()
        number = m.group(2)
        return f"{prefix}-{number}"
    return None


def extract_dreamcast_id(text):
    """Извлекает код диска Sega Dreamcast (например, T-13002N, MK-51000)."""
    if not text:
        return None
    ctx_match = re.search(r'(?:код(?:\s*диска|\s*игры)?|product\s*id|game\s*id)\s*[:=-]\s*([A-Z0-9-]{4,12})\b', text, re.IGNORECASE)
    if ctx_match:
        val = ctx_match.group(1).strip().upper()
        if re.match(r'^(?:T|MK|HDR)', val):
            return val
    m = DC_ID_RE.search(text)
    if m:
        val = m.group(1).upper()
        m_norm = re.match(r'^(T|MK|HDR)[-_ ]?([0-9]{4,5}[A-Z0-9]?)$', val)
        if m_norm:
            return f"{m_norm.group(1)}-{m_norm.group(2)}"
        return val
    return None


def extract_3ds_id(text):
    """Извлекает 16-значный Title ID (напр. 00040000000EC400) или Product Code (CTR-P-xxxx) для 3DS."""
    if not text:
        return None
    m_tid = N3DS_TITLE_ID_RE.search(text)
    if m_tid:
        val = m_tid.group(1).upper()
        # Нормализуем DLC/Update к base game (00040000...)
        if val.startswith('0004000E') or val.startswith('0004000C'):
            val = '00040000' + val[8:]
        return val
    m_code = N3DS_CODE_RE.search(text)
    if m_code:
        return m_code.group(1).upper()
    ctx_match = re.search(r'(?:title\s*id|код(?:\s*игры)?)\s*[:=-]\s*([0-9A-Fa-f]{16}|CTR-[A-Z]-[A-Z0-9]{4})\b', text, re.IGNORECASE)
    if ctx_match:
        return ctx_match.group(1).upper()
    return None


def extract_nds_id(text):
    """Извлекает код игры Nintendo DS (например, NTR-ADAE, NTR-P-AMHE, TWL-P-IRBO)."""
    if not text:
        return None
    m_code = NDS_CODE_RE.search(text)
    if m_code:
        return m_code.group(1).upper()
    ctx_match = re.search(r'(?:game\s*id|код(?:\s*игры)?|game\s*code|serial)\s*[:=-]\s*([A-Z0-9]{4})\b', text, re.IGNORECASE)
    if ctx_match:
        return ctx_match.group(1).upper()
    return None


def extract_platform_id(platform_key, text):
    """Универсальная точка извлечения ID игры в зависимости от платформы."""
    if not text:
        return None
    if platform_key == 'psp':
        return extract_psp_id(text)
    elif platform_key == 'ps1':
        return extract_ps1_id(text)
    elif platform_key == 'ps2':
        return extract_ps2_id(text)
    elif platform_key == 'psvita':
        return extract_psvita_id(text)
    elif platform_key == 'dreamcast':
        return extract_dreamcast_id(text)
    elif platform_key == 'wii':
        return extract_wii_id(text)
    elif platform_key == 'gamecube':
        return extract_gamecube_id(text)
    elif platform_key == 'wiiu':
        return extract_wiiu_id(text)
    elif platform_key == '3ds':
        return extract_3ds_id(text)
    elif platform_key == 'nds':
        return extract_nds_id(text)
    # Для всех ретро-систем (NES, SNES, Sega, N64, GBA, GBC) ID диска нет
    return None


def fetch_filelist_id(topic_id, platform_key):
    """Запрос viewtorrent.php (список файлов раздачи) для поиска ID игры.

    Часто авторы не пишут код в тексте, но он содержится в имени файла/папки
    (например, ULES-00123.iso или RMCE01.wbfs).
    """
    if platform_key in ('nes', 'snes', 'n64', 'gba', 'gbc',
                        'sega_md', 'sega_ms', 'sega_gg', 'sega_cd', 'sega_32x'):
        return None

    try:
        torrent_html = fetch_url(f"{BASE_URL}viewtorrent.php", is_post=True,
                                 post_data={"t": topic_id},
                                 wait_keywords=('dir', 'file', 'ul', 'li', 'torrent'))
        if torrent_html:
            return extract_platform_id(platform_key, torrent_html)
    except Exception:
        pass
    return None
