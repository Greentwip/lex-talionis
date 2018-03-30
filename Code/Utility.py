# Utility Functions
try:
    import manhattan_sphere
    FAST_SPHERE = True
except:
    FAST_SPHERE = False
    print('Fast manhattan sphere generation not available. Falling back on default Python implementation.')
try:
    import LOS
    FAST_LOS = True
except:
    FAST_LOS = False
    print('Fast line of sight calculation not available. Falling back on default Python implementation.')

# === TAXICAB DISTANCE =================================================
def calculate_distance(position1, position2):
    return (abs(position1[0] - position2[0]) + abs(position1[1] - position2[1]))

# === CLAMP NUMBERS ====================================================
def clamp(number_to_be_clamped, min_num, max_num):
    return min(max_num, max(min_num, number_to_be_clamped))

# === LINEAR EASING ====================================================
def easing(current_time, begin, change, total_time):
    """
    current_time = how much time has passed since start
    begin = starting value
    change = final value - starting value
    total_time = how long ease should take
    """
    return change * current_time / float(total_time) + begin

# === FINDS MAX VALUE ==================================================
def key_with_max_val(d):
    """
    a) create a list of the dict's keys and values; 
    b) return the key with the max value
    """  
    v = list(d.values())
    k = list(d.keys())
    return k[v.index(max(v))]

# === GREATER THAN OR EQUAL ============================================
def gte(a, b):
    return a >= b
# === LESS THAN =======================================================
def lt(a, b):
    return a < b
# === GREATER THAN =======================================================
def gt(a, b):
    return a > b

# === GET COLOR FROM TEAM ==============================================
def get_color(team):
    if team == 'player':
        return 'Blue'
    elif team == 'other':
        return 'Green'
    else:
        return 'Red'

# === DETERMINES MAX LEVEL FOR CLASS AT TIER ===========================
def find_max_level(tier, max_level_list):
    closest_tier = clamp(tier, 0, len(max_level_list) - 1)
    return max_level_list[closest_tier]

# === RAYTRACE ALGORITHM FOR TAXICAB GRID ==============================
def raytrace(old, new):
    x0, y0 = old
    x1, y1 = new
    tiles = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x = x0
    y = y0
    n = 1 + dx + dy
    x_inc = 1 if x1 > x0 else -1
    y_inc = 1 if y1 > y0 else -1
    error = dx - dy
    dx *= 2
    dy *= 2

    while(n > 0):
        tiles.append((x, y))
        if (error > 0):
            x += x_inc
            error -= dy
        else:
            y += y_inc
            error += dx
        n -= 1
    return tiles

# === PATH TRAVERSAL ===================================================
def travel_algorithm(gameStateObj, path, moves, unit, grid):
        """
        # Given a long path, travels along that path as far as possible 
        """
        if path:
            moves_left = moves
            through_path = 0
            for position in path[::-1][1:]: # Remove start position, travel backwards
                moves_left -= grid[gameStateObj.grid_manager.gridHeight * position[0] + position[1]].cost
                """
                if position in gameStateObj.map.tiles:
                    moves_left -= gameStateObj.map.tiles[position].get_mcost(unit)
                else:
                    break
                """
                if moves_left >= 0:
                    through_path += 1
                else:
                    break
            # Don't move where a unit already is, and don't make through_path < 0
            # Lower the through path by one, cause we can't move that far...
            while through_path > 0 and any(other_unit.position == path[-(through_path + 1)] for other_unit in gameStateObj.allunits if unit is not other_unit):
                through_path -= 1
            return path[-(through_path + 1)] # We found the quickest path, now attempt to travel along as far as we can
        else:
            return unit.position

# === Processes weighted lists
def process_terms(terms):
    # Process terms
    weight_sum = sum([term[1] for term in terms])
    if weight_sum <= 0:
        return 0
    # if cf.OPTIONS['debug']:
    #    print('Processed Terms: ', [term[0] for term in terms])
    return sum([float(term[0]*term[1]) for term in terms])/weight_sum 

# === Returns the index of a weighted list
def weighted_choice(choices):
    import random
    rn = random.randint(0, sum(choices) - 1)
    upto = 0
    for index, w in enumerate(choices):
        upto += w
        if upto > rn:
            return index
    assert False, "Shouldn't get here"

def get_adjacent_positions(c_pos, rng=1):
    if FAST_SPHERE:
        return manhattan_sphere.find_manhattan_spheres(range(1, rng+1), c_pos[0], c_pos[1])
    else:
        _range = range
        pos = set()
        for r in _range(1, rng+1):
            # Finds manhattan spheres of radius r
            for x in _range(-r, r + 1):
                pos_x = x if x >= 0 else -x
                for y in [(r - pos_x), -(r - pos_x)]:
                    pos.add((c_pos[0] + x, c_pos[1] + y))
        return pos

def find_manhattan_spheres(rng, c_pos):
    if FAST_SPHERE:
        return manhattan_sphere.find_manhattan_spheres(rng, c_pos[0], c_pos[1])
    else:
        _range = range
        main_set = set()
        for r in rng:
            # Finds manhattan spheres of radius r
            for x in _range(-r, r + 1):
                pos_x = x if x >= 0 else -x
                for y in [(r - pos_x), -(r - pos_x)]:
                    main_set.add((c_pos[0] + x, c_pos[1] + y))
        return main_set

def get_shell(ValidMoves, potentialRange, tile_map):
    if FAST_SPHERE:
        return manhattan_sphere.get_shell(ValidMoves, potentialRange, tile_map.width, tile_map.height)
    else:
        ValidAttacks = set()
        for validmove in ValidMoves:
            ValidAttacks |= find_manhattan_spheres(potentialRange, validmove)
        return [pos for pos in ValidAttacks if tile_map.check_bounds(pos)]

def farthest_away_pos(unit, valid_moves, all_units):
    # get farthest away position from general direction of enemy units
    if valid_moves:
        avg_position = [0, 0]
        enemy_units = [u for u in all_units if u.position and unit.checkIfEnemy(u)]
        if enemy_units:
            for u in enemy_units:
                avg_position[0] += u.position[0]
                avg_position[1] += u.position[1]
            avg_position[0] = avg_position[0]/len(enemy_units)
            avg_position[1] = avg_position[1]/len(enemy_units)
            return sorted(valid_moves, key=lambda move: calculate_distance(avg_position, move))[-1]
        else:
            return valid_moves[0]
    else:
        return None

def line_of_sight(source_pos, dest_pos, max_range, gameStateObj):
    if FAST_LOS:
        return LOS.line_of_sight(source_pos, dest_pos, max_range, gameStateObj.map.opacity_map, gameStateObj.map.height)

    # This is important so we can change the values of this while we iterate over it.
    class SimpleTile(object):
        def __init__(self):
            self.visibility = 'unknown'

    """
    def get_line3(start, end):
        # This one is to try and get more free results by tripling distance and checking 4 times instead of one, from each corner to middle
        # still gets weird results
        if start == end:
            return True
        #SuperCover Line Algorithm http://eugen.dedu.free.fr/projects/bresenham/
        # Setup initial conditions
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        x, y = x1, y1

        xstep, ystep = 1, 1
        if dy < 0:
            ystep = -1
            dy = -dy
        if dx < 0:
            xstep = -1
            dx = -dx
        ddy, ddx = 2*dy, 2*dx

        if ddx >= ddy:
            errorprev = error = dx
            for i in range(dx):
                x += xstep
                error += ddy
                # How far off the straight line to the right are you
                if error > ddx:
                    y += ystep
                    error -= ddx
                    if error + errorprev < ddx: # bottom square
                        pos = x/3, (y - ystep)/3
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    elif error + errorprev > ddx: # left square
                        pos = (x - xstep)/3, y/3
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    else:
                        pos1, pos2 = (x/3, (y - ystep)/3), ((x - xstep)/3, y/3)
                        if gameStateObj.map.tiles[pos1].opaque and gameStateObj.map.tiles[pos2].opaque:
                            return False
                pos = x/3, y/3
                if (x, y) != end and gameStateObj.map.tiles[pos].opaque:
                    return False
                errorprev = error
        else:
            errorprev = error = dy
            for i in range(dy):
                y += ystep
                error += ddx
                if error > ddy:
                    x += xstep
                    error -= ddy
                    if error + errorprev < ddy: # bottom square
                        pos = (x - xstep)/3, y/3
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    elif error + errorprev > ddy: # left square
                        pos = x/3, (y - ystep)/3
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    else:
                        pos1, pos2 = (x/3, (y - ystep)/3), ((x - xstep)/3, y/3)
                        if gameStateObj.map.tiles[pos1].opaque and gameStateObj.map.tiles[pos2].opaque:
                            return False
                pos = x/3, y/3
                if (x, y) != end and gameStateObj.map.tiles[pos].opaque:
                    return False
                errorprev = error
        assert x == x2 and y == y2
        return True
    """

    def get_line2(start, end):
        # This one is ~3-6 times faster than get_line1
        if start == end:
            return True
        # SuperCover Line Algorithm http://eugen.dedu.free.fr/projects/bresenham/
        # Setup initial conditions
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        x, y = x1, y1

        xstep, ystep = 1, 1
        if dy < 0:
            ystep = -1
            dy = -dy
        if dx < 0:
            xstep = -1
            dx = -dx
        ddy, ddx = 2*dy, 2*dx

        if ddx >= ddy:
            errorprev = error = dx
            for i in range(dx):
                x += xstep
                error += ddy
                # How far off the straight line to the right are you
                if error > ddx:
                    y += ystep
                    error -= ddx
                    if error + errorprev < ddx: # bottom square
                        pos = x, y - ystep
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    elif error + errorprev > ddx: # left square
                        pos = x - xstep, y
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    else:
                        pos1, pos2 = (x, y - ystep), (x - xstep, y)
                        if gameStateObj.map.tiles[pos1].opaque and gameStateObj.map.tiles[pos2].opaque:
                            return False
                pos = x, y
                if pos != end and gameStateObj.map.tiles[pos].opaque:
                    return False
                errorprev = error
        else:
            errorprev = error = dy
            for i in range(dy):
                y += ystep
                error += ddx
                if error > ddy:
                    x += xstep
                    error -= ddy
                    if error + errorprev < ddy: # bottom square
                        pos = x - xstep, y
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    elif error + errorprev > ddy: # left square
                        pos = x, y - ystep
                        if gameStateObj.map.tiles[pos].opaque:
                            return False
                    else:
                        pos1, pos2 = (x, y - ystep), (x - xstep, y)
                        if gameStateObj.map.tiles[pos1].opaque and gameStateObj.map.tiles[pos2].opaque:
                            return False
                pos = x, y
                if pos != end and gameStateObj.map.tiles[pos].opaque:
                    return False
                errorprev = error
        assert x == x2 and y == y2
        return True

    """
    def get_line(start, end):
        #print('Start:', start, "End:", end)
        if start == end:
            return True
        _int = int
        def rise_over_run((c_x, c_y), (e_x, e_y), end, d_x, d_y, d):
            #print(c_x, c_y)
            while (_int(c_x), _int(c_y)) != end:
                c_x += d_x * d
                c_y += d_y * d
                #print(c_x, c_y)
                c_pos = (_int(c_x), _int(c_y))
                if (c_x, c_y) == c_pos: # Don't need to check opacity if its on a corner
                    continue
                if gameStateObj.map.tiles[c_pos].opaque:
                    return False
                #elif c_pos in all_tiles and all_tiles[c_pos].visibility == 'unknown':
                #    all_tiles[c_pos].visibility = 'lit'
            return True
        x1, y1 = start
        x2, y2 = end
        d = 1/float(calculate_distance(start, end))/2 # Divide by 2 to get more accurate
        e_x, e_y = x2 + 0.5, y2 + 0.5
        # Go from each of the four corners
        for (x, y) in [(x1, y1), (x1 + 1, y1), (x1, y1 + 1), (x1 + 1, y1 + 1)]:
            # Determine which tiles are on the line
            #slope = (y - e_y)/(e_x - x) # difference because y goes down.
            d_x = (e_x - x)
            d_y = (e_y - y)
            if rise_over_run((x, y), (e_x, e_y), end, d_x, d_y, d):
                return True
    # End Func
    """

    all_tiles = {}
    for pos in dest_pos:
        all_tiles[pos] = SimpleTile()
        if pos in source_pos:
            all_tiles[pos].visibility = 'lit'

    # Any tile that can't be moved over at all is dark
    for pos, tile in all_tiles.iteritems():
        if gameStateObj.map.tiles[pos].opaque:
            tile.visibility = 'dark'

    # Iterate over remaining tiles
    for pos, tile in all_tiles.iteritems():
        if tile.visibility == 'unknown':
            for s_pos in source_pos:
                if calculate_distance(pos, s_pos) <= max_range and get_line2(s_pos, pos):
                    tile.visibility = 'lit'
                    break
            if tile.visibility == 'unknown':
                tile.visibility = 'dark'

    lit_tiles = [pos for pos in dest_pos if all_tiles[pos].visibility != 'dark']
    # print(time.clock() - time1)
    return lit_tiles

if __name__ == '__main__':
    for _ in range(100000):
        find_manhattan_spheres(range(10), (0, 0))
