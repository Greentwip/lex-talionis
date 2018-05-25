import math

import GlobalConstants as GC
import Engine, Counters, Image_Modification

class ScrollBar(object):
    top = Engine.subsurface(GC.IMAGESDICT['Scroll_Bar'], (0, 0, 7, 1))
    bottom = Engine.subsurface(GC.IMAGESDICT['Scroll_Bar'], (0, 2, 7, 1))
    middle = Engine.subsurface(GC.IMAGESDICT['Scroll_Bar'], (0, 1, 7, 1))
    fill = Engine.subsurface(GC.IMAGESDICT['Scroll_Bar'], (0, 3, 7, 1))
    
    def __init__(self, topright):
        self.x = topright[0] - 7
        self.y = topright[1] + 4
        self.arrow_counter = Counters.ArrowCounter()

    def draw(self, surf, scroll, limit, num_options):
        self.arrow_counter.update()
        height = limit*16 - 16
        start_frac = scroll/float(num_options)
        end_frac = (scroll + limit)/float(num_options)

        # Draw parts
        surf.blit(self.top, (self.x, self.y))
        surf.blit(self.bottom, (self.x, self.y + height + 2))
        for num in range(1, height + 2):
            surf.blit(self.middle, (self.x, self.y + num))

        # Draw bar
        start_position = int(start_frac*height)
        end_position = int(end_frac*height)
        for num in range(start_position, end_position + 1):
            surf.blit(self.fill, (self.x, self.y + num + 1))

        # Draw arrows
        if start_position > 0:
            top_arrow = Engine.subsurface(GC.IMAGESDICT['Scroll_Bar'], (8, 4 + self.arrow_counter.get()*6, 8, 6))
            surf.blit(top_arrow, (self.x - 1, self.y - 7))
        if end_position < height:
            bottom_arrow = Engine.subsurface(GC.IMAGESDICT['Scroll_Bar'], (0, 4 + self.arrow_counter.get()*6, 8, 6))
            surf.blit(bottom_arrow, (self.x - 1, self.y + height + 4))

class ScrollArrow(object):
    images = {'up': GC.IMAGESDICT['ScrollArrows'],
              'down': Engine.flip_horiz(Engine.flip_vert(GC.IMAGESDICT['ScrollArrows'])),
              'left': GC.IMAGESDICT['PageArrows'],
              'right': Engine.flip_horiz(Engine.flip_vert(GC.IMAGESDICT['PageArrows']))}

    def __init__(self, direction, topleft, offset=0):
        self.x, self.y = topleft
        self.direction = direction
        self.arrow_counter = Counters.ArrowCounter(offset)
        self.offset = []

    def pulse(self):
        self.arrow_counter.pulse()
        self.offset = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 2, 2, 2, 1, 1]

    def draw(self, surf):
        self.arrow_counter.update()
        if self.direction == 'up':
            pos = (self.x, self.y - (self.offset.pop() if self.offset else 0))
            surf.blit(Engine.subsurface(self.images['up'], (0, self.arrow_counter.get()*8, 14, 8)), pos)
        elif self.direction == 'down':
            pos = (self.x, self.y + (self.offset.pop() if self.offset else 0))
            surf.blit(Engine.subsurface(self.images['down'], (0, self.arrow_counter.get()*8, 14, 8)), pos)
        elif self.direction == 'left':
            pos = (self.x - (self.offset.pop() if self.offset else 0), self.y) 
            surf.blit(Engine.subsurface(self.images['left'], (self.arrow_counter.get()*8, 0, 8, 14)), pos)
        elif self.direction == 'right':
            pos = (self.x + (self.offset.pop() if self.offset else 0), self.y)
            surf.blit(Engine.subsurface(self.images['right'], (self.arrow_counter.get()*8, 0, 8, 14)), pos)

class DamageNumber(object):
        def __init__(self, num, idx, length, left, color):
            im = GC.IMAGESDICT.get('DamageNumbers' + color, GC.IMAGESDICT['DamageNumbersRed'])
            if color.startswith('Small'):
                self.small = True
            else:
                self.small = False
            self.num = num
            self.idx = idx
            self.length = length
            self.left = left
            self.true_image = Engine.subsurface(im, (num*16, 0, 16, 16))
            self.image = None
            self.done = False
            self.start_time = Engine.get_time()
            self.top_pos = 0
            self.state = -1
            if self.small:
                self.init_time = 50 * self.idx
            else:
                self.init_time = 50 * self.idx + 50

        def update(self):
            new_time = float(Engine.get_time() - self.start_time)
            # Totally transparent start_up
            if self.state == -1:
                if new_time > self.init_time:
                    self.state = 0
            # Initial bouncing and fading in
            if self.state == 0:
                state_time = new_time - self.init_time
                # Position
                self.top_pos = 10 * math.exp(-state_time/250) * math.sin(state_time/25)
                # Transparency
                new_transparency = max(0, (200 - state_time)/2)
                if new_transparency > 0:
                    self.image = Image_Modification.flickerImageTranslucent(self.true_image, new_transparency)
                else:
                    self.image = self.true_image
                if state_time > 400:
                    self.state = 1
                    self.top_pos = 0
            # Pause
            if self.state == 1:
                if new_time - self.init_time > 1000:
                    self.state = 2
            # Fade out and up
            if self.state == 2:
                state_time = new_time - self.init_time - 1000
                # Position
                self.top_pos = state_time/10
                # Transparency
                new_transparency = state_time/2
                self.image = Image_Modification.flickerImageTranslucent(self.true_image, new_transparency)
                if new_time > 1200:
                    self.done = True

        def draw(self, surf, pos):
            if self.image:
                if self.small:
                    true_pos = pos[0] - 4*self.length + 8*self.idx, pos[1] - self.top_pos
                else:
                    true_pos = pos[0] - 7*self.length + 14*self.idx, pos[1] - self.top_pos
                surf.blit(self.image, true_pos)
