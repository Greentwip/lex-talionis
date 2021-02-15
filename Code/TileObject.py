import os, math
from collections import OrderedDict

# Custom imports
from Code.imagesDict import COLORKEY
from . import GlobalConstants as GC
from . import configuration as cf
from . import StatusCatalog, CustomObjects, ItemMethods
from . import Image_Modification, Engine, Weather, Utility, Action
from . import Highlight

import logging
logger = logging.getLogger(__name__)

DESTRUCTION_ANIM_TIME = 500

# === GENERIC MAP OBJECT
class MapObject(object):
    def __init__(self, gameStateObj, mapfilename, tilefilename, levelfolder, weather=None):
        colorkey, self.width, self.height = self.build_color_key(Engine.image_load(tilefilename, convert=True))

        self._tiles = {} # The mechanical information about the tile organized by position
        self.tile_sprites = {} # The sprite information about the tile organized by position
        self.escape_highlights = {}
        self.formation_highlights = {}
        self.origin = None
        self.hp = {}

        self.levelfolder = levelfolder
        self.mapfilename = mapfilename
        self.parse_tile_info(self.levelfolder + '/' + 'tileInfo.txt', gameStateObj)

        self.weather = []
        if weather:
            for name in weather:
                self.add_weather(name)
        self.status_effects = set() # Status ids, not the statuses themselves

        # Layers
        self.layers = []
        self.terrain_layers = []
        self.true_tiles = None # Tiles with layers
        self.true_opacity_map = None

        # Populate tiles
        self.populate_tiles(colorkey)

        self.sprites_loaded_flag = False
        self.is_submap = False
        self.loadSprites()

        self.animations = []
        self.expected_coord = None

    def build_color_key(self, tiledata):
        width = tiledata.get_width()
        height = tiledata.get_height()
        mapObj = [] # Array of map data
    
        # Convert to a mapObj
        for x in range(width):
            mapObj.append([])
        for y in range(height):
            for x in range(width):
                mapObj[x].append(tiledata.get_at((x, y))) # appends [r,g,b,t] value

        return mapObj, width, height

    def populate_tiles(self, colorKeyObj, offset=(0, 0)):
        end_x = offset[0] + len(colorKeyObj)
        for x in range(offset[0], end_x):
            end_y = offset[1] + len(colorKeyObj[x - offset[0]])
            for y in range(offset[1], end_y):
                cur = colorKeyObj[x-offset[0]][y-offset[1]]
                for terrain in GC.TERRAINDATA.getroot().findall('terrain'):
                    colorKey = terrain.find('color').text.split(',')
                    if (int(cur[0]) == int(colorKey[0]) and int(cur[1]) == int(colorKey[1]) and int(cur[2]) == int(colorKey[2])):
                        # Instantiate
                        new_tile = TileObject(int(terrain.find('id').text), terrain.get('name'), terrain.find('minimap').text, terrain.find('platform').text, (x, y),
                                              terrain.find('mtype').text, [terrain.find('DEF').text, terrain.find('AVO').text], self)
                        self._tiles[(x, y)] = new_tile
                        break
                else: # Never found terrain...
                    logger.error('Terrain matching colorkey %s never found.', cur)
        self.true_tiles = None  # Reset tiles
        self.true_opacity_map = None

    def area_replace(self, coord, image_filename, grid_manager):
        colorkey, width, height = self.build_color_key(self.loose_tile_sprites[image_filename])
        self.populate_tiles(colorkey, coord)
        if grid_manager:
            self.update_grid_manager(coord, width, height, grid_manager)
        return width, height

    def update_grid_manager(self, coord, width, height, grid_manager):
        # Remember to update the grid also
        for x in range(coord[0], coord[0] + width):
            for y in range(coord[1], coord[1] + height):
                grid_manager.update_tile(self.tiles[(x, y)])

    def change_tile_sprites(self, coord, image_filename, size, transition=None):
        for x in range(coord[0], coord[0] + size[0]):
            for y in range(coord[1], coord[1] + size[1]):
                if image_filename:
                    pos = (x - coord[0], y - coord[1])
                else:
                    pos = (x, y)
                self.tile_sprites[(x, y)] = TileSprite(None, (x, y), self)
                if transition:
                    self.tile_sprites[(x, y)].new_image_name = image_filename
                    self.tile_sprites[(x, y)].new_position = pos
                    self.tile_sprites[(x, y)].loadNewSprites()
                    if transition == 'destroy':
                        # To be moved to global during next update
                        self.animations.append(CustomObjects.Animation(GC.IMAGESDICT['Snag'], (x, y - 1), (5, 13), animation_speed=DESTRUCTION_ANIM_TIME//(13*5)))
                else:
                    self.tile_sprites[(x, y)].image_name = image_filename
                    self.tile_sprites[(x, y)].position = pos
                    self.tile_sprites[(x, y)].loadSprites()

    # If you change the map, you also need to reset their position to their normal position, and their image name to none,
    # so the tile sprites reference the new map sprite...
    def reset_all_tile_sprites(self):
        for position, tile_sprite in self.tile_sprites.items():
            tile_sprite.position = position
            tile_sprite.image_name = None

    def draw(self, surf, gameStateObj):
        if self.autotiles:
            surf.blit(self.autotiles[self.autotile_frame], (0, 0))
        surf.blit(self.map_image, (0, 0))

        for position, tile in self.tile_sprites.items():
            tile.draw(surf, position)
        
        """    
        need_draw = [position for position in self.tile_sprites if not self.tile_sprites[position].new_image]
        for position in need_draw:
            self.tile_sprites[position].draw(self.map_image, position) # Done, can place on main layer
            del self.tile_sprites[position] # Can delete now that it has been permanently etched onto map image
        """
                
        # Layers
        for layer in self.layers:
            if layer.show or layer.fade > 0:
                layer.draw(surf)

        for pos, highlight in self.escape_highlights.items():
            highlight.draw(surf, pos, gameStateObj.highlight_manager.updateIndex, 0)

        if gameStateObj.stateMachine.getState() in ('prep_formation', 'prep_formation_select'):
            for pos, highlight in self.formation_highlights.items():
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
            for position, tile_values in self.tile_info_dict.items():
                if "Escape" in tile_values or "Arrive" in tile_values:
                    self.escape_highlights[position] = Highlight.Highlight(GC.IMAGESDICT["YellowHighlight"])
                if "Formation" in tile_values:
                    self.formation_highlights[position] = Highlight.Highlight(GC.IMAGESDICT["BlueHighlight"])

            # Re-add associated status sprites
            for position, value in self.tile_info_dict.items():
                if 'Status' in value:
                    for status in value['Status']:
                        status.loadSprites()

    def destroy(self, tile, gameStateObj):
        from . import Dialogue
        if 'Destructible' in self.tile_info_dict[tile.position]:
            destroy_index = self.tile_info_dict[tile.position]['Destructible']
            script_name = self.levelfolder + '/destroyScript.txt'
            if os.path.exists(script_name):
                gameStateObj.message.append(Dialogue.Dialogue_Scene(script_name, name=destroy_index, tile_pos=tile.position))
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
        for terrain in GC.TERRAINDATA.getroot().findall('terrain'):
            if tile_id == terrain.find('id').text or tile_id == int(terrain.find('id').text):
                tile = TileObject(tile_id, terrain.get('name'), terrain.find('minimap').text, terrain.find('platform').text,
                                  None, terrain.find('mtype').text,
                                  [terrain.find('DEF').text, terrain.find('AVO').text], self)
                return tile
        else:
            logger.error('Could not find tile matching id: %s', tile_id)
            return None # Couldn't find any that match id
        
    def parse_tile_info(self, tile_info_location, gameStateObj):
        logger.info('Parsing tile info at %s', tile_info_location)
        self.reset_tile_info()

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
                        self.parse_tile_line((i, j), line[1].split(';'), gameStateObj)
            else:
                self.parse_tile_line((x1, y1), line[1].split(';'), gameStateObj)

    def parse_tile_line(self, coord, property_list, gameStateObj):
        if property_list:
            for tile_property in property_list:
                self.add_tile_property(coord, tile_property.split('='), gameStateObj)
        else:
            # Empty dictionary
            for tile_property in self.tile_info_dict[coord].items():
                self.remove_tile_property_from_name(coord, tile_property[0])

    def add_tile_property(self, coord, tile_property, gameStateObj):
        property_name, property_value = tile_property
        # Handle special cases...
        if property_name == 'Status': # Treasure does not need to be split. It is split by the itemparser function itself.
            # Turn these string of ids into a list of status objects
            if isinstance(property_value, str):
                status_list = []
                for status in property_value.split(','):
                    status_obj = StatusCatalog.statusparser(status, gameStateObj)
                    status_list.append(status_obj)
                property_value = status_list
            else: # Is already a list of statuses
                property_value = property_value
        elif property_name == 'Weapon':
            # For now we're ignoring saving Stationary Weapons, which means they can't have uses...
            property_value = ItemMethods.itemparser(property_value)
        elif property_name in ("Escape", "Arrive"):
            self.escape_highlights[coord] = Highlight.Highlight(GC.IMAGESDICT["YellowHighlight"])
        elif property_name == "Formation":
            self.formation_highlights[coord] = Highlight.Highlight(GC.IMAGESDICT["BlueHighlight"])
        elif property_name == "HP":
            self.hp[coord] = TileHP(int(property_value))
        self.tile_info_dict[coord][property_name] = property_value

    def remove_tile_property_from_name(self, coord, property_name):
        del self.tile_info_dict[coord][property_name]
        if property_name == "HP" and coord in self.hp:
            del self.hp[coord]
        elif property_name in ("Escape", "Arrive") and coord in self.escape_highlights:
            del self.escape_highlights[coord]

    def update(self, gameStateObj):
        current_time = Engine.get_time()

        # Move animations to global
        gameStateObj.allanimations += self.animations
        self.animations = []

        for weather in self.weather:
            weather.update(current_time, gameStateObj)
        self.weather = [weather for weather in self.weather if not weather.remove_me]

        if self.autotiles:
            time = int(GC.FRAMERATE*29)
            mod_time = current_time%(len(self.autotiles)*time) # 29 ticks
            self.autotile_frame = mod_time//time

    def initiate_warp_flowers(self, center_pos):
        self.weather.append(Weather.Weather('Warp_Flower', -1, (-1, -1, -1, -1), (self.width, self.height)))
        angle_frac = math.pi/8
        true_pos = center_pos[0] * GC.TILEWIDTH + GC.TILEWIDTH//2, center_pos[1] * GC.TILEHEIGHT + GC.TILEHEIGHT//2
        for speed in (2.0, 2.5):
            for num in range(0, 16):
                angle = num*angle_frac + angle_frac/2
                self.weather[-1].particles.append(Weather.WarpFlower(true_pos, speed, angle))

    def serialize(self):
        serial_dict = {}
        serial_dict['HP'] = [(pos, hp.currenthp) for pos, hp in self.hp.items()]
        return serial_dict

    def layer_tile_sprite(self, layer, coord, image_filename):
        new_sprite = LayerSprite(image_filename, coord, self)
        while len(self.layers) <= layer:
            self.layers.append(Layer())
        self.layers[layer].append(new_sprite)

    def layer_terrain(self, layer, coord, fn, grid_manager=None):
        while len(self.terrain_layers) <= layer:
            self.terrain_layers.append(TerrainLayer(self))
        self.terrain_layers[layer].add(fn, coord)
        if self.terrain_layers[layer].show:
            self.true_tiles = None  # Reset tiles if we made changes while showing
            self.true_opacity_map = None
            if grid_manager:
                self.handle_grid_manager_with_layer(layer, grid_manager)

    def show_layer(self, layer, transition, grid_manager=None):
        # Image layer
        if len(self.layers) > layer:
            if transition == 'fade' or transition == 'destroy':
                self.layers[layer].show = True
                if transition == 'destroy':
                    for sprite in self.layers[layer]:
                        x, y = sprite.position
                        self.animations.append(CustomObjects.Animation(GC.IMAGESDICT['Snag'], (x, y - 1), (5, 13), animation_speed=DESTRUCTION_ANIM_TIME//(13*5)))
            else:
                self.layers[layer].fullshow()          
        # Terrain layer
        if len(self.terrain_layers) > layer:
            self.terrain_layers[layer].show = True
            self.true_tiles = None  # Reset tiles
            self.true_opacity_map = None
            if grid_manager:
                self.handle_grid_manager_with_layer(layer, grid_manager)

    def hide_layer(self, layer, transition, grid_manager=None):
        # Image layer
        if len(self.layers) > layer:
            if transition == 'fade' or transition == 'destroy':
                self.layers[layer].show = False
                if transition == 'destroy':
                    for sprite in self.layers[layer]:
                        x, y = sprite.position
                        self.animations.append(CustomObjects.Animation(GC.IMAGESDICT['Snag'], (x, y - 1), (5, 13), animation_speed=DESTRUCTION_ANIM_TIME//(13*5)))
            else:
                self.layers[layer].fullhide()
        # Terrain layer
        if len(self.terrain_layers) > layer:
            self.terrain_layers[layer].show = False
            self.true_tiles = None  # Reset tiles
            self.true_opacity_map = None
            if grid_manager:
                self.handle_grid_manager_with_layer(layer, grid_manager)

    def handle_grid_manager_with_layer(self, layer, grid_manager):
        current_layer = self.terrain_layers[layer]
        coords = current_layer._tiles.keys()
        if current_layer.show:  # Determine if anything obstructs each coordinate
            all_higher_coords = {coord for l in self.terrain_layers[layer+1:] for coord in l._tiles.keys() if l.show}
            for coord in coords:
                if coord not in all_higher_coords:  # Nothing's obstructing showing this
                    grid_manager.update_tile(current_layer._tiles[coord])
        else:  # Determine which tile should be shown
            lower_terrain_layers = list(reversed([i for i in self.terrain_layers[:layer] if i.show]))
            all_higher_coords = {coord for l in self.terrain_layers[layer+1:] for coord in l._tiles.keys() if l.show}
            for coord in coords:
                if coord not in all_higher_coords:  # Nothing's obstructing showing a lower level
                    for terrain_layer in lower_terrain_layers:  # Highest first
                        if coord in terrain_layer._tiles:
                            grid_manager.update_tile(terrain_layer._tiles[coord])
                            break
                    else:  # Defaults to base level
                        grid_manager.update_tile(self._tiles[coord])

    def clear_layer(self, layer):
        # Assumes layer is hidden!!!
        if len(self.layers) > layer:
            self.layers[layer] = Layer()
        if len(self.terrain_layers) > layer:
            self.terrain_layers[layer] = TerrainLayer(self)
        self.true_tiles = None
        self.true_opacity_map = None

    def replace_tile(self, coord, tile_id, grid_manager=None):
        self._tiles[coord] = self.get_tile_from_id(tile_id)
        self._tiles[coord].position = coord
        self.true_tiles = None  # Reset
        self.true_opacity_map = None
        if grid_manager:
            grid_manager.update_tile(self.tiles[coord])
        return coord

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

    def reset_tile_info(self):
        self.tile_info_dict = {}
        for x in range(self.width):
            for y in range(self.height):
                self.tile_info_dict[(x, y)] = {}

    # Init weather
    def add_weather(self, weather):
        if weather == "Rain":
            bounds = (-self.height*GC.TILEHEIGHT//4, self.width*GC.TILEWIDTH, -16, -8)
            self.weather.append(Weather.Weather('Rain', .1, bounds, (self.width, self.height)))
        elif weather == "Snow":
            bounds = (-self.height*GC.TILEHEIGHT, self.width*GC.TILEWIDTH, -16, -8)
            self.weather.append(Weather.Weather('Snow', .125, bounds, (self.width, self.height)))
        elif weather == "Sand":
            bounds = (-2*self.height*GC.TILEHEIGHT, self.width*GC.TILEWIDTH, self.height*GC.TILEHEIGHT+16, self.height*GC.TILEHEIGHT+32)
            self.weather.append(Weather.Weather('Sand', .075, bounds, (self.width, self.height)))
        elif weather == "Smoke":
            bounds = (-self.height*GC.TILEHEIGHT, self.width*GC.TILEWIDTH, self.height*GC.TILEHEIGHT, self.height*GC.TILEHEIGHT+16)
            self.weather.append(Weather.Weather('Smoke', .075, bounds, (self.width, self.height)))
        elif weather == "Light":
            bounds = (0, self.width*GC.TILEWIDTH, 0, self.height*GC.TILEHEIGHT)
            self.weather.append(Weather.Weather('Light', .04, bounds, (self.width, self.height)))
        elif weather == "Dark":
            bounds = (0, self.width*GC.TILEWIDTH, 0, self.height*GC.TILEHEIGHT)
            self.weather.append(Weather.Weather('Dark', .04, bounds, (self.width, self.height)))
        elif weather == "Fire":
            bounds = (0, GC.WINWIDTH, GC.WINHEIGHT, GC.WINHEIGHT+16)
            self.weather.append(Weather.Weather('Fire', .05, bounds, (GC.TILEX, GC.TILEY), blend=GC.IMAGESDICT['FireBG']))

    def remove_weather(self, name):
        self.weather = [weather for weather in self.weather if weather.name != name]

    def add_global_status(self, s_id, gameStateObj):
        if any(status.id == s_id for status in self.status_effects):
            return  # No stacking at all of global statuses
        status_obj = StatusCatalog.statusparser(s_id, gameStateObj)
        self.status_effects.add(status_obj)
        for unit in gameStateObj.allunits:
            if unit.position:
                Action.do(Action.AddStatus(unit, status_obj), gameStateObj)

    def remove_global_status(self, s_id, gameStateObj):
        if not any(status.id == s_id for status in self.status_effects):
            return  # Must have the right status to remove
        status_obj = [status for status in self.status_effects if status.id == s_id][0]
        self.status_effects.discard(status_obj)
        for unit in gameStateObj.allunits:
            if unit.position:
                Action.do(Action.RemoveStatus(unit, status_obj), gameStateObj)

    def create_display(self, coord, gameStateObj):
        if coord in self.hp:
            self.expected_coord = None  # Let HP tiles change all the time
            back_surf = GC.IMAGESDICT['DestructibleTileInfo'].copy()
            at_icon = GC.ICONDICT['Attackable_Terrain_Icon']
            back_surf.blit(at_icon, (7, back_surf.get_height() - 7 - at_icon.get_height()))
            v = str(self.hp[coord].currenthp)
            GC.FONT['small_white'].blit(v, back_surf, (back_surf.get_width() - GC.FONT['small_white'].size(v)[0] - 9, 24))
        else:
            self.expected_coord = coord
            back_surf = GC.IMAGESDICT['QuickTileInfo'].copy()
            if self.tiles[coord].mcost != 'Wall':
                # Blit DEF Text
                def_text = str(self.tiles[coord].stats['DEF'])
                position = back_surf.get_width() - GC.FONT['small_white'].size(def_text)[0] - 3, 17
                GC.FONT['small_white'].blit(def_text, back_surf, position)
                # Blit AVO Text
                avo_text = str(self.tiles[coord].AVO)
                position = back_surf.get_width() - GC.FONT['small_white'].size(avo_text)[0] - 3, 25
                GC.FONT['small_white'].blit(avo_text, back_surf, position)
        name = self.tiles[coord].name
        pos = (back_surf.get_width()//2 - GC.FONT['text_white'].size(name)[0]//2, 22 - GC.FONT['text_white'].size(name)[1])
        GC.FONT['text_white'].blit(name, back_surf, pos)

        self.display_surface = back_surf

    def getDisplay(self, coord, gameStateObj):
        if coord != self.expected_coord:
            self.create_display(coord, gameStateObj)
        return self.display_surface

    def get_tiles(self):
        if not self.true_tiles:
            # Base layer
            tiles = self._tiles.copy()
            # Extra layers
            for terrain_layer in self.terrain_layers:
                if terrain_layer.show:
                    tiles = terrain_layer.overwrite(tiles)
            self.true_tiles = tiles
        return self.true_tiles

    tiles = property(get_tiles)

    def get_opacity_map(self):
        if not self.true_opacity_map:
            opacity_map = [False for _ in range(self.width*self.height)]
            for coord, tile in self.tiles.items():
                opacity_map[coord[0] * self.height + coord[1]] = tile.opaque
            self.true_opacity_map = opacity_map
        return self.true_opacity_map

    opacity_map = property(get_opacity_map)

# === GENERIC TILE SPRITE =====================================================
class TileSprite(object):
    transition_speed = 5

    def __init__(self, image_name, position, parent_map):
        self.image_name = image_name
        self.position = position
        self.map_reference = parent_map # Keeps a reference to the parent map
        self.reset_transition()
        self.loadSprites()

    def reset_transition(self):
        self.new_image = None
        self.new_image_name = None
        self.new_position = None

        self.fade = 0

    def loadSprites(self):
        rect = (self.position[0]*GC.TILEWIDTH, self.position[1]*GC.TILEHEIGHT, GC.TILEWIDTH, GC.TILEHEIGHT)
        if self.image_name is None:
            self.image = Engine.subsurface(self.map_reference.map_image, rect)
            self.image = self.image.convert()
        else:
            self.image = Engine.subsurface(self.map_reference.loose_tile_sprites[self.image_name], rect)
            self.image = self.image.convert()

    def removeSprites(self):
        self.image = None

    def loadNewSprites(self):
        rect = (self.new_position[0]*GC.TILEWIDTH, self.new_position[1]*GC.TILEHEIGHT, GC.TILEWIDTH, GC.TILEHEIGHT)
        self.new_image = Engine.subsurface(self.map_reference.loose_tile_sprites[self.new_image_name], rect)
        self.new_image = self.new_image.convert()

    def draw(self, surf, position):
        pos = (position[0] * GC.TILEWIDTH, position[1] * GC.TILEHEIGHT)
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
        return iter(self.sprites)

    def remove(self, image_name, position):
        self.sprites = [s for s in self.sprites if s.image_name != image_name or s.position != position]

    def fullshow(self):
        self.show = True
        self.fade = 100
        for sprite in self.sprites:
            sprite.image = Image_Modification.flickerImageTranslucentColorKey(sprite.true_image, 0)

    def fullhide(self):
        self.show = False
        self.fade = 0
        for sprite in self.sprites:
            sprite.image = Image_Modification.flickerImageTranslucentColorKey(sprite.true_image, 100)

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
        pos = (self.position[0] * GC.TILEWIDTH, self.position[1] * GC.TILEHEIGHT)
        surf.blit(self.image, pos)

class TerrainLayer(object):
    def __init__(self, parent_map):
        self.map_reference = parent_map
        self._tiles = {}
        self.show = False

    def overwrite(self, tiles):
        for position, tile in self._tiles.items():
            tiles[position] = tile
        return tiles

    def add(self, image_name, position):
        image = self.map_reference.loose_tile_sprites[image_name]
        color_key_obj, width, height = self.map_reference.build_color_key(image)
        self.populate_tiles(color_key_obj, position)

    def reset(self, old_terrain_ids):
        self._tiles = {}
        for position, tile_id in old_terrain_ids.items():
            for terrain in GC.TERRAINDATA.getroot().findall('terrain'):
                if int(terrain.find('id').text) == tile_id:
                    new_tile = TileObject(tile_id, terrain.get('name'), terrain.find('minimap').text, terrain.find('platform').text, position,
                                          terrain.find('mtype').text, [terrain.find('DEF').text, terrain.find('AVO').text], self.map_reference)
                    self._tiles[position] = new_tile
                    break

    def populate_tiles(self, color_key_obj, offset):
        for x in range(len(color_key_obj)):
            for y in range(len(color_key_obj[x])):
                cur = color_key_obj[x][y]
                for terrain in GC.TERRAINDATA.getroot().findall('terrain'):
                    colorKey = terrain.find('color').text.split(',')
                    if (int(cur[0]) == int(colorKey[0]) and int(cur[1]) == int(colorKey[1]) and int(cur[2]) == int(colorKey[2])):
                        # Instantiate
                        pos = (offset[0] + x, offset[1] + y)
                        new_tile = TileObject(int(terrain.find('id').text), terrain.get('name'), terrain.find('minimap').text, terrain.find('platform').text, pos,
                                              terrain.find('mtype').text, [terrain.find('DEF').text, terrain.find('AVO').text], self.map_reference)
                        self._tiles[pos] = new_tile
                        break
                else: # Never found terrain...
                    logger.error('Terrain matching colorkey %s never found.', cur)

# === GENERIC TILE OBJECT =======================================
class TileObject(object):
    def __init__(self, tile_id, name, minimap, platform, position, mcost, stats, map_ref):
        self.tile_id = tile_id
        self.map_ref = map_ref
        DEF, AVO = stats 
        self.name = name
        self.minimap = minimap
        self.platform = platform
        self.mcost = mcost # terrain movement type

        # Stats
        self.position = position
        # print(self.position)
        assert not self.position or type(self.position) == tuple
        self.stats = OrderedDict()
        self.stats['DEF'] = int(DEF)
        self.stats['RES'] = self.stats['DEF']
        self.AVO = int(AVO)
        self.light_level = 0 # (0 bright light, 1 dim light, 2 darkness)
        if self.mcost == 'Wall':
            self.opaque = True
        else:
            self.opaque = False

        self.isDying = False # Whether I have been destroyed

        self.stats['HP'] = self.currenthp

    def get_mcost(self, unit):
        if isinstance(unit, int):
            return GC.MCOSTDATA[self.mcost][unit]
        elif 'flying' in unit.status_bundle:
            return GC.MCOSTDATA[self.mcost][cf.CONSTANTS['flying_mcost_column']]
        elif 'fleet_of_foot' in unit.status_bundle:
            return GC.MCOSTDATA[self.mcost][cf.CONSTANTS['fleet_mcost_column']]
        return GC.MCOSTDATA[self.mcost][unit.movement_group]

    def getMainWeapon(self):
        return None

    def get_hp(self):
        if self.position in self.map_ref.hp:
            return self.map_ref.hp[self.position].currenthp
        else:
            return 0

    def set_hp(self, value):
        if self.position in self.map_ref.hp:
            self.map_ref.hp[self.position].set_hp(value)

    def change_hp(self, dhp):
        if self.position in self.map_ref.hp:
            self.map_ref.hp[self.position].change_hp(dhp)

    currenthp = property(get_hp, set_hp)

# === Tile HP Object =====================================================
class TileHP(object):
    def __init__(self, hp):
        self.stats = {}
        self.stats['HP'] = self.currenthp = int(hp)

    def change_hp(self, dhp):
        self.currenthp += int(dhp)
        self.currenthp = Utility.clamp(self.currenthp, 0, int(self.stats['HP']))

    def set_hp(self, hp):
        self.currenthp = int(hp)
        self.currenthp = Utility.clamp(self.currenthp, 0, int(self.stats['HP']))
