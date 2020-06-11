import sys, os
import glob

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QMenuBar, QColorDialog, \
    QUndoStack, QAction, QMenu, QWidget, QLineEdit, QComboBox, QPushButton, \
    QFileDialog, QMessageBox, QApplication, QGridLayout, QFormLayout
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QColor, QImage, QPixmap

from palette_editor_code import PaletteList
from palette_editor_code import ImageMap
from palette_editor_code import Animation

class MainView(QGraphicsView):
    min_scale = 1
    max_scale = 5

    def __init__(self, window=None):
        QGraphicsView.__init__(self)
        self.window = window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMouseTracking(True)

        self.image = None
        self.screen_scale = 1

    def create_image(self, image_map, palette_frame):
        colors = [QColor(c).rgb() for c in palette_frame.get_colors()]
        width, height = image_map.width, image_map.height
        image = QImage(width, height, QImage.Format_ARGB32)
        for x in range(width):
            for y in range(height):
                idx = image_map.get(x, y)
                image.setPixel(x, y, colors[idx])
        return QImage(image)

    def set_image(self, image_map, palette_frame):
        self.image = self.create_image(image_map, palette_frame)
        # self.image = self.image.convertToFormat(QImage.Format_ARGB32)
        self.setSceneRect(0, 0, self.image.width(), self.image.height())

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.image:
            self.clear_scene()
            self.scene.addPixmap(QPixmap.fromImage(self.image))

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        if not pixmap:
            return
        image = pixmap.pixmap().toImage()
        pos = int(scene_pos.x()), int(scene_pos.y())

        if event.button() == Qt.LeftButton:
            dlg = QColorDialog()
            dlg.setCurrentColor(QColor(image.pixel(pos[0], pos[1])))
            if dlg.exec_():
                self.window.change_current_palette(pos, dlg.currentColor())

    def wheelEvent(self, event):
        if event.delta() > 0 and self.screen_scale < self.max_scale:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.delta() < 0 and self.screen_scale > self.min_scale:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

class MainEditor(QWidget):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Palette Editor v5.9.0')
        self.setMinimumSize(640, 480)

        self.grid = QGridLayout()
        self.setLayout(self.grid)

        self.main_view = MainView(self)
        self.menu_bar = QMenuBar(self)
        self.palette_list = PaletteList.PaletteList(self)
        self.image_map_list = ImageMap.ImageMapList()
        self.scripts = []

        self.undo_stack = QUndoStack(self)

        self.create_menu_bar()

        self.grid.setMenuBar(self.menu_bar)
        self.grid.addWidget(self.main_view, 0, 0)
        self.grid.addWidget(self.palette_list, 0, 1, 2, 1)
        self.info_form = QFormLayout()
        self.grid.addLayout(self.info_form, 1, 0)

        self.create_info_bars()
        self.clear_info()

    def create_menu_bar(self):
        load_class_anim = QAction("Load Class Animation...", self, triggered=self.load_class)
        load_single_anim = QAction("Load Single Animation...", self, triggered=self.load_single)
        load_image = QAction("Load Image...", self, triggered=self.load_image)
        save = QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        exit = QAction("E&xit...", self, shortcut="Ctrl+Q", triggered=self.close)

        file_menu = QMenu("&File", self)
        file_menu.addAction(load_class_anim)
        file_menu.addAction(load_single_anim)
        file_menu.addAction(load_image)
        file_menu.addAction(save)
        file_menu.addAction(exit)

        undo_action = QAction("Undo", self, shortcut="Ctrl+Z", triggered=self.undo)
        redo_action = QAction("Redo", self, triggered=self.redo)
        redo_action.setShortcuts(["Ctrl+Y", "Ctrl+Shift+Z"])

        edit_menu = QMenu("&Edit", self)
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)

        self.menu_bar.addMenu(file_menu)
        self.menu_bar.addMenu(edit_menu)

    def create_info_bars(self):
        self.class_text = QLineEdit()
        self.class_text.textChanged.connect(self.class_text_change)
        self.weapon_box = QComboBox()
        self.weapon_box.uniformItemSizes = True
        self.weapon_box.activated.connect(self.weapon_changed)
        self.palette_text = QLineEdit()
        self.palette_text.textChanged.connect(self.palette_text_change)

        self.play_button = QPushButton("View Animation")
        self.play_button.clicked.connect(self.view_animation)
        self.play_button.setEnabled(False)

        self.info_form.addRow("Class", self.class_text)
        self.info_form.addRow("Weapon", self.weapon_box)
        self.info_form.addRow("Palette", self.palette_text)
        self.info_form.addRow(self.play_button)

    def undo(self):
        self.undo_stack.undo()

    def redo(self):
        self.undo_stack.redo()

    def change_current_palette(self, position, color):
        palette_frame = self.palette_list.get_current_palette()
        image_map = self.image_map_list.get_current_map()
        color_idx = image_map.get(position[0], position[1])
        palette_frame.set_color(color_idx, color)

    def view_animation(self):
        image = self.main_view.image
        index = self.image_map_list.get_current_map().get_index()
        script = self.image_map_list.get_current_map().get_script()
        ok = Animation.Animator.get_dialog(image, index, script)

    def clear_info(self):
        self.class_text.setEnabled(True)
        self.class_text.setText('')
        self.weapon_box.clear()
        self.palette_text.setText('')
        self.play_button.setEnabled(False)
        self.image_map_list.clear()
        self.palette_list.clear()
        self.scripts = []
        self.mode = 0  # 1 - Class, 2 - Animation, 3 - Basic Image, 0 - Not defined yet
        self.undo_stack.clear()

    def class_text_change(self):
        pass

    def palette_text_change(self):
        self.palette_list.get_current_palette().set_name(self.palette_text.text())

    def weapon_changed(self, idx):
        self.image_map_list.set_current_idx(idx)
        self.update_view()

    def update_view(self):
        cur_image_map = self.image_map_list.get_current_map()
        cur_palette = self.palette_list.get_current_palette()
        self.main_view.set_image(cur_image_map, cur_palette)
        self.main_view.show_image()

    def get_script_from_index(self, fn):
        script = str(fn[:-10] + '-Script.txt')
        if os.path.exists(script):
            return script

        head, tail = os.path.split(script)
        s_l = tail.split('-')
        class_name = s_l[0]
        gender_num = int(class_name[-1])
        new_gender_num = (gender_num//5)*5
        new_class_name = class_name[:-1] + str(new_gender_num)
        new_script_name = '-'.join([new_class_name] + s_l[1:])
        script = os.path.join(head, new_script_name)
        if os.path.exists(script):
            return script

        new_class_name = class_name[:-1] + "0"
        new_script_name = '-'.join([new_class_name] + s_l[1:])
        script = os.path.join(head, new_script_name)
        if os.path.exists(script):
            return script

        return None

    def get_images_from_index(self, fn):
        image_header = fn[:-10]
        images = glob.glob(str(image_header + "-*.png"))
        return images

    def get_all_index_files(self, index_file):
        head, tail = os.path.split(index_file)
        class_name = tail.split('-')[0]
        index_files = glob.glob(head + '/' + class_name + "*-Index.txt")
        return index_files

    def handle_duplicates(self, palette, image_map):
        for existing_palette in self.palette_list.list[:-1]:
            # print('Image Map Weapon: %s' % image_map.weapon_name)
            # print('Existing Palette %s' % existing_palette.name)
            # print(existing_palette.get_colors())
            # print('New Palette %s' % palette.name)
            # print(palette.get_colors())
            if existing_palette.name == palette.name:
                if palette.get_colors() != existing_palette.get_colors():
                    image_map.reorder(palette, existing_palette)
                return True
        return False

    def auto_load_path(self):
        starting_path = QDir.currentPath()
        check_here = str(QDir.currentPath() + '/pe_config.txt')
        if os.path.exists(check_here):
            with open(check_here) as fp:
                directory = fp.readline().strip()
            if os.path.exists(directory):
                starting_path = directory
        return starting_path

    def auto_save_path(self, index_file):
        auto_load = str(QDir.currentPath() + '/pe_config.txt')
        with open(auto_load, 'w') as fp:
            print(os.path.relpath(str(index_file)))
            fp.write(os.path.relpath(str(index_file)))

    def load_class(self):
        if not self.maybe_save():
            return

        starting_path = self.auto_load_path()
        # starting_path = QDir.currentPath() + '/../Data'
        index_file = QFileDialog.getOpenFileName(self, "Choose Class", starting_path,
                                                       "Index Files (*-Index.txt);;All Files (*)")
        if index_file:
            self.auto_save_path(index_file)
            self.clear_info()
            weapon_index_files = self.get_all_index_files(str(index_file))
            for index_file in weapon_index_files:  # One image_map for each weapon
                script_file = self.get_script_from_index(index_file)
                image_files = [str(i) for i in self.get_images_from_index(index_file)]
                if image_files:
                    image_map = self.image_map_list.add_map_from_images(image_files)
                    image_map.load_script(script_file)
                    image_map.set_index(index_file)
                    self.play_button.setEnabled(True)
                    for image_filename in image_files:
                        self.palette_list.add_palette_from_image(image_filename, image_map)
                        dup = self.handle_duplicates(self.palette_list.get_last_palette(), image_map)
                        if dup:
                            self.palette_list.remove_last_palette()
            for weapon in self.image_map_list.get_available_weapons():
                self.weapon_box.addItem(weapon)
            klass_name = os.path.split(image_files[0][:-4])[-1].split('-')[0]  # Klass
            self.class_text.setText(klass_name)
            self.palette_list.set_current_palette(0)
            self.mode = 1

    def load_single(self):
        if not self.maybe_save():
            return
        starting_path = self.auto_load_path()
        index_file = QFileDialog.getOpenFileName(self, "Choose Animation", starting_path,
                                                       "Index Files (*-Index.txt);;All Files (*)")
        if index_file:
            self.auto_save_path(index_file)
            script_file = self.get_script_from_index(index_file)
            image_files = [str(i) for i in self.get_images_from_index(index_file)]
            if image_files:
                self.clear_info()
                image_map = self.image_map_list.add_map_from_images(image_files)
                image_map.load_script(script_file)
                image_map.set_index(index_file)
                self.play_button.setEnabled(True)
                for image_filename in image_files:
                    self.palette_list.add_palette_from_image(image_filename, image_map)
                self.weapon_box.addItem(self.image_map_list.get_current_map().weapon_name)
                klass_name = os.path.split(image_files[0][:-4])[-1].split('-')[0]  # Klass
                self.class_text.setText(klass_name)
                self.palette_list.set_current_palette(0)
            self.mode = 2

    def load_image(self):
        if not self.maybe_save():
            return
        starting_path = self.auto_load_path()
        image_filename = QFileDialog.getOpenFileName(self, "Choose Image PNG", starting_path,
                                                           "PNG Files (*.png);;All Files (*)")
        if image_filename:
            self.auto_save_path(image_filename)
            self.clear_info()
            image_map = self.image_map_list.add_map_from_images([str(image_filename)])
            self.palette_list.add_palette_from_image(str(image_filename), image_map)
            self.class_text.setEnabled(False)
            self.palette_list.set_current_palette(0)
            self.mode = 3

    def maybe_save(self):
        if self.mode:
            ret = QMessageBox.warning(self, "Palette Editor", "These images may have been modified.\n"
                                            "Do you want to save your changes?",
                                            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ret == QMessageBox.Save:
                return self.save()
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def save(self):
        if self.mode == 3:
            # Save as... PNG (defaults to name with palette )
            name = QFileDialog.getSaveFileName(self, 'Save Image', self.auto_load_path())
            image_map = self.image_map_list.get_current_map()
            palette = self.palette_list.get_current_palette()
            image = self.main_view.create_image(image_map, palette)
            pixmap = QPixmap.fromImage(image)
            pixmap.save(name, 'png')
        elif self.mode == 2:
            # Save all palettes with their palette names
            image_map = self.image_map_list.get_current_map()
            for palette in self.palette_list.list:
                image = self.main_view.create_image(image_map, palette)
                pixmap = QPixmap.fromImage(image)
                head, tail = os.path.split(image_map.image_filename)
                tail = '-'.join([str(self.class_text.text()), str(image_map.weapon_name), str(palette.name)]) + '.png'
                new_filename = os.path.join(head, tail)
                pixmap.save(new_filename, 'png')
            msg = QMessageBox.information(self, "Save Successful", "Successfully Saved!")
        elif self.mode == 1:
            # Save all weapons * palettes with their palette names
            for image_map in self.image_map_list.list:
                for palette in self.palette_list.list:
                    image = self.main_view.create_image(image_map, palette)
                    # image = image.convertToFormat(QImage.Format_RGB32)
                    pixmap = QPixmap.fromImage(image)
                    head, tail = os.path.split(image_map.image_filename)
                    tail = '-'.join([str(self.class_text.text()), str(image_map.weapon_name), str(palette.name)]) + '.png'
                    new_filename = os.path.join(head, tail)
                    pixmap.save(new_filename, 'png')
            msg = QMessageBox.information(self, "Save Successful", "Successfully Saved!")
        return True

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_editor = MainEditor()
    main_editor.show()
    app.exec_()
