try:
    import Engine
    from GlobalConstants import IMAGESDICT
except ImportError:
    from . import Engine
    from Code.GlobalConstants import IMAGESDICT

# Helper global object for passive sprite animations
class generic3Counter(object):
    def __init__(self, first_time=440, second_time=50, third_time=None):
        self.count = 0
        self.lastUpdate = Engine.get_time()
        self.lastcount = 1
        self.first_time = first_time
        self.second_time = second_time
        self.third_time = self.first_time if third_time is None else third_time
        
    def update(self, current_time=None):
        if not current_time:
            current_time = Engine.get_time()
        if self.count == 1 and current_time - self.lastUpdate > self.second_time:
            self.increment()
            self.lastUpdate = current_time
            return True
        elif self.count == 0 and current_time - self.lastUpdate > self.first_time:
            self.increment()
            self.lastUpdate = current_time
            return True
        elif self.count == 2 and current_time - self.lastUpdate > self.third_time:
            self.increment()
            self.lastUpdate = current_time
            return True
        return False

    def increment(self):
        if self.count == 0:
            self.count = 1
            self.lastcount = 0
        elif self.count == 2:
            self.count = 1
            self.lastcount = 2
        else:
            if self.lastcount == 0:
                self.count = 2
                self.lastcount = 1
            elif self.lastcount == 2:
                self.count = 0
                self.lastcount = 1

class CursorControl(object):
    def __init__(self):
        self.cursorCounter = 0 # Helper counter for cursor animation
        self.cursorAnim = [0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
        self.cursor = IMAGESDICT['menuHand']

    def update(self):
        self.cursorCounter += 1
        if self.cursorCounter > len(self.cursorAnim) - 1:
            self.cursorCounter = 0

class ArrowCounter(object):
    def __init__(self, offset=0):
        self.arrow_counter = offset # Helper counter for cursor animation
        self.arrow_anim = [0, 1, 2, 3, 4, 5]
        self.increment = []

    def update(self):
        if self.increment:
            self.arrow_counter += self.increment.pop()
        else:
            self.arrow_counter += 0.125
        if self.arrow_counter >= len(self.arrow_anim):
            self.arrow_counter = 0

    def get(self):
        return self.arrow_anim[int(self.arrow_counter)]

    def pulse(self):
        self.increment = [1, 1, 1, 1, 1, 1, 1, 1, .5, .5, .5, .5, .25, .25, .25]