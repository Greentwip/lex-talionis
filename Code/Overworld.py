try:
    import GlobalConstants as GC
    import StateMachine
    import configuration as cf
    import Utility, Engine, InputManager
except ImportError:
    from . import GlobalConstants as GC
    from . import StateMachine
    from . import configuration as cf
    from . import Utility, Engine, InputManager

class OverworldCursor(object):
    image = GC.IMAGESDICT['OverworldCursor']
    width = image.get_width()
    height = image.get_height()

    def __init__(self, overworld):
        self.x, self.y = 0, 0
        self.overworld = overworld
        self.speed = 4

        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed']/4)

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

    def draw(self, surf):
        if self.show:
            surf.blit(self.image, (self.position[0] - self.size/2, self.position[1] - self.size/2))

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
        mini_pos1 = self.pos1[0]/8, self.pos1[1]/8
        mini_pos2 = self.pos2[0]/8, self.pos2[1]/8
        dx = mini_pos2[0] - mini_pos1[0]
        dy = mini_pos2[1] - mini_pos1[1]
        adx, ady = abs(dx), abs(dy)
        print(self.pos1, self.pos2, mini_pos1, mini_pos2, dx, dy)
        x = self.pos1[0] if dx > 0 else self.pos2[0]
        y = self.pos1[1] if dy > 0 else self.pos2[1]

        if adx == 0:
            self.image = Engine.create_surface((16, ady * 8), transparent=True)
            for i in range(ady):
                self.image.blit(self.left_vert, (0, i * 8))
                self.image.blit(self.right_vert, (8, i * 8))
            self.position = (x - 8, y)
        elif ady == 0:
            self.image = Engine.create_surface((adx * 8, 16), transparent=True)
            for i in range(adx):
                self.image.blit(self.top_horiz, (i * 8, 0))
                self.image.blit(self.bottom_horiz, (i * 8, 8))
            self.position = (x, y - 8)
        else:
            # TBD
            self.image = Engine.create_surface((16, 16), transparent=True)
            self.position = (0, 0)

    def draw(self, surf):
        surf.blit(self.image, self.position)

class Overworld(object):
    def __init__(self):
        self.x, self.y = 0, 0
        self.main_sprite = GC.IMAGESDICT['OverworldSprite']
        self.width, self.height = self.main_sprite.get_width(), self.main_sprite.get_height()

        self.icons = {icon_data['level_name']: OverworldIcon(icon_data) for icon_data in GC.OVERWORLDDATA}
        self.create_routes()
        print(self.icons)
        print(self.routes)

        self.cursor = OverworldCursor(self)

    def create_routes(self):
        self.routes = {}
        for name, icon in self.icons.items():
            for connection in icon.connections:
                route_name = tuple(sorted((name, connection)))
                if route_name not in self.routes:
                    self.routes[route_name] = OverworldRoute(route_name, icon.position, self.icons[connection].position)

    def move_cursor(self, gameStateObj):
        self.cursor.handle_movement(gameStateObj)

    def change_x(self, dx):
        self.x = Utility.clamp(self.x + dx, 0, self.width - GC.WINWIDTH)

    def change_y(self, dy):
        self.y = Utility.clamp(self.y + dy, 0, self.height - GC.WINHEIGHT)

    def update(self):
        pass

    def draw(self, surf):
        image = Engine.copy_surface(self.main_sprite)
        for route in self.routes.values():
            route.draw(image)
        for icon in self.icons.values():
            icon.draw(image)
        image = Engine.subsurface(image, (self.x, self.y, GC.WINWIDTH, GC.WINHEIGHT))
        self.cursor.draw(image)
        surf.blit(image, (0, 0))

class OverworldState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.started = True
            self.overworld = Overworld()

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.overworld.move_cursor(gameStateObj)

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.overworld.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.overworld.draw(surf)
        return surf
