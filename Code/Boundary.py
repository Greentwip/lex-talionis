# from collections import Counter

from . import GlobalConstants as GC
from . import Utility, Engine

# === BOUNDARY MANAGER ============================================
class BoundaryInterface(object):
    fog_of_war_tile = GC.IMAGESDICT['FogOfWarTile1']

    def __init__(self, tilemap):
        self.types = {'attack': GC.IMAGESDICT['RedBoundary'],
                      'all_attack': GC.IMAGESDICT['PurpleBoundary'],
                      'spell': GC.IMAGESDICT['GreenBoundary'],
                      'all_spell': GC.IMAGESDICT['BlueBoundary']}
        self.gridHeight = tilemap.height
        self.gridWidth = tilemap.width
        self.grids = {'attack': self.init_grid(),
                      'spell': self.init_grid(),
                      'movement': self.init_grid()}
        self.dictionaries = {'attack': {},
                             'spell': {},
                             'movement': {}}
        self.order = ['all_spell', 'all_attack', 'spell', 'attack']

        self.draw_flag = False
        self.all_on_flag = False

        self.displaying_units = set()
        self.true_positions = {}  # Key: Unit ID, Value: Position

        self.surf = None

        # For FoW
        self.sight_dict = {}  # Key: Position, Value: Set of Unit IDs that can see that position
        self.sight_marker = {}  # Key: Unit ID, Value: Position
        self.fog_of_war_surf = None

    def init_grid(self):
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                cells.append(set())
        return cells

    def check_bounds(self, pos):
        if pos[0] >= 0 and pos[1] >= 0 and pos[0] < self.gridWidth and pos[1] < self.gridHeight:
            return True
        return False

    def toggle_unit(self, unit):
        if unit.id in self.displaying_units:
            self.displaying_units.discard(unit.id)
            unit.flickerRed = False
        else:
            self.displaying_units.add(unit.id)
            unit.flickerRed = True
        self.surf = None

    def reset_unit(self, unit):
        if unit.id in self.displaying_units:
            self.displaying_units.discard(unit.id)
            unit.flickerRed = False
            self.surf = None

    def _set(self, positions, kind, u_id):
        this_grid = self.grids[kind]
        self.dictionaries[kind][u_id] = set()
        for pos in positions:
            this_grid[pos[0] * self.gridHeight + pos[1]].add(u_id)
            self.dictionaries[kind][u_id].add(pos)
        # self.print_grid(kind)

    def clear(self, kind=False):
        if kind:
            kinds = [kind]
        else:
            kinds = list(self.grids)
        for k in kinds:
            for x in range(self.gridWidth):
                for y in range(self.gridHeight):
                    self.grids[k][x * self.gridHeight + y] = set()
        self.surf = None
        self.true_positions.clear()

        self.sight_dict.clear()
        self.fog_of_war_surf = None

    def _add_unit(self, unit, gameStateObj):
        ValidMoves = unit.getValidMoves(gameStateObj, force=True)
        ValidAttacks, ValidSpells = [], []
        if unit.getMainWeapon():
            ValidAttacks = unit.getExcessAttacks(gameStateObj, ValidMoves, boundary=True)
        if unit.getMainSpell():
            ValidSpells = unit.getExcessSpellAttacks(gameStateObj, ValidMoves, boundary=True)
        self._set(ValidAttacks, 'attack', unit.id)
        self._set(ValidSpells, 'spell', unit.id)
        # self._set(ValidMoves, 'movement', unit.id)
        area_of_influence = Utility.find_manhattan_spheres(range(1, unit.stats['MOV'] + 1), unit.position)
        area_of_influence = {pos for pos in area_of_influence if gameStateObj.map.check_bounds(pos)}
        self._set(area_of_influence, 'movement', unit.id)
        # print(unit.name, unit.position, unit.klass, unit.event_id)
        self.surf = None

    def _remove_unit(self, unit, gameStateObj):
        for kind, grid in self.grids.items():
            if unit.id in self.dictionaries[kind]:
                for (x, y) in self.dictionaries[kind][unit.id]:
                    grid[x * self.gridHeight + y].discard(unit.id)
        self.surf = None

    # Used for Fog of War
    def _add_ally(self, unit, position, gameStateObj):
        self.sight_marker[unit.id] = position
        can_see = unit.getSightRange(position, gameStateObj)
        for pos in can_see:
            if pos not in self.sight_dict:
                self.sight_dict[pos] = set()
            self.sight_dict[pos].add(unit.id)
        self.fog_of_war_surf = None

    def _remove_ally(self, unit, gameStateObj):
        self.sight_marker[unit.id] = None
        for pos in self.sight_dict:
            self.sight_dict[pos].discard(unit.id)
        self.fog_of_war_surf = None

    def update_ally(self, unit, gameStateObj, position=None):
        self._remove_ally(unit, gameStateObj)
        if position:
            self._add_ally(unit, position, gameStateObj)
        else:
            self._add_ally(unit, unit.position, gameStateObj)

    def has_vision_at(self, position) -> bool:
        if position in self.sight_dict:
            return len(self.sight_dict[position]) > 0
        return False
    # End Fog of War

    def leave(self, unit, gameStateObj):
        self.true_positions[unit.id] = None
        if unit.team.startswith('enemy'):
            self._remove_unit(unit, gameStateObj)
        # Update ranges of other units that might be affected by my leaving
        if unit.position:
            x, y = unit.position
            other_units = gameStateObj.get_unit_from_id(self.grids['movement'][x * self.gridHeight + y])
            # other_units = set()
            # for key, grid in self.grids.items():
            # What other units were affecting that position -- only enemies can affect position
            #    other_units |= gameStateObj.get_unit_from_id(grid[x * self.gridHeight + y])
            other_units = {other_unit for other_unit in other_units if not gameStateObj.compare_teams(unit.team, other_unit.team)} 
            for other_unit in other_units:
                self._remove_unit(other_unit, gameStateObj)
            for other_unit in other_units:
                if other_unit.position:
                    self._add_unit(other_unit, gameStateObj)

    def arrive(self, unit, gameStateObj):
        if unit.position:
            self.true_positions[unit.id] = unit.position
            if unit.team.startswith('enemy'):
                self._add_unit(unit, gameStateObj)

            # Update ranges of other units that might be affected by my arrival
            x, y = unit.position
            other_units = gameStateObj.get_unit_from_id(self.grids['movement'][x * self.gridHeight + y])
            # other_units = set()
            # for key, grid in self.grids.items():
            # What other units were affecting that position -- only enemies can affect position
            #    other_units |= gameStateObj.get_unit_from_id(grid[x * self.gridHeight + y])
            other_units = {other_unit for other_unit in other_units if not gameStateObj.compare_teams(unit.team, other_unit.team)} 
            # print([(other_unit.name, other_unit.position, other_unit.event_id, other_unit.klass, x, y) for other_unit in other_units])
            for other_unit in other_units:
                self._remove_unit(other_unit, gameStateObj)
            for other_unit in other_units:
                if other_unit.position:
                    self._add_unit(other_unit, gameStateObj)

    # Called when map changes
    def reset(self, gameStateObj):
        self.clear()
        for unit in gameStateObj.allunits:
            if unit.position:
                self.true_positions[unit.id] = unit.position
                if unit.team.startswith('enemy'):
                    self._add_unit(unit, gameStateObj)
                else:
                    self._add_ally(unit, unit.position, gameStateObj)

    def toggle_all_enemy_attacks(self):
        if self.all_on_flag:
            self.clear_all_enemy_attacks()
        else:
            self.show_all_enemy_attacks()

    def show_all_enemy_attacks(self):
        self.all_on_flag = True
        self.surf = None

    def clear_all_enemy_attacks(self):
        self.all_on_flag = False
        self.surf = None

    def draw(self, surf, size, gameStateObj):
        if not self.draw_flag:
            return
        if not self.surf:
            self.surf = Engine.create_surface(size, transparent=True)
            for grid_name in self.order:
                if grid_name == 'attack' and not self.displaying_units:
                    continue
                elif grid_name == 'spell' and not self.displaying_units:
                    continue
                elif grid_name == 'all_attack' and not self.all_on_flag:
                    continue
                elif grid_name == 'all_spell' and not self.all_on_flag:
                    continue
                if grid_name == 'all_attack' or grid_name == 'attack':
                    grid = self.grids['attack']
                else:
                    grid = self.grids['spell']
                for y in range(self.gridHeight):
                    for x in range(self.gridWidth):
                        cell = grid[x * self.gridHeight + y]
                        if cell:
                            if self.displaying_units:
                                display = any(u_id in self.displaying_units for u_id in cell)
                            else:
                                display = False
                            # print(x, y, cell, display)
                            # If there's one above this
                            if grid_name == 'all_attack' and display:
                                continue
                            if grid_name == 'all_spell' and display:
                                continue
                            if grid_name == 'attack' and not display:
                                continue
                            if grid_name == 'spell' and not display:
                                continue

                            # Handle fog of war
                            if gameStateObj.metaDataObj['fog_of_war']:
                                display = False
                                for u_id in cell:
                                    pos = self.true_positions.get(u_id)
                                    if pos and self.has_vision_at(pos):
                                        display = True
                                        break
                                if not display:
                                    continue

                            image = self.get_image(grid, x, y, grid_name)
                            topleft = x * GC.TILEWIDTH, y * GC.TILEHEIGHT
                            self.surf.blit(image, topleft)
                        # else:
                        #    print('- '),
                    # print('\n'),
        surf.blit(self.surf, (0, 0))

    def get_image(self, grid, x, y, grid_name):
        top_pos = (x, y - 1)
        left_pos = (x - 1, y)
        right_pos = (x + 1, y)
        bottom_pos = (x, y + 1)
        if grid_name == 'all_attack' or grid_name == 'all_spell':
            top = bool(grid[x * self.gridHeight + y - 1]) if self.check_bounds(top_pos) else False
            left = bool(grid[(x - 1) * self.gridHeight + y]) if self.check_bounds(left_pos) else False
            right = bool(grid[(x + 1) * self.gridHeight + y]) if self.check_bounds(right_pos) else False
            bottom = bool(grid[x * self.gridHeight + y + 1]) if self.check_bounds(bottom_pos) else False
        else:
            top = any(u_id in self.displaying_units for u_id in grid[x * self.gridHeight + y - 1]) if self.check_bounds(top_pos) else False
            left = any(u_id in self.displaying_units for u_id in grid[(x - 1) * self.gridHeight + y]) if self.check_bounds(left_pos) else False
            right = any(u_id in self.displaying_units for u_id in grid[(x + 1) * self.gridHeight + y]) if self.check_bounds(right_pos) else False
            bottom = any(u_id in self.displaying_units for u_id in grid[x * self.gridHeight + y + 1]) if self.check_bounds(bottom_pos) else False
        index = top*8 + left*4 + right*2 + bottom # Binary logic to get correct index
        # print(str(index) + ' '),
        return Engine.subsurface(self.types[grid_name], (index*GC.TILEWIDTH, 0, GC.TILEWIDTH, GC.TILEHEIGHT))

    def drawFogOfWar(self, surf, size):
        if not self.fog_of_war_surf:
            self.fog_of_war_surf = Engine.create_surface(size, transparent=True)
            for y in range(self.gridHeight):
                for x in range(self.gridWidth):
                    if not self.has_vision_at((x, y)):
                        image = self.fog_of_war_tile
                        topleft = x * GC.TILEWIDTH, y * GC.TILEHEIGHT
                        self.fog_of_war_surf.blit(image, topleft)
        surf.blit(self.fog_of_war_surf, (0, 0))

    def print_grid(self, grid_name):
        for y in range(self.gridHeight):
            for x in range(self.gridWidth):
                cell = self.grids[grid_name][x * self.gridHeight + y]
                if cell:
                    print(cell),
                else:
                    print('- '),
            print('\n'),
