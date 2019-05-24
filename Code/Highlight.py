try:
    import GlobalConstants as GC
    import Engine, Aura
except ImportError:
    from . import GlobalConstants as GC
    from . import Engine, Aura

import logging
logger = logging.getLogger(__name__)

# === GENERIC HIGHLIGHT OBJECT ===================================
class Highlight(object):
    def __init__(self, sprite):
        self.sprite = sprite
        self.image = Engine.subsurface(self.sprite, (0, 0, GC.TILEWIDTH, GC.TILEHEIGHT)) # First image

    def draw(self, surf, position, updateIndex, transition):
        updateIndex = int(updateIndex)  # Confirm int
        rect = (updateIndex*GC.TILEWIDTH + transition, transition, GC.TILEWIDTH - transition, GC.TILEHEIGHT - transition)
        self.image = Engine.subsurface(self.sprite, rect)
        x, y = position
        topleft = x * GC.TILEWIDTH, y * GC.TILEHEIGHT
        surf.blit(self.image, topleft)

# === HIGHLIGHT MANAGER ===========================================
class HighlightController(object):
    def __init__(self):
        self.types = {'spell': [Highlight(GC.IMAGESDICT['GreenHighlight']), 7],
                      'spell2': [Highlight(GC.IMAGESDICT['GreenHighlight']), 7],
                      'attack': [Highlight(GC.IMAGESDICT['RedHighlight']), 7],
                      'splash': [Highlight(GC.IMAGESDICT['LightRedHighlight']), 7],
                      'possible_move': [Highlight(GC.IMAGESDICT['LightBlueHighlight']), 7],
                      'move': [Highlight(GC.IMAGESDICT['BlueHighlight']), 7],
                      'aura': [Highlight(GC.IMAGESDICT['LightPurpleHighlight']), 7],
                      'spell_splash': [Highlight(GC.IMAGESDICT['LightGreenHighlight']), 7]}
        self.highlights = {t: set() for t in self.types}

        self.lasthighlightUpdate = 0
        self.updateIndex = 0

        self.current_hover = None

    def add_highlight(self, position, name, allow_overlap=False):
        if not allow_overlap:
            for t in self.types:
                self.highlights[t].discard(position)
        self.highlights[name].add(position)
        self.types[name][1] = 7 # Reset transitions

    def remove_highlights(self, name=None):
        if name in self.types:
            self.highlights[name] = set()
            self.types[name][1] = 7 # Reset transitions
        else:
            self.highlights = {t: set() for t in self.types}
            # Reset transitions
            for hl_name in self.types:
                self.types[hl_name][1] = 7
        self.current_hover = None

    def remove_aura_highlights(self):
        self.highlights['aura'] = set()

    def update(self):
        self.updateIndex += .25
        if self.updateIndex >= 16:
            self.updateIndex = 0

    def draw(self, surf):
        for name in self.highlights:
            transition = self.types[name][1]
            if transition > 0:
                transition -= 1
            self.types[name][1] = transition
            for pos in self.highlights[name]:
                self.types[name][0].draw(surf, pos, self.updateIndex, transition)

    def check_arrow(self, pos):
        if pos in self.highlights['move']:
            return True
        return False

    def handle_hover(self, gameStateObj):
        cur_hover = gameStateObj.cursor.getHoveredUnit(gameStateObj)
        if self.current_hover and (not cur_hover or cur_hover != self.current_hover):
            self.remove_highlights()
        if cur_hover and cur_hover != self.current_hover:
            ValidMoves = cur_hover.getValidMoves(gameStateObj)
            if cur_hover.getMainSpell():
                cur_hover.displayExcessSpellAttacks(gameStateObj, ValidMoves, light=True)
            if cur_hover.getMainWeapon():
                cur_hover.displayExcessAttacks(gameStateObj, ValidMoves, light=True)
            cur_hover.displayMoves(gameStateObj, ValidMoves, light=True)
            Aura.add_aura_highlights(cur_hover, gameStateObj)
        self.current_hover = cur_hover
