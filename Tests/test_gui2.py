from PyQt4 import QtGui, QtCore
import sys
sys.path.append('../')
import Code.configuration as cf
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad

import Code.ItemMethods as ItemMethods
import Code.CustomObjects as CustomObjects
import Code.StatusObject as StatusObject

import Code.UnitSprite as UnitSprite

# === DATA IMPORTING ===
def build_units(class_dict):
    units = []
    for unit in GC.UNITDATA.getroot().findall('unit'):
        u_i = {}
        u_i['id'] = unit.find('id').text
        u_i['name'] = unit.get('name')

        classes = unit.find('class').text.split(',')
        u_i['klass'] = classes[-1]

        u_i['gender'] = unit.find('gender').text
        u_i['level'] = int(unit.find('level').text)
        u_i['faction'] = unit.find('faction').text

        stats = SaveLoad.intify_comma_list(unit.find('bases').text)
        for n in xrange(len(stats), cf.CONSTANTS['num_stats']):
            stats.append(class_dict[u_i['klass']]['bases'][n])
        assert len(stats) == cf.CONSTANTS['num_stats'], "bases %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])
        u_i['stats'] = SaveLoad.build_stat_dict(stats)
        # print("%s's stats: %s", u_i['name'], u_i['stats'])

        u_i['growths'] = SaveLoad.intify_comma_list(unit.find('growths').text)
        u_i['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(u_i['growths'])))
        assert len(u_i['growths']) == cf.CONSTANTS['num_stats'], "growths %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])

        u_i['items'] = ItemMethods.itemparser(unit.find('inventory').text)
        # Parse wexp
        u_i['wexp'] = unit.find('wexp').text.split(',')
        for index, wexp in enumerate(u_i['wexp'][:]):
            if wexp in CustomObjects.WEAPON_EXP.wexp_dict:
                u_i['wexp'][index] = CustomObjects.WEAPON_EXP.wexp_dict[wexp]
        u_i['wexp'] = [int(num) for num in u_i['wexp']]

        assert len(u_i['wexp']) == len(CustomObjects.WEAPON_TRIANGLE.types), "%s's wexp must have as many slots as there are weapon types."%(u_i['name'])
        
        u_i['desc'] = unit.find('desc').text
        # Tags
        u_i['tags'] = set(unit.find('tags').text.split(',')) if unit.find('tags') is not None and unit.find('tags').text is not None else set()

        # Personal Skills
        personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []
        u_i['skills'] = [StatusObject.statusparser(status) for status in personal_skills]

        units.append(Unit(u_i))
    return units

# === MODEL CLASS ===
class Unit(object):
    def __init__(self, info):
        self.id = info['id']
        self.name = info['name']

        self.level = int(info['level'])
        self.gender = int(info['gender'])
        self.faction = info['faction']
        self.klass = info['klass']
        self.tags = info['tags']
        self.desc = info['desc']

        self.stats = info['stats']
        self.growths = info['growths']

        self.wexp = info['wexp']

        self.items = info['items']

        self.skills = info['skills']

        self.team = 'player'
        self.currenthp = self.stats['HP']
        self.icon = UnitSprite.UnitSprite(self)

        try:
            # Ex: HectorPortrait
            self.portrait = Engine.subsurface(GC.UNITDICT[self.name + 'Portrait'], (0, 0, 96, 80)).convert_alpha()
            self.chibi = Engine.subsurface(GC.UNITDICT[self.name + 'Portrait'], (96, 16, 32, 32)).convert_alpha()
        except KeyError:
            self.portrait = GC.UNITDICT['Generic_Portrait_' + self.klass].convert_alpha()
            self.chibi = GC.UNITDICT[self.faction + 'Emblem'].convert_alpha()
        self.chibi = Engine.transform_scale(self.chibi, (64, 64))

# === VIEW AND CONTROLLER METHODS ============================================
class ImageWidget(QtGui.QWidget):
    def __init__(self, surface, parent=None, x=0):
        super(ImageWidget, self).__init__(parent)
        w = surface.get_width()
        h = surface.get_height()
        self.data = surface.get_buffer().raw
        self.x = x
        # self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_RGB32)
        self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_ARGB32)
        self.resize(w, h)

def clicked_unit(index):
    print(index)
    row = index.row()
    print(row)
    item = index.data()
    print(item)
    name = item.toString()
    print(name)

def create_icon(image, window):
    icon = ImageWidget(image, window)
    icon = QtGui.QPixmap(icon.image)
    icon = QtGui.QIcon(icon)
    return icon

def create_pixmap(image, window):
    icon = ImageWidget(image, window)
    icon = QtGui.QPixmap(icon.image)
    return icon

class UnitView(QtGui.QWidget):
    teams = ['player', 'other', 'enemy', 'enemy2']

    def __init__(self, window):
        super(UnitView, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.window = window
        # window.setLayout(self.grid)
        self.current_unit = None

        # === Character Data ===
        char_grid = QtGui.QGridLayout()

        self.chibi = QtGui.QLabel()
        char_grid.addWidget(self.chibi, 0, 0, 2, 2, QtCore.Qt.AlignCenter)
        # Name
        name_label = QtGui.QLabel('Name:')
        char_grid.addWidget(name_label, 0, 2)
        self.name = QtGui.QLineEdit()
        self.name.setMaxLength(12)
        char_grid.addWidget(self.name, 0, 3)
        # Team
        team_label = QtGui.QLabel('Team:')
        char_grid.addWidget(team_label, 1, 2)
        self.team = QtGui.QComboBox()
        self.team.addItems(self.teams)
        char_grid.addWidget(self.team, 1, 3)
        # Level
        level_label = QtGui.QLabel('Level:')
        char_grid.addWidget(level_label, 2, 0)
        self.level = QtGui.QSpinBox()
        self.level.setMinimum(1)
        char_grid.addWidget(self.level, 2, 1)
        # Class
        klass_label = QtGui.QLabel('Class:')
        char_grid.addWidget(klass_label, 2, 2)
        self.klass = QtGui.QComboBox()
        self.klass.addItems(klasses)
        char_grid.addWidget(self.klass, 2, 3)

        # Gender
        gender_label = QtGui.QLabel('Gender:')
        char_grid.addWidget(gender_label, 3, 0)
        self.gender = QtGui.QSpinBox()
        self.gender.setMinimum(0)
        self.gender.setMaximum(9)
        char_grid.addWidget(self.gender, 3, 1)
        # Faction
        faction_label = QtGui.QLabel('Faction:')
        char_grid.addWidget(faction_label, 3, 2)
        self.faction = QtGui.QLineEdit()
        char_grid.addWidget(self.faction, 3, 3)
        # Lordbox
        self.lord = QtGui.QCheckBox('Lord?')
        char_grid.addWidget(self.lord, 4, 0, 1, 2)
        # Boss box
        self.boss = QtGui.QCheckBox('Boss?')
        char_grid.addWidget(self.boss, 4, 2, 1, 2)
        # Description
        desc_label = QtGui.QLabel('Desc:')
        char_grid.addWidget(desc_label, 5, 0)
        self.desc = QtGui.QTextEdit()
        char_grid.addWidget(self.desc, 5, 1, 2, 3)

        # === Stats ===
        stat_grid = QtGui.QGridLayout()
        # Names
        stats_label = QtGui.QLabel('Stats:')
        stat_grid.addWidget(stats_label, 0, 0)
        for index, stat_name in enumerate(cf.CONSTANTS['stat_names']):
            stat_label = QtGui.QLabel(stat_name)
            stat_grid.addWidget(stat_label, 0, index + 1)

        bases_label = QtGui.QLabel('Bases:')
        stat_grid.addWidget(bases_label, 1, 0)
        growths_label = QtGui.QLabel('Growths:')
        stat_grid.addWidget(growths_label, 2, 0)

        self.stat_bases = [QtGui.QSpinBox() for stat in cf.CONSTANTS['stat_names']]
        self.stat_growths = [QtGui.QSpinBox() for stat in cf.CONSTANTS['stat_names']]
        for index, s in enumerate(self.stat_bases):
            s.setMinimum(0)
            s.setMaximum(cf.CONSTANTS['max_stat'])
            stat_grid.addWidget(s, 1, index + 1)
        for index, s in enumerate(self.stat_growths):
            s.setSingleStep(5)
            s.setMaximum(500)
            stat_grid.addWidget(s, 2, index + 1)

        # === Weapon Exp ===
        wexp_grid = QtGui.QGridLayout()
        wexp_label = QtGui.QLabel('Wexp:')
        wexp_grid.addWidget(wexp_label, 0, 0, 2, 1)
        weapon_types = CustomObjects.WEAPON_TRIANGLE.types
        for index, wexp_name in enumerate(weapon_types):
            name_label = QtGui.QLabel(wexp_name)
            wexp_grid.addWidget(name_label, 0, index + 1)
        self.wexp = [QtGui.QSpinBox() for wexp in weapon_types]
        for index, s in enumerate(self.wexp):
            s.setMinimum(0)
            s.setMaximum(CustomObjects.WEAPON_EXP.sorted_list[-1][1])
            wexp_grid.addWidget(s, 1, index + 1)

        # === Items ===

        # === Personal Skills ===

        # === Unit Face Display ===

        # === Final gridding ===
        self.grid.addLayout(char_grid, 0, 0)
        self.grid.addLayout(stat_grid, 1, 0)
        self.grid.addLayout(wexp_grid, 2, 0)

    def disp_unit(self, unit):
        self.current_unit = unit

        pixmap = create_pixmap(unit.chibi, self.window)
        self.chibi.setPixmap(pixmap)
        self.name.setText(unit.name)
        self.team.setCurrentIndex(self.teams.index(unit.team))
        self.gender.setValue(unit.gender)
        self.level.setValue(unit.level)
        self.faction.setText(unit.faction)
        self.lord.setChecked('Lord' in unit.tags)
        self.boss.setChecked('Boss' in unit.tags)
        self.desc.setText(unit.desc)
        self.klass.setCurrentIndex(klasses.index(unit.klass))

        for index, (stat_name, stat) in enumerate(unit.stats.iteritems()):
            self.stat_bases[index].setValue(stat.base_stat)
            self.stat_growths[index].setValue(unit.growths[index])

        for index, wexp in enumerate(unit.wexp):
            self.wexp[index].setValue(wexp)

    def save_current_unit(self):
        if self.current_unit:
            self.current_unit.name = str(self.name.text())
            self.current_unit.team = str(self.team.currentText())
            self.current_unit.gender = int(self.gender.value())
            self.current_unit.level = int(self.level.value())
            self.current_unit.faction = str(self.faction.text())
            if self.lord.isChecked():
                self.current_unit.tags.add('Lord')
            if self.boss.isChecked():
                self.current_unit.tags.add('Boss')
            self.current_unit.desc = str(self.desc.toPlainText())
            self.current_unit.klass = str(self.klass.currentText())

            for index, s in enumerate(self.stat_bases):
                self.current_unit.stats.base_stat = int(s.value())
            self.current_unit.growths = [int(s.value()) for s in self.stat_growths]

            self.current_unit.wexp = [int(s.value()) for s in self.wexp]

def on_item_changed(curr, prev):
    idx = curr.row()
    unit = units[idx]
    unit_view.save_current_unit()
    unit_view.disp_unit(unit)

if __name__ == '__main__':
    class_dict = SaveLoad.create_class_dict()
    klasses = sorted(class_dict.keys())
    units = build_units(class_dict)

    app = QtGui.QApplication(sys.argv)
    window = QtGui.QMainWindow()
    main_widget = QtGui.QWidget()  # Needed for layout setting
    window.setCentralWidget(main_widget)
    # Create layout
    grid = QtGui.QGridLayout()
    main_widget.setLayout(grid)

    window.setWindowTitle('Unit Editor')
    # window.setMinimumSize(640, 640)

    # Create list
    unit_list = QtGui.QListView(main_widget)
    unit_list.setMinimumSize(128, 320)
    unit_list.clicked.connect(clicked_unit)
    # unit_list.selectionModel().currentChanged.connect(on_item_changed)
    unit_list.uniformItemSizes = True
    unit_list.setIconSize(QtCore.QSize(64, 48))
    model = QtGui.QStandardItemModel(unit_list)

    for index, unit in enumerate(units):
        icon = create_icon(unit.icon.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha(), main_widget)
        # Image_Modification.print_image(icon)
        item = QtGui.QStandardItem(icon, unit.name)
        model.appendRow(item)

    # apply the model to the list view
    unit_list.setModel(model)
    unit_list.selectionModel().currentChanged.connect(on_item_changed)

    grid.addWidget(unit_list, 0, 0)
    unit_view = UnitView(window)
    grid.addLayout(unit_view.grid, 0, 1)

    # window.setGeometry(100, 100, 640, 480)
    Engine.remove_display()
    window.show()
    app.exec_()
