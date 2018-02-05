# Palette Swapper
# Make a copy first

from PIL import Image
import os

PaletteDict = {(56, 56, 144): (96, 40, 32),
               (56, 80, 224): (168, 48, 40),
               (40, 160, 248): (224, 16, 16),
               (24, 240, 248): (248, 80, 72),
               (232, 16, 24): (56, 208, 48),
               (88, 72, 120): (104, 72, 96),
               (64, 56, 56): (64, 56, 56),
               (216, 232, 240): (224, 224, 224),
               (248, 248, 64): (248, 248, 64),
               (112, 96, 96): (112, 96, 96),
               (64, 56, 56): (64, 56, 56),
               (248, 248, 248): (248, 248, 248),
               (176, 144, 88): (176, 144, 88),
               (248, 248, 208): (248, 248, 208),
               (128, 136, 112): (128, 136, 112),
               (144, 184, 232): (192, 168, 184)}

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
                    if current_color != (128, 160, 128):
                        print(current_color)
                    new_color = current_color
                newimg.putpixel((x, y), new_color)

        newimg.save("enemy" + str(fp[6:]))        
