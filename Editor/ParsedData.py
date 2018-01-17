from collections import OrderedDict
from PyQt4 import QtGui, QtCore
import sys
sys.path.append('../')
import Code.configuration as cf
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import Code.ItemMethods as ItemMethods
import Code.CustomObjects as CustomObjects

from Code.UnitObject import Stat
import Code.Utility as Utility

import EditorUtilities
import DataImport

class TileData(object):
    def __init__(self):
        self.tiles = {}

    def get_tile_data(self):
        return self.tiles

    def load(self, tilefp):
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
                color = QtGui.QColor.fromRgb(tiledata.pixel(pos))
                mapObj[x].append((color.red(), color.green(), color.blue()))

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
        self.clear()
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
        cur_unit = EditorUtilities.find(DataImport.unit_data, legend['unit_id'])
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

        stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = \
            self.get_unit_info(DataImport.class_dict, u_i['klass'], u_i['level'], legend['items'])
        u_i['stats'] = self.build_stat_dict(stats)
        
        u_i['tags'] = DataImport.class_dict[u_i['klass']]['tags']
        u_i['ai'] = legend['ai']
        u_i['movement_group'] = DataImport.class_dict[u_i['klass']]['movement_group']
        u_i['skills'] = []

        cur_unit = DataImport.Unit(u_i)

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
