import os
import Engine

class BattleAnimationManager(object):
    def __init__(self, COLORKEY, home='./'):
        self.generated_klasses = set()
        # Class Animations
        self.directory = {}
        for root, dirs, files in os.walk(home + 'Data/Animations/'):
            for name in files:
                klass, weapon, desc = name.split('-')
                if klass not in self.directory:
                    self.directory[klass] = {}
                if weapon not in self.directory[klass]:
                    self.directory[klass][weapon] = {}
                    self.directory[klass][weapon]['images'] = {}
                full_name = os.path.join(root, name)
                if name.endswith('.png'):
                    image = Engine.image_load(full_name, convert=True)
                    Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                    self.directory[klass][weapon]['images'][desc[:-4]] = image
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
                if effect not in self.effects:
                    self.effects[effect] = {}
                full_name = os.path.join(root, name)
                if name.endswith('.png'):
                    image = Engine.image_load(full_name, convert_alpha=True)
                    self.effects[effect]['image'] = image
                elif name.endswith('Script.txt'):
                    self.effects[effect]['script'] = full_name
                elif name.endswith('Index.txt'):
                    self.effects[effect]['index'] = full_name

    def generate(self, klass):
        if klass in self.directory and klass not in self.generated_klasses:
            klass_directory = self.directory[klass]
            self.generated_klasses.add(klass) # Don't generate twice

            for weapon in klass_directory:
                frame_directory = {}
                for name, anim in klass_directory[weapon]['images'].iteritems():
                    frame_directory[name] = self.format_index(klass_directory[weapon]['index'], anim)
                # print(frame_directory)
                klass_directory[weapon]['images'] = frame_directory
                klass_directory[weapon]['script'] = self.parse_script(klass_directory[weapon]['script'])

    def generate_effect(self, effect):
        if effect in self.effects and effect not in self.generated_effects:
            self.generated_effects.add(effect)
            e_dict = self.effects[effect]
            if 'image' in e_dict:
                e_dict['image'] = self.format_index(e_dict['index'], e_dict['image'])
            else:
                e_dict['image'] = None
            e_dict['script'] = self.parse_script(e_dict['script'])

    def partake(self, klass, gender=0, item=None, magic=False, distance=1):
        klass = klass + str(gender)
        if klass in self.directory:
            self.generate(klass)
            check_item = False
            if not item:
                weapon = 'Unarmed'
            elif magic:
                weapon = 'Magic' + item.spritetype
                check_item = True # Make sure that we have the spell also
            elif max(item.RNG) > 1 and (item.spritetype != 'Lance' or distance > 1):
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

    def get_effect(self, effect):
        if effect in self.effects:
            self.generate_effect(effect)
            #print(self.effects[effect]['script'])
            return self.effects[effect]['image'], self.effects[effect]['script']
        else:
            print('Effect %s not found in self.effects!'%(effect))
            return None, None

    def format_index(self, index, anim):
        frame_directory = {}
        index_lines = []
        with open(index) as fp:
            index_lines = [line.strip().split(';') for line in fp.readlines()]

        for line in index_lines:
            name = line[0]
            x, y = (int(num) for num in line[1].split(','))
            width, height = (int(num) for num in line[2].split(','))
            offset = tuple(int(num) for num in line[3].split(','))
            image = Engine.subsurface(anim, (x, y, width, height))
            frame_directory[name] = (image, offset)
        return frame_directory

    def parse_script(self, script):
        all_lines = []
        with open(script) as fp:
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
        return poses
