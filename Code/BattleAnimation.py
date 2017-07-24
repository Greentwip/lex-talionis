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
        # Opacity
        self.opacity = 255

    def awake(self, owner, partner, right, at_range, init_speed, init_position):
        self.owner = owner
        self.partner = partner
        self.right = right
        self.at_range = at_range
        self.init_speed = init_speed
        self.entrance = init_speed
        self.init_position = init_position
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
        self.script_index = 0
        #self.processing = True
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
            if self.entrance:
                self.entrance -= 1
        elif self.state == 'Dying':
            if self.death_opacity:
                opacity = self.death_opacity.pop()
                if opacity == -1:
                    opacity = 255
                    self.flash_color = (248, 248, 248)
                    self.flash_frames = 100 # Just a lot
                self.opacity = opacity
            else:
                self.state = 'Inert'
        elif self.state == 'Leaving':
            self.entrance += 1
            if self.entrance > self.init_speed:
                self.entrance = self.init_speed
                self.state = 'Inert' # Done
        elif self.state == 'Wait':
            pass

    def end_current(self):
        #print('Animation: End Current')
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
        self.state = 'Run'
        self.script_index = 0

    def finish(self):
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
        self.state = 'Leaving'
        self.script_index = 0

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
            if self.owner.current_result.def_damage > 0:
                self.owner.shake(1)
            else: # No Damage
                self.owner.shake(2)
        elif line[0] == 'enemy_flash_white':
            num_frames = int(line[1])
            self.partner.flash(num_frames, (248, 248, 248))
        elif line[0] == 'screen_flash_white':
            self.foreground_frames = int(line[1])
            self.foreground = IMAGESDICT['BlackBackground'].copy()
            self.foreground.fill((248, 248, 248))
        elif line[0] == 'hit_spark':
            if self.owner.current_result.def_damage > 0:
                if self.right:
                    position = (-110, -30)
                else:
                    position = (-40, -30) # Enemy's position
                image = IMAGESDICT['HitSparkTrans']
                anim = CustomObjects.Animation(image, position, (3, 5), 14, ignore_map=True, 
                                              set_timing=(2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1))
            else: # No Damage
                if self.right:
                    position = (52, 20)
                else:
                    position = (110, 20) # Enemy's position
                team = self.owner.right.team if self.right else self.owner.left.team
                image = IMAGESDICT['NoDamageBlue' if team == 'player' else 'NoDamageRed']
                anim = CustomObjects.Animation(image, position, (5, 5), ignore_map=True, 
                                              set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
                                                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                                          1, 1, 1, 1, 48))
            self.animations.append(anim)
        elif line[0] == 'miss':
            if self.right:
                position = (72, 20)
            else:
                position = (130, 20) # Enemy's position
            team = self.owner.right.team if self.right else self.owner.left.team
            image = IMAGESDICT['MissBlue' if team == 'player' else 'MissRed']
            anim = CustomObjects.Animation(image, position, (5, 4), ignore_map=True, 
                                          set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
                                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 23))
            self.animations.append(anim)
            self.partner.dodge()

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

    def dodge(self):
        if self.at_range:
            self.start_anim('RangedDodge')
        else:
            self.start_anim('Dodge')

    def flash(self, num, color):
        self.flash_frames = num
        self.flash_color = color

    def start_dying_animation(self):
        self.state == 'Dying'
        self.death_opacity = [0, 20, 20, 20, 20, 44, 44, 44, 44, 64,
                              64, 64, 64, 84, 84, 84, 108, 108, 108, 108, 
                              128, 128, 128, 128, 148, 148, 148, 148, 172, 172, 
                              172, 192, 192, 192, 192, 212, 212, 212, 212, 236,
                              236, 236, 236, 255, 255, 255, 0, 0, 0, 0,
                              0, 0, -1, 0, 0, 0, 0, 0, 0, 255, 
                              0, 0, 0, 0, 0, 0, 255, 0, 0, 0,
                              0, 0, 0, 255, 0, 0, 0, 0, 0, 0,
                              255, 0, 0, 0, 0, 0, 0]

    def draw(self, surf, shake=(0, 0)):
        if self.state != 'Inert':
            image = self.current_frame[0].copy()
            if not self.right:
                image = Engine.flip_horiz(image)
            offset = self.current_frame[1]
            if not self.right:
                offset = WINWIDTH - offset[0] - image.get_width() + shake[0], offset[1] + shake[1]

            # Move the animations in at the beginning and out at the end
            if self.entrance:
                progress = (self.init_speed - self.entrance)/float(self.init_speed)
                image = Engine.transform_scale(image, (int(progress*image.get_width()), int(progress*image.get_height())))
                diff_x = offset[0] - self.init_position[0]
                diff_y = offset[1] - self.init_position[1]
                offset = int(self.init_position[0] + progress*diff_x), int(self.init_position[1] + progress*diff_y)

            # Self flash
            if self.flash_color:
                image = Image_Modification.flicker_image(image.convert_alpha(), self.flash_color)
                self.flash_frames -= 1
                # If done
                if self.flash_frames <= 0:
                    self.flash_color = None
                    self.flash_frames = 0

            if self.opacity != 255:
                image = Image_Modification.flickerImageTranslucent255(image.convert_alpha(), self.opacity)

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
