from collections import OrderedDict
import sys, os

from PyQt4 import QtGui, QtCore

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad

import PropertyMenu, Terrain, TileInfo, UnitData, EditorUtilities, Group

# TODO: Reinforcements
# TODO: Created Units
# TODO: Load new Map button
# TODO: Refresh button (also on losing and gaining focus)
# TODO: Highlight current unit
# TODO: Add color to text when unit isn't positioned
# TODO: Add Del key to Units
# TODO: Add Autotile support to map
# TODO: Add Weather to map
# TODO: Droppable and Equippable Item support
# TODO: Class sprites move
# TODO: Highlight dances

class MainView(QtGui.QGraphicsView):
    def __init__(self, tile_data, tile_info, unit_data, window=None):
        QtGui.QGraphicsView.__init__(self)
        self.window = window
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMinimumSize(15*16, 10*16)
        self.setMouseTracking(True)
        self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)

        self.image = None
        self.working_image = None
        self.tool = None
        # Data
        self.tile_data = tile_data
        self.tile_info = tile_info
        self.unit_data = unit_data

        self.screen_scale = 1

    def set_new_image(self, image):
        self.image = QtGui.QImage(image)

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.working_image:
            self.clear_scene()
            self.scene.addPixmap(QtGui.QPixmap.fromImage(self.working_image))

    def disp_main_map(self):
        if self.image:
            self.working_image = self.image.copy()

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
                painter.drawImage(coord[0] * 16, coord[1] * 16, image)
            painter.end()

    def disp_units(self):
        if self.working_image:
            painter = QtGui.QPainter()
            painter.begin(self.working_image)
            for coord, unit_image in self.unit_data.get_unit_images().iteritems():
                if unit_image:
                    painter.drawImage(coord[0] * 16, coord[1] * 16, unit_image)
            # Highlight current unit
            current_unit = self.window.unit_menu.get_current_unit()
            if current_unit and current_unit.position:
                painter.drawImage(current_unit.position[0] * 16 - 4, current_unit.position[1] * 16, EditorUtilities.create_cursor())
            painter.end()

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)
        if pixmap and pos in self.tile_data.tiles:
            # print('Press:', pos)
            if self.window.dock_visibility['Terrain'] and self.tool == 'Terrain':
                if event.button() == QtCore.Qt.LeftButton:
                    current_color = self.window.terrain_menu.get_current_color()
                    self.tile_data.tiles[pos] = current_color
                    self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    current_color = self.tile_data.tiles[pos]
                    self.window.terrain_menu.set_current_color(current_color)
            elif self.window.dock_visibility['Tile Info'] and self.tool == 'Tile Info':
                if event.button() == QtCore.Qt.LeftButton:
                    name = self.window.tile_info_menu.get_current_name()
                    value = self.window.tile_info_menu.start_dialog(self.tile_info.get(pos))
                    if value:
                        self.tile_info.set(pos, name, value)
                        self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    self.tile_info.delete(pos)
                    self.window.update_view()
            elif self.window.dock_visibility['Units'] and self.tool == 'Units':
                if event.button() == QtCore.Qt.LeftButton:
                    current_unit = self.window.unit_menu.get_current_unit()
                    if current_unit:
                        under_unit = self.unit_data.get_unit_from_pos(pos)
                        if under_unit:
                            under_unit.position = None
                        if current_unit.position:
                            new_unit = current_unit.copy()
                            self.unit_data.add_unit(new_unit)
                            self.window.unit_menu.add_unit(new_unit)
                        else:
                            current_unit.position = pos
                            # Reset the color
                            self.window.unit_menu.get_current_item().setTextColor(QtGui.QColor("black"))
                        self.window.update_view()
                elif event.button() == QtCore.Qt.RightButton:
                    current_idx = self.unit_data.get_idx_from_pos(pos)
                    if current_idx >= 0:
                        self.window.unit_menu.set_current_idx(current_idx)

    def mouseMoveEvent(self, event):
        # Do the parent's version
        QtGui.QGraphicsView.mouseMoveEvent(self, event)
        # Mine
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        if pixmap:
            pos = int(scene_pos.x() / 16), int(scene_pos.y() / 16)
            if self.window.dock_visibility['Units'] and self.unit_data.get_unit_from_pos(pos):
                info = self.unit_data.get_unit_str(pos)
                message = str(pos[0]) + ',' + str(pos[1]) + ': ' + info
                self.window.status_bar.showMessage(message)
            elif self.window.dock_visibility['Tile Info'] and self.tile_info.get(pos):
                info = self.tile_info.get_str(pos)
                message = str(pos[0]) + ', ' + str(pos[1]) + ': ' + info
                self.window.status_bar.showMessage(message)
            elif self.window.dock_visibility['Terrain'] and pos in self.tile_data.tiles:
                hovered_color = self.tile_data.tiles[pos]
                # print('Hover', pos, hovered_color)
                info = self.window.terrain_menu.get_info_str(hovered_color)
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
        self.tile_data = Terrain.TileData()
        self.tile_info = TileInfo.TileInfo()
        self.overview_dict = OrderedDict()
        self.unit_data = UnitData.UnitData()

        self.view = MainView(self.tile_data, self.tile_info, self.unit_data, self)
        self.setCentralWidget(self.view)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')

        self.directory = None
        self.current_level_num = None

        self.create_actions()
        self.create_menus()
        self.create_dock_windows()

        # Whether anything has changed since the last save
        self.modified = False

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
        self.view.show_image()

    def set_image(self, image_file):
        image = QtGui.QImage(image_file)
        if image.width() % 16 != 0 or image.height() % 16 != 0:
            QtGui.QErrorMessage().showMessage("Image width and/or height is not divisible by 16!")
            return
        self.view.clear_image()
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
                self.properties_menu.new()

    def import_new_map(self):
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Map PNG", QtCore.QDir.currentPath(),
                                                       "PNG Files (*.png);;All Files (*)")
        if image_file:
            self.set_image(image_file)
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
                    self.current_level_num = num
                self.directory = directory
                self.load_level()

    def load_level(self):
        image = self.directory + '/MapSprite.png'
        self.view.set_new_image(image)

        tilefilename = self.directory + '/TileData.png'
        self.tile_data.load(tilefilename)

        overview_filename = self.directory + '/overview.txt'
        self.overview_dict = SaveLoad.read_overview_file(overview_filename)
        self.properties_menu.load(self.overview_dict)

        tile_info_filename = self.directory + '/tileInfo.txt'
        self.tile_info.load(tile_info_filename)

        unit_level_filename = self.directory + '/UnitLevel.txt'
        self.unit_data.load(unit_level_filename)
        self.group_menu.load(self.unit_data)
        self.unit_menu.load(self.unit_data)

        if self.current_level_num:
            self.status_bar.showMessage('Loaded Level' + self.current_level_num)

        self.update_view()

    def write_overview(self, fp):
        with open(fp, 'w') as overview:
            for k, v in self.overview_dict.iteritems():
                if v:
                    overview.write(k + ';' + v + '\n')

    def write_tile_data(self, fp):
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
                tile_info.write(coord[0] + ',' + coord[1] + ':')
                value = self.tile_info.get_info_str(coord)
                if value:
                    tile_info.write(value + '\n')

    def write_unit_level(self, fp):
        def get_item_str(item):
            item_str = item.id
            if item.droppable:
                item_str = 'd' + item_str
            elif item.event:
                item_str = 'e' + item_str

        def write_unit_line(unit):
            pos_str = ','.join(str(p) for p in unit.position)
            ai_str = unit.ai + (('_' + str(unit.ai_group)) if unit.ai_group else '') 
            if unit.generic:
                item_strs = ','.join(get_item_str(item) for item in unit.items)
                klass_str = unit.klass + unit.gender
                order = (unit.team, '0', '0', klass_str, str(unit.level), item_strs, pos_str, ai_str, unit.group)
            else:
                order = (unit.team, '1' if unit.saved else '0', '0', unit.name, pos_str, ai_str)
            unit_level.write(';'.join(order) + '\n')

        with open(fp, 'w') as unit_level:
            unit_level.write(EditorUtilities.unit_level_header)
            groups = self.unit_data.groups
            if self.unit_data.load_all_player_characters:
                unit_level.write('load_all_player_characters\n')
            for group in groups:
                unit_level.write('group;' + group.group_id + ';' + group.unit_name + 
                                 ';' + group.faction + ';' + group.desc + '\n')
            # Units
            units = [unit for unit in self.unit_data if unit.position]
            # Player units
            player_units = [unit for unit in units if unit.team == 'player' and unit.position]
            unit_level.write('# Player Characters\n')
            for unit in player_units:
                write_unit_line(unit)
            # Other units
            other_units = [unit for unit in self.unit if unit.team == 'other']
            if other_units:
                unit_level.write('# Other Characters\n')
                for unit in other_units:
                    write_unit_line(unit)
            # Named enemy characters
            unit_level.write('# Enemies')
            named_enemies = [unit for unit in units if unit.team == 'enemy' and not unit.generic]
            if named_enemies:
                unit_level.write('# Bosses\n')
                for unit in named_enemies:
                    write_unit_line(unit)
            # Generic enemy characters
            generic_enemies = [unit for unit in units if unit.team == 'enemy' and not unit.generic]
            unit_level.write('# Generics\n')
            for unit in generic_enemies:
                write_unit_line(unit)

    def save(self):
        # Find what the next unused num is 
        if not self.current_level_num:
            self.current_level_num = 'test'
        self.save_level(self.current_level_num)

    def save_level(self, num):
        data_directory = QtCore.QDir.currentPath() + '/../Data'
        level_directory = data_directory + '/Level' + num
        if not os.path.exists(level_directory):
            os.mkdir(level_directory)

        overview_filename = level_directory + '/overview.txt'
        self.overview_dict = self.properties_menu.save()
        self.write_overview(overview_filename)

        tile_data_filename = level_directory + '/TileData.png'
        self.write_tile_data(tile_data_filename)

        tile_info_filename = level_directory + '/TileInfo.txt'
        self.write_tile_info(tile_info_filename)

        unit_level_filename = level_directory + '/UnitLevel.txt'
        self.write_unit_data(unit_level_filename)

        print('Saved Level' + num)

    def create_actions(self):
        self.new_act = QtGui.QAction("&New...", self, shortcut="Ctrl+N", triggered=self.new)
        self.open_act = QtGui.QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.save_act = QtGui.QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        self.exit_act = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.import_act = QtGui.QAction("&Import Map...", self, shortcut="Ctrl+I", triggered=self.import_new_map)
        self.reload_act = QtGui.QAction("&Reload", self, shortcut="Ctrl+R", triggered=self.load_level)
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

        self.view_menu = QtGui.QMenu("&View", self)

        help_menu = QtGui.QMenu("&Help", self)
        help_menu.addAction(self.about_act)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(self.view_menu)
        self.menuBar().addMenu(help_menu)

    def create_dock_windows(self):
        self.docks = {}
        self.docks['Properties'] = Dock("Properties", self)
        self.docks['Properties'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.properties_menu = PropertyMenu.PropertyMenu(self)
        self.docks['Properties'].setWidget(self.properties_menu)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.docks['Properties'])
        self.view_menu.addAction(self.docks['Properties'].toggleViewAction())

        self.docks['Terrain'] = Dock("Terrain", self)
        self.docks['Terrain'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.terrain_menu = Terrain.TerrainMenu(GC.TERRAINDATA, self.view, self)
        self.docks['Terrain'].setWidget(self.terrain_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Terrain'])
        self.view_menu.addAction(self.docks['Terrain'].toggleViewAction())

        self.docks['Tile Info'] = Dock("Tile Info", self)
        self.docks['Tile Info'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.tile_info_menu = TileInfo.TileInfoMenu(self.view, self)
        self.docks['Tile Info'].setWidget(self.tile_info_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Tile Info'])
        self.view_menu.addAction(self.docks['Tile Info'].toggleViewAction())

        self.docks['Groups'] = Dock("Groups", self)
        self.docks['Groups'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.group_menu = Group.GroupMenu(self.unit_data, self.view, self)
        self.docks['Groups'].setWidget(self.group_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Groups'])
        self.view_menu.addAction(self.docks['Groups'].toggleViewAction())

        self.docks['Units'] = Dock("Units", self)
        self.docks['Units'].setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.unit_menu = UnitData.UnitMenu(self.unit_data, self.view, self)
        self.docks['Units'].setWidget(self.unit_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks['Units'])
        self.view_menu.addAction(self.docks['Units'].toggleViewAction())

        self.tabifyDockWidget(self.docks['Terrain'], self.docks['Tile Info'])
        self.tabifyDockWidget(self.docks['Tile Info'], self.docks['Groups'])
        self.tabifyDockWidget(self.docks['Groups'], self.docks['Units'])

        self.dock_visibility = {k: False for k in self.docks.keys()}

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
