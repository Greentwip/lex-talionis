# Takes a series of 240x160 frames and converts them into one spritesheet
# and an associated indexing file for use by the BattleAnimation routines

import glob
from PIL import Image

COLORKEY = (128, 160, 128)
COLORKEY = (0, 0, 0)
FIND_COLORKEY = False
NEW_COLORKEY = (128, 160, 128)
WIDTH_LIMIT = 1024
folder = 'fenrir_torch'
index_lines = []

files = glob.glob(folder + '/*.png')

new_files = []
for idx, fp in enumerate(files):
    sign = fp[:-4]
    first_digit = 0
    for i, c in enumerate(sign):
        if c.isdigit():
            first_digit = i
            break
    if first_digit:
        name, number = sign[:i], int(sign[i:])
        new_files.append((name, number, idx))
    else:
        new_files.append((sign, 0, idx))

for name, number, idx in sorted(new_files):
    fp = files[idx]
    print(fp)
    name = fp[:-4]
    if '\\' in name:
        name = name.split('\\')[1]
    image = Image.open(fp).convert('RGB')

    width, height = image.size

    # Convert colorkey colors to 0, 0, 0
    for x in xrange(width):
        for y in xrange(height):
            color = image.getpixel((x, y))
            if FIND_COLORKEY and x == 0 and y == 0:
                COLORKEY = color
            if color == COLORKEY:
                image.putpixel((x, y), (0, 0, 0))

    # Now get bbox
    left, upper, right, lower = image.getbbox()
    # left, upper, right, lower = 0, 0, 240, 160
    # x, y on sprite_sheet
    # Width, Height
    width, height = right - left, lower - upper
    # Offset from 0, 0
    offset = left, upper
    # Crop
    cropped = image.crop((left, upper, left+right, upper+lower))

    index_lines.append((cropped, name, width, height, offset))

index_script = open('New-Index.txt', 'w')

# Organize
x = 0
row = []
row_height = []
for image, name, width, height, offset in index_lines:
    if x + width > WIDTH_LIMIT:
        row_height.append(max(r for r in row))
        x = width
        row = [height]
    else:
        x += width
        row.append(height)
row_height.append(max(r for r in row))

print(row_height)
total_width = min(WIDTH_LIMIT, sum(i[2] for i in index_lines))
max_height = sum(r for r in row_height)

sprite_sheet = Image.new('RGB', (total_width, max_height))

# Paste
x = 0
current_row = 0
for image, name, width, height, offset in index_lines:
    if x + width > WIDTH_LIMIT:
        x = 0
        current_row += 1
    print(name)
    y = sum(row_height[:current_row+1]) - height
    sprite_sheet.paste(image, (x, y))
    index_script.write(name + ';' + str(x) + ',' + str(y) + ';' + str(width) + ',' + str(height) + ';' + str(offset[0]) + ',' + str(offset[1]) + '\n')
    x += width

# Now convert 0, 0, 0 back to colorkey
if FIND_COLORKEY:
    COLORKEY = NEW_COLORKEY
for x in xrange(total_width):
    for y in xrange(max_height):
        color = sprite_sheet.getpixel((x, y))
        if color == (0, 0, 0):                
            sprite_sheet.putpixel((x, y), COLORKEY)

sprite_sheet.save('new_spritesheet.png')
index_script.close()
