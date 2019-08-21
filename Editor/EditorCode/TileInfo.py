# Terrain Data Menu
import sys

from PyQt5.QtWidgets import QWidget, QDialog, QFormLayout, QLabel, QInputDialog
from PyQt5.QtWidgets import QDialogButtonBox, QGridLayout, QListWidgetItem
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.Highlight as Highlight

from . import EditorUtilities
from EditorCode.CustomGUI import SignalList, CheckableComboBox
from EditorCode.DataImport import Data

class InfoKind(object):
    def __init__(self, num, name, kind):
        self.num = num
        self.name = name
        self.kind = kind
        self.image = Engine.subsurface(GC.ICONDICT['TileInfoIcons'], (0, num * 16, 16, 16))

info_kinds = [('Status', 'Status'),
              ('Formation', None),
              ('Seize', 'string'),
              ('Lord_Seize', 'string'),
              ('Enemy_Seize', 'string'),
              ('Escape', 'string'),
              ('Arrive', 'string'),
              ('Shop', 'Item'),
              ('Repair', None),
              ('Arena', None),
              ('Village', 'string'),
              ('Destructible', 'string'),
              ('HP', 'int'),
              ('Locked', 'string'),
              ('Switch', 'string'),
              ('Search', 'string'),
              ('Thief_Escape', None),
              ('Reinforcement', 'string')]

kinds = {name: InfoKind(i, name, kind) for i, (name, kind) in enumerate(info_kinds)}

class TileInfo(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.tile_info_dict = dict()
        self.formation_highlights = dict()
        self.escape_highlights = dict()

    def get(self, coord):
        if coord in self.tile_info_dict:
            return self.tile_info_dict[coord]
        else:
            return None

    def get_str(self, coord):
        if coord in self.tile_info_dict and self.tile_info_dict[coord]:
            return ';'.join([(name + '=' + value) for name, value in self.tile_info_dict[coord].items()])
        else:
            return None

    def set(self, coord, name, value):
        if coord not in self.tile_info_dict:
            self.tile_info_dict[coord] = {}
        self.tile_info_dict[coord][str(name)] = str(value)

    def delete(self, coord):
        self.tile_info_dict[coord] = {}

    def load(self, tile_info_location):
        self.clear()
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
            if property_name in ("Escape", "Arrive"):
                self.escape_highlights[coord] = Highlight.Highlight(GC.IMAGESDICT["YellowHighlight"])
            elif property_name == "Formation":
                self.formation_highlights[coord] = Highlight.Highlight(GC.IMAGESDICT["BlueHighlight"])
            self.tile_info_dict[coord][property_name] = property_value

    def get_images(self):
        image_coords = {}
        # Returns a dictionary of coordinates mapped to images to display
        for coord, properties in self.tile_info_dict.items():
            for name, value in properties.items():
                image_coords[coord] = EditorUtilities.ImageWidget(kinds[name].image).image
        return image_coords

class ComboDialog(QDialog):
    def __init__(self, instruction, items, item_list=None, parent=None):
        super(ComboDialog, self).__init__(parent)
        self.form = QFormLayout(self)
        self.form.addRow(QLabel(instruction))

        self.items = items
        if item_list is None:
            item_list = []

        # Create item combo box
        self.item_box = CheckableComboBox()
        self.item_box.uniformItemSizes = True
        self.item_box.setIconSize(QSize(16, 16))
        for idx, item in enumerate(self.items.values()):
            if item.image:
                self.item_box.addItem(EditorUtilities.create_icon(item.image), item.id)
            else:
                self.item_box.addItem(item.id)
            row = self.item_box.model().item(idx, 0)
            if item.id in item_list:
                row.setCheckState(Qt.Checked)
            else:
                row.setCheckState(Qt.Unchecked)
        self.form.addRow(self.item_box)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def getCheckedItems(self):
        item_list = []
        for idx, item in enumerate(self.items):
            row = self.item_box.model().item(idx, 0)
            if row.checkState() == Qt.Checked:
                item_list.append(item)
        return item_list

    @staticmethod
    def getItems(parent, title, instruction, items, item_list=[]):
        dialog = ComboDialog(instruction, items, item_list, parent)
        dialog.setWindowTitle(title)
        result = dialog.exec_()
        items = dialog.getCheckedItems()
        return items, result == QDialog.Accepted

class TileInfoMenu(QWidget):
    def __init__(self, view, window=None):
        super(TileInfoMenu, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.view = view

        self.list = SignalList(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QSize(32, 32))

        # Ingest Data
        self.info = sorted(kinds.values(), key=lambda x: x.num)
        for info in self.info:
            image = Engine.transform_scale(info.image, (32, 32))
            pixmap = EditorUtilities.create_pixmap(image)

            item = QListWidgetItem(info.name)
            item.setIcon(QIcon(pixmap))
            self.list.addItem(item)

        self.grid.addWidget(self.list, 0, 0)

    # def trigger(self):
    #     self.view.tool = 'Tile Info'

    def start_dialog(self, tile_info_at_pos):
        kind = self.info[self.list.currentRow()].kind
        if kind == 'Status':
            current_statuses = tile_info_at_pos.get('Status') if tile_info_at_pos else None
            current_statuses = current_statuses.split(',') if current_statuses else None
            statuses, ok = ComboDialog.getItems(self, "Tile Status Effects", "Select Status:", Data.skill_data, current_statuses)
            if ok:
                return ','.join(statuses)
            else:
                return None
        elif kind == 'Item':
            current_shop = tile_info_at_pos.get('Shop') if tile_info_at_pos else None
            current_shop = current_shop.split(',') if current_shop else None
            items, ok = ComboDialog.getItems(self, "Shop Items", "Select Items:", Data.item_data, current_shop)
            if ok:
                return ','.join(items)
            else:
                return None
        elif kind == 'string':
            text, ok = QInputDialog.getText(self, self.get_current_name(), 'Enter ID to use:')
            if ok:
                return text
            else:
                return None
        elif kind == 'int':
            text, ok = QInputDialog.getInt(self, self.get_current_name(), 'Set Starting HP:', 10, 0)
            if ok:
                return text
            else:
                return None
        else:  # None
            return '0'

    def get_current_name(self):
        return self.info[self.list.currentRow()].name
