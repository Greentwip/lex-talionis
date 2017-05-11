# Palette Swapper
# Make a copy first

from PIL import Image
import os

PaletteDict = {(56,56,144,255):(88,32,96,255),
               (56,80,224,255):(128,48,144,255),
               (40,160,248,255):(184,72,224,255),
               (24,240,248,255):(208,96,248,255),
               (232,16,24,255):(56,208,48,255),
               (88,72,120,255):(88,64,104,255),
               (144,184,232,255):(168,168,232,255),
               (64,56,56,255):(72,40,64,255)}

for fp in os.listdir('.'):
  if fp.endswith('.png'):
    picture = Image.open(fp)

    # Get the size of the image
    width, height = picture.size

    newimg = Image.new("RGBA", [width, height], (255,255,255,0))
    # Change color
    for x in range(width):
        for y in range(height):
            current_color = picture.getpixel((x,y))
            try:
                new_color = PaletteDict[current_color]
            except KeyError:
                new_color = current_color
            newimg.putpixel((x,y), new_color)

    newimg.save("enemy2" + str(fp[6:]))


#newimg.show()
        
