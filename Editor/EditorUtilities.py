from PyQt4 import QtGui
import sys
sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
# Editor Utilities

# === VIEW AND CONTROLLER METHODS ============================================
class ImageWidget(QtGui.QWidget):
    def __init__(self, surface, parent=None, x=0):
        super(ImageWidget, self).__init__(parent)
        w = surface.get_width()
        h = surface.get_height()
        self.data = surface.get_buffer().raw
        self.x = x
        # self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_RGB32)
        self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_ARGB32)
        self.resize(w, h)

def create_icon(image):
    icon = ImageWidget(image)
    icon = QtGui.QPixmap(icon.image)
    icon = QtGui.QIcon(icon)
    return icon

def create_pixmap(image):
    icon = ImageWidget(image)
    icon = QtGui.QPixmap(icon.image)
    return icon

def create_chibi(name):
    return Engine.subsurface(GC.UNITDICT[name + 'Portrait'], (96, 16, 32, 32)).convert_alpha()

# === DATA ===
def find(data, name):
    return next((x for x in data if x.name == name), None)

# === MAKE PRETTY ===
def stretch(grid):
    box_h = QtGui.QHBoxLayout()
    box_h.addStretch(1)
    box_h.addLayout(grid)
    box_h.addStretch(1)
    box_v = QtGui.QVBoxLayout()
    box_v.addStretch(1)
    box_v.addLayout(box_h)
    box_v.addStretch(1)
    return box_v

def add_line(grid, row):
    line = QtGui.QFrame()
    line.setFrameStyle(QtGui.QFrame.HLine)
    line.setLineWidth(0)
    grid.addWidget(line, row, 0)
