import os
from PIL import Image

def get_similarity(im1, im2):
    counter = 0
    width, height = im1.size
    for x in range(width):
        for y in range(height):
            color = im1.getpixel((x, y))
            if color == im2.getpixel((x, y)):
                counter += 1
    return counter

def get_coord(im, coord):
    current_best, high_score = (0, 0), 0
    match_me = im.crop((coord[0], coord[1], coord[0] + 32, coord[1] + 16))
    for x in range(0, 96-32, 8):
        for y in range(0, 80-16, 8):
            test = im.crop((x, y, x + 32, y + 16))
            similarity = get_similarity(match_me, test)
            if similarity > high_score:
                current_best = (x, y)
                high_score = similarity
    return current_best

portraits = {}
orig_dir = 'Characters/NPCs'
for fn in os.listdir(orig_dir):
    im = Image.open(os.path.join(orig_dir, fn))
    name = fn[:-12]
    mouth_coord = get_coord(im, (64, 96))
    blink_coord = get_coord(im, (96, 48))
    portraits[name] = (mouth_coord, blink_coord)

with open('portrait_coords.xml', 'a') as fp:
    portraits = sorted(portraits.items())
    print(portraits)
    for name, coords in portraits:
        mouth, blink = coords
        fp.write('\t<portrait name="%s">\n' % name)
        fp.write('\t\t<mouth>%d,%d</mouth>\n' % (mouth[0], mouth[1]))
        fp.write('\t\t<blink>%d,%d</blink>\n' % (blink[0], blink[1]))
        fp.write('\t</portrait>\n\n')
