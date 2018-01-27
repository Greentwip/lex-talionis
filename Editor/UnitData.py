from collections import OrderedDict
import sys
from PyQt4 import QtGui, QtCore

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
from CustomGUI import SignalList, CheckableComboBox
import DataImport

class Group(object):
    def __init__(self, group_id, unit_name, faction, desc):
        self.group_id = group_id
        self.unit_name = unit_name
        self.faction = faction
        self.desc = desc

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

    def get_unit_images(self):
        return {unit.position: EditorUtilities.create_image(EditorUtilities.find(DataImport.class_data, unit.klass).get_image(unit.team))
                for unit in self.units if unit.position}

    def get_unit_from_pos(self, pos):
        for unit in self.units:
            if unit.position == pos:
                return unit
        #print('Could not find unit at %s, %s' % (pos[0], pos[1]))

    def get_idx_from_pos(self, pos):
        for idx, unit in enumerate(self.units):
            if unit.position == pos:
                return idx
        #print('Could not find unit at %s, %s' % (pos[0], pos[1]))
        return -1

    def get_unit_str(self, pos):
        for unit in self.units:
            if unit.position == pos:
                return unit.name + ': ' + unit.klass + ' ' + str(unit.level) + ' -- ' + ','.join([item.name for item in unit.items])
        return ''

    def parse_unit_line(self, unitLine, current_mode):
        if unitLine[0] == 'group':
            self.groups[unitLine[1]] = Group(unitLine[1], unitLine[2], unitLine[3], unitLine[4])
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
        self.add_unit_from_legend(legend)

    def add_unit_from_legend(self, legend):
        cur_unit = EditorUtilities.find(DataImport.unit_data, legend['unit_id'])
        position = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None
        if legend['event_id'] != "0": # unit does not start on board
            cur_unit.position = None
            self.reinforcements[legend['event_id']] = (cur_unit.id, position)
        else: # Unit does start on board
            cur_unit.position = position

        self.units.append(cur_unit)

    def add_unit(self, unit):
        self.units.append(unit)

    def remove_unit_from_idx(self, unit_idx):
        if self.units:
            self.units.pop(unit_idx)

    def replace_unit(self, unit_idx, unit):
        if self.units:
            self.units.pop(unit_idx)
        self.units.insert(unit_idx, unit)

    def saved_unit_from_line(self, unitLine):
        self.add_unit_from_line(unitLine)

    def create_unit_from_line(self, unitLine):
        assert len(unitLine) in [9, 10], "unitLine %s must have length 9 or 10 (if optional status)"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'class': unitLine[3], 'level': unitLine[4], 'items': unitLine[5], 
                  'position': unitLine[6], 'ai': unitLine[7], 'group': unitLine[8]}
        self.create_unit_from_legend(legend)

    def create_unit_from_legend(self, legend):
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

        group = self.groups[legend['group']]
        u_i['name'] = group.unit_name
        u_i['faction'] = group.faction
        u_i['desc'] = group.desc

        stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = \
            self.get_unit_info(DataImport.class_dict, u_i['klass'], u_i['level'], legend['items'])
        u_i['stats'] = self.build_stat_dict(stats)
        
        u_i['tags'] = DataImport.class_dict[u_i['klass']]['tags']
        u_i['ai'] = legend['ai']
        u_i['movement_group'] = DataImport.class_dict[u_i['klass']]['movement_group']
        u_i['skills'] = []
        u_i['generic'] = True

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

def setComboBox(combo_box, value):
    i = combo_box.findText(value)
    if i >= 0:
        combo_box.setCurrentIndex(i)

class GenderBox(QtGui.QGroupBox):
    def __init__(self):
        super(GenderBox, self).__init__()

        radios = (QtGui.QRadioButton("Male:"), QtGui.QRadioButton("Female:"))
        radios[0].setChecked(True)
        self.gender = 0

        hbox = QtGui.QHBoxLayout()

        self.gender_buttons = QtGui.QButtonGroup()
        for idx, radio in enumerate(radios):
            hbox.addWidget(radio)
            self.gender_buttons.addButton(radio, idx)
            radio.clicked.connect(self.radio_button_clicked)

        self.setLayout(hbox)

    def radio_button_clicked(self):
        self.gender = int(self.gender_buttons.checkedId())

    def value(self):
        return self.gender

    def setValue(self, value):
        self.radios[0].setChecked(not value)
        self.radios[1].setChecked(value)

class LoadUnitDialog(QtGui.QDialog):
    def __init__(self, instruction, parent):
        super(LoadUnitDialog, self).__init__(parent)
        self.form = QtGui.QFormLayout(self)
        self.form.addRow(QtGui.QLabel(instruction))

        # Unit Select
        self.unit_box = QtGui.QComboBox()
        self.unit_box.uniformItemSizes = True
        self.unit_box.setIconSize(QtCore.QSize(32, 32))
        self.unit_data = DataImport.unit_data
        for idx, unit in self.unit_data:
            if unit.image:
                self.unit_box.addItem(EditorUtilities.create_icon(unit.image), unit.name)
            else:
                self.unit_box.addItem(unit.name)
        self.form.addRow(self.unit_box)
        self.unit_box.currentItemChanged.connect(self.choose_unit)

        # Team
        self.team_box = QtGui.QComboBox()
        self.team_box.uniformItemSizes = True
        for team in DataImport.teams:
            self.team_box.addItem(team)
        self.team_box.activated.connect(self.team_changed)

        # Saved
        self.saved_checkbox = QtGui.QCheckBox('Load from last level?')
        self.form.addRow(self.saved_checkbox)

        # AI
        self.ai_select = QtGui.QComboBox()
        self.ai_select.uniformItemSizes = True
        for ai_name in GC.AIDATA:
            self.ai_select.addItem(ai_name)
        self.ai_select.setEnabled(False)
        self.form.addRow('Select AI:', self.ai_select)

        self.buttonbox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def load(self, unit):
        setComboBox(self.unit_box, unit.name)
        setComboBox(self.team_box, unit.team)
        self.saved_checkbox.setChecked(unit.saved)
        setComboBox(self.ai_select, unit.ai)

    def choose_unit(self, curr, prev):
        idx = self.unit_box.row(curr)
        self.current_unit = self.unit_data[idx]

    def team_changed(self, item):
        self.saved_checkbox.setEnabled(str(item) == 'player')
        self.ai_select.setEnabled(str(item) != 'player')

    def get_ai(self):
        return str(self.ai_select.currentText()) if self.ai_select.isEnabled() else 'None'

    @staticmethod
    def getUnit(parent, title, instruction, current_unit=None):
        dialog = LoadUnitDialog(instruction, parent)
        if current_unit:
            dialog.load(current_unit)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        unit = DataImport.unit_data[dialog.unit_box.currentIndex()]
        unit.ai = dialog.get_ai()
        unit.saved = bool(dialog.saved_checkbox.isChecked())
        return unit, result == QtGui.QDialog.Accepted

class CreateUnitDialog(QtGui.QDialog):
    def __init__(self, instruction, unit_data, parent):
        super(CreateUnitDialog, self).__init__(parent)
        self.form = QtGui.QFormLayout(self)
        self.form.addRow(QtGui.QLabel(instruction))
        self.unit_data = unit_data

        # Team
        self.team_box = QtGui.QComboBox()
        self.team_box.uniformItemSizes = True
        for team in DataImport.teams:
            self.team_box.addItem(team)
        self.team_box.activated.connect(self.team_changed)

        # Class
        self.class_box = QtGui.QComboBox()
        self.class_box.uniformItemSizes = True
        self.class_box.setIconSize(QtCore.QSize(48, 32))
        for klass in DataImport.class_data:
            self.class_box.addItem(EditorUtilities.create_icon(klass.images[0]), klass.name)
        self.form.addRow('Class:', self.class_box)

        # Level
        self.level = QtGui.QSpinBox()
        self.level.setMinimum(1)
        self.form.addRow('Level:', self.level)

        # Gender
        self.gender_box = GenderBox()
        self.form.addRow('Gender:', self.gender_box)

        # Items
        self.item_box = CheckableComboBox()
        self.item_box.uniformItemSizes = True
        self.item_box.setIconSize(QtCore.QSize(16, 16))
        for idx, item in enumerate(DataImport.item_data):
            if item.image:
                self.item_box.addItem(EditorUtilities.create_icon(item.image), item.name)
            else:
                self.item_box.addItem(item.name)
            row = self.item_box.model().item(idx, 0)
            row.setCheckState(QtCore.Qt.Unchecked)
        self.form.addRow('Items: ', self.item_box)   

        # AI
        self.ai_select = QtGui.QComboBox()
        self.ai_select.uniformItemSizes = True
        for ai_name in GC.AIDATA:
            self.ai_select.addItem(ai_name)
        self.form.addRow('AI:', self.ai_select)

        # Group
        self.group_select = QtGui.QComboBox()
        self.group_select.uniformItemSizes = True
        for group_name, group in unit_data.groups.iteritems():
            item = QtGui.QListWidgetItem(group.group_id)
            image = GC.UNITDICT.get(group.faction + 'Emblem')
            if image:
                image = image.convert_alpha()
                item.setIcon(EditorUtilities.create_icon(image))
            self.group_select.addItem(item)
        self.form.addRow('Group:', self.group_select)

        self.buttonbox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def load(self, unit):
        setComboBox(self.group_select, unit.group)
        self.level.setValue(unit.level)
        self.gender.setValue(unit.gender)
        setComboBox(self.team_box, unit.team)
        setComboBox(self.class_box, unit.klass)
        setComboBox(self.ai_select, unit.ai)
        item_list = [item.id for item in unit.items]
        for idx, item in enumerate(DataImport.item_data):
            row = self.item_box.model().item(idx, 0)
            if item.id in item_list:
                row.setCheckState(QtCore.Qt.Checked)
            else:
                row.setCheckState(QtCore.Qt.Unchecked)

    def team_changed(self, item):
        # Change class box to use sprites of that team
        # And also turn off AI
        self.ai_select.setEnabled(str(item) == 'player')
        for idx, klass in enumerate(DataImport.class_data):
            self.class_box.setItemIcon(idx, EditorUtilities.create_icon(klass.images[0]))

    def get_ai(self):
        return str(self.ai_select.currentText()) if self.ai_select.isEnabled() else 'None'

    def getCheckedItems(self):
        item_list = []
        for idx, item in enumerate(DataImport.item_data):
            row = self.item_box.model().item(idx, 0)
            if row.checkState() == QtCore.Qt.Checked:
                item_list.append(item)
        return item_list

    def create_unit(self):
        info = {}
        info['group'] = str(self.group_select.currentText)
        group = self.unit_data[info['group']]
        if group:
            info['name'] = group.unit_name
            info['faction'] = group.faction
            info['desc'] = group.desc
        info['level'] = int(self.level.value())
        info['gender'] = int(self.gender.value())
        info['klass'] = str(self.class_box.currentText())
        info['items'] = self.getCheckedItems()
        info['ai'] = self.get_ai()
        info['team'] = str(self.team_box.currentText())
        created_unit = DataImport.Unit(info)
        return created_unit

    @staticmethod
    def getUnit(parent, title, instruction, current_unit=None):
        dialog = CreateUnitDialog(instruction, parent.unit_data, parent)
        if current_unit:
            dialog.load(current_unit)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        unit = dialog.create_unit()
        return unit, result == QtGui.QDialog.Accepted

class UnitMenu(QtGui.QWidget):
    def __init__(self, unit_data, view, window=None):
        super(UnitMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window
        self.view = view

        self.list = SignalList(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QtCore.QSize(32, 32))

        self.load(unit_data)
        self.list.itemDoubleClicked.connect(self.modify_unit)

        self.load_unit_button = QtGui.QPushButton('Load Unit')
        self.load_unit_button.clicked.connect(self.load_unit)
        self.create_unit_button = QtGui.QPushButton('Create Unit')
        self.create_unit_button.clicked.connect(self.create_unit)
        self.remove_unit_button = QtGui.QPushButton('Remove Unit')
        self.remove_unit_button.clicked.connect(self.remove_unit)

        self.grid.addWidget(self.list, 0, 0)
        self.grid.addWidget(self.load_unit_button, 1, 0)
        self.grid.addWidget(self.create_unit_button, 2, 0)
        self.grid.addWidget(self.remove_unit_button, 3, 0)

    def trigger(self):
        self.view.tool = 'Units'

    def get_current_unit(self):
        return self.list.item(self.list.currentRow())

    def set_current_idx(self, idx):
        self.list.setCurrentRow(idx)

    def load(self, unit_data):
        self.unit_data = unit_data
        # Ingest Data
        for unit in self.unit_data.units:
            self.list.addItem(self.create_item(unit))

    # TODO: Need to use text color to show whether unit has a position set
    def create_item(self, unit):
        if unit.generic:
            item = QtGui.QListWidgetItem(str(unit.klass) + ': L' + str(unit.level))
        else:
            item = QtGui.QListWidgetItem(unit.name)
        klass = EditorUtilities.find(DataImport.class_data, unit.klass)
        if klass:
            item.setIcon(EditorUtilities.create_icon(klass.get_image(unit.team)))
        return item

    def load_unit(self):
        loaded_unit, ok = LoadUnitDialog.getUnit(self, "Load Unit", "Select unit:")
        if ok:
            self.add_unit(loaded_unit)
            self.unit_data.add_unit(loaded_unit)

    def create_unit(self):
        created_unit, ok = CreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:")
        if ok:
            self.add_unit(created_unit)
            self.unit_data.add_unit(created_unit)

    def remove_unit(self):
        unit_idx = self.list.currentRow()
        self.list.takeItem(unit_idx)
        self.unit_data.remove_unit_from_idx(unit_idx)

    def modify_unit(self, unit):
        idx = self.list.row(unit)
        if unit.generic:
            modified_unit, ok = LoadUnitDialog.getUnit(self, "Load Unit", "Select unit:", unit)
        else:
            modified_unit, ok = CreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:", unit)
        if ok:
            modified_unit.position = unit.position
            # Replace unit
            self.list.takeItem(idx)
            self.list.insertItem(idx, self.create_item(modified_unit))
            self.unit_data.replace_unit(idx, modified_unit)

    def add_unit(self, unit):
        self.list.addItem(self.create_item(unit))
        self.list.setCurrentRow(self.list.count() - 1)

class GroupDialog(QtGui.QDialog):
    def __init__(self, instruction, group=None, parent=None):
        super(GroupDialog, self).__init__(parent)
        self.form = QtGui.QFormLayout(self)
        self.form.addRow(QtGui.QLabel(instruction))

        self.id_line_edit = QtGui.QLineEdit()
        self.unit_name_line_edit = QtGui.QLineEdit()
        self.faction_line_edit = QtGui.QLineEdit()
        self.desc_text_edit = QtGui.QTextEdit()
        self.desc_text_edit.setFixedHeight(48)

        if group:
            self.id_line_edit.setText(group.group_id)
            self.unit_name_line_edit.setText(group.unit_name)
            self.faction_line_edit.setText(group.faction)
            self.desc_text_edit.setPlainText(group.desc)

        self.form.addRow("Group ID:", self.id_line_edit)
        self.form.addRow("Unit Name:", self.unit_name_line_edit)
        self.form.addRow("Faction:", self.faction_line_edit)
        self.form.addRow("Description:", self.desc_text_edit)

        self.buttonbox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def build_group(self):
        return Group(str(self.id_line_edit.text()), str(self.unit_name_line_edit.text()),
                     str(self.faction_line_edit.text()), str(self.desc_text_edit.toPlainText()))

    @staticmethod
    def getGroup(parent, title, instruction, group):
        dialog = GroupDialog(instruction, group, parent)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        group_obj = dialog.build_group()
        return group_obj, result == QtGui.QDialog.Accepted

class GroupMenu(QtGui.QWidget):
    def __init__(self, unit_data, view, window=None):
        super(GroupMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window
        self.view = view

        self.load_player_characters = QtGui.QCheckBox('Load saved player characters?')
        self.load_player_characters.stateChanged.connect(self.set_load_player_characters)

        self.list = SignalList(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QtCore.QSize(32, 32))

        self.load(unit_data)

        self.list.itemDoubleClicked.connect(self.modify_group)

        self.add_group_button = QtGui.QPushButton('Add Group')
        self.add_group_button.clicked.connect(self.add_group)
        self.remove_group_button = QtGui.QPushButton('Remove Group')
        self.remove_group_button.clicked.connect(self.remove_group)

        self.grid.addWidget(self.load_player_characters, 0, 0)
        self.grid.addWidget(self.list, 1, 0)
        self.grid.addWidget(self.add_group_button, 2, 0)
        self.grid.addWidget(self.remove_group_button, 3, 0)

    def trigger(self):
        self.view.tool = 'Groups'

    def create_item(self, group):
        item = QtGui.QListWidgetItem(group.group_id)

        image = GC.UNITDICT.get(group.faction + 'Emblem')
        if image:
            image = image.convert_alpha()
            item.setIcon(EditorUtilities.create_icon(image))

        return item

    def add_group(self):
        group_obj, ok = GroupDialog.getGroup(self, "Groups", "Enter New Group Values:")
        if ok:
            self.list.addItem(self.create_item(group_obj))
            self.groups.append(group_obj)

    def modify_group(self, item):
        group_obj, ok = GroupDialog.getGroup(self, "Groups", "Modify Group Values:", self.get_current_group())
        if ok:
            cur_row = self.list.currentRow()
            self.list.takeItem(cur_row)
            self.list.insertItem(cur_row, self.create_item(group_obj))
            self.groups[cur_row] = group_obj

    def remove_group(self):
        cur_row = self.list.currentRow()
        self.list.takeItem(cur_row)
        self.groups.pop(cur_row)

    def set_load_player_characters(self, state):
        self.unit_data.load_player_characters = bool(state)

    def get_current_group(self):
        return self.groups[self.list.currentRow()]

    def load(self, unit_data):
        self.unit_data = unit_data
        # Convert to list
        self.groups = sorted(self.unit_data.groups.values(), key=lambda x: x.group_id)
        # Ingest Data
        for group in self.groups:
            self.list.addItem(self.create_item(group))
        self.load_player_characters.setChecked(self.unit_data.load_player_characters)
