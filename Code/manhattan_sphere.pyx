# manhattan_spheres.py
# cython

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