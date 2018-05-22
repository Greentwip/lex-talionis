import GlobalConstants as GC
import configuration as cf
import Engine

class Affinity(object):
    def __init__(self, name, attack, defense, accuracy, avoid, index, desc):
        self.name = name
        self.attack = attack
        self.defense = defense
        self.accuracy = accuracy
        self.avoid = avoid
        self.index = index
        self.desc = desc

    def draw(self, surf, topleft):
        image = Engine.subsurface(GC.ITEMDICT['Affinity'], (0, 16*self.index, 16, 16))
        surf.blit(image, topleft)

AFFINITY_DICT = {'Light': Affinity('Light', 0, 1, 1, 0, 6, "+1 Defense and +5 Hit per support level."),
                 'Dark': Affinity('Dark', 1, 0, 0, 1, 1, "+1 Attack Damage and +5 Avoid per support level."),
                 'Earth': Affinity('Earth', 1, 1, 0, 0, 3, "+1 Attack Damage and +1 Defense per support level."),
                 'Wind': Affinity('Wind', 0, 0, 1, 1, 7, "+5 Hit and +5 Avoid per support level."),
                 'Water': Affinity('Water', 0, 1, 0, 1, 5, "+1 Defense and +1 Avoid per support level."),
                 'Fire': Affinity('Fire', 1, 0, 1, 0, 4, "+1 Attack Damage and +5 Hit per support level.")}
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
    def __init__(self, start, inc, limit, script_loc):
        self.current_value = start
        self.increment = inc
        self.limit = limit
        self.script = script_loc

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
                frm, to, start, inc, limit = line.split(';')
                script_loc = 'Data/SupportConvos/' + frm + to + '.txt'
                self.add_edge(frm, to, int(start), int(inc), int(limit), script_loc)

    def add_node(self, name, affinity):
        self.node_dict[name] = Support_Node(name, affinity)

    def get_node(self, name):
        if name in self.node_dict:
            return self.node_dict[name]
        else:
            return None

    def add_edge(self, frm, to, start, inc, limit, script_loc):
        edge = Support_Edge(start, inc, limit, script_loc)
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

    def get_supports(self, unit_name):
        """
        # Returns a list of 3-tuples representing the current supports of a name
        # These values are the name, the affinity, and the current support level
        """
        supports = []
        if unit_name in self.node_dict:
            node = self.node_dict[unit_name]
            for name, edge in node.adjacent.iteritems():
                support_level = edge.current_value//cf.CONSTANTS['support_points']
                affinity = self.node_dict[name].affinity
                supports.append((name, affinity, support_level))
        return supports

    def serialize(self):
        serial_dict = {}
        for name1, node in self.node_dict.iteritems():
            serial_dict[name1] = {}
            for name2, edge in node.adjacent.iteritems():
                serial_dict[name1][name2] = edge.current_value
        return serial_dict

    def deserialize(self, serial_dict):
        for name1, names in serial_dict.iteritems():
            for name2, value in names.iteritems():
                self.node_dict[name1].adjacent[name2].current_value = value
