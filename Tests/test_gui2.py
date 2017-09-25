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
from Code.Dialogue import UnitPortrait

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
        
        blink_pos = (0, 0)
        mouth_pos = (0, 0)
        try:
            # Ex: HectorPortrait
            if self.name in portrait_dict:
                blink_pos = portrait_dict[self.name]['blink']
                mouth_pos = portrait_dict[self.name]['mouth']
            self.portrait = UnitPortrait(self.name, blink_pos, mouth_pos, (0, 0))
            self.chibi = Engine.subsurface(GC.UNITDICT[self.name + 'Portrait'], (96, 16, 32, 32)).convert_alpha()
        except KeyError:
            self.portrait = UnitPortrait('Generic', blink_pos, mouth_pos, (0, 0))
            self.chibi = GC.UNITDICT[self.faction + 'Emblem'].convert_alpha()
        # self.chibi = Engine.transform_scale(self.chibi, (64, 64))

# === A new unit when created ===
class DefaultUnit(object):
    portrait = Engine.subsurface(GC.UNITDICT['GenericPortrait'], (0, 0, 96, 80)).convert_alpha()
    chibi = Engine.subsurface(GC.UNITDICT['GenericPortrait'], (96, 16, 32, 32)).convert_alpha()

    def __init__(self):
        self.id = 0
        self.name = ''
        self.level = 1
        self.gender = 0
        self.faction = ''
        self.klass = 'Citizen'
        self.tags = set()
        self.desc = ''
        self.stats = SaveLoad.build_stat_dict(class_dict[self.klass]['bases'])
        self.growths = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
        self.items = []
        self.skills = []
        self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
        self.team = 'player'

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

        # === Unit Face Display ===
        face_grid = QtGui.QGridLayout()

        self.portrait = QtGui.QLabel()
        face_grid.addWidget(self.portrait, 0, 0, 4, 4, QtCore.Qt.AlignCenter)

        self.smile_button = QtGui.QPushButton('Smile')
        self.smile_button.setCheckable(True)
        self.smile_button.clicked.connect(self.smile)
        self.talk_button = QtGui.QPushButton('Talk')
        self.talk_button.setCheckable(True)
        self.talk_button.clicked.connect(self.talk)
        face_grid.addWidget(self.smile_button, 4, 0, 1, 2)
        face_grid.addWidget(self.talk_button, 4, 2, 1, 2)

        blink_label = QtGui.QLabel('Blink Pos. (x, y)')
        mouth_label = QtGui.QLabel('Mouth Pos. (x, y)')
        face_grid.addWidget(blink_label, 5, 0, 1, 2)
        face_grid.addWidget(mouth_label, 5, 2, 1, 2)
        self.portrait_pos_boxes = []
        for num in xrange(4):
            box = QtGui.QSpinBox()
            box.setMinimum(0)
            box.setMaximum(96)
            face_grid.addWidget(box, 6, num)
            self.portrait_pos_boxes.append(box)

        # === Character Data ===
        char_grid = QtGui.QGridLayout()

        # Name
        name_label = QtGui.QLabel('Name:')
        char_grid.addWidget(name_label, 0, 0, 1, 2)
        self.name = QtGui.QLineEdit()
        self.name.setMaxLength(12)
        char_grid.addWidget(self.name, 0, 1, 1, 2)
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
        for klass in klasses:
            if 'icon' in klass and klass['icon']:
                self.klass.addItem(klass['icon'], klass['name'])
            else:
                self.klass.addItem(klass['name'])
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
            icon_label = QtGui.QLabel()
            wexp_icon = CustomObjects.WeaponIcon(idx=index)
            icon_label.setPixmap(create_pixmap(wexp_icon.image.convert_alpha(), self.window))
            wexp_grid.addWidget(name_label, 0, (index + 1)*2 + 1)
            wexp_grid.addWidget(icon_label, 0, (index + 1)*2)
        self.wexp = [QtGui.QSpinBox() for wexp in weapon_types]
        for index, s in enumerate(self.wexp):
            s.setMinimum(0)
            s.setMaximum(CustomObjects.WEAPON_EXP.sorted_list[-1][1])
            wexp_grid.addWidget(s, 1, (index + 1)*2, 1, 2)

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
            item_grid.addWidget(item_box, index + 1, 0, 1, 2)
            item_grid.addWidget(drop, index + 1, 2)
            item_grid.addWidget(event, index + 1, 3)

        item_grid.addWidget(item_label, 0, 0, 1, 2)
        item_grid.addWidget(drop_label, 0, 2)
        item_grid.addWidget(event_label, 0, 3)
        item_grid.addWidget(self.add_item_button, cf.CONSTANTS['max_items'] + 2, 0, 1, 2)
        item_grid.addWidget(self.remove_item_button, cf.CONSTANTS['max_items'] + 2, 2, 1, 2)
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
        self.grid.addLayout(self.stretch(face_grid), 0, 0)
        self.grid.addLayout(self.stretch(char_grid), 0, 1)
        self.grid.addLayout(self.stretch(stat_grid), 1, 0, 1, 2)
        self.grid.addLayout(self.stretch(wexp_grid), 2, 0, 1, 2)
        self.grid.addLayout(self.stretch(item_grid), 3, 0)
        self.grid.addLayout(self.stretch(skill_grid), 3, 1)

        # === Timing ===
        self.main_timer = QtCore.QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.main_timer.start(33) # 30 FPS
        self.elapsed_timer = QtCore.QElapsedTimer()
        self.elapsed_timer.start()

    def stretch(self, grid):
        box_h = QtGui.QHBoxLayout()
        box_h.addStretch(1)
        box_h.addLayout(grid)
        box_h.addStretch(1)
        box_v = QtGui.QVBoxLayout()
        box_v.addStretch(1)
        box_v.addLayout(box_h)
        box_v.addStretch(1)
        return box_v

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

    # For face
    def smile(self):
        if self.smile_button.isChecked():
            self.current_unit.portrait.expression ='Smiling'
        else:
            self.current_unit.portrait.expression = 'Normal'

    def talk(self):
        if self.talk_button.isChecked():
            self.current_unit.portrait.talk()
        else:
            self.current_unit.portrait.stop_talking()

    # Displaying functions
    def disp_unit(self, unit):
        self.current_unit = unit

        # Face
        self.smile()  # Check these
        self.talk() 
        unit.portrait.create_image()
        pixmap = create_pixmap(Engine.transform_scale(unit.portrait.image.convert_alpha(), (96*2, 80*2)), self.window)
        self.portrait.setPixmap(pixmap)
        self.portrait_pos_boxes[0].setValue(unit.portrait.blink_position[0])
        self.portrait_pos_boxes[1].setValue(unit.portrait.blink_position[1])
        self.portrait_pos_boxes[2].setValue(unit.portrait.mouth_position[0])
        self.portrait_pos_boxes[3].setValue(unit.portrait.mouth_position[1])

        # Char data
        self.name.setText(unit.name)
        # self.team.setCurrentIndex(self.teams.index(unit.team))
        self.gender.setValue(unit.gender)
        self.level.setValue(unit.level)
        self.faction.setText(unit.faction)
        self.lord.setChecked('Lord' in unit.tags)
        self.boss.setChecked('Boss' in unit.tags)
        self.desc.setText(unit.desc)
        self.klass.setCurrentIndex([k['name'] for k in klasses].index(unit.klass))

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

    def save_current_unit(self):
        if self.current_unit:
            self.current_unit.name = str(self.name.text())
            # self.current_unit.team = str(self.team.currentText())
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

            self.current_unit.items = []
            for index, (item_box, drop_box, event_box) in enumerate(self.items[:self.num_items]):
                item = item_data[item_box.currentIndex()]
                item.droppable = drop_box.isChecked()
                item.event_combat = event_box.isChecked()
                self.current_unit.items.append(item)

            self.current_unit.skills = []
            for index, skill_box in enumerate(self.skills[:self.num_skills]):
                self.current_unit.skills.append(skill_data[skill_box.currentIndex()])

    def tick(self):
        # Update global sprite counters
        current_time = self.elapsed_timer.elapsed()
        
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for index, klass in enumerate(klasses):
                klass['icon'] = create_icon(klass['images'][GC.PASSIVESPRITECOUNTER.count], window)
                self.klass.setItemIcon(index, klass['icon'])

        self.current_unit.portrait.update(current_time)
        self.current_unit.portrait.create_image()
        pixmap = create_pixmap(Engine.transform_scale(self.current_unit.portrait.image.convert_alpha(), (96*2, 80*2)), self.window)
        self.portrait.setPixmap(pixmap)

def on_item_changed(curr, prev):
    current_idx = unit_list.row(curr)
    unit = units[current_idx]
    unit_view.save_current_unit()
    unit_view.disp_unit(unit)

def on_reorder(row, old_idx, new_idx):
    moved_unit = units.pop(old_idx)
    new_idx = unit_list.currentRow()
    units.insert(new_idx, moved_unit)

def add_unit():
    unit = DefaultUnit()
    current_idx = unit_list.currentRow()
    units.insert(current_idx + 1, unit)
    icon = create_icon(unit.chibi, main_widget)
    item = QtGui.QListWidgetItem(unit.name)
    item.setIcon(icon)
    unit_list.insertItem(current_idx + 1, item)

def remove_unit():
    idx = unit_list.currentRow()
    del units[idx]
    unit_list.takeItem(idx)
    if idx < len(units):
        new_current_unit = units[idx]
        unit_view.disp_unit(new_current_unit)
    else:
        unit_view.disp_unit(units[-1])

def save_to_file():
    pass

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = QtGui.QMainWindow()
    main_widget = QtGui.QWidget()  # Needed for layout setting
    window.setCentralWidget(main_widget)
    # Create layout
    grid = QtGui.QGridLayout()
    main_widget.setLayout(grid)

    window.setWindowTitle('Game Editor')
    # window.setMinimumSize(640, 640)

    # Get data
    item_data = [ItemMethods.itemparser(item)[0] for item in GC.ITEMDATA]
    item_data = sorted(item_data, key=lambda item: GC.ITEMDATA[item.id]['num'])
    item_data = [item for item in item_data if not item.virtual]
    for item in item_data:
        if item.image:
            item.icon = create_icon(item.image.convert_alpha(), window)
    skill_data = [StatusObject.statusparser(skill.find('id').text) for skill in GC.STATUSDATA.getroot().findall('status')]
    for skill in skill_data:
        if skill.icon:
            skill.icon = create_icon(skill.icon.convert_alpha(), window)
    portrait_dict = SaveLoad.create_portrait_dict()
    class_dict = SaveLoad.create_class_dict()
    for klass in class_dict.values():
        generic_unit = GenericUnit(klass['name'])
        klass['images'] = (generic_unit.image1, generic_unit.image2, generic_unit.image3)
        klass['icon'] = create_icon(klass['images'][0], window)
    klasses = sorted([klass for klass in class_dict.values()], key=lambda x: (x['id']%100, x['id']))
    units = build_units(class_dict)

    # Create list
    current_idx = 0
    unit_list = QtGui.QListWidget(main_widget)
    unit_list.setMinimumSize(128, 320)
    # unit_list.selectionModel().currentChanged.connect(on_item_changed)
    unit_list.uniformItemSizes = True
    unit_list.setDragDropMode(unit_list.InternalMove)
    unit_list.setIconSize(QtCore.QSize(32, 32))
    # model = QtGui.QStandardItemModel(unit_list)

    for index, unit in enumerate(units):
        icon = create_icon(unit.chibi, main_widget)
        # Image_Modification.print_image(icon)
        item = QtGui.QListWidgetItem(unit.name)
        item.setIcon(icon)
        unit_list.addItem(item)

    # apply the model to the list view
    unit_list.currentItemChanged.connect(on_item_changed)
    unit_list.model().rowsMoved.connect(on_reorder)

    add_unit_button = QtGui.QPushButton("Add Unit")
    add_unit_button.clicked.connect(add_unit)
    remove_unit_button = QtGui.QPushButton("Remove Unit")
    remove_unit_button.clicked.connect(remove_unit)
    save_button = QtGui.QPushButton("Save to File")
    save_button.clicked.connect(save_to_file)
    button_grid = QtGui.QGridLayout()
    button_grid.addWidget(add_unit_button, 0, 0)
    button_grid.addWidget(remove_unit_button, 1, 0)
    button_grid.addWidget(save_button, 2, 0)

    grid.addWidget(unit_list, 0, 0)
    grid.addLayout(button_grid, 1, 0)
    unit_view = UnitView(window)
    grid.addLayout(unit_view.grid, 0, 1, 2, 1)

    # Engine.remove_display()
    window.show()
    app.exec_()
