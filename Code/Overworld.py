import os
try:
    import GlobalConstants as GC
    import configuration as cf
    import StateMachine, SaveLoad, Dialogue, MenuFunctions
    import Utility, Engine, InputManager, GenericMapSprite
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import StateMachine, SaveLoad, Dialogue, MenuFunctions
    from . import Utility, Engine, InputManager, GenericMapSprite

class OverworldCursor(object):
    image = GC.IMAGESDICT['OverworldCursor']
    width = image.get_width()
    height = image.get_height()

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
        surf.blit(self.image, (self.x - self.overworld.x, self.y - self.overworld.y))

class OverworldIcon(object):
    icon_bases = GC.IMAGESDICT['OverworldIcons']
    size = 32

    def __init__(self, data):
        self.level_name = data['level_name']
        self.icon_idx = data['icon_idx']
        self.position = data['position']
        self.connections = data['connections']
        self.image = Engine.subsurface(self.icon_bases, (0, self.size * self.icon_idx, self.size, self.size))
        self.show = True
        self.display_flag = False

    def get_position(self):
        return self.position[0]*8, self.position[1]*8

    def draw(self, surf):
        if self.show:
            surf.blit(self.image, (self.position[0]*8 - self.size/2, self.position[1]*8 - self.size/2))

    def show_icon(self):
        self.show = True

    def hide_icon(self):
        self.show = False

    def serialize(self):
        return (self.show, self.display_flag)

    def deserialize(self, data):
        if not data:
            return
        self.show, self.display_flag = data

class OverworldRoute(object):
    route_sheet = GC.IMAGESDICT['OverworldRoutes']
    top_horiz = Engine.subsurface(route_sheet, (8 * 1, 0, 8, 8))
    bottom_horiz = Engine.subsurface(route_sheet, (8 * 2, 0, 8, 8))
    left_vert = Engine.subsurface(route_sheet, (8 * 3, 0, 8, 8))
    right_vert = Engine.subsurface(route_sheet, (8 * 4, 0, 8, 8))

    def __init__(self, name, pos1, pos2):
        self.name = name
        self.pos1 = pos1
        self.pos2 = pos2

        self.create_image()

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

    def draw(self, surf):
        surf.blit(self.image, (self.position[0]*8, self.position[1]*8))

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
        if all(not sprite.isMoving for sprite in self.sprites):
            self.location = self.next_location
            self.position = self.next_position
            self.next_location = None
            self.next_position = None

    def draw(self, surf):
        for sprite in self.sprites:
            sprite.draw(surf)

class Overworld(object):
    def __init__(self):
        self.x, self.y = 0, 0
        self.main_sprite = GC.IMAGESDICT['OverworldSprite']
        self.width, self.height = self.main_sprite.get_width(), self.main_sprite.get_height()

        self.icons = {icon_data['level_name']: OverworldIcon(icon_data) for icon_data in GC.OVERWORLDDATA}
        self.create_routes()
        print(self.icons)
        print(self.routes)
        self.parties = {}

        self.cursor = OverworldCursor(self)

        self.triggers = []

    def create_routes(self):
        self.routes = {}
        for name, icon in self.icons.items():
            for connection in icon.connections:
                route_name = tuple(sorted((name, connection)))
                if route_name not in self.routes:
                    self.routes[route_name] = OverworldRoute(route_name, icon.position, self.icons[connection].position)

    def move_cursor(self, gameStateObj):
        self.cursor.handle_movement(gameStateObj)

    def move_current_party(self, event, gameStateObj):
        cur_party = self.parties[gameStateObj.current_party]

        if event == 'UP':
            new_location = self.icons[cur_party.location].connections[0]
        elif event == 'LEFT':
            new_location = self.icons[cur_party.location].connections[1]
        elif event == 'RIGHT':
            new_location = self.icons[cur_party.location].connections[2]
        elif event == 'DOWN':
            new_location = self.icons[cur_party.location].connections[3]

        if new_location != cur_party.location:
            cur_party.move(new_location, self.icons[new_location].position)

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

    def show_icon(self, icon_id):
        self.icons[icon_id].show_icon()

    def hide_icon(self, icon_id):
        self.icons[icon_id].hide_icon()

    def set_next_icon(self, icon_id):
        if icon_id:
            self.icons[icon_id].display_flag = True
        else:
            for icon in self.icons.values():
                icon.display_flag = False

    def move_party(self, icon_id, party_id):
        position = self.icons[icon_id].get_position()
        self.parties[party_id].move(icon_id, position)

    def add_party(self, icon_id, party_id, lords):
        position = self.icons[icon_id].get_position()
        self.parties[party_id] = OverworldParty(party_id, icon_id, position, lords)

    def remove_party(self, party_id):
        del self.parties[party_id]

    def get_current_hovered_party(self):
        for name, party in self.parties.items():
            if party.position == self.cursor.get_position():
                return name
        return None

    def draw(self, surf, gameStateObj):
        image = Engine.copy_surface(self.main_sprite)
        for route in self.routes.values():
            route.draw(image)
        for icon in self.icons.values():
            icon.draw(image)
        for party in self.parties.values():
            party.draw(image)
        image = Engine.subsurface(image, (self.x, self.y, GC.WINWIDTH, GC.WINHEIGHT))
        if gameStateObj.current_party is None:
            self.cursor.draw(image)
        surf.blit(image, (0, 0))

    def serialize(self):
        d = {'triggers': self.triggers,
             'icons': {name: icon.serialize() for name, icon in self.icons.items()},
             }
        return d

    @classmethod
    def deserialize(cls, data):
        if not data:
            return None
        s = cls()
        s.triggers = data['triggers']
        for name, icon in s.icons.items():
            icon.deserialize(data['icons'].get(name))
        return s

class OverworldState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.started = True
            gameStateObj.current_party = None

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
        
        if gameStateObj.current_party is not None:
            level_name = gameStateObj.overworld.move_current_party(event, gameStateObj)
            if level_name is not None:
                gameStateObj.stateMachine.changeState('turn_change')
                levelfolder = 'Data/Level' + level_name
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)

            if event == 'BACK':
                gameStateObj.current_party = None

        else:
            gameStateObj.overworld.move_cursor(gameStateObj)

            if event == 'SELECT':
                gameStateObj.current_party = gameStateObj.overworld.get_current_hovered_party()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.update(gameStateObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.overworld.draw(surf, gameStateObj)
        if gameStateObj.current_party is None and gameStateObj.overworld.get_current_hovered_party() is not None:
            party_surf = MenuFunctions.CreateBaseMenuSurf((64, 40))
            party_name = str(gameStateObj.overworld.get_current_hovered_party())
            p_size = GC.FONT['yellow'].size(party_name)[0]
            GC.FONT['yellow'].blit(party_name, party_surf, (32 - p_size/2, 4))
            GC.FONT['blue'].blit('Units', party_surf, (0, 20))
            num_units = len(gameStateObj.get_units_in_party(gameStateObj.current_party))
            GC.FONT['blue'].blit(str(num_units), party_surf, (64 - GC.FONT['blue'].size(str(num_units))[0], 4))

        return surf
