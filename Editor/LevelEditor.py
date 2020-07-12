from collections import OrderedDict
import sys, os, shutil, math

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QDockWidget, QMainWindow, QErrorMessage, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QAction, QMenu, QApplication
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QImage, QPixmap, QBrush, QPen, qRgb, qRgba, QCursor
from PyQt5.QtCore import Qt, QTimer, QElapsedTimer, QDir

sys.path.append('./')
sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad
from Code.imagesDict import COLORKEY

from EditorCode import PropertyMenu, Terrain, TileInfo, UnitData
from EditorCode import EditorUtilities, Faction, Triggers, QtWeather
from EditorCode.DataImport import Data
from EditorCode import Autotiles

__version__ = "0.9.4.1"

# TODO: Created Units

class MainView(QGraphicsView):
    def __init__(self, tile_data, tile_info, unit_data, window=None):
        QGraphicsView.__init__(self)
        self.window = window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMinimumSize(15*16, 10*16)
        self.setMouseTracking(True)
        # self.setDragMode(QGraphicsView.ScrollHandDrag)

        self.image = None
        self.working_image = None
        # self.tool = None
        # Data
        self.tile_data = tile_data
        self.tile_info = tile_info
        self.unit_data = unit_data

        self.screen_scale = 1

    def set_new_image(self, image):
        self.image = QImage(image)
        self.image = self.image.convertToFormat(QImage.Format_ARGB32)
        # Handle colorkey
        qCOLORKEY = qRgb(*COLORKEY)
        new_color = qRgba(0, 0, 0, 0)
        for x in range(self.image.width()):
            for y in range(self.image.height()):
                if self.image.pixel(x, y) == qCOLORKEY:
                    self.image.setPixel(x, y, new_color)
        self.setSceneRect(0, 0, self.image.width(), self.image.height())

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.working_image:
            self.clear_scene()
            self.scene.addPixmap(QPixmap.fromImage(self.working_image))

    def disp_main_map(self):
        if self.image:
            image = self.window.autotiles.draw()
            if image:
                image = image.copy()
                painter = QPainter()
                painter.begin(image)
                painter.drawImage(0, 0, self.image.copy())  # Draw image on top of autotiles
                painter.end()
                self.working_image = image
            else:
                self.working_image = self.image.copy()

    def disp_weather(self):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            for weather in self.window.weather:
                particles = weather.draw()
                for image, coord in particles:
                    painter.drawImage(coord[0], coord[1], image)
            painter.end()

    def disp_tile_data(self):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            for coord, color in self.tile_data.tiles.items():
                write_color = QColor(color[0], color[1], color[2])
                write_color.setAlpha(self.window.terrain_menu.get_alpha())
                painter.fillRect(coord[0] * 16, coord[1] * 16, 16, 16, write_color)
            painter.end()

    def disp_tile_info(self):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            for coord, image in self.tile_info.get_images().items():
                painter.drawImage(coord[0] * 16 + 1, coord[1] * 16, image)
            painter.end()

    def disp_units(self):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            current_mode = self.window.unit_menu.current_mode_view()
            for coord, unit_image in self.unit_data.get_unit_images(current_mode).items():
                if unit_image:
                    painter.drawImage(coord[0] * 16 - 4, coord[1] * 16 - 6, unit_image)
            # Highlight current unit
            current_unit = self.window.unit_menu.get_current_unit()
            if current_unit and current_unit.position:
                painter.drawImage(current_unit.position[0] * 16 - 8, current_unit.position[1] * 16 - 5, EditorUtilities.create_cursor())
            painter.end()

    def disp_reinforcements(self):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            current_mode = self.window.reinforcement_menu.current_mode_view()
            current_pack = self.window.reinforcement_menu.current_pack()
            for coord, unit_image in self.unit_data.get_reinforcement_images(current_mode, current_pack).items():
                if unit_image:
                    painter.drawImage(coord[0] * 16 - 4, coord[1] * 16 - 6, unit_image)
            # Highlight current unit
            current_unit = self.window.reinforcement_menu.get_current_unit()
            if current_unit and current_unit.position:
                painter.drawImage(current_unit.position[0] * 16 - 8, current_unit.position[1] * 16 - 5, EditorUtilities.create_cursor())
            painter.end()

    def disp_triggers(self):
        def draw_arrow(painter, start, end, color):
            angle = math.atan2(end[1] - start[1], end[0] - start[0]) + math.pi
            left_angle, right_angle = angle - math.pi/6, angle + math.pi/6
            left_x = end[0] + (.5 * math.cos(left_angle))
            left_y = end[1] + (.5 * math.sin(left_angle))
            right_x = end[0] + (.5 * math.cos(right_angle))
            right_y = end[1] + (.5 * math.sin(right_angle))
            path = QPainterPath()
            path.moveTo(end[0] * 16 + 7, end[1] * 16 + 7)
            path.lineTo(left_x * 16 + 7, left_y * 16 + 7)
            path.lineTo(right_x * 16 + 7, right_y * 16 + 7)
            painter.setPen(Qt.NoPen)
            painter.fillPath(path, QBrush(color))

            # painter.drawLine(end[0] * 16 + 7, end[1] * 16 + 7, left_x * 16 + 7, left_y * 16 + 7)
            # painter.drawLine(end[0] * 16 + 7, end[1] * 16 + 7, right_x * 16 + 7, right_y * 16 + 7)

        def draw(painter, start, end, unit, alpha):
            if unit.team == 'player':
                color = QColor(0, 144, 144, alpha)
            elif unit.team == 'other':
                color = QColor(0, 248, 0, alpha)
            else:
                color = QColor(248, 72, 0, alpha)
            pen.setColor(color)
            painter.setPen(pen)
            painter.drawLine(start[0] * 16 + 7, start[1] * 16 + 7, end[0] * 16 + 7, end[1] * 16 + 7)
            draw_arrow(painter, start, end, color)

        if self.working_image:
            current_trigger_name = self.window.trigger_menu.get_current_trigger_name()
            current_pack = self.window.reinforcement_menu.current_pack()
            painter = QPainter()
            painter.begin(self.working_image)
            pen = QPen(Qt.blue, 2, Qt.SolidLine, Qt.RoundCap)
            for trigger_name, trigger in self.unit_data.triggers.items():
                alpha = 255 if current_trigger_name == trigger_name else 120
                for unit, (start, end) in trigger.units.items():
                    if (self.window.dock_visibility['Units'] and unit in self.unit_data.units) or \
                       (self.window.dock_visibility['Reinforcements'] and unit in self.unit_data.reinforcements and unit.pack == current_pack):
                            draw(painter, start, end, unit, alpha)    
            # Draw current
            current_arrow = self.window.trigger_menu.get_current_arrow()
            if current_arrow:
                unit, old_pos = current_arrow
                scene_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
                pixmap = self.scene.itemAt(scene_pos, self.transform())
                pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)
                # print(pixmap, pos)
                # if pixmap and pos in self.tile_data.tiles:
                draw(painter, pos, old_pos, unit, 255)
                    
            painter.end()

    def trigger_mouse_press(self, event, pos):
        current_arrow = self.window.trigger_menu.get_current_arrow()
        current_trigger = self.window.trigger_menu.get_current_trigger()
        current_trigger_name = self.window.trigger_menu.get_current_trigger_name()
        if event.button() == Qt.LeftButton:
            if current_trigger:
                if current_arrow:
                    unit, old_pos = current_arrow
                    if pos != old_pos:
                        current_trigger.units[unit] = (pos, old_pos)
                    self.window.trigger_menu.clear_current_arrow()
                else:
                    if self.window.dock_visibility['Units']:                            
                        current_mode = self.window.unit_menu.current_mode_view()
                        current_unit = self.unit_data.get_unit_from_pos(pos, [current_mode])
                    elif self.window.dock_visibility['Reinforcements']:
                        current_mode = self.window.reinforcement_menu.current_mode_view()
                        current_pack = self.window.reinforcement_menu.current_pack()
                        current_unit = self.unit_data.get_rein_from_pos(pos, [current_mode], current_pack)
                    if current_unit:
                        self.window.trigger_menu.set_current_arrow(current_unit, pos)
                    else:
                        for trigger_name, trigger in self.unit_data.triggers.items():
                            if trigger_name == current_trigger_name:
                                continue
                            for unit, (start, end) in trigger.units.items():
                                if start == pos:
                                    current_unit = unit
                                    self.window.trigger_menu.set_current_arrow(current_unit, pos)
                                    return
            else:
                self.window.status_bar.showMessage('Select a trigger to use!')
        elif event.button() == Qt.RightButton:
            if current_arrow:
                self.window.trigger_menu.clear_current_arrow()
            elif current_trigger:
                # Remove unit lines if they overlap with position
                current_trigger.units = {unit: (start, end) for unit, (start, end) in current_trigger.units.items() if 
                                         start != pos and end != pos}
            else:
                self.window.status_bar.showMessage('Select a trigger to use!')

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos, self.transform())
        pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)

        if self.window.dock_visibility['Move Triggers'] and (self.window.dock_visibility['Units'] or self.window.dock_visibility['Reinforcements']):
            self.trigger_mouse_press(event, pos)
        elif pixmap and pos in self.tile_data.tiles:
            # print('mousePress Tool: %s' % self.tool)
            if self.window.dock_visibility['Terrain']:
                if event.button() == Qt.LeftButton:
                    self.window.terrain_menu.paint(pos)
                elif event.button() == Qt.RightButton:
                    current_color = self.tile_data.tiles[pos]
                    self.window.terrain_menu.set_current_color(current_color)
            elif self.window.dock_visibility['Event Tiles']:
                if event.button() == Qt.LeftButton:
                    name = self.window.tile_info_menu.get_current_name()
                    value = self.window.tile_info_menu.start_dialog(self.tile_info.get(pos))
                    if value:
                        self.tile_info.set(pos, name, value)
                        self.window.update_view()
                elif event.button() == Qt.RightButton:
                    self.tile_info.delete(pos)
                    self.window.update_view()
            elif self.window.dock_visibility['Units']:
                if event.button() == Qt.LeftButton:
                    current_unit = self.window.unit_menu.get_current_unit()
                    if current_unit:
                        modes = current_unit.mode
                        under_unit = self.unit_data.get_unit_from_pos(pos, modes)
                        if under_unit:
                            print('Removing Unit')
                            under_unit.position = None
                            self.window.unit_menu.get_item_from_unit(under_unit).setForeground(QColor("red"))
                        if current_unit.position:
                            if current_unit.generic:
                                print('Copy & Place Unit')
                                new_unit = current_unit.copy()
                                new_unit.position = pos
                                self.unit_data.add_unit(new_unit)
                                self.window.unit_menu.add_unit(new_unit)
                                self.window.unit_menu.center(new_unit)
                            else:
                                print('Move Unit')
                                current_unit.position = pos
                                self.window.unit_menu.center(current_unit)
                        else:
                            print('Place Unit')
                            current_unit.position = pos
                            # Reset the color
                            self.window.unit_menu.get_current_item().setForeground(QColor("black"))
                            self.window.unit_menu.center(current_unit)
                        self.window.update_view()
                elif event.button() == Qt.RightButton:
                    current_mode = self.window.unit_menu.current_mode_view()
                    current_idx = self.unit_data.get_idx_from_pos(pos, [current_mode])
                    print('Current IDX %s' % current_idx)
                    if current_idx >= 0:
                        self.window.unit_menu.set_current_idx(current_idx)
            elif self.window.dock_visibility['Reinforcements']:
                if event.button() == Qt.LeftButton:
                    current_unit = self.window.reinforcement_menu.get_current_unit()
                    if current_unit:
                        if current_unit.position:
                            print('Copy & Place Unit')
                            new_unit = current_unit.copy()
                            pack_mates = [rein for rein in self.unit_data.reinforcements if rein.pack == new_unit.pack]
                            new_unit.event_id = EditorUtilities.next_available_event_id(pack_mates)
                            new_unit.position = pos
                            self.unit_data.add_reinforcement(new_unit)
                            self.window.reinforcement_menu.add_unit(new_unit)
                            self.window.reinforcement_menu.center(new_unit)
                        else:
                            print('Place Unit')
                            current_unit.position = pos
                            # Reset the color
                            self.window.reinforcement_menu.get_current_item().setForeground(QColor("black"))
                            self.window.reinforcement_menu.center(current_unit)
                        self.window.update_view()
                elif event.button() == Qt.RightButton:
                    current_mode = self.window.reinforcement_menu.current_mode_view()
                    current_pack = self.window.reinforcement_menu.current_pack()
                    current_idx = self.unit_data.get_ridx_from_pos(pos, [current_mode], current_pack)
                    print(current_idx)
                    if current_idx >= 0:
                        self.window.reinforcement_menu.set_current_idx(current_idx)
        else:
            if self.window.dock_visibility['Units']:
                if event.button() == Qt.LeftButton:
                    current_unit = self.window.unit_menu.get_current_unit()
                    if current_unit:
                        print("Removing Unit's Position")
                        current_unit.position = None
                        self.window.unit_menu.get_item_from_unit(current_unit).setForeground(QColor("red"))
            elif self.window.dock_visibility['Reinforcements']:
                if event.button() == Qt.LeftButton:
                    current_unit = self.window.reinforcement_menu.get_current_unit()
                    if current_unit:
                        print("Removing Unit's Position")
                        current_unit.position = None
                        self.window.reinforcement_menu.get_item_from_unit(current_unit).setForeground(QColor("red"))

    def mouseReleaseEvent(self, event):
        # Do the parent's version
        QGraphicsView.mouseReleaseEvent(self, event)
        if self.window.dock_visibility['Terrain']:
            self.window.terrain_menu.mouse_release()

    def mouseMoveEvent(self, event):
        # Do the parent's version
        QGraphicsView.mouseMoveEvent(self, event)
        # Mine
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos, self.transform())
        if pixmap:
            pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)
            info = None
            current_unit_mode = self.window.unit_menu.current_mode_view()
            current_rein_mode = self.window.reinforcement_menu.current_mode_view()
            if self.window.dock_visibility['Units'] and self.unit_data.get_unit_from_pos(pos, [current_unit_mode]):
                info = self.unit_data.get_unit_str(pos, [current_unit_mode])
            elif self.window.dock_visibility['Reinforcements'] and \
                    self.unit_data.get_rein_from_pos(pos, [current_rein_mode], self.window.reinforcement_menu.current_pack()):
                info = self.unit_data.get_reinforcement_str(pos, [current_rein_mode], self.window.reinforcement_menu.current_pack())
            elif self.window.dock_visibility['Event Tiles'] and self.tile_info.get(pos):
                info = self.tile_info.get_str(pos)
            elif self.window.dock_visibility['Terrain'] and pos in self.tile_data.tiles:
                hovered_color = self.tile_data.tiles[pos]
                # print('Hover', pos, hovered_color)
                info = self.window.terrain_menu.get_info_str(hovered_color)
                if self.window.terrain_menu.mouse_down:
                    self.window.terrain_menu.paint(pos)
            # print('mouseMove: %s' % info)
            if info:
                message = str(pos[0]) + ', ' + str(pos[1]) + ': ' + info
                self.window.status_bar.showMessage(message)
        elif self.window.dock_visibility['Terrain']:
            self.window.terrain_menu.mouse_release()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0 and self.screen_scale < 4:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.angleDelta().y() < 0 and self.screen_scale > 1:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

    def keyPressEvent(self, event):
        super(QGraphicsView, self).keyPressEvent(event)
        if self.window.dock_visibility['Terrain']:
            # if (event.modifiers() & Qt.ControlModifier) and event.key() == 
            if event.key() == (Qt.Key_Control and Qt.Key_Z):
                self.window.terrain_menu.undo()

    def center_on_pos(self, pos):
        self.centerOn(pos[0] * 16, pos[1] * 16)
        self.window.update_view()

class Dock(QDockWidget):
    def __init__(self, title, parent):
        super(Dock, self).__init__(title, parent)
        self.main_editor = parent
        self.visibilityChanged.connect(self.visible)

    def visible(self, visible):
        # print("%s's Visibility Changed to %s" %(self.windowTitle(), visible))
        title = str(self.windowTitle())
        self.main_editor.dock_visibility[title] = visible
        if visible:
            print(title)
            message = None
            if title == 'Terrain':
                message = 'L-click to place selected color. R-click to select color.'
            elif title == 'Event Tiles':
                message = 'L-click to place selected event tile. R-click to delete event tile.'
            elif title == 'Units':
                message = 'L-click to place selected unit. R-click to select unit.'
            elif title == 'Reinforcements':
                message = 'L-click to place selected unit. R-click to select unit.'

            if message:
                self.main_editor.status_bar.showMessage(message)
        self.main_editor.update_view()

class MainEditor(QMainWindow):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Level Editor v' + __version__)
        self.installEventFilter(self)

        # Data
        self.init_data()

        self.view = MainView(self.tile_data, self.tile_info, self.unit_data, self)
        self.setCentralWidget(self.view)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')

        self.map_image_file = None
        self.directory = None
        self.current_level_name = None

        self.create_actions()
        self.create_menus()
        self.create_dock_windows()

        # Whether anything has changed since the last save
        # For now just always modified
        self.modified = True

        # === Timing ===
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.main_timer.start(33)  # 30 FPS
        self.elapsed_timer = QElapsedTimer()
        self.elapsed_timer.start()

        # === Auto-open ===
        self.auto_open()

    def init_data(self):
        self.tile_data = Terrain.TileData()
        self.tile_info = TileInfo.TileInfo()
        self.overview_dict = OrderedDict()
        self.unit_data = UnitData.UnitData()
        self.weather = []
        self.autotiles = Terrain.Autotiles()

    def tick(self):
        current_time = self.elapsed_timer.elapsed()
        if self.dock_visibility['Units']:
            self.unit_menu.tick(current_time)
        if self.dock_visibility['Reinforcements']:
            self.reinforcement_menu.tick(current_time)
        for weather in self.weather:
            weather.update(current_time, self.tile_data)
        if self.autotiles:
            self.autotiles.update(current_time)
        self.update_view()

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def update_view(self):
        self.view.disp_main_map()
        if self.dock_visibility['Terrain']:
            self.view.disp_tile_data()
        if self.dock_visibility['Event Tiles']:
            self.view.disp_tile_info()
        if self.dock_visibility['Units']:
            self.view.disp_units()
        if self.dock_visibility['Reinforcements']:
            self.view.disp_reinforcements()
        if self.dock_visibility['Move Triggers'] and (self.dock_visibility['Units'] or self.dock_visibility['Reinforcements']):
            self.view.disp_triggers()
        if self.weather:
            self.view.disp_weather()
        self.view.show_image()

    # === Loading Data ===
    def set_image(self, image_file):
        self.map_image_file = image_file
        # This section is for fixing weird png errors
        pixmap = QPixmap()
        pixmap.load(image_file)
        pixmap.save(image_file, "PNG")
        # End weird section
        image = QImage(image_file)
        print("Loading %s (a %dx%d image)..." % (image_file, image.width(), image.height()), flush=True)
        if image.width() % 16 != 0 or image.height() % 16 != 0:
            QErrorMessage().showMessage("Image width and/or height is not divisible by 16!")
            return
        self.view.clear_scene()
        self.view.set_new_image(image_file)

    def new(self):
        if self.maybe_save():
            self.current_level_name = None
            self.new_level()

    def new_level(self):
        image_file, _ = QFileDialog.getOpenFileName(self, "Choose Map PNG", QDir.currentPath(),
                                                    "PNG Files (*.png);;All Files (*)")
        if image_file:
            self.set_image(image_file)
            self.autotiles.clear()
            self.overview_dict = OrderedDict()
            self.properties_menu.new()
            self.tile_info.clear()
            self.unit_data.clear()
            self.faction_menu.clear()
            self.unit_menu.clear()
            self.reinforcement_menu.clear()
            self.tile_data.new(image_file)

            self.status_bar.showMessage('Created New Level')

            self.update_view()

    def is_same_size(self, image1: QImage, image2: QImage) -> bool:
        return image1.width() == image2.width() and image1.height() == image2.height()

    def import_new_map(self):
        image_file, _ = QFileDialog.getOpenFileName(self, "Choose Map PNG", QDir.currentPath(),
                                                    "PNG Files (*.png);;All Files (*)")
        if image_file:
            if not self.view.image or not self.is_same_size(self.view.image, QImage(image_file)):
                self.tile_data.new(image_file)
            self.set_image(image_file)
            self.remove_full_image()
            self.update_view()

    def remove_full_image(self):
        self.autotiles.clear()
        if self.directory:
            full_map_sprite_filename = self.directory + '/MapSprite_full.png'
            if os.path.exists(full_map_sprite_filename):
                os.remove(full_map_sprite_filename)

    def generate_autotiles(self):
        if self.directory:
            # map_sprite_filename = self.directory + '/MapSprite.png'
            map_sprite_filename = self.map_image_file
            full_map_sprite_filename = self.directory + '/MapSprite_full.png'
            if os.path.exists(full_map_sprite_filename):
                self.autotile_maker = Autotiles.AutotileMaker(full_map_sprite_filename, self.directory, self)
            else:
                shutil.copy(map_sprite_filename, full_map_sprite_filename)  # Make a backup
                self.autotile_maker = Autotiles.AutotileMaker(map_sprite_filename, self.directory, self)
        else:
            print("Please save me first!!!")

    def open(self):
        if self.maybe_save():
            # "Levels (Level*);;All Files (*)",
            starting_path = QDir.currentPath() + '/../Data'
            directory = QFileDialog.getExistingDirectory(self, "Choose Level", starting_path,
                                                               QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            if directory:
                # Get the current level num
                if 'Level' in str(directory):
                    idx = str(directory).index('Level')
                    num = str(directory)[idx + 5:]
                    self.current_level_name = num
                self.directory = directory
                self.load_level()

    def auto_open(self):
        starting_path = str(QDir.currentPath() + '/le_config.txt')
        if os.path.exists(starting_path):
            with open(starting_path, 'r') as fp:
                self.directory = fp.readline().strip()
            if os.path.exists(self.directory):
                # Get the current level num
                if 'Level' in str(self.directory):
                    idx = str(self.directory).index('Level')
                    num = str(self.directory)[idx + 5:]
                    self.current_level_name = num
                self.load_level()

    def load_level(self):
        if self.directory:
            image = self.directory + '/MapSprite.png'
            self.set_image(image)

            tilefilename = self.directory + '/TileData.png'
            self.tile_data.load(tilefilename)

            auto_loc = self.directory + '/Autotiles/'
            self.autotiles.load(auto_loc)

            overview_filename = self.directory + '/overview.txt'
            self.overview_dict = SaveLoad.read_overview_file(overview_filename)
            self.properties_menu.load(self.overview_dict)

            tile_info_filename = self.directory + '/tileInfo.txt'
            self.tile_info.load(tile_info_filename)

            unit_level_filename = self.directory + '/UnitLevel.txt'
            self.unit_data.load(unit_level_filename)
            self.faction_menu.load(self.unit_data)
            self.unit_menu.load(self.unit_data)
            self.reinforcement_menu.load(self.unit_data)
            self.trigger_menu.load(self.unit_data)

            if self.current_level_name:
                self.status_bar.showMessage('Loaded Level' + self.current_level_name)

            self.update_view()

    def load_data(self):
        Data.load_data()
        self.update_view()

    # === Weather ===
    def add_weather(self, weather):
        if not self.tile_data or not hasattr(self.tile_data, 'width'):
            return
        width, height = self.tile_data.width, self.tile_data.height
        if weather == "Rain":
            bounds = (-height*GC.TILEHEIGHT/4, width*GC.TILEWIDTH, -16, -8)
            self.weather.append(QtWeather.Weather('Rain', .1, bounds, (width, height)))
        elif weather == "Snow":
            bounds = (-height*GC.TILEHEIGHT, width*GC.TILEWIDTH, -16, -8)
            self.weather.append(QtWeather.Weather('Snow', .125, bounds, (width, height)))
        elif weather == "Sand":
            bounds = (-2*height*GC.TILEHEIGHT, width*GC.TILEWIDTH, height*GC.TILEHEIGHT+16, height*GC.TILEHEIGHT+32)
            self.weather.append(QtWeather.Weather('Sand', .075, bounds, (width, height)))
        elif weather == "Light":
            bounds = (0, width*GC.TILEWIDTH, 0, height*GC.TILEHEIGHT)
            self.weather.append(QtWeather.Weather('Light', .04, bounds, (width, height)))
        elif weather == "Dark":
            bounds = (0, width*GC.TILEWIDTH, 0, height*GC.TILEHEIGHT)
            self.weather.append(QtWeather.Weather('Dark', .04, bounds, (width, height)))
        elif weather == "Fire":
            bounds = (0, width*GC.TILEWIDTH, height*GC.TILEHEIGHT, height*GC.TILEHEIGHT+16)
            self.weather.append(QtWeather.Weather('Fire', .05, bounds, (width, height)))

    def remove_weather(self, name):
        self.weather = [weather for weather in self.weather if weather.name != name]

    # === Save ===
    def write_overview(self, fp):
        with open(fp, mode='w', encoding='utf-8') as overview:
            for k, v in self.overview_dict.items():
                if v:
                    overview.write(k + ';' + v + '\n')

    def write_tile_data(self, fp):
        if self.tile_data.width:
            image = QImage(self.tile_data.width, self.tile_data.height, QImage.Format_RGB32)
            painter = QPainter()
            painter.begin(image)
            for coord, color in self.tile_data.tiles.items():
                write_color = QColor(color[0], color[1], color[2])
                painter.fillRect(coord[0], coord[1], 1, 1, write_color)
            painter.end()
            pixmap = QPixmap.fromImage(image)
            pixmap.save(fp, 'png')

    def write_tile_info(self, fp):
        with open(fp, mode='w', encoding='utf-8') as tile_info:
            for coord, properties in self.tile_info.tile_info_dict.items():
                value = self.tile_info.get_str(coord)
                if value:
                    tile_info.write(str(coord[0]) + ',' + str(coord[1]) + ':')
                    tile_info.write(value + '\n')

    def write_unit_level(self, fp):
        def get_item_str(item):
            item_str = item.id
            if item.droppable:
                item_str = 'd' + item_str
            elif item.event:
                item_str = 'e' + item_str
            return item_str

        def write_unit_line(unit):
            if unit.position:
                pos_str = ','.join(str(p) for p in unit.position)
            else:
                pos_str = 'None'
            ai_str = str(unit.ai) + (('_' + str(unit.ai_group)) if unit.ai_group else '') 
            event_id_str = (str(unit.pack) + '_' + str(unit.event_id) if unit.pack else str(unit.event_id)) if unit.event_id else '0'
            if unit.generic:
                item_strs = ','.join(get_item_str(item) for item in unit.items)
                klass_str = str(unit.klass) + ('F' if unit.gender >= 5 else '')
                order = [unit.team, '0', event_id_str, klass_str, str(unit.level), item_strs, pos_str, ai_str, unit.faction]
            else:
                order = [unit.team, '1' if unit.saved else '0', event_id_str, unit.id, pos_str, ai_str]
            if unit.extra_statuses:
                order.append(unit.extra_statuses)
            unit_level.write(';'.join(order) + '\n')

        def write_units(units):
            # Player units
            unit_level.write('# Player Characters\n')
            player_units = [unit for unit in units if unit.team == 'player']
            player_units = sorted(player_units, key=lambda x: x.mode)
            current_mode = [mode['name'] for mode in GC.DIFFICULTYDATA.values()]
            for unit in player_units:
                if unit.mode != current_mode:
                    current_mode = unit.mode
                    unit_level.write('mode;' + ','.join(current_mode) + '\n')
                write_unit_line(unit)
            # Other units
            other_units = [unit for unit in units if unit.team == 'other']
            if other_units:
                other_units = sorted(other_units, key=lambda x: x.mode)
                unit_level.write('# Other Characters\n')
                for unit in other_units:
                    if unit.mode != current_mode:
                        current_mode = unit.mode
                        unit_level.write('mode;' + ','.join(current_mode) + '\n')
                    write_unit_line(unit)
            # Enemies
            unit_level.write('# Enemies\n')
            for team in ('enemy', 'enemy2'):
                # Named enemy characters
                named_enemies = [unit for unit in units if unit.team == team and not unit.generic]
                if named_enemies:
                    named_enemies = sorted(named_enemies, key=lambda x: x.mode)
                    unit_level.write('# Bosses\n')
                    for unit in named_enemies:
                        if unit.mode != current_mode:
                            current_mode = unit.mode
                            unit_level.write('mode;' + ','.join(current_mode) + '\n')
                        write_unit_line(unit)
                # Generic enemy characters
                generic_enemies = [unit for unit in units if unit.team == team and unit.generic]
                if generic_enemies:
                    generic_enemies = sorted(generic_enemies, key=lambda x: x.mode)
                    unit_level.write('# Generics\n')
                    for unit in generic_enemies:
                        if unit.mode != current_mode:
                            current_mode = unit.mode
                            unit_level.write('mode;' + ','.join(current_mode) + '\n')
                        write_unit_line(unit)

        with open(fp, mode='w', encoding='utf-8') as unit_level:
            unit_level.write(EditorUtilities.unit_level_header)
            factions = self.unit_data.factions
            # if self.unit_data.load_player_characters:
            #     unit_level.write('load_player_characters\n')
            for faction in factions.values():
                unit_level.write('faction;' + faction.faction_id + ';' + faction.unit_name + 
                                 ';' + faction.faction_icon + ';' + faction.desc + '\n')
            # Units
            units = [unit for unit in self.unit_data.units]
            reinforcements = [rein for rein in self.unit_data.reinforcements]
            write_units(units)
            unit_level.write('# === Reinforcements ===\n')
            write_units(reinforcements)
            # Triggers
            unit_level.write('# === Triggers ===\n')
            current_mode = [mode['name'] for mode in GC.DIFFICULTYDATA.values()]
            for trigger_name, trigger in self.unit_data.triggers.items():
                for unit, (start, end) in trigger.units.items():
                    start_str = str(start[0]) + ',' + str(start[1])
                    end_str = str(end[0]) + ',' + str(end[1])
                    if unit.generic and unit in self.unit_data.units:
                        if unit.mode != current_mode:
                            current_mode = unit.mode
                            unit_level.write('mode;' + ','.join(current_mode) + '\n')
                        unit_id = str(unit.position[0]) + ',' + str(unit.position[1])
                    elif unit in self.unit_data.reinforcements:
                        unit_id = unit.pack + '_' + str(unit.event_id) if unit.pack else str(unit.event_id)
                    else:
                        unit_id = str(unit.id)
                    trigger_str = ';'.join(['trigger', str(trigger_name), unit_id, start_str, end_str])
                    unit_level.write(trigger_str + '\n')

    def clear_directory(self, directory):
        for fp in os.listdir(directory):
            file_path = os.path.join(directory, fp)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(e)

    def save_as(self):
        self.save(True)

    def save(self, new=False):
        if new or not self.current_level_name:
            text, ok = QInputDialog.getText(self, "Level Editor", "Enter Level Number:")
            if ok:
                self.current_level_name = text
            else:
                return False
            new = True

        data_directory = str(QDir.currentPath() + '/../Data')
        level_directory = str(data_directory + '/Level' + self.current_level_name)
        if new:
            if os.path.exists(level_directory):
                ret = QMessageBox.warning(self, "Level Editor", "A level with that number already exists!\n"
                                                "Do you want to overwrite it?",
                                                QMessageBox.Save | QMessageBox.Cancel)
                if ret == QMessageBox.Save:
                    print("Removing %s..." % (level_directory))
                    self.clear_directory(level_directory)
                else:
                    return False
            else:
                os.mkdir(level_directory)

        overview_filename = level_directory + '/overview.txt'
        self.overview_dict = self.properties_menu.save()
        self.write_overview(overview_filename)

        map_sprite_filename = level_directory + '/MapSprite.png'
        image = self.view.image
        print("Saving %s (a %dx%d image)..." % (map_sprite_filename, image.width(), image.height()), flush=True)
        assert image.width() > 0 and image.height() > 0, "The image being saved is null! This should not be possible!"
        # Handle colorkey
        # because the image has alpha, and we need to remove the alpha from the image
        # and replace alpha sections with COLORKEY
        qCOLORKEY = qRgba(*COLORKEY, 255)
        new_color = qRgba(0, 0, 0, 0)
        for x in range(image.width()):
            for y in range(image.height()):
                if image.pixel(x, y) == new_color:
                    image.setPixel(x, y, qCOLORKEY)
        image = image.convertToFormat(QImage.Format_RGB32)
        pixmap = QPixmap.fromImage(image)
        assert pixmap.width() > 0 and pixmap.height() > 0, "The pixmap being saved is null! This should not be possible!"
        pixmap.save(map_sprite_filename, 'png')

        # Now convert it back to alpha
        image = level_directory + '/MapSprite.png'
        self.set_image(image)

        tile_data_filename = level_directory + '/TileData.png'
        self.write_tile_data(tile_data_filename)

        tile_info_filename = level_directory + '/tileInfo.txt'
        self.write_tile_info(tile_info_filename)

        unit_level_filename = level_directory + '/UnitLevel.txt'
        self.write_unit_level(unit_level_filename)

        self.directory = level_directory  # New level directory
        level_editor_config = str(QDir.currentPath() + '/le_config.txt')
        with open(level_editor_config, 'w') as fp:
            fp.write(os.path.relpath(str(self.directory)))

        print('Saved Level' + self.current_level_name)
        return True

    # === Create Menu ===
    def create_actions(self):
        self.new_act = QAction("&New...", self, shortcut="Ctrl+N", triggered=self.new)
        self.open_act = QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.save_act = QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        self.save_as_act = QAction("&Save As...", self, shortcut="Ctrl+Shift+S", triggered=self.save_as)
        self.exit_act = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.import_act = QAction("&Import Map...", self, shortcut="Ctrl+I", triggered=self.import_new_map)
        self.autotiles_act = QAction("Generate Autotiles...", self, triggered=self.generate_autotiles)
        self.reload_act = QAction("&Reload", self, shortcut="Ctrl+R", triggered=self.load_data)
        self.about_act = QAction("&About", self, triggered=self.about)

    def create_menus(self):
        file_menu = QMenu("&File", self)
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.save_as_act)
        file_menu.addSeparator()
        file_menu.addAction(self.import_act)
        file_menu.addAction(self.autotiles_act)
        file_menu.addAction(self.reload_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        help_menu = QMenu("&Help", self)
        help_menu.addAction(self.about_act)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(help_menu)

    def create_dock_windows(self):
        self.docks = {}
        self.docks['Properties'] = Dock("Properties", self)
        self.docks['Properties'].setAllowedAreas(Qt.LeftDockWidgetArea)
        self.properties_menu = PropertyMenu.PropertyMenu(self)
        self.docks['Properties'].setWidget(self.properties_menu)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.docks['Properties'])

        self.docks['Terrain'] = Dock("Terrain", self)
        self.docks['Terrain'].setAllowedAreas(Qt.RightDockWidgetArea)
        self.terrain_menu = Terrain.TerrainMenu(self.tile_data, self.view, self)
        self.docks['Terrain'].setWidget(self.terrain_menu)
        self.addDockWidget(Qt.RightDockWidgetArea, self.docks['Terrain'])

        self.docks['Event Tiles'] = Dock("Event Tiles", self)
        self.docks['Event Tiles'].setAllowedAreas(Qt.RightDockWidgetArea)
        self.tile_info_menu = TileInfo.TileInfoMenu(self.view, self)
        self.docks['Event Tiles'].setWidget(self.tile_info_menu)
        self.addDockWidget(Qt.RightDockWidgetArea, self.docks['Event Tiles'])

        self.docks['Factions'] = Dock("Factions", self)
        self.docks['Factions'].setAllowedAreas(Qt.LeftDockWidgetArea)
        self.faction_menu = Faction.FactionMenu(self.unit_data, self.view, self)
        self.docks['Factions'].setWidget(self.faction_menu)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.docks['Factions'])

        self.docks['Units'] = Dock("Units", self)
        self.docks['Units'].setAllowedAreas(Qt.RightDockWidgetArea)
        self.unit_menu = UnitData.UnitMenu(self.unit_data, self.view, self)
        self.docks['Units'].setWidget(self.unit_menu)
        self.addDockWidget(Qt.RightDockWidgetArea, self.docks['Units'])

        self.docks['Reinforcements'] = Dock("Reinforcements", self)
        self.docks['Reinforcements'].setAllowedAreas(Qt.RightDockWidgetArea)
        self.reinforcement_menu = UnitData.ReinforcementMenu(self.unit_data, self.view, self)
        self.docks['Reinforcements'].setWidget(self.reinforcement_menu)
        self.addDockWidget(Qt.RightDockWidgetArea, self.docks['Reinforcements'])

        self.docks['Move Triggers'] = Dock("Move Triggers", self)
        self.docks['Move Triggers'].setAllowedAreas(Qt.LeftDockWidgetArea)
        self.trigger_menu = Triggers.TriggerMenu(self.unit_data, self.view, self)
        self.docks['Move Triggers'].setWidget(self.trigger_menu)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.docks['Move Triggers'])

        # Left
        self.tabifyDockWidget(self.docks['Properties'], self.docks['Factions'])
        self.tabifyDockWidget(self.docks['Factions'], self.docks['Move Triggers'])
        self.docks['Properties'].raise_()  # GODDAMN FINDING THIS FUNCTION TOOK A LONG TIME

        # Right
        self.tabifyDockWidget(self.docks['Terrain'], self.docks['Event Tiles'])
        self.tabifyDockWidget(self.docks['Event Tiles'], self.docks['Units'])
        self.tabifyDockWidget(self.docks['Units'], self.docks['Reinforcements'])
        self.docks['Units'].raise_()

        self.dock_visibility = {k: False for k in self.docks.keys()}

        # Remove ability for docks to be moved.
        for name, dock in self.docks.items():
            dock.setFeatures(QDockWidget.NoDockWidgetFeatures)

    def maybe_save(self):
        if self.modified:
            ret = QMessageBox.warning(self, "Level Editor", "The level may have been modified.\n"
                                            "Do you want to save your changes?",
                                            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ret == QMessageBox.Save:
                return self.save()
            elif ret == QMessageBox.Cancel:
                return False

        return True

    # def eventFilter(self, obj, event):
    #     if event.type() == QEvent.WindowActivate:
    #         print "widget window has gained focus"
    #         # self.load_data()
    #     elif event.type() == QEvent.WindowDeactivate:
    #         print "widget window has lost focus"
    #     elif event.type() == QEvent.FocusIn:
    #         print "widget has gained keyboard focus"
    #     elif event.type() == QEvent.FocusOut:
    #         print "widget has lost keyboard focus"
    #     return super(MainEditor, self).eventFilter(obj, event)

    def about(self):
        QMessageBox.about(self, "About Lex Talionis",
            "<p>This is the <b>Lex Talionis</b> Level Editor.</p>"
            "<p>Check out https://gitlab.com/rainlash/lex-talionis/wikis/home "
            "for more information and helpful tutorials.</p>"
            "<p>This program has been freely distributed under the MIT License.</p>"
            "<p>Copyright 2014-2019 rainlash.</p>")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainEditor()
    # Engine.remove_display()
    window.show()
    app.exec_()
