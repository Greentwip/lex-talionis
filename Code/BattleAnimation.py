from GlobalConstants import *
import Engine
# Mode types:
#* Attack 
#* Attack2 - behind
# Critical
# Critical2 - behind
#* Miss
#* Spell
# CriticalSpell
#* Dodge
#* RangedDodge
#* Stand
#* RangedStand

class BattleAnimation(object):
    loop_set = {'Stand', 'RangedStand'}
    def __init__(self, unit):
        self.unit = unit
        self.active = False
        self.current_mode = None
        self.state = 'Inert'
        self.processing = True
        self.modes = {}
        self.loadSprites()
    
    def loadSprites():
        image_name = unit.klass + '-' + unit.name
        if unit.team == 'player':
            color = 'Blue'
        else:
            color = 'Red'
        generic_image_name = unit.klass + '-Generic' + color
        if image_name in ANIMDICT['image']:
            anim = ANIMDICT['image'][image_name]
        elif generic_image_name in ANIMDICT:
            anim = ANIMDICT['image'][image_name]
        else:
            self.indexing = None
            self.animation = None
            self.script = None
            return
        self.indexing = ANIMDICT['index'][unit.klass] # Converts image of animations to frames
        self.animation = anim # Actual image of animations
        self.script = ANIMDICT['script'][unit.klass] # Script that controls animations
        self.parse_script(self.script)

    def parse_script(self, script):
        all_lines = []
        with open(script) as fp:
            all_lines = [line.strip().split(';') for line in fp.readlines() if not line.startswith('#')]

        for line in all_lines:
            if line[0] == 'mode':
                self.current_mode = line[1]
                self.modes[line[1]] = []
            else:
                self.modes[self.current_mode].append(line)

    def awake(self, partner, right, at_range):
        self.partner = partner
        self.right = right
        self.at_range = at_range
        self.current_mode = 'RangedStand' if self.at_range else 'Stand'
        self.script_index = 0
        self.state = 'Run'

    def update(self):
        if self.state == 'Run':
            self.frame_count += 1
            if self.frame_count >= self.num_frames:
                self.processing = True
                self.read_script()
                if self.state == 'Wait':
                    return 'HP'
            if self.script_index >= len(self.modes[self.current_mode]):
                # check whether we should loop or truly end
                if self.current_mode in self.loop_set:
                    self.script_index = 0
                else:
                    self.end_current()
                    return 'Done'
        elif self.state == 'Wait':
            pass

    def end_current(self):
        self.current_mode = 'RandgedStand' if self.at_range else 'Stand'
        self.state = 'Run'
        self.script_index = 0

    def read_script(self):
        while(self.script_index < len(self.modes[self.current_mode]) and self.processing):
            line = self.modes[self.current_mode[self.script_index]]
            self.parse_line(line)
            self.script_index += 1

    def parse_line(self, line):
        if line[0] == 'f':
            self.frame_count = 0
            self.num_frames = int(line[1])
            self.current_frame = self.frame_directory[line[2]]
            self.processing = False
        elif line[0] == 'sound':
            SOUNDDICT[line[1]].play()
        elif line[0] == 'hit':
            self.state = 'Wait'
            self.processing = False

    def start_anim(self, mode):
        self.current_mode = mode
        self.state = 'Run'
        self.script_index = 0

    def resume(self):
        self.state = 'Run'

    def draw(self, surf):
        if self.state != 'Inert':
            image = self.current_frame.image.copy()
            if not self.right:
                image = Engine.flip_horiz(image)
            offset = self.current_frame.offset
            if not self.right:
                offset = WINWIDTH - offset[0], offset[1]
            surf.blit(image, offset)

    def draw_under(self, surf):
        pass
