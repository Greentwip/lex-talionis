import os
import Engine

class BattleAnimationManager(object):
    def __init__(self, COLORKEY):
        self.generated_klasses = set()
        self.directory = {}
        for root, dirs, files in os.walk('./Data/Animations/'):
            for name in files:
                klass, weapon, desc = name.split('-')
                #print(klass, weapon, desc)
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

    def generate(self, klass):
        if klass in self.directory and klass not in self.generated_klasses:
            klass_directory = self.directory[klass]
            self.generated_klasses.add(klass) # Don't generate twice

            for weapon in klass_directory:
                frame_directory = {}
                for name, anim in klass_directory[weapon]['images'].iteritems():
                    frame_directory[name] = self.format_index(klass_directory[weapon]['index'], anim)
                #print(frame_directory)
                klass_directory[weapon]['images'] = frame_directory
                klass_directory[weapon]['script'] = self.parse_script(klass_directory[weapon]['script'])

    def partake(self, unit, item=None, magic=False):
        if unit.klass in self.directory:
            self.generate(unit.klass)
            if not item:
                weapon = 'Unarmed'
            elif magic:
                weapon = 'Magic' + item.spritetype
            elif max(item.RNG) > 1:
                weapon = 'Ranged' + item.spritetype
            else:
                weapon = item.spritetype
            if weapon in self.directory[unit.klass]:
                return self.directory[unit.klass][weapon]
            else:
                return None
        else:
            return None

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
                poses[line[1]] = []
            else:
                poses[current_pose].append(line)
        return poses