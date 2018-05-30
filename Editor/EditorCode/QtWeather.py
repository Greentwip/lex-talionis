import random, sys, math

sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import EditorUtilities

class Weather(object):
    def __init__(self, name, abundance, bounds, size):
        width, height = size
        self.name = name
        self.particle = WEATHER_CATALOG[name]
        self.abundance = int(abundance*(width*height)) # How many should there be at once
        self.particles = []
        self.last_update = 0
        self.remove_me = False

        self.l_x, self.u_x, self.l_y, self.u_y = bounds

    def update(self, current_time, tile_data):
        for particle in self.particles:
            particle.update(current_time, tile_data)

        # remove particles that have left the map
        self.particles = [particle for particle in self.particles if not particle.remove_me]

        # print(self.abundance, len(self.particles))
        # If we're missing some particles and we haven't updated in 250 ms over the num of particles
        if len(self.particles) < self.abundance and current_time - self.last_update > 250/self.abundance:
            self.particles.append(self.particle((random.randint(self.l_x, self.u_x), random.randint(self.l_y, self.u_y))))
            self.last_update = current_time

        if self.abundance <= 0 and not self.particles:
            self.remove_me = True

    def draw(self):
        return [particle.get_image() for particle in self.particles]

class Raindrop(object):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = EditorUtilities.create_image(GC.IMAGESDICT['Rain'].convert_alpha())
        self.speed = 2
        self.remove_me = False

    def update(self, current_time, tile_data):
        self.x += self.speed
        self.y += self.speed*4
        if self.x > tile_data.width*GC.TILEWIDTH or self.y > tile_data.height*GC.TILEHEIGHT:
            self.remove_me = True

    def get_image(self):
        return self.sprite, (self.x, self.y)

class Sand(Raindrop):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = EditorUtilities.create_image(GC.IMAGESDICT['Sand'])
        self.speed = 6
        self.remove_me = False

    def update(self, current_time, tile_data):
        self.x += self.speed*2
        self.y -= self.speed
        if self.x > tile_data.width*GC.TILEWIDTH or self.y < -32:
            self.remove_me = True

class Snow(Raindrop):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        rng = random.randint(0, 2)
        self.sprite = EditorUtilities.create_image(Engine.subsurface(GC.IMAGESDICT['Snow'], (0, rng*8, 8, 8)))
        self.speed = random.choice([1.0, 1.5, 2.0, 2.5, 3.0])
        self.remove_me = False

        self.floor = False

    def update(self, current_time, tile_data):
        speed = int(self.speed)
        if self.speed == 1.5 or self.speed == 2.5:
            if not self.floor:
                speed += 1
            self.floor = not self.floor

        self.x += speed
        self.y += speed
        if self.x > tile_data.width * GC.TILEWIDTH or self.y > tile_data.height * GC.TILEHEIGHT:
            self.remove_me = True

class LightMote(object):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = EditorUtilities.create_image(GC.IMAGESDICT['LightMote'])
        self.transition = True
        self.transparency = 75
        self.change_over_time = random.choice([1, 2, 3])
        self.remove_me = False
        self.last_move_update = 0
        self.x_change = 1
        self.y_change = 1

    def update(self, current_time, tile_data):
        if current_time - self.last_move_update > 100:
            self.x += self.x_change
            self.y += self.y_change
            self.last_move_update = current_time

        if self.transition:
            self.transparency -= self.change_over_time
            if self.transparency <= 5:
                self.transition = False
        else:
            self.transparency += self.change_over_time
            if self.transparency >= 75:
                self.remove_me = True
                self.transparency = 100

    def get_image(self):
        return EditorUtilities.setOpacity(self.sprite, self.transparency/100.), (self.x, self.y)

class DarkMote(LightMote):
    def __init__(self, pos):
        LightMote.__init__(self, pos)
        self.sprite = EditorUtilities.create_image(GC.IMAGESDICT['DarkMote'])
        self.x_change = -1
        self.y_change = -1

WEATHER_CATALOG = {'Rain': Raindrop,
                   'Sand': Sand,
                   'Snow': Snow,
                   'Light': LightMote,
                   'Dark': DarkMote}