#!/usr/bin/env/python2.7

# FERepo to Lex Talionis Format for Full Combat Animations
# Takes in FERepo data... a set of images along with a *.txt file that serves as the script.

import glob
from collections import OrderedDict
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

def animation_collater(images, bg_color, weapon_type):
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
        bbox = image.getbbox()
        if not bbox:
            print('Replace instances of %s with "wait" command!' % name)
            continue
        left, upper, right, lower = bbox
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
            row_height.append(max(row))
            x = width
            row = [height]
        else:
            x += width
            row.append(height)
    row_height.append(max(row))

    total_width = min(WIDTH_LIMIT, sum(i[2] for i in index_lines))
    max_height = sum(row_height)

    sprite_sheet = Image.new('RGB', (total_width, max_height))
    index_script = open(weapon_type + '-Index.txt', 'w')

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

    sprite_sheet.save(weapon_type + '-GenericBlue.png')
    index_script.close()

def write_scripts(script, images, weapon_type):
    # Open fe repo script
    with open(script) as s:
        script_lines = s.readlines()

    begin = False
    current_mode = None
    melee_script, melee_images = {}, set()
    ranged_script, ranged_images = {}, set()
    current_pose = []
    current_frame = None
    crit = False  # Whether this is a critical hit
    start_hit = False  # Whether we need to append our start_hit command after the next frame
    throwing_axe = False
    dodge_front = False
    used_names = set()

    def write_frame(current_pose, name, num_frames):
        if (name + '_under') in images:
            current_pose.append('f;' + str(num_frames) + ';' + name + ';' + name + '_under')
            used_names.add(name + '_under')
        else:
            current_pose.append('f;' + str(num_frames) + ';' + name)
        used_names.add(name)

    def write_over_frame(current_pose, name, num_frames):
        if (name + '_under') in images:
            current_pose.append('of;' + str(num_frames) + ';' + name + ';' + name + '_under')
            used_names.add(name + '_under')
        else:
            current_pose.append('of;' + str(num_frames) + ';' + name)
        used_names.add(name)

    def write_wait_for_hit(current_pose, name):
        if (name + '_under') in images:
            current_pose.append('wait_for_hit;' + name + ';' + name + '_under')
            used_names.add(name + '_under')
        else:
            current_pose.append('wait_for_hit;' + name)
        used_names.add(name)

    def save_mode(mode):
        if weapon_type == 'Magic':
            if mode not in (5, 6, 7, 9, 11):
                used_names.clear()
                return
        if mode in (1, 2):
            melee_script['Attack'] = current_pose
            melee_images.update(used_names)
        elif mode in (3, 4):
            melee_script['Critical'] = current_pose
            melee_images.update(used_names)
        elif mode == 5:
            ranged_script['Attack'] = current_pose
            ranged_images.update(used_names)
        elif mode == 6:
            ranged_script['Critical'] = current_pose
            ranged_images.update(used_names)
        elif mode == 7:
            melee_script['Dodge'] = current_pose
            melee_images.update(used_names)
            ranged_script['Dodge'] = current_pose
            ranged_images.update(used_names)
        elif mode == 9:
            melee_script['Stand'] = current_pose
            melee_images.update(used_names)
        elif mode == 11:
            ranged_script['Stand'] = current_pose
            ranged_images.update(used_names)
        elif mode == 12:
            melee_script['Miss'] = current_pose
            melee_images.update(used_names)
        used_names.clear()  # Reset used names

    for line in script_lines:
        if '#' in line:
            line = line[:line.index('#')]
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('/// - '):
            if current_mode:
                save_mode(current_mode)
            if line.startswith('/// - Mode '):
                current_mode = int(line[11:])
                current_pose = []  # New current pose
                throwing_axe = False
                current_frame = None
                dodge_front = False
                shield_toss = False
            else:
                break  # Done

        elif line.startswith('C'):
            command_code = line[1:3]
            write_extra_frame = True
            if command_code == '01':
                if throwing_axe:
                    current_pose.append('start_loop')
                    write_frame(current_pose, current_frame, 1)
                    current_pose.append('end_loop')
                    write_frame(current_pose, current_frame, 8)
                elif current_mode == 12:  # Miss
                    write_frame(current_pose, current_frame, 1)
                    current_pose.append('miss')
                    write_frame(current_pose, current_frame, 30)
                elif current_mode == 5 or current_mode == 6:  # Ranged
                    current_pose.append('start_loop')
                    write_frame(current_pose, current_frame, 4)
                    current_pose.append('end_loop')
                    write_frame(current_pose, current_frame, 4)
                elif current_mode == 7 or current_mode == 8:  # Dodge
                    if dodge_front:
                        write_over_frame(current_pose, current_frame, 26)
                    else:
                        write_frame(current_pose, current_frame, 26)
                elif current_mode in (1, 2, 3, 4):
                    write_wait_for_hit(current_pose, current_frame)
                    if shield_toss:
                        current_pose.append('end_child_loop')
                    else:
                        write_frame(current_pose, current_frame, 4)
                elif current_mode in (9, 10, 11):
                    write_frame(current_pose, current_frame, 3)
                write_extra_frame = False  # 01 does not drop 1 frame after it runs
            elif command_code == '02':
                write_extra_frame = False  # Normally says this is a dodge, but that doesn't matter
            elif command_code == '03':
                begin = True
            elif command_code == '04':
                write_extra_frame = False  # Normally prepares some code for returning to stand
            elif command_code == '05':  # Start spell
                if weapon_type == 'Sword' or weapon_type == 'Magic':
                    current_pose.append('spell')
                elif weapon_type == 'Lance':
                    current_pose.append('spell;Javelin')
                elif weapon_type in ('Axe', 'Handaxe'):
                    current_pose.append('spell;ThrowingAxe')
                elif weapon_type == 'Bow':
                    current_pose.append('spell;Arrow')
                write_extra_frame = False
            elif command_code == '06':
                write_extra_frame = False  # Normally starts enemy turn, but that doesn't happen in LT script
            elif command_code == '07':
                begin = True
            elif command_code in ('08', '09', '0A', '0B', '0C'):  # Start crit
                crit = True
                current_pose.append('enemy_flash_white;8')
                write_frame(current_pose, current_frame, 1)
                current_pose.append('foreground_blend;2;248,248,248')
                start_hit = True
                write_extra_frame = False
            elif command_code == '0D':  # End
                write_frame(current_pose, current_frame, 1)
                write_extra_frame = False
            elif command_code == '0E':  # Dodge
                write_extra_frame = False
            elif command_code == '13':
                current_pose.append('start_loop')
                write_frame(current_pose, current_frame, 1)
                current_pose.append('end_loop')
                throwing_axe = True
            elif command_code == '14':
                current_pose.append('screen_shake')
            elif command_code == '15':
                current_pose.append('platform_shake')
            elif command_code == '18':
                dodge_front = True  # Dodge to the front
                write_extra_frame = False  
            elif command_code == '1A':  # Start hit
                crit = False
                current_pose.append('enemy_flash_white;8')
                write_frame(current_pose, current_frame, 1)
                current_pose.append('screen_flash_white;4')
                start_hit = True
            elif command_code in ('1F', '20', '21'):  # Actual hit
                write_extra_frame = False
            # Sounds and other effects
            elif command_code == '19':
                current_pose.append('sound;Bow')
            elif command_code == '1B':
                current_pose.append('sound;Foot Step')
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
            elif command_code == '24':
                current_pose.append('sound;Weapon Swing')
            elif command_code == '25':
                current_pose.append('sound;Heavy Wing Flap')
            elif command_code == '26' or command_code == '27':
                current_pose.append('effect;ShieldToss')
                shield_toss = True
            elif command_code == '28':
                current_pose.append('sound;ShamanRune')
            elif command_code == '2B':
                current_pose.append('sound;ArmorShift')
            elif command_code == '2E':
                current_pose.append('effect;MageInit')
                print('Change "effect;MageInit" to "effect;SageInit" if working with Sage animations')
            elif command_code == '2F':
                current_pose.append('effect;MageCrit')
                print('Change "effect;MageCrit" to "effect;SageCrit" if working with Sage animations')
            elif command_code == '30':
                current_pose.append('effect;DirtKick')
            elif command_code == '33':
                current_pose.append('sound;Battle Cry')
            elif command_code == '34':
                current_pose.append('sound;Step Back 1')
            elif command_code == '35':
                current_pose.append('sound;Long Wing Flap')
            elif command_code == '36':
                current_pose.append('sound;Unsheathe')
            elif command_code == '37':
                current_pose.append('sound;Sheathe')
            elif command_code == '38':
                current_pose.append('sound;Heavy Spear Spin')
            elif command_code == '41':
                current_pose.append('sound;Axe Pull')
            elif command_code == '42':
                current_pose.append('sound;Axe Push')
            elif command_code == '43':
                current_pose.append('sound;Weapon Click')
            elif command_code == '44':
                current_pose.append('sound;Weapon Shine')
            elif command_code == '47':
                current_pose.append('effect;Cape Animation')
                print('Replace "effect;Cape Animation" with actual frames for cape animation in a loop')
            elif command_code == '49':
                current_pose.append('sound;SageRune')
            elif command_code == '4B':
                current_pose.append('sound;MonkRune')
            elif command_code == '4F':
                current_pose.append('sound;DruidCrit')
            elif command_code == '51':
                current_pose.append('screen_flash_white;4')
            elif command_code == '79':
                current_pose.append('sound;StrategistRune')
            elif command_code == '7A':
                current_pose.append('sound;StrategistCrit')
            else:
                print('Unknown Command Code: C%s' % command_code)
            
            if write_extra_frame and current_frame:
                if dodge_front:
                    write_over_frame(current_pose, current_frame, 1)
                else:
                    write_frame(current_pose, current_frame, 1)
            
        elif line.startswith('~~~'):
            pass

        else:
            num_frames, _, png_name = line.split()
            num_frames = int(num_frames)
            name = png_name[:-4]
            if name not in images:
                raise ValueError('%s frame not in images!' % name)
            if begin:
                num_frames = 6
                begin = False
            current_frame = name
            if not (start_hit and crit):  # Don't write this frame if we're starting a crit
                if dodge_front:
                    write_over_frame(current_pose, current_frame, num_frames)
                else:
                    write_frame(current_pose, current_frame, num_frames)
            if start_hit:
                if crit:
                    current_pose.append('start_hit')
                    write_frame(current_pose, current_frame, 2)
                    current_pose.append('crit_spark')
                else:
                    write_frame(current_pose, current_frame, 2)
                    current_pose.append('hit_spark')
                    current_pose.append('start_hit')
                start_hit = False

    def write_script(script, s):
        for pose, line_list in script.items():
            s.write('pose;' + pose + '\n')
            for line in line_list:
                s.write(line + '\n')
            s.write('\n')

    def collate_script(script):
        for pose in script.keys():
            new_line_list = []
            old_line_list = [_ for _ in script[pose]]
            prev, curr = None, None
            while old_line_list:
                curr = old_line_list.pop()
                if prev:
                    if curr.startswith('f;') and prev.startswith('f;'):
                        c_s = curr.split(';')
                        p_s = prev.split(';')
                        if p_s[2:] == c_s[2:]:
                            curr = 'f;' + str(int(c_s[1]) + int(p_s[1])) + ';' + ';'.join(c_s[2:])
                            prev = None
                if prev:
                    new_line_list.append(prev)
                prev = curr
            if prev:
                new_line_list.append(prev)
            script[pose] = list(reversed(new_line_list))

    # Combines frame numbers if they are the same frame
    collate_script(melee_script)
    collate_script(ranged_script)

    # Now actually write scripts
    if weapon_type == 'Sword':
        with open('Sword-Script.txt', 'w') as s:
            write_script(melee_script, s)
        with open('MagicSword-Script.txt', 'w') as s:
            write_script(ranged_script, s)
    elif weapon_type == 'Lance':
        with open('Lance-Script.txt', 'w') as s:
            write_script(melee_script, s)
        with open('RangedLance-Script.txt', 'w') as s:
            write_script(ranged_script, s)
    elif weapon_type == 'Axe':
        with open('Axe-Script.txt', 'w') as s:
            write_script(melee_script, s)
    elif weapon_type == 'Handaxe':
        with open('RangedAxe-Script.txt', 'w') as s:
            write_script(ranged_script, s)
    elif weapon_type == 'Bow':
        with open('RangedBow-Script.txt', 'w') as s:
            write_script(ranged_script, s)
    elif weapon_type == 'Disarmed':
        # only need stand and dodge frames
        unarmed_script = {pose: line_list for pose, line_list in melee_script.items() if pose in ('Stand', 'Dodge')}
        with open('Unarmed-Script.txt', 'w') as s:
            write_script(unarmed_script, s)
    elif weapon_type == 'Magic':
        with open('Magic-Script.txt', 'w') as s:
            write_script(ranged_script, s)
        unarmed_script = {pose: line_list for pose, line_list in ranged_script.items() if pose in ('Stand', 'Dodge')}
        with open('Unarmed-Script.txt', 'w') as s:
            write_script(unarmed_script, s)

    return melee_images, ranged_images

images = glob.glob('*.png')
script = glob.glob('*.txt')

if len(script) == 1:
    script = script[0]
elif len(script) == 0:
    raise ValueError("No script file present in current directory!")
else:
    raise ValueError("Could not determine which *.txt file to use!")

weapon_types = {'Sword', 'Lance', 'Axe', 'Disarmed', 'Handaxe', 'Bow', 'Magic'}
weapon_type = script[:-4]
if weapon_type not in weapon_types:
    raise ValueError("%s not a currently supported weapon type!" % weapon_type)

# Convert to images
images = {name[:-4]: Image.open(name) for name in images}

# Convert to GBA Colors
images = {name: convert_gba(image.convert('RGB')) for name, image in images.items()}

def simple_crop(image):
    if image.width == 248:
        image = image.crop((0, 0, 240, image.height))
    elif image.width == 488:
        image = image.crop((0, 0, 480, image.height))
    return image
# If width of image == 248, clip last 8 pixels
images = {name: simple_crop(image) for name, image in images.items()}

# If double image, create one as under image instead
new_images = {}
for name in images.keys():
    image = images[name]
    if image.width == 480:
        image1 = image.crop((0, 0, 240, image.height))
        image2 = image.crop((240, 0, 480, image.height))
        new_images[name] = image1
        if image1 != image2:
            new_images[name + '_under'] = image2
images.update(new_images)

bg_color = determine_bg_color(images.values()[0])

melee_image_names, ranged_image_names = write_scripts(script, images, weapon_type)
melee_images = OrderedDict()
ranged_images = OrderedDict()
for name, image in sorted(images.items()):
    if name in melee_image_names:
        melee_images[name] = image
    if name in ranged_image_names:
        ranged_images[name] = image

# Preprocess
def preprocess(images):
    for name, image in images.items():
        width, height = image.size

        # Convert colorkey colors to 0, 0, 0
        for x in xrange(width):
            for y in xrange(height):
                color = image.getpixel((x, y))
                if color == (0, 0, 0):
                    image.putpixel((x, y), (40, 40, 40))

preprocess(melee_images)
preprocess(ranged_images)

# Once done with building script for melee and ranged, make an image collater
# Create image and index script
if weapon_type == 'Disarmed':
    weapon_type = 'Unarmed'
if weapon_type == 'Handaxe':
    weapon_type = 'Axe'
if weapon_type not in ('Bow', 'Magic'):
    animation_collater(melee_images, bg_color, weapon_type)
if weapon_type == 'Magic':
    animation_collater(melee_images, bg_color, 'Unarmed')
if ranged_images:
    if weapon_type == 'Sword':
        animation_collater(ranged_images, bg_color, 'Magic' + weapon_type)
    elif weapon_type in ('Lance', 'Axe', 'Bow'):
        animation_collater(ranged_images, bg_color, 'Ranged' + weapon_type)
    elif weapon_type == 'Magic':
        animation_collater(ranged_images, bg_color, 'Magic')

print(' === Done! ===')
