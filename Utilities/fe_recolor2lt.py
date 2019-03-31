# converts GE Recolor GBA Hex Codes to REAL COLORS YEAH!

from itertools import izip_longest

def groupby(iterable, n):
    args = [iter(iterable)] * n
    return izip_longest(*args)

def hex_to_binary(hex):
    return bin(int(hex, 16))[2:].zfill(16)

print("Paste hex code here: ")
hex_code = raw_input("> ")

colors = groupby(hex_code, 4)
new_colors = []
for color in colors:
    color_string = ''.join(color)
    bin_string = hex_to_binary(color_string)
    # little endian to big endian
    bin_string = bin_string[8:] + bin_string[:8]

    blue = int(bin_string[1:6], 2)
    green = int(bin_string[6:11], 2)
    red = int(bin_string[11:], 2)

    red, green, blue = red*8, green*8, blue*8
    new_colors.append((red, green, blue))

"""
Workflow
Pull up animation image in gui
color palette shows up to the right
Can zoom in on images
Plays sounds?
Can play different animations with buttons to the right
Can swap colors and see how that works
Can swap between palettes already defined
Can create new palettes
Can have multiple rows of palettes
Can load GBA palettes. How to organize order of colors?
"""
