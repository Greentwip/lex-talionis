from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QImage, QPixmap, QIcon, QPainter

import sys
from itertools import count
sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
# Editor Utilities

# === VIEW AND CONTROLLER METHODS ============================================
class ImageWidget(QWidget):
    def __init__(self, surface, parent=None):
        super(ImageWidget, self).__init__(parent)
        w = surface.get_width()
        h = surface.get_height()
        self.data = surface.get_buffer().raw
        # self.image = QImage(self.data, w, h, QImage.Format_RGB32)
        self.image = QImage(self.data, w, h, QImage.Format_ARGB32)
        self.resize(w, h)

def create_icon(image):
    icon = ImageWidget(image)
    icon = QPixmap(icon.image)
    icon = QIcon(icon)
    return icon

def create_pixmap(image):
    icon = ImageWidget(image)
    icon = QPixmap(icon.image)
    return icon

def create_image(image):
    image = ImageWidget(image)
    return image.image

def create_chibi(name):
    return Engine.subsurface(GC.UNITDICT[name + 'Portrait'], (96, 16, 32, 32)).convert_alpha()

def create_cursor():
    sprite = GC.IMAGESDICT['Cursor']
    # Sprites are in 64 x 64 boxes
    activesprite = Engine.subsurface(sprite, (0, 64, 32, 32)).convert_alpha()
    return create_image(activesprite)

def setOpacity(image, opacity):
    new_img = QImage(image.size(), QImage.Format_ARGB32)
    new_img.fill(Qt.transparent)

    painter = QPainter()
    painter.begin(new_img)
    painter.setOpacity(opacity)
    painter.drawImage(QRect(0, 0, image.width(), image.height()), image)
    painter.end()

    return new_img

def setComboBox(combo_box, value):
    i = combo_box.findText(value)
    if i >= 0:
        combo_box.setCurrentIndex(i)

# === Event ID ===
def next_available_event_id(pack_mates, unit=None):
    if unit and unit in pack_mates:
        pack_mates.remove(unit)
    for num in count(start=1):
        if not any(rein.event_id == num for rein in pack_mates):
            return num

# === MAKE PRETTY ===
def stretch(grid):
    box_h = QHBoxLayout()
    box_h.addStretch(1)
    box_h.addLayout(grid)
    box_h.addStretch(1)
    box_v = QVBoxLayout()
    box_v.addStretch(1)
    box_v.addLayout(box_h)
    box_v.addStretch(1)
    return box_v

def add_line(grid, row):
    line = QFrame()
    line.setFrameStyle(QFrame.HLine)
    line.setLineWidth(0)
    grid.addWidget(line, row, 0)

unit_level_header = """# UnitLevel.txt is used to define what units will be part of this level and where they will spawn
# 
# Each unit belongs on its own line
# Syntax:
# New Units:
# team; 0; event_id; class; level; items; position; ai; faction; status (optional)
# - OR -
# Named units:
# team; 1; event_id; unit_id; position; ai
# - OR -
# Created Units:
# team; 2; event_id; class; items; position; ai; faction; status (optional)
# 
# event_id gives the unit a unique id that scripts can use. The unit will not start on the battlefield unless event_id == 0.
# unit_id - unit to load from the units.xml file
# position should be formatted like #,#
# ai refers to what kind of AI the unit should possess.
#
# --------------------------------------------
"""
