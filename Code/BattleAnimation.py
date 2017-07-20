from GlobalConstants import *
import Engine
# Mode types:
#* Attack 
#* Attack2 - behind
# Critical
# Critical2 - behind
#* Miss
#* Dodge
#* RangedDodge
#* Stand
#* RangedStand

class BattleAnimation(object):
    loop_set = {'Stand', 'RangedStand'}
    def __init__(self, anim, script):
        self.frame_directory = anim
        self.poses = script
        self.current_pose = None
        self.state = 'Inert' # Internal state
        self.tag = None # For others to read
        self.num_frames = 0 # How long this frame of animation should exist for (in frames)

    def awake(self, partner, right, at_range):
        self.partner = partner
        self.right = right
        self.at_range = at_range
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
        self.script_index = 0
        self.processing = True
        self.reset()

    def update(self):
        if self.state == 'Run':
            if self.frame_count >= self.num_frames:
                self.processing = True
                self.read_script()
            if self.script_index >= len(self.poses[self.current_pose]):
                # check whether we should loop or truly end
                if self.current_pose in self.loop_set:
                    self.script_index = 0
                else:
                    self.end_current()
            self.frame_count += 1
        elif self.state == 'Wait':
            pass

    def end_current(self):
        self.current_pose = 'RandgedStand' if self.at_range else 'Stand'
        self.state = 'Run'
        self.script_index = 0
        self.tag = 'Done'

    def read_script(self):
        script = self.poses[self.current_pose]
        while(self.script_index < len(script) and self.processing):
            line = script[self.script_index]
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
            self.tag = 'HP'

    def start_anim(self, pose):
        self.current_pose = pose
        self.script_index = 0
        self.reset()

    def resume(self):
        self.reset()

    def reset(self):
        self.state = 'Run'
        self.tag = None
        self.frame_count = 0

    def draw(self, surf):
        if self.state != 'Inert':
            image = self.current_frame[0].copy()
            if not self.right:
                image = Engine.flip_horiz(image)
            offset = self.current_frame[1]
            if not self.right:
                offset = WINWIDTH - offset[0] - image.get_width(), offset[1]
            surf.blit(image, offset)

    def draw_under(self, surf):
        pass
