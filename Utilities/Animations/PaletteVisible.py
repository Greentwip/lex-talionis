#! usr/bin/env python2.7

# import random
from PIL import Image

color_set = [(240,163,255),(0,117,220),(153,63,0),(76,0,92),(25,25,25),(0,92,49),(43,206,72),(255,204,153),(128,128,128),(148,255,181),(143,124,0),(157,204,0),(194,0,136),(0,51,128),(255,164,5),(255,168,187),(66,102,0),(255,0,16),(94,241,242),(0,153,143),(224,255,102),(116,10,255),(153,0,0),(255,255,128),(255,255,0),(255,80,5)]

fp = 'Paladin0-Sword.png'
picture = Image.open(fp)

# Get the size of the image
width, height = picture.size

# Change color
for x in range(width):
    for y in range(height):
        current_color = picture.getpixel((x, y))
        """
        random.seed(current_color[0])
        new_color_1 = random.randint(0, 31)*8
        new_color_2 = random.randint(0, 31)*8
        new_color_3 = random.randint(0, 31)*8
        """
        new_color_1, new_color_2, new_color_3 = color_set[current_color[0]]
        picture.putpixel((x, y), (new_color_1, new_color_2, new_color_3, current_color[3]))

picture.save('New'+fp)
