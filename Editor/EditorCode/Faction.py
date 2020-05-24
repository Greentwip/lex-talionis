import sys

from PyQt5.QtWidgets import QDialog, QLabel, QFormLayout, QLineEdit, QComboBox, QTextEdit
from PyQt5.QtWidgets import QDialogButtonBox, QDialog, QWidget, QGridLayout, QPushButton, QListWidgetItem
from PyQt5.QtCore import Qt, QSize

sys.path.append('../')
import Code.Engine as Engine
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

from . import EditorUtilities
from EditorCode.CustomGUI import SignalList

all_faction_icons = [key[:-6] for key in GC.UNITDICT if key.endswith('Emblem')]

class Faction(object):
    def __init__(self, faction_id, unit_name, faction_icon, desc):
        self.faction_id = faction_id
        self.unit_name = unit_name
        self.faction_icon = faction_icon
        self.desc = desc

class FactionDialog(QDialog):
    def __init__(self, instruction, faction=None, parent=None):
        super(FactionDialog, self).__init__(parent)
        self.form = QFormLayout(self)
        self.form.addRow(QLabel(instruction))

        self.id_line_edit = QLineEdit()
        self.unit_name_line_edit = QLineEdit()
        self.faction_icon_box = QComboBox()
        self.faction_icon_box.setIconSize(QSize(32, 32))
        self.desc_text_edit = QTextEdit()
        self.desc_text_edit.setFixedHeight(48)

        for faction_icon in all_faction_icons:
            self.faction_icon_box.addItem(EditorUtilities.create_icon(GC.UNITDICT[faction_icon + "Emblem"].convert_alpha()), faction_icon)

        if faction:
            self.id_line_edit.setText(faction.faction_id)
            self.unit_name_line_edit.setText(faction.unit_name)
            if faction.faction_icon in all_faction_icons:
                self.faction_icon_box.setCurrentIndex(all_faction_icons.index(faction.faction_icon))
            else:
                self.faction_icon_box.setCurrentIndex(all_faction_icons.index('Neutral'))
            self.desc_text_edit.setPlainText(faction.desc)

        self.form.addRow("Faction ID:", self.id_line_edit)
        self.form.addRow("Unit Name:", self.unit_name_line_edit)
        self.form.addRow("Faction Icon:", self.faction_icon_box)
        self.form.addRow("Description:", self.desc_text_edit)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def build_faction(self):
        return Faction(str(self.id_line_edit.text()), str(self.unit_name_line_edit.text()),
                       str(self.faction_icon_box.currentText()), str(self.desc_text_edit.toPlainText()))

    @staticmethod
    def getFaction(parent, title, instruction, faction=None):
        dialog = FactionDialog(instruction, faction, parent)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        faction_obj = dialog.build_faction()
        return faction_obj, result == QDialog.Accepted

class FactionMenu(QWidget):
    def __init__(self, unit_data, view, window=None):
        super(FactionMenu, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window
        self.view = view

        # self.load_player_characters = QCheckBox('Load saved player characters?')
        # self.load_player_characters.stateChanged.connect(self.set_load_player_characters)

        self.list = SignalList(self, del_func=self.remove_faction)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QSize(32, 32))

        self.unit_data = unit_data
        self.load(unit_data)

        self.list.itemDoubleClicked.connect(self.modify_faction)

        self.add_faction_button = QPushButton('Add Faction')
        self.add_faction_button.clicked.connect(self.add_faction)
        self.remove_faction_button = QPushButton('Remove Faction')
        self.remove_faction_button.clicked.connect(self.remove_faction)

        # self.grid.addWidget(self.load_player_characters, 0, 0)
        self.grid.addWidget(self.list, 1, 0)
        self.grid.addWidget(self.add_faction_button, 2, 0)
        self.grid.addWidget(self.remove_faction_button, 3, 0)

    def create_item(self, faction):
        item = QListWidgetItem(faction.faction_id)

        image = GC.UNITDICT.get(faction.faction_icon + 'Emblem')
        if image:
            image = image.convert_alpha()
            item.setIcon(EditorUtilities.create_icon(image))

        return item

    def add_faction(self):
        faction_obj, ok = FactionDialog.getFaction(self, "Factions", "Enter New Faction Values:")
        if ok:
            self.list.addItem(self.create_item(faction_obj))
            self.unit_data.factions[faction_obj.faction_id] = faction_obj

    def modify_faction(self, item):
        faction_obj, ok = FactionDialog.getFaction(self, "Factions", "Modify Faction Values:", self.get_current_faction())
        if ok:
            cur_row = self.list.currentRow()
            self.list.takeItem(cur_row)
            self.list.insertItem(cur_row, self.create_item(faction_obj))
            self.unit_data.factions[faction_obj.faction_id] = faction_obj

    def remove_faction(self):
        idx = self.list.currentRow()
        self.list.takeItem(idx)
        del self.unit_data.factions[list(self.unit_data.factions.keys())[idx]]

    # def set_load_player_characters(self, state):
    #     self.unit_data.load_player_characters = bool(state)

    def get_current_faction(self):
        return list(self.unit_data.factions.values())[self.list.currentRow()]

    def load(self, unit_data):
        self.clear()
        self.unit_data = unit_data
        # Ingest Data
        for faction in self.unit_data.factions.values():
            self.list.addItem(self.create_item(faction))
        # self.load_player_characters.setChecked(self.unit_data.load_player_characters)

    def clear(self):
        self.list.clear()
        # self.load_player_characters.setChecked(False)
