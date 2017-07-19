import pygame, os
from pygame.locals import *
import bmpfont, Engine, imagesDict
from configuration import *

import logging
logger = logging.getLogger(__name__)

# === GLOBAL CONSTANTS ===========================================
FPS = 60
FRAMERATE = 1000/FPS
TILEY = 10
TILEX = 15
TILEWIDTH = 16
TILEHEIGHT = 16
WINWIDTH = TILEWIDTH * TILEX
WINHEIGHT = TILEHEIGHT * TILEY
HALF_WINWIDTH = WINWIDTH/2
HALF_WINHEIGHT = WINHEIGHT/2

# Colors
colorDict = {'bright_blue': (0, 168, 248),
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

#pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
pygame.mixer.init()

# Icon
small_icon = Engine.image_load('Sprites/General/main_icon.png')
#Engine.set_colorkey(small_icon, (0, 0, 0), False)
pygame.display.set_icon(small_icon)

FPSCLOCK = pygame.time.Clock()
DISPLAYSURF = pygame.display.set_mode((WINWIDTH*OPTIONS['screen_scale'], WINHEIGHT*OPTIONS['screen_scale']))
version = "0.6"
pygame.display.set_caption(''.join(["The Lion Throne - ", version]))

IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT, ANIMDICT = imagesDict.getImages()
SOUNDDICT, MUSICDICT = imagesDict.getSounds()

# DATA
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
# Outside data
# === CREATE ITEM DICTIONARY =================================================
def create_item_dict():
    item_dict = {}
    # For each lore
    for entry in ET.parse('Data/items.xml').getroot().findall('item'):
        item_dict[entry.find('id').text] = {c.tag: c.text for c in entry}
        item_dict[entry.find('id').text].update(entry.attrib)
    return item_dict
ITEMDATA = create_item_dict() # This is done differently because I thought the ET was slow. Turns out its not slow. Creating ItemObjects is slow.
STATUSDATA = ET.parse('Data/status.xml')
UNITDATA = ET.parse('Data/units.xml')
CLASSDATA = ET.parse('Data/class_info.xml')
LOREDATA = ET.parse('Data/lore.xml')
PORTRAITDATA = ET.parse('Data/portrait_coords.xml')
TERRAINDATA = ET.parse('Data/terrain.xml')
def create_mcost_dict(fp):
    mcost_dict = {}
    with open(fp, 'r') as mcost_data:
        for line in mcost_data.readlines():
            if line.startswith('#'):
                continue
            s_line = line.strip().split()
            mcost_dict[s_line[0]] = [int(s) if s != '-' else 99 for s in s_line[1:]]
    return mcost_dict
MCOSTDATA = create_mcost_dict('Data/mcost.txt')

FONT = {}
for fp in os.listdir('Sprites/Fonts'):
    if fp.endswith('.png'):
        fp = fp[:-4]
        name = fp.lower()
        FONT[name] = bmpfont.BmpFont(fp)

MAINFONT = "Sprites/Fonts/KhmerUI.ttf"
BASICFONT = pygame.font.Font(MAINFONT, 10)
BIGFONT = pygame.font.Font(MAINFONT, 12)

import Counters
PASSIVESPRITECOUNTER = Counters.generic3Counter()
ACTIVESPRITECOUNTER = Counters.generic3Counter(280, 40)
CURSORSPRITECOUNTER = Counters.generic3Counter(250, 0, 100)