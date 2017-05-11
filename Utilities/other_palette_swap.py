# Palette Swapper
# Make a copy first

from PIL import Image
import os

PaletteDict = {(56,56,144):(32,80,16),
               (56,80,224):(8,144,0),
               (40,160,248):(24,208,16),
               (24,240,248):(80,248,56),
               (232,16,24):(0,120,200),
               (88,72,120):(56,80,56),
               (144,184,232):(152,200,158),
               (216,232,240):(216,248,184),
               (112,96,96):(88,88,80),
               (176,144,88):(160,136,64),
               (248,248,208):(248,248,192),
               (248,248,64):(224,248,40)}

for fp in os.listdir('.'):
  if fp.endswith('.png'):
    picture = Image.open(fp)

    # Get the size of the image
    width, height = picture.size

    newimg = Image.new("RGB", [width, height], (255,255,255))
    # Change color
    for x in range(width):
        for y in range(height):
            current_color = picture.getpixel((x,y))
            try:
                new_color = PaletteDict[current_color]
            except KeyError:
                new_color = current_color
            newimg.putpixel((x,y), new_color)

    newimg.save("other" + str(fp[6:]))


#newimg.show()
        
