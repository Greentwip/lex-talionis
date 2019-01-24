try:
    import GlobalConstants as GC
    import configuration as cf
    import Utility, Image_Modification, Engine, GenericMapSprite
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import Utility, Image_Modification, Engine, GenericMapSprite

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

    def add_marker(self, sprite, position):
        self.wm_markers.append(WMMarker(sprite, position))

    def clear_markers(self):
        self.wm_markers = []

    def add_sprite(self, name, klass, gender, team, position):
        # Key is string assigned by user. Value is units class, gender, team, starting_position
        self.wm_sprites[name] = GenericMapSprite.GenericMapSprite(klass, gender, team, position)

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
        self.wm_highlights = [highlight for highlight in self.wm_highlights if not highlight.remove]
        # Draw label
        for label in self.wm_labels:
            label.draw(image)
        self.wm_labels = [label for label in self.wm_labels if not label.remove]
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
    def __init__(self, name, position):
        self.font = GC.FONT['Label']
        if name in GC.IMAGESDICT:
            self.surface = GC.IMAGESDICT[name]
        else:
            size = self.font.size(name)
            self.surface = Engine.create_surface(size, transparent=True)
            self.font.blit(name, self.surface, (0, 0))
        self.position = position

        self.state = 'fade_in'
        self.transition_counter = 0
        self.transition_speed = 12
        self.remove = False

    def draw(self, surf):
        if self.state == 'fade_in':
            progress = float(self.transition_counter)/self.transition_speed
            transparency = int(100*progress)
            image = Image_Modification.flickerImageTranslucent(self.surface, transparency)
            pos_x = int(Utility.quad_ease_out(16, 0, progress, 1))
            pos = self.position[0] + pos_x, self.position[1]
            if progress >= 1:
                self.state = 'normal'
            else:
                self.transition_counter += 1
        elif self.state == 'normal':
            image = self.surface
            pos = self.position
        elif self.state == 'fade_out':
            progress = float(self.transition_counter)/self.transition_speed
            transparency = int(100*progress)
            image = Image_Modification.flickerImageTranslucent(self.surface, transparency)
            pos_x = int(Utility.quad_ease_out(16, 0, progress, 1))
            pos = self.position[0] + pos_x, self.position[1]
            if progress <= 0:
                # self.state = 'remove_me'
                pass
            else:
                self.transition_counter -= 1

        surf.blit(image, pos)

class WMHighlight(object):
    def __init__(self, sprite, position):
        self.sprite = sprite
        self.position = position
        self.trans_value = 0
        self.trans_dir = True

        self.remove_asap = False
        self.remove = False

    def update(self):
        if self.trans_dir:
            self.trans_value += 2
            if self.trans_value >= 100:
                self.trans_value = 100
                self.trans_dir = False
        else:
            self.trans_value -= 2
            if self.trans_value <= 0:
                self.trans_value = 0
                self.trans_dir = True
        if self.remove_flag:
            self.remove_clear = True

        return False

    def remove(self):
        self.remove_asap = True

    def draw(self, surf):
        self.update()
        image = Image_Modification.flickerImageTranslucentBlend(self.sprite, 2.55*self.trans_value)
        Engine.blit(image, surf, self.position, None, Engine.BLEND_RGB_ADD)
        # surf.blit(image, self.position)

class WMMarker(object):
    def __init__(self, sprite, position):
        self.sprite = sprite
        self.position = position

        self.current_idx = 0

    def draw(self, surf):
        self.current_idx += 1
        x_pos = self.current_idx/8
        y_pos = self.current_idx%8
        image = Engine.subsurface(self.sprite, (x_pos*8, y_pos*8, 8, 8))
        surf.blit(image, self.position)
