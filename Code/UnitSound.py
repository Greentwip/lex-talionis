from . import GlobalConstants as GC

class UnitSound(object):
    sound_catalog = {
        'Flier': {0: 'Flier', 20: 'repeat'},
        'Mounted': {0: 'Mounted1', 3: 'Mounted2', 10: 'Mounted3', 21: 'repeat'},
        'Armor': {0: 'Armor1', 16: 'Armor2', 32: 'repeat'},
        'Infantry': {0: 'Infantry1', 8: 'Infantry2', 16: 'repeat'}}

    def __init__(self, unit):
        self.unit = unit
        self.frame = 0
        self.current_sound = None
        self.playing_sound = None

    def play(self):
        if 'flying' in self.unit.status_bundle:
            self.current_sound = 'Flier'
        elif 'Mounted' in self.unit.tags or self.unit.movement_group in (2, 3):
            self.current_sound = 'Mounted'
        elif 'Armor' in self.unit.tags or self.unit.movement_group == 1:
            self.current_sound = 'Armor'
        else:
            self.current_sound = 'Infantry'

    def update(self):
        if self.current_sound:
            if self.frame in self.sound_catalog[self.current_sound]:
                sound = self.sound_catalog[self.current_sound][self.frame]
                if sound == 'repeat':
                    self.frame = -1
                else:
                    self.playing_sound = 'Map_Step_' + sound
                    GC.SOUNDDICT[self.playing_sound].play()
            self.frame += 1

    def stop(self):
        GC.SOUNDDICT[self.playing_sound].stop()
        self.current_sound, self.playing_sound = None, None
        self.frame = 0
