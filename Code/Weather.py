import random, math

from . import GlobalConstants as GC
from . import Engine, Image_Modification

class Weather(object):
    def __init__(self, name, abundance, bounds, size, blend=None):
        width, height = size
        self.name = name
        self.particle = WEATHER_CATALOG[name]
        self.abundance = int(abundance*(width*height)) # How many should there be at once
        self.particles = []
        self.last_update = 0
        self.remove_me = False

        self.l_x, self.u_x, self.l_y, self.u_y = bounds

        self.blend = blend

    def update(self, current_time, gameStateObj):
        for particle in self.particles:
            particle.update(gameStateObj)

        # remove particles that have left the map
        self.particles = [particle for particle in self.particles if not particle.remove_me]

        # print(self.abundance, len(self.particles))
        # If we're missing some particles and we haven't updated in 250 ms over the num of particles
        if len(self.particles) < self.abundance and current_time - self.last_update > 250//self.abundance:
            self.particles.append(self.particle((random.randint(self.l_x, self.u_x), random.randint(self.l_y, self.u_y))))
            self.last_update = current_time

        if self.abundance <= 0 and not self.particles:
            self.remove_me = True

    def draw(self, surf, pos_x=0, pos_y=0):
        if self.blend:
            Engine.blit(surf, self.blend, (pos_x, pos_y), None, Engine.BLEND_RGB_ADD)
        for particle in self.particles:
            particle.draw(surf, pos_x, pos_y)

class Raindrop(object):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = GC.IMAGESDICT['Rain']
        self.speed = 2
        self.remove_me = False

    def update(self, gameStateObj):
        self.x += self.speed
        self.y += self.speed*4
        if hasattr(gameStateObj, 'map') and gameStateObj.map and \
                (self.x > gameStateObj.map.width*GC.TILEWIDTH or
                 self.y > gameStateObj.map.height*GC.TILEHEIGHT):
            self.remove_me = True

    def draw(self, surf, pos_x=0, pos_y=0):
        surf.blit(self.sprite, (self.x + pos_x, self.y + pos_y))

class Sand(Raindrop):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = GC.IMAGESDICT['Sand']
        self.speed = 6
        self.remove_me = False

    def update(self, gameStateObj):
        self.x += self.speed*2
        self.y -= self.speed
        if hasattr(gameStateObj, 'map') and gameStateObj.map and \
                (self.x > gameStateObj.map.width*GC.TILEWIDTH or self.y < -32):
            self.remove_me = True

class Smoke(Raindrop):
    full_sprite = GC.IMAGESDICT['SmokeParticle']
    bottom_sprite = Engine.subsurface(full_sprite, (3, 0, 3, 4))
    top_sprite = Engine.subsurface(full_sprite, (0, 0, 3, 4))

    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.speed = 6
        self.remove_me = False
        self.on_bottom_flag = True
        self.sprite = self.bottom_sprite

    def update(self, gameStateObj):
        self.x += random.randint(self.speed//2, self.speed)
        self.y -= random.randint(self.speed//2, self.speed)
        if hasattr(gameStateObj, 'map') and gameStateObj.map and self.x > gameStateObj.map.width*GC.TILEWIDTH:
            self.remove_me = True
        elif self.x > GC.WINWIDTH:
            self.remove_me = True
        if self.y < -32:
            self.remove_me = True
        if self.on_bottom_flag and self.y < GC.WINHEIGHT//2:
            self.sprite = self.top_sprite
            self.on_bottom_flag = False

class Fire(Raindrop):
    full_sprite = GC.IMAGESDICT['FireParticle']

    def __init__(self, pos):
        Fire.sprites = [Engine.subsurface(Fire.full_sprite, (0, i*2, 3, 2)) for i in range(6)]
        self.x = pos[0]
        self.y = pos[1]
        self.speed = random.randint(1, 4)
        self.remove_me = False
        self.sprite = self.sprites[-1]

    def update(self, gameStateObj):
        self.x -= random.randint(0, self.speed)
        self.y -= random.randint(0, self.speed)
        if self.y > 112:
            self.sprite = Fire.sprites[-1]
        elif self.y > 104:
            self.sprite = Fire.sprites[-2]
        elif self.y > 88:
            self.sprite = Fire.sprites[-3]
        elif self.y > 80:
            self.sprite = Fire.sprites[-4]
        elif self.y > 72:
            self.sprite = Fire.sprites[-5]
        elif self.y > 64:
            self.sprite = Fire.sprites[-6]
        else:
            self.remove_me = True

class Snow(Raindrop):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        rng = random.randint(0, 2)
        self.sprite = Engine.subsurface(GC.IMAGESDICT['Snow'], (0, rng*8, 8, 8))
        self.speed = random.choice([1.0, 1.5, 2.0, 2.5, 3.0])
        self.remove_me = False

        self.floor = False

    def update(self, gameStateObj):
        speed = int(self.speed)
        if self.speed == 1.5 or self.speed == 2.5:
            if not self.floor:
                speed += 1
            self.floor = not self.floor

        self.x += speed
        self.y += speed
        if hasattr(gameStateObj, 'map') and gameStateObj.map and \
                (self.x > gameStateObj.map.width * GC.TILEWIDTH or
                 self.y > gameStateObj.map.height * GC.TILEHEIGHT):
            self.remove_me = True

class WarpFlower(object):
    def __init__(self, pos, speed, angle):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = GC.IMAGESDICT['Warp_Flower']
        self.speed = speed
        self.angle = angle
        self.remove_me = False

    def update(self, gameStateObj):
        self.x += self.speed*math.cos(self.angle)
        self.y += self.speed*math.sin(self.angle)
        if hasattr(gameStateObj, 'map') and gameStateObj.map and \
                (self.x < 0 or self.y < 0 or 
                 self.x > gameStateObj.map.width*GC.TILEWIDTH or
                 self.y > gameStateObj.map.height*GC.TILEHEIGHT):
            self.remove_me = True

    def draw(self, surf, pos_x=0, pos_y=0):
        # Ignore camera position
        surf.blit(self.sprite, (self.x, self.y))

class LightMote(object):
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.sprite = GC.IMAGESDICT['LightMote']
        self.transition = True
        self.transparency = 75
        self.change_over_time = random.choice([1, 2, 3])
        self.remove_me = False
        self.last_move_update = 0
        self.x_change = 1
        self.y_change = 1

    def update(self, gameStateObj):
        if Engine.get_time() - self.last_move_update > 100:
            self.x += self.x_change
            self.y += self.y_change
            self.last_move_update = Engine.get_time()

        if self.transition:
            self.transparency -= self.change_over_time
            if self.transparency <= 5:
                self.transition = False
        else:
            self.transparency += self.change_over_time
            if self.transparency >= 75:
                self.remove_me = True
                self.transparency = 100

    def draw(self, surf, pos_x, pos_y):
        surf.blit(Image_Modification.flickerImageTranslucent(self.sprite, self.transparency), (self.x, self.y))

class DarkMote(LightMote):
    def __init__(self, pos):
        LightMote.__init__(self, pos)
        self.sprite = GC.IMAGESDICT['DarkMote']
        self.x_change = -1
        self.y_change = -1

WEATHER_CATALOG = {'Rain': Raindrop,
                   'Sand': Sand,
                   'Smoke': Smoke,
                   'Fire': Fire,
                   'Snow': Snow,
                   'Light': LightMote,
                   'Dark': DarkMote,
                   'Warp_Flower': WarpFlower}
