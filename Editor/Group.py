import sys
from PyQt4 import QtGui, QtCore

sys.path.append('../')
import Code.Engine as Engine
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import EditorUtilities
from CustomGUI import SignalList

class Group(object):
    def __init__(self, group_id, unit_name, faction, desc):
        self.group_id = group_id
        self.unit_name = unit_name
        self.faction = faction
        self.desc = desc

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

        self.list = SignalList(self, del_func=self.remove_group)
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
