from collections import OrderedDict
import sys

from PyQt5.QtWidgets import QWidget, QStyledItemDelegate, QGridLayout, QPushButton, QErrorMessage
from PyQt5.QtWidgets import QLabel, QComboBox, QHBoxLayout, QListWidgetItem, QMessageBox, QInputDialog
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import Code.ItemMethods as ItemMethods
import Code.Weapons as Weapons

from Code.StatObject import build_stat_dict
import Code.Utility as Utility
from Code.Triggers import Trigger

from . import DataImport
from EditorCode.DataImport import Data
from . import EditorUtilities, Faction, UnitDialogs
from EditorCode.CustomGUI import DragAndDropSignalList

class UnitData(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.units = []
        self.reinforcements = []
        self.factions = OrderedDict()
        self.triggers = OrderedDict()
        # self.load_player_characters = False

    def load(self, fp):
        self.clear()
        current_mode = [mode['name'] for mode in GC.DIFFICULTYDATA.values()] # Defaults to all modes
        with open(fp, mode='r', encoding='utf-8') as data:
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

    def get_unit_images(self, mode):
        return {unit.position: EditorUtilities.create_image(unit.klass_image) if unit.klass_image else 
                EditorUtilities.create_image(Data.class_data.get(unit.klass, Data.class_data['Citizen']).get_image(unit.team, unit.gender))
                for unit in self.units if unit.position and mode in unit.mode}

    def get_reinforcement_images(self, mode, pack):
        return {rein.position: EditorUtilities.create_image(rein.klass_image) if rein.klass_image else 
                EditorUtilities.create_image(Data.class_data.get(rein.klass, Data.class_data['Citizen']).get_image(rein.team, rein.gender))
                for rein in self.reinforcements if rein.position and mode in rein.mode and rein.pack == pack}

    def get_unit_from_id(self, e_id):
        for unit in self.units:
            if unit.id == e_id:
                return unit
        return None

    def get_rein_from_id(self, e_id):
        for rein in self.reinforcements:
            if rein.id == e_id:
                return rein
            else:
                written_event_id = rein.pack + '_' + str(rein.event_id) if rein.pack else str(rein.event_id)
                if written_event_id == e_id:
                    return rein
        return None

    def get_unit_from_pos(self, pos, modes):
        for unit in self.units:
            if unit.position == pos and any(mode in modes for mode in unit.mode):
                return unit
        # print('Could not find unit at %s, %s' % (pos[0], pos[1]))

    def get_rein_from_pos(self, pos, modes, pack):
        for rein in self.reinforcements:
            if rein.position == pos and any(mode in modes for mode in rein.mode) and rein.pack == pack:
                return rein
        # print('Could not find unit at %s, %s' % (pos[0], pos[1]))

    def get_idx_from_pos(self, pos, modes):
        for idx, unit in enumerate(self.units):
            if unit.position == pos and any(mode in modes for mode in unit.mode):
                return idx
        # print('Could not find unit at %s, %s' % (pos[0], pos[1]))
        return -1

    def get_ridx_from_pos(self, pos, modes, pack):
        for idx, rein in enumerate(self.reinforcements):
            if rein.position == pos and any(mode in modes for mode in rein.mode) and rein.pack == pack:
                return idx
        # print('Could not find unit at %s, %s' % (pos[0], pos[1]))
        return -1

    def get_unit_str(self, pos, modes):
        for unit in self.units:
            if unit.position == pos and any(mode in modes for mode in unit.mode):
                return unit.name + ': ' + unit.klass + ' ' + str(unit.level) + ' -- ' + ','.join([item.name for item in unit.items])
        return ''

    def get_reinforcement_str(self, pos, modes, pack):
        for rein in self.reinforcements:
            if rein.position == pos and any(mode in modes for mode in rein.mode) and rein.pack == pack:
                return pack + '_' + str(rein.event_id) + ': ' + rein.klass + ' ' + str(rein.level) + ' -- ' + ','.join([item.name for item in rein.items])
        return ''

    def parse_unit_line(self, unitLine, current_mode):
        def read_trigger_line(unitLine, current_mode):
            if ',' in unitLine[2]:
                position = tuple(int(n) for n in unitLine[2].split(','))
                return self.get_unit_from_pos(position, current_mode)
            else:
                unit = self.get_unit_from_id(unitLine[2])
                if unit:
                    return unit
                else:
                    return self.get_rein_from_id(unitLine[2])

        if unitLine[0] == 'faction':
            self.factions[unitLine[1]] = Faction.Faction(unitLine[1], unitLine[2], unitLine[3], unitLine[4])
        elif unitLine[0] == 'mode':
            current_mode = unitLine[1].split(',')
            if 'All' in current_mode:
                current_mode = [mode['name'] for mode in GC.DIFFICULTYDATA.values()]
        elif unitLine[0] == 'load_player_characters':
            # self.load_player_characters = True
            pass
        elif unitLine[0] == 'trigger':
            unit = read_trigger_line(unitLine, current_mode)
            if unitLine[1] not in self.triggers:
                self.triggers[unitLine[1]] = Trigger()
            self.triggers[unitLine[1]].add_unit(unit, unitLine[3], unitLine[4])
        else: # For now it just loads every unit, irrespective of mode
            if unitLine[1] == "2":
                return current_mode  # Skip infinite created units for now (TODO)
            # New Unit
            if len(unitLine) > 7:
                self.create_unit_from_line(unitLine, current_mode)
            else:
                self.add_unit_from_line(unitLine, current_mode)
            # # Saved Unit
            # elif unitLine[1] == "1":
            #     print("Saved!")
            #     self.saved_unit_from_line(unitLine)
        return current_mode

    def add_unit_from_line(self, unitLine, mode):
        assert len(unitLine) == 6, "unitLine %s must have length 6"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'unit_id': unitLine[3], 'position': unitLine[4], 'ai': unitLine[5]}
        self.add_unit_from_legend(legend, mode)

    def add_unit_from_legend(self, legend, mode):
        unit_prefab = Data.unit_data.get(legend['unit_id'])
        if not unit_prefab:
            return
        cur_unit = unit_prefab.copy()
        position = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None
        cur_unit.position = position
        if '_' in legend['ai']:
            cur_unit.ai, cur_unit.ai_group = legend['ai'].split('_')
        else:
            cur_unit.ai, cur_unit.ai_group = legend['ai'], None
        cur_unit.team = legend['team']
        cur_unit.mode = mode
        if legend['unit_type'] == '1':
            cur_unit.saved = True
        else:
            cur_unit.saved = False
        if legend['event_id'] != "0": # unit does not start on board
            if '_' in legend['event_id']:
                split_term = legend['event_id'].split('_')
                cur_unit.pack = '_'.join(split_term[:-1])
                cur_unit.event_id = split_term[-1]
                cur_unit.event_id = int(cur_unit.event_id)
            else:
                cur_unit.pack, cur_unit.event_id = legend['event_id'], 1
            self.reinforcements.append(cur_unit)
        else: # Unit does start on board
            self.units.append(cur_unit)

    def add_unit(self, unit):
        self.units.append(unit)

    def add_reinforcement(self, rein):
        self.reinforcements.append(rein)

    def remove_unit_from_idx(self, unit_idx):
        if self.units:
            self.units.pop(unit_idx)

    def remove_reinforcement_from_idx(self, rein_idx):
        if self.reinforcements:
            self.reinforcements.pop(rein_idx)

    def replace_unit(self, unit_idx, unit):
        if self.units:
            self.units.pop(unit_idx)
        self.units.insert(unit_idx, unit)

    def replace_reinforcement(self, rein_idx, rein):
        if self.reinforcements:
            self.reinforcements.pop(rein_idx)
        self.reinforcements.insert(rein_idx, rein)

    def drag_and_drop_unit(self, old_idx, new_idx):
        if self.units:
            unit = self.units.pop(old_idx)
            self.units.insert(new_idx, unit)

    def drag_and_drop_rein(self, old_idx, new_idx):
        if self.reinforcements:
            rein = self.reinforcements.pop(old_idx)
            self.reinforcements.insert(new_idx, rein)

    def add_trigger(self, trigger_name):
        self.triggers[trigger_name] = Trigger()

    def remove_trigger(self, idx):
        trigger_name = list(self.triggers.keys())[idx]
        del self.triggers[trigger_name]   

    def get_trigger(self, idx):
        trigger_name = list(self.triggers.keys())[idx]
        return self.triggers[trigger_name]

    def get_trigger_name(self, idx):
        return list(self.triggers.keys())[idx]

    def saved_unit_from_line(self, unitLine):
        self.add_unit_from_line(unitLine)

    def create_unit_from_line(self, unitLine, mode):
        assert len(unitLine) in (9, 10), "unitLine %s must have length 9 or 10 (if optional status)"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'class': unitLine[3], 'level': unitLine[4], 'items': unitLine[5], 
                  'position': unitLine[6], 'ai': unitLine[7], 'faction': unitLine[8]}
        if len(unitLine) == 10:
            legend['extra_status'] = unitLine[9]
        else:
            legend['extra_status'] = None
        self.create_unit_from_legend(legend, mode)

    def create_unit_from_legend(self, legend, mode):
        GC.U_ID += 1

        u_i = {}
        u_i['id'] = GC.U_ID
        u_i['team'] = legend['team']
        if '_' in legend['event_id']:
            split_term = legend['event_id'].split('_')
            u_i['pack'] = '_'.join(split_term[:-1])
            u_i['event_id'] = split_term[-1]
            u_i['event_id'] = int(u_i['event_id'])
        elif legend['event_id'] != '0':
            u_i['pack'] = legend['event_id']
            u_i['event_id'] = 1
        else:
            u_i['pack'] = None
            u_i['event_id'] = 0
        if legend['class'].endswith('F'):
            legend['class'] = legend['class'][:-1] # strip off the F
            u_i['gender'] = 5  # Default female gender is 5
        else:
            u_i['gender'] = 0  # Default male gender is 0
        classes = legend['class'].split(',')
        u_i['klass'] = classes[-1]
        # Give default previous class
        # default_previous_classes(u_i['klass'], classes, class_dict)

        if legend['level'].startswith('f'):
            legend['level'] = legend['level'][1:]  # Remove f at the beginning
        u_i['level'] = int(legend['level'])  # Doesn't need force_fixed since it is fixed by default in LevelEditor
        u_i['position'] = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None

        u_i['faction'] = legend['faction']
        faction = self.factions[u_i['faction']]
        u_i['name'] = faction.unit_name
        u_i['faction_icon'] = faction.faction_icon
        u_i['desc'] = faction.desc

        stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = \
            self.get_unit_info(Data.class_dict, u_i['klass'], u_i['level'], legend['items'])
        u_i['stats'] = build_stat_dict(stats)
        
        cur_class = Data.class_dict.get(u_i['klass'], Data.class_dict.get('Citizen'))
        if not cur_class:
            raise KeyError("Must have Citizen class! Do not delete Citizen class!")
        u_i['tags'] = cur_class['tags']
        if '_' in legend['ai']:
            u_i['ai'], u_i['ai_group'] = legend['ai'].split('_')
        else:
            u_i['ai'], u_i['ai_group'] = legend['ai'], None
        u_i['movement_group'] = cur_class['movement_group']
        u_i['skills'] = []
        u_i['generic'] = True
        u_i['mode'] = mode

        cur_unit = DataImport.Unit(u_i)

        # Reposition units
        cur_unit.position = u_i['position']
        if legend['event_id'] != '0': # Unit does not start on board
            self.reinforcements.append(cur_unit)
        else: # Unit does start on board
            self.units.append(cur_unit)

        # Status Effects and Skills
        # get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj, feat=False)

        # Extra Skills
        cur_unit.extra_statuses = legend['extra_status']
    
    def get_unit_info(self, class_dict, klass, level, item_line):
        # Handle stats
        # hp, str, mag, skl, spd, lck, def, res, con, mov
        cur_class = class_dict.get(klass)
        if not cur_class:  # Fallback to Citizen class
            klass = 'Citizen'
        cur_class = class_dict.get(klass)
        if not cur_class:
            raise KeyError("Must have Citizen class! Do not delete Citizen class!")
        bases = cur_class['bases'][:] # Using copies    
        growths = cur_class['growths'][:] # Using copies

        # ignoring modify stats for now
        # bases = [sum(x) for x in zip(bases, gameStateObj.modify_stats['enemy_bases'])]
        # growths = [sum(x) for x in zip(growths, gameStateObj.modify_stats['enemy_growths'])]

        stats, growth_points = self.auto_level(bases, growths, level)
        # Make sure we don't exceed max
        stats = [Utility.clamp(stat, 0, cur_class['max'][index]) for index, stat in enumerate(stats)]

        # Handle items
        if item_line:
            items = [ItemMethods.itemparser(item) for item in item_line.split(',') if item]
        else:
            items = []
        items = [item for item in items if item]  # Remove Nones

        # Handle required wexp
        wexp = cur_class['wexp_gain'][:]
        # print(klass, wexp)
        for item in items:
            if item.weapon:
                weapon_type = item.TYPE
                item_level = item.weapon.LVL
            elif item.spell:
                weapon_type = item.TYPE
                item_level = item.spell.LVL
            else:
                continue
            if weapon_type:
                wexp_index = Weapons.TRIANGLE.name_to_index[weapon_type]
                item_requirement = Weapons.EXP.get_item_requirement(item_level)
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

# This allows for drawing the units items to the right of the unit on the list menu
class ItemDelegate(QStyledItemDelegate):
    def __init__(self, unit_data=None, rein=False):
        super(ItemDelegate, self).__init__()
        self.unit_data = unit_data
        self.rein = rein

    def paint(self, painter, option, index):
        super(ItemDelegate, self).paint(painter, option, index)
        if self.rein:
            current_unit = self.unit_data.reinforcements[index.row()]
        else:
            current_unit = self.unit_data.units[index.row()]
        for idx, item in enumerate(current_unit.items):
            image = Data.item_data[item.id].image
            rect = option.rect
            painter.drawImage(rect.right() - ((idx + 1) * 16), rect.center().y() - 8, EditorUtilities.create_image(image))

class UnitMenu(QWidget):
    def __init__(self, unit_data, view, window):
        super(UnitMenu, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window
        self.view = view

        self.create_mode_view_box()

        self.list = DragAndDropSignalList(self, del_func=self.remove_unit)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QSize(32, 32))
        self.delegate = ItemDelegate(unit_data)
        self.list.setItemDelegate(self.delegate)
        self.list.itemMoved.connect(self.drag_unit)

        self.load(unit_data)
        self.list.currentItemChanged.connect(self.center_on_unit)
        self.list.itemDoubleClicked.connect(self.modify_unit)
        # delete_key = QShortcut(QKeySequence(Qt.Key_Delete), self.list)
        # self.connect(delete_key, SIGNAL('activated()'), self.remove_unit)

        self.load_unit_button = QPushButton('Load Unit')
        self.load_unit_button.clicked.connect(self.load_unit)
        self.create_unit_button = QPushButton('Create Unit')
        self.create_unit_button.clicked.connect(self.create_unit)
        self.remove_unit_button = QPushButton('Remove Unit')
        self.remove_unit_button.clicked.connect(self.remove_unit)

        self.grid.addWidget(self.list, 2, 0)
        self.grid.addWidget(self.load_unit_button, 3, 0)
        self.grid.addWidget(self.create_unit_button, 4, 0)
        self.grid.addWidget(self.remove_unit_button, 5, 0)

        self.last_touched_generic = None

    # def trigger(self):
    #     self.view.tool = 'Units'

    def create_mode_view_box(self):
        self.mode_view_label = QLabel("Current Mode:")
        names = [mode['name'] for mode in GC.DIFFICULTYDATA.values()]
        self.mode_view_combobox = QComboBox()
        for name in names:
            self.mode_view_combobox.addItem(name)

        hbox = QHBoxLayout()
        hbox.addWidget(self.mode_view_label)
        hbox.addWidget(self.mode_view_combobox)
        self.grid.addLayout(hbox, 0, 0)

    def current_mode_view(self):
        return str(self.mode_view_combobox.currentText())

    def get_current_item(self):
        return self.list.item(self.list.currentRow())

    def get_current_unit(self):
        if self.unit_data.units and self.list.currentRow() >= 0:
            return self.unit_data.units[self.list.currentRow()]
        else:
            return None

    def get_item_from_unit(self, unit):
        return self.list.item(self.unit_data.units.index(unit))

    def set_current_idx(self, idx):
        self.list.setCurrentRow(idx)

    def center_on_unit(self, item, prev=None):
        idx = self.list.row(item)
        if self.unit_data.units:
        # idx = int(idx)
            unit = self.unit_data.units[idx]
            if unit.position:
                current_mode = str(self.mode_view_combobox.currentText())
                if unit.mode and current_mode not in unit.mode:
                    EditorUtilities.setComboBox(self.mode_view_combobox, unit.mode[0])
                self.view.center_on_pos(unit.position)

    def center(self, unit):
        if unit.position:
            current_mode = str(self.mode_view_combobox.currentText())
            if unit.mode and current_mode not in unit.mode:
                EditorUtilities.setComboBox(self.mode_view_combobox, unit.mode[0])
            self.view.center_on_pos(unit.position)

    def load(self, unit_data):
        self.clear()
        self.unit_data = unit_data
        # Ingest Data
        for unit in self.unit_data.units:
            self.list.addItem(self.create_item(unit))

    def clear(self):
        self.list.clear()

    def create_item(self, unit):
        if unit.generic:
            item = QListWidgetItem(str(unit.klass) + ': L' + str(unit.level))
        else:
            item = QListWidgetItem(unit.id)
        klass = Data.class_data.get(unit.klass)
        if klass:
            item.setIcon(EditorUtilities.create_icon(klass.get_image(unit.team, unit.gender)))
        if not unit.position:
            item.setForeground(QColor("red"))
        return item

    def load_unit(self):
        loaded_unit, ok = UnitDialogs.LoadUnitDialog.getUnit(self, "Load Unit", "Select unit:")
        if ok:
            self.unit_data.add_unit(loaded_unit)
            self.add_unit(loaded_unit)
            self.window.update_view()

    def create_unit(self):
        if self.unit_data.factions:
            unit = self.get_current_unit()
            if unit and not unit.generic:
                unit = self.last_touched_generic
            created_unit, ok = UnitDialogs.CreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:", unit)
            if ok:
                self.unit_data.add_unit(created_unit)
                self.add_unit(created_unit)
                self.last_touched_generic = created_unit
                self.window.update_view()
        else:
            # Show pop-up
            QMessageBox.critical(self, "No Faction!", "Must create at least one faction to create a generic unit!")

    def remove_unit(self):
        unit_idx = self.list.currentRow()
        self.list.takeItem(unit_idx)
        self.unit_data.remove_unit_from_idx(unit_idx)
        self.window.update_view()

    def modify_unit(self, item):
        idx = self.list.row(item)
        unit = self.unit_data.units[idx]
        if unit.generic:
            modified_unit, ok = UnitDialogs.CreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:", unit)
        else:
            modified_unit, ok = UnitDialogs.LoadUnitDialog.getUnit(self, "Load Unit", "Select unit:", unit)
        if ok:
            modified_unit.position = unit.position
            # Replace unit
            self.list.takeItem(idx)
            self.list.insertItem(idx, self.create_item(modified_unit))
            self.unit_data.replace_unit(idx, modified_unit)
            if modified_unit.generic:
                self.last_touched_generic = modified_unit
            self.window.update_view()

    def add_unit(self, unit):
        self.list.addItem(self.create_item(unit))
        self.list.setCurrentRow(self.list.count() - 1)

    def drag_unit(self, old_idx, new_idx, item):
        self.unit_data.drag_and_drop_unit(old_idx, new_idx)

    def tick(self, current_time):
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for idx, unit in enumerate(self.unit_data.units):
                if unit.klass in Data.class_data:
                    klass = Data.class_data[unit.klass]
                else:
                    klass = Data.class_data['Citizen']
                klass_image = klass.get_image(unit.team, unit.gender)
                self.list.item(idx).setIcon(EditorUtilities.create_icon(klass_image))
                unit.klass_image = klass_image

class ReinforcementMenu(UnitMenu):
    def __init__(self, unit_data, view, window):
        UnitMenu.__init__(self, unit_data, view, window)
        self.delegate = ItemDelegate(unit_data, rein=True)
        self.list.setItemDelegate(self.delegate)

        self.pack_view_label = QLabel("Group to display:")
        self.pack_view_combobox = QComboBox()
        self.packs = []

        hbox = QHBoxLayout()
        hbox.addWidget(self.pack_view_label)
        hbox.addWidget(self.pack_view_combobox)
        self.grid.addLayout(hbox, 1, 0)

        self.duplicate_group_button = QPushButton('Duplicate Group')
        self.duplicate_group_button.clicked.connect(self.duplicate_current_pack)
        self.grid.addWidget(self.duplicate_group_button, 5, 0)

        self.last_touched_generic = None

    # def trigger(self):
    #     self.view.tool = 'Reinforcements'

    def get_current_unit(self):
        if self.unit_data.reinforcements and self.list.currentRow() >= 0:
            rein = self.unit_data.reinforcements[self.list.currentRow()]
            return rein
        else:
            return None

    def get_item_from_unit(self, unit):
        return self.list.item(self.unit_data.reinforcements.index(unit))

    def center_on_unit(self, item, prev):
        idx = self.list.row(item)
        # idx = int(idx)
        unit = self.unit_data.reinforcements[idx]
        if unit.position:
            current_mode = str(self.mode_view_combobox.currentText())
            if unit.mode and current_mode not in unit.mode:
                EditorUtilities.setComboBox(self.mode_view_combobox, unit.mode[0])
            EditorUtilities.setComboBox(self.pack_view_combobox, unit.pack)
            self.view.center_on_pos(unit.position)

    def current_pack(self):
        return str(self.pack_view_combobox.currentText())

    def load(self, unit_data):
        self.clear()
        self.unit_data = unit_data
        # Ingest Data
        for unit in self.unit_data.reinforcements:
            item = self.create_item(unit)
            self.list.addItem(item)

    def create_item(self, unit):
        if unit.generic:
            item = QListWidgetItem(unit.pack + '_' + str(unit.event_id) + ' -- L' + str(unit.level))
        else:
            item = QListWidgetItem(unit.pack + '_' + str(unit.event_id) + ' -- ' + unit.id)
        klass = Data.class_data.get(unit.klass)
        if klass:
            item.setIcon(EditorUtilities.create_icon(klass.get_image(unit.team, unit.gender)))
        if not unit.position:
            item.setForeground(QColor("red"))
        if unit.pack not in self.packs:
            self.packs.append(unit.pack)
            self.pack_view_combobox.addItem(unit.pack)
            self.pack_view_combobox.setCurrentIndex(self.pack_view_combobox.count() - 1)
        return item

    def load_unit(self):
        loaded_unit, ok = UnitDialogs.ReinLoadUnitDialog.getUnit(self, "Load Reinforcement", "Select reinforcement:")
        if ok:
            self.unit_data.add_reinforcement(loaded_unit)
            self.add_unit(loaded_unit)
            self.window.update_view()

    def create_unit(self):
        if self.unit_data.factions:
            unit = self.get_current_unit()
            if unit and not unit.generic:
                unit = self.last_touched_generic
            created_unit, ok = UnitDialogs.ReinCreateUnitDialog.getUnit(self, "Create Reinforcement", "Enter values for reinforcement:", unit)
            if ok:
                self.unit_data.add_reinforcement(created_unit)
                self.add_unit(created_unit)            
                self.last_touched_generic = created_unit
                self.window.update_view()
        else:
            # Show pop-up
            QErrorMessage().showMessage("Must create at least one faction to use generic units!")

    def remove_unit(self):
        unit_idx = self.list.currentRow()
        self.list.takeItem(unit_idx)
        unit = self.unit_data.reinforcements[unit_idx]
        self.unit_data.remove_reinforcement_from_idx(unit_idx)
        self.check_remove_pack(unit.pack)
        self.window.update_view()

    def check_remove_pack(self, old_pack):
        for rein in self.unit_data.reinforcements:
            if rein.pack == old_pack:
                break
        else:
            # Remove pack from pack combo
            idx = self.pack_view_combobox.findText(old_pack)
            self.pack_view_combobox.removeItem(idx)

    def modify_unit(self, item):
        idx = self.list.row(item)
        unit = self.unit_data.reinforcements[idx]
        old_pack = unit.pack
        if unit.generic:
            modified_unit, ok = UnitDialogs.ReinCreateUnitDialog.getUnit(self, "Create Reinforcement", "Enter values for reinforcement:", unit)
        else:
            modified_unit, ok = UnitDialogs.ReinLoadUnitDialog.getUnit(self, "Load Reinforcement", "Select reinforcement:", unit)
        if ok:
            modified_unit.position = unit.position
            # Replace unit
            self.list.takeItem(idx)
            item = self.create_item(modified_unit)
            self.list.insertItem(idx, item)
            self.list.setCurrentRow(self.list.row(item))
            self.unit_data.replace_reinforcement(idx, modified_unit)
            self.check_remove_pack(old_pack)
            if modified_unit.generic:
                self.last_touched_generic = modified_unit
            print(idx, self.list.row(item))
            self.window.update_view()

    def add_unit(self, unit):
        item = self.create_item(unit)
        self.list.addItem(item)
        self.list.setCurrentRow(self.list.row(item))

    def drag_unit(self, old_idx, new_idx, unit):
        self.unit_data.drag_and_drop_rein(old_idx, new_idx)

    def duplicate_current_pack(self):
        current_pack = self.current_pack()  # Need to be saved since it changes within this function's for loop
        new_name, ok = QInputDialog.getText(self, "Duplicate Group", 'Enter name of duplicated group:',
                                                  text=current_pack if current_pack else "")
        if ok:
            if not any(rein.pack == new_name for rein in self.unit_data.reinforcements):
                counter = 0
                for idx, unit in enumerate(self.unit_data.reinforcements):
                    if unit.pack == current_pack:
                        counter += 1
                        created_unit = unit.copy()
                        created_unit.pack = new_name
                        created_unit.event_id = counter
                        created_unit.position = unit.position  # Make sure position is copied over
                        self.unit_data.add_reinforcement(created_unit)
                        self.add_unit(created_unit)              
                self.window.update_view()
            else:
                # Show pop-up
                QErrorMessage().showMessage("Must use new name for duplicated group!")

    def tick(self, current_time):
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for idx, unit in enumerate(self.unit_data.reinforcements):
                klass = Data.class_data[unit.klass]
                klass_image = klass.get_image(unit.team, unit.gender)
                self.list.item(idx).setIcon(EditorUtilities.create_icon(klass_image))
                unit.klass_image = klass_image
