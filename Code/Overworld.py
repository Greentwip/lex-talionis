import os
try:
    import GlobalConstants as GC
    import configuration as cf
    import StateMachine, SaveLoad, Dialogue, MenuFunctions, CustomObjects
    import Utility, Engine, InputManager, GenericMapSprite, Image_Modification
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import StateMachine, SaveLoad, Dialogue, MenuFunctions, CustomObjects
    from . import Utility, Engine, InputManager, GenericMapSprite, Image_Modification

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

    def get_position(self):
        return self.x, self.y

    def handle_movement(self, gameStateObj):
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        # Normal movement
        if 'LEFT' in directions and self.x >= self.speed:
            self.x -= self.speed
            if self.x <= self.overworld.x + 48: # Cursor controls camera movement
                # Set x is move the camera. Move it to its x_pos - 1, cause we're moving left
                self.overworld.change_x(-self.speed)
        elif 'RIGHT' in directions and self.x < (self.overworld.width - self.width):
            self.x += self.speed
            if self.x >= (self.overworld.x + GC.WINWIDTH - 48):
                self.overworld.change_x(self.speed)
        if 'UP' in directions and self.y >= self.speed:
            self.y -= self.speed
            if self.y <= self.overworld.y + 48:
                self.overworld.change_y(-self.speed)
        elif 'DOWN' in directions and self.y < (self.overworld.height - self.height):
            self.y += self.speed
            if self.y >= (self.overworld.y + GC.WINHEIGHT - 48):
                self.overworld.change_y(self.speed)

    def draw(self, surf):
        self.counter += 1
        if self.counter >= 4:
            self.icon_state_counter += 1
            self.counter = 0

        image = Engine.subsurface(self.image, (0, self.icon_state_counter%len(self.icon_states), self.width, self.height))
        surf.blit(image, (self.x - self.overworld.x, self.y - self.overworld.y))

class OverworldLocation(object):
    icons = GC.IMAGESDICT['OverworldIcons']
    next_icon = GC.IMAGESDICT['OverworldNextIcon']
    icon_size = 32
    show_anim = GC.IMAGESDICT['OverworldShowAnim']

    def __init__(self, data):
        self.level_id = data['level_id']
        self.location_name = data['location_name']
        self.icon_idx = data['icon_idx']
        self.position = data['position']
        self.connections = data['connections']
        self.image = Engine.subsurface(self.icons, (0, self.icon_size * self.icon_idx, self.icon_size, self.icon_size))
        self.show = True
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
        self.anim = CustomObjects.Animation(self.show_anim, self.get_draw_pos(), (4, 4), animation_speed=66, ignore_map=True)
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

    def __init__(self, connection, pos1, pos2, route):
        self.connection = connection
        self.pos1 = pos1
        self.pos2 = pos2
        self.route = route

        self.create_image2()

    def create_image(self):
        dx = self.pos2[0] - self.pos1[0]
        dy = self.pos2[1] - self.pos1[1]
        adx, ady = abs(dx), abs(dy)
        print(self.pos1, self.pos2, dx, dy)
        x = self.pos1[0] if dx > 0 else self.pos2[0]
        y = self.pos1[1] if dy > 0 else self.pos2[1]

        if adx == 0:
            self.image = Engine.create_surface((16, ady * 8), transparent=True)
            for i in range(ady):
                self.image.blit(self.left_vert, (0, i * 8))
                self.image.blit(self.right_vert, (8, i * 8))
            self.position = (x - 1, y)
        elif ady == 0:
            self.image = Engine.create_surface((adx * 8, 16), transparent=True)
            for i in range(adx):
                self.image.blit(self.top_horiz, (i * 8, 0))
                self.image.blit(self.bottom_horiz, (i * 8, 8))
            self.position = (x, y - 1)
        else:
            # TBD
            self.image = Engine.create_surface((16, 16), transparent=True)
            self.position = (0, 0)

    def create_image2(self):
        self.image = Engine.create_surface((len(self.route)*8, len(self.route)*8), transparent=True)
        if self.pos1[0] < self.pos2[0]:
            if self.pos1[1] < self.pos2[1]:
                cur_x, cur_y = 0, 0
                self.topleft = self.pos1
            else:
                cur_x, cur_y = 0, len(self.route)
                self.topleft = (self.pos1[0], self.pos2[1])
        else:
            if self.pos1[1] < self.pos2[1]:
                cur_x, cur_y = len(self.route), 0
                self.topleft = (self.pos2[0], self.pos1[1])
            else:
                cur_x, cur_y = len(self.route), len(self.route)
                self.topleft = self.pos2
        for route in self.route:
            if route == 2:
                self.image.blit(self.left_vert, (cur_x*8 - 8, cur_y*8))
                self.image.blit(self.right_vert, (cur_x*8, cur_y*8))
                cur_y += 1
            elif route == 4:
                self.image.blit(self.top_horiz, (cur_x*8 - 8, cur_y*8 - 8))
                self.image.blit(self.bottom_horiz, (cur_x*8 - 8, cur_y*8))
                cur_x -= 1
            elif route == 6:
                self.image.blit(self.top_horiz, (cur_x*8, cur_y*8 - 8))
                self.image.blit(self.bottom_horiz, (cur_x*8, cur_y*8))
                cur_x += 1
            elif route == 8:
                self.image.blit(self.left_vert, (cur_x*8 - 8, cur_y*8 - 8))
                self.image.blit(self.right_vert, (cur_x*8, cur_y*8 - 8))
                cur_y -= 1

    def draw(self, surf):
        surf.blit(self.image, self.topleft)

class OverworldParty(object):
    def __init__(self, name, location, position, lords):
        self.name = name
        self.position = position
        self.location = location
        self.lords = lords
        self.next_position = None
        self.next_location = None
        self.sprites = []
        for lord in self.lords:
            if isinstance(lord, tuple):
                self.sprites.append(GenericMapSprite.GenericMapSprite(lord[0], lord[1], 'player', self.position))
            else:
                self.sprites.append(GenericMapSprite.GenericMapSprite(lord.klass, lord.gender, 'player', self.position))

    def move(self, next_location, next_position):
        self.location = None
        self.next_location = next_location
        self.next_position = next_position
        for sprite in self.sprites:
            sprite.set_target(self.next_position)

    def update(self):
        for sprite in self.sprites:
            sprite.update()
        # Check if done moving
        if not self.isMoving():
            self.location = self.next_location
            self.position = self.next_position
            self.next_location = None
            self.next_position = None

    def isMoving(self):
        return any(sprite.isMoving for sprite in self.sprites)

    def draw(self, surf):
        for sprite in self.sprites:
            sprite.draw(surf)

class Overworld(object):
    def __init__(self):
        self.x, self.y = 0, 0
        self.main_sprite = GC.IMAGESDICT['OverworldSprite']
        self.width, self.height = self.main_sprite.get_width(), self.main_sprite.get_height()

        self.locations = {location_data['level_id']: OverworldLocation(location_data) for location_data in GC.OVERWORLDDATA['Locations']}
        self.create_routes()
        print(self.locations)
        print(self.routes)
        self.parties = {}

        self.cursor = OverworldCursor(self)

        self.triggers = []

    def create_routes(self):
        self.routes = {}
        for route in GC.OVERWORLDDATA['Routes']:
            connection = route['connection']
            loc1, loc2 = self.locations[connection[0]], self.locations[connection[1]]
            self.routes[connection] = OverworldRoute(connection, loc1.position, loc2.position, route['route'])

    def set_cursor(self, pos):
        self.cursor.x, self.cursor.y = pos
        self.x = Utility.clamp(self.cursor.x, max(0, self.cursor.x - GC.WINWIDTH + 48), min(self.width - GC.WINWIDTH, self.cursor.x - 48))
        self.y = Utility.clamp(self.cursor.y, max(0, self.cursor.y - GC.WINHEIGHT + 48), min(self.height - GC.WINHEIGHT, self.cursor.y - 48))

    def change_x(self, dx):
        self.x = Utility.clamp(self.x + dx, 0, self.width - GC.WINWIDTH)

    def change_y(self, dy):
        self.y = Utility.clamp(self.y + dy, 0, self.height - GC.WINHEIGHT)

    def update(self, gameStateObj):
        if gameStateObj.current_party is not None:
            cur_party = self.parties[gameStateObj.current_party]
            self.x = Utility.clamp(cur_party.position[0] - GC.WINWIDTH/2, 0, self.width - GC.WINWIDTH)
            self.y = Utility.clamp(cur_party.position[1] - GC.WINHEIGHT/2, 0, self.height - GC.WINHEIGHT)

    def show_location(self, level_id):
        self.locations[level_id].fade_in()

    def hide_location(self, level_id):
        OverworldLocation[level_id].fade_out()

    def quick_show_location(self, level_id):
        self.locations[level_id].show = True

    def set_next_location(self, level_id):
        for location in self.locations.values():
                location.display_flag = False
        if level_id:
            self.locations[level_id].display_flag = True

    def move_party(self, level_id, party_id):
        position = self.locations[level_id].get_position()
        self.parties[party_id].move(level_id, position)

    def add_party(self, level_id, party_id, lords):
        position = self.locations[level_id].get_position()
        self.parties[party_id] = OverworldParty(party_id, level_id, position, lords)

    def remove_party(self, party_id):
        del self.parties[party_id]

    def get_current_hovered_party(self):
        for name, party in self.parties.items():
            if party.position == self.cursor.get_position():
                return name
        return None

    def draw(self, surf, gameStateObj, show_cursor=True):
        image = Engine.copy_surface(self.main_sprite)
        for route in self.routes.values():
            route.draw(image)
        for location in self.locations.values():
            location.draw(image)
        for party in self.parties.values():
            party.draw(image)
        image = Engine.subsurface(image, (self.x, self.y, GC.WINWIDTH, GC.WINHEIGHT))
        if gameStateObj.current_party is None and show_cursor:
            self.cursor.draw(image)
        surf.blit(image, (0, 0))

    def serialize(self):
        d = {'triggers': self.triggers,
             'locations': {name: location.serialize() for name, location in self.locations.items()},
             }
        return d

    @classmethod
    def deserialize(cls, data):
        if not data:
            return None
        s = cls()
        s.triggers = data['triggers']
        for level_name, location in s.locations.items():
            location.deserialize(data['locations'].get(level_name))
        return s

class OverworldState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.started = True
            gameStateObj.current_party = None
            self.choice_menu = None
            self.state = 'normal'
            self.show_cursor = False

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

        if self.triggers:
            # Play any triggers
            trigger = self.triggers[0]
            overworld_script_name = 'Data/overworld_script.txt'
            if os.path.exists(overworld_script_name):
                overworld_script = Dialogue.Dialogue_Scene(overworld_script_name, name=trigger)
                gameStateObj.message.append(overworld_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')
            del self.triggers[0]
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        
        if self.state == 'normal':
            if gameStateObj.current_party is not None:
                cur_party = gameStateObj.overworld.parties[gameStateObj.current_party]
                new_location = cur_party.location

                if event == 'BACK':
                    gameStateObj.current_party = None
                elif event == 'SELECT':
                    if not gameStateObj.overworld.locations[cur_party.location].visited:
                        self.state = 'are_you_sure'
                        self.choice_menu = MenuFunctions.ChoiceMenu(self, ['Yes', 'No'], (GC.TILEWIDTH//2, GC.WINHEIGHT - GC.TILEHEIGHT * 1.5), horizontal=True)
                    else:
                        gameStateObj.stateMachine.changeState('base_main')
                        gameStateObj.stateMachine.changeState('transition_out')
                elif event == 'UP':
                    new_location = gameStateObj.overworld.locations[cur_party.location].connections[0]
                elif event == 'LEFT':
                    new_location = gameStateObj.overworld.locations[cur_party.location].connections[1]
                elif event == 'RIGHT':
                    new_location = gameStateObj.overworld.locations[cur_party.location].connections[2]
                elif event == 'DOWN':
                    new_location = gameStateObj.overworld.locations[cur_party.location].connections[3]

                if new_location != cur_party.location:
                    cur_party.move(new_location, gameStateObj.overworld.locations[new_location].position)
                    self.state = 'party_moving'

            else:
                gameStateObj.overworld.cursor.handle_movement(gameStateObj)

                if event == 'SELECT':
                    gameStateObj.current_party = gameStateObj.overworld.get_current_hovered_party()
                    if gameStateObj.current_party is None:
                        # TODO Open up several menus (Options, Save)
                        pass
                elif event == 'INFO':
                    # TODO open up Manage Items menu / Or base menu
                    # Add R: Make Camp Here (maybe child menu check before?)
                    pass

        elif self.state == 'are_you_sure':
            cur_party = gameStateObj.overworld.parties[gameStateObj.current_party]
            if event == 'SELECT':
                if self.choice_menu.getSelection() == 'Yes':
                    level_id = cur_party.location
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
        if not self.triggers and not self.show_cursor:
            self.show_cursor = True  # Fix this
        if self.state == 'party_moving':
            cur_party = gameStateObj.overworld.parties[gameStateObj.current_party]
            if not cur_party.isMoving():
                self.state = 'normal'

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.draw(surf, gameStateObj)

        cur_party = gameStateObj.overworld.get_current_hovered_party()
        if cur_party is not None:
            overworld_info = GC.IMAGESDICT['OverworldInfo']
            location_name = cur_party.location.name
            l_size = GC.FONT['white'].size(location_name)[0]
            GC.FONT['white'].blit(location_name, overworld_info, (52 - l_size/2, 4))
            party_name = cur_party.name
            p_size = GC.FONT['info_grey'].size(party_name)[0]
            GC.FONT['info_grey'].blit(party_name, overworld_info, (52 - p_size/2, 4))
            GC.FONT['white'].blit('Units', overworld_info, (4, 20))
            num_units = len(gameStateObj.get_units_in_party(gameStateObj.current_party))
            GC.FONT['white'].blit(str(num_units), overworld_info, (92 - GC.FONT['white'].size(str(num_units))[0], 4))
            surf.blit(overworld_info, (0, 0))
            # TODO: Add lord unit minimug

        return surf
