import os
from collections import OrderedDict

from . import bmpfont, Engine, imagesDict, Equations
from . import configuration as cf
from . import static_random

import metrosetup

#import logging
#logger = logging.getLogger(__name__)

version = "0.9.4.4"
# === GLOBAL CONSTANTS ===========================================
FPS = 60
FRAMERATE = 1000//FPS
TILEY = 10
TILEX = 15
TILEWIDTH = 16
TILEHEIGHT = 16
WINWIDTH = TILEWIDTH * TILEX
WINHEIGHT = TILEHEIGHT * TILEY

SCREEN_WIDTH = cf.OPTIONS['Screen Width']
SCREEN_HEIGHT = cf.OPTIONS['Screen Height']


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

SUSPEND_LOC = metrosetup.get_prefs_dir() + '/' 'Saves/Suspend.pmeta'

Engine.init()

# Icon
small_icon = Engine.image_load(Engine.engine_constants['home'] + 'Sprites/General/main_icon.png')
# Engine.set_colorkey(small_icon, (0, 0, 0), False)
Engine.set_icon(small_icon)

FPSCLOCK = Engine.clock()
#DISPLAYSURF = Engine.build_display((WINWIDTH*cf.OPTIONS['Screen Size'], WINHEIGHT*cf.OPTIONS['Screen Size']))
DISPLAYSURF = Engine.build_display((cf.OPTIONS['Screen Width'], cf.OPTIONS['Screen Height']))
 
def get_temp_canvas_rect():
    size = (cf.OPTIONS['Screen Width'], cf.OPTIONS['Screen Height'])
    height_proportion = 160 / size[1]
    width = int(240 / height_proportion) 
    height = size[1]
    return (int((size[0] - width) / 2), 0, width, height)

TEMPCANVASRECT = get_temp_canvas_rect()

def build_temp_canvas():
    return Engine.create_surface((TEMPCANVASRECT[2], TEMPCANVASRECT[3]))

TEMPCANVAS = build_temp_canvas()

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

EQUATIONS = Equations.Parser(loc + 'Data/equations.txt')

def create_item_dict():
    item_dict = {}
    # For each item
    for idx, entry in enumerate(ET.parse(loc + 'Data/items.xml').getroot().findall('item')):
        name = entry.find('id').text
        item_dict[name] = {c.tag: c.text for c in entry}
        item_dict[name].update(entry.attrib)
        item_dict[name]['num'] = idx
    return item_dict
ITEMDATA = create_item_dict()  # This is done differently because I thought the ET was slow. Turns out its not slow. Creating ItemObjects is slow.

STATUSDATA = ET.parse('Assets/Lex-Talionis/Data/status.xml')
UNITDATA = ET.parse('Assets/Lex-Talionis/Data/units.xml')
CLASSDATA = ET.parse('Assets/Lex-Talionis/Data/class_info.xml')
LOREDATA = ET.parse('Assets/Lex-Talionis/Data/lore.xml')
PORTRAITDATA = ET.parse('Assets/Lex-Talionis/Data/portrait_coords.xml')
TERRAINDATA = ET.parse('Assets/Lex-Talionis/Data/terrain.xml')
try:
    PRELOADDATA = ET.parse('Assets/Lex-Talionis/Data/preload_levels.xml')
except:
    PRELOADDATA = None

# === Grab general catalogs
def create_portrait_dict():
    portrait_dict = OrderedDict()
    for portrait in PORTRAITDATA.getroot().findall('portrait'):
        portrait_dict[portrait.get('name')] = {'mouth': [int(coord) for coord in portrait.find('mouth').text.split(',')],
                                               'blink': [int(coord) for coord in portrait.find('blink').text.split(',')]}
    return portrait_dict

def create_lore_dict():
    lore_dict = {}
    # For each lore
    for entry in LOREDATA.getroot().findall('lore'):
        lore_dict[entry.get('name')] = {'long_name': entry.find('long_name').text,
                                        'short_name': entry.get('name'),
                                        'desc': entry.find('desc').text,
                                        'type': entry.find('type').text,
                                        'unread': True}
    return lore_dict

PORTRAITDICT = create_portrait_dict()
LOREDICT = create_lore_dict()

def create_difficulty_dict(fp):
    difficulty_dict = OrderedDict()
    # For each difficulty
    for idx, entry in enumerate(ET.parse(fp).getroot().findall('difficulty')):
        name = entry.attrib['name']
        difficulty_dict[name] = {c.tag: c.text for c in entry}
        cur = difficulty_dict[name]
        cur['name'] = name
        for var in ('enemy_growths', 'player_growths', 'boss_growths', 'enemy_bases', 'player_bases', 'boss_bases'):
            if var in cur:
                cur[var] = [int(num) for num in cur[var].split(',')]
            else:
                cur[var] = [0] * len(EQUATIONS.stat_list)
        for var in ('autolevel_enemies', 'autolevel_players', 'autolevel_bosses'):
            if var not in cur:
                cur[var] = "0"
    return difficulty_dict
DIFFICULTYDATA = create_difficulty_dict('Assets/Lex-Talionis/Data/difficulty_modes.xml')

def create_mcost_dict(fp):
    mcost_dict = {}
    with open(fp, mode='r', encoding='utf-8') as mcost_data:
        for line in mcost_data.readlines():
            if line.startswith('#'):
                continue
            s_line = line.strip().split()
            mcost_dict[s_line[0]] = [int(s) if s != '-' else 99 for s in s_line[1:]]
    return mcost_dict
MCOSTDATA = create_mcost_dict('Assets/Lex-Talionis/Data/mcost.txt')

def create_ai_dict(fp):
    ai_dict = OrderedDict()
    if not os.path.exists(fp):
        print("error finding ai")
        return ai_dict
    with open(fp, mode='r', encoding='utf-8') as ai_data:
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
AIDATA = create_ai_dict('Assets/Lex-Talionis/Data/ai_presets.txt')

def create_overworld_data(fp):
    overworld_data = {}
    cur_dict = None
    if not os.path.exists(fp):
        return overworld_data
    with open(fp, mode='r', encoding='utf-8') as data:
        for line in data.readlines():
            if line.startswith('#'):
                continue
            elif line.startswith('==='):
                cur_dict = line.strip()[3:]
                overworld_data[cur_dict] = []
                continue
            s_line = line.strip().split(';')
            if cur_dict == 'Locations':
                place = {}
                place['level_id'] = s_line[0]
                place['location_name'] = s_line[1]
                place['icon_idx'] = int(s_line[2])
                place['position'] = tuple([int(i) for i in s_line[3].split(',')])
                overworld_data[cur_dict].append(place)
            elif cur_dict == 'Routes':
                route = {}
                route['connection'] = tuple(s_line[0].split(','))
                route['route'] = tuple([int(i) for i in s_line[1].split(',')])
                overworld_data[cur_dict].append(route)   
            elif cur_dict == 'Parties':
                party = {}
                party['party_id'] = int(s_line[0])
                party['name'] = s_line[1]
                overworld_data[cur_dict].append(party)   
    return overworld_data
OVERWORLDDATA = create_overworld_data('Assets/Lex-Talionis/Data/overworld_data.txt')

class LevelUpQuotes():
    def __init__(self, fn):
        self.info = {}
        if os.path.exists(fn):
            with open(fn, encoding='utf-8', mode='r') as fp:
                lines = [l.strip().split(';') for l in fp.readlines() if l.strip() and not l.strip().startswith('#')]
            for line in lines:
                self.info[line[0]] = []
                for quotes in line[1:]:
                    s_quotes = quotes.split('|')
                    # List of lists
                    self.info[line[0]].append(s_quotes)

    def get(self, unit_id, num_stats, level):
        if unit_id in self.info:
            if num_stats <= 1:
                quotes = self.info[unit_id][0]
            elif num_stats in (2, 3):
                quotes = self.info[unit_id][1]
            elif num_stats in (4, 5):
                quotes = self.info[unit_id][2]
            else:
                quotes = self.info[unit_id][3]
            # Return a random quote
            r = static_random.get_levelup(unit_id, level)
            return quotes[r.randint(0, len(quotes) - 1)]
        return None

    def get_capped(self, unit_id, level):
        if unit_id in self.info:
            if len(self.info[unit_id]) > 4:
                quotes = self.info[unit_id][4]
                r = static_random.get_levelup(unit_id, level)
                return quotes[r.randint(0, len(quotes) - 1)]
        return None

    def get_promotion(self, unit_id, level):
        if unit_id in self.info:
            if len(self.info[unit_id]) > 5:
                quotes = self.info[unit_id][5]
                r = static_random.get_levelup(unit_id, level)
                return quotes[r.randint(0, len(quotes) - 1)]
        return None

LEVELUPQUOTES = LevelUpQuotes('Assets/Lex-Talionis/Data/levelup_quotes.txt')

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
