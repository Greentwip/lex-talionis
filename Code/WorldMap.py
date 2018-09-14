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

class Link(object):
    def __init__(self, pos):
        self.position = pos
        self.adjacent_links = set()
        self.chain = None
        self.orientation = None

    def __repr__(self):
        return '%s %s'%(self.position, self.orientation)

class Cliff_Manager(object):
    def __init__(self, cliff_positions, size):
        self.unexplored = set([Link(pos) for pos in cliff_positions])
        unexplored_length = len(self.unexplored)
        self.chains = []
        if self.unexplored:
            self.gen_chains()

        self.width, self.height = size
        self.orientation_grid = [0 for _ in range(self.width*self.height)]

        chain_length = sum(len(chain) for chain in self.chains) 
        assert chain_length == unexplored_length, "%s, %s"%(chain_length, unexplored_length)

        for chain in self.chains:
            self.place_chain(chain)

    def gen_chains(self):
        current_chain = set()
        explored = []
        explored.append(self.unexplored.pop())
        while explored:
            current_link = explored.pop()
            current_chain.add(current_link)
            current_link.chain = current_chain
            adj = self.get_adjacent(current_link)
            if adj:
                for a in adj:
                    self.make_adjacent(current_link, a)
                    explored.append(a)
                self.unexplored -= adj
            elif explored:
                continue
            else:
                self.chains.append(current_chain)
                if self.unexplored:
                    current_chain = set()
                    current_link = self.unexplored.pop()
                    explored.append(current_link)

    def make_adjacent(self, a, b):
        a.adjacent_links.add(b)
        b.adjacent_links.add(a)

    def is_adjacent(self, pos1, pos2):
        if pos1 in [(pos2[0], pos2[1] - 1), (pos2[0] - 1, pos2[1]), (pos2[0] + 1, pos2[1]), (pos2[0], pos2[1] + 1)]:
            return True
        return False

    def get_adjacent(self, current_link):
        adj = set()
        pos = current_link.position
        for link in self.unexplored:
            if self.is_adjacent(link.position, pos):
                adj.add(link)
        for link in self.unexplored:
            # If you are at a diagonal and you are not adjacent to anything I am already adjacent to
            if link.position in [(pos[0] - 1, pos[1] - 1), (pos[0] - 1, pos[1] + 1), (pos[0] + 1, pos[1] - 1), (pos[0] + 1, pos[1] + 1)] and \
                    not any(self.is_adjacent(a.position, link.position) for a in adj):
                adj.add(link)
        return adj

    def place_chain(self, chain):
        if len(chain) == 1:
            c_link = next(iter(chain))
            c_link.orientation = 1
            x, y = c_link.position
            self.orientation_grid[x + y*self.width] = 1
            return
        # Look for endings links (ie, have only one adjacency)
        ending_links = [link for link in chain if len(link.adjacent_links) == 1]
        if len(ending_links) == 0: # Cycle
            ending_link = next(iter(chain))
        # Initial set-up
        else:
            ending_link = ending_links[0]
        assert len(ending_link.adjacent_links) >= 1
        adj_link = next(iter(ending_link.adjacent_links))
        if len(chain) == 2: # Only if there is no middle links
            dx, dy = self.get_difference(ending_link, adj_link)
            if dx == 0:
                ending_link.orientation = 2
            elif dy == 0:
                ending_link.orientation = 1
            elif dx == dy:
                ending_link.orientation = 3
            else:
                ending_link.orientation = 4
        # Now iterate through
        explored = set()
        explored.add((ending_link, adj_link))
        while explored:
            prev, current = explored.pop()
            other_adjs = current.adjacent_links - set([prev])
            if other_adjs:
                for adj in other_adjs:
                    self.find_orientation(prev, current, adj)
                    explored.add((current, adj))
            else:
                self.find_ending_orientation(prev, current)
        # get starting point now -- only if there were middle links
        if len(chain) != 2:
            self.find_ending_orientation(adj_link, ending_link)

        # Lastly, commit it to the orientation grid
        for link in chain:
            x, y = link.position
            self.orientation_grid[x + y*self.width] = link.orientation

    def find_orientation(self, prev, current, next):
        pdx, pdy = self.get_difference(prev, current)
        ndx, ndy = self.get_difference(current, next)
        tdx, tdy = self.get_difference(prev, next)
        if tdx == 0:
            current.orientation = 2
            return
        if tdy == 0:
            current.orientation = 1
            return
        slope = tdy/float(tdx)
        if slope > 0:
            current.orientation = 3
        else:
            current.orientation = 4
        return

    def find_ending_orientation(self, prev, current):
        dx, dy = self.get_difference(prev, current)
        if dy == 0:
            if prev.orientation == 1:
                current.orientation = 1
            elif prev.orientation == 2:
                current.orientation = 2
            elif prev.orientation == 3:
                current.orientation = 4
            else:
                current.orientation = 3
        elif dx == 0:
            if prev.orientation == 1:
                current.orientation = 1
            elif prev.orientation == 2:
                current.orientation = 2
            elif prev.orientation == 3:
                current.orientation = 4
            else:
                current.orientation = 3
        elif dx == dy:
            current.orientation = 3
        else:
            current.orientation = 4
                            
    def get_difference(self, a, b):
        dx = b.position[0] - a.position[0]
        dy = b.position[1] - a.position[1]
        return dx, dy

    def get_orientation(self, pos):
        x, y = pos
        orientation = self.orientation_grid[x + y*self.width]
        if orientation == 2:
            return (9, 6)
        elif orientation == 3:
            return (11, 6)
        elif orientation == 4:
            return (10, 6)
        else:
            return (8, 6)

# Minimap
class MiniMap(object):
    # Constants
    minimap_tiles = GC.IMAGESDICT['Minimap_Tiles']
    minimap_units = GC.IMAGESDICT['Minimap_Sprites']
    minimap_cursor = GC.IMAGESDICT['Minimap_Cursor']
    single_map = {'Grass': (1, 0),
                  'House': (2, 0),
                  'Shop': (3, 0),
                  'Switch': (4, 0),
                  'Fort': (5, 0),
                  'Ruins': (6, 0),
                  'Forest': (8, 0),
                  'Thicket': (9, 0),
                  'Hill': (11, 0),
                  'Floor': (12, 0),
                  'Pillar': (13, 0),
                  'Throne': (14, 0),
                  'Chest': (15, 0),
                  'Mountain': (4, 1),
                  'Desert': (10, 0),
                  'Snow': (12, 1),
                  'Dark_Snow': (13, 1),
                  'Pier': (14, 1)}
    complex_map = ('Wall', 'River', 'Sand', 'Sea')
    scale_factor = 4

    def __init__(self, tile_map, units):
        self.tile_map = tile_map
        self.width = self.tile_map.width
        self.height = self.tile_map.height
        self.colorkey = (0, 0, 0)
        self.surf = Engine.create_surface((self.width*self.scale_factor, self.height*self.scale_factor))
        Engine.set_colorkey(self.surf, self.colorkey, rleaccel=False) # black is transparent
        self.pin_surf = Engine.create_surface((self.width*self.scale_factor, self.height*self.scale_factor), transparent=True)

        # All the rest of this is used for occlusion generation
        self.bg = Engine.copy_surface(self.surf)
        self.starting_scale = 0.25
        new_width = int(self.height*self.scale_factor*self.starting_scale)
        new_height = int(self.width*self.scale_factor*self.starting_scale)
        self.base_mask = Engine.create_surface((new_width, new_height))
        Engine.set_colorkey(self.base_mask, self.colorkey, rleaccel=False)
        Engine.fill(self.base_mask, (255, 255, 255), None)

        # Handle cliffs
        cliff_positions = set()
        for x in range(self.width):
            for y in range(self.height):
                key = self.tile_map.tiles[(x, y)].minimap
                if key in ('Cliff', 'Desert_Cliff', 'Snow_Cliff'):
                    cliff_positions.add((x, y))
        self.cliff_manager = Cliff_Manager(cliff_positions, (self.width, self.height))

        # Build Terrain
        for x in range(self.width):
            for y in range(self.height):
                key = self.tile_map.tiles[(x, y)].minimap
                sprite = self.handle_key(key, (x, y))
                self.surf.blit(sprite, (x*self.scale_factor, y*self.scale_factor))

        # Build units
        self.build_units(units)
        
    def handle_key(self, key, position):
        # print(key)
        # Normal keys
        if key in self.single_map:
            return self.get_sprite(self.single_map[key])
        # Bridge
        elif key == 'Bridge':
            if self.bridge_left_right(position):
                return self.get_sprite((0, 1))
            else:
                return self.get_sprite((8, 1))
        # Door
        elif key == 'Door':
            return self.door_type(position)
        # Wall, River, Desert, Sea
        elif key in self.complex_map:
            return self.complex_shape(key, position)
        # Coast
        elif key == 'Coast':
            return self.coast2(position)
        # Cliff
        elif key in ('Cliff', 'Desert_Cliff', 'Snow_Cliff'):
            pos = self.cliff_manager.get_orientation(position)
            if key == 'Desert_Cliff':
                pos = (pos[0] + 4, pos[1])
            elif key == 'Snow_Cliff':
                pos = (pos[0] - 4, pos[1] + 1)
            return self.get_sprite(pos)
        # Error!
        else:
            print("Error! Unrecognized Minimap Key %s" %(key))

    def build_units(self, units):
        for unit in units:
            if unit.position:
                pos = unit.position[0] * self.scale_factor, unit.position[1] * self.scale_factor
                if unit.team == 'player':
                    self.pin_surf.blit(Engine.subsurface(self.minimap_units, (0, 0, self.scale_factor, self.scale_factor)), pos)
                elif unit.team == 'enemy':
                    self.pin_surf.blit(Engine.subsurface(self.minimap_units, (self.scale_factor*1, 0, self.scale_factor, self.scale_factor)), pos)
                elif unit.team == 'other':
                    self.pin_surf.blit(Engine.subsurface(self.minimap_units, (self.scale_factor*2, 0, self.scale_factor, self.scale_factor)), pos)
                else:
                    self.pin_surf.blit(Engine.subsurface(self.minimap_units, (self.scale_factor*3, 0, self.scale_factor, self.scale_factor)), pos)

    def coast2(self, position):
        sea_keys = ('Sea', 'Pier', 'River', 'Bridge')
        # A is up, B is left, C is right, D is down
        # This code determines which minimap tiles fit assuming you only knew one side of the tile, and then intersects to find the best
        a, b, c, d = None, None, None, None
        up_pos = position[0], position[1] - 1
        if up_pos not in self.tile_map.tiles or self.tile_map.tiles[up_pos].minimap in sea_keys:
            a = {0, 1, 5, 6, 7, 9, 10}
        elif self.tile_map.tiles[up_pos].minimap == 'Coast':
            a = {0, 1, 5, 6, 7, 9, 10, 11, 12}
        else:
            a = {2, 3, 4, 8, 11, 12, 13}
        left_pos = position[0] - 1, position[1]
        if left_pos not in self.tile_map.tiles or self.tile_map.tiles[left_pos].minimap in sea_keys:
            b = {0, 2, 5, 6, 8, 9, 11}
        elif self.tile_map.tiles[left_pos].minimap == 'Coast':
            b = {0, 2, 5, 6, 8, 9, 10, 11, 12}
        else:
            b = {1, 3, 4, 7, 10, 12, 13}
        right_pos = position[0] + 1, position[1]
        if right_pos not in self.tile_map.tiles or self.tile_map.tiles[right_pos].minimap in sea_keys:
            c = {0, 3, 5, 7, 8, 10, 12}
        elif self.tile_map.tiles[right_pos].minimap == 'Coast':
            c = {0, 3, 5, 7, 8, 9, 10, 11, 12}
        else:
            c = {1, 2, 4, 6, 9, 11, 13}
        down_pos = position[0], position[1] + 1
        if down_pos not in self.tile_map.tiles or self.tile_map.tiles[down_pos].minimap in sea_keys:
            d = {0, 4, 6, 7, 8, 11, 12}
        elif self.tile_map.tiles[down_pos].minimap == 'Coast':
            d = {0, 4, 6, 7, 8, 9, 10, 11, 12}
        else:
            d = {1, 2, 3, 5, 9, 10, 13}
        intersection = list(a & b & c & d)
        if len(intersection) == 0:
            value = 9
        elif len(intersection) == 1:
            value = intersection[0]
        elif len(intersection) >= 2:
            value = sorted(intersection)[-1]
        if value == 0:
            row, column = 0, 7
        elif value == 1:
            row, column = 1, 7
        elif value == 2:
            row, column = 2, 7
        elif value == 3:
            row, column = 3, 7
        elif value == 4:
            row, column = 4, 7
        elif value == 5:
            row, column = 4, 6
        elif value == 6:
            row, column = 6, 6
        elif value == 7:
            row, column = 2, 6
        elif value == 8:
            row, column = 0, 6
        elif value == 9:
            row, column = 5, 6
        elif value == 10:
            row, column = 3, 6
        elif value == 11:
            row, column = 7, 6
        elif value == 12:
            row, column = 1, 6
        elif value == 13:
            row, column = 0, 5

        return self.get_sprite((row, column))

    # def coast(self, position):
    #     column = 6
    #     # sea_keys = ('Sea', 'Coast', 'Pier', 'River', 'Bridge')
    #     sea_keys = ('Sea', 'Pier', 'River', 'Bridge')
    #     adj_pos = self.tile_map.get_adjacent(position)
    #     border = 4 - len(adj_pos)
    #     number_matching = sum([self.tile_map.tiles[pos].minimap in sea_keys for pos in adj_pos])
    #     number_matching += border

    #     left_pos = position[0] - 1, position[1]
    #     right_pos = position[0] + 1, position[1]
    #     top_pos = position[0], position[1] - 1
    #     bottom_pos = position[0], position[1] + 1

    #     if number_matching == 0:
    #         row, column = 0, 5
    #     elif number_matching == 1:
    #         if not self.tile_map.check_bounds(left_pos) or self.tile_map.tiles[left_pos].minimap in sea_keys:
    #             row = 6
    #         elif not self.tile_map.check_bounds(right_pos) or self.tile_map.tiles[right_pos].minimap in sea_keys:
    #             row = 2
    #         elif not self.tile_map.check_bounds(top_pos) or self.tile_map.tiles[top_pos].minimap in sea_keys:
    #             row = 4
    #         elif not self.tile_map.check_bounds(bottom_pos) or self.tile_map.tiles[bottom_pos].minimap in sea_keys:
    #             row = 0
    #     elif number_matching == 2:
    #         # Topleft
    #         if (not self.tile_map.check_bounds(left_pos) or self.tile_map.tiles[left_pos].minimap in sea_keys) and \
    #            (not self.tile_map.check_bounds(top_pos) or self.tile_map.tiles[top_pos].minimap in sea_keys):
    #             row = 5
    #         # Topright
    #         elif (not self.tile_map.check_bounds(right_pos) or self.tile_map.tiles[right_pos].minimap in sea_keys) and \
    #            (not self.tile_map.check_bounds(top_pos) or self.tile_map.tiles[top_pos].minimap in sea_keys):
    #             row = 3
    #         # Bottomleft
    #         elif (not self.tile_map.check_bounds(left_pos) or self.tile_map.tiles[left_pos].minimap in sea_keys) and \
    #            (not self.tile_map.check_bounds(bottom_pos) or self.tile_map.tiles[bottom_pos].minimap in sea_keys):
    #             row = 7
    #         # Bottomright
    #         elif (not self.tile_map.check_bounds(right_pos) or self.tile_map.tiles[right_pos].minimap in sea_keys) and \
    #            (not self.tile_map.check_bounds(bottom_pos) or self.tile_map.tiles[bottom_pos].minimap in sea_keys):
    #             row = 1
    #         else:
    #             row, column = 0, 0
    #     elif number_matching == 3:
    #         if not self.tile_map.check_bounds(left_pos) or self.tile_map.tiles[left_pos].minimap not in sea_keys:
    #             row = 2
    #         elif not self.tile_map.check_bounds(right_pos) or self.tile_map.tiles[right_pos].minimap not in sea_keys:
    #             row = 6
    #         elif not self.tile_map.check_bounds(top_pos) or self.tile_map.tiles[top_pos].minimap not in sea_keys:
    #             row = 0
    #         elif not self.tile_map.check_bounds(bottom_pos) or self.tile_map.tiles[bottom_pos].minimap not in sea_keys:
    #             row = 4
    #     elif number_matching == 4:
    #         row, column = 0, 7

    #     return self.get_sprite((row, column))

    def bridge_left_right(self, position):
        # Keep running left along bridge until we leave bridge
        pos = position
        while self.tile_map.check_bounds(pos) and self.tile_map.tiles[pos].minimap == 'Bridge':
            pos = (pos[0] - 1, pos[1]) # Go left
        # If we hit sea or the end of the map, not left/right bridge
        if not self.tile_map.check_bounds(pos) or self.tile_map.tiles[pos].minimap in ['Sea', 'River', 'Wall']:
            return False
        else:
            return True

    def door_type(self, position):
        left_pos = position[0] - 1, position[1]
        right_pos = position[0] + 1, position[1]
        if self.tile_map.check_bounds(left_pos) and self.tile_map.tiles[left_pos].minimap == 'Door':
            return self.get_sprite((7, 1))
        elif self.tile_map.check_bounds(right_pos) and self.tile_map.tiles[right_pos].minimap == 'Door':
            return self.get_sprite((6, 1))
        else:
            return self.get_sprite((7, 0))

    def complex_shape(self, key, position):
        column = self.complex_map.index(key) + 2
        
        if key == 'Sand':
            keys = ('Sand', 'Desert', 'Desert_Cliff', 'Wall')
        elif key in ('Sea', 'River'):
            keys = ('Sea', 'Coast', 'River', 'Wall', 'Pier', 'Bridge')
        else:
            keys = (key, )

        row = 0

        left_pos = position[0] - 1, position[1]
        right_pos = position[0] + 1, position[1]
        top_pos = position[0], position[1] - 1
        bottom_pos = position[0], position[1] + 1

        if not self.tile_map.check_bounds(left_pos) or self.tile_map.tiles[left_pos].minimap in keys:
            row += 1
        if not self.tile_map.check_bounds(right_pos) or self.tile_map.tiles[right_pos].minimap in keys:
            row += 2
        if not self.tile_map.check_bounds(top_pos) or self.tile_map.tiles[top_pos].minimap in keys:
            row += 4
        if not self.tile_map.check_bounds(bottom_pos) or self.tile_map.tiles[bottom_pos].minimap in keys:
            row += 8

        return self.get_sprite((row, column))

    def get_sprite(self, pos):
        return Engine.subsurface(self.minimap_tiles, (pos[0]*self.scale_factor, pos[1]*self.scale_factor, self.scale_factor, self.scale_factor))

    def draw(self, surf, camera_offset, progress=1):
        current_time = Engine.get_time()%2000

        progress = Utility.clamp(progress, 0, 1)
        image = Engine.copy_surface(self.surf)
        units = self.pin_surf
        # Flicker pin surf
        if current_time > 1600:
            whiteness = 2.55 * (100 - abs(current_time - 1800)//2)
            units = Image_Modification.flickerImageWhite(units, whiteness)
        image.blit(units, (0, 0))

        if progress != 1:
            image = self.occlude(Engine.copy_surface(image), progress)

        # TODO make minimaps work with even bigger maps (current limit is 60x40)
        pos = (GC.WINWIDTH//2 - image.get_width()//2, GC.WINHEIGHT//2 - image.get_height()//2)
        surf.blit(image, pos)
        x = camera_offset.x
        y = camera_offset.y
        cursor_pos = pos[0] + x*self.scale_factor - 1, pos[1] + y*self.scale_factor - 1
        if progress == 1:
            minimap_cursor = self.minimap_cursor
            if current_time > 1600 or (current_time > 600 and current_time < 1000):
                if current_time > 1600:
                    whiteness = 2.55 * (100 - abs(current_time - 1800)//2)
                else:
                    whiteness = 2.55 * (100 - abs(current_time - 800)//2)
                minimap_cursor = Image_Modification.flickerImageWhite(minimap_cursor, whiteness)
            surf.blit(minimap_cursor, cursor_pos)

    def occlude(self, surf, progress):
        # Generate Mask
        bg = Engine.copy_surface(self.bg) # Copy background area for mask
        # Scale mask to correct size
        # Width is original width of starting mask (uses height because of 90 deg rot)
        width = int(self.height*self.scale_factor*self.starting_scale)
        # W_Add is how much more width should be added to get current_width
        w_add = int(self.height*self.scale_factor*(1-self.starting_scale)*progress)
        # Same goes for height
        height = int(self.width*self.scale_factor*self.starting_scale)
        h_add = int(self.width*self.scale_factor*(1-self.starting_scale)*progress)
        # Actually scale mask
        mask = Engine.transform_scale(self.base_mask, (width + w_add, height + h_add))
        # Rotate mask by -90 degrees at max
        mask = Engine.transform_rotate(mask, progress*-90)
        # Place mask within center of minimap
        bg.blit(mask, (bg.get_width()//2 - mask.get_width()//2, bg.get_height()//2 - mask.get_height()//2))

        # Apply mask to surf
        Engine.blit(surf, bg, bg.get_rect().topleft, bg.get_rect(), Engine.BLEND_RGB_MULT)
        return surf
