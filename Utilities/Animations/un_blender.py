# Unblends an image using a background image
import collections
from PIL import Image

COLORKEY = (128, 160, 128)
bg = Image.open('Background.png')
im = Image.open('Test.png')

width, height = bg.size
assert bg.size == im.size

new_im = Image.new('RGB', bg.size)

# color_dict = collections.Counter()
# marked = set()
for x in xrange(width):
    for y in xrange(height):
        bg_color = bg.getpixel((x, y))
        im_color = im.getpixel((x, y))
        # if im_color[0:3] == COLORKEY:
            # new_im.putpixel((x, y), COLORKEY)
        if im_color[0:3] == (248, 248, 248) and bg_color[0:3] != (248, 248, 248):
            new_im.putpixel((x, y), (248, 248, 248))
        else:
            new_color = [im_color[n] - bg_color[n] for n in xrange(3)]
            new_color = tuple(new_color)
            # if any(band == 248 for band in im_color[0:3]):
            #     marked.add((x, y))
            # color_dict[new_color] += 1
            new_im.putpixel((x, y), new_color)

# print(color_dict)
# valid_colors = {k: v for k, v in color_dict.iteritems() if v > 15}

# for _ in xrange(1):
#     for x, y in marked:
#         color = new_im.getpixel((x, y))
#         good = False
#         for valid_color in valid_colors:
#             num_same = 0
#             for i in xrange(3):
#                 if color[i] == valid_color[i]:
#                     num_same += 1
#             if num_same >= 2:
#                 new_im.putpixel((x, y), valid_color)
#                 good = True
#                 break

#         if not good:
#             for valid_color in valid_colors:
#                 num_same = 0
#                 for i in xrange(3):
#                     if color[i] == valid_color[i]:
#                         num_same += 1
#                 if num_same >= 1:
#                     new_im.putpixel((x, y), valid_color)
#                     good = True
#                     break

new_im.save('unblended.png')
