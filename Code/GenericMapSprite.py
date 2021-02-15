import math

from . import GlobalConstants as GC
from . import Engine, Image_Modification

class GenericMapSprite(object):
    def __init__(self, klass, gender, team, position, transition_in=False):
        self.standspritesName = team + klass + gender # Ex: EnemyMercenaryM
        self.movespritesName = team + klass + gender + '_move' # Ex: EnemyMercenaryM_move
        self.position = position # Describes the actual position of the sprite
        self.new_position = position # Describe where the sprite wants to go
        # For transition
        self.state = 'fade_in' if transition_in else 'normal'
        self.transition_counter = 0

        self.isMoving = False
        self.selected = False
        self.hovered = False
        self.remove_flag = False
        self.loadSprites()

        # Counters
        self.moveSpriteCounter = 0
        self.lastUpdate = Engine.get_time()
        self.last_move_update = Engine.get_time()

    def draw(self, surf):
        x, y = self.position
        topleft = x - max(0, (self.image.get_width() - 16)//2), y - max(0, self.image.get_height() - 16)
        if self.state != 'normal':
            progress = 100 - int(self.transition_counter/32.*100.)
            self.image = Image_Modification.flickerImageBlackColorKey(self.image, progress)
        surf.blit(self.image, topleft)

    def move(self, new_pos, slow=False):
        target = self.new_position[0] + new_pos[0], self.new_position[1] + new_pos[1]
        self.new_position = target
        self.cur_speed = 1 if slow else 2
        self.isMoving = True

    def offset(self, new_pos):
        target = self.new_position[0] + new_pos[0], self.new_position[1] + new_pos[1]
        self.position = target

    def teleport(self, new_pos):
        self.position = new_pos

    def set_target(self, new_pos, slow=False):
        self.new_position = new_pos
        self.cur_speed = 1 if slow else 2
        self.isMoving = True

    def remove(self):
        self.state = 'fade_out'
        self.transition_counter = 32

    def update(self):
        currentTime = Engine.get_time()

        # === MOVE SPRITE COUNTER LOGIC ===
        if currentTime - self.lastUpdate > 100:
            self.moveSpriteCounter += 1
            if self.moveSpriteCounter >= 4:
                self.moveSpriteCounter = 0
            self.lastUpdate = currentTime

        # Transition counter logic
        if self.state == 'fade_in':
            self.transition_counter += 1
            if self.transition_counter > 32:
                self.state = 'normal'
        elif self.state == 'fade_out':
            self.transition_counter -= 1
            if self.transition_counter <= 0:
                self.remove_flag = True

        # Move unit if he/she needs to be moved
        if self.isMoving:
            if currentTime - self.last_move_update > 50:
                # Finds difference between new_position and position
                diff_pos = (self.new_position[0] - self.position[0], self.new_position[1] - self.position[1])
                # No longer moving if difference of position is small
                if -self.cur_speed <= diff_pos[0] <= self.cur_speed and -self.cur_speed <= diff_pos[1] <= self.cur_speed:
                    # Close enough for gov't work
                    self.position = self.new_position
                    self.isMoving = False
                else:
                    angle = math.atan2(diff_pos[1], diff_pos[0])
                    if angle >= -math.pi/4 and angle <= math.pi/4:
                        self.image = Engine.subsurface(self.moveRight, (self.moveSpriteCounter*48, 0, 48, 40))
                    elif angle <= -3*math.pi/4 or angle >= 3*math.pi/4:
                        self.image = Engine.subsurface(self.moveLeft, (self.moveSpriteCounter*48, 0, 48, 40))
                    elif angle <= -math.pi/4:
                        self.image = Engine.subsurface(self.moveUp, (self.moveSpriteCounter*48, 0, 48, 40))
                    else:
                        self.image = Engine.subsurface(self.moveDown, (self.moveSpriteCounter*48, 0, 48, 40))
                    updatedown_position = (self.position[0] + self.cur_speed * math.cos(angle), self.position[1] + self.cur_speed * math.sin(angle))
                    self.position = updatedown_position

                self.last_move_update = currentTime

        elif self.selected:
            self.image = Engine.subsurface(self.moveDown, (self.moveSpriteCounter*48, 0, 48, 40))
        elif self.hovered:
            self.image = Engine.subsurface(self.activeSprite, (GC.ACTIVESPRITECOUNTER.count*64, 0, 64, 40))
        else:
            self.image = Engine.subsurface(self.passiveSprite, (GC.PASSIVESPRITECOUNTER.count*64, 0, 64, 40))

    def loadSprites(self):
        # Load sprites
        standsprites = GC.UNITDICT[self.standspritesName]
        movesprites = GC.UNITDICT[self.movespritesName]
        self.passiveSprite, self.graySprite, self.activeSprite, self.moveLeft, self.moveRight, self.moveDown, self.moveUp = self.formatSprite(standsprites, movesprites)
        self.image = Engine.subsurface(self.passiveSprite, (0, 0, GC.TILEWIDTH*4, 48))

    def formatSprite(self, standSprites, moveSprites):
        passiveSprites = Engine.subsurface(standSprites, (0, 0, standSprites.get_width(), 48))
        graySprites = Engine.subsurface(standSprites, (0, 48, standSprites.get_width(), 48))
        activeSprites = Engine.subsurface(standSprites, (0, 96, standSprites.get_width(), 48))
        moveDown = Engine.subsurface(moveSprites, (0, 0, moveSprites.get_width(), 40))
        moveLeft = Engine.subsurface(moveSprites, (0, 40, moveSprites.get_width(), 40))
        moveRight = Engine.subsurface(moveSprites, (0, 80, moveSprites.get_width(), 40))
        moveUp = Engine.subsurface(moveSprites, (0, 120, moveSprites.get_width(), 40))
        return passiveSprites, graySprites, activeSprites, moveLeft, moveRight, moveDown, moveUp
