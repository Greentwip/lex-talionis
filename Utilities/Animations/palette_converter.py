from PIL import Image

from palette_index import *

### === INPUTS ===
p1 = joshua
p2 = myrmidon_red
image_to_convert = 'Myrmidon-Sword-Joshua.png'


conversion = {p1[i]: p2[i] for i in xrange(len(p1))}

image = Image.open(image_to_convert)
width, height = image.size

for x in xrange(width):
        for y in xrange(height):
                color = image.getpixel((x, y))
                if color in conversion:
                	new_color = conversion[color]
                else:
                	print('%s %s: %s %s %s'%(x, y, color[0], color[1], color[2]))
                	continue
                image.putpixel((x, y), new_color)

image.save('fixed' + image_to_convert)
