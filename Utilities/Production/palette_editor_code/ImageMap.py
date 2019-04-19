import os
from PyQt4 import QtGui

class ImageMap(object):
    def __init__(self, image_filename):
        self.script = None
        self.index = None
        self.grid = []
        self.weapon_name = os.path.split(image_filename)[-1].split('-')[-2]
        print(self.weapon_name)
        pixmap = QtGui.QPixmap(image_filename)
        image = pixmap.toImage()
        self.width, self.height = image.width(), image.height()

        colors = []
        for x in range(self.width):
            for y in range(self.height):
                color = QtGui.QColor(image.pixel(x, y))
                if color not in colors:
                    colors.append(color)
                self.grid.append(colors.index(color))

    def get(self, x, y):
        return self.grid[x * self.height + y]

    def load_script(self, fn):
        with open(fn) as script:
            lines = [l.strip().split(';') for l in script.readlines()]
        self.script = lines

    def set_index(self, fn):
        with open(fn) as index:
            lines = [l.strip().split(';') for l in index.readlines()]
        self.index = lines

    def get_script(self):
        return self.script

    def get_index(self):
        return self.index

    def reorder(self, old_palette, new_palette):
        order_swap = {}
        for idx, color in enumerate(old_palette.get_colors()):
            order_swap[idx] = new_palette.get_colors().index(color)
        print(order_swap)
        self.grid = [order_swap[i] for i in self.grid]

class ImageMapList(object):
    def __init__(self):
        self.list = []
        self.current_index = 0

    def get_current_map(self):
        return self.list[self.current_index]

    def set_current_map(self, weapon_name):
        print(weapon_name)
        for idx, image_map in enumerate(self.list):
            if image_map.weapon_name == weapon_name:
                self.current_index = idx
                break
        else:
            print("Couldn't find %s" % weapon_name)
            print(self.get_available_weapons())

    def set_current_idx(self, idx):
        self.current_index = idx

    def get_available_weapons(self):
        return [image_map.weapon_name for image_map in self.list]

    def add_map_from_image(self, image_filename):
        image_map = ImageMap(image_filename)
        self.list.append(image_map)
        return image_map

    def clear(self):
        self.list = []
        self.current_index = 0
