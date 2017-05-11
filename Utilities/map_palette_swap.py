#! usr/bin/env python2.7

"""
 # Author: rainlash
 # Purpose: Takes one image and tries to replace its palette with the palette of another image
 # Inputs: Name of two images, one image to have its color replaced with the colors of another
 # Assumptions: 16x16 tiles that are shared shape.
"""

# Palette Swapper
my_orig = '10007312.png' # Image to base colors off of
my_new = 'TileSet.png' # Image that will have its color replaced

from PIL import Image
#import numpy as np

class PaletteData(object):
    def __init__(self, arr):
        self.data = list(arr.getdata()) 
        count = 1
        uniques = reduce(lambda l, x: l if x in l else l+[x], self.data, [])
        self.palette = self.data[:]
        for u in uniques:
            for index, pixel in enumerate(self.data):
                if pixel == u:
                    self.palette[index] = count
            count += 1

def replace_colors(convert, data, orig_colors, new_colors, done_colors):
    for index, color in enumerate(orig_colors):
        if color in done_colors:
            continue
        print(color, new_colors[index])
        for y in xrange(convert.size[1]):
            for x in xrange(convert.size[0]):
                if data[x, y] == color:
                    data[x, y] = new_colors[index]
        done_colors.append(color)
    return done_colors

orig = Image.open(my_orig)
convert = Image.open(my_new)
#convert_data = np.array(convert)
convert_data = convert.load()

done_colors = []

base_tiles = []
for x in range(orig.size[0]/16):
    for y in range(orig.size[1]/16):
        tile = PaletteData(orig.crop((x*16, y*16, x*16+16, y*16+16)))
        #print(tile.palette)
        base_tiles.append(tile)

# Get positions of convert
for i in range(convert.size[0]/16):
    for j in range(convert.size[1]/16):
        test_im = PaletteData(convert.crop((i*16, j*16, i*16+16, j*16+16)))
        #print(test_im.palette)

        for tile in base_tiles:
            if tile.palette == test_im.palette:
                #print(tile.palette)
                #print(test_im.palette)
                replace_colors(convert, convert_data, test_im.data, tile.data, done_colors)

#convert = Image.fromarray(convert_data)
convert.save('new_convert.png')

