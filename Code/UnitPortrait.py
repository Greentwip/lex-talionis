import random, math

from . import GlobalConstants as GC
from . import Engine, Counters, Image_Modification

class UnitPortrait(object):
    def __init__(self, portrait_name, blink_position, mouth_position, position, 
                 priority=0, mirror=False, transition=False, expression=None, 
                 slide=None):
        self.name = portrait_name
        try:
            portrait_sprite = GC.UNITDICT[portrait_name + 'Portrait'].copy()
        except KeyError:
            raise KeyError
        self.halfblink = Engine.subsurface(portrait_sprite, (96, 48, 32, 16))
        self.fullblink = Engine.subsurface(portrait_sprite, (96, 64, 32, 16))
        self.openmouth = Engine.subsurface(portrait_sprite, (0, 96, 32, 16))
        self.halfmouth = Engine.subsurface(portrait_sprite, (32, 96, 32, 16))
        self.closemouth = Engine.subsurface(portrait_sprite, (64, 96, 32, 16))
        self.opensmile = Engine.subsurface(portrait_sprite, (0, 80, 32, 16))
        self.halfsmile = Engine.subsurface(portrait_sprite, (32, 80, 32, 16))
        self.closesmile = Engine.subsurface(portrait_sprite, (64, 80, 32, 16))
        self.portrait = Engine.subsurface(portrait_sprite, (0, 0, 96, 80))

        self.blink_position = blink_position
        self.mouth_position = mouth_position

        self.position = position
        # For movement
        self.new_position = position
        self.isMoving = False
        self.last_move_update = 0
        self.unit_speed = 6
        self.update_time = 25

        self.priority = priority
        self.mirror = mirror
        self.remove_flag = False
        self.image = self.portrait.copy()

        # Talking setup
        self.talking = False
        self.talk_state = 0
        self.last_talk_update = 0
        self.next_talk_update = 0

        # Transition info
        self.transition = 'trans2color' if transition else 0
        self.transition_transparency = 100 if transition else 0  # 100 is most transparency
        self.transition_last_update = Engine.get_time()
        self.slide = slide

        # Blinking set up
        self.offset_blinking = [x for x in range(-2000, 2000, 125)]
        self.blink_counter = Counters.generic3Counter(7000 + random.choice(self.offset_blinking), 40, 40) # 3 frames for each

        # Expression
        self.expression = set(expression) if expression else set()

        # For bop
        self.bops_remaining = 0
        self.bop_state = False
        self.last_bop = None

    def talk(self):
        self.talking = True

    def stop_talking(self):
        self.talking = False

    def set_expression(self, commands):
        self.expression = set(commands)
        if 'Full_Blink' in self.expression:
            self.expression.add('CloseEyes')
        if 'Half_Blink' in self.expression:
            self.expression.add('HalfCloseEyes')
        if 'Smiling' in self.expression:
            self.expression.add('Smile')
        if 'Normal' in self.expression:
            self.expression = set()

    def move(self, new_position):
        self.new_position = self.new_position[0] + new_position[0], self.new_position[1] + new_position[1]
        self.isMoving = True

    def bop(self):
        self.bops_remaining = 2
        self.bop_state = False
        self.last_bop = Engine.get_time()

    def update(self, current_time=None):
        if not current_time:
            current_time = Engine.get_time()
        # update mouth
        if self.talking and current_time - self.last_talk_update > self.next_talk_update:
            self.last_talk_update = current_time
            chance = random.randint(1, 10)
            if self.talk_state == 0:
                # 10% chance to skip to state 2    
                if chance == 1:
                    self.talk_state = 2
                    self.next_talk_update = random.randint(70, 160)
                else:
                    self.talk_state = 1
                    self.next_talk_update = random.randint(30, 50)
            elif self.talk_state == 1:
                # 10% chance to go back to state 0
                if chance == 1:
                    self.talk_state = 0
                    self.next_talk_update = random.randint(50, 100)
                else:
                    self.talk_state = 2
                    self.next_talk_update = random.randint(70, 160)
            elif self.talk_state == 2:
                # 10% chance to skip back to state 0
                # 10% chance to go back to state 1
                chance = random.randint(1, 10)
                if chance == 1:
                    self.talk_state = 0
                    self.next_talk_update = random.randint(50, 100)
                elif chance == 2:
                    self.talk_state = 1
                    self.next_talk_update = random.randint(30, 50)
                else:
                    self.talk_state = 3
                    self.next_talk_update = random.randint(30, 50)
            elif self.talk_state == 3:
                self.talk_state = 0
                self.next_talk_update = random.randint(50, 100)

        if not self.talking:
            self.talk_state = 0
        self.blink_counter.update(current_time)

        if self.transition:
            # 14 frames for Unit Face to appear
            perc = 100. * (current_time - self.transition_last_update) / 233
            if self.transition == 'trans2color':
                self.transition_transparency = 100 - perc 
            elif self.transition == 'color2trans':
                self.transition_transparency = perc
            if self.transition_transparency > 100 or self.transition_transparency < 0:
                self.transition = 0
                self.transition_transparency = max(0, min(100, self.transition_transparency))
                # Done transitioning to invisibility, so remove me!
                if self.remove_flag:
                    return True

        # Move unit if he/she needs to be moved
        if self.isMoving:
            if current_time - self.last_move_update > self.update_time:
                # Finds difference between new_position and position
                diff_pos = (self.new_position[0] - self.position[0], self.new_position[1] - self.position[1])
                # No longer moving if difference of position is small
                if diff_pos[0] <= self.unit_speed and diff_pos[0] >= -self.unit_speed and diff_pos[1] <= self.unit_speed and diff_pos[1] >= -self.unit_speed:
                    # Close enough for gov't work
                    self.position = self.new_position
                    self.isMoving = False
                else:
                    angle = math.atan2(diff_pos[1], diff_pos[0])
                    updated_position = (self.position[0] + self.unit_speed * math.cos(angle), self.position[1] + self.unit_speed * math.sin(angle))
                    self.position = updated_position

                self.last_move_update = current_time

        # Bop unit if he/she needs to be bopped
        if self.bops_remaining:
            if current_time - self.last_bop > 150:
                self.last_bop = current_time
                if self.bop_state:
                    self.bops_remaining -= 1
                self.bop_state = not self.bop_state
                
        return False

    def create_image(self):
        self.image = self.portrait.copy()
        if "CloseEyes" in self.expression:
            self.image.blit(self.fullblink, self.blink_position)
        elif "HalfCloseEyes" in self.expression:
            self.image.blit(self.halfblink, self.blink_position)
        elif "OpenEyes" in self.expression:
            pass
        else:
            if self.blink_counter.count == 0:  # Open eyes
                pass
            elif self.blink_counter.count == 1:  # Half-lidded eyes
                self.image.blit(self.halfblink, self.blink_position)
            elif self.blink_counter.count == 2:  # Closed eyes
                self.image.blit(self.fullblink, self.blink_position)

        if self.talk_state == 0:
            if "Smile" in self.expression:
                self.image.blit(self.closesmile, self.mouth_position)
            else:
                self.image.blit(self.closemouth, self.mouth_position)
        elif self.talk_state == 1 or self.talk_state == 3:
            if "Smile" in self.expression:
                self.image.blit(self.halfsmile, self.mouth_position)
            else:
                self.image.blit(self.halfmouth, self.mouth_position)
        elif self.talk_state == 2:
            if "Smile" in self.expression:
                self.image.blit(self.opensmile, self.mouth_position) 
            else:
                self.image.blit(self.openmouth, self.mouth_position)
        
    def draw(self, surf):
        self.create_image()    
        # === MODS ===
        image_sprite = self.image.copy()

        if self.transition:
            if self.slide:
                image_sprite = Image_Modification.flickerImageTranslucentColorKey(image_sprite, self.transition_transparency)
            else:
                image_sprite = Image_Modification.flickerImageBlackColorKey(image_sprite, self.transition_transparency)

        # Mirror if necessary...
        if self.mirror:
            image_sprite = Engine.flip_horiz(image_sprite)

        # Slide left or right
        if self.slide:
            if self.slide == 'right':
                position = self.position[0] - int(24./100 * self.transition_transparency), self.position[1]
            else:
                position = self.position[0] + int(24./100 * self.transition_transparency), self.position[1]
        else:
            position = self.position
        # bop
        position = position[0], position[1] + (2 if self.bop_state else 0)
            
        surf.blit(image_sprite, position)

    def remove(self):
        self.transition = 'color2trans'
        self.remove_flag = True
        self.transition_last_update = Engine.get_time()
