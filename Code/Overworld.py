import os

from . import GlobalConstants as GC
from . import configuration as cf
from . import StateMachine, SaveLoad, Dialogue, MenuFunctions, CustomObjects
from . import Utility, Engine, InputManager, Image_Modification
from . import GenericMapSprite, BaseMenuSurf

class OverworldCursor(object):
    image = GC.IMAGESDICT['OverworldCursor']
    width = 16
    height = 16
    icon_states = (0, 0, 1, 2, 3, 4, 5, 6, 6, 5, 4, 3, 2, 1)

    def __init__(self, overworld):
        self.x, self.y = 0, 0
        self.overworld = overworld
        self.speed = 8

        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed']/2)

        self.counter = 0
        self.icon_state_counter = 0

        self.overworld_info = None
        self.remove_overworld_info = True
        self.overworld_info_offset = -72

    def get_position(self):
        return self.x, self.y

    def set_cursor(self, pos, overworld):
        print('Setting Cursor to:', pos)
        self.remove_overworld_info = True
        self.x, self.y = pos
        overworld.next_x = Utility.clamp(overworld.next_x, max(0, self.x - GC.WINWIDTH + 48), min(overworld.width - GC.WINWIDTH, self.x - 48))
        overworld.next_y = Utility.clamp(overworld.next_y, max(0, self.y - GC.WINHEIGHT + 48), min(overworld.height - GC.WINHEIGHT, self.y - 48))

    def handle_movement(self, gameStateObj):
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        # Normal movement
        if 'LEFT' in directions and self.x > 0:
            self.x -= self.speed
            self.remove_overworld_info = True
            if self.x <= self.overworld.next_x + 48: # Cursor controls camera movement
                # Set x is move the camera. Move it to its x_pos - 1, cause we're moving left
                self.overworld.change_x(-self.speed)
        elif 'RIGHT' in directions and self.x < (self.overworld.width - self.width):
            self.x += self.speed
            self.remove_overworld_info = True
            if self.x >= (self.overworld.next_x + GC.WINWIDTH - 48):
                self.overworld.change_x(self.speed)
        if 'UP' in directions and self.y > self.height:
            self.y -= self.speed
            self.remove_overworld_info = True
            if self.y <= self.overworld.next_y + 48:
                self.overworld.change_y(-self.speed)
        elif 'DOWN' in directions and self.y < (self.overworld.height):
            self.y += self.speed
            self.remove_overworld_info = True
            if self.y >= (self.overworld.next_y + GC.WINHEIGHT - 48):
                self.overworld.change_y(self.speed)

    def create_info(self, cur_party, cur_location, gameStateObj):
        if cur_party is not None:
            overworld_info = GC.IMAGESDICT['OverworldInfo'].copy()
            location_name = gameStateObj.overworld.locations[cur_party.location_id].name
            l_size = GC.FONT['text_white'].size(location_name)[0]
            GC.FONT['text_white'].blit(location_name, overworld_info, (48 - l_size/2, 8))
            party_name = cur_party.lords[0]
            p_size = GC.FONT['info_grey'].size(party_name)[0]
            GC.FONT['info_grey'].blit(party_name, overworld_info, (66 - p_size/2, 32))
            GC.FONT['text_white'].blit('Units', overworld_info, (44, 46))
            num_units = len(gameStateObj.get_units_in_party(cur_party.party_id))
            GC.FONT['text_white'].blit(str(num_units), overworld_info, (85 - GC.FONT['text_white'].size(str(num_units))[0], 46))
            try:
                portrait = Engine.subsurface(GC.UNITDICT[party_name + 'Portrait'], (96, 16, 32, 32))
            except KeyError:
                portrait = GC.UNITDICT.get('MonsterEmblem', None)
            if portrait:
                overworld_info.blit(portrait, (8, 32))
        else:
            if cur_location is not None:
                overworld_info = GC.IMAGESDICT['OverworldInfoSmall'].copy()
                location_name = cur_location.name
                l_size = GC.FONT['text_white'].size(location_name)[0]
                GC.FONT['text_white'].blit(location_name, overworld_info, (48 - l_size/2, 8))
        return overworld_info

    def draw_info(self, surf, cur_party, cur_location, gameStateObj):
        if self.remove_overworld_info:
            if cur_party is not None or cur_location is not None:
                self.remove_overworld_info = False
                self.overworld_info = self.create_info(cur_party, cur_location, gameStateObj)
                # self.overworld_info_offset = min(self.overworld_info.get_height(), self.overworld_info_offset)
            elif self.overworld_info:
                self.overworld_info_offset -= 18
                if self.overworld_info_offset < -72:
                    self.overworld_info = None
        else:
            self.overworld_info_offset += 18
            self.overworld_info_offset = min(0, self.overworld_info_offset)

        if self.overworld_info:
            cursor_pos = gameStateObj.overworld.cursor.get_position()
            if cursor_pos[0] - gameStateObj.overworld.x > GC.WINWIDTH/2:
                info_pos = (0, self.overworld_info_offset)
            else:
                info_pos = (136, self.overworld_info_offset)
            surf.blit(self.overworld_info, info_pos)

    def draw(self, surf):
        self.counter += 1
        if self.counter >= 4:
            self.icon_state_counter += 1
            self.counter = 0

        which_icon = self.icon_states[self.icon_state_counter%len(self.icon_states)]
        image = Engine.subsurface(self.image, (0, which_icon*self.height, self.width, self.height))
        surf.blit(image, (self.x - self.overworld.x, self.y - self.height - self.overworld.y))

class OverworldLocation(object):
    icons = GC.IMAGESDICT['OverworldIcons']
    next_icon = GC.IMAGESDICT['OverworldNextIcon']
    icon_size = 32
    show_anim = GC.IMAGESDICT['OverworldShowAnim']

    def __init__(self, data):
        self.level_id = data['level_id']
        self.name = data['location_name']
        self.icon_idx = data['icon_idx']
        self.position = data['position']
        self.image = Engine.subsurface(self.icons, (0, self.icon_size * self.icon_idx, self.icon_size, self.icon_size))
        self.show = False
        self.display_flag = False
        self.visited = False

        self.counter = 0
        self.transparency = 0
        self.state = 'normal'

    def get_position(self):
        return self.position[0]*8, self.position[1]*8

    def draw(self, surf):
        self.counter += 1
        if self.state == 'fade_in':
            self.transparency -= 5
            if self.transparency <= 0:
                self.transparency = 0
                self.state = 'normal'
        elif self.state == 'fade_out':
            self.transparency += 5
            if self.transparency >= 100:
                self.transparency = 100
                self.show = False
                self.state = 'normal'

        if self.show:
            pos = self.get_draw_pos()
            image = Image_Modification.flickerImageTranslucent(self.image, self.transparency)
            surf.blit(image, pos)
            if self.display_flag:
                # Next icon every 13 frames -- there are four icons
                which_icon = self.counter//13%4
                icon = Engine.subsurface(self.next_icon, (32*which_icon, 0, 32, 32))
                icon = Image_Modification.flickerImageTranslucent(icon, self.transparency)
                surf.blit(icon, (pos[0], pos[1] - 16))

        if self.state == 'anim_in':
            remove = self.anim.update()
            if remove:
                self.state = 'fade_in'
                self.anim = None
                self.show = True
            else:
                self.anim.draw(surf)

    def get_draw_pos(self):
        return (self.position[0]*8 - self.icon_size/2, self.position[1]*8 - self.icon_size/2)

    def fade_in(self):
        self.transparency = 100
        self.state = 'anim_in'
        position = self.get_draw_pos()
        position = position[0] - 16, position[1] - 16
        self.anim = CustomObjects.Animation(self.show_anim, position, (4, 4), animation_speed=66, ignore_map=True)
        self.anim.tint = True

    def fade_out(self):
        self.state = 'fade_out'

    def serialize(self):
        return (self.show, self.display_flag, self.visited)

    def deserialize(self, data):
        if not data:
            return
        self.show, self.display_flag, self.visited = data

class OverworldRoute(object):
    route_sheet = GC.IMAGESDICT['OverworldRoutes']
    top_horiz = Engine.subsurface(route_sheet, (8 * 1, 0, 8, 8))
    bottom_horiz = Engine.subsurface(route_sheet, (8 * 2, 0, 8, 8))
    left_vert = Engine.subsurface(route_sheet, (8 * 3, 0, 8, 8))
    right_vert = Engine.subsurface(route_sheet, (8 * 4, 0, 8, 8))
    backslash = Engine.subsurface(route_sheet, (8 * 6, 0, 8, 8))
    forwardslash = Engine.flip_horiz(backslash)

    def __init__(self, connection, pos1, pos2, route):
        self.connection = connection
        self.pos1 = pos1
        self.pos2 = pos2
        self.route = route

        self.show = False

        self.create_image()

        # For fading in and out
        self.transparency = 0
        self.state = 'normal'

    def create_image(self):
        width = abs(sum(-1 for route in self.route if route in (1, 4, 7)) + sum(1 for route in self.route if route in (3, 6, 9)))
        height = abs(sum(-1 for route in self.route if route in (7, 8, 9)) + sum(1 for route in self.route if route in (1, 2, 3)))
        self.image = Engine.create_surface((width*8 + 16, height*8 + 16), transparent=True)
        if self.pos1[0] <= self.pos2[0]:
            if self.pos1[1] <= self.pos2[1]:
                cur_x, cur_y = 0, 0
                self.topleft = self.pos1
            else:
                cur_x, cur_y = 0, height
                self.topleft = (self.pos1[0], self.pos2[1])
        else:
            if self.pos1[1] < self.pos2[1]:
                cur_x, cur_y = width, 0
                self.topleft = (self.pos2[0], self.pos1[1])
            else:
                cur_x, cur_y = width, height
                self.topleft = self.pos2
        for route in self.route:
            if route == 1:
                self.image.blit(self.forwardslash, (cur_x*8 - 8, cur_y*8))
                cur_x -= 1
                cur_y += 1
            elif route == 2:
                self.image.blit(self.left_vert, (cur_x*8 - 8, cur_y*8))
                self.image.blit(self.right_vert, (cur_x*8, cur_y*8))
                cur_y += 1
            elif route == 3:
                self.image.blit(self.backslash, (cur_x*8, cur_y*8))
                cur_x += 1
                cur_y += 1
            elif route == 4:
                self.image.blit(self.top_horiz, (cur_x*8 - 8, cur_y*8 - 8))
                self.image.blit(self.bottom_horiz, (cur_x*8 - 8, cur_y*8))
                cur_x -= 1
            elif route == 6:
                self.image.blit(self.top_horiz, (cur_x*8, cur_y*8 - 8))
                self.image.blit(self.bottom_horiz, (cur_x*8, cur_y*8))
                cur_x += 1
            elif route == 7:
                self.image.blit(self.backslash, (cur_x*8 - 8, cur_y*8 - 8))
                cur_x -= 1
                cur_y -= 1
            elif route == 8:
                self.image.blit(self.left_vert, (cur_x*8 - 8, cur_y*8 - 8))
                self.image.blit(self.right_vert, (cur_x*8, cur_y*8 - 8))
                cur_y -= 1
            elif route == 9:
                self.image.blit(self.forwardslash, (cur_x*8, cur_y*8 - 8))
                cur_x += 1
                cur_y -= 1

    def fade_in(self):
        self.state = 'fade_in'
        self.transparency = 100
        self.show = True

    def fade_out(self):
        self.state = 'fade_out'

    def draw(self, surf):
        if self.state == 'fade_in':
            self.transparency -= 4
            if self.transparency <= 0:
                self.transparency = 0
                self.state = 'normal'
        elif self.state == 'fade_out':
            self.transparency += 5
            if self.transparency >= 100:
                self.transparency = 100
                self.show = False
                self.state = 'normal'

        if self.show:
            image = Image_Modification.flickerImageTranslucent(self.image, self.transparency)
            surf.blit(image, (self.topleft[0]*8, self.topleft[1]*8))

    def serialize(self):
        return self.show

    def deserialize(self, data):
        if not data:
            return
        self.show = data

class OverworldParty(object):
    def __init__(self, party_id, location_id, position, lords, gameStateObj):
        self.party_id = party_id
        self.location_id = location_id
        self.lords = lords
        self.next_position = []
        self.next_location_id = None
        self.current_move = None
        self.sprites = []
        for lord in self.lords:
            unit = gameStateObj.get_unit_from_id(lord)
            gender = 'M' if unit.gender < 5 else 'F'
            pos = self.mod_pos(position)
            self.sprites.append(GenericMapSprite.GenericMapSprite(unit.klass, gender, 'player', pos))

    def move(self, next_location_id, gameStateObj):
        self.next_position = gameStateObj.overworld.get_route(self.location_id, next_location_id, gameStateObj)
        self.location_id = None
        self.next_location_id = next_location_id
        self.current_move = self.mod_pos(self.next_position.pop())
        for sprite in self.sprites:
            sprite.set_target(self.current_move)
        return len(self.next_position) + 1

    def select(self):
        for sprite in self.sprites:
            sprite.selected = True

    def deselect(self):
        for sprite in self.sprites:
            sprite.selected = False

    def hover_over(self):
        for sprite in self.sprites:
            sprite.hovered = True

    def quick_move(self, next_location_id, gameStateObj):
        self.location_id = next_location_id
        position = gameStateObj.overworld.locations[next_location_id].get_position()
        for sprite in self.sprites:
            sprite.teleport(position)

    def update(self):
        for sprite in self.sprites:
            sprite.update()
        # Check if done moving
        if not self.isMoving():
            if self.next_position:
                self.current_move = self.mod_pos(self.next_position.pop())
                for sprite in self.sprites:
                    sprite.set_target(self.current_move)
            elif self.location_id is None:
                self.location_id = self.next_location_id
                self.next_location_id = None
                self.next_position = []
                self.current_move = None

    def isMoving(self):
        return any(sprite.isMoving for sprite in self.sprites)

    def mod_pos(self, position):
        return position[0] - 8, position[1] - 8

    def draw(self, surf):
        for sprite in self.sprites:
            sprite.draw(surf)
            sprite.hovered = False

    def serialize(self):
        return self.party_id, self.location_id, self.lords

    @classmethod
    def deserialize(cls, data, overworld, gameStateObj):
        if not data:
            return None
        location_id = data[1]
        position = overworld.locations[location_id].get_position()            
        s = cls(data[0], location_id, position, data[2], gameStateObj)
        return s

class Overworld(object):
    def __init__(self):
        self.x, self.y = 0, 0
        self.next_x, self.next_y = 0, 0
        self.camera_speed = 8.0

        self.main_sprite = GC.IMAGESDICT['OverworldSprite']
        self.width, self.height = self.main_sprite.get_width(), self.main_sprite.get_height()

        self.locations = {location_data['level_id']: OverworldLocation(location_data) for location_data in GC.OVERWORLDDATA['Locations']}
        self.create_routes()
        self.parties = {}
        self.last_party = None

        self.cursor = OverworldCursor(self)

        self.triggers = []

    def create_routes(self):
        self.routes = {}
        for route in GC.OVERWORLDDATA['Routes']:
            connection = route['connection']
            loc1, loc2 = self.locations[connection[0]], self.locations[connection[1]]
            self.routes[connection] = OverworldRoute(connection, loc1.position, loc2.position, route['route'])

    def autocursor(self):
        if self.last_party is not None:
            last_party = self.parties[self.last_party]
            self.cursor.set_cursor(self.locations[last_party.location_id].get_position(), self)

    def change_x(self, dx):
        self.next_x = Utility.clamp(self.next_x + dx, 0, self.width - GC.WINWIDTH)

    def change_y(self, dy):
        self.next_y = Utility.clamp(self.next_y + dy, 0, self.height - GC.WINHEIGHT)

    def update(self, gameStateObj):
        if gameStateObj.current_party is not None:
            cur_party = self.parties[gameStateObj.current_party]
            if cur_party.isMoving() and cur_party.current_move:
                pos = cur_party.current_move
            elif cur_party.location_id is not None:
                pos = self.locations[cur_party.location_id].get_position()
            self.next_x = Utility.clamp(pos[0] - GC.WINWIDTH/2, 0, self.width - GC.WINWIDTH)
            self.next_y = Utility.clamp(pos[1] - GC.WINHEIGHT/2, 0, self.height - GC.WINHEIGHT)
        # actually move camera
        if self.next_x > self.x:
            self.x += (self.next_x - self.x)/self.camera_speed
        elif self.next_x < self.x:
            self.x -= (self.x - self.next_x)/self.camera_speed
        if self.next_y > self.y:
            self.y += (self.next_y - self.y)/self.camera_speed
        elif self.next_y < self.y:
            self.y -= (self.y - self.next_y)/self.camera_speed
        if abs(self.next_x - self.x) < 0.25:
            self.x = self.next_x
        if abs(self.next_y - self.y) < 0.25:
            self.y = self.next_y

    def show_location(self, level_id):
        self.locations[level_id].fade_in()
        self.cursor.set_cursor(self.locations[level_id].get_position(), self)
        # Handle adjacent routes
        for route_id, route in self.routes.items():
            if level_id == route_id[0]:
                if self.locations[route_id[1]].show:
                    route.fade_in()
            elif level_id == route_id[1]:
                if self.locations[route_id[0]].show:
                    route.fade_in()

    def hide_location(self, level_id):
        self.locations[level_id].fade_out()
        for route_id, route in self.routes.items():
            if level_id == route_id[0]:
                if self.locations[route_id[1]].show:
                    route.fade_out()
            elif level_id == route_id[1]:
                if self.locations[route_id[0]].show:
                    route.fade_out()

    def quick_show_location(self, level_id):
        self.locations[level_id].show = True
        # Handle adjacent routes
        for route_id, route in self.routes.items():
            if level_id == route_id[0]:
                if self.locations[route_id[1]].show:
                    route.show = True
            elif level_id == route_id[1]:
                if self.locations[route_id[0]].show:
                    route.show = True

    def set_next_location(self, level_id):
        for location in self.locations.values():
            location.display_flag = False
        if level_id:
            self.locations[level_id].display_flag = True

    def get_route(self, loc_id1, loc_id2, gameStateObj):
        sorted_routes = sorted([loc_id1, loc_id2])
        route_name = tuple(sorted_routes)
        route = self.routes[route_name]
        cur_x, cur_y = self.locations[loc_id1].position
        overall_path = []
        if route_name[0] != loc_id1:  # route is backwards
            route_path = list(reversed(route.route))
        else:
            route_path = list(route.route)
        for path in route_path:
            if route_name[0] != loc_id1:  # route is backwards
                path = 10 - path  # Run route backwards
            if path == 1:
                cur_x -= 1
                cur_y += 1
            elif path == 2:
                cur_y += 1
            elif path == 3:
                cur_x += 1
                cur_y += 1
            elif path == 4:
                cur_x -= 1
            elif path == 6:
                cur_x += 1
            elif path == 7:
                cur_x -= 1
                cur_y -= 1
            elif path == 8:
                cur_y -= 1
            elif path == 9:
                cur_x += 1
                cur_y -= 1
            overall_path.append((cur_x*8, cur_y*8))
        return list(reversed(overall_path))

    def move_party(self, level_id, party_id, gameStateObj):
        route_length = self.parties[party_id].move(level_id, gameStateObj)
        return route_length

    def quick_move_party(self, level_id, party_id, gameStateObj):
        self.parties[party_id].quick_move(level_id, gameStateObj)

    def add_party(self, level_id, party_id, lords, gameStateObj):
        position = self.locations[level_id].get_position()
        self.parties[party_id] = OverworldParty(party_id, level_id, position, lords, gameStateObj)

    def remove_party(self, party_id):
        del self.parties[party_id]

    def get_current_hovered_party(self):
        cursor_pos = self.cursor.get_position()
        for name, party in self.parties.items():
            if party.location_id is not None:
                party_pos = self.locations[party.location_id].get_position()
                if party_pos == cursor_pos:
                    return party
        return None

    def get_current_hovered_location(self):
        cursor_pos = self.cursor.get_position()
        for loc_id, location in self.locations.items():
            if location.show:
                loc_pos = location.get_position()
                if loc_pos == cursor_pos:
                    return location
        return None

    def get_location(self, location_id, direction):
        valid_directions = {i: None for i in range(1, 10)}
        for name, route in self.routes.items():
            if route.show and location_id in name:
                if location_id == name[0]:
                    valid_directions[route.route[0]] = name[1]
                else:
                    valid_directions[10 - route.route[-1]] = name[0]
        if direction == 'UP':
            if valid_directions[8]:
                return valid_directions[8]
            if valid_directions[7] and not valid_directions[9]:
                return valid_directions[7]
            if valid_directions[9] and not valid_directions[7]:
                return valid_directions[9]
            if valid_directions[7] and valid_directions[9]:
                if valid_directions[4]:
                    return valid_directions[7]
                else:
                    return valid_directions[9]
        elif direction == 'LEFT':
            if valid_directions[4]:
                return valid_directions[4]
            if valid_directions[7] and not valid_directions[1]:
                return valid_directions[7]
            if valid_directions[1] and not valid_directions[7]:
                return valid_directions[1]
            if valid_directions[7] and valid_directions[1]:
                if valid_directions[2]:
                    return valid_directions[1]
                else:
                    return valid_directions[7]
        elif direction == 'RIGHT':
            if valid_directions[6]:
                return valid_directions[6]
            if valid_directions[9] and not valid_directions[3]:
                return valid_directions[9]
            if valid_directions[3] and not valid_directions[9]:
                return valid_directions[3]
            if valid_directions[9] and valid_directions[3]:
                if valid_directions[8]:
                    return valid_directions[9]
                else:
                    return valid_directions[3]
        elif direction == 'DOWN':
            if valid_directions[2]:
                return valid_directions[2]
            if valid_directions[1] and not valid_directions[3]:
                return valid_directions[1]
            if valid_directions[3] and not valid_directions[1]:
                return valid_directions[3]
            if valid_directions[1] and valid_directions[3]:
                if valid_directions[6]:
                    return valid_directions[3]
                else:
                    return valid_directions[1]
        return None

    def draw(self, surf, gameStateObj=None, show_cursor=True):
        image = Engine.copy_surface(self.main_sprite)
        for route in self.routes.values():
            route.draw(image)
        for location in self.locations.values():
            location.draw(image)
        for party in self.parties.values():
            party.update()
            party.draw(image)
        image = Engine.subsurface(image, (self.x, self.y, GC.WINWIDTH, GC.WINHEIGHT))
        if gameStateObj and gameStateObj.current_party is None and show_cursor:
            self.cursor.draw(image)
        surf.blit(image, (0, 0))

    def serialize(self):
        d = {'triggers': self.triggers,
             'locations': {name: location.serialize() for name, location in self.locations.items()},
             'routes': {name: route.serialize() for name, route in self.routes.items()},
             'parties': {party_id: party.serialize() for party_id, party in self.parties.items()}
             }
        return d

    @classmethod
    def deserialize(cls, data, gameStateObj):
        if not data:
            return None
        s = cls()
        s.triggers = data['triggers']
        for level_name, location in s.locations.items():
            location.deserialize(data['locations'].get(level_name))
        for route_name, route in s.routes.items():
            route.deserialize(data['routes'].get(route_name))
        for party_id, party in data['parties'].items():
            s.parties[party_id] = OverworldParty.deserialize(party, s, gameStateObj)
        return s

class OverworldState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        print("Begin Overworld")
        if not self.started:
            self.started = True
            gameStateObj.overworld.last_party = gameStateObj.current_party
            gameStateObj.current_party = None
            self.choice_menu = None
            self.state = 'normal'
            self.show_cursor = False
            self.triggers_done = False

            if not gameStateObj.overworld.triggers:
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

        if gameStateObj.overworld.triggers:
            # Play any triggers
            trigger = gameStateObj.overworld.triggers[0]
            overworld_script_name = 'Data/overworld_script.txt'
            if os.path.exists(overworld_script_name):
                overworld_script = Dialogue.Dialogue_Scene(overworld_script_name, name=trigger)
                gameStateObj.message.append(overworld_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')
            del gameStateObj.overworld.triggers[0]
            self.processed = False  # Force begin() again!
            return 'repeat'
        else:
            self.show_cursor = True
            self.triggers_done = True
            if gameStateObj.overworld.last_party is not None:
                gameStateObj.overworld.autocursor()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        
        if self.state == 'normal':
            if gameStateObj.current_party is not None:
                cur_party = gameStateObj.overworld.parties[gameStateObj.current_party]
                new_location_id = cur_party.location_id

                if event == 'BACK':
                    self.show_cursor = True
                    cur_party.deselect()
                    gameStateObj.overworld.autocursor()
                    gameStateObj.current_party = None
                elif event == 'SELECT':
                    # If unvisited before
                    cur_loc = gameStateObj.overworld.locations[cur_party.location_id]
                    if not cur_loc.visited:
                        self.state = 'are_you_sure'
                        header = "Explore " + cur_loc.name + "?"
                        self.choice_menu = MenuFunctions.HorizOptionsMenu(header, ['Yes', 'No'])
                    else:
                        self.go_to_base(cur_party, gameStateObj, metaDataObj)
                elif event in ('UP', 'LEFT', 'RIGHT', 'DOWN'):
                    new_location_id = gameStateObj.overworld.get_location(cur_party.location_id, event)    
                    if new_location_id is None:
                        GC.SOUNDDICT['Error'].play()
                    elif new_location_id != cur_party.location_id:
                        cur_party.move(new_location_id, gameStateObj)
                        self.state = 'party_moving'
                elif event == 'INFO':
                    self.go_to_base(cur_party, gameStateObj, metaDataObj)
            else:
                gameStateObj.overworld.cursor.handle_movement(gameStateObj)

                if event == 'SELECT':
                    cur_party = gameStateObj.overworld.get_current_hovered_party()
                    if cur_party:
                        gameStateObj.current_party = cur_party.party_id
                        cur_party.select()
                        self.show_cursor = False
                    else:
                        gameStateObj.stateMachine.changeState('overworld_options')

        elif self.state == 'are_you_sure':
            cur_party = gameStateObj.overworld.parties[gameStateObj.current_party]
            if event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                self.choice_menu.moveLeft()
            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                self.choice_menu.moveRight()

            if event == 'SELECT':
                if self.choice_menu.getSelection() == 'Yes':
                    level_id = cur_party.location_id
                    if level_id is not None:
                        gameStateObj.stateMachine.changeState('turn_change')
                        levelfolder = 'Data/Level' + level_id
                        SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                else:
                    self.state = 'normal'
                    self.choice_menu = None
            elif event == 'BACK':
                self.state = 'normal'
                self.choice_menu = None

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.update(gameStateObj)
        if self.state == 'party_moving':
            cur_party = gameStateObj.overworld.parties[gameStateObj.current_party]
            if not cur_party.isMoving():
                self.state = 'normal'

    def go_to_base(self, cur_party, gameStateObj, metaDataObj):
        levelfolder = 'Data/Level' + cur_party.location_id
        overview_filename = levelfolder + '/overview.txt'
        if os.path.exists(overview_filename):
            overview_dict = SaveLoad.read_overview_file(overview_filename)
            metaDataObj['baseFlag'] = overview_dict['base_flag'] if overview_dict['base_flag'] != '0' else False
        else:
            metaDataObj['baseFlag'] = 'MainBase'
        gameStateObj.stateMachine.changeState('base_main')
        gameStateObj.stateMachine.changeState('transition_out')

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.draw(surf, gameStateObj, self.show_cursor)

        cur_party = gameStateObj.overworld.get_current_hovered_party()
        cur_location = gameStateObj.overworld.get_current_hovered_location()
        if self.show_cursor:
            if cur_party is not None:
                cur_party.hover_over()
        elif self.triggers_done:
            # Draw R: Info display
            camp_surf = BaseMenuSurf.CreateBaseMenuSurf((96, 24), 'WhiteMenuBackground75')
            helper = Engine.get_key_name(cf.OPTIONS['key_INFO']).upper()
            GC.FONT['text_yellow'].blit(helper, camp_surf, (4, 3))
            GC.FONT['text_white'].blit(': Make Camp Here', camp_surf, (4 + GC.FONT['text_blue'].size(helper)[0], 3))
            surf.blit(camp_surf, (119, 139))

        if self.show_cursor:
            gameStateObj.overworld.cursor.draw_info(surf, cur_party, cur_location, gameStateObj)

        if self.choice_menu:
            self.choice_menu.draw(surf)

        return surf

class OverworldEffectsState(StateMachine.State):
    name = 'overworld_effects'
    show_map = False

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.update(gameStateObj)
        # Only switch states if no other unit is moving
        if not any(party.isMoving() for party in gameStateObj.overworld.parties.values()) and \
           not any(loc.state != 'normal' for loc in gameStateObj.overworld.locations.values()) and \
           not any(route.state != 'normal' for route in gameStateObj.overworld.routes.values()):
            gameStateObj.stateMachine.back()
            # If this was part of a cutscene and I am the last unit moving, head back to dialogue state
            if gameStateObj.stateMachine.getPreviousState() in ('dialogue', 'transparent_dialogue') or gameStateObj.message: # The back should move us out of 'movement' state
                gameStateObj.message[-1].current_state = "Processing" # Make sure that we can go back to processing
            return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.draw(surf, gameStateObj, False)

        return surf

class OverworldOptionsState(StateMachine.State):
    name = 'overworld_optons'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        options = [cf.WORDS['Options'], cf.WORDS['Save']]
        info_desc = [cf.WORDS['Options_desc'], cf.WORDS['Save_desc']]
        self.menu = MenuFunctions.ChoiceMenu(None, options, 'auto', gameStateObj=gameStateObj, info_desc=info_desc)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveUp(first_push)

        # Back - to overworld state
        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            self.menu = None # Remove menu
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            selection = self.menu.getSelection()
            GC.SOUNDDICT['Select 1'].play()
            if selection == cf.WORDS['Save']:
                gameStateObj.shared_state_data['option_owner'] = selection
                gameStateObj.stateMachine.changeState('optionchild')
            elif selection == cf.WORDS['Options']:
                gameStateObj.stateMachine.changeState('config_menu')
                gameStateObj.stateMachine.changeState('transition_out')

        elif event == 'INFO':
            self.toggle_info()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.update(gameStateObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.draw(surf, gameStateObj, False)
        if self.menu:
            self.menu.draw(surf, gameStateObj)
            self.menu.drawInfo(surf)
        return surf
