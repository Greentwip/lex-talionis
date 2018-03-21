#!/usr/bin/env/python2.7

# FERepo to Lex Talionis Format for Full Combat Animations
# Takes in FERepo data... a set of images along with a *.txt file that serves as the script.

import glob
from PIL import Image

COLORKEY = 128, 160, 128
WIDTH_LIMIT = 240 * 5

def convert_gba(im):
    width, height = im.size
    for x in xrange(width):
        for y in xrange(height):
            color = im.getpixel((x, y))
            new_color = (color[0] / 8 * 8), (color[1] / 8 * 8), (color[2] / 8 * 8)
            im.putpixel((x, y), new_color)
    return im

def determine_bg_color(im):
    color = im.getpixel((0, 0))
    return color

def animation_collater(images, bg_color):
    index_lines = []
    for name, image in images.items():
        width, height = image.size

        # Convert colorkey colors to 0, 0, 0
        for x in xrange(width):
            for y in xrange(height):
                color = image.getpixel((x, y))
                if color == bg_color:
                    image.putpixel((x, y), (0, 0, 0))

        # Now get bbox
        left, upper, right, lower = image.getbbox()
        width, height = right - left, lower - upper
        # Offset from 0, 0
        offset = left, upper
        cropped = image.crop((left, upper, left + right, upper + lower))

        index_lines.append((cropped, name, width, height, offset))

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

    total_width = min(WIDTH_LIMIT, sum(i[2] for i in index_lines))
    max_height = sum(r for r in row_height)

    sprite_sheet = Image.new('RGB', (total_width, max_height))
    index_script = open('new_index.txt', 'w')

    # Paste
    x = 0
    current_row = 0
    for image, name, width, height, offset in index_lines:
        if x + width > WIDTH_LIMIT:
            x = 0
            current_row += 1
        y = sum(row_height[:current_row + 1]) - height
        sprite_sheet.paste(image, (x, y))
        index_script.write(name + ';' + str(x) + ',' + str(y) + ';' + str(width) + ',' +
                           str(height) + ';' + str(offset[0]) + ',' + str(offset[1]) + '\n')
        x += width

    # Now convert 0, 0, 0 back to COLORKEY
    for x in xrange(total_width):
        for y in xrange(max_height):
            color = sprite_sheet.getpixel((x, y))
            if color == (0, 0, 0):
                sprite_sheet.putpixel((x, y), COLORKEY)

    sprite_sheet.save('new_spritesheet.png')
    index_script.close()

images = glob.glob('*.png')
script = glob.glob('*.txt')

if len(script) == 1:
    script = script[0]
elif len(script) == 0:
    raise ValueError("No script file present in current directory!")
else:
    raise ValueError("Could not determine which *.txt file to use!")

# Convert to images
images = {name[:-4]: Image.open(name) for name in images}

# Convert to GBA Colors
for image in images.values():
    image = convert_gba(image).convert('RGB')

# If width of image == 248, clip last 8 pixels
for image in images.values():
    if image.width == 248:
        image = image.crop((0, 0, 240, image.height))
    elif image.width == 488:
        image = image.crop((0, 0, 480, image.height))

# If double image, create one as under image instead
new_images = {}
for name in images.keys():
    image = images[name]
    if image.width == 480:
        image1 = image.crop((0, 0, 240, image.height))
        image2 = image.crop((240, 0, 480, image.height))
        new_images[name] = image1
        new_images[name + '_under'] = image2
images.update(new_images)

bg_color = determine_bg_color(images.values()[0])

# Create image and index script
animation_collater(images, bg_color)

# Open fe repo script
with open(script) as s:
    script_lines = s.readlines()

begin = False
current_mode = None
melee_script = {}
ranged_script = {}
current_pose = []
current_frames = None
frame_index = 0
crit = False
for line in script_lines:
    if '#' in line:
        line = line[:line.index('#')]
    line = line.strip()
    
    if line.startswith('/// - '):
        print(line[11:])
        if current_mode:
            if current_mode in (1, 2):
                melee_script['Attack'] = current_pose
            elif current_mode in (3, 4):
                melee_script['Critical'] = current_pose
            elif current_mode == 5:
                ranged_script['Attack'] = current_pose
            elif current_mode == 6:
                ranged_script['Critical'] = current_pose
            elif current_mode == 7:
                melee_script['Dodge'] = current_pose
                ranged_script['Dodge'] = current_pose
            elif current_mode == 8:
                melee_script['RangedDodge'] = current_pose
                ranged_script['RangedDodge'] = current_pose
            elif current_mode == 9:
                melee_script['Stand'] = current_pose
            elif current_mode == 11:
                ranged_script['Stand'] = current_pose
            elif current_mode == 12:
                melee_script['Miss'] = current_pose
            
        if line.startswith('/// - Mode '):
            current_mode = int(line[11:])
        else:
            break  # Done

    elif line.startswith('C'):
        command_code = line[1:3]
        if command_code == '01':
            if current_mode == 12:  # Miss
                current_pose.append('f;2;' + current_frames[0])
                current_pose.append('miss')
                current_pose.append('f;30' + current_frames[0])
                frame_index += 32
            else:  # Hit
                current_pose.append('wait_for_hit;' + current_frames[0])
                current_pose.append('f;4' + current_frames[0])
                frame_index += 4
        elif command_code == '03':
            begin = True
        elif command_code == '04':
            if current_mode == 12:  # Ignore if miss
                pass
            else:
                current_pose.append('enemy_flash_white;8')
        elif command_code == '06':
            pass  # Normally starts enemy turn, but that doesn't happen in LT script
        elif command_code == '07':
            begin = True
        elif command_code == '08':
            crit = True
            current_pose.append('foreground_blend;2;248,248,248')
        elif command_code == '0D':
            current_pose.append('f;' + str(current_frames[1]) + ';' + current_frames[0])  
            current_frames = None
        elif command_code == '1A':
            crit = False
            current_pose.append('screen_flash_white;4')
        elif command_code == '1F':
            if crit:
                current_pose.append('start_hit')
                current_pose.append('f;2' + current_frames[0])
                current_pose.append('crit_spark')
                current_pose.append('f;2' + current_frames[0])
            else:
                current_pose.append('f;4;' + current_frames[0])
                current_pose.append('hit_spark')
                current_pose.append('start_hit')
            frame_index += 4
        # Sounds
        elif command_code == '1C':
            current_pose.append('sound;Horse Step 1')
        elif command_code == '1D':
            current_pose.append('sound;Horse Step 3')
        elif command_code == '1E':
            current_pose.append('sound;Horse Step 2')
        elif command_code == '22':
            current_pose.append('sound;Weapon Pull')
        elif command_code == '23':
            current_pose.append('sound;Weapon Push')
        
        # Need to keep track of how many of these we pass, since each adds a frame
        current_frames[1] += 1
        
    elif line.startswith('~~~'):
        pass

    else:
        num_frames, _, png_name = line.split()
        num_frames = int(num_frames)
        name = png_name[:-4]
        if begin:
            num_frames = 6
        if current_frames:  # write the last one
            current_pose.append('f;' + str(current_frames[1]) + ';' + current_frames[0])  
        current_frames = [name, num_frames]
        frame_index += num_frames
