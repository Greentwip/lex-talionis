import os
from collections import OrderedDict
try:
    import bmpfont, Engine, imagesDict
    import configuration as cf
except ImportError:
    from . import bmpfont, Engine, imagesDict
    from . import configuration as cf

import logging
logger = logging.getLogger(__name__)

version = "0.8.7"
# === GLOBAL cf.CONSTANTS ===========================================
FPS = 60
FRAMERATE = 1000//FPS
TILEY = 10
TILEX = 15
TILEWIDTH = 16
TILEHEIGHT = 16
WINWIDTH = TILEWIDTH * TILEX
WINHEIGHT = TILEHEIGHT * TILEY

# Colors
COLORDICT = {'bright_blue': (0, 168, 248),
             'black': (0, 0, 0),
             'white': (248, 248, 248),
             'gold': (248, 240, 136),
             'dark_gold': (96, 104, 56),
             'light_gold': (248, 248, 152),
             'light_blue': (192, 248, 248),
             'light_gray': (192, 192, 192),
             'dark_gray': (168, 168, 168),
             'yellow': (248, 248, 0),
             'green': (0, 248, 0),
             'red': (248, 0, 0),
             'pink': (248, 144, 184),
             'blue': (0, 0, 248),
             'green_white': (64, 248, 64),
             'bg_color': (0, 168, 248),
             'off_white': (242, 234, 216),
             'brown': (72, 48, 24),
             'light_brown': (136, 120, 96),
             'off_black': (56, 48, 40),
             'navy_blue': (24, 24, 88)}

U_ID = 100
SUSPEND_LOC = 'Saves/Suspend.pmeta'

Engine.init()

# Icon
small_icon = Engine.image_load(Engine.engine_constants['home'] + 'Sprites/General/main_icon.png')
# Engine.set_colorkey(small_icon, (0, 0, 0), False)
Engine.set_icon(small_icon)

FPSCLOCK = Engine.clock()
DISPLAYSURF = Engine.build_display((WINWIDTH*cf.OPTIONS['Screen Size'], WINHEIGHT*cf.OPTIONS['Screen Size']))
Engine.set_caption(''.join([cf.CONSTANTS['title'], " - ", version]))
print('Version: v%s' % version)

IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT, ANIMDICT = imagesDict.getImages(Engine.engine_constants['home'])
SOUNDDICT, MUSICDICT = imagesDict.getSounds(Engine.engine_constants['home'])

# DATA
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
# Outside data
# === CREATE ITEM DICTIONARY =================================================
loc = Engine.engine_constants['home']

def create_item_dict():
    item_dict = {}
    # For each lore
    for idx, entry in enumerate(ET.parse(loc + 'Data/items.xml').getroot().findall('item')):
        name = entry.find('id').text
        item_dict[name] = {c.tag: c.text for c in entry}
        item_dict[name].update(entry.attrib)
        item_dict[name]['num'] = idx
    return item_dict
ITEMDATA = create_item_dict()  # This is done differently because I thought the ET was slow. Turns out its not slow. Creating ItemObjects is slow.

STATUSDATA = ET.parse(loc + 'Data/status.xml')
UNITDATA = ET.parse(loc + 'Data/units.xml')
CLASSDATA = ET.parse(loc + 'Data/class_info.xml')
LOREDATA = ET.parse(loc + 'Data/lore.xml')
PORTRAITDATA = ET.parse(loc + 'Data/portrait_coords.xml')
TERRAINDATA = ET.parse(loc + 'Data/terrain.xml')
if os.path.exists(loc + 'Data/preload_levels.xml'):
    PRELOADDATA = ET.parse(loc + 'Data/preload_levels.xml')
else:
    PRELOADDATA = None

def create_difficulty_dict(fp):
    difficulty_dict = OrderedDict()
    # For each difficulty
    for idx, entry in enumerate(ET.parse(fp).getroot().findall('difficulty')):
        name = entry.attrib['name']
        difficulty_dict[name] = {c.tag: c.text for c in entry}
        cur = difficulty_dict[name]
        cur['name'] = name
        cur['enemy_growths'] = [int(num) for num in cur['enemy_growths'].split(',')]
        cur['player_growths'] = [int(num) for num in cur['player_growths'].split(',')]
        cur['enemy_bases'] = [int(num) for num in cur['enemy_bases'].split(',')]
        cur['player_bases'] = [int(num) for num in cur['player_bases'].split(',')]
    return difficulty_dict
DIFFICULTYDATA = create_difficulty_dict(loc + 'Data/difficulty_modes.xml')

def create_mcost_dict(fp):
    mcost_dict = {}
    with open(fp, 'r') as mcost_data:
        for line in mcost_data.readlines():
            if line.startswith('#'):
                continue
            s_line = line.strip().split()
            mcost_dict[s_line[0]] = [int(s) if s != '-' else 99 for s in s_line[1:]]
    return mcost_dict
MCOSTDATA = create_mcost_dict(loc + 'Data/mcost.txt')

def create_ai_dict(fp):
    ai_dict = OrderedDict()
    with open(fp, 'r') as ai_data:
        for line in ai_data.readlines():
            if line.startswith('#'):
                continue
            s_line = line.strip().split()
            ai_dict[s_line[0]] = []
            for obj in s_line[1:]:
                if obj == '-':
                    obj = []
                elif obj.startswith('[') and obj.endswith(']'):
                    obj = obj[1:-1].split(',')
                elif obj.isdigit():
                    obj = int(obj)
                ai_dict[s_line[0]].append(obj)
    return ai_dict
AIDATA = create_ai_dict(loc + 'Data/ai_presets.txt')

FONT = {}
for fp in os.listdir(loc + 'Sprites/Fonts'):
    if fp.endswith('.png'):
        fp = fp[:-4]
        name = fp.lower()
        FONT[name] = bmpfont.BmpFont(fp)

MAINFONT = loc + "Sprites/Fonts/KhmerUI.ttf"
BASICFONT = Engine.build_font(MAINFONT, 10)
BIGFONT = Engine.build_font(MAINFONT, 12)

try:
    import Counters
except ImportError:
    from . import Counters
PASSIVESPRITECOUNTER = Counters.generic3Counter(int(32*FRAMERATE), int(4*FRAMERATE))
ACTIVESPRITECOUNTER = Counters.generic3Counter(int(13*FRAMERATE), int(6*FRAMERATE))
CURSORSPRITECOUNTER = Counters.generic3Counter(int(20*FRAMERATE), int(2*FRAMERATE), int(8*FRAMERATE))
