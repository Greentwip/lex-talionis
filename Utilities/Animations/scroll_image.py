import glob
from PIL import Image

lr_scroll = -0
ud_scroll = 1

for image in glob.glob('*.png'):
    print(image)
    im = Image.open(image)
    width, height = im.size
    new_im = Image.new('RGB', (width, height))
    for x in xrange(width):
        for y in xrange(height):
            color = im.getpixel((x, y))
            new_x = (x + lr_scroll) % width
            new_y = (y + ud_scroll) % height
            new_im.putpixel((new_x, new_y), color)
    new_im.save(image)

print('Done!')
