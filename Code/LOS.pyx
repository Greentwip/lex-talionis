# line_of_sight.pyx
# cython: boundscheck=False
# cython: wraparound=False

cdef int get_pos(int x, int y, int grid_height):
    return x * grid_height + y

cdef int calculate_distance(int x1, int y1, int x2, int y2):
    return abs(x1 - x2) + abs(y1 - y2)

cdef bint get_line(int x1, int y1, int x2, int y2, opacity_map, int grid_height):
        if x1 == x2 and y1 == y2:
            return True
        # SuperCover Line Algorithm http://eugen.dedu.free.fr/projects/bresenham/
        # Setup initial conditions
        cdef int dx, dy, x, y, xstep, ystep, ddy, ddx, errorprev, error
        dx = x2 - x1
        dy = y2 - y1
        x = x1
        y = y1

        xstep = 1
        ystep = 1
        if dy < 0:
            ystep = -1
            dy = -dy
        if dx < 0:
            xstep = -1
            dx = -dx
        ddy = 2*dy
        ddx = 2*dx

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
                        if (x != x2 or y - ystep != y2) and opacity_map[get_pos(x, y - ystep, grid_height)]:
                            return False
                    elif error + errorprev > ddx: # left square
                        if (x - xstep != x2 or y != y2) and opacity_map[get_pos(x - xstep, y, grid_height)]:
                            return False
                    else:  # through the middle
                        if opacity_map[get_pos(x, y - ystep, grid_height)] and opacity_map[get_pos(x - xstep, y, grid_height)]:
                            return False
                if (x != x2 or y != y2) and opacity_map[get_pos(x, y, grid_height)]:
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
                        if (x - xstep != x2 or y != y2) and opacity_map[get_pos(x - xstep, y, grid_height)]:
                            return False
                    elif error + errorprev > ddy: # left square
                        if (x != x2 or y - ystep != y2) and opacity_map[get_pos(x, y - ystep, grid_height)]:
                            return False
                    else:  # through the middle
                        if opacity_map[get_pos(x, y - ystep, grid_height)] and opacity_map[get_pos(x - xstep, y, grid_height)]:
                            return False
                if (x != x2 or y != y2) and opacity_map[get_pos(x, y, grid_height)]:
                    return False
                errorprev = error
        assert x == x2 and y == y2
        return True

def line_of_sight(source_pos, dest_pos, int max_range, opacity_map, int grid_height):
    cdef int x1, y1, x2, y2
    cdef tuple pos, s_pos

    # 0 is unknown, 1 is dark, 2 is lit
    all_tiles = {}
    for pos in dest_pos:
        all_tiles[pos] = 0
        if pos in source_pos:
            all_tiles[pos] = 2

    # Any tile that can't be moved over at all is dark
    # for pos in all_tiles:
    #     if opacity_map[get_pos(pos[0], pos[1], grid_height)]:
    #         all_tiles[pos] = 1

    # Iterate over remaining tiles
    for pos in all_tiles:
        if all_tiles[pos] == 0:
            for s_pos in source_pos:
                x1, y1 = pos
                x2, y2 = s_pos
                if calculate_distance(x1, y1, x2, y2) <= max_range and get_line(x2, y2, x1, y1, opacity_map, grid_height):
                    all_tiles[pos] = 2
                    break
            if all_tiles[pos] == 0:
                all_tiles[pos] = 1

    lit_tiles = [pos for pos in dest_pos if all_tiles[pos] != 1]
    return lit_tiles
