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

class Loop(object):
    def __init__(self, start):
        self.start_index = start
        self.end_index = 0

class BattleAnimation(object):
    idle_poses = {'Stand', 'RangedStand'}
    def __init__(self, anim, script):
        self.frame_directory = anim
        self.poses = script
        self.current_pose = None
        self.state = 'Inert' # Internal state
        self.num_frames = 0 # How long this frame of animation should exist for (in frames)
        self.animations = []

        self.child_effect = None
        self.loop = False
        self.deferred_commands = []

        # For drawing
        self.blend = None
        # flash frames
        self.foreground = None
        self.foreground_frames = 0
        self.flash_color = None
        self.flash_frames = 0
        # Opacity
        self.opacity = 255
        # Offset
        self.static = False

    def awake(self, owner, partner, right, at_range, init_speed=None, init_position=None, parent=None):
        self.owner = owner
        self.partner = partner
        self.parent = parent if parent else self
        self.right = right
        self.at_range = at_range
        self.init_speed = init_speed
        self.entrance = init_speed
        self.init_position = init_position
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
        self.current_frame = None
        self.under_frame = None
        self.script_index = 0
        #self.processing = True
        self.reset()

    def update(self):
        if self.state == 'Run':
            for num_frames, line in self.deferred_commands:
                num_frames -= 1
                if num_frames <= 0:
                    self.parse_line(line)
            self.deferred_commands = [c for c in self.deferred_commands if c[0] > 0]
            if self.frame_count >= self.num_frames:
                self.processing = True
                self.read_script()
            if self.script_index >= len(self.poses[self.current_pose]):
                # check whether we should loop or truly end
                if self.current_pose in self.idle_poses:
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
                    SOUNDDICT['Death'].play() # Play death sound now
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

        # Handle spells
        if self.child_effect:
            self.child_effect.update()
            if self.child_effect.state == 'Inert':
                self.child_effect = None

    def end_current(self):
        #print('Animation: End Current')
        if 'Stand' in self.poses:
            self.current_pose = 'RangedStand' if self.at_range else 'Stand'
            self.state = 'Run'
        else:
            self.state = 'Inert'
        self.script_index = 0

    def finish(self):
        self.current_pose = 'RangedStand' if self.at_range else 'Stand'
        self.state = 'Leaving'
        self.script_index = 0

    def waiting_for_hp(self):
        return self.state == 'Wait' or (self.child_effect and self.child_effect.waiting_for_hp())

    def read_script(self):
        script = self.poses[self.current_pose]
        while(self.script_index < len(script) and self.processing):
            line = script[self.script_index]
            self.parse_line(line)
            self.script_index += 1

    def parse_line(self, line):
        #print(self.right, True if self.child_effect else False, line)
        # === TIMING AND IMAGES ===
        if line[0] == 'f':
            self.frame_count = 0
            self.num_frames = int(line[1])
            self.current_frame = self.frame_directory[line[2]]
            self.processing = False
            if len(line) > 3: # Under frame
                self.under_frame = self.frame_directory[line[3]]
            else:
                self.under_frame = None
        elif line[0] == 'wait':
            self.frame_count = 0
            self.num_frames = int(line[1])
            self.current_frame = None
            self.under_frame = None
            self.processing = False
        # === SFX ===
        elif line[0] == 'sound':
            SOUNDDICT[line[1]].play()
        # === COMBAT HIT ===
        elif line[0] == 'hit':
            if len(line) > 1:
                self.current_frame = self.frame_directory[line[1]]
            else:
                self.current_frame = None
            if len(line) > 2:
                self.under_frame = self.frame_directory[line[2]]
            else:
                self.under_frame = None
            self.state = 'Wait'
            self.processing = False
            if self.owner.current_result.def_damage > 0:
                self.owner.shake(1)
            else: # No Damage
                self.owner.shake(2)
        elif line[0] == 'spell_hit':
            if len(line) > 1:
                self.current_frame = self.frame_directory[line[1]]
            else:
                self.current_frame = None
            if len(line) > 2:
                self.under_frame = self.frame_directory[line[2]]
            else:
                self.under_frame = None
            self.state = 'Wait'
            self.processing = False
            if self.owner.current_result.def_damage > 0:
                self.owner.shake(3)
            else: # No Damage
                self.owner.shake(2)
        # === FLASHING ===
        elif line[0] == 'enemy_flash_white':
            num_frames = int(line[1])
            self.partner.flash(num_frames, (248, 248, 248))
        elif line[0] == 'screen_flash_white':
            self.foreground_frames = int(line[1])
            self.foreground = IMAGESDICT['BlackBackground'].copy()
            self.foreground.fill((248, 248, 248))
        elif line[0] == 'darken':
            self.owner.darken()
        elif line[0] == 'lighten':
            self.owner.lighten()
        # === ANIMATIONS ===
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
                    position = (52, 21)
                else:
                    position = (110, 21) # Enemy's position
                team = self.owner.right.team if self.right else self.owner.left.team
                image = IMAGESDICT['NoDamageBlue' if team == 'player' else 'NoDamageRed']
                anim = CustomObjects.Animation(image, position, (5, 5), ignore_map=True, 
                                              set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
                                                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                                          1, 1, 1, 1, 48))
            self.animations.append(anim)
        elif line[0] == 'miss':
            if self.right:
                position = (72, 21)
            else:
                position = (128, 21) # Enemy's position
            team = self.owner.right.team if self.right else self.owner.left.team
            image = IMAGESDICT['MissBlue' if team == 'player' else 'MissRed']
            anim = CustomObjects.Animation(image, position, (5, 4), ignore_map=True, 
                                          set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
                                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 23))
            self.animations.append(anim)
            self.partner.dodge()
        # === EFFECTS ===
        elif line[0] == 'effect':
            image, script = ANIMDICT.get_effect(line[1])
            self.child_effect = BattleAnimation(image, script)
            self.child_effect.awake(self.owner, self.partner, self.right, self.at_range, parent=self)
            self.child_effect.start_anim(self.current_pose)
        elif line[0] == 'enemy_effect':
            image, script = ANIMDICT.get_effect(line[1])
            self.partner.child_effect = BattleAnimation(image, script)
            # Opposite effects
            self.partner.child_effect.awake(self.owner, self.parent, not self.right, self.at_range, parent=self.parent.partner)
            self.partner.child_effect.start_anim(self.current_pose)
        elif line[0] == 'blend':
            self.blend = 'RGB_ADD'
        elif line[0] == 'spell':
            attacker = self.owner.current_result.attacker
            image, script = ANIMDICT.get_effect(self.owner.right_item.id if attacker is self.owner.right else self.owner.left_item.id)
            self.child_effect = BattleAnimation(image, script)
            self.child_effect.awake(self.owner, self.partner, self.right, self.at_range, parent=self)
            self.child_effect.start_anim(self.current_pose)
        elif line[0] == 'static':
            self.static = True
        # === LOOPING ===
        elif line[0] == 'start_loop':
            self.loop = Loop(self.script_index)
        elif line[0] == 'end_loop':
            if self.loop:
                self.loop.end_index = self.script_index
                self.script_index = self.loop.start_index # re-loop
        elif line[0] == 'end_parent_loop':
            self.parent.end_loop()
        elif line[0] == 'defer':
            num_frames = int(line[1])
            rest_of_line = line[2:]
            self.deferred_commands.append([num_frames, rest_of_line])
        # === CONDITIONALS ===
        elif line[0] == 'if_range':
            if not self.at_range:
                self.script_index += int(line[1])
        elif line[0] == 'nif_range':
            if self.at_range:
                self.script_index += int(line[1])
        # === MOVEMENT ===
        elif line[0] == 'pan':
            self.owner.pan()

    def end_loop(self):
        if self.loop:
            self.script_index = self.loop.end_index
            self.loop = None

    def start_anim(self, pose):
        #print('Animation: Start')
        self.current_pose = pose
        self.script_index = 0
        self.reset()

    def resume(self):
        #print('Animation: Resume')
        if self.state == 'Wait':
            self.reset()
        if self.child_effect:
            self.child_effect.resume()

    def reset(self):
        self.state = 'Run'
        self.frame_count = 0
        self.num_frames = 0

    def done(self):
        return self.state == 'Inert' or (self.state == 'Run' and self.current_pose in self.idle_poses)

    def dodge(self):
        if self.at_range:
            self.start_anim('RangedDodge')
        else:
            self.start_anim('Dodge')

    def flash(self, num, color):
        self.flash_frames = num
        self.flash_color = color

    def start_dying_animation(self):
        self.state = 'Dying'
        self.death_opacity = [0, 20, 20, 20, 20, 44, 44, 44, 44, 64,
                              64, 64, 64, 84, 84, 84, 108, 108, 108, 108, 
                              128, 128, 128, 128, 148, 148, 148, 148, 172, 172, 
                              172, 192, 192, 192, 192, 212, 212, 212, 212, 236,
                              236, 236, 236, 255, 255, 255, 0, 0, 0, 0,
                              0, 0, -1, 0, 0, 0, 0, 0, 0, 255, 
                              0, 0, 0, 0, 0, 0, 255, 0, 0, 0,
                              0, 0, 0, 255, 0, 0, 0, 0, 0, 0,
                              255, 0, 0, 0, 0, 0, 0]

    def draw(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert':
            if self.current_frame is not None:
                image = self.current_frame[0].copy()
                if not self.right:
                    image = Engine.flip_horiz(image)
                offset = self.current_frame[1]
                if self.right:
                    offset = offset[0] + shake[0] + range_offset + (pan_offset if not self.static else 0), offset[1] + shake[1]
                else:
                    offset = WINWIDTH - offset[0] - image.get_width() + shake[0] + range_offset + (pan_offset if not self.static else 0), offset[1] + shake[1]

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

                Engine.blit(surf, image, offset, None, self.blend)

            # Handle child
            if self.child_effect:
                self.child_effect.draw(surf, (0, 0), range_offset, pan_offset)

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

    def draw_under(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert' and self.under_frame is not None:
            image = self.under_frame[0].copy()
            if not self.right:
                image = Engine.flip_horiz(image)
            offset = self.under_frame[1]
            if self.right:
                offset = offset[0] + shake[0] + range_offset + (pan_offset if not self.static else 0), offset[1] + shake[1]
            else:
                offset = WINWIDTH - offset[0] - image.get_width() + shake[0] + range_offset + (pan_offset if not self.static else 0), offset[1] + shake[1]
            # Actually draw
            Engine.blit(surf, image, offset, None, self.blend)