# FERepo to Lex Talionis Format for Full Combat Animations
# Takes in FERepo data... a set of images along with a *.txt file that serves as the script.

import os, sys, glob, datetime
from collections import OrderedDict, Counter
from PIL import Image

COLORKEY = 128, 160, 128
WIDTH_LIMIT = 240 * 5

class Logger(object):
    def __init__(self, name, mode):
        self.log = open(name, mode)
        self.stdout = sys.stdout
        sys.stdout = self
        self.stderr = sys.stderr
        sys.stderr = self

        self.write(str(datetime.datetime.now()) + '\n')

    def __del__(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.log.close()

    def write(self, data):
        self.log.write(data)
        self.stdout.write(data)
        # self.stderr.write(data)

    def flush(self):
        self.log.flush()

def convert_gba(im):
    width, height = im.size
    for x in range(width):
        for y in range(height):
            color = im.getpixel((x, y))
            new_color = (color[0] // 8 * 8), (color[1] // 8 * 8), (color[2] // 8 * 8)
            im.putpixel((x, y), new_color)
    return im

def determine_bg_color(im):
    color = im.getpixel((0, 0))
    return color

def determine_bg_color_slow(im):
    colors = Counter()
    width, height = image.size
    for w in range(width):
        for h in range(height):
            color = im.getpixel((w, h))
            colors[color] += 1
    return colors.most_common()[0][0]

def animation_collater(images, weapon_type):
    bad_images = set()
    index_lines = []
    for name, image in images.items():
        width, height = image.size
        bg_color = determine_bg_color(image)

        # Convert colorkey colors to 0, 0, 0
        for x in range(width):
            for y in range(height):
                color = image.getpixel((x, y))
                if color == bg_color:
                    image.putpixel((x, y), (0, 0, 0))

        # Now get bbox
        bbox = image.getbbox()
        if not bbox:
            print('%s is a bad image. Replacing with "wait" in script' % name)
            bad_images.add(name)
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
    for x in range(total_width):
        for y in range(max_height):
            color = sprite_sheet.getpixel((x, y))
            if color == (0, 0, 0):
                sprite_sheet.putpixel((x, y), COLORKEY)

    sprite_sheet.save(weapon_type + '-GenericBlue.png')
    index_script.close()

    return bad_images

class Pose(list):
    def append(self, obj):
        if isinstance(obj, Frame) and self and isinstance(self[-1], Frame) and obj.name == self[-1].name:
            self[-1].length += obj.length
        else:
            super(Pose, self).append(obj)

class Frame(object):
    def __init__(self, name, length, used_names, over=False):
        self.name = name
        self.length = length
        self.over = over

        if (self.name + '_under') in images:
            used_names.add(self.name + '_under')
        used_names.add(self.name)

    def __str__(self):
        if self.over:
            command = 'of'
        else:
            command = 'f'
        if (self.name + '_under') in images:
            ret = '%s;%d;%s;%s_under' % (command, self.length, self.name, self.name)
        else:
            ret = '%s;%d;%s' % (command, self.length, self.name)
        return ret

class WaitForHit(object):
    def __init__(self, name, used_names):
        self.name = name

        if (self.name + '_under') in images:
            used_names.add(self.name + '_under')
        used_names.add(self.name)

    def __str__(self):
        if (self.name + '_under') in images:
            ret = 'wait_for_hit;%s;%s_under' % (self.name, self.name)
        else:
            ret = 'wait_for_hit;%s' % self.name
        return ret

class Sound(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'sound;%s' % self.name

class Effect(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'effect;%s' % self.name

class DodgeStart(object):
    def __init__(self):
        pass

    def __str__(self):
        return ''

class Loop(object):
    def __init__(self, end):
        self.end = end

    def __str__(self):
        return 'end_loop' if self.end else 'start_loop'

def parse_script(script, images, weapon_type):
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

    def save_mode(mode):
        if weapon_type in ('Magic', 'Staff', 'Refresh'):
            if mode not in (5, 6, 7, 9, 11):
                used_names.clear()
                return
        if weapon_type in ('Transform', 'Revert'):
            if mode not in (1, 9, 11):
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
                current_pose = Pose()  # New current pose
                throwing_axe = False
                current_frame = None
                dodge_front = False
                shield_toss = False
                l_loop_start = False
            else:
                break  # Done

        elif line.startswith('C'):
            command_code = line[1:3]
            write_extra_frame = True
            if command_code == '01':
                if throwing_axe:
                    current_pose.append(Loop(0))
                    current_pose.append(Frame(current_frame, 1, used_names))
                    current_pose.append(Loop(1))
                    current_pose.append(Frame(current_frame, 8, used_names))
                elif l_loop_start:
                    current_pose.append(Loop(1))
                    l_loop_start = False
                elif current_mode == 12:  # Miss
                    current_pose.append(Frame(current_frame, 1, used_names))
                    current_pose.append('miss')
                    current_pose.append(Frame(current_frame, 30, used_names))
                elif current_mode == 5 or current_mode == 6:  # Ranged
                    current_pose.append(Loop(0))
                    current_pose.append(Frame(current_frame, 4, used_names))
                    current_pose.append(Loop(1))
                    current_pose.append(Frame(current_frame, 4, used_names))
                elif current_mode == 7 or current_mode == 8:  # Dodge
                    # Count number of frames already written to the dodge
                    cur_index = len(current_pose) - 1
                    cur = current_pose[cur_index]
                    counter = 0
                    while not isinstance(cur, DodgeStart):
                        if isinstance(cur, Frame):
                            counter += cur.length
                        cur_index -= 1
                        if cur_index < 0:
                            break
                        cur = current_pose[cur_index]
                    # 30 frames in a dodge
                    current_pose.append(Frame(current_frame, 30 - counter, used_names, over=dodge_front))
                elif current_mode in (1, 2, 3, 4):
                    current_pose.append(WaitForHit(current_frame, used_names))
                    if shield_toss:
                        current_pose.append('end_child_loop')
                    else:
                        current_pose.append(Frame(current_frame, 4, used_names))
                elif current_mode in (9, 10, 11):
                    current_pose.append(Frame(current_frame, 3, used_names))
                write_extra_frame = False  # 01 does not drop 1 frame after it runs
            elif command_code == '02':
                write_extra_frame = False  # Normally says this is a dodge, but that doesn't matter
            elif command_code == '03':
                begin = True
            elif command_code == '04':
                write_extra_frame = False  # Normally prepares some code for returning to stand
            elif command_code == '05':  # Start spell
                if weapon_type in ('Sword', 'Magic', 'Staff', 'Neutral', 'Refresh', 'Dragonstone'):
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
                if current_frame:
                    current_pose.append(Frame(current_frame, 1, used_names))
                current_pose.append('foreground_blend;2;248,248,248')
                start_hit = True
                write_extra_frame = False
            elif command_code == '0D':  # End
                current_pose.append(Frame(current_frame, 1, used_names))
                write_extra_frame = False
            elif command_code == '0E':  # Dodge
                current_pose.append(DodgeStart())
                write_extra_frame = False
            elif command_code == '13':
                current_pose.append(Loop(0))
                current_pose.append(Frame(current_frame, 1, used_names))
                current_pose.append(Loop(1))
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
                if current_frame:
                    current_pose.append(Frame(current_frame, 1, used_names))
                current_pose.append('screen_flash_white;4')
                start_hit = True
            elif command_code in ('1F', '20', '21'):  # Actual hit
                write_extra_frame = False
            # Sounds and other effects
            elif command_code == '19':
                current_pose.append(Sound('Bow'))
            elif command_code == '1B':
                current_pose.append(Sound('Foot Step'))
            elif command_code == '1C':
                current_pose.append(Sound('Horse Step 1'))
            elif command_code == '1D':
                current_pose.append(Sound('Horse Step 3'))
            elif command_code == '1E':
                current_pose.append(Sound('Horse Step 2'))
            elif command_code == '22':
                current_pose.append(Sound('Weapon Pull'))
            elif command_code == '23':
                current_pose.append(Sound('Weapon Push'))
            elif command_code == '24':
                current_pose.append(Sound('Weapon Swing'))
            elif command_code == '25':
                current_pose.append(Sound('Heavy Wing Flap'))
            elif command_code == '26' or command_code == '27':
                current_pose.append(Effect('ShieldToss'))
                shield_toss = True
            elif command_code == '28':
                current_pose.append(Sound('ShamanRune'))
            elif command_code == '2B':
                current_pose.append(Sound('ArmorShift'))
            elif command_code == '2E':
                current_pose.append(Effect('MageInit'))
                print('Change "effect;MageInit" to "effect;SageInit" if working with Sage animations')
            elif command_code == '2F':
                current_pose.append(Effect('MageCrit'))
                print('Change "effect;MageCrit" to "effect;SageCrit" if working with Sage animations')
            elif command_code == '30':
                current_pose.append('effect;DirtKick')
            elif command_code == '33':
                current_pose.append(Sound('Battle Cry'))
            elif command_code == '34':
                current_pose.append(Sound('Step Back 1'))
            elif command_code == '35':
                current_pose.append(Sound('Long Wing Flap'))
            elif command_code == '36':
                current_pose.append(Sound('Unsheathe'))
            elif command_code == '37':
                current_pose.append(Sound('Sheathe'))
            elif command_code == '38':
                current_pose.append(Sound('Heavy Spear Spin'))
            elif command_code == '3A':
                current_pose.append(Sound('RefreshDance'))
            elif command_code == '3B':
                current_pose.append(Sound('RefreshFlute'))
            elif command_code == '3C':
                current_pose.append(Sound('Sword Whoosh'))
            elif command_code == '41':
                current_pose.append(Sound('Axe Pull'))
            elif command_code == '42':
                current_pose.append(Sound('Axe Push'))
            elif command_code == '43':
                current_pose.append(Sound('Weapon Click'))
            elif command_code == '44':
                current_pose.append(Sound('Weapon Shine'))
            elif command_code == '45':
                current_pose.append(Sound('Neigh'))
            elif command_code == '47':
                current_pose.append(Effect('Cape Animation'))
                print('Replace "effect;Cape Animation" with actual frames for cape animation in a loop')
                print("For instance:")
                print("start_loop")
                print("    f;3;Magic033")
                print("    f;3;Magic034")
                print("end_loop")
            elif command_code == '49':
                current_pose.append(Sound('SageRune'))
            elif command_code == '4B':
                current_pose.append(Sound('MonkRune'))
            elif command_code == '4F':
                current_pose.append(Sound('DruidCrit'))
            elif command_code == '51':
                current_pose.append('screen_flash_white;4')
            elif command_code == '5A':
                current_pose.append(Sound('MautheDoogGrowl'))
            elif command_code == '5B':
                current_pose.append(Sound('MautheDoogBark'))
            elif command_code == '5C':
                current_pose.append(Sound('MautheDoogHowl'))
            elif command_code == '5D':
                current_pose.append(Sound('MautheDoogWalk'))
            elif command_code == '79':
                current_pose.append(Sound('StrategistRune'))
            elif command_code == '7A':
                current_pose.append(Sound('StrategistCrit'))
            elif command_code == '7B':
                current_pose.append(Sound('ManaketeRoar'))
            else:
                print('Unknown Command Code: C%s' % command_code)
            
            if write_extra_frame and current_frame:
                current_pose.append(Frame(current_frame, 1, used_names, over=dodge_front))
            
        elif line.startswith('~~~'):
            pass

        elif line == 'L':
            current_pose.append(Loop(0))
            l_loop_start = True

        elif line.startswith('S'):
            print('Cannot parse "%s"! Skipping over this line...' % line)

        else:
            try:
                num_frames, _, png_name = line.split()
            except ValueError:
                print('Cannot parse "%s"! Skipping over this line...' % line)
                continue
            num_frames = int(num_frames)
            name = png_name[:-4]
            if name not in images:
                raise ValueError('%s frame not in images!' % name)
            if begin:
                num_frames = 6
                begin = False
            current_frame = name
            if not (start_hit and crit):  # Don't write this frame if we're starting a crit
                current_pose.append(Frame(current_frame, num_frames, used_names, over=dodge_front))
            if start_hit:
                if crit:
                    current_pose.append('start_hit')
                    current_pose.append(Frame(current_frame, 2, used_names))
                    current_pose.append('crit_spark')
                else:
                    current_pose.append(Frame(current_frame, 2, used_names))
                    current_pose.append('hit_spark')
                    current_pose.append('start_hit')
                start_hit = False

    return melee_script, melee_images, ranged_script, ranged_images

def write_script(weapon_type, melee_script, ranged_script):
    def write_script(script, s):
        for pose, line_list in script.items():
            s.write('pose;' + pose + '\n')
            for line in line_list:
                if str(line):
                    s.write(str(line) + '\n')                    
            s.write('\n')

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
    elif weapon_type == 'Unarmed':
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
    elif weapon_type == 'Staff':
        with open('MagicStaff-Script.txt', 'w') as s:
            write_script(ranged_script, s)
    elif weapon_type == 'Neutral':
        with open('Neutral-Script.txt', 'w') as s:
            write_script(melee_script, s)
        with open('RangedNeutral-Script.txt', 'w') as s:
            write_script(ranged_script, s)
        unarmed_script = {pose: line_list for pose, line_list in melee_script.items() if pose in ('Stand', 'Dodge')}
        with open('Unarmed-Script.txt', 'w') as s:
            write_script(unarmed_script, s)
    elif weapon_type == 'Dragonstone':
        with open('Dragonstone-Script.txt', 'w') as s:
            write_script(ranged_script, s)
    elif weapon_type == 'Refresh':
        with open('Refresh-Script.txt', 'w') as s:
            write_script(ranged_script, s)
        unarmed_script = {pose: line_list for pose, line_list in melee_script.items() if pose in ('Stand', 'Dodge')}
        with open('Unarmed-Script.txt', 'w') as s:
            write_script(unarmed_script, s)

# === START ==================================================================
log = Logger('fe_repo_to_lex.log', 'a')

images = glob.glob('*.png')
script = glob.glob('*.txt')

if 'Transform.txt' in script:
    script.remove('Transform.txt')
if 'Revert.txt' in script:
    script.remove('Revert.txt')
if len(script) == 2:
    if script[0].endswith('_without_comment.txt'):
        script = script[1]
    elif script[1].endswith('_without_comment.txt'):
        script = script[0]
    else:
        raise ValueError("Could not determine which *.txt file to use! %s" % script)
elif len(script) == 1:
    script = script[0]
elif len(script) == 0:
    raise ValueError("No script file present in current directory!")
else:
    raise ValueError("Could not determine which *.txt file to use! %s" % script)

weapon_types = {'Sword', 'Lance', 'Axe', 'Disarmed', 'Unarmed', 'Handaxe',
                'Bow', 'Magic', 'Staff', 'Monster', 'Dragonstone', 'Refresh'}
weapon_type = script[:-4]
if weapon_type not in weapon_types:
    raise ValueError("%s not a currently supported weapon type!" % weapon_type)

if weapon_type == 'Disarmed':
    weapon_type = 'Unarmed'
if weapon_type == 'Monster':
    weapon_type = 'Neutral'

print("Converting %s to Lex Talionis format..." % script)

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

melee_script, melee_image_names, ranged_script, ranged_image_names = \
    parse_script(script, images, weapon_type)

# Extra transform and revert poses for Dragonstone
if weapon_type == 'Dragonstone' and os.path.exists('Transform.txt'):
    transform_script, transform_image_names, _, _ = parse_script('Transform.txt', images, 'Transform')
    ranged_script['Transform'] = transform_script['Attack']
    # Change stand
    ranged_script['TransformStand'] = ranged_script['Stand']
    ranged_script['Stand'] = transform_script['Stand']
    ranged_image_names.update(transform_image_names)

    revert_script, revert_image_names, _, _ = parse_script('Revert.txt', images, 'Revert')
    ranged_script['Revert'] = revert_script['Attack']
    ranged_image_names.update(revert_image_names)

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
        for x in range(width):
            for y in range(height):
                color = image.getpixel((x, y))
                if color == (0, 0, 0):
                    image.putpixel((x, y), (40, 40, 40))

preprocess(melee_images)
preprocess(ranged_images)

# Once done with building script for melee and ranged, make an image collater
# Create image and index script
bad_images = set()
if weapon_type not in ('Bow', 'Magic', 'Staff', 'Refresh', 'Dragonstone', 'Handaxe'):
    bad_images |= animation_collater(melee_images, weapon_type)
if weapon_type in ('Magic', 'Refresh'):
    bad_images |= animation_collater(melee_images, 'Unarmed')
if weapon_type == 'Neutral':
    bad_images |= animation_collater(ranged_images, 'Unarmed')
if ranged_images:
    if weapon_type == 'Sword':
        bad_images |= animation_collater(ranged_images, 'Magic' + weapon_type)
    elif weapon_type in ('Lance', 'Axe', 'Bow', 'Neutral'):
        bad_images |= animation_collater(ranged_images, 'Ranged' + weapon_type)
    elif weapon_type == 'Handaxe':
        bad_images |= animation_collater(ranged_images, 'RangedAxe')
    elif weapon_type in ('Magic', 'Refresh', 'Dragonstone'):
        bad_images |= animation_collater(ranged_images, weapon_type)
    elif weapon_type == 'Staff':
        bad_images |= animation_collater(ranged_images, 'MagicStaff')

def replace_bad_images(script, bad_images):
    for pose, line_list in script.items():
        for idx, command in enumerate(line_list):
            if isinstance(command, Frame) and command.name in bad_images:
                line_list[idx] = 'wait;%d' % command.length
            elif isinstance(command, WaitForHit) and command.name in bad_images:
                line_list[idx] = 'wait_for_hit'

if bad_images:
    replace_bad_images(melee_script, bad_images)
    replace_bad_images(ranged_script, bad_images)

# Actually write the script
write_script(weapon_type, melee_script, ranged_script)

print(' === Done! ===')
