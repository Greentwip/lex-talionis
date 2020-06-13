from . import GlobalConstants as GC
from . import configuration as cf
from . import Engine

# === WEAPON TRIANGLE OBJECT ==================================================
class Weapon_Triangle(object):
    def __init__(self, fn):
        self.types = []
        self.advantage = {}
        self.disadvantage = {}
        self.name_to_index = {}
        self.index_to_name = {}
        self.magic_types = set()

        self.parse_file(fn)

    def number(self):
        return len(self.types)

    def parse_file(self, fn):
        with open(fn, mode='r', encoding='utf-8') as fp:
            lines = fp.readlines()

        for index, line in enumerate(lines):
            split_line = line.strip().split(';')
            name = split_line[0]
            advantage = split_line[1].split(',')
            disadvantage = split_line[2].split(',')
            magic = True if split_line[3] == 'M' else False
            # Ascend
            self.types.append(name)
            self.name_to_index[name] = index
            self.index_to_name[index] = name
            self.advantage[name] = advantage
            self.disadvantage[name] = disadvantage
            if magic:
                self.magic_types.add(name)

        self.name_to_index['Consumable'] = len(lines)
        self.index_to_name[len(lines)] = 'Consumable'

    def compute_advantage(self, weapon1, weapon2):
        """ Returns two-tuple describing advantage """
        if not weapon1 and not weapon2:
            return (0, 0) # If either does not have a weapon, neither has advantage
        elif not weapon1:
            return (0, cf.CONSTANTS['unarmed_punish'])
        elif not weapon2:
            return (cf.CONSTANTS['unarmed_punish'], 0)
        if not weapon1.TYPE or not weapon2.TYPE:
            return (0, 0)
        if weapon1.ignore_weapon_advantage or weapon2.ignore_weapon_advantage:
            return (0, 0)

        weapon1_advantage, weapon2_advantage = 0, 0
        if weapon2.TYPE in self.advantage[weapon1.TYPE]:
            weapon1_advantage += 1
        if weapon2.TYPE in self.disadvantage[weapon1.TYPE]:
            weapon1_advantage -= 1
        if weapon1.TYPE in self.advantage[weapon2.TYPE]:
            weapon2_advantage += 1
        if weapon1.TYPE in self.disadvantage[weapon2.TYPE]:
            weapon2_advantage -= 1

        # Handle reverse (reaver) weapons
        if weapon1.reverse or weapon2.reverse:
            return (-2*weapon1_advantage, -2*weapon2_advantage)
        else:
            return (weapon1_advantage, weapon2_advantage)

class Weapon_Advantage(object):
    class Advantage(object):
        def __init__(self, damage, resist, accuracy, avoid, crit, evade, attackspeed):
            self.damage = damage
            self.resist = resist
            self.accuracy = accuracy
            self.avoid = avoid
            self.crit = self.crit_accuracy = crit
            self.evade = self.dodge = self.crit_avoid = evade
            self.attackspeed = attackspeed

    def __init__(self, fn):
        self.wadv_dict = {}
        self.wdadv_dict = {}
        self.no_advantage = self.Advantage(0, 0, 0, 0, 0, 0, 0)
        self.parse_file(fn)

    def parse_file(self, fn):
        with open(fn, mode='r', encoding='utf-8') as fp:
            lines = [l.strip() for l in fp.readlines()]

        on_disadvantage = False
        for index, line in enumerate(lines):
            if line.startswith('#'):
                continue
            elif line.startswith('Disadvantage'):
                on_disadvantage = True
                continue
            split_line = line.split()
            weapon_type = split_line[0]
            weapon_rank = split_line[1]
            stats = [int(x) for x in split_line[2:]]
            if on_disadvantage:
                if weapon_type not in self.wdadv_dict:
                    self.wdadv_dict[weapon_type] = {}
                self.wdadv_dict[weapon_type][weapon_rank] = self.Advantage(*stats)
            else:
                if weapon_type not in self.wadv_dict:
                    self.wadv_dict[weapon_type] = {}
                self.wadv_dict[weapon_type][weapon_rank] = self.Advantage(*stats)

        assert 'All' in self.wadv_dict
        assert 'All' in self.wadv_dict['All']
        assert 'All' in self.wdadv_dict
        assert 'All' in self.wdadv_dict['All']

    def _get_data(self, weapon, wexp, data):
        if weapon:
            weapon_type = weapon.TYPE
            if not weapon_type:
                return self.no_advantage
            weapon_wexp = wexp[TRIANGLE.name_to_index[weapon_type]]
            weapon_rank = EXP.number_to_letter(weapon_wexp)
            if weapon_type in data:
                if weapon_rank in data[weapon_type]:
                    return data[weapon_type][weapon_rank]
                else:
                    return data[weapon_type]['All']
            else:
                if weapon_rank in data['All']:
                    return data['All'][weapon_rank]
                else:
                    return data['All']['All']
        else:
            return self.no_advantage

    def get_advantage(self, weapon, wexp):
        return self._get_data(weapon, wexp, self.wadv_dict)

    def get_disadvantage(self, weapon, wexp):
        return self._get_data(weapon, wexp, self.wdadv_dict)

class Weapon_Exp(object):
    def __init__(self, fn):
        self.wexp_dict = {}
        self.sorted_list = []
        self.rank_bonuses = {}
        self.parse_file(fn)

    def parse_file(self, fn):
        with open(fn, mode='r', encoding='utf-8') as fp:
            lines = fp.readlines()

        for line in lines:
            if line.startswith('#'):
                continue
            split_line = line.strip().split(';')
            letter = split_line[0]
            number = int(split_line[1])
            if len(split_line) > 2:
                accuracy = int(split_line[2])
            else:
                accuracy = 0
            if len(split_line) > 3:
                damage = int(split_line[3])
            else:
                damage = 0
            if len(split_line) > 4:
                crit_rate = int(split_line[4])
            else:
                crit_rate = 0
            self.wexp_dict[letter] = number
            self.rank_bonuses[letter] = (accuracy, damage, crit_rate)

        self.sorted_list = sorted(self.wexp_dict.items(), key=lambda x: x[1])

    def number_to_letter(self, wexp):
        current_letter = "--"
        for letter, number in self.sorted_list:
            if wexp >= number:
                current_letter = letter
            else:
                break
        return current_letter

    def get_item_requirement(self, lvl):
        if lvl in self.wexp_dict:
            return self.wexp_dict[lvl]
        else:
            return 0

    def get_rank_bonus(self, wexp):
        if wexp <= 0: 
            return (0, 0, 0)
        return self.rank_bonuses[self.number_to_letter(wexp)]

    # Returns a float between 0 and 1 desribing how closes number is to next tier from previous tier
    def percentage(self, wexp):
        current_percentage = 0.0
        # print(wexp, self.sorted_list)
        for index, (letter, number) in enumerate(self.sorted_list):
            if index + 1 >= len(self.sorted_list):
                current_percentage = 1.0
                break
            elif wexp >= number:
                difference = float(self.sorted_list[index+1][1] - number)
                if wexp - number >= difference:
                    continue
                current_percentage = (wexp - number)/difference
                # print('WEXP', wexp, number, difference, current_percentage)
                break
        return current_percentage

class Icon(object):
    def __init__(self, name=None, idx=None, grey=False):
        if name:
            self.name = name
            self.idx = TRIANGLE.name_to_index.get(self.name, 0)
        else:
            self.name = None
            self.idx = idx
        self.set_grey(grey)

    def set_grey(self, grey):
        self.grey = grey
        self.create_image()

    def create_image(self):
        # Weapon Icons Pictures
        if self.grey:
            weaponIcons = GC.ITEMDICT['Gray_Wexp_Icons']
        else:
            weaponIcons = GC.ITEMDICT['Wexp_Icons']
        if self.idx * 16 + 16 > weaponIcons.get_height():
            # You have a problem
            self.image = Engine.subsurface(weaponIcons, (0, 0, 16, 16))
        else:
            self.image = Engine.subsurface(weaponIcons, (0, 16*self.idx, 16, 16))

    def draw(self, surf, topleft, cooldown=False):
        surf.blit(self.image, topleft)

TRIANGLE = Weapon_Triangle(Engine.engine_constants['home'] + "Data/weapon_triangle.txt")
EXP = Weapon_Exp(Engine.engine_constants['home'] + "Data/weapon_exp.txt")
ADVANTAGE = Weapon_Advantage(Engine.engine_constants['home'] + 'Data/weapon_advantage.txt')
