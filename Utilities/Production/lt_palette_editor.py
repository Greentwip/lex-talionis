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

    def wheelEvent(self, event):
        if event.delta() > 0 and self.screen_scale < 4:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.delta() < 0 and self.screen_scale > 1:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

class MainEditor(QtGui.QWidget):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Palette Editor v')
        self.setMinimumSize(480, 480)

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.view = MainView(self)

        self.menuBar = QtGui.QMenuBar(self)
        self.animation = Animation(self)
        self.palette_editor = PaletteEditor(self)

        self.create_menus()

        self.grid.setMenuBar(self.menuBar)
        self.grid.addWidget(self.view, 0, 0)
        self.grid.addWidget(self.animation_info, 1, 0)

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
        self.image = QtGui.QImage(image_file)
        self.view.clear_scene()
        self.view.set_new_image(image_file)

    def update_view(self):
        self.view.show_image()

    def load_class(self):
        pass

    def get_script_from_index(self, fn):
        script = fn[:-10] + '-Script.txt'
        if os.path.exists(script):
            return script
        return None

    def get_images_from_index(self, fn):
        image_header = fn[:-10]
        images = glob.glob(image_header + "-*.png")
        return images

    def get_info(self, image_fn):
        klass, weapon, palette = image_fn[:-4].split('-')
        return klass, weapon, palette

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
                self.palette_editor.load_palettes(image_files)
                self.palette_editor.set_current_palette(palette)

    def load_image(self):
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Image PNG", QtCore.QDir.currentPath(),
                                                       "PNG Files (*.png);;All Files (*)")
        if image_file:
            self.set_image(image_file)
            self.animation.clear_info()
            self.update_view()

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
        self.weapon_text = QtGui.QLineEdit()
        self.palette_text = QtGui.QLineEdit()

        self.playable = False
        self.play_button = QtGui.QPushButton("Play Animation", )
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

class Palette(object):
    def __init__(self, image_file):
        self.name = image_file[:-4].split('-')[-1]

    def get_name(self):
        return self.name

    def get_horiz_image(self):
        pass

class PaletteEditor(QtGui.QWidget):
    def __init__(self, window=None):
        super(PaletteEditor, self).__init__()
        self.window = window

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.palettes = []
        self.current_idx = 0

    def set_current_palette(self, idx):
        self.current_idx = idx

    def load_palettes(self, image_files):
        self.palettes = [Palette(image) for image in image_files]
        self.update_view()

    def duplicate(self, idx):
        copy = Palette(self.palettes[idx].get_name())
        self.palettes.append(copy)
        self.update_view()

    def update_view(self):
        self.view_grid = QtGui.QGridLayout()
        for idx, palette in enumerate(self.palettes):
            radio_button = QtGui.QRadioButton()
            radio_button.clicked.connect(self.set_current_palette, idx)
            name = QtGui.QLabel(palette.get_name())
            pic = palette.get_horiz_image()
            copy = QtGui.QPushButton("Duplicate")
            copy.clicked.connect(self.duplicate, idx)
            self.view_grid.addWidget(radio_button, idx, 0)
            self.view_grid.addWidget(name, idx, 0)
            self.view_grid.addWidget(pic, idx, 0)
            self.view_grid.addWidget(copy, idx, 0)
        if self.palettes:
            self.set_current_palette(0)
        self.grid.addLayout(self.view_grid, 0, 0)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = MainEditor()
    window.show()
    app.exec_()
