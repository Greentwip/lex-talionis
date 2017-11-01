# Converts to gba colors

import glob
from PIL import Image

loc = 'swordmaster_unarmed_lloyd/'
# Get all sprites
imageList = [im for im in glob.glob(loc + '*.png')]

def convert_gba(im):
    width, height = im.size
    for x in xrange(width):
        for y in xrange(height):
            color = im.getpixel((x, y))
            new_color = (color[0] / 8 * 8), (color[1] / 8 * 8), (color[2] / 8 * 8)
            im.putpixel((x, y), new_color)
    return im

for image in imageList:
    print(image)
    convert_gba(Image.open(image)).convert('RGB').save(image)
