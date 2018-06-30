# Palette Swapper
# Make a copy first

from PIL import Image
import os

PaletteDict = {(56, 56, 144): (88, 32, 96),
               (56, 80, 224): (128, 48, 144),
               (40, 160, 248): (184, 72, 224),
               (24, 240, 248): (208, 96, 248),
               (232, 16, 24): (56, 208, 48),
               (88, 72, 120): (88, 64, 104),
               (144, 184, 232): (168, 168, 232),
               (64, 56, 56): (72, 40, 64)}

for fp in os.listdir('.'):
    if fp.endswith('.png'):
        picture = Image.open(fp)

        # Get the size of the image
        width, height = picture.size

        newimg = Image.new("RGB", (width, height), (128, 160, 128))
        # Change color
        for x in range(width):
            for y in range(height):
                current_color = picture.getpixel((x, y))
                try:
                    new_color = PaletteDict[current_color]
                except KeyError:
                    new_color = current_color
                newimg.putpixel((x, y), new_color)

        newimg.save("enemy2" + str(fp[6:]))


#newimg.show()
        
