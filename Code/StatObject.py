import GlobalConstants as GC
# === Helper component class for unit stats ===================================
class Stat(object):
    def __init__(self, idx, stat, bonus=0):
        self.idx = idx
        self.base_stat = int(stat)
        self.bonuses = bonus

    def __float__(self):
        return float(self.base_stat) + self.bonuses

    def __int__(self):
        return self.base_stat + self.bonuses

    def __str__(self):
        return str(self.base_stat + self.bonuses)

    def __repr__(self):
        return str(self.base_stat + self.bonuses)

    def __sub__(self, other):
        return self.base_stat + self.bonuses - other

    def __add__(self, other):
        return self.base_stat + self.bonuses + other

    def __rsub__(self, other):
        return other - self.base_stat - self.bonuses

    def __radd__(self, other):
        return other + self.base_stat + self.bonuses

    def __mul__(self, other):
        return (self.base_stat + self.bonuses) * other

    def __rmul__(self, other):
        return other * (self.base_stat + self.bonuses)

    def __div__(self, other):
        return (self.base_stat + self.bonuses) / other

    def __floordiv__(self, other):
        return (self.base_stat + self.bonuses) // other

    def __rdiv__(self, other):
        return other / (self.base_stat + self.bonuses)

    def __rfloordiv__(self, other):
        return other // (self.base_stat + self.bonuses)

    def __neg__(self):
        return -(self.base_stat + self.bonuses)

    def __cmp__(self, other):
        total = self.base_stat + self.bonuses
        if total > other:
            return 1
        elif total == other:
            return 0
        elif total < other:
            return -1

    def serialize(self):
        return (self.base_stat, self.bonuses)

    def draw(self, surf, unit, topright, metaDataObj, compact=False):
        if compact:
            if self.base_stat >= metaDataObj['class_dict'][unit.klass]['max'][self.idx]:
                font = GC.FONT['text_yellow']
            elif self.bonuses > 0: 
                font = GC.FONT['text_green']
            elif self.bonuses < 0:
                font = GC.FONT['text_red']
            else:
                font = GC.FONT['text_blue']
            value = self.base_stat + self.bonuses
            font.blit(str(value), surf, (topright[0] - font.size(str(value))[0], topright[1]))
        else:
            value = self.base_stat
            if value >= metaDataObj['class_dict'][unit.klass]['max'][self.idx]:
                GC.FONT['text_yellow'].blit(str(value), surf, (topright[0] - GC.FONT['text_green'].size(str(value))[0], topright[1]))
            else:
                GC.FONT['text_blue'].blit(str(value), surf, (topright[0] - GC.FONT['text_blue'].size(str(value))[0], topright[1]))
            output = ""
            if self.bonuses > 0:
                output = "+" + str(self.bonuses)
                GC.FONT['small_green'].blit(output, surf, (topright[0], topright[1]))
            elif self.bonuses < 0:
                output = str(self.bonuses)
                GC.FONT['small_red'].blit(output, surf, (topright[0], topright[1]))
