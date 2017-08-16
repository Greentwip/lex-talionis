from GlobalConstants import *
import Engine, Counters

class ScrollBar(object):
    top = Engine.subsurface(IMAGESDICT['Scroll_Bar'], (0, 0, 7, 1))
    bottom = Engine.subsurface(IMAGESDICT['Scroll_Bar'], (0, 2, 7, 1))
    middle = Engine.subsurface(IMAGESDICT['Scroll_Bar'], (0, 1, 7, 1))
    fill = Engine.subsurface(IMAGESDICT['Scroll_Bar'], (0, 3, 7, 1))
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
        for num in xrange(1, height + 2):
            surf.blit(self.middle, (self.x, self.y + num))

        # Draw bar
        start_position = int(start_frac*height)
        end_position = int(end_frac*height)
        for num in xrange(start_position, end_position + 1):
            surf.blit(self.fill, (self.x, self.y + num + 1))

        # Draw arrows
        if start_position > 0:
            top_arrow = Engine.subsurface(IMAGESDICT['Scroll_Bar'], (8, 4 + self.arrow_counter.get()*6, 8, 6))
            surf.blit(top_arrow, (self.x - 1, self.y - 7))
        if end_position < height:
            bottom_arrow = Engine.subsurface(IMAGESDICT['Scroll_Bar'], (0, 4 + self.arrow_counter.get()*6, 8 ,6))
            surf.blit(bottom_arrow, (self.x - 1, self.y + height + 4))

class ScrollArrow(object):
    images = {'up': IMAGESDICT['ScrollArrows'],
              'down': Engine.flip_horiz(Engine.flip_vert(IMAGESDICT['ScrollArrows'])),
              'left': IMAGESDICT['PageArrows'],
              'right': Engine.flip_horiz(Engine.flip_vert(IMAGESDICT['PageArrows']))}
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
            surf.blit(Engine.subsurface(self.images['up'], (0,self.arrow_counter.get()*8,14,8)), pos)
        elif self.direction == 'down':
            pos = (self.x, self.y + (self.offset.pop() if self.offset else 0))
            surf.blit(Engine.subsurface(self.images['down'], (0,self.arrow_counter.get()*8,14,8)), pos)
        elif self.direction == 'left':
            pos = (self.x - (self.offset.pop() if self.offset else 0), self.y) 
            surf.blit(Engine.subsurface(self.images['left'], (self.arrow_counter.get()*8,0,8,14)), pos)
        elif self.direction == 'right':
            pos = (self.x + (self.offset.pop() if self.offset else 0), self.y)
            surf.blit(Engine.subsurface(self.images['right'], (self.arrow_counter.get()*8,0,8,14)), pos)
