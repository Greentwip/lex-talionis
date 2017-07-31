x1, x2, x3 = 96, 152, 200 # Base Color
z1, z2, z3 = 104, 200, 248 # Desired Color
x4, x5, x6 = 40, 40, 40 # Base Color #2
z4, z5, z6 = 48, 88, 248 # Desired Color #2

min_diff = 255
closest_color = (0, 0, 0, 0)
for r in xrange(0, 255, 8):
    print(r)
    for g in xrange(0, 255, 8):
        for b in xrange(0, 255, 8):
            for a in xrange(0, 32):
                p = (a/32.)
                new_z1 = x1 + (r - x1)*p
                new_z2 = x2 + (g - x2)*p
                new_z3 = x3 + (b - x3)*p
                new_z4 = x4 + (r - x4)*p
                new_z5 = x5 + (g - x5)*p
                new_z6 = x6 + (b - x6)*p
                diff = abs(z1 - new_z1) + abs(z2 - new_z2) + abs(z3 - new_z3) + abs(z4 - new_z4) + abs(z5 - new_z5) + abs(z6 - new_z6)
                if diff < min_diff:
                    min_diff = diff
                    closest_color = (r, g, b, a*8)

print(min_diff)
print(closest_color)




