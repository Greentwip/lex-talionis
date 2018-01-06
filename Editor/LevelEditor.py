from collections import OrderedDict
import sys, os

from PyQt4 import QtGui, QtCore

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad

import ParsedData
import PropertyMenu, TerrainMenu

class MainView(QtGui.QGraphicsView):
    def __init__(self):
        QtGui.QGraphicsView.__init__(self)
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMinimumSize(15*16, 10*16)

        self.image = None

    def set_new_image(self, image):
        self.image = QtGui.QImage(image)
        self.disp_main_map()

    def disp_main_map(self):
        self.scene.addPixmap(QtGui.QPixmap.fromImage(self.image))

    def clear_image(self):
        self.scene.clear()

    def add_image(self):
        levelfolder = '../Data/LevelDEBUG'
        self.image = QtGui.QImage(levelfolder + '/MapSprite.png')
        self.disp_main_map()

    def disp_tile_data(self, tile_data):
        self.clear_image()

        new_image = self.image.copy()

        painter = QtGui.QPainter()
        painter.begin(new_image)
        for coord, color in tile_data.iteritems():
            color = QtGui.QColor(color)
            color.setAlpha(192)
            painter.fillRect(coord[0] * 16, coord[1] * 16, 16, 16, color)
        painter.end()

        self.scene.addPixmap(QtGui.QPixmap.fromImage(new_image))

class MainEditor(QtGui.QMainWindow):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Level Editor v0.7.0')

        self.view = MainView()
        self.setCentralWidget(self.view)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')

        self.current_level_num = None

        self.create_actions()
        self.create_menus()
        self.create_dock_windows()

        # self.resize(640, 480)

        # Data
        self.tile_data = ParsedData.TileData()
        self.tile_info = ParsedData.TileInfo()
        self.overview_dict = OrderedDict()
        self.unit_data = ParsedData.UnitData()

        # Whether anything has changed since the last save
        self.modified = False

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def new(self):
        if self.maybe_save():
            self.new_level()

    def new_level(self):
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Map PNG", QtCore.QDir.currentPath(),
                                                  "PNG Files (*.png);;All Files (*)")
        if image_file:
            image = QtGui.QImage(image_file)
            if image.width() % 16 != 0 or image.height() % 16 != 0:
                QtGui.QErrorMessage().showMessage("Image width and/or height is not divisible by 16!")
                return
            self.view.clear_image()
            self.view.set_new_image(image_file)

            self.properties_menu.new()

    def open(self):
        if self.maybe_save():
            # "Levels (Level*);;All Files (*)",
            starting_path = QtCore.QDir.currentPath() + '/../Data'
            print('Starting Path')
            print(starting_path)
            directory = QtGui.QFileDialog.getExistingDirectory(self, "Choose Level", starting_path,
                                                               QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontResolveSymlinks)
            if directory:
                # Get the current level num
                if 'Level' in str(directory):
                    idx = str(directory).index('Level')
                    num = str(directory)[idx + 5:]
                    print('Level num')
                    print(num)
                    self.current_level_num = num
                self.load_level(directory)

    def load_level(self, directory):
        self.view.clear_image()
        image = directory + '/MapSprite.png'
        self.view.set_new_image(image)

        tilefilename = directory + '/TileData.png'
        print(tilefilename)
        self.tile_data.set_tile_data(tilefilename)

        overview_filename = directory + '/overview.txt'
        self.overview_dict = SaveLoad.read_overview_file(overview_filename)
        self.properties_menu.load(self.overview_dict)

        tile_info_filename = directory + '/tileInfo.txt'
        self.tile_info.load(tile_info_filename)

        unit_level_filename = directory + '/UnitLevel.txt'
        self.unit_data.clear()
        self.unit_data.load(unit_level_filename)

        if self.current_level_num:
            print('Loaded Level' + self.current_level_num)

        self.view.clear_image()
        self.view.disp_tile_data(self.tile_data.get_tile_data())

    def write_overview(self, fp):
        with open(fp, 'w') as overview:
            for k, v in self.overview_dict.iteritems():
                if v:
                    overview.write(k + ';' + v + '\n')

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

        print('Saved Level' + num)

    def create_actions(self):
        self.new_act = QtGui.QAction("&New...", self, shortcut="Ctrl+N", triggered=self.new)
        self.open_act = QtGui.QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.save_act = QtGui.QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        self.exit_act = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)

    def create_menus(self):
        file_menu = QtGui.QMenu("&File", self)
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.save_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        self.view_menu = QtGui.QMenu("&View", self)

        help_menu = QtGui.QMenu("&Help", self)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(self.view_menu)
        self.menuBar().addMenu(help_menu)

    def create_dock_windows(self):
        self.properties_dock = QtGui.QDockWidget("Properties", self)
        self.properties_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.properties_menu = PropertyMenu.PropertyMenu()
        self.properties_dock.setWidget(self.properties_menu)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.properties_dock)
        self.view_menu.addAction(self.properties_dock.toggleViewAction())

        self.terrain_dock = QtGui.QDockWidget("Terrain", self)
        self.terrain_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.terrain_menu = TerrainMenu.TerrainMenu(GC.TERRAINDATA)
        self.terrain_dock.setWidget(self.terrain_menu)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.terrain_dock)
        self.view_menu.addAction(self.terrain_dock.toggleViewAction())

        self.tile_info_dock = QtGui.QDockWidget("Tile Info", self)
        self.tile_info_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Choose Tile Information Here")
        self.tile_info_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.tile_info_dock)
        self.view_menu.addAction(self.tile_info_dock.toggleViewAction())

        self.group_dock = QtGui.QDockWidget("Groups", self)
        self.group_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Create Groups Here")
        self.group_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.group_dock)
        self.view_menu.addAction(self.group_dock.toggleViewAction())

        self.unit_dock = QtGui.QDockWidget("Units", self)
        self.unit_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        label = QtGui.QLabel("Create Units Here")
        self.unit_dock.setWidget(label)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.unit_dock)
        self.view_menu.addAction(self.unit_dock.toggleViewAction())

        self.tabifyDockWidget(self.terrain_dock, self.tile_info_dock)
        self.tabifyDockWidget(self.tile_info_dock, self.group_dock)
        self.tabifyDockWidget(self.group_dock, self.unit_dock)

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

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = MainEditor()
    # Engine.remove_display()
    window.show()
    app.exec_()
