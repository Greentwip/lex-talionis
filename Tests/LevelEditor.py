from collections import OrderedDict
from PyQt4 import QtGui, QtCore
import sys, os, shutil
sys.path.append('../')
import Code.configuration as cf
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad

import Code.ItemMethods as ItemMethods
import Code.CustomObjects as CustomObjects
import Code.StatusObject as StatusObject

import Code.UnitSprite as UnitSprite
from Code.Dialogue import UnitPortrait
from Code.UnitObject import Stat
import Code.Utility as Utility

# DATA XML
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# === VIEW AND CONTROLLER METHODS ============================================
class ImageWidget(QtGui.QWidget):
    def __init__(self, surface, parent=None, x=0):
        super(ImageWidget, self).__init__(parent)
        w = surface.get_width()
        h = surface.get_height()
        self.data = surface.get_buffer().raw
        self.x = x
        # self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_RGB32)
        self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_ARGB32)
        self.resize(w, h)

def create_icon(image):
    icon = ImageWidget(image)
    icon = QtGui.QPixmap(icon.image)
    icon = QtGui.QIcon(icon)
    return icon

def create_pixmap(image):
    icon = ImageWidget(image)
    icon = QtGui.QPixmap(icon.image)
    return icon

def create_chibi(name):
    return Engine.subsurface(GC.UNITDICT[name + 'Portrait'], (96, 16, 32, 32)).convert_alpha()

def stretch(grid):
    box_h = QtGui.QHBoxLayout()
    box_h.addStretch(1)
    box_h.addLayout(grid)
    box_h.addStretch(1)
    box_v = QtGui.QVBoxLayout()
    box_v.addStretch(1)
    box_v.addLayout(box_h)
    box_v.addStretch(1)
    return box_v

# === DATA IMPORTING ===
def build_units(class_dict):
    units = []
    for unit in GC.UNITDATA.getroot().findall('unit'):
        u_i = {}
        u_i['id'] = unit.find('id').text
        u_i['name'] = unit.get('name')

        classes = unit.find('class').text.split(',')
        u_i['klass'] = classes[-1]

        u_i['gender'] = unit.find('gender').text
        u_i['level'] = int(unit.find('level').text)
        u_i['faction'] = unit.find('faction').text

        stats = SaveLoad.intify_comma_list(unit.find('bases').text)
        for n in xrange(len(stats), cf.CONSTANTS['num_stats']):
            stats.append(class_dict[u_i['klass']]['bases'][n])
        assert len(stats) == cf.CONSTANTS['num_stats'], "bases %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])
        u_i['stats'] = SaveLoad.build_stat_dict(stats)
        # print("%s's stats: %s", u_i['name'], u_i['stats'])

        u_i['growths'] = SaveLoad.intify_comma_list(unit.find('growths').text)
        u_i['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(u_i['growths'])))
        assert len(u_i['growths']) == cf.CONSTANTS['num_stats'], "growths %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])

        u_i['items'] = ItemMethods.itemparser(unit.find('inventory').text)
        # Parse wexp
        u_i['wexp'] = unit.find('wexp').text.split(',')
        for index, wexp in enumerate(u_i['wexp'][:]):
            if wexp in CustomObjects.WEAPON_EXP.wexp_dict:
                u_i['wexp'][index] = CustomObjects.WEAPON_EXP.wexp_dict[wexp]
        u_i['wexp'] = [int(num) for num in u_i['wexp']]

        assert len(u_i['wexp']) == len(CustomObjects.WEAPON_TRIANGLE.types), "%s's wexp must have as many slots as there are weapon types."%(u_i['name'])
        
        u_i['desc'] = unit.find('desc').text
        # Tags
        u_i['tags'] = set(unit.find('tags').text.split(',')) if unit.find('tags') is not None and unit.find('tags').text is not None else set()

        # Personal Skills
        personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []
        u_i['skills'] = [StatusObject.statusparser(status) for status in personal_skills]

        units.append(Unit(u_i))
    return units

def find(data, name):
    return next((x for x in data if x.name == name), None)

# === MODEL CLASS ===
class Unit(object):
    def __init__(self, info):
        if info:
            self.id = info['id']
            self.name = info['name']

            self.position = None
            self.level = int(info['level'])
            self.gender = int(info['gender'])
            self.faction = info['faction']
            self.klass = info['klass']
            self.tags = info['tags']
            self.desc = info['desc']

            self.stats = info['stats']
            self.growths = info['growths']

            self.wexp = info['wexp']
            self.items = info['items']
            self.skills = info['skills']

            self.team = info['team'] if 'team' in info else 'player' 
            try:
                self.image = create_chibi(self.name)
            except KeyError:
                self.image = GC.UNITDICT[self.faction + 'Emblem'].convert_alpha()
        else:
            self.id = 0
            self.name = ''
            self.position = None
            self.level = 1
            self.gender = 0
            self.faction = ''
            self.klass = 'Citizen'
            self.tags = set()
            self.desc = ''
            current_class = find(class_data, self.klass)
            self.stats = SaveLoad.build_stat_dict(current_class.bases)
            self.growths = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.items = []
            self.skills = []
            self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
            self.team = 'player'
            self.image = None

class Klass(object):
    def __init__(self, info):
        if info:
            self.name = info['id']
            self.wexp = info['wexp_gain']
            self.promotes_from = info['promotes_from']
            self.promotes_to = info['turns_into']
            self.movement_group = info['movement_group']
            self.tags = info['tags']
            self.skills = [s[1] for s in info['skills']]
            self.skill_levels = [s[0] for s in info['skills']]
            self.growths = info['growths']
            self.bases = info['bases']
            self.promotion = info['promotion']
            self.max = info['max']
            self.desc = info['desc']
        else:
            self.name = ''
            self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
            self.promotes_from = ''
            self.promotes_to = []
            self.movement_group = 0
            self.tags = set()
            self.skills = []
            self.skill_levels = []
            self.bases = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.growths = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.promotion = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.max = [40, 15, 15, 15, 15, 20, 15, 15, 20]
            self.desc = ''

        self.unit = GenericUnit(self.name)
        self.images = (self.unit.image1, self.unit.image2, self.unit.image3)
        self.image = self.images[0]

# === For use by class object ===
class GenericUnit(object):
    def __init__(self, klass, gender=0):
        self.gender = gender
        self.team = 'player'
        self.klass = klass
        self.stats = {}
        self.stats['HP'] = 1
        self.currenthp = 1
        self.sprite = UnitSprite.UnitSprite(self)
        GC.PASSIVESPRITECOUNTER.count = 0
        self.image1 = self.sprite.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha()
        GC.PASSIVESPRITECOUNTER.increment()
        self.image2 = self.sprite.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha()
        GC.PASSIVESPRITECOUNTER.increment()        
        self.image3 = self.sprite.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha()

    def get_images(self):
        self.images = (self.image1, self.image2, self.image3)

class MainView(QtGui.QGraphicsView):
    def __init__(self):
        QtGui.QGraphicsView.__init__(self)
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMinimumSize(15*16, 10*16)

    def set_new_image(self, image):
        image = QtGui.QImage(image)

        painter = QtGui.QPainter()
        painter.begin(image)
        painter.end()

        self.scene.addPixmap(QtGui.QPixmap.fromImage(image))

    def clear_image(self):
        self.scene.clear()

    def add_image(self):
        levelfolder = '../Data/LevelDEBUG'
        image = QtGui.QImage(levelfolder + '/MapSprite.png')

        painter = QtGui.QPainter()
        painter.begin(image)
        painter.end()

        self.scene.addPixmap(QtGui.QPixmap.fromImage(image))

class TileData(object):
    def __init__(self):
        self.tiles = {}

    def set_tile_data(self, tilefp):
        self.tiles = {}
        tiledata = QtGui.QImage(tilefp)
        colorkey, self.width, self.height = self.build_color_key(tiledata)
        self.populate_tiles(colorkey)

    def build_color_key(self, tiledata):
        width = tiledata.width()
        height = tiledata.height()
        mapObj = [] # Array of map data
    
        # Convert to a mapObj
        for x in range(width):
            mapObj.append([])
        for y in range(height):
            for x in range(width):
                pos = QtCore.QPoint(x, y)
                mapObj[x].append(QtGui.QColor.fromRgb(tiledata.pixel(pos))) # appends [r,g,b,t] value

        return mapObj, width, height

    def populate_tiles(self, colorKeyObj):
        for x in range(len(colorKeyObj)):
            for y in range(len(colorKeyObj[x])):
                cur = colorKeyObj[x][y]
                self.tiles[(x, y)] = cur

class UnitData(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.units = []
        self.reinforcements = {}
        self.groups = {}
        self.load_player_characters = False

    def load(self, fp):
        current_mode = '0123456789' # Defaults to all modes
        with open(fp) as data:
            unitcontent = data.readlines()
            for line in unitcontent:
                # Process each line that was in the level file.
                line = line.strip()
                # Skip empty or comment lines
                if not line or line.startswith('#'):
                    continue
                # Process line
                unitLine = line.split(';')
                current_mode = self.parse_unit_line(unitLine, current_mode)

    def parse_unit_line(self, unitLine, current_mode):
        if unitLine[0] == 'group':
            self.groups[unitLine[1]] = (unitLine[2], unitLine[3], unitLine[4])
        elif unitLine[0] == 'mode':
            current_mode = unitLine[1]
        elif unitLine[0] == 'load_player_characters':
            self.load_player_characters = True
        else: # For now it just loads every unit, irrespective of mode
            # New Unit
            if unitLine[1] == "0":
                if len(unitLine) > 7:
                    self.create_unit_from_line(unitLine)
                else:
                    self.add_unit_from_line(unitLine)
            # Saved Unit
            elif unitLine[1] == "1":
                self.saved_unit_from_line(unitLine)
        return current_mode

    def add_unit_from_line(self, unitLine):
        assert len(unitLine) == 6, "unitLine %s must have length 6"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'unit_id': unitLine[3], 'position': unitLine[4], 'ai': unitLine[5]}
        self.add_unit(legend)

    def add_unit(self, legend):
        cur_unit = find(unit_data, legend['unit_id'])
        position = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None
        if legend['event_id'] != "0": # unit does not start on board
            cur_unit.position = None
            self.reinforcements[legend['event_id']] = (cur_unit.id, position)
        else: # Unit does start on board
            cur_unit.position = position

        self.units.append(cur_unit)

    def saved_unit_from_line(self, unitLine):
        self.add_unit_from_line(unitLine)

    def create_unit_from_line(self, unitLine):
        assert len(unitLine) in [9, 10], "unitLine %s must have length 9 or 10 (if optional status)"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'class': unitLine[3], 'level': unitLine[4], 'items': unitLine[5], 
                  'position': unitLine[6], 'ai': unitLine[7], 'group': unitLine[8]}
        self.create_unit(legend)

    def create_unit(self, legend):
        GC.U_ID += 1

        u_i = {}
        u_i['id'] = GC.U_ID
        u_i['team'] = legend['team']
        u_i['event_id'] = legend['event_id']
        if legend['class'].endswith('F'):
            legend['class'] = legend['class'][:-1] # strip off the F
            u_i['gender'] = 5  # Default female gender is 5
        else:
            u_i['gender'] = 0  # Default male gender is 0
        classes = legend['class'].split(',')
        u_i['klass'] = classes[-1]
        # Give default previous class
        # default_previous_classes(u_i['klass'], classes, class_dict)

        u_i['level'] = int(legend['level'])
        u_i['position'] = tuple([int(num) for num in legend['position'].split(',')])
        u_i['name'], u_i['faction'], u_i['desc'] = self.groups[legend['group']]

        stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = self.get_unit_info(class_dict, u_i['klass'], u_i['level'], legend['items'])
        u_i['stats'] = self.build_stat_dict(stats)
        
        u_i['tags'] = class_dict[u_i['klass']]['tags']
        u_i['ai'] = legend['ai']
        u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']
        u_i['skills'] = []

        cur_unit = Unit(u_i)

        # Reposition units
        if u_i['event_id'] != "0": # Unit does not start on board
            cur_unit.position = None
            self.reinforcements[u_i['event_id']] = (cur_unit.id, u_i['position'])
        else: # Unit does start on board
            cur_unit.position = u_i['position']

        # Status Effects and Skills
        # get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj, feat=False)

        # Extra Skills
        # if len(unitLine) == 10:
            # statuses = [StatusObject.statusparser(status) for status in unitLine[9].split(',')]
            # for status in statuses:
                # StatusObject.HandleStatusAddition(status, cur_unit, gameStateObj)

        self.units.append(cur_unit)

    def build_stat_dict(self, stats):
        st = OrderedDict()
        for idx, name in enumerate(cf.CONSTANTS['stat_names']):
            st[name] = Stat(idx, stats[idx])
        return st
    
    def get_unit_info(self, class_dict, klass, level, item_line):
        # Handle stats
        # hp, str, mag, skl, spd, lck, def, res, con, mov
        bases = class_dict[klass]['bases'][:] # Using copies    
        growths = class_dict[klass]['growths'][:] # Using copies

        # ignoring modify stats for now
        # bases = [sum(x) for x in zip(bases, gameStateObj.modify_stats['enemy_bases'])]
        # growths = [sum(x) for x in zip(growths, gameStateObj.modify_stats['enemy_growths'])]

        stats, growth_points = self.auto_level(bases, growths, level)
        # Make sure we don't exceed max
        stats = [Utility.clamp(stat, 0, class_dict[klass]['max'][index]) for index, stat in enumerate(stats)]

        # Handle items
        items = ItemMethods.itemparser(item_line)

        # Handle required wexp
        wexp = class_dict[klass]['wexp_gain'][:]
        # print(klass, wexp)
        for item in items:
            if item.weapon:
                weapon_types = item.TYPE
                item_level = item.weapon.LVL
            elif item.spell:
                weapon_types = item.TYPE
                item_level = item.spell.LVL
            else:
                continue
            for weapon_type in weapon_types:
                wexp_index = CustomObjects.WEAPON_TRIANGLE.type_to_index[weapon_type]
                item_requirement = CustomObjects.WEAPON_EXP.wexp_dict[item_level]
                # print(item, weapon_type, wexp_index, item_requirement, wexp[wexp_index])
                if item_requirement > wexp[wexp_index] and wexp[wexp_index] > 0:
                    wexp[wexp_index] = item_requirement
        # print(wexp)

        return stats, growths, growth_points, items, wexp

    def auto_level(self, bases, growths, level):
        # Only does fixed leveling
        stats = bases[:]
        growth_points = [50 for growth in growths]

        for index, growth in enumerate(growths):
            growth_sum = growth * (level - 1)
            stats[index] += growth_sum/100
            growth_points[index] += growth_sum%100

        return stats, growth_points

class TileInfo(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.tile_info_dict = dict()
        self.formation_highlights = dict()
        self.escape_highlights = dict()

    def load(self, tile_info_location):
        with open(tile_info_location) as fp:
            tile_info = fp.readlines()

        for line in tile_info:
            line = line.strip().split(':') # Should split in 2. First half being coordinate. Second half being properties
            coord = line[0].split(',')
            x1 = int(coord[0])
            y1 = int(coord[1])
            if len(coord) > 2:
                x2 = int(coord[2])
                y2 = int(coord[3])
                for i in range(x1, x2+1):
                    for j in range(y1, y2+1):
                        self.parse_tile_line((i, j), line[1].split(';'))
            else:
                self.parse_tile_line((x1, y1), line[1].split(';'))

    def parse_tile_line(self, coord, property_list):
        if coord not in self.tile_info_dict:
            self.tile_info_dict[coord] = {}
        for tile_property in property_list:
            property_name, property_value = tile_property.split('=')
            # Handle special cases...
            if property_name == 'Status': # Treasure does not need to be split. It is split by the itemparser function itself.
                # Turn these string of ids into a list of status objects
                status_list = []
                for status in property_value.split(','):
                    status_list.append(StatusObject.statusparser(status))
                property_value = status_list
            elif property_name in ("Escape", "Arrive"):
                self.escape_highlights[coord] = CustomObjects.Highlight(GC.IMAGESDICT["YellowHighlight"])
            elif property_name == "Formation":
                self.formation_highlights[coord] = CustomObjects.Highlight(GC.IMAGESDICT["BlueHighlight"])
            self.tile_info_dict[coord][property_name] = property_value

class MusicBox(QtGui.QWidget):
    def __init__(self, label, music='', window=None):
        super(MusicBox, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.label = QtGui.QLabel(label)
        self.txt = QtGui.QLineEdit(music)
        self.button = QtGui.QPushButton('...')
        self.button.clicked.connect(self.change)

        self.grid.addWidget(self.label, 0, 0)
        self.grid.addWidget(self.txt, 0, 1)
        self.grid.addWidget(self.button, 0, 2)

    def change(self):
        starting_path = QtCore.QDir.currentPath() + '/../Audio/music'
        print(starting_path)
        music_file = QtGui.QFileDialog.getOpenFileName(self, "Select Music File", starting_path,
                                                       "OGG Files (*.ogg);;All Files (*)")
        if music_file:
            music_file = str(music_file)
            starting_path = str(starting_path)
            head, tail = os.path.split(music_file)
            print(head)
            if os.path.normpath(head) != os.path.normpath(starting_path):
                print('Copying ' + music_file + ' to ' + starting_path)
                shutil.copy(music_file, starting_path)
            self.text.setText(tail.split('.')[0])

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class ImageBox(QtGui.QWidget):
    def __init__(self, label, image='', window=None):
        super(ImageBox, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.label = QtGui.QLabel(label)
        self.txt = QtGui.QLineEdit(image)
        self.button = QtGui.QPushButton('...')
        self.button.clicked.connect(self.change)

        self.grid.addWidget(self.label, 0, 0)
        self.grid.addWidget(self.txt, 0, 1)
        self.grid.addWidget(self.button, 0, 2)

    def change(self):
        starting_path = QtCore.QDir.currentPath() + '/../Sprites/General/Panoramas'
        print(starting_path)
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Select Image File", starting_path,
                                                       "PNG Files (*.png);;All Files (*)")
        if image_file:
            image = QtGui.QImage(image_file)
            if image.width() != 240 or image.height() != 160:
                QtGui.QErrorMessage().showMessage("Image chosen is not 240 pixels wide by 160 pixels high!")
                return
            image_file = str(image_file)
            starting_path = str(starting_path)
            head, tail = os.path.split(image_file)
            print(head)
            if os.path.normpath(head) != os.path.normpath(starting_path):
                print('Copying ' + image_file + ' to ' + starting_path)
                shutil.copy(image_file, starting_path)
            self.text.setText(tail.split('.')[0])

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class StringBox(QtGui.QWidget):
    def __init__(self, label, text='', max_length=None, window=None):
        super(StringBox, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        label = QtGui.QLabel(label)
        self.grid.addWidget(label, 0, 0)
        self.txt = QtGui.QLineEdit(text)
        if max_length:
            self.txt.setMaxLength(max_length)
        self.grid.addWidget(self.txt, 0, 1)

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

def add_line(grid, row):
    line = QtGui.QFrame()
    line.setFrameStyle(QtGui.QFrame.HLine)
    line.setLineWidth(0)
    grid.addWidget(line, row, 0)

class PropertyMenu(QtGui.QWidget):
    def __init__(self, window=None):
        super(PropertyMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        #self.grid.setVerticalSpacing(1)
        self.setLayout(self.grid)
        self.window = window

        self.name = StringBox('Chapter Name')
        self.grid.addWidget(self.name, 0, 0)

        self.prep = QtGui.QCheckBox('Show Prep Menu?')
        self.grid.addWidget(self.prep, 1, 0)

        self.prep_music = MusicBox('Prep Music')
        self.grid.addWidget(self.prep_music, 2, 0)

        self.pick = QtGui.QCheckBox('Allow Pick Units?')
        self.grid.addWidget(self.pick, 3, 0)

        self.prep.stateChanged.connect(self.prep_enable)

        self.base = QtGui.QCheckBox('Show Base Menu?')
        self.grid.addWidget(self.base, 4, 0)

        self.base_music = MusicBox('Base Music')
        self.grid.addWidget(self.base_music, 5, 0)

        self.base_bg = ImageBox('Base Image')
        self.grid.addWidget(self.base_bg, 6, 0)

        self.base.stateChanged.connect(self.base_enable)

        self.market = QtGui.QCheckBox('Allow Prep/Base Market?')
        self.grid.addWidget(self.market, 7, 0)

        self.transition = QtGui.QCheckBox('Show Chpt. Transition?')
        self.grid.addWidget(self.transition, 8, 0)

        # Main music
        music_grid = QtGui.QGridLayout()
        self.grid.addLayout(music_grid, 10, 0)
        music_grid.setVerticalSpacing(0)

        add_line(music_grid, 0)
        self.player_music = MusicBox('Player Phase Music')
        music_grid.addWidget(self.player_music, 1, 0)
        self.enemy_music = MusicBox('Enemy Phase Music')
        music_grid.addWidget(self.enemy_music, 2, 0)
        self.other_music = MusicBox('Other Phase Music')
        music_grid.addWidget(self.other_music, 3, 0)
        add_line(music_grid, 4)

        self.create_weather(12)
        add_line(self.grid, 14)
        self.create_objective(15)

        self.update()

    def create_weather(self, row):
        grid = QtGui.QGridLayout()
        weather = QtGui.QLabel('Weather')
        grid.addWidget(weather, 1, 0)

        self.weathers = ('Light', 'Dark', 'Rain', 'Sand', 'Snow')
        self.weather_boxes = []
        for idx, weather in enumerate(self.weathers):
            label = QtGui.QLabel(weather)
            grid.addWidget(label, 0, idx + 1, alignment=QtCore.Qt.AlignHCenter)
            check_box = QtGui.QCheckBox()
            grid.addWidget(check_box, 1, idx + 1, alignment=QtCore.Qt.AlignHCenter)
            self.weather_boxes.append(check_box)

        self.grid.addLayout(grid, row, 0, 2, 1)

    def create_objective(self, row):
        label = QtGui.QLabel('WIN CONDITION')
        self.grid.addWidget(label, row, 0, alignment=QtCore.Qt.AlignHCenter)

        self.simple_display = StringBox('Simple Display')
        self.grid.addWidget(self.simple_display, row + 1, 0)

        self.win_condition = StringBox('Win Condition')
        self.grid.addWidget(self.win_condition, row + 2, 0)

        self.loss_condition = StringBox('Loss Condition')
        self.grid.addWidget(self.loss_condition, row + 3, 0)

    def prep_enable(self, b):
        self.prep_music.setEnabled(b)
        self.pick.setEnabled(b)

    def base_enable(self, b):
        self.base_music.setEnabled(b)
        self.base_bg.setEnabled(b)

    def update(self):
        self.prep_enable(self.prep.isChecked())
        self.base_enable(self.base.isChecked())

    def new(self):
        self.name.setText('Example Name')
        self.prep.setChecked(False)
        self.base.setChecked(False)
        self.market.setChecked(False)
        self.transition.setChecked(True)
        self.player_music.setText('')
        self.enemy_music.setText('')
        self.other_music.setText('')
        self.prep_music.setText('')
        self.pick.setChecked(True)
        self.base_music.setText('')
        self.base_bg.setText('')

        for box in self.weather_boxes:
            box.setChecked(False)

        self.simple_display.setText('Defeat Boss')
        self.win_condition.setText('Defeat Boss')
        self.loss_condition.setText('Lord dies,OR,Party size falls below 5. Currently {gameStateObj.get_total_party_members()}')

    def load(self, overview):
        self.name.setText(overview['name'])
        self.prep.setChecked(bool(int(overview['prep_flag'])))
        self.base.setChecked(overview['base_flag'] != '0')
        self.market.setChecked(bool(int(overview['market_flag'])))
        self.transition.setChecked(bool(int(overview['transition_flag'])))
        self.player_music.setText(overview['player_phase_music'])
        self.enemy_music.setText(overview['enemy_phase_music'])
        self.other_music.setText(overview['other_phase_music'] if 'other_phase_music' in overview else '')
        self.prep_music.setText(overview['prep_music'] if self.prep.isChecked() else '')
        self.pick.setChecked(bool(int(overview['pick_flag'])))
        self.base_music.setText(overview['base_music'] if self.base.isChecked() else '')
        self.base_bg.setText(overview['base_flag'] if self.base.isChecked() else '')

        weather = overview['weather'].split(',') if 'weather' in overview else []
        for box in self.weather_boxes:
            box.setChecked(False)
        for name in weather:
            if name in self.weathers:
                idx = self.weathers.index(name)
                print(name)
                self.weather_boxes[idx].setChecked(True)

        self.simple_display.setText(overview['display_name'])
        self.win_condition.setText(overview['win_condition'])
        self.loss_condition.setText(overview['loss_condition'])

    def save(self):
        overview = OrderedDict()
        overview['name'] = self.name.text()
        overview['prep_flag'] = '1' if self.prep.isChecked() else '0'
        overview['prep_music'] = self.prep_music.text()
        overview['pick_flag'] = '1' if self.pick.isChecked() else '0'
        overview['base_flag'] = self.base_bg.text() if self.base.isChecked() else '0'
        overview['base_music'] = self.base_music.text()
        overview['market_flag'] = '1' if self.market.isChecked() else '0'
        overview['transition_flag'] = '1' if self.transition.isChecked() else '0'
        
        overview['display_name'] = self.simple_display.text()
        overview['win_condition'] = self.win_condition.text()
        overview['loss_condition'] = self.loss_condition.text()

        overview['player_phase_music'] = self.player_music.text()
        overview['enemy_phase_music'] = self.enemy_music.text()
        overview['other_phase_music'] = self.other_music.text()

        overview['weather'] = ','.join([w for i, w in enumerate(self.weathers) if self.weather_boxes[i].isChecked()])

        return overview

class MainEditor(QtGui.QMainWindow):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Level Editor v0.7.0')

        self.view = MainView()
        self.setCentralWidget(self.view)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')

        self.current_level_num = None

        self.create_actions()
        self.create_menus()
        self.create_dock_windows()

        # self.resize(640, 480)

        # Data
        self.tile_data = TileData()
        self.tile_info = TileInfo()
        self.overview_dict = OrderedDict()
        self.unit_data = UnitData()

        # Whether anything has changed since the last save
        self.modified = False

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def new(self):
        if self.maybe_save():
            self.new_level()

    def new_level(self):
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Map PNG", QtCore.QDir.currentPath(),
                                                  "PNG Files (*.png);;All Files (*)")
        if image_file:
            image = QtGui.QImage(image_file)
            if image.width() % 16 != 0 or image.height() % 16 != 0:
                QtGui.QErrorMessage().showMessage("Image width and/or height is not divisible by 16!")
                return
            self.view.clear_image()
            self.view.set_new_image(image_file)

            self.properties_menu.new()

    def open(self):
        if self.maybe_save():
            # "Levels (Level*);;All Files (*)",
            starting_path = QtCore.QDir.currentPath() + '/../Data'
            print('Starting Path')
            print(starting_path)
            directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Level", starting_path,
                                                               QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontResolveSymlinks)
            if directory:
                # Get the current level num
                if 'Level' in str(directory):
                    idx = str(directory).index('Level')
                    num = str(directory)[idx + 5:]
                    print('Level num')
                    print(num)
                    self.current_level_num = num
                self.load_level(directory)

    def load_level(self, directory):
        self.view.clear_image()
        image = directory + '/MapSprite.png'
        self.view.set_new_image(image)

        tilefilename = directory + '/TileData.png'
        print(tilefilename)
        self.tile_data.set_tile_data(tilefilename)

        overview_filename = directory + '/overview.txt'
        self.overview_dict = SaveLoad.read_overview_file(overview_filename)
        self.properties_menu.load(self.overview_dict)

        tile_info_filename = directory + '/tileInfo.txt'
        self.tile_info.load(tile_info_filename)

        unit_level_filename = directory + '/UnitLevel.txt'
        self.unit_data.clear()
        self.unit_data.load(unit_level_filename)

        if self.current_level_num:
            print('Loaded Level' + self.current_level_num)

    def write_overview(self, fp):
        with open(fp, 'w') as overview:
            for k, v in self.overview_dict.iteritems():
                if v:
                    overview.write(k + ';' + v + '\n')

    def save(self):
        # Find what the next unused num is 
        if not self.current_level_num:
            self.current_level_num = 'test'
        self.save_level(self.current_level_num)

    def save_level(self, num):
        data_directory = QtCore.QDir.currentPath() + '/../Data'
        level_directory = data_directory + '/Level' + num
        if not os.path.exists(level_directory):
            os.mkdir(level_directory)

        overview_filename = level_directory + '/overview.txt'
        self.overview_dict = self.properties_menu.save()
        self.write_overview(overview_filename)

        print('Saved Level' + num)

    def create_actions(self):
        self.new_act = QtGui.QAction("&New...", self, shortcut="Ctrl+N", triggered=self.new)
        self.open_act = QtGui.QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.save_act = QtGui.QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        self.exit_act = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)

    def create_menus(self):
        file_menu = QtGui.QMenu("&File", self)
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.save_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        self.view_menu = QtGui.QMenu("&View", self)

        help_menu = QtGui.QMenu("&Help", self)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(self.view_menu)
        self.menuBar().addMenu(help_menu)

    def create_dock_windows(self):
        self.properties_dock = QtGui.QDockWidget("Properties", self)
        self.properties_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.properties_menu = PropertyMenu()
        self.properties_dock.setWidget(self.properties_menu)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.properties_dock)
        self.view_menu.addAction(self.properties_dock.toggleViewAction())

        self.terrain_dock = QtGui.QDockWidget("Terrain", self)
        self.terrain_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Choose Terrain Here")
        self.terrain_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.terrain_dock)
        self.view_menu.addAction(self.terrain_dock.toggleViewAction())

        self.tile_info_dock = QtGui.QDockWidget("Tile Info", self)
        self.tile_info_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Choose Tile Information Here")
        self.tile_info_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.tile_info_dock)
        self.view_menu.addAction(self.tile_info_dock.toggleViewAction())

        self.group_dock = QtGui.QDockWidget("Groups", self)
        self.group_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Create Groups Here")
        self.group_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.group_dock)
        self.view_menu.addAction(self.group_dock.toggleViewAction())

        self.unit_dock = QtGui.QDockWidget("Units", self)
        self.unit_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Create Units Here")
        self.unit_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.unit_dock)
        self.view_menu.addAction(self.unit_dock.toggleViewAction())

        self.tabifyDockWidget(self.terrain_dock, self.tile_info_dock)
        self.tabifyDockWidget(self.tile_info_dock, self.group_dock)
        self.tabifyDockWidget(self.group_dock, self.unit_dock)

    def maybe_save(self):
        if self.modified:
            ret = QtGui.QMessageBox.warning(self, "Level Editor", "The level has been modified.\n"
                                            "Do you want to save your changes?",
                                            QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
            if ret == QtGui.QMessageBox.Save:
                return self.save()
            elif ret == QtGui.QMessageBox.Cancel:
                return False

        return True

def load_data():
    item_data = [ItemMethods.itemparser(item)[0] for item in GC.ITEMDATA]
    item_data = sorted(item_data, key=lambda item: GC.ITEMDATA[item.id]['num'])
    item_data = [item for item in item_data if not item.virtual]
    for item in item_data:
        if item.image:
            item.image = item.image.convert_alpha()
    skill_data = [StatusObject.statusparser(skill.find('id').text) for skill in GC.STATUSDATA.getroot().findall('status')]
    for skill in skill_data:
        if skill.image:
            skill.image = skill.image.convert_alpha()
    portrait_dict = SaveLoad.create_portrait_dict()
    
    class_dict = SaveLoad.create_class_dict()
    class_data = [Klass(v) for v in class_dict.values()]
    unit_data = build_units(class_dict)
    # Setting up portrait data
    portrait_data = []
    for name, portrait in portrait_dict.items():
        portrait_data.append(UnitPortrait(name, portrait['blink'], portrait['mouth'], (0, 0)))
    for portrait in portrait_data:
        portrait.create_image()
        portrait.image = portrait.image.convert_alpha()

    return unit_data, class_dict, class_data, item_data, skill_data, portrait_data

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    unit_data, class_dict, class_data, item_data, skill_data, portrait_data = load_data()
    window = MainEditor()
    # Engine.remove_display()
    window.show()
    app.exec_()
