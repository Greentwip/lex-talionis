import random

from . import GlobalConstants as GC
from . import Engine, Image_Modification
from . import CustomObjects

speed = 1

class Loop(object):
    def __init__(self, start):
        self.start_index = start
        self.end_index = 0

class BattleAnimation(object):
    idle_poses = {'Stand', 'RangedStand', 'TransformStand'}

    def __init__(self, unit, anim, script, palette_name=None, item=None):
        self.unit = unit
        self.item = item
        self.frame_directory = anim
        self.poses = script
        self.current_pose = None
        self.palette_name = palette_name
        self.state = 'Inert'  # Internal state
        self.num_frames = 0  # How long this frame of animation should exist for (in frames)
        self.animations = []
        self.base_state = False  # Whether the animation is in a basic state (normally Stand or wait_for_hit)
        self.wait_for_hit = False

        self.children = []
        self.under_children = []
        self.loop = False
        self.end_next_loop = 0  # A counter that keeps track of how many loops in the future to skip
        self.deferred_commands = []

        # For drawing
        self.blend = 0
        # flash frames
        self.foreground = None
        self.foreground_frames = 0
        self.background = None
        self.background_frames = 0
        self.flash_color = None
        self.flash_frames = 0
        self.flash_image = None
        self.screen_dodge_color = None
        self.screen_dodge_frames = 0
        self.screen_dodge_image = None
        # Opacity
        self.opacity = 255
        # Offset
        self.under_static = False
        self.static = False
        self.over_static = False
        self.ignore_pan = False
        self.pan_away = False
        self.lr_offset = []
        self.effect_offset = (0, 0)
        self.personal_offset = (0, 0)

        # Awake stuff
        self.owner = None
        self.parent = None

    def get_stand(self):
        if self.transformed:
            self.current_pose = 'TransformStand'
        elif self.at_range:
            self.current_pose = 'RangedStand'
        else:
            self.current_pose = 'Stand'

    def awake(self, owner, partner, right, at_range, init_speed=0, init_position=None, parent=None):
        # print('Awake')
        self.owner = owner
        self.partner = partner
        self.parent = parent if parent else self
        self.right = right
        self.at_range = at_range
        self.transformed = False
        self.init_speed = init_speed
        self.entrance = init_speed
        self.init_position = init_position
        self.get_stand()
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
            if self.current_pose in self.poses:
                if self.script_index >= len(self.poses[self.current_pose]):
                    # check whether we should loop or truly end
                    if self.current_pose in self.idle_poses:
                        self.script_index = 0
                    else:
                        self.end_current()
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
                    GC.SOUNDDICT['CombatDeath'].play()  # Play death sound now
                    # self.unit.deathCounter = 1  # Skip sound
                    self.unit.deathCounter = 0
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
        for child in self.children:
            child.update()
        for child in self.under_children:
            child.update()

        # Remove completed child_effects
        self.children = [child for child in self.children if child.state != 'Inert']
        self.under_children = [child for child in self.under_children if child.state != 'Inert']

    def clear_all_effects(self):
        for child in self.children:
            child.clear_all_effects()
        for child in self.under_children:
            child.clear_all_effects()
        self.children = []
        self.under_children = []

    def get_effect(self, name, offset=None, enemy=False):
        image, script = GC.ANIMDICT.get_effect(name, self.palette_name)
        if script:
            child_effect = BattleAnimation(self.unit, image, script, self.palette_name, self.item)
            right = not self.right if enemy else self.right
            parent = self.parent.partner if enemy else self
            child_effect.awake(self.owner, self.partner, right, self.at_range, parent=parent)
            if offset:
                child_effect.effect_offset = offset
            child_effect.start_anim(self.current_pose)
            return child_effect
        else:
            return None

    def add_effect(self, effect, pose=None):
        if pose and pose in effect.poses:
            effect.change_pose(pose)
        self.children.append(effect)

    def remove_effects(self, effects):
        for effect in effects:
            if effect in self.children:
                self.children.remove(effect)
            if effect in self.under_children:
                self.under_children.remove(effect)

    def end_current(self):
        # print('Animation: End Current')
        if 'Stand' in self.poses:
            self.get_stand()
            self.state = 'Run'
        else:
            self.state = 'Inert'
        # Make sure to return to correct pan if we somehow didn't
        if self.pan_away:
            self.pan_away = False
            self.owner.pan_back()
        self.script_index = 0

    def finish(self):
        self.get_stand()
        self.state = 'Leaving'
        self.script_index = 0

    def get_frames(self, num):
        return max(1, int(int(num) * speed))

    def read_script(self):
        if self.current_pose not in self.poses:
            return
        script = self.poses[self.current_pose]
        while(self.script_index < len(script) and self.processing):
            line = script[self.script_index]
            self.parse_line(line)
            self.script_index += 1

    def parse_line(self, line):
        # print(self.right, line)
        self.base_state = False
        # === TIMING AND IMAGES ===
        if line[0] == 'f':
            self.frame_count = 0
            self.num_frames = self.get_frames(line[1])
            self.current_frame = self.frame_directory.get(line[2])
            self.processing = False
            if line[2] == 'Stand':
                self.base_state = True
            if len(line) > 3 and line[3]:  # Under frame
                self.under_frame = self.frame_directory.get(line[3])
            else:
                self.under_frame = None
            self.over_frame = None
            if len(line) > 4 and line[4]:
                self.personal_offset = tuple(int(num) for num in line[4].split(','))
        elif line[0] == 'of':
            self.frame_count = 0
            self.num_frames = self.get_frames(line[1])
            self.under_frame = None
            self.processing = False
            self.over_frame = self.frame_directory.get(line[2])
            if len(line) > 3:  # Current frame
                self.current_frame = self.frame_directory.get(line[3])
            else:
                self.current_frame = None
        elif line[0] == 'uf':
            self.frame_count = 0
            self.num_frames = self.get_frames(line[1])
            self.current_frame = None
            self.over_frame = None
            self.under_frame = self.frame_directory.get(line[2])
            self.processing = False
            if len(line) > 3:
                self.personal_offset = tuple(int(num) for num in line[3].split(','))
        elif line[0] == 'wait':
            self.frame_count = 0
            self.num_frames = self.get_frames(line[1])
            self.current_frame = None
            self.under_frame = None
            self.over_frame = None
            self.processing = False
        # === SFX ===
        elif line[0] == 'sound':
            sound = random.choice(line[1:])
            GC.SOUNDDICT[sound].play()
        elif line[0] == 'stop_sound':
            for sound in line[1:]:
                GC.SOUNDDICT[sound].stop()
        # === COMBAT HIT ===
        elif line[0] == 'start_hit':
            if 'no_shake' not in line:
                if self.owner.outcome() == 2:
                    self.owner.shake(4)  # Critical
                elif self.owner.def_damage() > 0:
                    self.owner.shake(1)
                else:  # No Damage -- Hit spark handles anim
                    self.owner.shake(2)
            self.owner.start_hit('no_sound' not in line)
            # Also offset partner by [-1, -2, -3, -2, -1]
            if self.partner:
                self.partner.lr_offset = [-1, -2, -3, -2, -1]
        elif line[0] == 'wait_for_hit':
            if self.wait_for_hit:
                if len(line) > 1:
                    self.current_frame = self.frame_directory[line[1]]
                else:
                    self.current_frame = None
                if len(line) > 2:
                    self.under_frame = self.frame_directory[line[2]]
                else:
                    self.under_frame = None
                self.over_frame = None
                self.state = 'Wait'
                self.processing = False
                self.base_state = True
        elif line[0] == 'spell_hit':
            # To handle ruin item
            if not self.item.half or self.owner.def_damage() > 0:
                self.owner.start_hit('no_sound' not in line, self.owner.outcome() == 0)
                self.state = 'Wait'
                self.processing = False
                if self.owner.def_damage() > 0:
                    if 'no_shake' not in line:
                        if self.owner.outcome() == 2:  # Crit
                            self.owner.shake(4)
                        else:
                            self.owner.shake(3)
                elif self.owner.def_damage() == 0:
                    if 'no_shake' not in line:
                        self.owner.shake(2)
                    if self.item and (self.item.weapon or (self.item.spell and self.item.damage)):
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
            if not self.item.half:  # Spell hit handles this
                self.owner.start_hit('no_sound' not in line, True)  # Miss
            if self.partner:
                self.partner.dodge()
        # === FLASHING ===
        elif line[0] == 'parent_tint_loop':
            num_frames = self.get_frames(line[1])
            color = [tuple([int(num) for num in color.split(',')]) for color in line[2:]]
            if self.parent:
                self.parent.flash(num_frames, color)
        elif line[0] == 'parent_tint':
            num_frames = self.get_frames(line[1])
            color = tuple([int(num) for num in line[2].split(',')])
            if self.parent:
                self.parent.flash(num_frames, color)
        elif line[0] == 'enemy_tint':
            num_frames = self.get_frames(line[1])
            color = tuple([int(num) for num in line[2].split(',')])
            if self.partner:
                self.partner.flash(num_frames, color)
        elif line[0] == 'parent_screen_dodge':
            num_frames = self.get_frames(line[1])
            color = tuple([int(num) for num in line[2].split(',')])
            if self.parent:
                self.parent.screen_dodge(num_frames, color)
        elif line[0] == 'enemy_screen_dodge':
            num_frames = self.get_frames(line[1])
            color = tuple([int(num) for num in line[2].split(',')])
            if self.partner:
                self.partner.screen_dodge(num_frames, color)
        elif line[0] == 'enemy_gray':
            num_frames = self.get_frames(line[1])
            if self.partner:
                self.partner.flash(num_frames, 'gray')
        elif line[0] == 'enemy_flash_white':
            num_frames = self.get_frames(line[1])
            if self.partner:
                self.partner.flash(num_frames, (248, 248, 248))
        elif line[0] == 'self_flash_white':
            num_frames = self.get_frames(line[1])
            self.flash(num_frames, (248, 248, 248))
        elif line[0] == 'screen_flash_white':
            num_frames = self.get_frames(line[1])
            if len(line) > 2:
                fade_out = self.get_frames(line[2])
            else:
                fade_out = 0
            self.owner.flash_color(num_frames, fade_out, color=(248, 248, 248))
        elif line[0] == 'screen_blend':
            num_frames = self.get_frames(line[1])
            color = tuple(int(num) for num in line[2].split(','))
            self.owner.flash_color(num_frames, color=color)
        elif line[0] == 'foreground_blend':
            self.foreground_frames = self.get_frames(line[1])
            color = tuple([int(num) for num in line[2].split(',')])
            self.foreground = GC.IMAGESDICT['BlackBackground'].copy()
            self.foreground.fill(color)
        elif line[0] == 'background_blend':
            self.background_frames = self.get_frames(line[1])
            color = tuple([int(num) for num in line[2].split(',')])
            self.background = GC.IMAGESDICT['BlackBackground'].copy()
            self.background.fill(color)
        elif line[0] == 'darken':
            self.owner.darken()
        elif line[0] == 'lighten':
            self.owner.lighten()
        elif line[0] == 'platform_shake':
            self.owner.platform_shake()
        elif line[0] == 'screen_shake':
            self.owner.shake(1)
        # === ANIMATIONS ===
        elif line[0] == 'hit_spark':
            if self.owner.def_damage() > 0:
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
        elif line[0] == 'crit_spark':
            if self.owner.def_damage() > 0:
                image = GC.IMAGESDICT['CritSpark']
                if not self.right:
                    image = Engine.flip_horiz(image)  # If on the left, then need to swap so enemy can have it
                anim = CustomObjects.Animation(image, (-40, -30), (3, 5), 15, ignore_map=True, 
                                               set_timing=(-1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
                self.animations.append(anim)
            else:  # No Damage
                self.no_damage()
        # === EFFECTS ===
        elif line[0] == 'effect':
            name = line[1]
            if len(line) > 2:
                offset = tuple(int(num) for num in line[2].split(','))
            else:
                offset = None
            child_effect = self.get_effect(name, offset)
            if child_effect:
                self.children.append(child_effect)
        elif line[0] == 'under_effect':
            name = line[1]
            if len(line) > 2:
                offset = tuple(int(num) for num in line[2].split(','))
            else:
                offset = None
            child_effect = self.get_effect(name, offset)
            if child_effect:
                self.parent.under_children.append(child_effect)
        elif line[0] == 'enemy_effect':
            name = line[1]
            if len(line) > 2:
                offset = tuple(int(num) for num in line[2].split(','))
            else:
                offset = None
            child_effect = self.get_effect(name, offset, enemy=True)
            if child_effect:
                self.partner.children.append(child_effect)
        elif line[0] == 'enemy_under_effect':
            name = line[1]
            if len(line) > 2:
                offset = tuple(int(num) for num in line[2].split(','))
            else:
                offset = None
            child_effect = self.get_effect(name, offset, enemy=True)
            if child_effect:
                self.partner.under_children.append(child_effect)
        elif line[0] == 'clear_all_effects':
            self.clear_all_effects()
        elif line[0] == 'blend':
            if self.blend:
                self.blend = 0
            else:
                self.blend = Engine.BLEND_RGB_ADD
        elif line[0] == 'spell':
            if len(line) > 1:
                item_id = line[1]
            else:
                item_id = self.item.id
            child_effect = self.get_effect(item_id)
            if child_effect:
                self.children.append(child_effect)
        elif line[0] == 'static':
            self.static = not self.static
        elif line[0] == 'over_static':
            self.over_static = not self.over_static
        elif line[0] == 'under_static':
            self.under_static = not self.under_static
        elif line[0] == 'ignore_pan':
            self.ignore_pan = not self.ignore_pan
        elif line[0] == 'opacity':
            self.opacity = int(line[1])
        elif line[0] == 'set_parent_opacity':
            self.parent.opacity = int(line[1])
        # === LOOPING ===
        elif line[0] == 'start_loop':
            if self.end_next_loop > 0:
                self.end_next_loop -= 1
            else:
                self.loop = Loop(self.script_index)
        elif line[0] == 'end_loop':
            if self.loop:
                self.loop.end_index = self.script_index
                self.script_index = self.loop.start_index  # re-loop
        elif line[0] == 'end_parent_loop':
            self.parent.end_loop()
        elif line[0] == 'end_child_loop':
            for child in self.children:
                child.end_loop()
            for child in self.under_children:
                child.end_loop()
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
            self.pan_away = not self.pan_away
            if self.pan_away:
                self.owner.pan_away()
            else:
                self.owner.pan_back()
        else:
            print('%s is not supported command'%(line[0]))

    def end_loop(self):
        if self.loop:
            if self.loop.end_index:  # If we haven't reached the end yet...
                self.script_index = self.loop.end_index
            self.loop = None  # Either way, done with loop
        else:
            self.end_next_loop += 1

    def start_anim(self, pose):
        self.change_pose(pose)
        if self.current_pose == 'Transform':
            self.transformed = True
        elif self.current_pose == 'Revert':
            self.transformed = False
        self.script_index = 0
        self.wait_for_hit = True
        self.reset()

    def change_pose(self, pose):
        self.current_pose = pose

    def has_pose(self, pose):
        return pose in self.poses

    def resume(self):
        # print('Animation: Resume')
        if self.state == 'Wait':
            self.reset()
        if self.children:
            for child in self.children:
                child.resume()
        if self.under_children:
            for child in self.under_children:
                child.resume()
        self.wait_for_hit = False

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

    def effect_playing(self):
        return bool(self.children or self.under_children)

    def dodge(self):
        if self.at_range:
            self.start_anim('RangedDodge')
        else:
            self.start_anim('Dodge')

    def flash(self, num, color):
        self.flash_frames = num
        self.flash_color = color

    def screen_dodge(self, num, color):
        self.screen_dodge_frames = num
        self.screen_dodge_color = color

    def no_damage(self):
        # print('No Damage!')
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
            self.num_frames = int(42 * speed)

    def get_image(self, frame, shake, range_offset, pan_offset, static):
        image = frame[0].copy()
        if not self.right:
            image = Engine.flip_horiz(image)
        offset = frame[1]
        # Handle own offset
        if self.lr_offset:
            offset = offset[0] + self.lr_offset.pop(), offset[1]
        if self.effect_offset:
            offset = offset[0] + self.effect_offset[0], offset[1] + self.effect_offset[1]
        if self.personal_offset:
            offset = offset[0] + self.personal_offset[0], offset[1] + self.personal_offset[1]
        
        left = 0
        if not static:
            left += shake[0] + range_offset
        if self.at_range and not static:
            if self.ignore_pan:
                if self.right:
                    pan_max = range_offset - 24
                else:
                    pan_max = range_offset + 24
                left -= pan_max
            else:
                left += pan_offset

        if self.right:
            offset = offset[0] + shake[0] + left, offset[1] + shake[1]
        else:
            offset = GC.WINWIDTH - offset[0] - image.get_width() + left, offset[1] + shake[1]
        return image, offset

    def draw(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert':
            # Screen flash
            if self.background and not self.blend:
                Engine.blit(surf, self.background, (0, 0), None, Engine.BLEND_RGB_ADD)

            # Handle under children
            for child in self.under_children:
                child.draw(surf, (0, 0), range_offset, pan_offset)

            if self.current_frame is not None:
                image, offset = self.get_image(self.current_frame, shake, range_offset, pan_offset, self.static)
                # Move the animations in at the beginning and out at the end
                if self.entrance:
                    progress = (self.init_speed - self.entrance) / float(self.init_speed)
                    new_size = (int(progress * image.get_width()), int(progress * image.get_height()))
                    image = Engine.transform_scale(image, new_size)
                    if self.flash_color and self.flash_image:  # Make sure that flash image uses resized image
                        self.flash_image = image
                    diff_x = offset[0] - self.init_position[0]
                    diff_y = offset[1] - self.init_position[1]
                    offset = int(self.init_position[0] + progress * diff_x), \
                        int(self.init_position[1] + progress * diff_y)

                # Self flash
                if self.flash_color:
                    if not self.flash_image or isinstance(self.flash_color, list):
                        if self.flash_color == 'gray':
                            self.flash_image = Image_Modification.gray_image(image.convert_alpha())
                        elif isinstance(self.flash_color, list):
                            self.flash_image = Image_Modification.flicker_image(image.convert_alpha(), self.flash_color[self.flash_frames%len(self.flash_color)])
                        else:
                            self.flash_image = Image_Modification.flicker_image(image.convert_alpha(), self.flash_color)
                    self.flash_frames -= 1
                    image = self.flash_image
                    # If done
                    if self.flash_frames <= 0:
                        self.flash_color = None
                        self.flash_frames = 0
                        self.flash_image = None

                # Self screen dodge
                if self.screen_dodge_color:
                    if not self.screen_dodge_image:
                        self.screen_dodge_image = Image_Modification.screen_dodge(image.convert_alpha(), self.screen_dodge_color)
                    self.screen_dodge_frames -= 1
                    image = self.screen_dodge_image
                    # If done
                    if self.screen_dodge_frames <= 0:
                        self.screen_dodge_color = None
                        self.screen_dodge_frames = 0
                        self.screen_dodge_image = None

                if self.opacity != 255:
                    if self.blend:
                        image = Image_Modification.flickerImageTranslucentBlend(image, self.opacity)
                    else:
                        image = Image_Modification.flickerImageTranslucent255(image.convert_alpha(), self.opacity)

                if self.background and self.blend:
                    old_bg = self.background.copy()
                    Engine.blit(old_bg, image, offset)
                    Engine.blit(surf, old_bg, (0, 0), None, self.blend)
                else:
                    Engine.blit(surf, image, offset, None, self.blend)

            # Handle children
            for child in self.children:
                child.draw(surf, (0, 0), range_offset, pan_offset)

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

            if self.background:                    
                self.background_frames -= 1
                # If done
                if self.background_frames <= 0:
                    self.background = None
                    self.background_frames = 0

    def draw_under(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert' and self.under_frame is not None:
            image, offset = self.get_image(self.under_frame, shake, range_offset, pan_offset, self.under_static)
            # Actually draw
            Engine.blit(surf, image, offset, None, self.blend)

    def draw_over(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'Inert' and self.over_frame is not None:
            image, offset = self.get_image(self.over_frame, shake, range_offset, pan_offset, self.over_static)
            # Actually draw
            Engine.blit(surf, image, offset, None, self.blend)
