def alphaize(desired_color, background_color):
    r1 = background_color[0]
    g1 = background_color[1]
    b1 = background_color[2]

    r2 = desired_color[0]
    g2 = desired_color[1]
    b2 = desired_color[2]

    alpha = 0
    r = -1
    g = -1
    b = -1

    while alpha < 1 and (r < 0 or g < 0 or b < 0 or r > 255 or g > 255 or b > 255):
        alpha += 1/256.0
        inv = 1 / alpha
        r = r2 * inv + r1 * (1 - inv)
        g = g2 * inv + g1 * (1 - inv)
        b = b2 * inv + b1 * (1 - inv)

    return r, g, b, alpha

desired_color = (48, 88, 248)
background_color = (40, 40, 40)
print(alphaize(desired_color, background_color))