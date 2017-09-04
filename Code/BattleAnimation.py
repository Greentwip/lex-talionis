import GlobalConstants as GC
import Engine, Image_Modification
import CustomObjects
# Mode types:
# * Attack 
# * Attack2 - behind
# Critical
# Critical2 - behind
# * Miss
# * Dodge
# * RangedDodge
# * Stand
# * RangedStand

class Loop(object):
    def __init__(self, start):
        self.start_index = start
        self.end_index = 0

class BattleAnimation(object):
    idle_poses = {'Stand', 'RangedStand'}

    def __init__(self, unit, anim, script, name=None):
        # print('Init:', name, anim)
        self.unit = unit
        self.frame_directory = anim
        self.poses = script
        self.current_pose = None
        self.name = name
        self.state = 'Inert'  # Internal state
        self.num_frames = 0  # How long this frame of animation should exist for (in frames)
        self.animations = []
        self.base_state = False  # Whether the animation is in a basic state (normally Stand or wait_for_hit)

        self.child_effect = None
        self.loop = False
        self.deferred_commands = []

        # For drawing
        self.blend = 0
        # flash frames
        self.foreground = None
        self.foreground_frames = 0
        self.flash_color = None
        self.flash_frames = 0
        # Opacity
        self.opacity = 255
        # Offset
        self.static = False
        self.ignore_range_offset = False
        self.lr_offset = []

        # Awake stuff
        self.owner = None
        self.parent = None

        self.speed = 1

    def awake(self, owner, partner, right, at_range, init_speed=None, init_position=None, parent=None):
        # print('Awake')
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
        self.over_frame = None
        self.script_index = 0
        # self.processing = True
        self.reset()

    def update(self):
        if self.state != 'Inert':
            # Handle deferred commands
            self.deferred_commands = \
                [(num_frames - 1, line) for num_frames, line in self.deferred_commands if num_frames > 0]
            for num_frames, line in self.deferred_commands:
                if num_frames <= 0:
                    self.parse_line(line)

        if self.state == 'Run':
            # Handle reading script
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
                    self.flash_frames = 100  # Just a lot
                    GC.SOUNDDICT['Death'].play()  # Play death sound now
                    self.unit.deathCounter = 1  # Skip sound
                self.opacity = opacity
            else:
                self.state = 'Inert'
        elif self.state == 'Leaving':
            self.entrance += 1
            if self.entrance > self.init_speed:
                self.entrance = self.init_speed
                self.state = 'Inert'  # Done
        elif self.state == 'Wait':
            pass

        # Handle spells
        if self.child_effect:
            self.child_effect.update()
            # Remove child_effect
            if self.child_effect.state == 'Inert':
                self.child_effect = None

    def end_current(self):
        # print('Animation: End Current')
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

    def read_script(self):
        script = self.poses[self.current_pose]
        while(self.script_index < len(script) and self.processing):
            line = script[self.script_index]
            self.parse_line(line)
            self.script_index += 1

    def parse_line(self, line):
        # print(self.right, True if self.child_effect else False, line)
        self.base_state = False
        # === TIMING AND IMAGES ===
        if line[0] == 'f':
            self.frame_count = 0
            self.num_frames = int(line[1]) * self.speed
            self.current_frame = self.frame_directory[line[2]]
            self.processing = False
            if line[2] == 'Stand':
                self.base_state = True
            if len(line) > 3:  # Under frame
                self.under_frame = self.frame_directory[line[3]]
            else:
                self.under_frame = None
            self.over_frame = None
        elif line[0] == 'of':
            self.frame_count = 0
            self.num_frames = int(line[1]) * self.speed
            self.under_frame = None
            self.processing = False
            self.over_frame = self.frame_directory[line[2]]
            if line(line) > 3:  # Current frame
                self.current_frame = self.frame_directory[line[3]]
            else:
                self.current_frame = None
        elif line[0] == 'wait':
            self.frame_count = 0
            self.num_frames = int(line[1]) * self.speed
            self.current_frame = None
            self.under_frame = None
            self.over_frame = None
            self.processing = False
        # === SFX ===
        elif line[0] == 'sound':
            GC.SOUNDDICT[line[1]].play()
        # === COMBAT HIT ===
        elif line[0] == 'start_hit':
            if self.owner.current_result.def_damage > 0:
                self.owner.shake(1)
            else:  # No Damage
                self.owner.shake(2)
            self.owner.start_hit()
            # Also offset partner by [-1, -2, -3, -2, -1]
            self.partner.lr_offset = [-1, -2, -3, -2, -1]
        elif line[0] == 'wait_for_hit':
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
            self.base_state = True
        elif line[0] == 'spell_hit':
            if len(line) > 1:
                self.current_frame = self.frame_directory[line[1]]
            else:
                self.current_frame = None
            if len(line) > 2:
                self.under_frame = self.frame_directory[line[2]]
            else:
                self.under_frame = None
            self.owner.start_hit()
            self.state = 'Wait'
            self.processing = False
            if self.owner.current_result.def_damage > 0:
                self.owner.shake(3)
            elif self.owner.current_result.def_damage == 0:
                self.owner.shake(2)
                self.no_damage()
        # === FLASHING ===
        elif line[0] == 'parent_tint_loop':
            num_frames = int(line[1]) * self.speed
            color = [tuple([int(num) for num in color.split(',')]) for color in line[2:]]
            self.parent.flash(num_frames, color)
        elif line[0] == 'parent_tint':
            num_frames = int(line[1]) * self.speed
            color = tuple([int(num) for num in line[2].split(',')])
            self.parent.flash(num_frames, color)
        elif line[0] == 'enemy_flash_white':
            num_frames = int(line[1]) * self.speed
            self.partner.flash(num_frames, (248, 248, 248))
        elif line[0] == 'screen_flash_white':
            num_frames = int(line[1]) * self.speed
            if len(line) > 2:
                fade_out = int(line[2]) * self.speed
            else:
                fade_out = 0
            self.owner.flash_white(num_frames, fade_out)
        elif line[0] == 'foreground_blend':
            self.foreground_frames = int(line[1]) * self.speed
            color = tuple([int(num) for num in line[2].split(',')])
            self.foreground = GC.IMAGESDICT['BlackBackground'].copy()
            self.foreground.fill(color)
        elif line[0] == 'darken':
            self.owner.darken()
        elif line[0] == 'lighten':
            self.owner.lighten()
        elif line[0] == 'platform_shake':
            self.owner.platform_shake()
        # === ANIMATIONS ===
        elif line[0] == 'hit_spark':
            if self.owner.current_result.def_damage > 0:
                if self.right:
                    position = (-110, -30)
                else:
                    position = (-40, -30)  # Enemy's position
                image = GC.IMAGESDICT['HitSpark']
                anim = CustomObjects.Animation(image, position, (3, 5), 14, ignore_map=True, 
                                               set_timing=(-1, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1))
                self.animations.append(anim)
            else:  # No Damage
                self.no_damage()
        elif line[0] == 'miss':
            if self.right:
                position = (72, 21)
            else:
                position = (128, 21)  # Enemy's position
            team = self.owner.right.team if self.right else self.owner.left.team
            image = GC.IMAGESDICT['MissBlue' if team == 'player' else 'MissRed']
            anim = CustomObjects.Animation(image, position, (5, 4), ignore_map=True, 
                                           set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                                       1, 1, 1, 1, 1, 1, 1, 1, 1, 23))
            self.animations.append(anim)
            self.partner.dodge()
        # === EFFECTS ===
        elif line[0] == 'effect':
            image, script = GC.ANIMDICT.get_effect(line[1])
            # print('Effect', script)
            self.child_effect = BattleAnimation(self.unit, image, script, line[1])
            self.child_effect.awake(self.owner, self.partner, self.right, self.at_range, parent=self)
            self.child_effect.start_anim(self.current_pose)
        elif line[0] == 'enemy_effect':
            image, script = GC.ANIMDICT.get_effect(line[1])
            self.partner.child_effect = BattleAnimation(self.partner.unit, image, script, line[1])
            # Opposite effects
            self.partner.child_effect.awake(self.owner, self.parent, not self.right,
                                            self.at_range, parent=self.parent.partner)
            self.partner.child_effect.start_anim(self.current_pose)
        elif line[0] == 'blend':
            if self.blend:
                self.blend = None
            else:
                self.blend = Engine.BLEND_RGB_ADD
        elif line[0] == 'spell':
            attacker = self.owner.current_result.attacker
            item_id = self.owner.right_item.id if attacker is self.owner.right else self.owner.left_item.id
            image, script = GC.ANIMDICT.get_effect(item_id)
            self.child_effect = BattleAnimation(self.unit, image, script, item_id)
            self.child_effect.awake(self.owner, self.partner, self.right, self.at_range, parent=self)
            self.child_effect.start_anim(self.current_pose)
        elif line[0] == 'static':
            self.static = not self.static
        elif line[0] == 'ignore_range_offset':
            self.ignore_range_offset = not self.ignore_range_offset
        elif line[0] == 'opacity':
            self.opacity = int(line[1])
        elif line[0] == 'set_parent_opacity':
            self.parent.opacity = int(line[1])
        # === LOOPING ===
        elif line[0] == 'start_loop':
            self.loop = Loop(self.script_index)
        elif line[0] == 'end_loop':
            if self.loop:
                self.loop.end_index = self.script_index
                self.script_index = self.loop.start_index  # re-loop
        elif line[0] == 'end_parent_loop':
            self.parent.end_loop()
        elif line[0] == 'defer':
            num_frames = int(line[1])
            rest_of_line = line[2:]
            self.deferred_commands.append((num_frames, rest_of_line))
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
        self.current_pose = pose
        self.script_index = 0
        self.reset()

    def resume(self):
        # print('Animation: Resume')
        if self.state == 'Wait':
            self.reset()
        if self.child_effect:
            self.child_effect.resume()

    def reset(self):
        self.state = 'Run'
        self.frame_count = 0
        self.num_frames = 0

    def can_proceed(self):
        if self.loop or self.state == 'Wait':
            return True
        return False

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

    def no_damage(self):
        if self.right:
            position = (52, 21)
        else:
            position = (110, 21)  # Enemy's position
        team = self.owner.right.team if self.right else self.owner.left.team
        image = GC.IMAGESDICT['NoDamageBlue' if team == 'player' else 'NoDamageRed']
        anim = CustomObjects.Animation(image, position, (5, 5), ignore_map=True, 
                                       set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                                   1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                                   1, 1, 1, 1, 48))
        self.animations.append(anim)
        # Also offset self by [-1, -2, -3, -2, -1]
        self.lr_offset = [-1, -2, -3, -2, -1]

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

    def wait_for_dying(self):
        if self.base_state:
            self.num_frames = 42 * self.speed

    def get_image(self, frame, shake, range_offset, pan_offset):
        image = frame[0].copy()
        if not self.right:
            image = Engine.flip_horiz(image)
        offset = frame[1]
        # Handle own offset
        if self.lr_offset:
            offset = offset[0] + self.lr_offset.pop(), offset[1]
        
        left = (shake[0] + range_offset if not self.ignore_range_offset else 0) + (pan_offset if not self.static else 0)
        if self.right:
            offset = offset[0] + shake[0] + left, offset[1] + shake[1]
        else:
            offset = GC.WINWIDTH - offset[0] - image.get_width() + left, offset[1] + shake[1]
        return image, offset

    def draw(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert':
            if self.current_frame is not None:
                image, offset = self.get_image(self.current_frame, shake, range_offset, pan_offset)
                # Move the animations in at the beginning and out at the end
                if self.entrance:
                    progress = (self.init_speed - self.entrance) / float(self.init_speed)
                    new_size = (int(progress * image.get_width()), int(progress * image.get_height()))
                    image = Engine.transform_scale(image, new_size)
                    diff_x = offset[0] - self.init_position[0]
                    diff_y = offset[1] - self.init_position[1]
                    offset = int(self.init_position[0] + progress * diff_x), \
                        int(self.init_position[1] + progress * diff_y)

                # Self flash
                if self.flash_color:
                    if isinstance(self.flash_color, list):
                        image = Image_Modification.flicker_image(image.convert_alpha(), self.flash_color[self.flash_frames%len(self.flash_color)])
                    else:
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
                Engine.blit(surf, self.foreground, (0, 0), None, Engine.BLEND_RGB_ADD)
                self.foreground_frames -= 1
                # If done
                if self.foreground_frames <= 0:
                    self.foreground = None
                    self.foreground_frames = 0

    def draw_under(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert' and self.under_frame is not None:
            image, offset = self.get_image(self.under_frame, shake, range_offset, pan_offset)
            # Actually draw
            Engine.blit(surf, image, offset, None, self.blend)

    def draw_over(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert' and self.over_frame is not None:
            image, offset = self.get_image(self.over_frame, shake, range_offset, pan_offset)
            # Actually draw
            Engine.blit(surf, image, offset, None, self.blend)
