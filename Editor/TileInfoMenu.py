# Terrain Data Menu
import sys
from collections import OrderedDict
from PyQt4 import QtGui, QtCore

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import EditorUtilities
from CustomGUI import SignalList

info_kinds = {'Status': 'Status',
              'Formation': None,
              'Seize': 'string',
              'Escape': 'string',
              'Arrive': 'string',
              'Shop': 'Item',
              'Village': 'string',
              'Locked': 'string',
              'Switch': 'string',
              'Search': 'string',
              'Thief_Escape': None,
              'Reinforcement': 'string'}

class TileInfoMenu(QtGui.QWidget):
    def __init__(self, view, window=None):
        super(TileInfoMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.view = view

        self.list = SignalList(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QtCore.QSize(32, 32))

        # Ingest Data
        for key, value in info_kinds.iteritems():
            image = Engine.transform_scale(GC.IMAGEDICT['TileInfoIcon_' + key], 2)
            pixmap = EditorUtilities.create_pixmap(image)

            item = QtGui.QListWidgetItem(key)
            item.setIcon(QtGui.QIcon(pixmap))
            self.list.addItem(item)

        self.grid.addWidget(self.list, 0, 0)

        self.update()

    def trigger(self):
        self.view.tool = 'Tile Info'

    def update(self):
        pass

    def new(self):
        pass

    def load(self, overview):
        pass

    def save(self):
        pass
