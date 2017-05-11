#!/usr/bin/env python

# Builds MapSprites
from PIL import Image

def replace_color(img):
    # Change color
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            current_color = img.getpixel((x,y))
            if current_color == (168, 208, 160):
                img.putpixel((x,y), (16*8, 20*8, 16*8))

im = Image.open('EnemyMugshots2.png')
i = 133
j = 240
new_image = im.crop((i, j, i+80, j+72))
replace_color(new_image)
new_image.save('Generic_Portrait_Warrior.png')