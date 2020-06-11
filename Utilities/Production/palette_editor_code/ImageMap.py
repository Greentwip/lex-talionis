import os

from PyQt5.QtGui import QPixmap, QColor

class ImageMap(object):
    def __init__(self, image_filename):
        self.script = None
        self.index = None
        self.image_filename = image_filename
        self.grid = []
        self.weapon_name = os.path.split(image_filename)[-1].split('-')[-2]
        print(self.weapon_name)
        pixmap = QPixmap(image_filename)
        image = pixmap.toImage()
        self.width, self.height = image.width(), image.height()

        self.colors = []
        for x in range(self.width):
            for y in range(self.height):
                color = QColor(image.pixel(x, y))
                if color not in self.colors:
                    self.colors.append(color)
                self.grid.append(self.colors.index(color))

        for idx, color in enumerate(self.colors):
            print(idx, color.getRgb())

        self.already_reordered = False

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
        if self.already_reordered:
            print("Already Reordered!")
            return
        order_swap = {}
        colors = new_palette.get_colors()
        for idx, color in enumerate(old_palette.get_colors()):
            if color in colors:
                order_swap[idx] = colors.index(color)
            else:
                order_swap[idx] = idx
        print(order_swap)
        self.grid = [order_swap[i] for i in self.grid]
        self.already_reordered = True

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

    def add_map_from_images(self, image_filenames):
        best_image_map = None
        most_colors = 0
        for image_filename in image_filenames:
            image_map = ImageMap(image_filename)
            num_colors = len(image_map.colors)
            if num_colors > most_colors:
                best_image_map = image_map
                most_colors = num_colors
            print(image_filename, num_colors)
        print("best_image_map")
        print(best_image_map.image_filename)
        self.list.append(best_image_map)
        return best_image_map

    def clear(self):
        print('Image Map List clear')
        self.list = []
        self.current_index = 0
