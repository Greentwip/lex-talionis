# manhattan_spheres.py
# cython: boundscheck=False
# cython: wraparound=False

cdef bint check_bounds(int x, int y, int width, int height):
    if x >= 0 and y >= 0 and x < width and y < height:
        return True
    return False

def find_manhattan_spheres(rng, int pos_x, int pos_y):
    cdef int r, x, y1, y2
    main_set = set()
    for r in rng:
        # Finds manhattan spheres of radius r
        for x in range(-r, r + 1):
            y1 = r - abs(x)
            y2 = -(r - abs(x))
            main_set.add((pos_x + x, pos_y + y1))
            main_set.add((pos_x + x, pos_y + y2))
    return main_set

def get_shell(ValidMoves, potentialRange, int width, int height):
    cdef tuple validmove, pos
    ValidAttacks = set()
    for validmove in ValidMoves:
        ValidAttacks |= find_manhattan_spheres(potentialRange, validmove[0], validmove[1])
    ValidAttacks = [pos for pos in ValidAttacks if check_bounds(pos[0], pos[1], width, height)]
    return ValidAttacks