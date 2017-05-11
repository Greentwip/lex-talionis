# Gray Converter
# Adds gray versions of sprite to the spritesheet

from PIL import Image
import os

PaletteDict = {(88,72,120):(64,64,64),
               (144,184,232):(120,120,120),
               (216,232,240):(184,184,184),
               (112,96,96):(80,80,80),
               (176,144,88):(128,128,128),
               (248,248,208):(200,200,200),
               (56,56,144):(72,72,72),
               (56,80,224):(88,88,88),
               (40,160,248):(152,152,152),
               (24,240,248):(184,184,184),
               (232,16,24):(112,112,112),
               (248,248,64):(200,200,200),
               (248,248,248):(208,208,208)}

def grayconvert(newimg):
    width, height = newimg.size
    grayimg = Image.new("RGB", [width, height], (16*8, 20*8, 16*8))
    # Change color
    for x in range(width):
        for y in range(height):
            current_color = newimg.getpixel((x,y))
            try:
                new_color = list(PaletteDict[current_color]) 
            except KeyError:
                new_color = current_color
            grayimg.putpixel((x,y), tuple(new_color))

    return grayimg

for fp in os.listdir('.'):
  if fp.endswith('.png'):
    picture = Image.open(fp)

    # Get the size of the image
    width, height = picture.size

    # Get only the passive_sprites
    passive_sprites = picture.crop((0, 0, width, height/3))
    gray_passive_sprites = grayconvert(passive_sprites)
    # Paste the new gray versions of the passive sprites 1/3 of the way down
    picture.paste(gray_passive_sprites, (0, height/3))

    picture.save('Fixed'+fp)

print "Done"

