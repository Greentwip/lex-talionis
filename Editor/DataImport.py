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

import EditorUtilities

teams = ('player', 'enemy', 'other', 'enemy2')

# === DATA IMPORTING ===
def build_units(class_dict):
    units = []
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

            self.stats = info.get('stats', None)
            self.growths = info.get('growths', None)

            self.wexp = info.get('wexp', [])
            self.items = info['items']
            self.skills = info.get('skills', [])

            self.team = info.get('team', 'player')
            self.ai = info.get('ai', None)
            try:
                self.image = EditorUtilities.create_chibi(self.name)
            except KeyError:
                self.image = GC.UNITDICT[self.faction + 'Emblem'].convert_alpha()
        else:
            self.id = 0
            self.name = ''
            self.generic = True
            self.position = None
            self.level = 1
            self.gender = 0
            self.faction = ''
            self.klass = 'Citizen'
            self.tags = set()
            self.desc = ''
            current_class = EditorUtilities.find(class_data, self.klass)
            self.stats = SaveLoad.build_stat_dict(current_class.bases)
            self.growths = [0 for n in xrange(cf.CONSTANTS['num_stats'])]
            self.items = []
            self.skills = []
            self.wexp = [0 for n in xrange(len(CustomObjects.WEAPON_TRIANGLE.types))]
            self.team = 'player'
            self.ai = 'None'
            self.image = None
        self.saved = False

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

        self.units = []
        for team in teams:
            try:
                unit = GenericUnit(self.name, team)
                self.units.append(unit)
            except KeyError as e:
                print('KeyError: %s' % e)
                continue
        self.images = {unit.team: (unit.image1, unit.image2, unit.image3) for unit in self.units}

    def get_image(self, team):
        return self.images[team][0]

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

def load_data():
    item_data = [ItemMethods.itemparser(item)[0] for item in GC.ITEMDATA]
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
    unit_data = build_units(class_dict)
    # Setting up portrait data
    portrait_data = []
    for name, portrait in portrait_dict.items():
        portrait_data.append(UnitPortrait(name, portrait['blink'], portrait['mouth'], (0, 0)))
    for portrait in portrait_data:
        portrait.create_image()
        portrait.image = portrait.image.convert_alpha()

    return unit_data, class_dict, class_data, item_data, skill_data, portrait_data

unit_data, class_dict, class_data, item_data, skill_data, portrait_data = load_data()
