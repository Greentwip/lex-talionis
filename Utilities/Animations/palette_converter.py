from PIL import Image
import glob
from palette_index import *

### === INPUTS ===
p1 = assassin_jaffar
p2 = assassin_red
images_to_convert = '*.png'

def palette_convert(p1, p2, image_to_convert):
    conversion = {p1[i]: p2[i] for i in xrange(len(p1))}

    image = Image.open(image_to_convert).convert('RGB')
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

    image.save('fixed_' + image_to_convert)

for fp in glob.glob(images_to_convert):
    print(fp)
    palette_convert(p1, p2, fp)
