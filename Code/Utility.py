# Utility Functions
import logging
logger = logging.getLogger(__name__)

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
     """ a) create a list of the dict's keys and values; 
         b) return the key with the max value"""  
     v=list(d.values())
     k=list(d.keys())
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

# === RAYTRACE ALGORITHM FOR TAXICAB GRID ==============================
def raytrace((x0, y0), (x1, y1)):
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
    #if OPTIONS['debug']:
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
    pos = set()
    for r in range(1, rng+1):
        # Finds manhattan spheres of radius r
        for x in range(-r, r + 1):
            for y in [(r - abs(x)), -(r - abs(x))]:
                pos.add((c_pos[0] + x, c_pos[1] + y))
    pos = list(pos)
    return pos

def find_manhattan_spheres(main_set, rng, c_pos, gameStateObj):
    for r in rng:
        # Finds manhattan spheres of radius r
        for x in range(-r, r + 1):
            for y in [(r - abs(x)), -(r - abs(x))]:
                pos = c_pos[0] + x, c_pos[1] + y
                if gameStateObj.map.check_bounds(pos):
                    main_set.add(pos)

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
    #import time
    #print('Source:', len(source_pos), source_pos)
    #print('Dest:', len(dest_pos), dest_pos)
    #time1 = time.clock()

    # This is important so we can change the values of this while we iterate over it.
    class SimpleTile(object):
        def __init__(self):
            self.visibility = 'unknown'

    """
    def get_line(start, end):
        #Bresenham's Line Algorithm
        # Setup initial conditions
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
     
        # Determine how steep the line is
        is_steep = abs(dy) > abs(dx)
     
        # Rotate line
        if is_steep:
            # Swap each's x and y coordinates
            x1, y1 = y1, x1
            x2, y2 = y2, x2
     
        # Swap start and end points if necessary and store swap state
        #swapped = False
        if x1 > x2:
            # Swap each one with the other.
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            #swapped = True
     
        # Recalculate differentials
        dx = x2 - x1
        dy = y2 - y1
     
        # Calculate error
        error = dx/2 #int(dx / 2.0)
        ystep = 1 if y1 < y2 else -1
     
        # Iterate over bounding box generating points between start and end
        y = y1
        for x in range(x1, x2 + 1):
            coord = (y, x) if is_steep else (x, y)
            if opaque(coord):
                return False
            error -= abs(dy)
            if error < 0:
                y += ystep
                error += dx
        return True

    def get_line2(start, end):
        # My own personal LOS algorithm
        print('Start:', start, "End:", end)
        logger.debug('Start: %s End: %s', start, end)
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        # Keeps a list of explored tiles on the way to the goal
        # If ever there are no more tiles in the list, the algorithm has failed
        # to find the end
        explored = [(x1, y1, dx, dy)]
        while explored:
            x, y, dx, dy = explored.pop()
            logger.debug('%s %s %s %s', x, y, dx, dy)
            #print(x, y, dx, dy)
            # If we're at an opaque tile, do not proceed
            if opaque((x, y)):
                continue
            # If we're in an obviously bad position, do not proceed
            if obviously_bad(start, (x, y)):
                continue
            # We reached our goal
            if (x, y) == end:
                return True
            # Determine where to go next. Can go up to two different places
            # If we need to go more y, go in that direction
            # If we need to go more x, go in that direction
            # If they're even, go in both directions
            adx = abs(dx)
            ady = abs(dy)
            if adx == ady:
                if dx > 0:
                    explored.append((x + 1, y, dx - 1, dy))
                elif dx < 0:
                    explored.append((x - 1, y, dx + 1, dy))
                if dy > 0:
                    explored.append((x, y + 1, dx, dy - 1))
                elif dy < 0:
                    explored.append((x, y - 1, dx, dy + 1))
            elif adx > ady:
                if dx > 0:
                    explored.append((x + 1, y, dx - 1, dy))
                elif dx < 0:
                    explored.append((x - 1, y, dx + 1, dy))
            elif ady > adx:
                if dy > 0:
                    explored.append((x, y + 1, dx, dy - 1))
                elif dy < 0:
                    explored.append((x, y - 1, dx, dy + 1))
        return False

    def obviously_bad(start, end):
        # A naive line of sight algorithm. 
        # If there is a block DIRECTLY in the way, its bad.
        if start == end:
            return False
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        x_inc = 1 if dx > 0 else -1
        y_inc = 1 if dy > 0 else -1
        while (x1, y1) != end:
            if dy == 0:
                x1 += x_inc
            elif dx == 0:
                y1 += y_inc
            elif abs(dx) == abs(dy):
                x1 += x_inc
                y1 += y_inc
            else:
                return False
            if opaque((x1, y1)):
                return True
        return False
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
        for (x, y) in [(x1, y1), (x1 + 1, y1), (x1, y1 + 1), (x1 + 1, y1 + 1)]:
            # Determine which tiles are on the line
            #slope = (y - e_y)/(e_x - x) # difference because y goes down.
            d_x = (e_x - x)
            d_y = (e_y - y)
            if rise_over_run((x, y), (e_x, e_y), end, d_x, d_y, d):
                return True
    # End Func

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
                if calculate_distance(pos, s_pos) <= max_range and get_line(s_pos, pos):
                    tile.visibility = 'lit'
                    break
            if tile.visibility == 'unknown':
                tile.visibility = 'dark'

    lit_tiles = [pos for pos in dest_pos if all_tiles[pos].visibility != 'dark']
    #print(time.clock() - time1)
    return lit_tiles