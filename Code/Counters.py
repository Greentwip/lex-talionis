#! usr/bin/env python2.7

import Engine
from GlobalConstants import IMAGESDICT

# Helper global object for passive sprite animations
class generic3Counter(object):
    def __init__(self, first_time = 440, second_time = 50, third_time = None):
        self.count = 0
        self.lastUpdate = Engine.get_time()
        self.lastcount = 1
        self.first_time = first_time
        self.second_time = second_time
        self.third_time = self.first_time if third_time is None else third_time
        
    def update(self):
        current_time = Engine.get_time()
        if self.count == 1 and current_time - self.lastUpdate > self.second_time:
            self.increment()
            self.lastUpdate = current_time
        elif self.count == 0 and current_time - self.lastUpdate > self.first_time:
            self.increment()
            self.lastUpdate = current_time
        elif self.count == 2 and current_time - self.lastUpdate > self.third_time:
            self.increment()
            self.lastUpdate = current_time

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
        self.cursorAnim = [0, 0, 0, 1, 2, 3, 4, 4, 5, 5, 5, 4, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()
        self.cursor = IMAGESDICT['menuHand']

    def update(self):
        currentTime = Engine.get_time()
        if currentTime - self.lastUpdate > 30:
            self.lastUpdate = currentTime
            self.cursorCounter += 1
            if self.cursorCounter > len(self.cursorAnim) - 1:
                self.cursorCounter = 0