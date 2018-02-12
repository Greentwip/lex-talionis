import sys
from collections import OrderedDict
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

import EditorUtilities

teams = ('player', 'enemy', 'other', 'enemy2')

# === DATA IMPORTING ===
def build_units(class_dict):
    units = OrderedDict()
    for unit in GC.UNITDATA.getroot().findall('unit'):
        u_i = {}
        u_i['id'] = unit.find('id').text
        u_i['name'] = unit.get('name')
        u_i['generic'] = False

        classes = unit.find('class').text.split(',')
        u_i['klass'] = classes[-1]

        u_i['gender'] = unit.find('gender').text
        u_i['level'] = int(unit.find('level').text)
        u_i['faction'] = unit.find('faction').text

        # stats = SaveLoad.intify_comma_list(unit.find('bases').text)
        # for n in xrange(len(stats), cf.CONSTANTS['num_stats']):
        #     stats.append(class_dict[u_i['klass']]['bases'][n])
        # assert len(stats) == cf.CONSTANTS['num_stats'], "bases %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])
        # u_i['stats'] = SaveLoad.build_stat_dict(stats)
        # # print("%s's stats: %s", u_i['name'], u_i['stats'])

        # u_i['growths'] = SaveLoad.intify_comma_list(unit.find('growths').text)
        # u_i['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(u_i['growths'])))
        # assert len(u_i['growths']) == cf.CONSTANTS['num_stats'], "growths %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])

        u_i['items'] = ItemMethods.itemparser(unit.find('inventory').text)
        # # Parse wexp
        # u_i['wexp'] = unit.find('wexp').text.split(',')
        # for index, wexp in enumerate(u_i['wexp'][:]):
        #     if wexp in CustomObjects.WEAPON_EXP.wexp_dict:
        #         u_i['wexp'][index] = CustomObjects.WEAPON_EXP.wexp_dict[wexp]
        # u_i['wexp'] = [int(num) for num in u_i['wexp']]

        # assert len(u_i['wexp']) == len(CustomObjects.WEAPON_TRIANGLE.types), "%s's wexp must have as many slots as there are weapon types."%(u_i['name'])
        
        u_i['desc'] = unit.find('desc').text
        # Tags
        u_i['tags'] = set(unit.find('tags').text.split(',')) if unit.find('tags') is not None and unit.find('tags').text is not None else set()

        # Personal Skills
        personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []
        u_i['skills'] = [StatusObject.statusparser(status) for status in personal_skills]

        units[u_i['id']] = Unit(u_i)
    return units

# === MODEL CLASS ===
class Unit(object):
    def __init__(self, info=None):
        if info:
            self.id = info.get('id', 100)
            self.group = info.get('group')
            self.name = info['name']
            self.generic = info.get('generic', False)

            self.position = None
            self.level = int(info['level'])
            self.gender = int(info['gender'])
            self.faction = info['faction']
            self.klass = info['klass']
            self.tags = info.get('tags', [])
            self.desc = info['desc']

            # self.wexp = info.get('wexp', [])
            self.items = info['items']
            self.skills = info.get('skills', [])

            self.team = info.get('team', 'player')
            self.ai = info.get('ai', None)
            self.ai_group = info.get('ai_group', None)
            try:
                self.image = EditorUtilities.create_chibi(self.name)
            except KeyError:
                self.image = GC.UNITDICT[self.faction + 'Emblem'].convert_alpha()
        else:
            self.id = 0
            self.group = None
            self.name = ''
            self.generic = True
            self.position = None
            self.level = 1
            self.gender = 0
            self.faction = ''
            self.klass = 'Citizen'
            self.tags = set()
            self.desc = ''
            # current_class = EditorUtilities.find(class_data, self.klass)
            self.items = []
            self.skills = []
            # self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
            self.team = 'player'
            self.ai = 'None'
            self.ai_group = None
            self.image = None
        self.saved = False
        self.klass_image = False

    def copy(self):
        new_unit = Unit()
        new_unit.id = self.id
        new_unit.group = self.group
        new_unit.name = self.name
        new_unit.generic = self.generic
        new_unit.saved = self.saved
        new_unit.position = None
        new_unit.gender = self.gender
        new_unit.klass = self.klass
        new_unit.tags = self.tags
        new_unit.faction = self.faction
        new_unit.desc = self.desc
        new_unit.team = self.team
        new_unit.items = [ItemMethods.itemparser(item.id)[0] for item in self.items]
        new_unit.ai = self.ai
        new_unit.image = self.image
        return new_unit

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

        # Set up images
        units = []
        for team in teams:
            try:
                unit = GenericUnit(self.name, team)
            except KeyError as e:
                # print('KeyError: %s' % e)
                unit = GenericUnit('Citizen', team)
            units.append(unit)
        self.male_images = {unit.team: (unit.image1, unit.image2, unit.image3) for unit in units}
        units = []
        for team in teams:
            try:
                unit = GenericUnit(self.name, team, gender=5)
            except KeyError as e:
                # print('KeyError: %s' % e)
                unit = GenericUnit('Citizen', team, gender=5)
            units.append(unit)
        self.female_images = {unit.team: (unit.image1, unit.image2, unit.image3) for unit in units}

    def get_image(self, team, gender):
        if gender < 5:
            team_images = self.male_images[team]
            return team_images[GC.PASSIVESPRITECOUNTER.count]
        else:
            team_images = self.female_images[team]
            return team_images[GC.PASSIVESPRITECOUNTER.count]

# === For use by class object ===
class GenericUnit(object):
    def __init__(self, klass, team, gender=0):
        self.gender = gender
        self.team = team
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

class GlobalData(object):
    def __init__(self):
        self.load_data()

    def load_data(self):
        # === Terrain Data ===
        # Saved dictionary of terrains 2-tuple {color: (id, name)}
        self.terrain_data = OrderedDict()
        # Ingest terrain_data
        for terrain in GC.TERRAINDATA.getroot().findall('terrain'):
            color = tuple(int(num) for num in terrain.find('color').text.split(','))
            tid = terrain.find('id').text
            name = terrain.get('name')
            self.terrain_data[color] = (tid, name)

        # === Item Data ===
        self.item_data = OrderedDict()
        items = [ItemMethods.itemparser(item)[0] for item in GC.ITEMDATA]
        items = sorted(items, key=lambda item: GC.ITEMDATA[item.id]['num'])
        items = [item for item in items if not item.virtual]
        for item in items:
            if item.image:
                item.image = item.image.convert_alpha()
            self.item_data[item.id] = item

        # === Skill Data ===
        self.skill_data = OrderedDict()
        skills = [StatusObject.statusparser(skill.find('id').text) for skill in GC.STATUSDATA.getroot().findall('status')]
        for skill in skills:
            if skill.image:
                skill.image = skill.image.convert_alpha()
            self.skill_data[skill.id] = skill

        # === Protrait Data ===
        # Has mouth and blink positions by name
        portrait_dict = SaveLoad.create_portrait_dict()
        # Setting up portrait data
        self.portrait_data = OrderedDict()
        for name, portrait in portrait_dict.items():
            self.portrait_data[name] = UnitPortrait(name, portrait['blink'], portrait['mouth'], (0, 0))
        for portrait in self.portrait_data.values():
            portrait.create_image()
            portrait.image = portrait.image.convert_alpha()
        
        # === Class Data ===
        self.class_dict = SaveLoad.create_class_dict()
        self.class_data = OrderedDict()
        for klass_id, klass in self.class_dict.items():
            self.class_data[klass_id] = Klass(klass)

        # === Loaded Preset Unit Data ===
        self.unit_data = build_units(self.class_dict)

Data = GlobalData()
