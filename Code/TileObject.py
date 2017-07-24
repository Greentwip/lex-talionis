import os, math
from imagesDict import COLORKEY
from GlobalConstants import *
from configuration import *
from collections import OrderedDict

# Custom imports
import StatusObject, CustomObjects, Dialogue, Image_Modification, Engine, Weather

import logging
logger = logging.getLogger(__name__)

DESTRUCTION_ANIM_TIME = 500
NUM_LAYERS = 4

# === GENERIC MAP OBJECT
class MapObject(object):
    def __init__(self, mapfilename, tilefilename, levelfolder, weather=[]):
        colorkey, self.width, self.height = self.build_color_key(Engine.image_load(tilefilename, convert=True))

        self.tiles = {} # The mechanical information about the tile organized by position
        self.tile_sprites = {} # The sprite information about the tile organized by position
        self.opacity_map = [False for _ in range(self.width*self.height)]
        self.command_list = [] # The commands that have been acted upon the map by scripts
        self.escape_highlights = {}
        self.formation_highlights = {}
        self.custom_origin = None

        self.levelfolder = levelfolder
        self.mapfilename = mapfilename
        self.parse_tile_info(self.levelfolder + '/' + 'tileInfo.txt')

        self.weather = []
        for name in weather:
            self.add_weather(name)
        self.status_effects = set() # Status ids, not the statuses themselves

        # Populate tiles
        self.populate_tiles(colorkey)

        self.sprites_loaded_flag = False
        self.loadSprites()
        # Layers
        self.layers = [Layer() for _ in range(NUM_LAYERS)]

        self.animations = []

    def build_color_key(self, tiledata, orig=True):
        width = tiledata.get_width()
        height = tiledata.get_height()
        mapObj = [] # Array of map data
    
        # Convert to a mapObj
        for x in range(width):
            mapObj.append([])
        for y in range(height):
            for x in range(width):
                mapObj[x].append(tiledata.get_at((x,y))) # appends [r,g,b,t] value

        return mapObj, width, height

    def populate_tiles(self, colorKeyObj, offset=(0,0)):
        for x in range(offset[0], offset[0]+len(colorKeyObj)):
            for y in range(offset[1], offset[1]+len(colorKeyObj[x-offset[0]])):
                cur = colorKeyObj[x-offset[0]][y-offset[1]]
                for terrain in TERRAINDATA.getroot().findall('terrain'):
                    colorKey = terrain.find('color').text.split(',')
                    if (int(cur[0]) == int(colorKey[0]) and int(cur[1]) == int(colorKey[1]) and int(cur[2]) == int(colorKey[2])):
                        # Instantiate
                        new_tile = TileObject(terrain.get('name'), terrain.find('minimap').text, terrain.find('platform').text, (x,y), \
                                              terrain.find('mtype').text, [terrain.find('DEF').text, terrain.find('AVO').text])
                        self.tiles[(x,y)] = new_tile
                        self.opacity_map[x * self.height + y] = new_tile.opaque
                        if 'HP' in self.tile_info_dict[(x,y)]: # Tile hp is needed so apply that here
                            self.tiles[(x,y)].give_hp_stat(self.tile_info_dict[(x,y)]['HP'])
                        break
                else: # Never found terrain...
                    logger.error('Terrain matching colorkey %s never found.', cur)

    def area_replace(self, coord, image_filename, grid_manager=None):
        colorkey, width, height = self.build_color_key(self.loose_tile_sprites[image_filename])
        self.populate_tiles(colorkey, coord)
        if grid_manager:
            # Remember to update the grid also
            for x in range(coord[0], coord[0]+width):
                for y in range(coord[1], coord[1]+height):
                    grid_manager.update_tile(self.tiles[(x,y)])
        return width, height

    def change_tile_sprites(self, coord, image_filename, transition=None):
        image = self.loose_tile_sprites[image_filename]
        size = image.get_width()/TILEWIDTH, image.get_height()/TILEHEIGHT
        for x in range(coord[0], coord[0]+size[0]):
            for y in range(coord[1], coord[1]+size[1]):
                pos = (x - coord[0], y - coord[1])
                self.tile_sprites[(x,y)] = TileSprite(None, (x, y), self)
                #print(pos)
                if transition:
                    self.tile_sprites[(x,y)].new_image_name = image_filename
                    self.tile_sprites[(x,y)].new_position = pos
                    self.tile_sprites[(x,y)].loadNewSprites()
                    if transition == 'destroy':
                        # To be moved to global during next update
                        self.animations.append(CustomObjects.Animation(IMAGESDICT['Snag'], (x, y - 1), (5, 13), animation_speed = DESTRUCTION_ANIM_TIME/(13*5)))
                else:
                    self.tile_sprites[(x,y)].image_name = image_filename
                    self.tile_sprites[(x,y)].position = pos
                    self.tile_sprites[(x,y)].loadSprites()

    # If you change the map, you also need to reset their position to their normal position, and their image name to none,
    # so the tile sprites reference the new map sprite...
    def reset_all_tile_sprites(self):
        for position, tile_sprite in self.tile_sprites.iteritems():
            tile_sprite.position = position
            tile_sprite.image_name = None

    def draw(self, surf, gameStateObj):
        if self.autotiles:
            surf.blit(self.autotiles[self.autotile_frame], (0, 0))
        surf.blit(self.map_image, (0, 0))
        for position, tile in self.tile_sprites.iteritems():
            tile.draw(surf, position)
        for position in self.tile_sprites.keys():
            tile = self.tile_sprites[position]
            if not tile.new_image:
                tile.draw(self.map_image, position) # Done, can place on main layer
                del self.tile_sprites[position] # Can delete now that it has been permanently etched onto map image
        # Layers
        for layer in self.layers:
            if layer.show or layer.fade > 0:
                layer.draw(surf)

        for pos, highlight in self.escape_highlights.iteritems():
            highlight.draw(surf, pos, gameStateObj.highlight_manager.updateIndex, 0)

        if gameStateObj.stateMachine.getState() in ['prep_formation', 'prep_formation_select']:
            for pos, highlight in self.formation_highlights.iteritems():
                highlight.draw(surf, pos, gameStateObj.highlight_manager.updateIndex, 0)

    def loadSprites(self):
        if not self.sprites_loaded_flag:
            self.sprites_loaded_flag = True
            # Handle grabbing normal sprites
            self.map_image = Engine.image_load(self.mapfilename, convert=True)
            Engine.set_colorkey(self.map_image, COLORKEY, rleaccel=True)
            # Auto-tiles
            auto_loc = self.levelfolder + '/Autotiles/'
            self.autotile_frame = 0
            if os.path.exists(auto_loc):
                files = sorted([fp for fp in os.listdir(auto_loc) if fp.startswith('autotile') and fp.endswith('.png')], key=lambda x: int(x[8:-4]))
                imageList = [Engine.image_load(auto_loc + image, convert=True) for image in files]
                for image in imageList:
                    Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                self.autotiles = imageList
            else:
                self.autotiles = []
            # Loose Tile Sprites
            lts_loc = self.levelfolder + '/LooseTileSprites/'
            if os.path.exists(lts_loc):
                itemnameList = [image[:-4] for image in os.listdir(lts_loc) if image.endswith('.png')]
                imageList = [Engine.image_load(lts_loc + image, convert=True) for image in os.listdir(lts_loc) if image.endswith('.png')]
                for image in imageList:
                    Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                self.loose_tile_sprites = dict(zip(itemnameList, imageList))
            else:
                self.loose_tile_sprites = {}

            # Re-add escape highlights if necessary
            for position, tile_values in self.tile_info_dict.iteritems():
                if "Escape" in tile_values or "Arrive" in tile_values:
                    self.escape_highlights[position] = CustomObjects.Highlight(IMAGESDICT["YellowHighlight"])
                if "Formation" in tile_values:
                    self.formation_highlights[position] = CustomObjects.Highlight(IMAGESDICT["BlueHighlight"])

            # Re-add associated status sprites
            for position, value in self.tile_info_dict.iteritems():
                if 'Status' in value:
                    for status in value['Status']:
                        status.loadSprites()

    def removeSprites(self):
        self.sprites_loaded_flag = False
        for position, tile in self.tiles.iteritems():
            tile.removeSprites()
        self.map_image = None
        self.loose_tile_sprites = {}
        self.autotiles = {}
        self.layers = [Layer() for _ in range(NUM_LAYERS)]
        # Clear tile_sprites...
        for position, value in self.tile_sprites.iteritems():
            value.removeSprites()
        # Clear sprites in escape_highlights
        self.escape_highlights = {}
        self.formation_highlights = {}
        # Remove associated status sprites if necessary
        for position, value in self.tile_info_dict.iteritems():
            if 'Status' in value:
                for status in value['Status']:
                    status.removeSprites()
        # Remove weather
        self.weather = []

    def destroy(self, tile, gameStateObj):
        destroy_index = self.tile_info_dict[tile.position]['Destructible']
        gameStateObj.message.append(Dialogue.Dialogue_Scene(self.levelfolder + '/destroyScript.txt', destroy_index, tile_pos=tile.position))
        gameStateObj.stateMachine.changeState('dialogue')

    def check_bounds(self, pos):
        if pos[0] >= 0 and pos[1] >= 0 and pos[0] < self.width and pos[1] < self.height:
            return True
        return False

    # Determines whether the position is on the border of the map
    def on_border(self, pos):
        if pos[0] == 0 or pos[1] == 0 or pos[0] == self.width - 1 or pos[1] == self.height - 1:
            return True
        return False

    # Determines which border of the map the position is on
    def which_border(self, pos):
        if pos[1] == 0:
            return [0, -1] # Top
        elif pos[0] == 0:
            return [-1, 0] # Left
        elif pos[0] == self.width - 1:
            return [1, 0] # Right
        elif pos[1] == self.height - 1:
            return [0, 1] # Bottom
        else:
            return [0, 0] # None

    def get_adjacent(self, pos):
        return [adj_pos for adj_pos in [(pos[0], pos[1] - 1), (pos[0] - 1, pos[1]), (pos[0] + 1, pos[1]), (pos[0], pos[1] + 1)] if self.check_bounds(adj_pos)]
        
    def get_tile_from_id(self, tile_id):
        for terrain in TERRAINDATA.getroot().findall('terrain'):
            if tile_id == terrain.find('id').text or tile_id == int(terrain.find('id').text):
                tile = TileObject(terrain.get('name'), terrain.find('minimap').text, terrain.find('platform').text, \
                                  None, terrain.find('mtype').text, \
                                  [terrain.find('DEF').text, terrain.find('AVO').text])
                return tile
        else:
            logger.error('Could not find tile matching id: %s', tile_id)
            return None # Couldn't find any that match id
        
    def parse_tile_info(self, tile_info_location):
        logger.info('Parsing tile info at %s', tile_info_location)
        self.tile_info_dict = {}
        for x in range(self.width):
            for y in range(self.height):
                self.tile_info_dict[(x,y)] = {'Status': []}

        if not os.path.isfile(tile_info_location):
            return None

        tile_info = []
        with open(tile_info_location) as fp:
            tile_info = fp.readlines()

        for line in tile_info:
            logger.debug('Parsing tile info line: %s', line.strip())
            line = line.strip().split(':') # Should split in 2. First half being coordinate. Second half being properties
            coord = line[0].split(',')
            x1 = int(coord[0])
            y1 = int(coord[1])
            if len(coord) > 2:
                x2 = int(coord[2])
                y2 = int(coord[3])
                for i in range(x1, x2+1):
                    for j in range(y1, y2+1):
                        self.parse_tile_line((i, j), line[1].split(';'))
            else:
                self.parse_tile_line((x1, y1), line[1].split(';'))

    def parse_tile_line(self, coord, property_list):
        if property_list:
            for tile_property in property_list:
                property_name, property_value = tile_property.split('=')
                # Handle special cases...
                if property_name == 'Status': # Treasure does not need to be split. It is split by the itemparser function itself.
                    # Turn these string of ids into a list of status objects
                    status_list = []
                    for status in property_value.split(','):
                        status_list.append(StatusObject.statusparser(status))
                    property_value = status_list
                elif property_name in ["Escape", "Arrive"]:
                    self.escape_highlights[coord] = CustomObjects.Highlight(IMAGESDICT["YellowHighlight"])
                elif property_name == "Formation":
                    self.formation_highlights[coord] = CustomObjects.Highlight(IMAGESDICT["BlueHighlight"])
                self.tile_info_dict[coord][property_name] = property_value
        else:
            self.tile_info_dict[coord] = {'Status': []} # Empty Dictionary

    def update(self, gameStateObj):
        current_time = Engine.get_time()

        # Move animations to global
        gameStateObj.allanimations += self.animations
        self.animations = []

        for weather in self.weather:
            weather.update(current_time, gameStateObj)
        self.weather = [weather for weather in self.weather if not weather.remove_me]

        if self.autotiles:
            # Might also try 333? 
            mod_time = current_time%(len(self.autotiles)*484) # 29 ticks
            self.autotile_frame = mod_time/484
            #self.autotile_frame += 1
            #if self.autotile_frame >= len(self.autotiles):
            #    self.autotile_frame = 0

    def initiate_warp_flowers(self, center_pos):
        self.weather.append(Weather.Weather('Warp_Flower', -1, (-1, -1, -1, -1), (self.width, self.height)))
        angle_frac = math.pi/8
        true_pos = center_pos[0] * TILEWIDTH + TILEWIDTH/2, center_pos[1] * TILEHEIGHT + TILEHEIGHT/2
        for speed in [2.0, 2.5]:
            for num in range(0, 16):
                angle = num*angle_frac + angle_frac/2
                self.weather[-1].particles.append(Weather.WarpFlower(true_pos, speed, angle))

    def serialize(self):
        serial_dict = {}
        serial_dict['command_list'] = self.command_list
        serial_dict['HP'] = [(tile.position, tile.currenthp) for position, tile in self.tiles.iteritems() if tile.tilehp]
        return serial_dict

    # === SCRIPT COMMANDS ===
    def replay_commands(self, command_list, currentLevelIndex):
        for line in command_list:
            # Set a custom origin point
            if line[0] == 'set_custom_origin':
                self.custom_origin = line[1]
            # Change tile sprites
            elif line[0] == 'change_tile_sprite' or line[0] == 'change_sprite':
                self.change_sprite(line)
            # Add tile sprite to layer
            elif line[0] == 'layer_tile_sprite':
                self.layer_tile_sprite(line)
            # Show Layer
            elif line[0] == 'show_layer':
                self.show_layer(line)
            # Hide Layer
            elif line[0] == 'hide_layer':
                self.hide_layer(line)
            # Clear Layer
            elif line[0] == 'clear_layer':
                self.clear_layer(line[1])
            # Change one tile
            elif line[0] == 'replace_tile':
                self.replace_tile(line)
            # Change area of tile (must include pic instead of id)
            elif line[0] == 'area_replace_tile':
                self.mass_replace_tile(line)
            # Change one tile's information
            elif line[0] == 'set_tile_info':
                self.set_tile_info(line)
            # Changing whole map tile data!
            elif line[0] == 'load_new_map_tiles':
                self.load_new_map_tiles(line, currentLevelIndex)
            # Changing whole map's sprites!
            elif line[0] == 'load_new_map_sprite':
                self.load_new_map_sprite(line, currentLevelIndex)
            # Reset whole map's tile_info!
            elif line[0] == 'reset_map_tile_info':
                self.reset_tile_info()
            # Add westher
            elif line[0] == 'add_weather':
                self.add_weather(line[1])
            # Remove weather
            elif line[0] == 'remove_weather':
                self.remove_weather(line[1])
            # Add global status
            elif line[0] == 'add_global_status':
                self.add_global_status(line[1])
            # Remove global status
            elif line[0] == 'remove_global_status':
                self.remove_global_status(line[1])

    def get_position(self, pos_line):
        position_list = [self.parse_pos(coord) for coord in pos_line.split('.')]
        return position_list

    def parse_pos(self, pos):
        offset = False
        if pos[0] == 'o': # Offset
            offset = True
            pos = pos[1:]
        new_pos = tuple([int(num) for num in pos.split(',')])
        if offset:
            if self.custom_origin:
                return (self.custom_origin[0] + new_pos[0], self.custom_origin[1] + new_pos[1])
            else:
                return (0, 0)
        else:
            return new_pos 

    def change_sprite(self, line):
        coord = self.parse_pos(line[1])
        transition = None
        if 'fade' in line:
            transition = 'fade'
        elif 'destroy' in line:
            transition = 'destroy'
        self.change_tile_sprites(coord, line[2], transition)

    def layer_tile_sprite(self, line):
        layer = int(line[1])
        coord = self.parse_pos(line[2])
        image_filename = line[3]
        new_sprite = LayerSprite(image_filename, coord, self)
        self.layers[layer].append(new_sprite)

    def show_layer(self, line):
        layer = int(line[1])
        transition = line[2] if len(line) > 2 else None
        if transition == 'fade' or transition == 'destroy':
            self.layers[layer].show = True
            if transition == 'destroy':
                for sprite in self.layers[layer]:
                    x, y = sprite.position
                    self.animations.append(CustomObjects.Animation(IMAGESDICT['Snag'], (x, y - 1), (5, 13), animation_speed = DESTRUCTION_ANIM_TIME/(13*5)))
        else:
            self.layers[layer].show = True
            self.layers[layer].fade = 100          

    def hide_layer(self, line):
        layer = int(line[1])
        transition = line[2] if len(line) > 2 else None
        if transition == 'fade' or transition == 'destroy':
            self.layers[layer].show = False
            if transition == 'destroy':
                for sprite in self.layers[layer]:
                    x, y = sprite.position
                    self.animations.append(CustomObjects.Animation(IMAGESDICT['Snag'], (x, y - 1), (5, 13), animation_speed = DESTRUCTION_ANIM_TIME/(13*5)))
        else:
            self.layers[layer].show = False
            self.layers[layer].fade = 0

    def clear_layer(self, num):
        self.layers[int(num)] = Layer()

    def replace_tile(self, line, grid_manager=None):
        coords = self.get_position(line[1])
        for coord in coords:
            self.tiles[coord] = self.get_tile_from_id(int(line[2]))
            self.tiles[coord].position = coord
            self.opacity_map[coord[0] * self.height + coord[1]] = self.tiles[coord].opaque
            if grid_manager:
                grid_manager.update_tile(self.tiles[coord])
            if 'HP' in self.tile_info_dict[coord]: # Tile hp is needed so apply that here
                self.tiles[coord].give_hp_stat(self.tile_info_dict[coord]['HP'])
        return coords

    def mass_replace_tile(self, line, grid_manager=None):
        coord = self.parse_pos(line[1])
        image_fp = line[2]
        width, height = self.area_replace(coord, image_fp, grid_manager)
        return coord, (width, height)

    def set_tile_info(self, line):
        coord = self.parse_pos(line[1])
        if len(line) > 2:
            self.parse_tile_line(coord, line[2:])
        else:
            self.parse_tile_line(coord, None)

    def load_new_map_tiles(self, line, currentLevelIndex):
        tile_data_suffix = 'Data/Level' + str(currentLevelIndex) + '/TileData' + line[1] + '.png'
        colorkey, width, height = self.build_color_key(Engine.image_load(tile_data_suffix))
        self.width = width
        self.height = height
        self.populate_tiles(colorkey)

    def load_new_map_sprite(self, line, currentLevelIndex):
        map_data_suffix = 'Data/Level' + str(currentLevelIndex) + '/MapSprite' + line[1] + '.png'
        self.mapfilename = map_data_suffix
        self.reset_all_tile_sprites()
        self.loadSprites()

    def reset_tile_info(self, line=None):
        self.tile_info_dict = {}

    # Init weather
    def add_weather(self, weather):
        if weather == "Rain":
            bounds = (-self.height*TILEHEIGHT/4, self.width*TILEWIDTH, -16, -8)
            self.weather.append(Weather.Weather('Rain', .1, bounds, (self.width, self.height)))
        elif weather == "Snow":
            bounds = (-self.height*TILEHEIGHT, self.width*TILEWIDTH, -16, -8)
            self.weather.append(Weather.Weather('Snow', .125, bounds, (self.width, self.height)))
        elif weather == "Sand":
            bounds = (-2*self.height*TILEHEIGHT, self.width*TILEWIDTH, self.height*TILEHEIGHT+16, self.height*TILEHEIGHT+32)
            self.weather.append(Weather.Weather('Sand', .075, bounds, (self.width, self.height)))
        elif weather == "Smoke":
            bounds = (-self.height*TILEHEIGHT, self.width*TILEWIDTH, self.height*TILEHEIGHT, self.height*TILEHEIGHT+16)
            self.weather.append(Weather.Weather('Smoke', .075, bounds, (self.width, self.height)))
        elif weather == "Light":
            bounds = (0, self.width*TILEWIDTH, 0, self.height*TILEHEIGHT)
            self.weather.append(Weather.Weather('Light', .04, bounds, (self.width, self.height)))
        elif weather == "Dark":
            bounds = (0, self.width*TILEWIDTH, 0, self.height*TILEHEIGHT)
            self.weather.append(Weather.Weather('Dark', .04, bounds, (self.width, self.height)))

    def remove_weather(self, name):
        self.weather = [weather for weather in self.weather if weather.name != name]

    def add_global_status(self, s_id):
        self.status_effects.add(s_id)

    def remove_global_status(self, s_id):
        self.status_effects.discard(s_id)

# === GENERIC TILE SPRITE =====================================================
class TileSprite(object):
    transition_speed = 5
    def __init__(self, image_name, position, parent_map):
        self.image_name = image_name
        self.position = position
        self.map_reference = parent_map # Keeps a reference to the parent map
        self.loadSprites()

        self.reset_transition()

    def reset_transition(self):
        self.new_image = None
        self.new_image_name = None
        self.new_position = None

        self.fade = 0

    def loadSprites(self):
        if self.image_name is None:
            self.image = Engine.subsurface(self.map_reference.map_image, (self.position[0]*TILEWIDTH, self.position[1]*TILEHEIGHT, TILEWIDTH, TILEHEIGHT))
        else:
            self.image = Engine.subsurface(self.map_reference.loose_tile_sprites[self.image_name], (self.position[0]*TILEWIDTH, self.position[1]*TILEHEIGHT, TILEWIDTH, TILEHEIGHT))

    def removeSprites(self):
        self.image = None

    def loadNewSprites(self):
        #print(self.new_position)
        rect = (self.new_position[0]*TILEWIDTH, self.new_position[1]*TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
        #print(rect)
        self.new_image = Engine.subsurface(self.map_reference.loose_tile_sprites[self.new_image_name], rect)

    def draw(self, surf, position):
        pos = (position[0] * TILEWIDTH, position[1] * TILEHEIGHT)
        surf.blit(self.image, pos)
        if self.new_image:
            self.fade += self.transition_speed
            new_image = Image_Modification.flickerImageTranslucentColorKey(self.new_image, 100 - self.fade)
            surf.blit(new_image, pos)
            if self.fade >= 100: # Done
                self.image_name = self.new_image_name
                self.position = self.new_position
                self.loadSprites()
                self.reset_transition()

# === GENERIC LAYER SPRITE ======================================
class Layer(object):
    transition_speed = 5
    def __init__(self):
        self.sprites = []
        self.show = False
        self.fade = 0

    def append(self, obj):
        self.sprites.append(obj)

    def __iter__(self):
        return self.sprites

    def draw(self, surf):
        if self.show and self.fade < 100:
            self.fade += self.transition_speed
            for sprite in self.sprites:
                sprite.image = Image_Modification.flickerImageTranslucentColorKey(sprite.true_image, 100 - self.fade)
        elif not self.show and self.fade > 0:
            self.fade -= self.transition_speed
            for sprite in self.sprites:
                sprite.image = Image_Modification.flickerImageTranslucentColorKey(sprite.true_image, 100 - self.fade)
        # Now actually draw
        for sprite in self.sprites:
            sprite.draw(surf)

class LayerSprite(object):
    def __init__(self, image_name, position, parent_map):
        self.image_name = image_name
        self.position = position # True Position
        self.map_reference = parent_map # Keeps a reference to the parent map
        self.loadSprites()

    def loadSprites(self):
        self.true_image = self.map_reference.loose_tile_sprites[self.image_name]
        self.image = self.true_image.copy()

    def removeSprites(self):
        self.true_image = None
        self.image = None

    def draw(self, surf):
        pos = (self.position[0] * TILEWIDTH, self.position[1] * TILEHEIGHT)
        surf.blit(self.image, pos)

# === GENERIC TILE OBJECT =======================================
class TileObject(object):
    def __init__(self, name, minimap, platform, position, mcost, (DEF, AVO)):
        self.name = name
        self.minimap = minimap
        self.platform = platform
        self.mcost = mcost # terrain movement type

        # Stats
        self.position = position
        self.stats = OrderedDict()
        self.stats['DEF'] = int(DEF)
        self.stats['RES'] = self.stats['DEF']
        self.AVO = int(AVO)
        self.light_level = 0 # (0 bright light, 1 dim light, 2 darkness)
        if self.mcost == 'Wall':
            self.opaque = True
        else:
            self.opaque = False

        self.tilehp = False
        self.stats['HP'] = self.currenthp = 0
        self.isDying = False # Whether I have been destroyed

        self.removeSprites()

    def removeSprites(self):
        # Display surface
        self.display_surface = None
        # List of things that could conceivable change without just replacing the tile.
        self.expected_tilehp = None
        self.expected_currenthp = None

    def give_hp_stat(self, hp):
        self.tilehp = True
        self.stats['HP'] = self.currenthp = int(hp)

    def get_mcost(self, unit):
        if isinstance(unit, int):
            return MCOSTDATA[self.mcost][unit]
        elif 'flying' in unit.status_bundle:
            return MCOSTDATA[self.mcost][CONSTANTS['flying_mcost_column']]
        elif 'fleet_of_foot' in unit.status_bundle:
            return MCOSTDATA[self.mcost][CONSTANTS['fleet_mcost_column']]
        return MCOSTDATA[self.mcost][unit.movement_group]

    def getMainWeapon(self):
        return None

    def create_display(self, gameStateObj):
        if self.tilehp:
            back_surf = IMAGESDICT['DestructibleTileInfo'].copy()
            at_icon = ICONDICT['Attackable_Terrain_Icon']
            back_surf.blit(at_icon, (7, back_surf.get_height() - 7 - at_icon.get_height()))
            FONT['small_white'].blit(str(self.currenthp), back_surf, (back_surf.get_width() - FONT['small_white'].size(str(self.currenthp))[0] - 9, 24))
        else:
            back_surf = IMAGESDICT['QuickTileInfo'].copy()
            if self.mcost != 'Wall':
                # Blit DEF Text
                position = back_surf.get_width() - FONT['small_white'].size(str(self.stats['DEF']))[0] - 3, 17
                FONT['small_white'].blit(str(self.stats['DEF']), back_surf, position)
                # Blit AVO Text
                position = back_surf.get_width() - FONT['small_white'].size(str(self.AVO))[0] - 3, 25
                FONT['small_white'].blit(str(self.AVO), back_surf,  position)
        FONT['text_white'].blit(self.name, back_surf, (back_surf.get_width()/2 - FONT['text_white'].size(self.name)[0]/2, 22 - FONT['text_white'].size(self.name)[1]))
        self.display_surface = back_surf

    def getDisplay(self, gameStateObj):
        if self.currenthp != self.expected_currenthp or self.tilehp != self.expected_tilehp:
            self.create_display(gameStateObj)
            self.expected_currenthp = self.currenthp
            self.expected_tilehp = self.tilehp

        return self.display_surface

if __name__ == '__main__':
    print('Use Main.py instead')