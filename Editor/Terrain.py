# Terrain Data Menu
from collections import OrderedDict
from PyQt4 import QtGui, QtCore

from CustomGUI import SignalList

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

class TerrainMenu(QtGui.QWidget):
    def __init__(self, terrain_data, view, window=None):
        super(TerrainMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.view = view

        self.list = SignalList(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QtCore.QSize(32, 32))

        # Saved dictionary of terrains 2-tuple {color: (id, name)}
        self.terrain = OrderedDict()
        # Ingest terrain_data
        for terrain in terrain_data.getroot().findall('terrain'):
            color = tuple(int(num) for num in terrain.find('color').text.split(','))
            tid = terrain.find('id').text
            name = terrain.get('name')
            self.terrain[color] = (tid, name)

            pixmap = QtGui.QPixmap(32, 32)
            pixmap.fill(QtGui.QColor(color[0], color[1], color[2]))

            item = QtGui.QListWidgetItem(tid + ': ' + name)
            item.setIcon(QtGui.QIcon(pixmap))
            self.list.addItem(item)

        self.grid.addWidget(self.list, 0, 0)

    def get_current_color(self):
        color = self.terrain.keys()[self.list.currentRow()]
        print(color)
        return color

    def set_current_color(self, color):
        idx = self.terrain.keys().index(color)
        self.list.setCurrentRow(idx)

    def get_info(self, color):
        return self.terrain[color]

    def get_info_str(self, color):
        tid, name = self.terrain[color]
        return str(tid) + " - " + str(name)

    def trigger(self):
        self.view.tool = 'Terrain'
