# fast_pathfinding.pyx
# cython
import heapq
import GlobalConstants as GC
import configuration as cf

cdef bint compare_teams(str team1, str team2):
    # Returns True if allies, false if enemies
    if team1 == team2:
        return True
    elif (team1 == 'player' and team2 == 'other') or (team2 == 'player' and team1 == 'other'):
        return True
    return False

cdef class Node:
    cdef public bint reachable
    cdef public int cost
    cdef public int x
    cdef public int y
    cdef public Node parent
    cdef public int g
    cdef public float h
    cdef public float f

    def __init__(self, int x, int y, bint reachable, int cost):
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

    cpdef int reset(self):
        # Malleable properties
        self.parent = None
        self.g = 0
        self.h = 0
        self.f = 0

    def __gt__(self, n):
        return self.cost > n

    def __lt__(self, n):
        return self.cost < n

    def __hash__(self):
        return hash(str(id(self)))

class Grid_Manager(object):
    __slots__ = ['gridHeight', 'gridWidth', 'grids', 'team_map', 'unit_map', 'aura_map', 'known_auras']
    def __init__(self, tilemap):
        self.gridHeight = tilemap.height
        self.gridWidth = tilemap.width
        self.grids = {} # Dictionary

        cdef int num
        for num in range(len(GC.MCOSTDATA['Normal'])):
            self.grids[num] = self.init_grid(num, tilemap) # For each movement type

        self.team_map = self.init_unit_map()
        self.unit_map = self.init_unit_map()
        self.aura_map = self.init_aura_map()
        self.known_auras = {} # Key: Aura, Value: Set of positions

    def init_unit_map(self):
        cdef int x, y
        cdef list cells
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                cells.append(None)
        return cells

    def init_aura_map(self):
        cdef int x, y
        cdef list cells
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                cells.append(set())
        return cells

    def set_unit_node(self, tuple pos, unit):
        cdef int idx
        idx = pos[0] * self.gridHeight + pos[1]
        self.unit_map[idx] = unit
        if unit:
            self.team_map[idx] = unit.team
        else:
            self.team_map[idx] = None

    def get_unit_node(self, pos):
        return self.unit_map[pos[0] * self.gridHeight + pos[1]]

    def get_team_node(self, pos):
        return self.team_map[pos[0] * self.gridHeight + pos[1]]

    # === For Auras ===
    def reset_aura(self, aura):
        self.known_auras[aura] = set()

    def add_aura_node(self, tuple pos, aura):
        self.aura_map[pos[0] * self.gridHeight + pos[1]].add(aura)
        self.known_auras[aura].add(pos)

    def remove_aura_node(self, tuple pos, aura):
        self.aura_map[pos[0] * self.gridHeight + pos[1]].discard(aura)

    def get_aura_positions(self, aura):
        return self.known_auras[aura]

    def get_aura_node(self, pos):
        return self.aura_map[pos[0] * self.gridHeight + pos[1]]

    # === For Movement ===
    def get_grid(self, unit):
        if 'flying' in unit.status_bundle:
            return self.grids[cf.CONSTANTS['flying_mcost_column']]
        elif 'fleet_of_foot' in unit.status_bundle:
            return self.grids[cf.CONSTANTS['fleet_mcost_column']]
        else:
            return self.grids[unit.movement_group]

    def init_grid(self, mode, tilemap):
        cdef int x, y, tile_cost
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                tile = tilemap.tiles[(x,y)]
                tile_cost = tile.get_mcost(mode)
                cells.append(Node(x, y, tile_cost != 99, tile_cost))
        return cells

    def update_tile(self, tile):
        cdef int x, y, num, cost
        x = tile.position[0]
        y = tile.position[1]
        for num in range(len(GC.MCOSTDATA['Normal'])):
            cost = tile.get_mcost(num)
            self.grids[num][x * self.gridHeight + y] = Node(x, y, cost != 99, cost)

    def draw_grid(self, str grid_name):
        cdef int x, y
        for y in range(self.gridHeight):
            for x in range(self.gridWidth):
                cell = self.grids[grid_name][x * self.gridHeight + y]
                if cell.reachable:
                    print(str(cell.cost) + ' '),
                else:
                    print('- '),
            print('\n'),

class AStar(object):
    def __init__(self, startposition, goalposition, grid, int width, int height, str unit_team, bint pass_through):
        self.cells = grid
        self.gridHeight = height
        self.gridWidth = width
        self.startposition = startposition
        self.goalposition = goalposition
        self.start = self.get_cell(self.startposition[0], self.startposition[1])
        self.end = self.get_cell(self.goalposition[0], self.goalposition[1]) if self.goalposition else None
        self.adj_end = self.get_adjacent_cells(self.end) if self.end else None
        self.unit_team = unit_team
        self.pass_through = pass_through
        self.reset()

    def reset_grid(self):
        cdef Node cell
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
        self.end = self.get_cell(self.goalposition[0], self.goalposition[1])
        self.adj_end = self.get_adjacent_cells(self.end)

    def get_heuristic(self, Node cell):
        """Compute the heuristic for this cell, h
        h is approximate distance between this cell and the ending cell"""
        # Get main heuristic
        cdef int dx1, dy1, h, dx2, dy2, cross
        dx1 = cell.x - self.end.x
        dy1 = cell.y - self.end.y
        h = abs(dx1) + abs(dy1)
        # Are we going in direction of goal? -
        # Slight nudge in direction that lies along path from start to end
        dx2 = self.start.x - self.end.x
        dy2 = self.start.y - self.end.y
        cross = abs(dx1 * dy2 - dx2 * dy1)
        return h + cross*.001

    def get_cell(self, int x, int y):
        return self.cells[x * self.gridHeight + y]

    def get_adjacent_cells(self, Node cell):
        """
        Returns adjacent cells to a cell. Clockwise starting from the one on
        the right"""
        cells = []
        if cell.x < self.gridWidth-1:
            cells.append(self.get_cell(cell.x+1, cell.y))
        if cell.y > 0:
            cells.append(self.get_cell(cell.x, cell.y-1))
        if cell.x > 0:
            cells.append(self.get_cell(cell.x-1, cell.y))
        if cell.y < self.gridHeight-1:
            cells.append(self.get_cell(cell.x, cell.y+1))
        return cells

    def update_cell(self, Node adj, Node cell):
        # h is approximate distance between this cell and end goal
        # g is true distance between this cell and starting position
        # f is simply them added together. # c.x, c.y or cell.x, cell.y
        adj.g = cell.g + adj.cost
        adj.h = self.get_heuristic(adj)
        adj.parent = cell
        adj.f = adj.h + adj.g

    def return_path(self, Node cell):
        path = []
        while cell:
            path.append((cell.x, cell.y))
            cell = cell.parent
        return path
        
    def process(self, gameStateObj, bint adj_good_enough=False, bint ally_block=False, limit=None):
        cdef float f
        cdef Node cell
        cdef list adj_cells
        # add starting cell to open heap queue
        heapq.heappush(self.open, (self.start.f, self.start))
        while self.open:
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
                if c.reachable and c not in self.closed:
                    unit_team = gameStateObj.grid_manager.get_team_node((c.x, c.y))
                    if not unit_team or (not ally_block and compare_teams(self.unit_team, unit_team)) or self.pass_through:
                        if (c.f, c) in self.open:
                            # if adj cell in open list, check if current path is
                            # better than the one previously found for this adj
                            # cell.
                            if c.g > cell.g + c.cost:
                                self.update_cell(c, cell)
                                heapq.heappush(self.open, (c.f, c))
                        else:
                            self.update_cell(c, cell)
                            # Add adj cell to open list
                            heapq.heappush(self.open, (c.f, c))

# THIS ACTUALLY WORKS!!!
cdef class Djikstra:
    cdef list open
    cdef set closed
    cdef list cells
    cdef int gridWidth
    cdef int gridHeight
    cdef tuple startposition
    cdef Node start
    cdef str unit_team
    cdef bint pass_through

    def __init__(self, tuple startposition, list grid, int grid_width, int grid_height, str unit_team, bint pass_through):
        self.open = []
        heapq.heapify(self.open)
        self.closed = set()
        self.cells = grid # Must keep order.
        self.gridHeight = grid_height
        self.gridWidth = grid_width
        self.reset_grid()
        self.startposition = startposition
        self.start = self.get_cell(self.startposition[0], self.startposition[1])
        self.unit_team = unit_team
        self.pass_through = pass_through

    cdef Node get_cell(self, int x, int y):
        return self.cells[x * self.gridHeight + y]

    cdef void reset_grid(self):
        cdef Node cell
        for cell in self.cells:
            cell.reset()

    cdef list get_adjacent_cells(self, Node cell):
        """
        Returns adjacent cells to a cell. Clockwise starting from the one on
        the right"""
        cells = []
        if cell.x < self.gridWidth-1:
            cells.append(self.get_cell(cell.x+1, cell.y))
        if cell.y > 0:
            cells.append(self.get_cell(cell.x, cell.y-1))
        if cell.x > 0:
            cells.append(self.get_cell(cell.x-1, cell.y))
        if cell.y < self.gridHeight-1:
            cells.append(self.get_cell(cell.x, cell.y+1))
        return cells

    cdef void update_cell(self, Node adj, Node cell):
        # g is true distance between this cell and starting position
        adj.g = cell.g + adj.cost
        adj.parent = cell
        
    cpdef set process(self, list team_map, int movement_left):
        cdef int g
        cdef Node cell
        cdef list adj_cells
        # add starting cell to open heap queue
        heapq.heappush(self.open, (self.start.g, self.start))
        while self.open:
            # pop cell from heap queue
            g, cell = heapq.heappop(self.open)
            if g > movement_left:
                return {(node.x, node.y) for node in self.closed}
            # add cell to closed set so we don't process it twice
            self.closed.add(cell)
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for c in adj_cells:
                if c.reachable and c not in self.closed:
                    unit_team = team_map[c.x * self.gridHeight + c.y]
                    if not unit_team or compare_teams(self.unit_team, unit_team) or self.pass_through:
                        if (c.g, c) in self.open:
                            # if adj cell in open list, check if current path is
                            # better than the one previously found for this adj
                            # cell.
                            if c.g > cell.g + c.cost:
                                self.update_cell(c, cell)
                                heapq.heappush(self.open, (c.g, c))
                        else:
                            self.update_cell(c, cell)
                            # Add adj cell to open list
                            heapq.heappush(self.open, (c.g, c))
        # Sometimes gets here if unit is enclosed.
        return {(node.x, node.y) for node in self.closed}
