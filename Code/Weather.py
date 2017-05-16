import random, math
from GlobalConstants import *
import Engine, Image_Modification

class Weather(object):
    def __init__(self, name, abundance, bounds, (width, height)):
        self.name = name
        self.particle = WEATHER_CATALOG[name]
        self.abundance = int(abundance*(width*height)) # How many should there be at once
        self.particles = []
        self.last_update = 0
        self.remove_me = False

        self.l_x, self.u_x, self.l_y, self.u_y = bounds

    def update(self, current_time, gameStateObj):
        for particle in self.particles:
            particle.update(gameStateObj)

        # remove particles that have left the map
        self.particles = [particle for particle in self.particles if not particle.remove_me]

        #print(self.abundance, len(self.particles))
        # If we're missing some particles and we haven't updated in 250 ms over the num of particles
        if len(self.particles) < self.abundance and current_time - self.last_update > 250/self.abundance:
            self.particles.append(self.particle((random.randint(self.l_x, self.u_x), random.randint(self.l_y, self.u_y))))
            self.last_update = current_time

        if self.abundance <= 0 and not self.particles:
            self.remove_me = True

    def draw(self, surf):
        for particle in self.particles:
            particle.draw(surf)

class Raindrop(object):
    def __init__(self, (x, y)):
        self.x = x
        self.y = y
        self.sprite = IMAGESDICT['Rain']
        self.speed = 2
        self.remove_me = False

    def update(self, gameStateObj):
        self.x += self.speed
        self.y += self.speed*4
        if self.x > gameStateObj.map.width*TILEWIDTH or self.y > gameStateObj.map.height*TILEHEIGHT:
            self.remove_me = True

    def draw(self, surf):
        surf.blit(self.sprite, (self.x, self.y))

class Sand(Raindrop):
    def __init__(self, (x,y)):
        self.x = x
        self.y = y
        self.sprite = IMAGESDICT['Sand']
        self.speed = 6
        self.remove_me = False

    def update(self, gameStateObj):
        self.x += self.speed*2
        self.y -= self.speed
        if self.x > gameStateObj.map.width*TILEWIDTH or self.y < -32:
            self.remove_me = True

class Smoke(Raindrop):
    full_sprite = IMAGESDICT['SmokeParticle']
    bottom_sprite = Engine.subsurface(full_sprite, (3, 0, 3, 4))
    top_sprite = Engine.subsurface(full_sprite, (0, 0, 3, 4))

    def __init__(self, (x, y)):
        self.x = x
        self.y = y
        self.speed = 6
        self.remove_me = False
        self.on_bottom_flag = True
        self.sprite = self.bottom_sprite

    def update(self, gameStateObj):
        self.x += random.randint(self.speed/2, self.speed)
        self.y -= random.randint(self.speed/2, self.speed)
        if hasattr(gameStateObj, 'map') and gameStateObj.map and self.x > gameStateObj.map.width*TILEWIDTH:
            self.remove_me = True
        elif self.x > WINWIDTH:
            self.remove_me = True
        if self.y < -32:
            self.remove_me = True
        if self.on_bottom_flag and self.y < WINHEIGHT/2:
            self.sprite = self.top_sprite
            self.on_bottom_flag = False

class Snow(Raindrop):
    def __init__(self, (x, y)):
        self.x = x
        self.y = y
        rng = random.randint(0,2)
        self.sprite = Engine.subsurface(IMAGESDICT['Snow'], (0, rng*8, 8, 8))
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
        if self.x > gameStateObj.map.width * TILEWIDTH or self.y > gameStateObj.map.height * TILEHEIGHT:
            self.remove_me = True

class WarpFlower(object):
    def __init__(self, (x, y), speed, angle):
        self.x = x
        self.y = y
        self.sprite = IMAGESDICT['Warp_Flower']
        self.speed = speed
        self.angle = angle
        self.remove_me = False

    def update(self, gameStateObj):
        self.x += self.speed*math.cos(self.angle)
        self.y += self.speed*math.sin(self.angle)
        if self.x < 0 or self.y < 0 or self.x > gameStateObj.map.width*TILEWIDTH or self.y > gameStateObj.map.height*TILEHEIGHT:
            self.remove_me = True

    def draw(self, surf):
        surf.blit(self.sprite, (self.x, self.y))

class LightMote(object):
    def __init__(self, (x,y)):
        self.x = x
        self.y = y
        self.sprite = IMAGESDICT['LightMote']
        self.transition = True
        self.transparency = 75
        self.change_over_time = random.choice([1,2,3])
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

    def draw(self, surf):
        surf.blit(Image_Modification.flickerImageTranslucent(self.sprite, self.transparency), (self.x, self.y))

class DarkMote(LightMote):
    def __init__(self, (x,y)):
        LightMote.__init__(self, (x,y))
        self.sprite = IMAGESDICT['DarkMote']
        self.x_change = -1
        self.y_change = -1

WEATHER_CATALOG = {'Rain': Raindrop,
                   'Sand': Sand,
                   'Smoke': Smoke,
                   'Snow': Snow,
                   'Light': LightMote,
                   'Dark': DarkMote,
                   'Warp_Flower': WarpFlower}