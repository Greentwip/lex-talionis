import glob
from PIL import Image

BACKGROUND = (128, 160, 128)
for fp in glob.glob('*.png'):
    image = Image.open(fp)
    my_image = image.crop((0, 0, 96, 80))
    width, height = my_image.size
    for x in xrange(width):
        for y in xrange(height):
            color = my_image.getpixel((x, y))
            if color == BACKGROUND:
                my_image.putpixel((x, y), (255, 255, 255))
    my_image.save(fp[:-12] + '_white.png')