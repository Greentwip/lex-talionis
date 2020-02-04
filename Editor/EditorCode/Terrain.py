import os
# Terrain Data Menu
from PyQt5.QtWidgets import QGridLayout, QWidget, QSlider, QLabel, QListWidgetItem
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QImage, QIcon, QPixmap, QColor

import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'

from EditorCode.DataImport import Data
from EditorCode.CustomGUI import SignalList

class Autotiles(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.autotiles = []
        self.autotile_frame = 0

    def load(self, auto_loc):
        # Auto-tiles
        self.autotile_frame = 0
        if os.path.exists(auto_loc):
            files = sorted([fp for fp in os.listdir(auto_loc) if fp.startswith('autotile') and fp.endswith('.png')], key=lambda x: int(x[8:-4]))
            self.autotiles = [QImage(auto_loc + image) for image in files]
        else:
            self.autotiles = []

    def update(self, current_time):
        time = 483  # 29 ticks
        mod_time = current_time%(len(self.autotiles)*time)
        self.autotile_frame = mod_time//time

    def draw(self):
        if self.autotiles:
            return self.autotiles[self.autotile_frame]
        else:
            return None

    # Python 2
    def __nonzero__(self):
        return bool(self.autotiles)

    # Python 3
    def __bool__(self):
        return bool(self.autotiles)

class TileData(object):
    GRASS_TILE = (192, 224, 48)

    def __init__(self):
        self.tiles = {}
        self.image_file = None
        self.width, self.height = 0, 0

    def clear(self):
        self.tiles = {}

    def get_tile_data(self):
        return self.tiles

    def load(self, tilefp):
        self.clear()
        tiledata = QImage(tilefp)
        colorkey, self.width, self.height = self.build_color_key(tiledata)
        self.populate_tiles(colorkey)

    def new(self, image_file):
        self.clear()
        self.image_file = str(image_file)
        image = QImage(image_file)
        self.width, self.height = image.width() // 16, image.height() // 16

        mapObj = []
        for x in range(self.width):
            mapObj.append([])
        for y in range(self.height):
            for x in range(self.width):
                color = QColor.fromRgb(*self.GRASS_TILE)
                mapObj[x].append((color.red(), color.green(), color.blue()))

        self.populate_tiles(mapObj)

    def build_color_key(self, tiledata):
        width = tiledata.width()
        height = tiledata.height()
        mapObj = [] # Array of map data
    
        # Convert to a mapObj
        for x in range(width):
            mapObj.append([])
        for y in range(height):
            for x in range(width):
                pos = QPoint(x, y)
                color = QColor.fromRgb(tiledata.pixel(pos))
                mapObj[x].append((color.red(), color.green(), color.blue()))

        return mapObj, width, height

    def populate_tiles(self, colorKeyObj):
        for x in range(len(colorKeyObj)):
            for y in range(len(colorKeyObj[x])):
                cur = colorKeyObj[x][y]
                self.tiles[(x, y)] = cur

class TerrainMenu(QWidget):
    def __init__(self, tile_data, view, window=None):
        super(TerrainMenu, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.tile_data = tile_data
        self.window = window

        self.view = view

        self.alpha_slider = QSlider(Qt.Horizontal, self)
        self.alpha_slider.setRange(0, 255)
        self.alpha_slider.setValue(192)
        self.grid.addWidget(QLabel("Transparency"), 0, 0)
        self.grid.addWidget(self.alpha_slider, 0, 1)

        self.list = SignalList(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QSize(32, 32))

        # Ingest terrain_data
        for color, terrain in Data.terrain_data.items():
            tid, name = terrain
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(color[0], color[1], color[2]))

            item = QListWidgetItem(tid + ': ' + name)
            item.setIcon(QIcon(pixmap))
            self.list.addItem(item)

        self.grid.addWidget(self.list, 1, 0, 1, 2)

        self.mouse_down = False
        self.undo_stack = []

    def get_current_color(self):
        color = list(Data.terrain_data.keys())[self.list.currentRow()]
        return color

    def set_current_color(self, color):
        idx = list(Data.terrain_data.keys()).index(color)
        self.list.setCurrentRow(idx)

    def get_info(self, color):
        return Data.terrain_data[color]

    def get_info_str(self, color):
        tid, name = Data.terrain_data[color]
        return str(tid) + " - " + str(name)

    def get_alpha(self):
        return int(self.alpha_slider.value())

    def undo(self):
        if not self.undo_stack:
            return
        last_actions = self.undo_stack.pop()
        for action in last_actions:
            pos, old_color, new_color = action
            self.tile_data.tiles[pos] = old_color
        self.window.update_view()

    def paint(self, pos):
        if not self.mouse_down:  # First pick
            self.undo_stack.append([])
        self.mouse_down = True
        old_color = self.tile_data.tiles[pos]
        new_color = self.get_current_color()
        self.tile_data.tiles[pos] = new_color
        if old_color != new_color:  # Required since updating view each frame is EXPENSIVE!
            self.undo_stack[-1].append((pos, old_color, new_color))
            self.window.update_view()

    def mouse_release(self):
        self.mouse_down = False

    # def trigger(self):
    #     self.view.tool = 'Terrain'
