from PIL import Image
import glob

for fp in glob.glob('*.png'):
    im = Image.open(fp)
    width, height = im.size
    new_image = Image.new('RGB', (width, height))
    for x in xrange(width):
        for y in xrange(height):
            color = im.getpixel((x, y))
            new_x, new_y = 240 - x, y
            if 0 < new_x < 240 and 0 < new_y < 160:
                new_image.putpixel((new_x, new_y), color)

    new_image.save(fp)
