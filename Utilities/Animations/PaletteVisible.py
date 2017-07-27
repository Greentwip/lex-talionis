#! usr/bin/env python2.7

from PIL import Image

fp = 'Mage0-Magic.png'
picture = Image.open(fp)

# Get the size of the image
width, height = picture.size

# Change color
for x in range(width):
    for y in range(height):
    	current_color = picture.getpixel((x,y))
    	new_grayscale = current_color[0] * 16
    	picture.putpixel((x, y), (new_grayscale, new_grayscale, new_grayscale, current_color[3]))

picture.save('Fixed'+fp)