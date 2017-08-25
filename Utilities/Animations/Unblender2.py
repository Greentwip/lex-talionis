# Unblendes backgrounds and outputs their bg color to stdout

from PIL import Image

im = Image.open('ThunderMagic-Image.png')
new_im = Image.new('RGB', im.size)
for x_idx in xrange(8):
    for y_idx in xrange(2):
        color = im.getpixel((x_idx*240, y_idx*160))
        print(color)
        for x in xrange(240):
            for y in xrange(160):
                orig_color = im.getpixel((x_idx*240 + x, y_idx*160 + y))
                new_color = orig_color[0] - color[0], orig_color[1] - color[1], orig_color[2] - color[2]
                new_im.putpixel((x_idx*240 + x, y_idx*160 + y), new_color)

new_im.save('fixedThunderMagic-image.png')
