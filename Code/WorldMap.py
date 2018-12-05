import math

# Custom imports
try:
    import GlobalConstants as GC
    import configuration as cf
    import Utility, Image_Modification, Engine
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import Utility, Image_Modification, Engine

class WorldMapBackground(object):
    def __init__(self, sprite, labels=True):
        self.x = 0
        self.y = 0
        self.sprite = sprite

        # for easing
        self.easing_flag = False
        self.target_x = 0
        self.target_y = 0
        self.old_x = 0
        self.old_y = 0
        self.start_time = 0

        # Dictionary of world map sprites
        self.wm_sprites = {}

        # Labels for world map
        self.wm_labels = []
        if labels:
            self.parse_labels('Data/world_map_labels.txt')

        # Highlights
        self.wm_highlights = []

        # Cursor
        self.cursor = None

    def parse_labels(self, fp):
        with open(fp, 'r') as label_data:
            for line in label_data:
                split_line = line.strip().split(';')
                coord = (int(split_line[1]), int(split_line[2]))
                if split_line[3] == '1':
                    font = GC.FONT['chapter_yellow']
                else:
                    font = GC.FONT['chapter_green']
                self.add_label(split_line[0], coord, font)

    def add_label(self, name, position, font=GC.FONT['chapter_yellow']):
        self.wm_labels.append(WMLabel(name, position, font))

    def clear_labels(self):
        self.wm_labels = []

    def add_highlight(self, sprite, position):
        self.wm_highlights.append(WMHighlight(sprite, position))

    def clear_highlights(self):
        for highlight in self.wm_highlights:
            highlight.remove()

    def add_sprite(self, name, klass, gender, team, position):
        # Key is string assigned by user. Value is units class, gender, team, starting_position
        self.wm_sprites[name] = WMSprite(klass, gender, team, position)

    def remove_sprite(self, name):
        del self.wm_sprites[name]

    def move_sprite(self, name, new_pos):
        if name in self.wm_sprites:
            self.wm_sprites[name].move(new_pos)
        elif cf.OPTIONS['debug']:
            print('Error! ', name, ' not in self.wm_sprites')

    def quick_move(self, new_pos):
        self.x += new_pos[0]
        self.y += new_pos[1]

        self.x, self.y = self.bound(self.x, self.y)

    def move(self, new_pos):
        self.old_x = self.x
        self.old_y = self.y
        self.target_x = self.x + new_pos[0]
        self.target_y = self.y + new_pos[1]
        self.start_time = Engine.get_time()
        self.easing_flag = True

        self.target_x, self.target_y = self.bound(self.target_x, self.target_y)

    def bound(self, x, y):
        x = Utility.clamp(x, 0, self.sprite.get_width() - GC.WINWIDTH)
        y = Utility.clamp(y, 0, self.sprite.get_height() - GC.WINHEIGHT)
        return x, y

    def create_cursor(self, coord):
        from Cursor import Cursor
        self.cursor = Cursor('Cursor', coord, fake=True)

    def remove_cursor(self):
        self.cursor = None

    def draw(self, surf):
        # === UPDATE ===
        # Handle easing
        current_time = Engine.get_time()
        if self.easing_flag:
            self.x = Utility.easing(current_time - self.start_time, self.old_x, self.target_x - self.old_x, 400)
            self.y = Utility.easing(current_time - self.start_time, self.old_y, self.target_y - self.old_y, 400)
            if self.target_x > self.old_x and self.x >= self.target_x or \
               self.target_x < self.old_x and self.x <= self.target_x or \
               self.target_y > self.old_y and self.y >= self.target_y or \
               self.target_y < self.old_y and self.y <= self.target_y:
                self.easing_flag = False
                self.x = self.target_x
                self.y = self.target_y

        # === DRAW ===
        image = Engine.copy_surface(self.sprite)
        # Highlights
        for highlight in self.wm_highlights:
            highlight.draw(image)
        self.wm_highlights = [highlight for highlight in self.wm_highlights if not highlight.remove_clear]
        # Draw label
        for label in self.wm_labels:
            label.draw(image)
        # Update world_map_sprites
        for key, wm_unit in self.wm_sprites.items():
            wm_unit.update()
        # World map sprites
        for key, wm_unit in self.wm_sprites.items():
            wm_unit.draw(image)
        # Cursor
        if self.cursor:
            self.cursor.image = Engine.subsurface(self.cursor.passivesprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
            self.cursor.draw(image)

        image = Engine.subsurface(image, (self.x, self.y, GC.WINWIDTH, GC.WINHEIGHT))
        surf.blit(image, (0, 0))

class WMLabel(object):
    def __init__(self, name, position, font=GC.FONT['chapter_yellow']):
        self.name = name
        self.font = font
        self.position = position

    def draw(self, surf):
        self.font.blit(self.name, surf, self.position)

class WMHighlight(object):
    def __init__(self, sprite, position):
        self.sprite = sprite
        self.position = position
        self.trans_value = 0
        self.trans_dir = True

        self.remove_flag = False
        self.remove_clear = False

    def update(self):
        if self.trans_dir:
            self.trans_value += 1
            if self.trans_value >= 50:
                self.trans_value = 50
                self.trans_dir = False
        else:
            self.trans_value -= 1
            if self.trans_value <= 0:
                self.trans_value = 0
                self.trans_dir = True
        if self.remove_flag:
            self.remove_clear = True

        return False

    def remove(self):
        self.remove_flag = True

    def draw(self, surf):
        self.update()
        image = Image_Modification.flickerImageTranslucent(Engine.copy_surface(self.sprite), self.trans_value)
        surf.blit(image, self.position)

class WMSprite(object):
    def __init__(self, klass, gender, team, position):
        self.standspritesName = team + klass + gender # Ex: EnemyMercenaryM
        self.movespritesName = team + klass + gender + '_move' # Ex: EnemyMercenaryM_move
        self.position = position # Describes the actual position of the sprite
        self.new_position = position # Describe where the sprite wants to go

        self.isMoving = False
        self.loadSprites()

        # Counters
        self.moveSpriteCounter = 0
        self.lastUpdate = Engine.get_time()
        self.last_move_update = Engine.get_time()

    def draw(self, surf):
        x, y = self.position
        topleft = x - max(0, (self.image.get_width() - 16)//2), y - max(0, self.image.get_height() - 16)
        surf.blit(self.image, topleft)

    def move(self, new_pos):
        target = self.new_position[0] + new_pos[0], self.new_position[1] + new_pos[1]
        self.new_position = target
        self.isMoving = True

    def update(self):
        currentTime = Engine.get_time()

        # === MOVE SPRITE COUNTER LOGIC ===
        if currentTime - self.lastUpdate > 100:
            self.moveSpriteCounter += 1
            if self.moveSpriteCounter >= 4:
                self.moveSpriteCounter = 0
            self.lastUpdate = currentTime

        # Move unit if he/she needs to be moved
        if self.isMoving:
            if currentTime - self.last_move_update > 50:
                # Finds difference between new_position and position
                unit_speed = 2
                diff_pos = (self.new_position[0] - self.position[0], self.new_position[1] - self.position[1])
                # No longer moving if difference of position is small
                if diff_pos[0] <= unit_speed and diff_pos[0] >= -unit_speed and diff_pos[1] <= unit_speed and diff_pos[1] >= -unit_speed:
                    # Close enough for gov't work
                    self.position = self.new_position
                    self.isMoving = False
                else:
                    angle = math.atan2(diff_pos[1], diff_pos[0])
                    if angle >= -math.pi/4 and angle <= math.pi/4:
                        self.image = Engine.subsurface(self.moveRight, (self.moveSpriteCounter*GC.TILEWIDTH*3, 0, GC.TILEWIDTH*3, 40))
                    elif angle <= -3*math.pi/4 or angle >= 3*math.pi/4:
                        self.image = Engine.subsurface(self.moveLeft, (self.moveSpriteCounter*GC.TILEWIDTH*3, 0, GC.TILEWIDTH*3, 40))
                    elif angle <= -math.pi/4:
                        self.image = Engine.subsurface(self.moveUp, (self.moveSpriteCounter*GC.TILEWIDTH*3, 0, GC.TILEWIDTH*3, 40))
                    else:
                        self.image = Engine.subsurface(self.moveDown, (self.moveSpriteCounter*GC.TILEWIDTH*3, 0, GC.TILEWIDTH*3, 40))
                    updatedown_position = (self.position[0] + unit_speed * math.cos(angle), self.position[1] + unit_speed * math.sin(angle))
                    self.position = updatedown_position

                self.last_move_update = currentTime

        else:
            self.image = Engine.subsurface(self.passiveSprite, (GC.PASSIVESPRITECOUNTER.count*GC.TILEWIDTH*4, 0, GC.TILEWIDTH*4, 40))

    def loadSprites(self):
        # Load sprites
        standsprites = GC.UNITDICT[self.standspritesName]
        movesprites = GC.UNITDICT[self.movespritesName]
        self.passiveSprite, self.graySprite, self.activeSprite, self.moveLeft, self.moveRight, self.moveDown, self.moveUp = self.formatSprite(standsprites, movesprites)
        self.image = Engine.subsurface(self.passiveSprite, (0, 0, GC.TILEWIDTH*4, 40))

    def formatSprite(self, standSprites, moveSprites):
        passiveSprites = Engine.subsurface(standSprites, (0, 0, standSprites.get_width(), GC.TILEHEIGHT*3))
        graySprites = Engine.subsurface(standSprites, (0, GC.TILEHEIGHT*3, standSprites.get_width(), GC.TILEHEIGHT*3))
        activeSprites = Engine.subsurface(standSprites, (0, 2*GC.TILEHEIGHT*3, standSprites.get_width(), GC.TILEHEIGHT*3))
        moveDown = Engine.subsurface(moveSprites, (0, 0, moveSprites.get_width(), 40))
        moveLeft = Engine.subsurface(moveSprites, (0, 40, moveSprites.get_width(), 40))
        moveRight = Engine.subsurface(moveSprites, (0, 80, moveSprites.get_width(), 40))
        moveUp = Engine.subsurface(moveSprites, (0, 120, moveSprites.get_width(), 40))
        return passiveSprites, graySprites, activeSprites, moveLeft, moveRight, moveDown, moveUp
