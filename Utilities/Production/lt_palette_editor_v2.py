import sys, os
import glob
from PyQt4 import QtGui, QtCore

class MainView(QtGui.QGraphicsView):
    min_scale = 1
    max_scale = 5

    def __init__(self, window=None):
        QtGui.QGraphicsView.__init__(self)
        self.window = window
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMouseTracking(True)

        self.image = None
        self.screen_scale = 1

    def set_image(self, image_map, palette):
        # TODO generate image from palette (pixel by pixel)
        image = None
        self.image = QtGui.QImage(image)
        self.image = self.image.convertToFormat(QtGui.QImage.Format_ARGB32)
        self.setSceneRect(0, 0, self.image.width(), self.image.height())

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.image:
            self.clear_scene()
            self.scene.addPixmap(QtGui.QPixmap.fromImage(self.image))

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        image = pixmap.pixmap().toImage()
        pos = int(scene_pos.x()), int(scene_pos.y())

        if event.button() == QtCore.Qt.LeftButton:
            dlg = QtGui.QColorDialog()
            dlg.setCurrentColor(QtGui.QColor(image.pixel(pos[0], pos[1])))
            if dlg.exec_():
                self.window.change_palette(pos, dlg.currentColor())

    def wheelEvent(self, event):
        if event.delta() > 0 and self.screen_scale < self.max_scale:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.delta() < 0 and self.screen_scale > self.min_scale:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

class ImageMap(object):
    def __init__(self, image_filename):
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

class ImageMapList(object):
    def __init__(self):
        self.list = []
        self.current_index = 0

    def get_current_map(self):
        return self.list[self.current_index]

    def set_current_map(self, weapon_name):
        for idx, image_map in enumerate(self.list):
            if image_map.weapon_name == weapon_name:
                self.current_index = idx

    def get_available_weapons(self):
        return [image_map.weapon_name for image_map in self.list]

    def add_map_from_image(self, image_filename):
        self.list.append(ImageMap(image_filename))

    def clear(self):
        self.list = []
        self.current_index = 0

class ColorDisplay(QtGui.QPushButton):
    colorChanged = QtCore.pyqtSignal(int, QtGui.QColor)

    def __init__(self, idx, window):
        super(ColorDisplay, self).__init__(window)
        self.window = window
        self.idx = idx
        self._color = None

        self.setMinimumHeight(16)
        self.setMaximumHeight(16)
        self.setMinimumWidth(16)
        self.setMaximumWidth(16)
        self.resize(16, 16)
        self.pressed.connect(self.onColorPicker)

    def set_color(self, color):
        if color != self._color:
            self.colorChanged.emit(self.idx, QtGui.QColor(color))
            self._color = color

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        dlg = QtGui.QColorDialog()
        if self._color:
            dlg.setCurrentColor(QtGui.QColor(self._color))
        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.RightButton:
            self.setColor(QtGui.QtColor("black").name())

        return super(ColorDisplay, self).mousePressEvent(e)

class PaletteDisplay(QtGui.QWidget):
    def __init__(self, colors, window):
        super(PaletteDisplay, self).__init__(window)
        self.window = window
        self.main_editor = self.window.window.window
        self.color_list = colors

        self.color_display_list = []

        self.layout = QtGui.QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        for idx, color in enumerate(self.color_list):
            color_display = ColorDisplay(idx, self)
            color_display.set_color(color.name())
            # TODO figure out what this needs to connect to
            color_display.colorChanged.connect(self.main_editor.update_view)
            self.layout.addWidget(color_display, 0, QtCore.Qt.AlignCenter)
            self.color_display_list.append(color_display)

    def set_color(self, idx, color):
        self.color_display_list[idx].set_color(color.name())

class PaletteFrame(QtGui.QWidget):
    def __init__(self, idx, image_filename=None, window=None):
        super(PaletteFrame, self).__init__(window)
        self.window = window

        self.idx = idx
        if image_filename:
            self.name = image_filename[:-4].split('-')[-1]
            palette = self.get_palette_from_image(image_filename)

            self.create_widgets(palette)

    def create_widgets(self, palette):
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)

        radio_button = QtGui.QRadioButton()
        window.radio_button_group.addButton(radio_button, self.idx)
        radio_button.clicked.connect(lambda: window.set_current_palette(self.idx))
        self.name_label = QtGui.QLabel(self.name)
        copy = QtGui.QPushButton("Duplicate")
        copy.clicked.connect(lambda: window.duplicate(self.idx))
        self.palette_display = PaletteDisplay(palette, window)
        layout.addWidget(radio_button)
        layout.addWidget(self.name_label)
        layout.addWidget(self.palette_display)
        layout.addWidget(copy)

    def set_name(self, name):
        self.name_label.setText(name)

    def set_color(self, idx, color):
        self.palette_display.set_color(idx, color)

    def get_palette_from_image(self, fn):
        colors = []
        pixmap = QtGui.QPixmap(fn)
        image = pixmap.toImage()
        for x in range(image.width()):
            for y in range(image.height()):
                color = QtGui.QColor(image.pixel(x, y))
                if color not in colors:
                    colors.append(color)
        return colors

    @classmethod
    def from_palette(cls, new_idx, palette_frame, window):
        p = cls(new_idx, None, window)
        p.name = palette_frame.name
        color_list = palette_frame.palette_display.color_list
        p.create_widgets(color_list)
        return p

class PaletteList(QtGui.QListWidget):
    def __init__(self, image_filenames, window=None):
        super(PaletteList, self).__init__(window)
        self.window = window

        self.list = []
        self.current_index = 0
        self.radio_button_group = QtGui.QButtonGroup()

        for idx, fn in enumerate(image_filenames):
            self.add_palette_from_image(idx, fn)

    def add_palette_from_image(self, idx, image_filename):
        item = QtGui.QListWidgetItem(self)
        self.addItem(item)
        pf = PaletteFrame(idx, image_filename, self)
        self.list.append(pf)
        item.setSizeHint(pf.minimumSizeHint())
        self.setItemWidget(item, pf)

    def duplicate(self, idx):
        new_idx = len(self.list) - 1
        item = QtGui.QListWidgetItem(self)
        self.addItem(item)
        new_pf = PaletteFrame.from_palette(new_idx, self.list[idx], self)
        self.list.append(new_pf)
        item.setSizeHint(new_pf.minimumSizeHint())
        self.setItemWidget(item, new_pf)

    def set_current_palette(self, idx):
        self.current_index = idx
        self.radio_button_group.button(idx).setChecked(True)

    def get_current_palette(self):
        return self.list[self.current_index]

    def get_palette(self, idx):
        return self.list[idx]

    def clear(self):
        for l in self.list:
            l.deleteLater()
        self.list = []
        self.current_index = 0

class MainEditor(QtGui.QWidget):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Palette Editor v5.9.0')
        self.setMinimumSize(640, 480)

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.main_view = MainView(self)
        self.menu_bar = QtGui.QMenuBar(self)
        self.palette_list = PaletteList(self)
        self.image_map_list = ImageMapList()
        self.scripts = []

        self.create_menu_bar()

        self.grid.setMenuBar(self.menu_bar)
        self.grid.addWidget(self.main_view, 0, 0)
        self.grid.addWidget(self.palette_list, 0, 1, 2, 1)
        self.info_form = QtGui.QFormLayout()
        self.grid.addLayout(self.info_grid, 1, 0)

        self.create_info_bars()

    def create_menus(self):
        load_class_anim = QtGui.QAction("Load Class Animation...", self, triggered=self.load_class)
        load_single_anim = QtGui.QAction("Load Single Animation...", self, triggered=self.load_single)
        load_image = QtGui.QAction("Load Image...", self, triggered=self.load_image)
        save = QtGui.QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        exit = QtGui.QAction("E&xit...", self, shortcut="Ctrl+Q", triggered=self.close)

        file_menu = QtGui.QMenu("&File", self)
        file_menu.addAction(load_class_anim)
        file_menu.addAction(load_single_anim)
        file_menu.addAction(load_image)
        file_menu.addAction(save)
        file_menu.addAction(exit)

        self.menuBar.addMenu(file_menu)

    def create_info_bars(self):
        self.class_text = QtGui.QLineEdit()
        self.class_text.textChanged.connect(self.class_text_change)
        self.weapon_box = QtGui.QComboBox()
        self.weapon_box.uniformItemSizes = True
        self.weapon_box.activated.connect(self.weapon_changed)
        self.palette_text = QtGui.QLineEdit()
        self.palette_text.textChanged.connect(self.palette_text_change)

        self.play_button = QtGui.QPushButton("View Animations")
        self.play_button.clicked.connect(self.view_animations)
        self.play_button.setEnabled = False

        self.info_form.addRow("Class", self.class_text)
        self.info_form.addRow("Weapon", self.weapon_box)
        self.info_form.addRow("Palette", self.palette_text)
        self.info_form.addRow(self.play_button)

    def view_animations(self):
        pass

    def load_script(self, fn):
        with open(self, fn) as script:
            lines = script.readlines()
        self.scripts.append(lines)

    def clear_info(self):
        self.class_text.setEnabled(True)
        self.class_text.setText('')
        self.weapon_text.setText('')
        self.palette_text.setText('')
        self.image_map_list.clear()
        self.palette_list.clear()
        self.scripts = []

    def class_text_change(self):
        pass

    def palette_text_change(self):
        self.palette_list.get_current_palette().set_name(self.palette_text.text())

    def weapon_changed(self, item):
        self.item_map_list.set_current_map(str(item))
        self.update_view()

    def update_view(self):
        cur_image_map = self.image_map_list.get_current_map()
        cur_palette = self.palette_list.get_current_palette()
        self.main_view.set_image(cur_image_map, cur_palette)
        self.main_view.show_image()

    def get_script_from_index(self, fn):
        script = fn[:-10] + '-Script.txt'
        if os.path.exists(script):
            return script
        return None

    def get_images_from_index(self, fn):
        image_header = fn[:-10]
        images = glob.glob(str(image_header + "-*.png"))
        print(images)
        return images

    def load_class(self):
        # starting_path = QtCore.QDir.currentPath() + '/../Data'
        index_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Class", QtCore.QDir.currentPath(),
                                                       "Index Files (*-Index.txt);;All Files (*)")
        if index_file:
            self.clear_info()
            weapon_index_files = self.get_all_index_files(index_file)
            for index_file in weapon_index_files:  # One for each weapon
                script_file = self.get_script_from_index(index_file)
                image_files = self.get_images_from_index(index_file)
                if image_files:
                    self.load_script(script_file)
                    self.play_button.setEnabled = True
                    self.image_map_list.add_map_from_image(image_files[0])
                    for image_filename in image_files:
                        self.palette_list.add_palette_from_image(image_filename)
            self.palette_text.setText(self.palette_list.get_current_palette().name)
            for weapon in self.image_map_list.get_available_weapons():
                self.weapon_box.addItem(weapon)
            klass_name = os.path.split(image_files[0][:-4])[-1].split('-')[0]  # Klass
            self.class_text.setText(klass_name)
            self.update_view()

    def load_single(self):
        index_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Animation", QtCore.QDir.currentPath(),
                                                       "Index Files (*-Index.txt);;All Files (*)")
        if index_file:
            script_file = self.get_script_from_index(index_file)
            image_files = self.get_images_from_index(index_file)
            if image_files:
                self.clear_info()
                self.load_script(script_file)
                self.play_button.setEnabled = True
                self.image_map_list.add_map_from_image(image_files[0])
                for image_filename in image_files:
                    self.palette_list.add_palette_from_image(image_filename)
                self.palette_text.setText(self.palette_list.get_current_palette().name)
                self.weapon_box.addItem(self.image_map_list.get_current_map().weapon_name)
                klass_name = os.path.split(image_files[0][:-4])[-1].split('-')[0]  # Klass
                self.class_text.setText(klass_name)
                self.update_view()

    def load_image(self):
        image_filename = QtGui.QFileDialog.getOpenFileName(self, "Choose Image PNG", QtCore.QDir.currentPath(),
                                                           "PNG Files (*.png);;All Files (*)")
        if image_filename:
            self.clear_info()
            self.play_button.setEnabled = False
            self.image_map_list.add_map_from_image(image_filename)
            self.palette_list.add_palette_from_image(image_filename)
            self.palette_text.setText(self.palette_list.get_current_palette().name)
            self.class_text.setEnabled(False)
            self.update_view()

    def save(self):
        pass

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = MainEditor()
    window.show()
    app.exec_()
