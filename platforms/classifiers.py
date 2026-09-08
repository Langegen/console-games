"""Классификаторы тем для смешанных разделов RuTracker: f=773 и f=129."""
import re

# ─── ФОРУМ 773: Wii U / Wii / GameCube ───
RE_WIIU_TITLE = re.compile(r'\[(Wii[\s_-]*U|WiiU)\]|\bWii[\s_-]*U\b|\bWiiU\b', re.IGNORECASE)
RE_GC_TITLE = re.compile(r'\[(GameCube|Game\s*Cube|NGC|GC)\]|\bGameCube\b|\bGame\s*Cube\b|\bNGC\b', re.IGNORECASE)
RE_WII_TITLE = re.compile(r'\[Wii\]|(?<!Wii\s)(?<!Wii-)(?<!Wii_)\bWii\b(?!\s*U)(?!-U)(?!_U)', re.IGNORECASE)


def classify_topic_773(raw_title, text_content=""):
    """Классифицирует раздачу из раздела f=773.

    Возвращает список платформ: ['wiiu'], ['wii'], ['gamecube'].
    """
    matched = []
    combined = f"{raw_title} {text_content[:200]}"

    is_wiiu = bool(RE_WIIU_TITLE.search(combined))
    is_gc = bool(RE_GC_TITLE.search(combined))

    # Wii: проверяем наличие тега Wii, исключая Wii U
    has_wii_tag = bool(re.search(r'\[Wii\]', combined, re.IGNORECASE))
    has_wii_word = bool(re.search(r'\bNintendo\s*Wii\b', combined, re.IGNORECASE)) or (
        bool(re.search(r'\bWii\b', combined, re.IGNORECASE)) and not is_wiiu
    )
    is_wii = has_wii_tag or has_wii_word

    if is_wiiu:
        matched.append('wiiu')
    if is_gc:
        matched.append('gamecube')
    if is_wii and not is_wiiu:
        matched.append('wii')

    return matched


# ─── ФОРУМ 129: Ретро (NES, SNES, Sega, N64, GBA, GBC) ───

RE_NES = re.compile(r'\[(?!S)(?:[^\]]*\b)?(NES|Dendy|Famicom|FC|Денди)\b|(?<!S)\b(NES|Dendy|Famicom|FC|Денди)\b', re.IGNORECASE)
RE_SNES = re.compile(r'\[(?:[^\]]*\b)?(SNES|SFC|Super[\s_-]*Nintendo|Super[\s_-]*Famicom)\b|\b(SNES|SFC|Super[\s_-]*Nintendo|Super[\s_-]*Famicom)\b', re.IGNORECASE)
RE_N64 = re.compile(r'\[(?:[^\]]*\b)?(N64|Nintendo[\s_-]*64)\b|\b(N64|Nintendo[\s_-]*64)\b', re.IGNORECASE)
RE_GBA = re.compile(r'\[(?:[^\]]*\b)?(GBA|Game[\s_-]*Boy[\s_-]*Advance)\b|\b(GBA|Game[\s_-]*Boy[\s_-]*Advance)\b', re.IGNORECASE)
# GBC объединяет GB и GBC, исключая GBA и единицу измерения гигабайт (GB)
RE_GBC = re.compile(
    r'\[(?:[^\]]*\b)?(GBC|Game[\s_-]*Boy[\s_-]*Color|Game[\s_-]*Boy|GB)\b|'
    r'\b(GBC|Game[\s_-]*Boy[\s_-]*Color|Game[\s_-]*Boy)\b|'
    r'(?<!\d\s)(?<!\d)(?<!\d\.)\bNintendo\s+GB\b|'
    r'\[GB\]',
    re.IGNORECASE
)

# Sega системы
RE_SEGA_32X = re.compile(r'\[(?:[^\]]*\b)?(32X|Sega[\s_-]*32X)\b|\b(32X|Sega[\s_-]*32X)\b', re.IGNORECASE)
RE_SEGA_CD = re.compile(r'\[(?:[^\]]*\b)?(Sega[\s_-]*CD|Mega[\s_-]*CD)\b|\b(Sega[\s_-]*CD|Mega[\s_-]*CD)\b', re.IGNORECASE)
RE_SEGA_GG = re.compile(r'\[(?:[^\]]*\b)?(Game[\s_-]*Gear|Sega[\s_-]*Game[\s_-]*Gear)\b|\b(Game[\s_-]*Gear|Sega[\s_-]*Game[\s_-]*Gear)\b', re.IGNORECASE)
RE_SEGA_MS = re.compile(r'\[(?:[^\]]*\b)?(Master[\s_-]*System|Sega[\s_-]*Master[\s_-]*System|SMS)\b|\b(Master[\s_-]*System|Sega[\s_-]*Master[\s_-]*System|SMS)\b', re.IGNORECASE)
RE_SEGA_MD = re.compile(r'\[(?:[^\]]*\b)?(SMD|Sega[\s_-]*Mega[\s_-]*Drive|Mega[\s_-]*Drive|Genesis|Sega[\s_-]*Genesis|Sega)\b|\b(SMD|Sega[\s_-]*Mega[\s_-]*Drive|Mega[\s_-]*Drive|Genesis|Sega[\s_-]*Genesis|Сега)\b', re.IGNORECASE)


def classify_topic_129(raw_title, text_content=""):
    """Классифицирует раздачу из раздела f=129.

    Возвращает список платформ:
    ['nes', 'snes', 'n64', 'gba', 'gbc', 'sega_md', 'sega_ms', 'sega_gg', 'sega_cd', 'sega_32x']
    Поддерживает мульти-матчинг: сборники дублируются во все указанные платформы.
    """
    matched = []
    combined = f"{raw_title} {text_content[:300]}"

    # Удаляем единицы измерения объёма данных (GB, MB, TB и т.д.), чтобы "GB" не путалось с Game Boy
    combined = re.sub(r'\b[0-9.,]+\s*(?:GB|MB|KB|TB|ГБ|МБ|КБ|ТБ)\b', '', combined, flags=re.IGNORECASE)
    combined = re.sub(r'\[\s*[0-9.,]+\s*(?:GB|MB|KB|TB|ГБ|МБ|КБ|ТБ)\s*\]', '', combined, flags=re.IGNORECASE)

    # 1. NES / Dendy (проверяем, чтобы это не было SNES)
    # Удаляем SNES из временной строки перед проверкой NES
    temp_no_snes = re.sub(r'SNES|Super[\s_-]*Nintendo', '', combined, flags=re.IGNORECASE)
    if RE_NES.search(temp_no_snes):
        matched.append('nes')

    # 2. SNES
    if RE_SNES.search(combined):
        matched.append('snes')

    # 3. N64
    if RE_N64.search(combined):
        matched.append('n64')

    # 4. GBA
    if RE_GBA.search(combined):
        matched.append('gba')

    # 5. GBC / GB (Game Boy / Game Boy Color, исключая только GBA)
    temp_no_gba = re.sub(r'GBA|Game[\s_-]*Boy[\s_-]*Advance', '', combined, flags=re.IGNORECASE)
    if RE_GBC.search(temp_no_gba):
        matched.append('gbc')

    # 6. Sega платформы
    sega_matched = False
    if RE_SEGA_32X.search(combined):
        matched.append('sega_32x')
        sega_matched = True

    if RE_SEGA_CD.search(combined):
        matched.append('sega_cd')
        sega_matched = True

    if RE_SEGA_GG.search(combined):
        matched.append('sega_gg')
        sega_matched = True

    if RE_SEGA_MS.search(combined):
        matched.append('sega_ms')
        sega_matched = True

    # Если указан SMD / Genesis / Mega Drive или общее "Sega" (и нет специфичных 32X/CD/GG/MS)
    if RE_SEGA_MD.search(combined):
        if not sega_matched or re.search(r'Mega[\s_-]*Drive|Genesis|SMD', combined, re.IGNORECASE):
            matched.append('sega_md')

    return matched


# ─── ФОРУМ 774: Nintendo 3DS / Nintendo DS ───

RE_3DS = re.compile(r'\[(?:[^\]]*\b)?(3DS|Nintendo\s*3DS|N3DS)\b|\b(3DS|Nintendo\s*3DS|N3DS)\b|\bCTR-[A-Z]', re.IGNORECASE)
RE_NDS = re.compile(r'\[(?:[^\]]*\b)?(NDS|Nintendo\s*DS|DSiWare)\b|\b(NDS|Nintendo\s*DS|DSiWare)\b|\[DS\]|(?<!3)(?<!3D)\bDS\b|\b(?:NTR|TWL)-[A-Z0-9]', re.IGNORECASE)


def classify_topic_774(raw_title, text_content=""):
    """Классифицирует раздачу из раздела f=774 (3DS / DS).

    Возвращает список платформ: ['3ds'], ['nds'], или ['3ds', 'nds'].
    """
    matched = []
    combined = f"{raw_title} {text_content[:300]}"

    is_3ds = bool(RE_3DS.search(combined))

    # Для проверки NDS удаляем упоминания 3DS, чтобы не было ложного срабатывания на буквосочетание DS
    temp_no_3ds = re.sub(r'3DS|Nintendo[\s_-]*3DS|N3DS', '', combined, flags=re.IGNORECASE)
    is_nds = bool(RE_NDS.search(temp_no_3ds))

    if is_3ds:
        matched.append('3ds')
    if is_nds:
        matched.append('nds')

    # Если явных тегов не найдено, проверяем расширения файлов
    if not matched:
        if re.search(r'\.(?:cia|3ds|3dsx)\b', combined, re.IGNORECASE):
            matched.append('3ds')
        elif re.search(r'\.nds\b', combined, re.IGNORECASE):
            matched.append('nds')

    return matched


def classify_topic(forum_id, raw_title, text_content=""):
    """Универсальная классификация раздачи по forum_id."""
    fid = str(forum_id)
    if fid == '1352':
        return ['psp']
    elif fid == '908':
        return ['ps1']
    elif fid == '773':
        return classify_topic_773(raw_title, text_content)
    elif fid == '129':
        return classify_topic_129(raw_title, text_content)
    elif fid == '357':
        return ['ps2']
    elif fid == '595':
        return ['psvita']
    elif fid == '968':
        return ['dreamcast']
    elif fid == '774':
        return classify_topic_774(raw_title, text_content)
    return []
