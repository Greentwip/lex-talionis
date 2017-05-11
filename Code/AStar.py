# A* implementation
import heapq
from GlobalConstants import *
from configuration import *

class Node(object):
    def __init__(self, x, y, reachable, cost):
        """
        Initialize new cell
        x - node's x coordinate
        y - node's y coordinate
        reachable - is cell reachable? not a wall?
        cost - How many movement points to reach
        """
        self.reachable = reachable
        self.cost = cost
        self.x = x
        self.y = y
        self.reset()

    def reset(self):
        # Malleable properties
        self.parent = None
        self.g = 0
        self.h = 0
        self.f = 0

    def __repr__(self):
        return str(self.x) + ',' + str(self.y) + ' ; ' + str(self.reachable) + ' ' + str(self.cost)

class Grid_Manager(object):
    def __init__(self, tilemap):
        self.gridHeight = tilemap.height
        self.gridWidth = tilemap.width
        self.grids = {}

        for num in range(len(MCOSTDATA['Normal'])):
            self.grids[num] = self.init_grid(num, tilemap) # For each movement type

        self.unit_map = self.init_unit_map()

    def init_unit_map(self):
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                cells.append(None)
        return cells

    def set_unit_node(self, pos, team):
        self.unit_map[pos[0] * self.gridHeight + pos[1]] = team

    def get_unit_node(self, pos):
        return self.unit_map[pos[0] * self.gridHeight + pos[1]]

    def get_grid(self, unit):
        if unit.has_flying():
            return self.grids[CONSTANTS['flying_mcost_column']]
        elif unit.has_fleet_of_foot():
            return self.grids[CONSTANTS['fleet_mcost_column']]
        else:
            return self.grids[unit.movement_group]

    def init_grid(self, mode, tilemap):
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                tile = tilemap.tiles[(x,y)]
                tile_cost = tile.get_mcost(mode)
                cells.append(Node(x, y, mode != 99, tile.get_mcost(mode)))
        return cells

    def update_tile(self, tile):
        x = tile.position[0]
        y = tile.position[1]
        for num in range(len(MCOSTDATA['Normal'])):
            cost = tile.get_mcost(num)
            self.grids[num][x * self.gridHeight + y] = Node(x, y, cost != 99, cost)

    def draw_grid(self, grid_name):
        for y in range(self.gridHeight):
            for x in range(self.gridWidth):
                cell = self.grids[grid_name][x * self.gridHeight + y]
                if cell.reachable:
                    print(str(cell.cost) + ' '),
                else:
                    print('- '),
            print('\n'),

class AStar(object):
    def __init__(self, gameStateObj, startposition, goalposition, grid, unit):
        self.cells = grid
        self.gridHeight = gameStateObj.map.height
        self.gridWidth = gameStateObj.map.width
        self.startposition = startposition
        self.goalposition = goalposition
        self.start = self.get_cell(self.startposition)
        self.end = self.get_cell(self.goalposition) if self.goalposition else None
        self.adj_end = self.get_adjacent_cells(self.end) if self.end else None
        self.unit = unit
        self.reset()

    def reset_grid(self):
        for cell in self.cells:
            cell.reset()

    def reset(self):
        self.open = []
        heapq.heapify(self.open)
        self.closed = set()
        self.path = []
        self.reset_grid()

    def set_goal_pos(self, goal_pos):
        self.goalposition = goal_pos
        self.end = self.get_cell(self.goalposition)
        self.adj_end = self.get_adjacent_cells(self.end)

    def get_heuristic(self, cell):
        """Compute the heuristic for this cell, h
        h is approximate distance between this cell and the ending cell"""
        # Get main heuristic
        dx1 = cell.x - self.end.x
        dy1 = cell.y - self.end.y
        h = abs(dx1) + abs(dy1)
        # Are we going in direction of goal? -
        # Slight nudge in direction that lies along path from start to end
        dx2 = self.start.x - self.end.x
        dy2 = self.start.y - self.end.y
        cross = abs(dx1 * dy2 - dx2 * dy1)
        return h + cross*.001

    def get_cell(self, (x, y)):
        return self.cells[x * self.gridHeight + y]

    def get_adjacent_cells(self, cell):
        """
        Returns adjacent cells to a cell. Clockwise starting from the one on
        the right"""
        cells = []
        if cell.x < self.gridWidth-1:
            cells.append(self.get_cell((cell.x+1, cell.y)))
        if cell.y > 0:
            cells.append(self.get_cell((cell.x, cell.y-1)))
        if cell.x > 0:
            cells.append(self.get_cell((cell.x-1, cell.y)))
        if cell.y < self.gridHeight-1:
            cells.append(self.get_cell((cell.x, cell.y+1)))
        return cells

    def update_cell(self, adj, cell, gameStateObj):
        # h is approximate distance between this cell and end goal
        # g is true distance between this cell and starting position
        # f is simply them added together. # c.x, c.y or cell.x, cell.y
        adj.g = cell.g + adj.cost
        adj.h = self.get_heuristic(adj)
        adj.parent = cell
        adj.f = adj.h + adj.g

    def return_path(self, cell):
        path = []
        while cell:
            path.append((cell.x, cell.y))
            cell = cell.parent
        return path
        
    def process(self, gameStateObj, adj_good_enough=False, ally_block=False, limit=None):
        # add starting cell to open heap queue
        heapq.heappush(self.open, (self.start.f, self.start))
        while len(self.open):
            # pop cell from heap queue
            f, cell = heapq.heappop(self.open)
            # add cell to closed set so we don't process it twice
            self.closed.add(cell)
            # If this cell is past the limit, just return None. No valid path
            # Uses f, not g, because g will cut off if first greedy path fails
            # f only cuts off if all cells are bad
            if limit and cell.f > limit:
                break
            # if ending cell, display found path
            if cell is self.end or (adj_good_enough and cell in self.adj_end):
                self.path = self.return_path(cell)
                break
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for c in adj_cells:
                unit_team = gameStateObj.grid_manager.get_unit_node((c.x, c.y))
                if c.reachable and c not in self.closed and \
                    (not unit_team or (not ally_block and gameStateObj.compare_teams(self.unit.team, unit_team)) or self.unit.has_pass()):
                    if (c.f, c) in self.open:
                        # if adj cell in open list, check if current path is
                        # better than the one previously found for this adj
                        # cell.
                        if c.g > cell.g + c.cost:
                            self.update_cell(c, cell, gameStateObj)
                            heapq.heappush(self.open, (c.f, c))
                    else:
                        self.update_cell(c, cell, gameStateObj)
                        # Add adj cell to open list
                        heapq.heappush(self.open, (c.f, c))

# THIS ACTUALLY WORKS!!!
class Djikstra(object):
    def __init__(self, gameStateObj, startposition, grid, unit):
        self.open = []
        heapq.heapify(self.open)
        self.closed = set()
        self.cells = grid # Must keep order.
        self.gridHeight = gameStateObj.map.height
        self.gridWidth = gameStateObj.map.width
        self.reset_grid()
        self.startposition = startposition
        self.start = self.get_cell(self.startposition)
        self.unit = unit

    def get_cell(self, (x, y)):
        return self.cells[x * self.gridHeight + y]

    def reset_grid(self):
        for cell in self.cells:
            cell.reset()

    def get_adjacent_cells(self, cell):
        """
        Returns adjacent cells to a cell. Clockwise starting from the one on
        the right"""
        cells = []
        if cell.x < self.gridWidth-1:
            cells.append(self.get_cell((cell.x+1, cell.y)))
        if cell.y > 0:
            cells.append(self.get_cell((cell.x, cell.y-1)))
        if cell.x > 0:
            cells.append(self.get_cell((cell.x-1, cell.y)))
        if cell.y < self.gridHeight-1:
            cells.append(self.get_cell((cell.x, cell.y+1)))
        return cells

    def update_cell(self, adj, cell, gameStateObj):
        # g is true distance between this cell and starting position
        adj.g = cell.g + adj.cost
        adj.parent = cell
        
    def process(self, gameStateObj, movement_left):
        # add starting cell to open heap queue
        heapq.heappush(self.open, (self.start.g, self.start))
        while len(self.open):
            # pop cell from heap queue
            g, cell = heapq.heappop(self.open)
            if g > movement_left:
                return {(node.x, node.y) for node in self.closed}
            # add cell to closed set so we don't process it twice
            self.closed.add(cell)
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for c in adj_cells:
                unit_team = gameStateObj.grid_manager.get_unit_node((c.x, c.y))
                if c.reachable and c not in self.closed and \
                    (not unit_team or gameStateObj.compare_teams(self.unit.team, unit_team) or self.unit.has_pass()):
                    if (c.g, c) in self.open:
                        # if adj cell in open list, check if current path is
                        # better than the one previously found for this adj
                        # cell.
                        if c.g > cell.g + c.cost:
                            self.update_cell(c, cell, gameStateObj)
                            heapq.heappush(self.open, (c.g, c))
                    else:
                        self.update_cell(c, cell, gameStateObj)
                        # Add adj cell to open list
                        heapq.heappush(self.open, (c.g, c))
        # Sometimes gets here if unit is enclosed.
        return {(node.x, node.y) for node in self.closed}