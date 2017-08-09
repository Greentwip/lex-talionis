import glob
from PIL import Image

palette = {(248, 248, 248), (176, 224, 248), (88, 168, 240)}
COLORKEY = (128, 160, 128)
for fp in glob.glob('*.png'):
    print(fp)
    im = Image.open(fp).convert('RGB')
    width, height = im.size
    for x in xrange(width):
        for y in xrange(height):
            if x > 120 and y < 109 and y > 25:
                color = im.getpixel((x, y))
                if color in palette:
                    pass
                else:
                    im.putpixel((x, y), COLORKEY)
            else:
                im.putpixel((x, y), COLORKEY)

    im.save('fixed_' + fp)