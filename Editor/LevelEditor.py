from collections import OrderedDict
import sys, os

from PyQt4 import QtGui, QtCore

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad
from Code.imagesDict import COLORKEY

import PropertyMenu, Terrain, TileInfo, UnitData, EditorUtilities, Faction, QtWeather
from DataImport import Data

# TODO: Reinforcements -- impl
# TODO: Created Units -- maybe not
# TODO: Load new Map button -- impl
# TODO: Refresh button (also on losing and gaining focus) -- impl
# TODO: Highlight current unit -- impl
# TODO: Add color to text when unit isn't positioned -- impl
# TODO: Add Del key to Units -- impl
# TODO: Add Autotile support to map -- impl
# TODO: Add Weather to map -- impl
# TODO: Droppable and Equippable Item support -- impl
# TODO: Class sprites move -- impl
# TODO: Highlight dances -- maybe not
# TODO: Items displyed next to unit names in Units and Reinforcements -- impl
# TODO: Update status bar

class MainView(QtGui.QGraphicsView):
    def __init__(self, tile_data, tile_info, unit_data, window=None):
        QtGui.QGraphicsView.__init__(self)
        self.window = window
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMinimumSize(15*16, 10*16)
        self.setMouseTracking(True)
        # self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)

        self.image = None
        self.working_image = None
        # self.tool = None
        # Data
        self.tile_data = tile_data
        self.tile_info = tile_info
        self.unit_data = unit_data

        self.screen_scale = 1

    def set_new_image(self, image):
        self.image = QtGui.QImage(image)
        # Handle colorkey
        qCOLORKEY = QtGui.qRgb(*COLORKEY)
        new_color = QtGui.qRgba(0, 0, 0, 0)
        for x in xrange(self.image.width()):
            for y in xrange(self.image.height()):
                if self.image.pixel(x, y) == qCOLORKEY:
                    self.image.setPixel(x, y, new_color)

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.working_image:
            self.clear_scene()
            self.scene.addPixmap(QtGui.QPixmap.fromImage(self.working_image))

    def disp_main_map(self):
        if self.image:
            image = self.window.autotiles.draw()
            if image:
                image = image.copy()
                painter = QtGui.QPainter()
                painter.begin(image)
                painter.drawImage(0, 0, self.image.copy())
                painter.end()
                self.working_image = image
            else:
                self.working_image = self.image.copy()

    def disp_weather(self):
        if self.working_image:
            painter = QtGui.QPainter()
            painter.begin(self.working_image)
            for weather in self.window.weather:
                particles = weather.draw()
                for image, coord in particles:
                    painter.drawImage(coord[0], coord[1], image)
            painter.end()

    def disp_tile_data(self):
        if self.working_image:
            painter = QtGui.QPainter()
            painter.begin(self.working_image)
            for coord, color in self.tile_data.tiles.iteritems():
                write_color = QtGui.QColor(color[0], color[1], color[2])
                write_color.setAlpha(192)
                painter.fillRect(coord[0] * 16, coord[1] * 16, 16, 16, write_color)
            painter.end()

    def disp_tile_info(self):
        if self.working_image:
            painter = QtGui.QPainter()
            painter.begin(self.working_image)
            for coord, image in self.tile_info.get_images().iteritems():
                painter.drawImage(coord[0] * 16 + 1, coord[1] * 16, image)
            painter.end()

    def disp_units(self):
        if self.working_image:
            painter = QtGui.QPainter()
            painter.begin(self.working_image)
            for coord, unit_image in self.unit_data.get_unit_images().iteritems():
                if unit_image:
                    painter.drawImage(coord[0] * 16 - 4, coord[1] * 16 - 6, unit_image)
            # Highlight current unit
            current_unit = self.window.unit_menu.get_current_unit()
            if current_unit and current_unit.position:
                painter.drawImage(current_unit.position[0] * 16 - 8, current_unit.position[1] * 16 - 5, EditorUtilities.create_cursor())
            painter.end()

    def disp_reinforcements(self):
        if self.working_image:
            painter = QtGui.QPainter()
            painter.begin(self.working_image)
            for coord, unit_image in self.unit_data.get_reinforcement_images(self.window.reinforcement_menu.current_pack()).iteritems():
                if unit_image:
                    painter.drawImage(coord[0] * 16 - 4, coord[1] * 16 - 6, unit_image)
            # Highlight current unit
            current_unit = self.window.reinforcement_menu.get_current_unit()
            if current_unit and current_unit.position:
                painter.drawImage(current_unit.position[0] * 16 - 8, current_unit.position[1] * 16 - 5, EditorUtilities.create_cursor())
            painter.end()

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)
        if pixmap and pos in self.tile_data.tiles:
            # print('mousePress Tool: %s' % self.tool)
            # if self.window.dock_visibility['Terrain'] and self.tool == 'Terrain':
            if self.window.dock_visibility['Terrain']:
                if event.button() == QtCore.Qt.LeftButton:
                    current_color = self.window.terrain_menu.get_current_color()
                    self.tile_data.tiles[pos] = current_color
                    self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    current_color = self.tile_data.tiles[pos]
                    self.window.terrain_menu.set_current_color(current_color)
            # elif self.window.dock_visibility['Tile Info'] and self.tool == 'Tile Info':
            elif self.window.dock_visibility['Tile Info']:
                if event.button() == QtCore.Qt.LeftButton:
                    name = self.window.tile_info_menu.get_current_name()
                    value = self.window.tile_info_menu.start_dialog(self.tile_info.get(pos))
                    if value:
                        self.tile_info.set(pos, name, value)
                        self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    self.tile_info.delete(pos)
                    self.window.update_view()
            # elif self.window.dock_visibility['Units'] and self.tool not in ('Terrain', 'Tile Info', 'Reinforcements'):
            elif self.window.dock_visibility['Units']:
                if event.button() == QtCore.Qt.LeftButton:
                    current_unit = self.window.unit_menu.get_current_unit()
                    if current_unit:
                        under_unit = self.unit_data.get_unit_from_pos(pos)
                        if under_unit:
                            print('Removing Unit')
                            under_unit.position = None
                            self.window.unit_menu.get_item_from_unit(under_unit).setTextColor(QtGui.QColor("red"))
                        if current_unit.position:
                            print('Copy & Place Unit')
                            new_unit = current_unit.copy()
                            new_unit.position = pos
                            self.unit_data.add_unit(new_unit)
                            self.window.unit_menu.add_unit(new_unit)
                        else:
                            print('Place Unit')
                            current_unit.position = pos
                            # Reset the color
                            self.window.unit_menu.get_current_item().setTextColor(QtGui.QColor("black"))
                        self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    current_idx = self.unit_data.get_idx_from_pos(pos)
                    print('Current IDX %s' % current_idx)
                    if current_idx >= 0:
                        self.window.unit_menu.set_current_idx(current_idx)
            # elif self.window.dock_visibility['Reinforcements'] and self.tool == 'Reinforcements':
            elif self.window.dock_visibility['Reinforcements']:
                if event.button() == QtCore.Qt.LeftButton:
                    current_unit = self.window.reinforcement_menu.get_current_unit()
                    if current_unit:
                        if current_unit.position:
                            print('Copy & Place Unit')
                            new_unit = current_unit.copy()
                            new_unit.position = pos
                            self.unit_data.add_reinforcement(new_unit)
                            self.window.reinforcement_menu.add_unit(new_unit)
                        else:
                            print('Place Unit')
                            current_unit.position = pos
                            # Reset the color
                            self.window.reinforcement_menu.get_current_item().setTextColor(QtGui.QColor("black"))
                        self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    current_idx = self.unit_data.get_ridx_from_pos(pos, self.window.reinforcement_menu.current_pack())
                    print(current_idx)
                    if current_idx >= 0:
                        self.window.reinforcement_menu.set_current_idx(current_idx)

    def mouseMoveEvent(self, event):
        # Do the parent's version
        QtGui.QGraphicsView.mouseMoveEvent(self, event)
        # Mine
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        if pixmap:
            pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)
            info = None
            if self.window.dock_visibility['Units'] and self.unit_data.get_unit_from_pos(pos):
                info = self.unit_data.get_unit_str(pos)
            elif self.window.dock_visibility['Reinforcements'] and self.unit_data.get_rein_from_pos(pos, self.window.reinforcement_menu.current_pack()):
                info = self.unit_data.get_reinforcement_str(pos, self.window.reinforcement_menu.current_pack())
            elif self.window.dock_visibility['Tile Info'] and self.tile_info.get(pos):
                info = self.tile_info.get_str(pos)
            elif self.window.dock_visibility['Terrain'] and pos in self.tile_data.tiles:
                hovered_color = self.tile_data.tiles[pos]
                # print('Hover', pos, hovered_color)
                info = self.window.terrain_menu.get_info_str(hovered_color)
            # print('mouseMove: %s' % info)
            if info:
                message = str(pos[0]) + ', ' + str(pos[1]) + ': ' + info
                self.window.status_bar.showMessage(message)

    def wheelEvent(self, event):
        if event.delta() > 0 and self.screen_scale < 4:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.delta() < 0 and self.screen_scale > 1:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

    def center_on_pos(self, pos):
        self.centerOn(pos[0] * 16, pos[1] * 16)
        self.window.update_view()

class Dock(QtGui.QDockWidget):
    def __init__(self, title, parent):
        super(Dock, self).__init__(title, parent)
        self.main_editor = parent
        self.visibilityChanged.connect(self.visible)

    def visible(self, visible):
        # print("%s's Visibility Changed to %s" %(self.windowTitle(), visible))
        self.main_editor.dock_visibility[str(self.windowTitle())] = visible
        self.main_editor.update_view()

class MainEditor(QtGui.QMainWindow):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Level Editor v' + GC.version)
        self.installEventFilter(self)

        # Data
        self.init_data()

        self.view = MainView(self.tile_data, self.tile_info, self.unit_data, self)
        self.setCentralWidget(self.view)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')

        self.directory = None
        self.current_level_name = None

        self.create_actions()
        self.create_menus()
        self.create_dock_windows()

        # Whether anything has changed since the last save
        self.modified = False

        # === Timing ===
        self.main_timer = QtCore.QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.main_timer.start(33)  # 30 FPS
        self.elapsed_timer = QtCore.QElapsedTimer()
        self.elapsed_timer.start()

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
        if self.dock_visibility['Tile Info']:
            self.view.disp_tile_info()
        if self.dock_visibility['Units']:
            self.view.disp_units()
        if self.dock_visibility['Reinforcements']:
            self.view.disp_reinforcements()
        if self.weather:
            self.view.disp_weather()
        self.view.show_image()

    # === Loading Data ===
    def set_image(self, image_file):
        image = QtGui.QImage(image_file)
        if image.width() % 16 != 0 or image.height() % 16 != 0:
            QtGui.QErrorMessage().showMessage("Image width and/or height is not divisible by 16!")
            return
        self.view.clear_scene()
        self.view.set_new_image(image_file)

    def new(self):
        if self.maybe_save():
            self.new_level()

    def new_level(self):
        if self.maybe_save():
            image_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Map PNG", QtCore.QDir.currentPath(),
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

    def import_new_map(self):
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Map PNG", QtCore.QDir.currentPath(),
                                                       "PNG Files (*.png);;All Files (*)")
        if image_file:
            self.set_image(image_file)
            self.tile_data.new(image_file)
            self.update_view()

    def open(self):
        if self.maybe_save():
            # "Levels (Level*);;All Files (*)",
            starting_path = QtCore.QDir.currentPath() + '/../Data'
            directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Level", starting_path,
                                                               QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontResolveSymlinks)
            if directory:
                # Get the current level num
                if 'Level' in str(directory):
                    idx = str(directory).index('Level')
                    num = str(directory)[idx + 5:]
                    self.current_level_name = num
                self.directory = directory
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
        print('Add Weather')
        print(weather)
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

    def remove_weather(self, name):
        self.weather = [weather for weather in self.weather if weather.name != name]

    # === Save ===
    def write_overview(self, fp):
        with open(fp, 'w') as overview:
            for k, v in self.overview_dict.iteritems():
                if v:
                    overview.write(k + ';' + v + '\n')

    def write_tile_data(self, fp):
        if self.tile_data.width:
            image = QtGui.QImage(self.tile_data.width, self.tile_data.height, QtGui.QImage.Format_RGB32)
            painter = QtGui.QPainter()
            painter.begin(image)
            for coord, color in self.tile_data.tiles.iteritems():
                write_color = QtGui.QColor(color[0], color[1], color[2])
                painter.fillRect(coord[0], coord[1], 1, 1, write_color)
            painter.end()
            pixmap = QtGui.QPixmap.fromImage(image)
            pixmap.save(fp, 'png')

    def write_tile_info(self, fp):
        with open(fp, 'w') as tile_info:
            for coord, properties in self.tile_info.tile_info_dict.iteritems():
                tile_info.write(str(coord[0]) + ',' + str(coord[1]) + ':')
                value = self.tile_info.get_str(coord)
                if value:
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
            pos_str = ','.join(str(p) for p in unit.position)
            ai_str = unit.ai + (('_' + str(unit.ai_group)) if unit.ai_group else '') 
            event_id_str = (unit.pack + '_' + unit.event_id if unit.pack != 'None' else unit.event_id) if unit.event_id else '0'
            if unit.generic:
                item_strs = ','.join(get_item_str(item) for item in unit.items)
                klass_str = unit.klass + ('F' if unit.gender >= 5 else '')
                order = (unit.team, '0', event_id_str, klass_str, str(unit.level), item_strs, pos_str, ai_str, unit.faction)
            else:
                order = (unit.team, '1' if unit.saved else '0', event_id_str, unit.name, pos_str, ai_str)
            unit_level.write(';'.join(order) + '\n')

        def write_units(units):
            # Player units
            player_units = [unit for unit in units if unit.team == 'player']
            unit_level.write('# Player Characters\n')
            for unit in player_units:
                write_unit_line(unit)
            # Other units
            other_units = [unit for unit in units if unit.team == 'other']
            if other_units:
                unit_level.write('# Other Characters\n')
                for unit in other_units:
                    write_unit_line(unit)
            # Enemies
            unit_level.write('# Enemies\n')
            for team in ('enemy', 'enemy2'):
                # Named enemy characters
                named_enemies = [unit for unit in units if unit.team == team and not unit.generic]
                if named_enemies:
                    unit_level.write('# Bosses\n')
                    for unit in named_enemies:
                        write_unit_line(unit)
                # Generic enemy characters
                generic_enemies = [unit for unit in units if unit.team == team and unit.generic]
                if generic_enemies:
                    unit_level.write('# Generics\n')
                    for unit in generic_enemies:
                        write_unit_line(unit)

        with open(fp, 'w') as unit_level:
            unit_level.write(EditorUtilities.unit_level_header)
            factions = self.unit_data.factions
            if self.unit_data.load_player_characters:
                unit_level.write('load_player_characters\n')
            for faction in factions.values():
                unit_level.write('faction;' + faction.faction_id + ';' + faction.unit_name + 
                                 ';' + faction.faction_icon + ';' + faction.desc + '\n')
            # Units
            units = [unit for unit in self.unit_data.units if unit.position]
            reinforcements = [rein for rein in self.unit_data.reinforcements]
            write_units(units)
            unit_level.write('# === Reinforcements ===\n')
            write_units(reinforcements)

    def save(self):
        new = False
        if not self.current_level_name:
            text, ok = QtGui.QInputDialog.getText(self, "Level Editor", "Enter Level Number:")
            if ok:
                self.current_level_name = text
            else:
                return
            new = True

        data_directory = QtCore.QDir.currentPath() + '/../Data'
        level_directory = data_directory + '/Level' + self.current_level_name
        if new:
            if os.path.exists(level_directory):
                ret = QtGui.QMessageBox.warning(self, "Level Editor", "A level with that number already exists!\n"
                                                "Do you want to overwrite it?",
                                                QtGui.QMessageBox.Save | QtGui.QMessageBox.Cancel)
                if ret == QtGui.QMessageBox.Cancel:
                    return
            else:
                os.mkdir(level_directory)

        overview_filename = level_directory + '/overview.txt'
        self.overview_dict = self.properties_menu.save()
        self.write_overview(overview_filename)

        tile_data_filename = level_directory + '/TileData.png'
        self.write_tile_data(tile_data_filename)

        tile_info_filename = level_directory + '/TileInfo.txt'
        self.write_tile_info(tile_info_filename)

        unit_level_filename = level_directory + '/UnitLevel.txt'
        self.write_unit_level(unit_level_filename)

        print('Saved Level' + self.current_level_name)

    # === Create Menu ===
    def create_actions(self):
        self.new_act = QtGui.QAction("&New...", self, shortcut="Ctrl+N", triggered=self.new)
        self.open_act = QtGui.QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.save_act = QtGui.QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        self.exit_act = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.import_act = QtGui.QAction("&Import Map...", self, shortcut="Ctrl+I", triggered=self.import_new_map)
        self.reload_act = QtGui.QAction("&Reload", self, shortcut="Ctrl+R", triggered=self.load_data)
        self.about_act = QtGui.QAction("&About", self, triggered=self.about)

    def create_menus(self):
        file_menu = QtGui.QMenu("&File", self)
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.save_act)
        file_menu.addSeparator()
        file_menu.addAction(self.import_act)
        file_menu.addAction(self.reload_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        # self.view_menu = QtGui.QMenu("&View", self)

        help_menu = QtGui.QMenu("&Help", self)
        help_menu.addAction(self.about_act)

        self.menuBar().addMenu(file_menu)
        # self.menuBar().addMenu(self.view_menu)
        self.menuBar().addMenu(help_menu)

    def create_dock_windows(self):
        self.docks = {}
        self.docks['Properties'] = Dock("Properties", self)
        self.docks['Properties'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.properties_menu = PropertyMenu.PropertyMenu(self)
        self.docks['Properties'].setWidget(self.properties_menu)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.docks['Properties'])
        # self.view_menu.addAction(self.docks['Properties'].toggleViewAction())

        self.docks['Terrain'] = Dock("Terrain", self)
        self.docks['Terrain'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.terrain_menu = Terrain.TerrainMenu(self.view, self)
        self.docks['Terrain'].setWidget(self.terrain_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Terrain'])
        # self.view_menu.addAction(self.docks['Terrain'].toggleViewAction())

        self.docks['Tile Info'] = Dock("Tile Info", self)
        self.docks['Tile Info'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.tile_info_menu = TileInfo.TileInfoMenu(self.view, self)
        self.docks['Tile Info'].setWidget(self.tile_info_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Tile Info'])
        # self.view_menu.addAction(self.docks['Tile Info'].toggleViewAction())

        self.docks['Factions'] = Dock("Factions", self)
        self.docks['Factions'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.faction_menu = Faction.FactionMenu(self.unit_data, self.view, self)
        self.docks['Factions'].setWidget(self.faction_menu)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.docks['Factions'])
        # self.view_menu.addAction(self.docks['Factions'].toggleViewAction())

        self.docks['Units'] = Dock("Units", self)
        self.docks['Units'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.unit_menu = UnitData.UnitMenu(self.unit_data, self.view, self)
        self.docks['Units'].setWidget(self.unit_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Units'])
        # self.view_menu.addAction(self.docks['Units'].toggleViewAction())

        self.docks['Reinforcements'] = Dock("Reinforcements", self)
        self.docks['Reinforcements'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.reinforcement_menu = UnitData.ReinforcementMenu(self.unit_data, self.view, self)
        self.docks['Reinforcements'].setWidget(self.reinforcement_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Reinforcements'])
        # self.view_menu.addAction(self.docks['Reinforcements'].toggleViewAction())

        # Left
        self.tabifyDockWidget(self.docks['Properties'], self.docks['Factions'])
        self.docks['Properties'].raise_()  # GODDAMN FINDING THIS FUNCTION TOOK A LONG TIME

        # Right
        self.tabifyDockWidget(self.docks['Terrain'], self.docks['Tile Info'])
        self.tabifyDockWidget(self.docks['Tile Info'], self.docks['Units'])
        self.tabifyDockWidget(self.docks['Units'], self.docks['Reinforcements'])
        self.docks['Units'].raise_()

        self.dock_visibility = {k: False for k in self.docks.keys()}

        # Remove ability for docks to be moved.
        for name, dock in self.docks.iteritems():
            dock.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)

    def maybe_save(self):
        if self.modified:
            ret = QtGui.QMessageBox.warning(self, "Level Editor", "The level has been modified.\n"
                                            "Do you want to save your changes?",
                                            QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
            if ret == QtGui.QMessageBox.Save:
                return self.save()
            elif ret == QtGui.QMessageBox.Cancel:
                return False

        return True

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.WindowActivate:
            print "widget window has gained focus"
            # self.load_data()
        elif event.type() == QtCore.QEvent.WindowDeactivate:
            print "widget window has lost focus"
        elif event.type() == QtCore.QEvent.FocusIn:
            print "widget has gained keyboard focus"
        elif event.type() == QtCore.QEvent.FocusOut:
            print "widget has lost keyboard focus"
        return super(MainEditor, self).eventFilter(obj, event)

    def about(self):
        QtGui.QMessageBox.about(self, "About Lex Talionis",
            "<p>This is the <b>Lex Talionis</b> Engine Level Editor.</p>"
            "<p>Check out https://www.github.com/rainlash/lex-talionis "
            "for more information and helpful tutorials.</p>"
            "<p>This program has been freely distributed under the MIT License.</p>"
            "<p>Copyright 2014-2018 rainlash.</p>")

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = MainEditor()
    # Engine.remove_display()
    window.show()
    app.exec_()
