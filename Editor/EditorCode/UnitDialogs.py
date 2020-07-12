import sys

from PyQt5.QtWidgets import QGridLayout, QDialog, QFormLayout, QLabel, QComboBox, \
    QCheckBox, QLineEdit, QDialogButtonBox, QSpinBox, QPushButton
from PyQt5.QtCore import Qt, QSize

sys.path.append('../')
import Code.configuration as cf
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

from . import DataImport
from EditorCode.DataImport import Data
from . import EditorUtilities
from EditorCode.CustomGUI import GenderBox
from EditorCode.multi_select_combo_box import MultiSelectComboBox

class HasModes(object):
    def create_mode_combobox(self):
        self.mode_box = MultiSelectComboBox()
        mode_names = list(mode['name'] for mode in GC.DIFFICULTYDATA.values())
        for mode_name in mode_names:
            self.mode_box.addItem(mode_name)
        self.mode_box.setCurrentTexts(mode_names)
        self.form.addRow('Modes:', self.mode_box)

    def populate_mode(self, unit):
        self.mode_box.ResetSelection()
        self.mode_box.setCurrentTexts(unit.mode)

    def get_modes(self):
        return self.mode_box.currentText()

class LoadUnitDialog(QDialog, HasModes):
    def __init__(self, instruction, parent):
        super(LoadUnitDialog, self).__init__(parent)
        self.form = QFormLayout(self)
        self.form.addRow(QLabel(instruction))

        self.create_menus()

    def create_menus(self):
        # Team
        self.team_box = QComboBox()
        self.team_box.uniformItemSizes = True
        for team in DataImport.teams:
            self.team_box.addItem(team)
        self.team_box.currentTextChanged.connect(self.team_changed)
        self.form.addRow('Team:', self.team_box)

        # Unit Select
        self.unit_box = QComboBox()
        self.unit_box.uniformItemSizes = True
        self.unit_box.setIconSize(QSize(32, 32))
        self.unit_data = list(Data.unit_data.values())
        for idx, unit in enumerate(self.unit_data):
            if unit.image:
                self.unit_box.addItem(EditorUtilities.create_icon(unit.image), unit.id)
            else:
                self.unit_box.addItem(unit.id)
        self.form.addRow(self.unit_box)

        # Saved
        self.saved_checkbox = QCheckBox('Load from last level?')
        self.form.addRow(self.saved_checkbox)

        # AI
        self.ai_select = QComboBox()
        self.ai_select.uniformItemSizes = True
        for ai_name in GC.AIDATA:
            self.ai_select.addItem(ai_name)
        self.form.addRow('Select AI:', self.ai_select)

        # AI Group
        self.ai_group = QLineEdit()
        self.form.addRow('AI Group:', self.ai_group)

        self.create_mode_combobox()

        self.ai_select.setEnabled(str(self.team_box.currentText()) != 'player')
        self.ai_group.setEnabled(str(self.team_box.currentText()) != 'player')

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def load(self, unit):
        EditorUtilities.setComboBox(self.unit_box, unit.id)
        EditorUtilities.setComboBox(self.team_box, unit.team)
        self.saved_checkbox.setChecked(unit.saved)
        EditorUtilities.setComboBox(self.ai_select, unit.ai)
        if unit.ai_group:
            self.ai_group.setText(str(unit.ai_group))
        self.populate_mode(unit)

    def team_changed(self, item):
        self.saved_checkbox.setEnabled(str(item) == 'player')
        self.ai_select.setEnabled(str(item) != 'player')
        self.ai_group.setEnabled(str(item) != 'player')

    def get_ai(self):
        return str(self.ai_select.currentText()) if self.ai_select.isEnabled() else 'None'

    def get_team(self):
        return str(self.team_box.currentText())

    @staticmethod
    def getUnit(parent, title, instruction, current_unit=None):
        dialog = LoadUnitDialog(instruction, parent)
        if current_unit:
            dialog.load(current_unit)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            unit = list(Data.unit_data.values())[dialog.unit_box.currentIndex()]
            unit.team = dialog.get_team()
            unit.ai = dialog.get_ai()
            unit.saved = bool(dialog.saved_checkbox.isChecked())
            unit.ai_group = dialog.ai_group.text()
            unit.mode = dialog.get_modes()
            return unit, True
        else:
            return None, False

class ReinLoadUnitDialog(LoadUnitDialog):
    def __init__(self, instruction, parent):
        super(LoadUnitDialog, self).__init__(parent)
        self.form = QFormLayout(self)
        self.form.addRow(QLabel(instruction))

        # Pack
        self.pack = QLineEdit(parent.current_pack())
        self.form.addRow('Group:', self.pack)

        self.create_menus()

    def load(self, unit):
        EditorUtilities.setComboBox(self.unit_box, unit.id)
        EditorUtilities.setComboBox(self.team_box, unit.team)
        self.saved_checkbox.setChecked(unit.saved)
        print(unit.ai)
        EditorUtilities.setComboBox(self.ai_select, unit.ai)
        if unit.ai_group:
            self.ai_group.setText(str(unit.ai_group))
        if unit.pack:
            self.pack.setText(unit.pack)
        self.populate_mode(unit)

    @staticmethod
    def getUnit(parent, title, instruction, current_unit=None):
        dialog = ReinLoadUnitDialog(instruction, parent)
        if current_unit:
            dialog.load(current_unit)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            unit = list(Data.unit_data.values())[dialog.unit_box.currentIndex()]
            unit.team = dialog.get_team()
            unit.ai = dialog.get_ai()
            unit.saved = bool(dialog.saved_checkbox.isChecked())
            unit.ai_group = str(dialog.ai_group.text())
            unit.mode = dialog.get_modes()
            unit.pack = str(dialog.pack.text())
            same_pack = [rein for rein in parent.unit_data.reinforcements if rein.pack == unit.pack and
                         any(mode in unit.mode for mode in rein.mode)]
            unit.event_id = EditorUtilities.next_available_event_id(same_pack, unit)
            return unit, True
        else:
            return None, False

class CreateUnitDialog(QDialog, HasModes):
    def __init__(self, instruction, unit_data, parent):
        super(CreateUnitDialog, self).__init__(parent)
        self.form = QFormLayout(self)
        self.form.addRow(QLabel(instruction))
        self.unit_data = unit_data

        self.create_menus()

    def create_menus(self):
        # Team
        self.team_box = QComboBox()
        self.team_box.uniformItemSizes = True
        for team in DataImport.teams:
            self.team_box.addItem(team)
        self.team_box.activated.connect(self.team_changed)
        self.form.addRow('Team:', self.team_box)

        # Class
        self.class_box = QComboBox()
        self.class_box.uniformItemSizes = True
        self.class_box.setIconSize(QSize(48, 32))
        for klass in Data.class_data.values():
            self.class_box.addItem(EditorUtilities.create_icon(klass.get_image('player', 0)), klass.name)
        self.form.addRow('Class:', self.class_box)

        # Level
        self.level = QSpinBox()
        self.level.setMinimum(1)
        self.form.addRow('Level:', self.level)

        # Gender
        self.gender = GenderBox(self)
        self.form.addRow('Gender:', self.gender)

        # Items
        item_grid = self.set_up_items()
        self.form.addRow('Items: ', item_grid)   

        # AI
        self.ai_select = QComboBox()
        self.ai_select.uniformItemSizes = True
        for ai_name in GC.AIDATA:
            self.ai_select.addItem(ai_name)
        self.form.addRow('AI:', self.ai_select)

        # AI Group
        self.ai_group = QLineEdit()
        self.form.addRow('AI Group:', self.ai_group)

        self.ai_select.setEnabled(str(self.team_box.currentText()) != 'player')
        self.ai_group.setEnabled(str(self.team_box.currentText()) != 'player')

        # Faction
        self.faction_select = QComboBox()
        self.faction_select.uniformItemSizes = True
        self.faction_select.setIconSize(QSize(32, 32))
        for faction_name, faction in self.unit_data.factions.items():
            image = GC.UNITDICT.get(faction.faction_icon + 'Emblem')
            if image:
                self.faction_select.addItem(EditorUtilities.create_icon(image.convert_alpha()), faction.faction_id)
            else:
                self.faction_select.addItem(faction.faction_id)

        self.form.addRow('Faction:', self.faction_select)

        self.create_mode_combobox()

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def load(self, unit):
        EditorUtilities.setComboBox(self.faction_select, unit.faction)
        self.level.setValue(unit.level)
        self.gender.setValue(unit.gender)
        EditorUtilities.setComboBox(self.team_box, unit.team)
        EditorUtilities.setComboBox(self.class_box, unit.klass)
        EditorUtilities.setComboBox(self.ai_select, unit.ai)
        if unit.ai_group:
            self.ai_group.setText(str(unit.ai_group))
        # === Items ===
        self.clear_item_box()
        for index, item in enumerate(unit.items):
            self.add_item_box()
            item_box, drop_box, event_box = self.item_boxes[index]
            drop_box.setChecked(item.droppable)
            event_box.setChecked(item.event_combat)
            item_box.setCurrentIndex(list(Data.item_data.keys()).index(item.id))
        # === Mode ===
        self.populate_mode(unit)

        self.team_changed(0)
        self.gender_changed(unit.gender)

    def set_up_items(self):
        item_grid = QGridLayout()
        self.add_item_button = QPushButton('Add Item')
        self.add_item_button.clicked.connect(self.add_item_box)
        self.remove_item_button = QPushButton('Remove Item')
        self.remove_item_button.clicked.connect(self.remove_item_box)

        self.item_boxes = []
        for num in range(cf.CONSTANTS['max_items']):
            self.item_boxes.append((self.create_item_combo_box(), QCheckBox(), QCheckBox()))
        for index, item in enumerate(self.item_boxes):
            item_box, drop, event = item
            item_grid.addWidget(item_box, index + 1, 0, 1, 2, Qt.AlignTop)
            item_grid.addWidget(drop, index + 1, 2, Qt.AlignTop)
            item_grid.addWidget(event, index + 1, 3, Qt.AlignTop)

        item_grid.addWidget(QLabel('Name:'), 0, 0, 1, 2, Qt.AlignTop)
        item_grid.addWidget(QLabel('Drop?'), 0, 2, Qt.AlignTop)
        item_grid.addWidget(QLabel('Event?'), 0, 3, Qt.AlignTop)
        item_grid.addWidget(self.add_item_button, cf.CONSTANTS['max_items'] + 2, 0, 1, 2, Qt.AlignBottom)
        item_grid.addWidget(self.remove_item_button, cf.CONSTANTS['max_items'] + 2, 2, 1, 2, Qt.AlignBottom)
        self.clear_item_box()
        return item_grid

    # Item functions
    def clear_item_box(self):
        for index, (item_box, drop, event) in enumerate(self.item_boxes):
            item_box.hide(); drop.hide(); event.hide()
        self.num_items = 0
        self.remove_item_button.setEnabled(False)

    def add_item_box(self):
        self.num_items += 1
        self.remove_item_button.setEnabled(True)
        item_box, drop, event = self.item_boxes[self.num_items - 1]
        item_box.show(); drop.show(); event.show()
        if self.num_items >= cf.CONSTANTS['max_items']:
            self.add_item_button.setEnabled(False)

    def remove_item_box(self):
        self.num_items -= 1
        self.add_item_button.setEnabled(True)
        item_box, drop, event = self.item_boxes[self.num_items]
        item_box.hide(); drop.hide(); event.hide()
        if self.num_items <= 0:
            self.remove_item_button.setEnabled(False)

    def create_item_combo_box(self):
        item_box = QComboBox()
        item_box.uniformItemSizes = True
        item_box.setIconSize(QSize(16, 16))
        for item in Data.item_data.values():
            if item.image:
                item_box.addItem(EditorUtilities.create_icon(item.image), item.name)
            else:
                item_box.addItem(item.name)
        return item_box

    def getItems(self):
        items = []
        for index, (item_box, drop_box, event_box) in enumerate(self.item_boxes[:self.num_items]):
            item = list(Data.item_data.values())[item_box.currentIndex()]
            item.droppable = drop_box.isChecked()
            item.event_combat = event_box.isChecked()
            items.append(item)
        return items

    def team_changed(self, idx):
        # Change class box to use sprites of that team
        # And also turn off AI
        team = str(self.team_box.currentText())
        print("Team changed to %s" % team)
        self.ai_select.setEnabled(team != 'player')
        self.ai_group.setEnabled(team != 'player')
        for idx, klass in enumerate(Data.class_data.values()):
            gender = int(self.gender.value())
            self.class_box.setItemIcon(idx, EditorUtilities.create_icon(klass.get_image(team, gender)))

    def gender_changed(self, item):
        gender = int(item)
        print("Gender changed to %s" % gender)
        for idx, klass in enumerate(Data.class_data.values()):
            team = str(self.team_box.currentText())
            self.class_box.setItemIcon(idx, EditorUtilities.create_icon(klass.get_image(team, gender)))

    def get_ai(self):
        return str(self.ai_select.currentText()) if self.ai_select.isEnabled() else 'None'

    def create_unit(self, current_unit=None):
        info = {}
        info['faction'] = str(self.faction_select.currentText())
        faction = self.unit_data.factions[info['faction']]
        if faction:
            info['name'] = faction.unit_name
            info['faction_icon'] = faction.faction_icon
            info['desc'] = faction.desc
        info['level'] = int(self.level.value())
        info['gender'] = int(self.gender.value())
        info['klass'] = str(self.class_box.currentText())
        info['items'] = self.getItems()
        info['ai'] = self.get_ai()
        info['ai_group'] = str(self.ai_group.text())
        info['team'] = str(self.team_box.currentText())
        info['generic'] = True
        info['mode'] = self.get_modes()
        created_unit = DataImport.Unit(info)
        return created_unit

    def modify_current_unit(self, unit):
        unit.faction = str(self.faction_select.currentText())
        faction = self.unit_data.factions[unit.faction]
        if faction:
            unit.name = faction.unit_name
            unit.faction_icon = faction.faction_icon
            unit.desc = faction.desc
        unit.level = int(self.level.value())
        unit.gender = int(self.gender.value())
        unit.klass = str(self.class_box.currentText())
        unit.items = self.getItems()
        unit.ai = self.get_ai()
        unit.ai_group = str(self.ai_group.text())
        unit.team = str(self.team_box.currentText())
        unit.generic = True
        unit.mode = self.get_modes()
        return unit

    @classmethod
    def getUnit(cls, parent, title, instruction, current_unit=None):
        dialog = cls(instruction, parent.unit_data, parent)
        if current_unit:
            dialog.load(current_unit)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            unit = dialog.create_unit(current_unit)
            return unit, True
        else:
            return None, False

class ReinCreateUnitDialog(CreateUnitDialog):
    def __init__(self, instruction, unit_data, parent):
        super(CreateUnitDialog, self).__init__(parent)
        self.form = QFormLayout(self)
        self.form.addRow(QLabel(instruction))
        self.unit_data = unit_data

        # Pack
        self.pack = QLineEdit(parent.current_pack())
        self.form.addRow('Pack:', self.pack)

        self.create_menus()

    def load(self, unit):
        EditorUtilities.setComboBox(self.faction_select, unit.faction)
        self.level.setValue(unit.level)
        self.gender.setValue(unit.gender)
        EditorUtilities.setComboBox(self.team_box, unit.team)
        EditorUtilities.setComboBox(self.class_box, unit.klass)
        EditorUtilities.setComboBox(self.ai_select, unit.ai)
        if unit.ai_group:
            self.ai_group.setText(str(unit.ai_group))
        if unit.pack:
            self.pack.setText(unit.pack)
        # === Items ===
        self.clear_item_box()
        for index, item in enumerate(unit.items):
            self.add_item_box()
            item_box, drop_box, event_box = self.item_boxes[index]
            drop_box.setChecked(item.droppable)
            event_box.setChecked(item.event_combat)
            item_box.setCurrentIndex(list(Data.item_data.keys()).index(item.id))
        self.populate_mode(unit)

        self.team_changed(0)
        self.gender_changed(unit.gender)

    def create_unit(self, current_unit=None):
        info = {}
        info['faction'] = str(self.faction_select.currentText())
        faction = self.unit_data.factions[info['faction']]
        if faction:
            info['name'] = faction.unit_name
            info['faction_icon'] = faction.faction_icon
            info['desc'] = faction.desc
        info['level'] = int(self.level.value())
        info['gender'] = int(self.gender.value())
        info['klass'] = str(self.class_box.currentText())
        info['items'] = self.getItems()
        info['ai'] = self.get_ai()
        info['ai_group'] = str(self.ai_group.text())
        info['mode'] = self.get_modes()
        info['pack'] = str(self.pack.text())
        pack_mates = [rein for rein in self.unit_data.reinforcements if rein.pack == info['pack'] and
                      any(mode in info['mode'] for mode in rein.mode)]
        info['event_id'] = EditorUtilities.next_available_event_id(pack_mates, current_unit)
        info['team'] = str(self.team_box.currentText())
        info['generic'] = True
        
        created_unit = DataImport.Unit(info)
        return created_unit

    def modify_current_unit(self, unit):
        unit.faction = str(self.faction_select.currentText())
        faction = self.unit_data.factions[unit.faction]
        if faction:
            unit.name = faction.unit_name
            unit.faction_icon = faction.faction_icon
            unit.desc = faction.desc
        unit.level = int(self.level.value())
        unit.gender = int(self.gender.value())
        unit.klass = str(self.class_box.currentText())
        unit.items = self.getItems()
        unit.ai = self.get_ai()
        unit.ai_group = str(self.ai_group.text())
        unit.mode = self.get_modes()
        unit.pack = str(self.pack.text())
        pack_mates = [rein for rein in self.unit_data.reinforcements if rein.pack == unit.pack and
                      any(mode in unit.mode for mode in rein.mode)]
        unit.event_id = EditorUtilities.next_available_event_id(pack_mates, unit)
        unit.team = str(self.team_box.currentText())
        unit.generic = True
        
        return unit
