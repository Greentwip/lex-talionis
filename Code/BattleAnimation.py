from GlobalConstants import *
import Engine, Image_Modification
import CustomObjects
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
        self.animations = []

        # flash frames
        self.foreground = None
        self.foreground_frames = 0
        self.flash_color = None
        self.flash_frames = 0

    def awake(self, owner, partner, right, at_range):
        self.owner = owner
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
        #print('Animation: End Current')
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
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
            self.current_frame = self.frame_directory[line[1]]
            self.state = 'Wait'
            self.processing = False
            self.tag = 'HP'
            self.owner.shake(1)
        elif line[0] == 'enemy_flash_white':
            num_frames = int(line[1])
            self.partner.flash(num_frames, (248, 248, 248))
        elif line[0] == 'screen_flash_white':
            self.foreground_frames = int(line[1])
            self.foreground = IMAGESDICT['BlackBackground'].copy()
            self.foreground.fill((248, 248, 248))
        elif line[0] == 'hit_spark':
            if self.right:
                position = (-110, -30)
            else:
                position = (-40, -30) # Enemy's position
            image = IMAGESDICT['HitSparkTrans']
            anim = CustomObjects.Animation(image, position, (3, 5), 14, ignore_map=True, 
                                          set_timing=(2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1))
            self.animations.append(anim)

    def start_anim(self, pose):
        #print('Animation: Start')
        self.current_pose = pose
        self.script_index = 0
        self.reset()

    def resume(self):
        #print('Animation: Resume')
        self.reset()

    def reset(self):
        self.state = 'Run'
        self.tag = None
        self.frame_count = 0
        self.num_frames = 0

    def flash(self, num, color):
        self.flash_frames = num
        self.flash_color = color

    def draw(self, surf, shake=(0, 0)):
        if self.state != 'Inert':
            image = self.current_frame[0].copy()
            if not self.right:
                image = Engine.flip_horiz(image)
            offset = self.current_frame[1]
            if not self.right:
                offset = WINWIDTH - offset[0] - image.get_width() + shake[0], offset[1] + shake[1]

            # Self flash
            if self.flash_color:
                image = Image_Modification.flicker_image(image.convert_alpha(), self.flash_color)
                self.flash_frames -= 1
                # If done
                if self.flash_frames <= 0:
                    self.flash_color = None
                    self.flash_frames = 0

            surf.blit(image, offset)

            # Update and draw animations
            self.animations = [animation for animation in self.animations if not animation.update()]
            for animation in self.animations:
                animation.draw(surf)

            # Screen flash
            if self.foreground:
                surf.blit(self.foreground, (0, 0))
                self.foreground_frames -= 1
                # If done
                if self.flash_frames <= 0:
                    self.foreground = None
                    self.foreground_frames = 0

    def draw_under(self, surf, shake=(0, 0)):
        pass
