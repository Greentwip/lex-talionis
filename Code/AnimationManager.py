import os

from . import Engine

class BattleAnimationManager(object):
    def __init__(self, COLORKEY, home='./'):
        self.COLORKEY = COLORKEY
        self.generated_klasses = set()
        # Class Animations
        self.directory = {}
        for root, dirs, files in os.walk(home + 'Data/Animations/'):
            for name in files:
                if not (name.endswith('.png') or name.endswith('.txt')):
                    continue
                try:
                    klass, weapon, desc = name.split('-')
                except ValueError as e:
                    print('%s: Error loading in %s' % (e, name))
                    continue
                if klass not in self.directory:
                    self.directory[klass] = {}
                if weapon not in self.directory[klass]:
                    self.directory[klass][weapon] = {}
                    self.directory[klass][weapon]['images'] = {}
                full_name = os.path.join(root, name)
                if name.endswith('.png'):
                    # image = Engine.image_load(full_name, convert=True)
                    # Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                    self.directory[klass][weapon]['images'][desc[:-4]] = full_name
                elif name.endswith('Script.txt'):
                    self.directory[klass][weapon]['script'] = full_name
                elif name.endswith('Index.txt'):
                    self.directory[klass][weapon]['index'] = full_name
        # Custom Spell Animations
        self.generated_effects = set()
        self.effects = {}
        for root, dirs, files in os.walk(home + 'Data/Effects/'):
            for name in files:
                try:
                    effect, desc = name.split('-')
                except ValueError:
                    print('Error loading in %s' % name)
                    continue
                if effect not in self.effects:
                    self.effects[effect] = {}
                    self.effects[effect]['images'] = {}
                full_name = os.path.join(root, name)
                if name.endswith('.png'):
                    # image = Engine.image_load(full_name, convert_alpha=True)
                    self.effects[effect]['images'][desc[:-4]] = full_name
                elif name.endswith('Script.txt'):
                    self.effects[effect]['script'] = full_name
                elif name.endswith('Index.txt'):
                    self.effects[effect]['index'] = full_name

    def generate(self, klass):
        if klass in self.directory and klass not in self.generated_klasses:
            klass_directory = self.directory[klass]
            for weapon in klass_directory:
                frame_directory = {}
                for name, anim in list(klass_directory[weapon]['images'].items()):
                    if 'index' not in klass_directory[weapon]:
                        return False
                    # If the animation has not been loaded before
                    if isinstance(anim, str):
                        anim = Engine.image_load(anim, convert=True)
                        Engine.set_colorkey(anim, self.COLORKEY, rleaccel=True)
                        klass_directory[weapon]['images'][name] = anim
                    frame_directory[name] = self.format_index(klass_directory[weapon]['index'], anim)
                # print(frame_directory)
                klass_directory[weapon]['images'] = frame_directory
                if 'script' in klass_directory[weapon]:
                    klass_directory[weapon]['script'] = self.parse_script(klass_directory[weapon]['script'])
                else: # Search default klass
                    default_script = self.directory[klass[:-1] + '0'][weapon]['script']
                    if isinstance(default_script, dict):  # Already parsed
                        klass_directory[weapon]['script'] = default_script
                    else:
                        klass_directory[weapon]['script'] = self.parse_script(default_script)
            
            self.generated_klasses.add(klass)  # Don't generate twice
        return True

    def generate_effect(self, effect):
        if effect in self.effects and effect not in self.generated_effects:
            self.generated_effects.add(effect)
            e_dict = self.effects[effect]
            frame_directory = {}
            for name, anim in e_dict['images'].items():
                if 'index' not in e_dict:
                    print("Error! Couldn't find index for %s!" % effect)
                    return False
                # If the effect has not been loaded before
                if isinstance(anim, str):
                    anim = Engine.image_load(anim, convert_alpha=True)
                    e_dict['images'][name] = anim
                frame_directory[name] = self.format_index(e_dict['index'], anim)
            e_dict['images'] = frame_directory
            e_dict['script'] = self.parse_script(e_dict['script'])

    def partake(self, klass, gender=0, item=None, magic=False, distance=1):
        klass = klass + str(gender)
        if klass not in self.directory:
            gender = (gender//5) * 5  # Get nearest default
            klass = klass[:-1] + str(gender)
        if klass in self.directory:
            if not self.generate(klass):
                return None
            check_item = False
            if not item:
                weapon = 'Unarmed'
            elif item.use_custom_anim:
                if item.use_custom_anim is True:
                    custom_id = item.id
                else:
                    custom_id = item.use_custom_anim
                if magic:
                    weapon = 'Magic' + custom_id
                elif item.is_ranged() and distance > 1:
                    weapon = 'Ranged' + custom_id
                else:
                    weapon = custom_id
            elif magic:
                weapon = 'Magic' + item.spritetype
                check_item = True # Make sure that we have the spell also
            elif item.is_ranged() and (item.spritetype != 'Lance' or distance > 1):
                # Ranged Lances use Melee animation if adjacent
                weapon = 'Ranged' + item.spritetype
            else:
                weapon = item.spritetype
            if weapon in self.directory[klass]:
                if check_item and item.id not in self.effects:
                    return None
                return self.directory[klass][weapon]
            else:
                return None
        else:
            return None

    def get_effect(self, effect, name=None):
        if effect in self.effects:
            self.generate_effect(effect)
            if not name or name not in self.effects[effect]['images']:
                name = 'Image'
            if name in self.effects[effect]['images']:
                return self.effects[effect]['images'][name], self.effects[effect]['script']
            else:
                return None, self.effects[effect]['script']
        else:
            print('Effect %s not found in self.effects!' % effect)
            return None, None

    def format_index(self, index, anim):
        frame_directory = {}
        index_lines = []
        # print(index)
        with open(index, mode='r', encoding='utf-8') as fp:
            index_lines = [line.strip().split(';') for line in fp.readlines()]

        for idx, line in enumerate(index_lines):
            name = line[0]
            x, y = (int(num) for num in line[1].split(','))
            width, height = (int(num) for num in line[2].split(','))
            offset = tuple(int(num) for num in line[3].split(','))
            # print(name, x, y, width, height)
            try:
                image = Engine.subsurface(anim, (x, y, width, height))
            except ValueError:
                raise ValueError("Subsurface read error. %s is telling the Engine to read from an area on the image that does not exist. Check line %s:" % (index, idx + 1), line)
            frame_directory[name] = (image, offset)
        return frame_directory

    def parse_script(self, script):
        with open(script, mode='r', encoding='utf-8') as fp:
            all_lines = [line.strip() for line in fp.readlines()]
            all_lines = [line.split(';') for line in all_lines if line and not line.startswith('#')]

        poses = {}
        current_pose = None
        for line in all_lines:
            if line[0] == 'pose':
                current_pose = line[1]
                if current_pose in poses:
                    print('Warning! Pose %s already present in %s'%(current_pose, script))
                poses[current_pose] = []
            elif line[0] == 'effect':
                effect = line[1]
                self.generate_effect(effect)
                poses[current_pose].append(line)
            else:
                poses[current_pose].append(line)
        # Duplicate for ranged and miss if not explicitly provided
        if 'RangedDodge' not in poses and 'Dodge' in poses:
            poses['RangedDodge'] = poses['Dodge']
        if 'RangedStand' not in poses and 'Stand' in poses:
            poses['RangedStand'] = poses['Stand']
        if 'Miss' not in poses and 'Attack' in poses:
            poses['Miss'] = poses['Attack']
        if 'Critical' not in poses and 'Attack' in poses:
            poses['Critical'] = poses['Attack']
        return poses
