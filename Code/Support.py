import os

from . import GlobalConstants as GC
from . import configuration as cf
from . import Action, Engine, Utility

class Affinity(object):
    def __init__(self, icon_index, name, attack, defense, accuracy, avoid, crit, dodge, attackspeed):
        self.icon = Engine.subsurface(GC.ITEMDICT['Affinity'], (0, 16*icon_index, 16, 16))
        self.name = name
        self.attack = attack
        self.defense = defense
        self.accuracy = accuracy
        self.avoid = avoid
        self.crit = crit
        self.dodge = dodge
        self.attackspeed = attackspeed

        self.desc = self.create_desc()

    def draw(self, surf, topleft):
        surf.blit(self.icon, topleft)

    def create_desc(self):
        stats = [self.attack, self.defense, self.accuracy, self.avoid, self.crit, self.dodge, self.attackspeed]
        names = ["Damage", "Defense", "Hit", "Avoid", "Crit", "Crit Evade", "Attack Speed"]

        desc_parts = []
        for stat, name in zip(stats, names):
            if stat == 0:
                continue
            if stat.is_integer():
                s = "%d %s" % (stat, name)
            else:
                s = "%.1f %s" % (stat, name)
            if stat > 0:
                s = "+" + s
            desc_parts.append(s)
        if len(desc_parts) == 0:
            return "No bonus"
        elif len(desc_parts) == 1:
            return desc_parts[0] + " per support level"
        elif len(desc_parts) == 2:
            return desc_parts[0] + " and " + desc_parts[1] + " per support level"
        elif len(desc_parts) > 2:
            return ", ".join(desc_parts[:-1]) + ", and " + desc_parts[-1] + " per support level"

    def get_bonus(self):
        return [self.attack, self.defense, self.accuracy, self.avoid, self.crit, self.dodge, self.attackspeed]

# Support Graph
class Support_Node(object):
    def __init__(self, name, affinity):
        self.name = name
        self.affinity = AFFINITY_DICT[affinity]
        self.adjacent = {}
        # self.paired_with = None
        self.dead = False

    def add_neighbor(self, neighbor, edge):
        self.adjacent[neighbor.name] = edge

    def get_total_support_level(self):
        return sum(edge.support_level for edge in self.adjacent.values())

    def get_num_s_supports(self):
        return sum(edge.support_level >= 4 for edge in self.adjacent.values())

class Support_Edge(object):
    def __init__(self, support_limits, script_loc):
        self.support_limits = [int(x) for x in support_limits]
        self.current_value = 0
        self.support_level = 0
        self.script = script_loc
        self.reset()

    def reset(self):
        self.support_levels_this_chapter = 0
        self.value_added_this_chapter = 0

    def increment(self, value):
        # If I've reached the point that I could support again, but I've already supported this chapter, then I stop increment value
        if self.support_level < self.available_support_level() and self.support_levels_this_chapter > 0:
            return
        self.current_value += value
        self.value_added_this_chapter += value

    def increment_support_level(self):
        self.support_level += 1
        self.support_levels_this_chapter += 1

    def available_support_level(self):
        current_value = self.current_value
        for idx, support in enumerate(self.support_limits):
            current_value -= support
            if current_value < 0:
                return idx
        return len(self.support_limits)

    def can_support(self) -> bool:
        if self.support_level < self.available_support_level():
            if self.support_levels_this_chapter == 0:
                return True
            elif self.support_limits[self.support_level] == 0:
                return True
        return False

    def get_support_level(self):
        return self.support_level

class Support_Graph(object):
    def __init__(self, node_fp, edge_fp):
        self.node_dict = {}
        self.read_fp(node_fp, edge_fp)

    def read_fp(self, node_fp, edge_fp):
        with open(node_fp, mode='r', encoding='utf-8') as node_data:
            for line in node_data.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # print(line)
                name, affinity = line.split(';')
                self.add_node(name, affinity)

        with open(edge_fp, mode='r', encoding='utf-8') as edge_data:
            lines = [l.strip() for l in edge_data.readlines() if l.strip() and not l.startswith('#')]
            for line in lines:
                # print(line)
                s_l = line.split(';')
                frm, to = s_l[:2]
                support_limits = s_l[2:]
                script_loc = 'Data/SupportConvos/' + frm + to + '.txt'
                self.add_edge(frm, to, support_limits, script_loc)

    def add_node(self, name, affinity):
        self.node_dict[name] = Support_Node(name, affinity)

    def get_node(self, name):
        if name in self.node_dict:
            return self.node_dict[name]
        else:
            return None

    def add_edge(self, frm, to, support_limits, script_loc):
        edge = Support_Edge(support_limits, script_loc)
        self.node_dict[frm].add_neighbor(self.node_dict[to], edge)
        self.node_dict[to].add_neighbor(self.node_dict[frm], edge)

    def get_edge(self, frm, to):
        if frm in self.node_dict and to in self.node_dict[frm].adjacent:
            return self.node_dict[frm].adjacent[to]

    def get_adjacent(self, unit_id):
        if unit_id in self.node_dict:
            node = self.node_dict[unit_id]
            return list(node.adjacent.keys())
        else:
            return []

    def can_support(self, unit_id, other_id):
        if self.check_max_support_limit(unit_id, other_id):
            edge = self.get_edge(unit_id, other_id)
            if edge and edge.can_support() and self.check_s_support(unit_id, other_id):
                return True
        return False

    def check_max_support_limit(self, unit_id, other_id):
        if unit_id not in self.node_dict or other_id not in self.node_dict:
            return False
        return not cf.CONSTANTS['support_limit'] or (self.node_dict[unit_id].get_total_support_level() < cf.CONSTANTS['support_limit'] and 
                                                     self.node_dict[other_id].get_total_support_level() < cf.CONSTANTS['support_limit'])

    def check_s_support(self, unit_id, other_id):
        if unit_id not in self.node_dict or other_id not in self.node_dict:
            return False
        return not cf.CONSTANTS['support_s_limit'] or (self.node_dict[unit_id].get_num_s_supports() < cf.CONSTANTS['support_s_limit'] and 
                                                       self.node_dict[other_id].get_num_s_supports() < cf.CONSTANTS['support_s_limit'])

    def get_supports(self, unit_id):
        """
        # Returns a list of 3-tuples representing the current supports of a name
        # These values are the name, the affinity, and the current support level
        """
        supports = []
        if unit_id in self.node_dict:
            node = self.node_dict[unit_id]
            for name, edge in node.adjacent.items():
                support_level = edge.get_support_level()
                affinity = self.node_dict[name].affinity
                supports.append((name, affinity, support_level))
        return supports

    def get_affinity_bonuses(self, unit, other):
        if not cf.CONSTANTS['support_range'] or Utility.calculate_distance(unit.position, other.position) <= cf.CONSTANTS['support_range']:
            support_level = self.node_dict[unit.id].adjacent[other.id].get_support_level()
            if cf.CONSTANTS['support_bonus'] == 0:
                return [0] * 7
            elif cf.CONSTANTS['support_bonus'] == 1:
                return [int(b * support_level) for b in self.node_dict[unit.id].affinity.get_bonus()]
            elif cf.CONSTANTS['support_bonus'] == 2:
                return [int(b * support_level) for b in self.node_dict[other.id].affinity.get_bonus()]
            elif cf.CONSTANTS['support_bonus'] == 3:
                bonus1 = self.node_dict[unit.id].affinity.get_bonus()
                bonus2 = self.node_dict[other.id].affinity.get_bonus()
                return [int((a + b) * support_level / 2) for a, b in zip(bonus1, bonus2)]
            elif cf.CONSTANTS['support_bonus'] == 4:
                bonus1 = self.node_dict[unit.id].affinity.get_bonus()
                bonus2 = self.node_dict[other.id].affinity.get_bonus()
                return [int((a + b) * support_level) for a, b in zip(bonus1, bonus2)]
        else:
            return [0] * 7

    def _end_general(self, unit, gameStateObj, gain):
        if unit.id not in self.node_dict:
            return
        node = self.node_dict[unit.id]
        other_ids = {u.id for u in gameStateObj.allunits if u is not unit and u.position and not u.dead and
                     u.id in self.node_dict and unit.checkIfAlly(u) and
                     Utility.calculate_distance(unit.position, u.position) <= cf.CONSTANTS['support_growth_range']}
        for other_id, edge in node.adjacent.items():
            if other_id in other_ids:
                Action.do(Action.SupportGain(unit.id, other_id, gain), gameStateObj)
                
    def end_turn(self, gameStateObj):
        for unit in gameStateObj.allunits:
            if unit.position and unit.team == 'player':
                self._end_general(unit, gameStateObj, cf.CONSTANTS['support_end_turn'])

    def end_combat(self, unit, gameStateObj):
        self._end_general(unit, gameStateObj, cf.CONSTANTS['support_combat'])

    def check_interact(self, unit, units, gameStateObj):
        if unit.id not in self.node_dict:
            return
        node = self.node_dict[unit.id]
        other_ids = {u.id for u in units if u is not unit and unit.checkIfAlly(u) and 
                     u.id in self.node_dict}
        for other_id, edge in node.adjacent.items():
            if other_id in other_ids:
                Action.do(Action.SupportGain(unit.id, other_id, cf.CONSTANTS['support_interact']), gameStateObj)
                # edge.increment(cf.CONSTANTS['support_interact'])

    def serialize(self):
        serial_dict = {}
        for name1, node in self.node_dict.items():
            serial_dict[name1] = {}
            for name2, edge in node.adjacent.items():
                serial_dict[name1][name2] = (edge.current_value, edge.support_level,
                                             edge.support_levels_this_chapter,
                                             edge.value_added_this_chapter)
        return serial_dict

    def deserialize(self, serial_dict):
        for name1, names in serial_dict.items():
            for name2, value in names.items():
                current_value, support_level, support_levels_this_chapter, value_added_this_chapter = value
                edge = self.node_dict[name1].adjacent[name2]
                edge.current_value = current_value
                edge.support_level = support_level
                edge.support_levels_this_chapter = support_levels_this_chapter
                edge.value_added_this_chapter = value_added_this_chapter

def create_affinity_dict(fn):
    d = {}
    with open(fn, mode='r', encoding='utf-8') as fp:
        lines = fp.readlines()

    counter = 0
    for line in lines:
        if line.startswith('#'):
            continue
        split_line = line.strip().split()
        name = split_line[0]
        damage = float(split_line[1])
        resist = float(split_line[2])
        accuracy = float(split_line[3])
        avoid = float(split_line[4])
        crit = float(split_line[5])
        dodge = float(split_line[6])
        attackspeed = float(split_line[7])
        d[name] = Affinity(counter, name, damage, resist, accuracy, avoid, crit, dodge, attackspeed)
        counter += 1

    return d

if os.path.exists('Data/affinity.txt'):
    AFFINITY_DICT = create_affinity_dict('Data/affinity.txt')
else:
    AFFINITY_DICT = {}
