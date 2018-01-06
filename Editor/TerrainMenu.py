# Terrain Data Menu
from PyQt4 import QtGui, QtCore

class TerrainMenu(QtGui.QWidget):
    def __init__(self, terrain_data, window=None):
        super(TerrainMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.list = QtGui.QListWidget(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QtCore.QSize(32, 32))

        # Ingest Data
        for terrain in terrain_data.getroot().findall('terrain'):
            color = terrain.find('color').text.split(',')
            tid = terrain.find('id').text
            name = terrain.get('name')

            pixmap = QtGui.QPixmap(32, 32)
            pixmap.fill(QtGui.QColor(int(color[0]), int(color[1]), int(color[2])))

            item = QtGui.QListWidgetItem(tid + ': ' + name)
            item.setIcon(QtGui.QIcon(pixmap))
            self.list.addItem(item)

        self.grid.addWidget(self.list, 0, 0)

        self.update()

    def update(self):
        pass

    def new(self):
        pass

    def load(self, overview):
        pass

    def save(self):
        pass
