import sys, os
import glob
from PyQt4 import QtGui, QtCore

class MainView(QtGui.QGraphicsView):
    def __init__(self, window=None):
        QtGui.QGraphicsView.__init__(self)
        self.window = window
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMouseTracking(True)

        self.image = None

        self.screen_scale = 1

    def set_new_image(self, image):
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
                self.window.change_color(pos, dlg.currentColor())

    def wheelEvent(self, event):
        if event.delta() > 0 and self.screen_scale < 5:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.delta() < 0 and self.screen_scale > 1:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

class ImageMap(object):
    def __init__(self, image_filename):
        self.image_filename = image_filename
        self.image_map = []
        self.orig_colors = []
        pixmap = QtGui.QPixmap(self.image_filename)
        image = pixmap.toImage()
        self.width, self.height = image.width(), image.height()
        for x in range(self.width):
            for y in range(self.height):
                color = QtGui.QColor(image.pixel(x, y))
                if color not in self.orig_colors:
                    self.orig_colors.append(color)
                self.image_map.append(self.orig_colors.index(color))

    def get(self, x, y):
        return self.image_map[x * self.height + y]

class MainEditor(QtGui.QWidget):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Palette Editor v5.9.0')
        self.setMinimumSize(640, 480)

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.view = MainView(self)

        self.menuBar = QtGui.QMenuBar(self)
        self.animation = Animation(self)
        self.palette_editor = PaletteEditor(self)

        self.create_menus()

        self.grid.setMenuBar(self.menuBar)
        self.grid.addWidget(self.view, 0, 0)
        self.grid.addWidget(self.animation, 1, 0)
        self.grid.addWidget(self.palette_editor, 0, 1, 2, 1)

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

        toggle = QtGui.QAction("Toggle # Colors", self, triggered=self.toggle_num_colors)
        copy_hex = QtGui.QAction("Copy Hex", self, triggered=self.copy_hex)

        edit_menu = QtGui.QMenu("&Edit", self)
        edit_menu.addAction(toggle)
        edit_menu.addAction(copy_hex)

        self.menuBar.addMenu(file_menu)
        self.menuBar.addMenu(edit_menu)

    def set_image(self, image_file):
        self.view.clear_scene()
        self.view.set_new_image(image_file)
        self.image_map = ImageMap(image_file)
        self.update_view()

    def change_color(self, pos, color):
        print('MainEditor', 'change color', pos, color)
        palette_idx = self.image_map.get(pos[0], pos[1])
        self.palette_editor.palette_list.get_current_palette().set_color(palette_idx, color)
        print('MainEditor', 'change color', pos, color)
        # self.color_swap(palette_idx, color)

    def update_view(self):
        self.view.show_image()

    def color_swap(self, palette_idx, new_color):
        print('MainEditor', 'color_swap', palette_idx, new_color)
        for x in range(self.view.image.width()):
            for y in range(self.view.image.height()):
                if self.image_map.get(x, y) == palette_idx:
                    self.view.image.setPixel(x, y, new_color.rgb())
        self.update_view()

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

    def get_info(self, image_fn):
        print('MainEditor', 'get_info', image_fn)
        image_name = os.path.split(image_fn[:-4])[-1]
        klass, weapon, palette = image_name.split('-')
        return klass, weapon, palette

    def load_class(self):
        pass

    def load_single(self):
        index_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Animation", QtCore.QDir.currentPath(),
                                                       "Index Files (*-Index.txt);;All Files (*)")
        if index_file:
            script_file = self.get_script_from_index(index_file)
            image_files = self.get_images_from_index(index_file)
            if image_files:
                image_file = image_files[0]
                self.set_image(image_file)
                klass, weapon, palette = self.get_info(image_file)
                self.animation.clear_info()
                self.animation.load_info(klass, weapon, palette)
                self.animation.load_script(script_file)
                self.palette_editor.clear()
                self.palette_editor.load_palettes(image_files)
                self.palette_editor.set_current_palette(0)
                self.animation.set_palette_text()
                # self.update_view()

    def load_image(self):
        image_filename = QtGui.QFileDialog.getOpenFileName(self, "Choose Image PNG", QtCore.QDir.currentPath(),
                                                           "PNG Files (*.png);;All Files (*)")
        if image_filename:
            self.set_image(image_filename)
            self.animation.clear_info()
            self.palette_editor.clear()
            self.palette_editor.load_palettes([image_filename])
            self.palette_editor.set_current_palette(0)
            self.animation.set_palette_text()
            # self.update_view()

    def save(self):
        pass

    def toggle_num_colors(self):
        pass

    def copy_hex(self):
        pass

class Animation(QtGui.QWidget):
    def __init__(self, window=None):
        super(Animation, self).__init__()
        self.window = window

        self.script = None

        self.editable = True
        self.class_text = QtGui.QLineEdit()
        self.class_text.textChanged.connect(self.class_text_change)
        self.weapon_text = QtGui.QLineEdit()
        self.palette_text = QtGui.QLineEdit()
        self.palette_text.textChanged.connect(self.palette_text_change)        

        self.playable = False
        self.play_button = QtGui.QPushButton("View Animations")
        self.play_button.clicked.connect(self.play_animation)
        self.play_button.setEnabled(self.playable)

        self.form = QtGui.QFormLayout(self)
        self.form.addRow("Class", self.class_text)
        self.form.addRow("Weapon", self.weapon_text)
        self.form.addRow("Palette", self.palette_text)
        self.form.addRow(self.play_button)

        self.setLayout(self.form)

    def play_animation(self):
        pass

    def clear_info(self):
        self.class_text.setText('')
        self.weapon_text.setText('')
        self.palette_text.setText('')
        self.editable = True
        self.playable = False

    def class_text_change(self):
        pass

    def palette_text_change(self):
        self.window.palette_editor.set_current_palette_name(self.palette_text.text())

    def load_info(self, c, w, p):
        self.class_text.setText(c)
        self.weapon_text.setText(w)
        self.palette_text.setText(p)
        self.editable = False

    def load_script(self, fn):
        with open(fn) as script:
            lines = script.readlines()
        self.script = lines

        self.playable = True

    def set_palette_text(self, palette=None):
        if palette:
            self.palette_text.setText(palette)
        else:
            self.palette_text.setText('GenericBlue')

class ColorDisplay(QtGui.QPushButton):
    colorChanged = QtCore.pyqtSignal(int, QtGui.QColor)

    def __init__(self, idx, parent=None):
        super(ColorDisplay, self).__init__(parent)
        self.idx = idx
        self._color = None
        self.setMinimumHeight(16)
        self.setMaximumHeight(16)
        self.setMinimumWidth(16)
        self.setMaximumWidth(16)
        self.resize(16, 16)
        self.pressed.connect(self.onColorPicker)

    def setColor(self, color):
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
        self.frame = window
        self.palette_list = self.frame.window
        self.palette_editor = self.palette_list.window
        self.main_editor = self.palette_editor.window

        self.colors = colors
        self.displays = []

        self.layout = QtGui.QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        for idx, color in enumerate(self.colors):
            color_display = ColorDisplay(idx, self)
            color_display.setColor(color.name())
            color_display.colorChanged.connect(self.palette_editor.color_swap)
            self.layout.addWidget(color_display, 0, QtCore.Qt.AlignCenter)
            self.displays.append(color_display)

    def set_color(self, idx, color):
        print('PaletteDisplay', 'set_color', idx, color)
        self.displays[idx].setColor(color.name())

class PaletteFrame(QtGui.QWidget):
    def __init__(self, idx, image_filename, window=None):
        super(PaletteFrame, self).__init__(window)
        self.window = window

        self.idx = idx
        self.full_name = image_filename
        self.name = image_filename[:-4].split('-')[-1]
        self.get_colors()

        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)

        radio_button = QtGui.QRadioButton()
        window.radio_button_group.addButton(radio_button, self.idx)
        radio_button.clicked.connect(lambda: window.set_current_palette(self.idx))
        self.name_label = QtGui.QLabel(self.name)
        copy = QtGui.QPushButton("Duplicate")
        copy.clicked.connect(lambda: window.duplicate(self.idx))
        self.palette_display = PaletteDisplay(self.colors, window)
        layout.addWidget(radio_button)
        layout.addWidget(self.name_label)
        layout.addWidget(self.palette_display)
        layout.addWidget(copy)

    def set_name(self, name):
        self.name_label.setText(name)

    def set_color(self, idx, color):
        self.palette_display.set_color(idx, color)

    def get_colors(self):
        self.colors = []
        pixmap = QtGui.QPixmap(self.full_name)
        image = pixmap.toImage()
        for x in range(image.width()):
            for y in range(image.height()):
                color = QtGui.QColor(image.pixel(x, y))
                if color not in self.colors:
                    self.colors.append(color)

class PaletteList(QtGui.QListWidget):
    def __init__(self, image_filenames, window=None):
        super(PaletteList, self).__init__(window)
        self.window = window

        self.palette_frames = []
        self.current_idx = 0
        self.radio_button_group = QtGui.QButtonGroup()
        
        for idx, fn in enumerate(image_filenames):
            self.add_palette(idx, fn)

    def add_palette(self, idx, image_filename):
        item = QtGui.QListWidgetItem(self)
        self.addItem(item)
        pf = PaletteFrame(idx, image_filename, self)
        self.palette_frames.append(pf)
        item.setSizeHint(pf.minimumSizeHint())
        self.setItemWidget(item, pf)

    def duplicate(self, idx):
        new_idx = len(self.palette_frames) - 1
        self.add_palette(new_idx, self.palette_frames[idx].full_name)
        self.set_current_palette(new_idx)

    def set_current_palette(self, idx):
        # self.radio_button_group.button(idx).setChecked(False)
        self.current_idx = idx
        self.radio_button_group.button(idx).setChecked(True)
        self.window.window.animation.set_palette_text(self.palette_frames[idx].name)
        self.window.window.set_image(self.palette_frames[idx].full_name)

    def get_current_palette(self):
        return self.palette_frames[self.current_idx]

    def set_palette_by_name(self, name):
        palette_names = [p.name for p in self.palettes]
        idx = palette_names.index(name)
        self.set_current_palette(idx)

    def set_palette_name(self, idx, name):
        self.palette_frames[idx].set_name(name)

class PaletteEditor(QtGui.QWidget):
    def __init__(self, window):
        super(PaletteEditor, self).__init__(window)
        self.window = window

        self.setMinimumWidth(480)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.palette_list = None        

        pl_label = QtGui.QLabel("Available Palettes")
        self.grid.addWidget(pl_label, 0, 0, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

    def clear(self):
        if self.palette_list:
            self.palette_list.deleteLater()

    def load_palettes(self, image_filenames):
        # for i in reversed(range(self.grid.count())): 
            # self.grid.itemAt(i).widget().deleteLater()
        self.clear()
        self.palette_list = PaletteList(image_filenames, self)
        self.grid.addWidget(self.palette_list, 1, 0)

    def color_swap(self, idx, new):
        new = QtGui.QColor(new)
        self.window.color_swap(idx, new)

    def set_current_palette(self, idx):
        self.palette_list.set_current_palette(idx)

    def set_current_palette_name(self, name):
        print('PaletteEditor', 'set_current_palette_name', name)
        if self.palette_list:
            self.palette_list.set_palette_name(self.palette_list.current_idx, name)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = MainEditor()
    window.show()
    app.exec_()
