try:
    import GlobalConstants as GC
    import configuration as cf
    import Engine, Utility
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import Engine, Utility

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

        l = []
        for stat, name in zip(stats, names):
            s = "%d %s" % (stat, name)
            if stat >= 0:
                s = "+" + s
            l.append(s)
        if len(l) == 0:
            return "No bonus"
        elif len(l) == 1:
            return l[0] + " per support level"
        elif len(l) == 2:
            return l[0] + " and " + l[1] + " per support level"
        elif len(1) > 2:
            return ", ".join(l[:-1]) + ", and " + l[-1] + " per support level"

    def get_bonus(self):
        return [self.attack, self.defense, self.accuracy, self.avoid, self.crit, self.dodge, self.attackspeed]

# Support Graph
class Support_Node(object):
    def __init__(self, name, affinity):
        self.name = name
        self.affinity = AFFINITY_DICT[affinity]
        self.adjacent = {}
        self.paired_with = None
        self.dead = False

    def add_neighbor(self, neighbor, edge):
        self.adjacent[neighbor.name] = edge

class Support_Edge(object):
    def __init__(self, supports, script_loc):
        self.supports = [int(x) for x in supports]
        self.current_value = 0
        self.script = script_loc

    def get_support_level(self):
        current_value = self.current_value
        for idx, support in enumerate(self.supports):
            current_value -= support
            if current_value < 0:
                return idx
        return len(self.supports)

class Support_Graph(object):
    def __init__(self, node_fp, edge_fp):
        self.node_dict = {}
        self.read_fp(node_fp, edge_fp)

    def read_fp(self, node_fp, edge_fp):
        with open(node_fp, 'r') as node_data:
            for line in node_data.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # print(line)
                name, affinity = line.split(';')
                self.add_node(name, affinity)

        with open(edge_fp, 'r') as edge_data:
            for line in edge_data.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # print(line)
                s_l = line.split(';')
                frm, to = s_l[:2]
                supports = s_l[2:]
                script_loc = 'Data/SupportConvos/' + frm + to + '.txt'
                self.add_edge(frm, to, supports, script_loc)

    def add_node(self, name, affinity):
        self.node_dict[name] = Support_Node(name, affinity)

    def get_node(self, name):
        if name in self.node_dict:
            return self.node_dict[name]
        else:
            return None

    def add_edge(self, frm, to, supports, script_loc):
        edge = Support_Edge(supports, script_loc)
        self.node_dict[frm].add_neighbor(self.node_dict[to], edge)
        self.node_dict[to].add_neighbor(self.node_dict[frm], edge)

    def pair(self, name1, name2):
        name1_pair = self.node_dict[name1].paired_with
        name2_pair = self.node_dict[name2].paired_with
        if name1_pair:
            self.node_dict[name1_pair].paired_with = None
        if name2_pair:
            self.node_dict[name2_pair].paired_with = None
        self.node_dict[name1].paired_with = name2
        self.node_dict[name2].paired_with = name1

    def get_adjacent(self, unit_id):
        if unit_id in self.node_dict:
            node = self.node_dict[unit_id]
            return list(node.adjacent.keys())
        else:
            return []

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
                return [b * support_level for b in self.node_dict[unit.id].affinity.get_bonus()]
            elif cf.CONSTANTS['support_bonus'] == 2:
                return [b * support_level for b in self.node_dict[other.id].affinity.get_bonus()]
            elif cf.CONSTANTS['support_bonus'] == 3:
                bonus1 = self.node_dict[unit.id].affinity.get_bonus()
                bonus2 = self.node_dict[other.id].affinity.get_bonus()
                return [(a + b) * support_level / 2 for a, b in zip(bonus1, bonus2)]
            elif cf.CONSTANTS['support_bonus'] == 4:
                bonus1 = self.node_dict[unit.id].affinity.get_bonus()
                bonus2 = self.node_dict[other.id].affinity.get_bonus()
                return [(a + b) * support_level for a, b in zip(bonus1, bonus2)]
        else:
            return [0] * 7

    def serialize(self):
        serial_dict = {}
        for name1, node in self.node_dict.items():
            serial_dict[name1] = {}
            for name2, edge in node.adjacent.items():
                serial_dict[name1][name2] = edge.current_value
        return serial_dict

    def deserialize(self, serial_dict):
        for name1, names in serial_dict.items():
            for name2, value in names.items():
                self.node_dict[name1].adjacent[name2].current_value = value

def create_affinity_dict(fn):
    d = {}
    with open(fn) as fp:
        lines = fp.readlines()

    for index, line in enumerate(lines):
        if line.startswith('#'):
            continue
        split_line = line.strip().split()
        name = split_line[0]
        damage = int(split_line[1])
        resist = int(split_line[2])
        accuracy = int(split_line[3])
        avoid = int(split_line[4])
        crit = int(split_line[5])
        dodge = int(split_line[6])
        attackspeed = int(split_line[7])
        d[name] = Affinity(index, name, damage, resist, accuracy, avoid, crit, dodge, attackspeed)

    return d

AFFINITY_DICT = create_affinity_dict('Data/affinity.txt')
