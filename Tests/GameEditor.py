from PyQt5 import QtGui, QtCore
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
from Code.Dialogue import UnitPortrait

# DATA XML
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

try:
    from xml.dom import minidom
    PRETTY = True
except ImportError:
    PRETTY = False

def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

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

def create_icon(image):
    icon = ImageWidget(image)
    icon = QtGui.QPixmap(icon.image)
    icon = QtGui.QIcon(icon)
    return icon

def create_pixmap(image):
    icon = ImageWidget(image)
    icon = QtGui.QPixmap(icon.image)
    return icon

def create_chibi(name):
    return Engine.subsurface(GC.UNITDICT[name + 'Portrait'], (96, 16, 32, 32)).convert_alpha()

def stretch(grid):
    box_h = QtGui.QHBoxLayout()
    box_h.addStretch(1)
    box_h.addLayout(grid)
    box_h.addStretch(1)
    box_v = QtGui.QVBoxLayout()
    box_v.addStretch(1)
    box_v.addLayout(box_h)
    box_v.addStretch(1)
    return box_v

# === DATA IMPORTING ===
def build_units(class_dict, portrait_data):
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

        u_i['items'] = [ItemMethods.itemparser(item) for item in unit.find('inventory').text if item]
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

        units.append(Unit(u_i, portrait_data))
    return units

def find(data, name):
    return next((x for x in data if x.name == name), None)

# === MODEL CLASS ===
class Unit(object):
    def __init__(self, info, portrait_data):
        if info:
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
            try:
                self.image = create_chibi(self.name)
            except KeyError:
                self.image = GC.UNITDICT[self.faction + 'Emblem'].convert_alpha()
        else:
            self.id = 0
            self.name = ''
            self.level = 1
            self.gender = 0
            self.faction = ''
            self.klass = 'Citizen'
            self.tags = set()
            self.desc = ''
            current_class = find(class_data, self.klass)
            self.stats = SaveLoad.build_stat_dict(current_class.bases)
            self.growths = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.items = []
            self.skills = []
            self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
            self.team = 'player'
            self.image = None

class Klass(object):
    def __init__(self, info):
        if info:
            self.name = info['id']
            self.wexp = info['wexp_gain']
            self.promotes_from = info['promotes_from']
            self.promotes_to = info['turns_into']
            self.movement_group = info['movement_group']
            self.tags = info['tags']
            self.skills = [s[1] for s in info['skills']]
            self.skill_levels = [s[0] for s in info['skills']]
            self.growths = info['growths']
            self.bases = info['bases']
            self.promotion = info['promotion']
            self.max = info['max']
            self.desc = info['desc']
        else:
            self.name = ''
            self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
            self.promotes_from = ''
            self.promotes_to = []
            self.movement_group = 0
            self.tags = set()
            self.skills = []
            self.skill_levels = []
            self.bases = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.growths = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.promotion = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.max = [40, 15, 15, 15, 15, 20, 15, 15, 20]
            self.desc = ''

        self.unit = GenericUnit(self.name)
        self.images = (self.unit.image1, self.unit.image2, self.unit.image3)
        self.image = self.images[0]

# === For use by class object ===
class GenericUnit(object):
    def __init__(self, klass, gender=0):
        self.gender = gender
        self.team = 'player'
        self.klass = klass
        self.stats = {}
        self.stats['HP'] = 1
        self.currenthp = 1
        self.sprite = UnitSprite.UnitSprite(self)
        GC.PASSIVESPRITECOUNTER.count = 0
        self.image1 = self.sprite.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha()
        GC.PASSIVESPRITECOUNTER.increment()
        self.image2 = self.sprite.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha()
        GC.PASSIVESPRITECOUNTER.increment()        
        self.image3 = self.sprite.create_image('passive').subsurface(20, 18, 24, 24).convert_alpha()

    def get_images(self):
        self.images = (self.image1, self.image2, self.image3)

# === Overall View Methods ===
class UnitView(QtGui.QWidget):
    def __init__(self, window):
        super(UnitView, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.window = window
        self.current = None

        # === Unit Face Display ===
        face_grid = QtGui.QGridLayout()

        self.portrait = QtGui.QLabel()
        face_grid.addWidget(self.portrait, 0, 0, 4, 4, QtCore.Qt.AlignCenter)

        # === Character Data ===
        char_grid = QtGui.QGridLayout()

        # Name
        name_label = QtGui.QLabel('Name:')
        char_grid.addWidget(name_label, 0, 0)
        self.name = QtGui.QLineEdit()
        self.name.setMaxLength(12)
        self.name.setStatusTip("Change name")
        char_grid.addWidget(self.name, 0, 1, 1, 2)
        self.set_name_button = QtGui.QPushButton('Change Name')
        self.set_name_button.clicked.connect(self.change_name)
        char_grid.addWidget(self.set_name_button, 0, 3)
        # Level
        level_label = QtGui.QLabel('Level:')
        char_grid.addWidget(level_label, 1, 0)
        self.level = QtGui.QSpinBox()
        self.level.setMinimum(1)
        char_grid.addWidget(self.level, 1, 1)
        # Gender
        gender_label = QtGui.QLabel('Gender:')
        char_grid.addWidget(gender_label, 1, 2)
        self.gender = QtGui.QSpinBox()
        self.gender.setMinimum(0)
        self.gender.setMaximum(9)
        char_grid.addWidget(self.gender, 1, 3)
        # Class
        klass_label = QtGui.QLabel('Class:')
        char_grid.addWidget(klass_label, 2, 0)
        self.klass = QtGui.QComboBox()
        self.klass.uniformItemSizes = True
        self.klass.setIconSize(QtCore.QSize(48, 32))
        for klass in class_data:
            self.klass.addItem(create_icon(klass.images[0]), klass.name)
        self.klass.currentIndexChanged.connect(self.class_change)
        char_grid.addWidget(self.klass, 2, 1, 1, 3)

        # Faction
        faction_label = QtGui.QLabel('Faction:')
        char_grid.addWidget(faction_label, 3, 0)
        self.faction = QtGui.QLineEdit()
        char_grid.addWidget(self.faction, 3, 1, 1, 3)
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
        self.desc.setFixedHeight(48)
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
            s.setMinimum(-500)
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
            icon_label = QtGui.QLabel()
            wexp_icon = CustomObjects.WeaponIcon(idx=index)
            icon_label.setPixmap(create_pixmap(wexp_icon.image.convert_alpha()))
            wexp_grid.addWidget(name_label, 0, (index + 1)*2 + 1)
            wexp_grid.addWidget(icon_label, 0, (index + 1)*2)
        self.wexp = [QtGui.QSpinBox() for wexp in weapon_types]
        for index, s in enumerate(self.wexp):
            s.setMinimum(0)
            s.setMaximum(CustomObjects.WEAPON_EXP.sorted_list[-1][1])
            wexp_grid.addWidget(s, 1, (index + 1)*2, 1, 2)
        # Horizontal line
        line = QtGui.QFrame()
        line.setFrameStyle(QtGui.QFrame.HLine)
        line.setLineWidth(0)
        wexp_grid.addWidget(line, 2, 0, 1, len(self.wexp)*2 + 2)

        # === Items ===
        item_grid = QtGui.QGridLayout()
        item_label = QtGui.QLabel('Item:')
        drop_label = QtGui.QLabel('Drop?')
        event_label = QtGui.QLabel('Event?')
        self.add_item_button = QtGui.QPushButton('Add Item')
        self.add_item_button.clicked.connect(self.add_item)
        self.remove_item_button = QtGui.QPushButton('Remove Item')
        self.remove_item_button.clicked.connect(self.remove_item)
        self.remove_item_button.setEnabled(False)

        self.items = []
        for num in xrange(cf.CONSTANTS['max_items']):
            self.items.append((self.create_item_combo_box(), QtGui.QCheckBox(), QtGui.QCheckBox()))
        for index, item in enumerate(self.items):
            item_box, drop, event = item
            item_grid.addWidget(item_box, index + 1, 0, 1, 2, QtCore.Qt.AlignTop)
            item_grid.addWidget(drop, index + 1, 2, QtCore.Qt.AlignTop)
            item_grid.addWidget(event, index + 1, 3, QtCore.Qt.AlignTop)

        item_grid.addWidget(item_label, 0, 0, 1, 2, QtCore.Qt.AlignTop)
        item_grid.addWidget(drop_label, 0, 2, QtCore.Qt.AlignTop)
        item_grid.addWidget(event_label, 0, 3, QtCore.Qt.AlignTop)
        item_grid.addWidget(self.add_item_button, cf.CONSTANTS['max_items'] + 2, 0, 1, 2, QtCore.Qt.AlignBottom)
        item_grid.addWidget(self.remove_item_button, cf.CONSTANTS['max_items'] + 2, 2, 1, 2, QtCore.Qt.AlignBottom)
        self.clear_items()

        # === Personal Skills ===
        skill_grid = QtGui.QGridLayout()
        skill_label = QtGui.QLabel('Personal Skill:')
        self.add_skill_button = QtGui.QPushButton('Add Skill')
        self.add_skill_button.clicked.connect(self.add_skill)
        self.remove_skill_button = QtGui.QPushButton('Remove Skill')
        self.remove_skill_button.clicked.connect(self.remove_skill)
        self.remove_skill_button.setEnabled(False)

        self.skills = []
        for num in xrange(cf.CONSTANTS['num_skills']):
            self.skills.append(self.create_skill_combo_box())
        for index, skill_box in enumerate(self.skills):
            skill_grid.addWidget(skill_box, index + 1, 0, 1, 2, )

        skill_grid.addWidget(skill_label, 0, 0, 1, 2, QtCore.Qt.AlignTop)
        skill_grid.addWidget(self.add_skill_button, cf.CONSTANTS['num_skills'] + 2, 0)
        skill_grid.addWidget(self.remove_skill_button, cf.CONSTANTS['num_skills'] + 2, 1)
        self.clear_skills()

        # === Final gridding ===
        self.grid.addLayout(face_grid, 0, 0)
        self.grid.addLayout(stretch(char_grid), 0, 1)
        self.grid.addLayout(stretch(stat_grid), 1, 0, 1, 2)
        self.grid.addLayout(stretch(wexp_grid), 2, 0, 1, 2)
        self.grid.addLayout(stretch(item_grid), 3, 0)
        self.grid.addLayout(stretch(skill_grid), 3, 1)

    def change_name(self):
        if self.current:
            new_name = str(self.name.text())
            self.current.name = new_name
            try:
                self.current.image = create_chibi(new_name)
            except KeyError:
                # Show pop-up
                message_box = QtGui.QMessageBox()
                message_box.setText("No png file named %s found in Data/Characters/" % (new_name + 'Portrait.png'))
                message_box.exec_()
                self.current.image = create_chibi('Generic')
            portrait = find(portrait_data, new_name)
            if portrait:
                self.current.portrait = portrait
            self.window.reset()
            self.display(self.current)

    # Item functions
    def clear_items(self):
        for index, (item_box, drop, event) in enumerate(self.items):
            item_box.hide()
            drop.hide()
            event.hide()
        self.num_items = 0

    def add_item(self):
        self.num_items += 1
        self.remove_item_button.setEnabled(True)
        item_box, drop, event = self.items[self.num_items - 1]
        item_box.show()
        drop.show()
        event.show()
        if self.num_items >= cf.CONSTANTS['max_items']:
            self.add_item_button.setEnabled(False)

    def remove_item(self):
        self.num_items -= 1
        self.add_item_button.setEnabled(True)
        item_box, drop, event = self.items[self.num_items]
        item_box.hide()
        drop.hide()
        event.hide()
        if self.num_items <= 0:
            self.remove_item_button.setEnabled(False)

    def create_item_combo_box(self):
        item_box = QtGui.QComboBox()
        item_box.uniformItemSizes = True
        item_box.setIconSize(QtCore.QSize(16, 16))
        for item in item_data:
            if item.icon:
                item_box.addItem(item.icon, item.name)
            else:
                item_box.addItem(item.name)
        return item_box

    # Skill functions
    def clear_skills(self):
        for index, skill_box in enumerate(self.skills):
            skill_box.hide()
        self.num_skills = 0

    def add_skill(self):
        self.num_skills += 1
        self.remove_skill_button.setEnabled(True)
        skill_box = self.skills[self.num_skills - 1]
        skill_box.show()
        if self.num_skills >= cf.CONSTANTS['num_skills']:
            self.add_skill_button.setEnabled(False)

    def remove_skill(self):
        self.num_skills -= 1
        self.add_skill_button.setEnabled(True)
        skill_box = self.skills[self.num_skills]
        skill_box.hide()
        if self.num_skills <= 0:
            self.remove_skill_button.setEnabled(False)

    def create_skill_combo_box(self):
        skill_box = QtGui.QComboBox()
        skill_box.uniformItemSizes = True
        skill_box.setIconSize(QtCore.QSize(16, 16))
        for skill in skill_data:
            if skill.icon:
                skill_box.addItem(skill.icon, skill.name)
            else:
                skill_box.addItem(skill.name)
        return skill_box

    def class_change(self, new):
        # Set which wexps are valid
        valid_weapons = class_data[new].wexp
        for index in xrange(len(self.wexp)):
            enable = valid_weapons[index]
            self.wexp[index].setEnabled(enable)
            if enable:
                self.wexp[index].setMinimum(1)
            else:
                self.wexp[index].setMinimum(0)
                self.wexp[index].setValue(0)

    # Displaying functions
    def display(self, unit):
        self.current = unit

        # Char data
        self.name.setText(unit.name)
        # self.team.setCurrentIndex(self.teams.index(unit.team))
        self.gender.setValue(unit.gender)
        self.level.setValue(unit.level)
        self.faction.setText(unit.faction)
        self.lord.setChecked('Lord' in unit.tags)
        self.boss.setChecked('Boss' in unit.tags)
        self.desc.setText(unit.desc)
        for idx, klass in enumerate(class_data):
            if klass.name == unit.klass:
                class_index = idx
                break
        self.klass.setCurrentIndex(class_index)
        self.class_change(class_index)

        for index, (stat_name, stat) in enumerate(unit.stats.iteritems()):
            self.stat_bases[index].setValue(stat.base_stat)
            self.stat_growths[index].setValue(unit.growths[index])

        for index, wexp in enumerate(unit.wexp):
            self.wexp[index].setValue(wexp)

        self.clear_items()
        for index, item in enumerate(unit.items):
            self.add_item()
            item_box, drop_box, event_box = self.items[index]
            drop_box.setChecked(item.droppable)
            event_box.setChecked(item.event_combat)
            item_box.setCurrentIndex([i.name for i in item_data].index(item.name))

        self.clear_skills()
        for index, skill in enumerate(unit.skills):
            self.add_skill()
            skill_box = self.skills[index]
            skill_box.setCurrentIndex([s.id for s in skill_data].index(skill.id))

        portrait = find(portrait_data, unit.name)
        if portrait:
            portrait.create_image()
            pixmap = create_pixmap(Engine.transform_scale(portrait.image.convert_alpha(), (96*2, 80*2)))
            self.portrait.setPixmap(pixmap)
        else:
            self.portrait.clear()

    def save_current(self):
        if self.current:
            # self.current.name = str(self.name.text())
            self.current.gender = int(self.gender.value())
            self.current.level = int(self.level.value())
            self.current.faction = str(self.faction.text())
            self.current.tags = set()
            if self.lord.isChecked():
                self.current.tags.add('Lord')
            if self.boss.isChecked():
                self.current.tags.add('Boss')
            self.current.desc = str(self.desc.toPlainText())
            self.current.klass = str(self.klass.currentText())

            for index, s in enumerate(self.stat_bases):
                self.current.stats.base_stat = int(s.value())
            self.current.growths = [int(s.value()) for s in self.stat_growths]

            self.current.wexp = [int(s.value()) for s in self.wexp]

            self.current.items = []
            for index, (item_box, drop_box, event_box) in enumerate(self.items[:self.num_items]):
                item = item_data[item_box.currentIndex()]
                item.droppable = drop_box.isChecked()
                item.event_combat = event_box.isChecked()
                self.current.items.append(item)

            self.current.skills = []
            for index, skill_box in enumerate(self.skills[:self.num_skills]):
                self.current.skills.append(skill_data[skill_box.currentIndex()])

    def tick(self, current_time):
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for index, klass in enumerate(class_data):
                icon = create_icon(klass.images[GC.PASSIVESPRITECOUNTER.count])
                self.klass.setItemIcon(index, icon)

class ClassView(QtGui.QWidget):
    def __init__(self, window):
        super(ClassView, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.window = window
        self.current = None

        # === Character Data ===
        char_grid = QtGui.QGridLayout()

        # Name
        name_label = QtGui.QLabel('Name:')
        char_grid.addWidget(name_label, 0, 0)
        self.name = QtGui.QLineEdit()
        self.name.setMaxLength(12)
        self.name.setStatusTip("Change name")
        char_grid.addWidget(self.name, 0, 1, 1, 2)
        self.set_name_button = QtGui.QPushButton('Change Name')
        self.set_name_button.clicked.connect(self.change_name)
        char_grid.addWidget(self.set_name_button, 0, 3)
        # Description
        desc_label = QtGui.QLabel('Desc:')
        char_grid.addWidget(desc_label, 1, 0)
        self.desc = QtGui.QTextEdit()
        self.desc.setFixedHeight(48)
        char_grid.addWidget(self.desc, 1, 1, 1, 3)
        # Movement Group
        move_label = QtGui.QLabel('Movement Group:')
        char_grid.addWidget(move_label, 2, 0)
        self.movement_group = QtGui.QSpinBox()
        self.movement_group.setMinimum(0)
        self.movement_group.setMaximum(10)  # Placeholder
        char_grid.addWidget(self.movement_group, 2, 1)
        # Mounted box
        self.mounted = QtGui.QCheckBox('Mounted?')
        char_grid.addWidget(self.mounted, 2, 2)
        # Flying box
        self.flying = QtGui.QCheckBox('Flying?')
        char_grid.addWidget(self.flying, 2, 3)
        # Class
        klass_label = QtGui.QLabel('Promotes From:')
        char_grid.addWidget(klass_label, 3, 0)
        self.promotes_from = QtGui.QComboBox()
        self.promotes_from.uniformItemSizes = True
        self.promotes_from.setIconSize(QtCore.QSize(48, 32))
        self.promotes_from.addItem('None')
        for klass in class_data:
            self.promotes_from.addItem(create_icon(klass.images[0]), klass.name)
        char_grid.addWidget(self.promotes_from, 3, 1, 1, 3)

        # === Weapon Exp ===
        wexp_grid = QtGui.QGridLayout()
        wexp_label = QtGui.QLabel('Wexp:')
        wexp_grid.addWidget(wexp_label, 0, 0, 2, 1)
        weapon_types = CustomObjects.WEAPON_TRIANGLE.types
        for index, wexp_name in enumerate(weapon_types):
            name_label = QtGui.QLabel(wexp_name)
            icon_label = QtGui.QLabel()
            wexp_icon = CustomObjects.WeaponIcon(idx=index)
            icon_label.setPixmap(create_pixmap(wexp_icon.image.convert_alpha()))
            wexp_grid.addWidget(name_label, 0, (index + 1)*2 + 1)
            wexp_grid.addWidget(icon_label, 0, (index + 1)*2)
        self.wexp = [QtGui.QSpinBox() for wexp in weapon_types]
        for index, s in enumerate(self.wexp):
            s.setMinimum(0)
            s.setMaximum(CustomObjects.WEAPON_EXP.sorted_list[-1][1])
            wexp_grid.addWidget(s, 1, (index + 1)*2, 1, 2)
        # Horizontal line
        line = QtGui.QFrame()
        line.setFrameStyle(QtGui.QFrame.HLine)
        line.setLineWidth(0)
        wexp_grid.addWidget(line, 2, 0, 1, len(self.wexp)*2 + 2)

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
        promotion_label = QtGui.QLabel('Promotion:')
        stat_grid.addWidget(promotion_label, 3, 0)
        max_label = QtGui.QLabel('Max:')
        stat_grid.addWidget(max_label, 4, 0)

        self.stat_bases = [QtGui.QSpinBox() for stat in cf.CONSTANTS['stat_names']]
        self.stat_growths = [QtGui.QSpinBox() for stat in cf.CONSTANTS['stat_names']]
        self.stat_promotion = [QtGui.QSpinBox() for stat in cf.CONSTANTS['stat_names']]
        self.stat_max = [QtGui.QSpinBox() for stat in cf.CONSTANTS['stat_names']]

        for index, s in enumerate(self.stat_bases):
            s.setMinimum(0)
            s.setMaximum(int(self.stat_max[index].value()))
            stat_grid.addWidget(s, 1, index + 1)
        for index, s in enumerate(self.stat_growths):
            s.setMinimum(-500)
            s.setSingleStep(5)
            s.setMaximum(500)
            stat_grid.addWidget(s, 2, index + 1)
        for index, s in enumerate(self.stat_promotion):
            s.setMinimum(-10)
            s.setMaximum(int(self.stat_max[index].value()))
            stat_grid.addWidget(s, 3, index + 1)
        for index, s in enumerate(self.stat_max):
            s.setMinimum(0)
            s.setMaximum(60)
            s.valueChanged.connect(self.max_change)
            stat_grid.addWidget(s, 4, index + 1)

        # === Promotions ===
        option_grid = QtGui.QGridLayout()
        option_label = QtGui.QLabel('Promotes To:')
        self.add_option_button = QtGui.QPushButton('Add Option')
        self.add_option_button.clicked.connect(self.add_option)
        self.remove_option_button = QtGui.QPushButton('Remove Option')
        self.remove_option_button.clicked.connect(self.remove_option)
        self.remove_option_button.setEnabled(False)

        self.options = []
        for num in xrange(cf.CONSTANTS['max_promotions']):
            self.options.append(self.create_option_combo_box())
        for index, option in enumerate(self.options):
            option_grid.addWidget(option, index + 1, 0, 1, 2, QtCore.Qt.AlignTop)

        option_grid.addWidget(option_label, 0, 0, 1, 2, QtCore.Qt.AlignTop)
        option_grid.addWidget(self.add_option_button, cf.CONSTANTS['max_promotions'] + 2, 0, 1, 1, QtCore.Qt.AlignBottom)
        option_grid.addWidget(self.remove_option_button, cf.CONSTANTS['max_promotions'] + 2, 1, 1, 1, QtCore.Qt.AlignBottom)
        self.clear_options()

        # === Personal Skills ===
        skill_grid = QtGui.QGridLayout()
        skill_label = QtGui.QLabel('Class Skills:')
        level_label = QtGui.QLabel('Level:')
        skill_label2 = QtGui.QLabel('Skill:')
        self.add_skill_button = QtGui.QPushButton('Add Skill')
        self.add_skill_button.clicked.connect(self.add_skill)
        self.remove_skill_button = QtGui.QPushButton('Remove Skill')
        self.remove_skill_button.clicked.connect(self.remove_skill)
        self.remove_skill_button.setEnabled(False)

        self.skills, self.skill_levels = [], []
        for num in xrange(cf.CONSTANTS['num_skills']):
            self.skills.append(self.create_skill_combo_box())
            skill_level = QtGui.QSpinBox()
            skill_level.setMinimum(1)
            skill_level.setMaximum(40)
            self.skill_levels.append(skill_level)
        for index, skill_box in enumerate(self.skills):
            skill_grid.addWidget(skill_box, index + 2, 1, 1, 3)
            skill_grid.addWidget(self.skill_levels[index], index + 2, 0)

        skill_grid.addWidget(skill_label, 0, 0, 1, 4, QtCore.Qt.AlignTop)
        skill_grid.addWidget(level_label, 1, 0)
        skill_grid.addWidget(skill_label2, 1, 1, 1, 3)
        skill_grid.addWidget(self.add_skill_button, cf.CONSTANTS['num_skills'] + 3, 0, 1, 2)
        skill_grid.addWidget(self.remove_skill_button, cf.CONSTANTS['num_skills'] + 3, 2, 1, 2)
        self.clear_skills()

        # === Final gridding ===
        self.grid.addLayout(stretch(char_grid), 0, 0)
        self.grid.addLayout(stretch(wexp_grid), 1, 0, 1, 3)
        self.grid.addLayout(stretch(stat_grid), 2, 0, 1, 3)
        self.grid.addLayout(stretch(option_grid), 0, 1)
        self.grid.addLayout(stretch(skill_grid), 0, 2)

    def change_name(self):
        if self.current:
            new_name = str(self.name.text())
            self.current.name = new_name
            self.current.images = GenericUnit(new_name).get_images()
            self.window.reset()
            self.display(self.current)

    def max_change(self):
        for index, s in enumerate(self.stat_bases):
            s.setMaximum(int(self.stat_max[index].value()))
        for index, s in enumerate(self.stat_promotion):
            s.setMaximum(int(self.stat_max[index].value()))
            
    # Promotion Option functions
    def clear_options(self):
        for index, option in enumerate(self.options):
            option.hide()
        self.num_options = 0

    def add_option(self):
        self.num_options += 1
        self.remove_option_button.setEnabled(True)
        option = self.options[self.num_options - 1]
        option.show()
        if self.num_options >= cf.CONSTANTS['max_promotions']:
            self.add_option_button.setEnabled(False)

    def remove_option(self):
        self.num_options -= 1
        self.add_option_button.setEnabled(True)
        option = self.option[self.num_option]
        option.hide()
        if self.num_option <= 0:
            self.remove_option_button.setEnabled(False)

    def create_option_combo_box(self):
        option = QtGui.QComboBox()
        option.uniformItemSizes = True
        option.setIconSize(QtCore.QSize(48, 32))
        for klass in class_data:
            option.addItem(create_icon(klass.images[0]), klass.name)
        return option

    # Skill functions
    def clear_skills(self):
        for index, skill_box in enumerate(self.skills):
            skill_box.hide()
        for index, level_box in enumerate(self.skill_levels):
            level_box.hide()
        self.num_skills = 0

    def add_skill(self):
        self.num_skills += 1
        self.remove_skill_button.setEnabled(True)
        self.skills[self.num_skills - 1].show()
        self.skill_levels[self.num_skills - 1].show()
        if self.num_skills >= cf.CONSTANTS['num_skills']:
            self.add_skill_button.setEnabled(False)

    def remove_skill(self):
        self.num_skills -= 1
        self.add_skill_button.setEnabled(True)
        self.skills[self.num_skills].hide()
        self.skill_levels[self.num_skills].hide()
        if self.num_skills <= 0:
            self.remove_skill_button.setEnabled(False)

    def create_skill_combo_box(self):
        skill_box = QtGui.QComboBox()
        skill_box.uniformItemSizes = True
        skill_box.setIconSize(QtCore.QSize(16, 16))
        for skill in skill_data:
            if skill.image:
                skill_box.addItem(create_icon(skill.image), skill.name)
            else:
                skill_box.addItem(skill.name)
        return skill_box

    # Displaying functions
    def display(self, klass):
        self.current = klass

        # Char data
        self.name.setText(klass.name)
        self.desc.setText(klass.desc)
        self.movement_group.setValue(klass.movement_group)
        self.mounted.setChecked('Mounted' in klass.tags)
        self.flying.setChecked('Flying' in klass.tags)
        class_index = -1
        for idx, k in enumerate(class_data):
            if k.name == klass.promotes_from:
                class_index = idx
                break
        self.promotes_from.setCurrentIndex(class_index + 1)

        for index in xrange(len(cf.CONSTANTS['stat_names'])):
            self.stat_max[index].setValue(klass.max[index])
            self.stat_bases[index].setValue(klass.bases[index])
            self.stat_growths[index].setValue(klass.growths[index])
            self.stat_promotion[index].setValue(klass.promotion[index])

        for index, wexp in enumerate(klass.wexp):
            self.wexp[index].setValue(wexp)

        self.clear_options()
        class_names = [c.name for c in class_data]
        for index, name in enumerate(klass.promotes_to):
            self.add_option()
            self.options[index].setCurrentIndex(class_names.index(name))

        self.clear_skills()
        skill_names = [s.id for s in skill_data]
        for index, skill in enumerate(klass.skills):
            self.add_skill()
            self.skills[index].setCurrentIndex(skill_names.index(skill))
            self.skill_levels[index].setValue(klass.skill_levels[index])

    def save_current(self):
        if self.current:
            # self.current.name = str(self.name.text()
            self.current.movement_group = int(self.movement_group.value())
            self.current.tags = set()
            if self.mounted.isChecked():
                self.current.tags.add('Mounted')
            if self.flying.isChecked():
                self.current.tags.add('Flying')
            self.current.desc = str(self.desc.toPlainText())
            self.current.promotes_from = str(self.promotes_from.currentText())

            self.current.bases = [int(s.value()) for s in self.stat_bases]
            self.current.growths = [int(s.value()) for s in self.stat_growths]
            self.current.promotion = [int(s.value()) for s in self.stat_promotion]
            self.current.max = [int(s.value()) for s in self.stat_max]

            self.current.wexp = [int(s.value()) for s in self.wexp]

            self.current.promotes_to = []
            for index, option in enumerate(self.options[:self.num_options]):
                klass = class_data[option.currentIndex()]
                self.current.promotes_to.append(klass.name)

            self.current.skills = []
            self.current.skill_levels = []
            for index, skill_box in enumerate(self.skills[:self.num_skills]):
                self.current.skills.append(skill_data[skill_box.currentIndex()].id)
                self.current.skill_levels.append(int(self.skill_levels[index].value()))

    def tick(self, current_time):
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for index, klass in enumerate(class_data):
                icon = create_icon(klass.images[GC.PASSIVESPRITECOUNTER.count])
                self.promotes_from.setItemIcon(index + 1, icon)
                for option in self.options[:self.num_options]:
                    option.setItemIcon(index, icon)

class PortraitView(QtGui.QWidget):
    def __init__(self, window):
        super(PortraitView, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.window = window
        # window.setLayout(self.grid)
        self.current = None

        # === Unit Face Display ===
        face_grid = QtGui.QGridLayout()

        self.portrait = QtGui.QLabel()
        face_grid.addWidget(self.portrait, 0, 0, 4, 4, QtCore.Qt.AlignCenter)

        face2_grid = QtGui.QHBoxLayout()
        self.blink_button = QtGui.QPushButton('Blink')
        self.blink_button.setCheckable(True)
        self.blink_button.clicked.connect(self.blink)
        self.smile_button = QtGui.QPushButton('Smile')
        self.smile_button.setCheckable(True)
        self.smile_button.clicked.connect(self.smile)
        self.talk_button = QtGui.QPushButton('Talk')
        self.talk_button.setCheckable(True)
        self.talk_button.clicked.connect(self.talk)
        face2_grid.addWidget(self.blink_button)
        face2_grid.addWidget(self.smile_button)
        face2_grid.addWidget(self.talk_button)
        face_grid.addLayout(face2_grid, 4, 0, 1, 4)

        blink_label = QtGui.QLabel('Blink Position (x, y)')
        mouth_label = QtGui.QLabel('Mouth Position (x, y)')
        face_grid.addWidget(blink_label, 5, 0, 1, 2)
        face_grid.addWidget(mouth_label, 5, 2, 1, 2)
        self.pos_boxes = []
        self.portrait_change = True
        for num in xrange(4):
            box = QtGui.QSpinBox()
            box.setMinimum(0)
            box.setMaximum(96)
            box.valueChanged.connect(self.spin_box_change)
            face_grid.addWidget(box, 6, num)
            self.pos_boxes.append(box)

        # Name
        char_grid = QtGui.QGridLayout()
        name_label = QtGui.QLabel('Name:')
        char_grid.addWidget(name_label, 0, 0)
        self.name = QtGui.QLineEdit()
        self.name.setMaxLength(12)
        self.name.setStatusTip("Change name")
        char_grid.addWidget(self.name, 0, 1)
        reload_button = QtGui.QPushButton('Find')
        reload_button.clicked.connect(self.reload_current)
        char_grid.addWidget(reload_button, 0, 2)

        self.grid.addLayout(face_grid, 0, 0)
        self.grid.addLayout(char_grid, 1, 0)
            
    # For face
    def blink(self):
        if self.blink_button.isChecked():
            self.current.blinking = 1
        else:
            self.current.blinking = 2

    def smile(self):
        if self.smile_button.isChecked():
            self.current.expression ='Smiling'
        else:
            self.current.expression = 'Normal'

    def talk(self):
        if self.talk_button.isChecked():
            self.current.talk()
        else:
            self.current.stop_talking()

    def reload_current(self):
        if self.current:
            name = str(self.name.text())
            try:
                new_portrait = UnitPortrait(name, self.current.blink_position, self.current.mouth_position, (0, 0))
                self.window.data[self.window.list.currentRow()] = new_portrait
                self.current = new_portrait
            except KeyError:
                # Show pop-up
                message_box = QtGui.QMessageBox()
                message_box.setText("No png file named %s found in Data/Characters/" % (name + 'Portrait.png'))
                message_box.exec_()
            self.window.reset()

    def spin_box_change(self):
        if self.portrait_change:
            self.current.blink_position = self.pos_boxes[0].value(), self.pos_boxes[1].value()
            self.current.mouth_position = self.pos_boxes[2].value(), self.pos_boxes[3].value()

    # Displaying functions
    def display(self, portrait):
        self.current = portrait

        # Name
        self.name.setText(portrait.name)

        # Face
        self.smile()  # Check these
        self.talk() 
        portrait.create_image()
        pixmap = create_pixmap(Engine.transform_scale(portrait.image.convert_alpha(), (96*2, 80*2)))
        self.portrait.setPixmap(pixmap)
        self.portrait_change = False
        self.pos_boxes[0].setValue(portrait.blink_position[0])
        self.pos_boxes[1].setValue(portrait.blink_position[1])
        self.pos_boxes[2].setValue(portrait.mouth_position[0])
        self.pos_boxes[3].setValue(portrait.mouth_position[1])
        self.portrait_change = True

    def save_current(self):
        pass

    def tick(self, current_time):
        if self.current:
            self.current.update(current_time)
            self.current.create_image()
            pixmap = create_pixmap(Engine.transform_scale(self.current.image.convert_alpha(), (96*2, 80*2)))
            self.portrait.setPixmap(pixmap)

class GenericMenu(QtGui.QWidget):
    def __init__(self, data, kind, view, parent=None):
        super(GenericMenu, self).__init__(parent)

        self.data = data
        self.kind = kind
        # Create list
        self.list = QtGui.QListWidget(self)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setDragDropMode(self.list.InternalMove)
        self.list.setIconSize(QtCore.QSize(32, 32))

        for index, datum in enumerate(data):
            icon = create_icon(datum.image.convert_alpha())
            item = QtGui.QListWidgetItem(datum.name)
            item.setIcon(icon)
            self.list.addItem(item)

        self.list.currentItemChanged.connect(self.on_item_changed)
        self.list.model().rowsMoved.connect(self.on_reorder)

        self.add_button = QtGui.QPushButton("Add " + kind)
        self.add_button.clicked.connect(self.add)
        self.add_button.setStatusTip("Insert a new " + kind.lower())
        self.remove_button = QtGui.QPushButton("Remove " + kind)
        self.remove_button.clicked.connect(self.remove)
        self.remove_button.setStatusTip("Remove selected " + kind.lower() + " data")
        self.save_button = QtGui.QPushButton("Save to File")
        self.save_button.clicked.connect(self.save)
        self.save_button.setStatusTip("Write out current " + kind.lower() + " data to file")
        button_grid = QtGui.QGridLayout()
        button_grid.addWidget(self.add_button, 0, 0)
        button_grid.addWidget(self.remove_button, 1, 0)
        button_grid.addWidget(self.save_button, 2, 0)

        # Create view
        self.view = view(self)

        # Create layout
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.grid.addWidget(self.list, 0, 0)
        self.grid.addLayout(button_grid, 1, 0)
        self.grid.addLayout(self.view.grid, 0, 1, 2, 1)

    def tick(self, current_time):
        self.view.tick(current_time)

    def on_item_changed(self, curr, prev):
        current_idx = self.list.row(curr)
        d = self.data[current_idx]
        self.view.save_current()
        self.view.display(d)

    def on_reorder(self, row, old_idx, new_idx):
        moved_d = self.data.pop(old_idx)
        new_idx = self.list.currentRow()
        self.data.insert(new_idx, moved_d)

    def remove(self):
        idx = self.list.currentRow()
        del self.data[idx]
        self.list.takeItem(idx)
        if idx < len(self.data):
            new = self.data[idx]
            self.view.display(new)
        else:
            self.view.display(self.data[-1])

    def reset(self):
        idx = self.list.currentRow()
        item = self.list.currentItem()
        item.setText(self.data[idx].name)
        if self.data[idx].image:
            item.setIcon(create_icon(self.data[idx].image.convert_alpha()))
        else:
            item.setIcon(QtGui.QIcon())

class UnitMenu(GenericMenu):
    def add(self):
        unit = Unit(None, portrait_data)
        current_idx = self.list.currentRow()
        self.data.insert(current_idx + 1, unit)
        icon = create_icon(unit.image)
        item = QtGui.QListWidgetItem(unit.name)
        item.setIcon(icon)
        self.list.insertItem(current_idx + 1, item)

    def save(self):
        root = ET.Element("unit_catalog")
        for u in self.data:
            unit = ET.SubElement(root, "unit", name=u.name)
            ET.SubElement(unit, "id").text = u.name
            ET.SubElement(unit, "gender").text = str(u.gender)
            ET.SubElement(unit, "wexp").text = ','.join([str(w) for w in u.wexp])
            ET.SubElement(unit, "bases").text = ','.join([str(s.base_stat) for s in u.stats.values()])
            ET.SubElement(unit, "growths").text = ','.join([str(g) for g in u.growths])
            ET.SubElement(unit, "inventory").text = ','.join([i.id for i in u.items])
            ET.SubElement(unit, "level").text = str(u.level)
            ET.SubElement(unit, "class").text = u.klass
            ET.SubElement(unit, "desc").text = u.desc
            ET.SubElement(unit, "faction").text = u.faction
            ET.SubElement(unit, "tags").text = ','.join(u.tags)
            ET.SubElement(unit, "skills").text = ','.join([s.id for s in u.skills])

        if PRETTY:
            with open("units.xml", 'w') as fp:
                fp.write(prettify(root))
        else:
            tree = ET.ElementTree(root)
            tree.write("units.xml")

        # Show pop-up
        message_box = QtGui.QMessageBox()
        message_box.setText("Saved to units.xml")
        message_box.exec_()

class ClassMenu(GenericMenu):
    def add(self):
        klass = Klass()
        current_idx = self.list.currentRow()
        self.data.insert(current_idx + 1, klass)
        icon = create_icon(klass.image)
        item = QtGui.QListWidgetItem(klass.name)
        item.setIcon(icon)
        self.list.insertItem(current_idx + 1, item)

    def save(self):
        root = ET.Element("class_info")
        for u in self.data:
            klass = ET.SubElement(root, "class", name=u.name)
            ET.SubElement(klass, "wexp").text = ','.join([str(w) for w in u.wexp])
            ET.SubElement(klass, "promotes_from").text = u.promotes_from
            ET.SubElement(klass, "turns_into").text = ','.join(u.promotes_to)
            ET.SubElement(klass, "movement_group").text = str(u.movement_group)
            ET.SubElement(klass, "tags").text = ','.join(u.tags)
            skills = zip([str(l) for l in u.skill_levels], u.skills)
            ET.SubElement(klass, "skills").text = ';'.join([','.join(s) for s in skills])            
            ET.SubElement(klass, "bases").text = ','.join([str(b) for b in u.bases])
            ET.SubElement(klass, "growths").text = ','.join([str(g) for g in u.growths])
            ET.SubElement(klass, "promotion").text = ','.join([str(p) for p in u.promotion])
            ET.SubElement(klass, "max").text = ','.join([str(m) for m in u.max])
            ET.SubElement(klass, "desc").text = u.desc

        if PRETTY:
            with open("class_info.xml", 'w') as fp:
                fp.write(prettify(root))
        else:
            tree = ET.ElementTree(root)
            tree.write("class_info.xml")

        # Show pop-up
        message_box = QtGui.QMessageBox()
        message_box.setText("Saved to class_info.xml")
        message_box.exec_()

class PortraitMenu(GenericMenu):
    def add(self):
        portrait = UnitPortrait('Generic', (0, 0), (0, 0), (0, 0))
        current_idx = self.list.currentRow()
        self.data.insert(current_idx + 1, portrait)
        icon = create_icon(portrait.image.convert_alpha())
        item = QtGui.QListWidgetItem(portrait.name)
        item.setIcon(icon)
        self.list.insertItem(current_idx + 1, item)

    def save(self):
        root = ET.Element("portrait_info")
        for p in self.data:
            unit = ET.SubElement(root, "portrait", name=p.name)
            ET.SubElement(unit, "blink").text = ','.join([str(pos) for pos in p.blink_position])
            ET.SubElement(unit, "mouth").text = ','.join([str(pos) for pos in p.mouth_position])

        if PRETTY:
            with open("portrait_coords.xml", 'w') as fp:
                fp.write(prettify(root))
        else:
            tree = ET.ElementTree(root)
            tree.write("portrait_coords.xml")

        # Show pop-up
        message_box = QtGui.QMessageBox()
        message_box.setText("Saved to portrait_coords.xml")
        message_box.exec_()

class MainEditor(QtGui.QMainWindow):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Game Editor')
        self.tabs = QtGui.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Set up status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')

        # Set up self.tabs
        self.tab_names = ["Units", "Classes", "Items", "Skills", 
                          "Lore", "Portraits", "Weapons", "Terrain", 
                          "Movement", "Constants"]
        self.tab_directory = {}
        self.menu_directory = {}
        for name in self.tab_names:
            tab = QtGui.QWidget()
            self.tabs.addTab(tab, name)
            self.tab_directory[name] = tab

        self.tabs.currentChanged.connect(self.page_swap)
        self.current_idx = 0

        # === Timing ===
        self.main_timer = QtCore.QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.main_timer.start(33)  # 30 FPS
        self.elapsed_timer = QtCore.QElapsedTimer()
        self.elapsed_timer.start()

    def start(self):
        self.load_tab(self.current_idx)

    def page_swap(self, new):
        # new is index of tab
        print('Switching Pages')
        print(self.tab_names[new])
        self.current_menu.view.save_current()
        self.current_idx = new
        self.load_tab(new)
        if self.current_menu.view.current:
            self.current_menu.view.display(self.current_menu.view.current)

    def load_tab(self, idx):
        if idx == 0:
            self.load_unit_tab()
        elif idx == 1:
            self.load_class_tab()
        elif idx == 5:
            self.load_portrait_tab()

    def load_unit_tab(self):
        if "Units" not in self.menu_directory:
            self.menu_directory["Units"] = UnitMenu(unit_data, 'Unit', UnitView)
            self.tab_directory["Units"].setLayout(self.menu_directory["Units"].grid)
        self.current_menu = self.menu_directory["Units"]

    def load_class_tab(self):
        if "Classes" not in self.menu_directory:
            self.menu_directory["Classes"] = ClassMenu(class_data, 'Class', ClassView)
            self.tab_directory["Classes"].setLayout(self.menu_directory["Classes"].grid)
        self.current_menu = self.menu_directory["Classes"]

    def load_portrait_tab(self):
        if "Portraits" not in self.menu_directory:
            self.menu_directory["Portraits"] = PortraitMenu(portrait_data, 'Portrait', PortraitView)
            self.tab_directory["Portraits"].setLayout(self.menu_directory["Portraits"].grid)
        self.current_menu = self.menu_directory["Portraits"]

    def tick(self):
        current_time = self.elapsed_timer.elapsed()
        name = self.tab_names[self.current_idx]
        menu = self.menu_directory[name]
        menu.tick(current_time)

def load_data(window):
    item_data = [ItemMethods.itemparser(item) for item in GC.ITEMDATA]
    item_data = sorted(item_data, key=lambda item: GC.ITEMDATA[item.id]['num'])
    item_data = [item for item in item_data if not item.virtual]
    for item in item_data:
        if item.image:
            item.image = item.image.convert_alpha()
    skill_data = [StatusObject.statusparser(skill.find('id').text) for skill in GC.STATUSDATA.getroot().findall('status')]
    for skill in skill_data:
        if skill.image:
            skill.image = skill.image.convert_alpha()
    portrait_dict = SaveLoad.create_portrait_dict()
    
    class_dict = SaveLoad.create_class_dict()
    class_data = [Klass(v) for v in class_dict.values()]
    unit_data = build_units(class_dict, portrait_dict)
    # Setting up portrait data
    portrait_data = []
    for name, portrait in portrait_dict.items():
        portrait_data.append(UnitPortrait(name, portrait['blink'], portrait['mouth'], (0, 0)))
    for portrait in portrait_data:
        portrait.create_image()
        portrait.image = portrait.image.convert_alpha()

    return unit_data, class_data, item_data, skill_data, portrait_data

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = MainEditor()
    unit_data, class_data, item_data, skill_data, portrait_data = load_data(window)
    window.start()
    # Engine.remove_display()
    window.show()
    app.exec_()
