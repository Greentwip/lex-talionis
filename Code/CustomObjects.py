import os, pickle, re

import GlobalConstants as GC
import configuration as cf

# Custom Imports
import MenuFunctions
import Utility, Image_Modification, Engine, InputManager

import logging
logger = logging.getLogger(__name__)

# === Simple Finite State Machine Object ===============================
class StateMachine(object):
    def __init__(self, startingstate):
        self.state = []
        self.state.append(startingstate)
        self.state_log = []

    def changeState(self, newstate):
        self.state.append(newstate)

    def back(self):
        self.state.pop()

    def getState(self):
        return self.state[-1]

    def clear(self):
        self.state = []

    # Keeps track of the state at every tick
    def update(self):
        self.state_log.append(self.getState())
    
# === CURSOR OBJECT =============================================
class Cursor(object):
    def __init__(self, sprite, position, fake=False):
        self.spriteName = sprite

        self.fake = fake

        self.loadSprites()
       
        self.position = position
        self.currentSelectedUnit = None
        self.secondSelectedUnit = None
        self.currentHoveredUnit = None
        self.currentHoveredTile = None
        self.camera_follow = None

        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed'])

        self.movePath = []

        self.drawState = 0 # If cursor will be drawn

        self.spriteOffset = [0, 0]
        
    def draw(self, surf):
        if self.drawState or self.fake: # Only draws if cursor is on
            x, y = self.position
            # The space Rect is constructed like so so as to center the cursor sprite
            topleft = x * GC.TILEWIDTH - max(0, (self.image.get_width() - 16)/2), y * GC.TILEHEIGHT - max(0, (self.image.get_height() - 16)/2)
            topleft = topleft[0] - self.spriteOffset[0], topleft[1] - self.spriteOffset[1]
            surf.blit(self.image, topleft)
            # Reset sprite offset afterwards
            if self.spriteOffset[0] > 0:
                self.spriteOffset[0] -= 4
            elif self.spriteOffset[0] < 0:
                self.spriteOffset[0] += 4
            if self.spriteOffset[1] > 0:
                self.spriteOffset[1] -= 4
            elif self.spriteOffset[1] < 0:
                self.spriteOffset[1] += 4

    def getHoveredUnit(self, gameStateObj):
        for unit in gameStateObj.allunits:
            if unit.position == self.position:
                return unit
        return None

    def init_displays(self):
        self.unit_info_disp = None
        self.tile_info_disp = None
        self.obj_info_disp = None

        self.unit_info_offset = 0
        self.tile_info_offset = 0
        self.obj_info_offset = 0

        self.remove_unit_info = True
        self.tile_left = False
        self.obj_top = False

    def removeSprites(self):
        self.sprite = None
        self.image = None
        self.passivesprite, self.activesprite, self.redsprite = None, None, None

        # Current displays
        self.init_displays()
        
    def loadSprites(self):
        # Load sprite
        self.sprite = GC.IMAGESDICT[self.spriteName]
        self.passivesprite, self.activesprite, self.redsprite, self.formationsprite = self.formatSprite(self.sprite)
        self.image = Engine.subsurface(self.passivesprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2)) # 32*32

        # Current displays
        self.init_displays()

    def remove_unit_display(self):
        self.remove_unit_info = True
    
    def move(self, move, gameStateObj):
        dx, dy = move
        gameStateObj.allarrows = [] # Clear all arrows
        GC.SOUNDDICT['Select 5'].stop() # Play cursor sound on move
        GC.SOUNDDICT['Select 5'].play()
        x, y = self.position
        self.position = x + dx, y + dy
        self.place_arrows(gameStateObj)
        # Remove unit display
        self.remove_unit_display()
        # Sprite Offset -- but only if we're not traveling too fast
        if cf.OPTIONS['Cursor Speed'] >= 40:
            self.spriteOffset[0] += 12*dx
            self.spriteOffset[1] += 12*dy

    def place_arrows(self, gameStateObj):
        if gameStateObj.stateMachine.getState() == 'move' and gameStateObj.highlight_manager.check_arrow(self.position):
            self.movePath = self.currentSelectedUnit.getPath(gameStateObj, self.position)
            self.constructArrows(self.movePath[::-1], gameStateObj)

    # The algorithm below is all hard-coded in, which sucks, should change it later, but it WORKS, so thats good
    # ALSO IS EXTREMELY SHITTY ALGORITHM I DON'T UNDERSTAND. was found using trial and error, for the most part
    def constructArrows(self, movePath, gameStateObj):
        arrow = None
        if len(movePath) <= 1: # ie, we haven't really moved yet
            return
        for index in range(len(movePath)):
            if index == 0:
                directionTuple = (movePath[index + 1][0] - movePath[index][0], movePath[index + 1][1] - movePath[index][1])
                if directionTuple == (1, 0): # right
                    arrow = ArrowObject((0, 0), movePath[index])
                elif directionTuple == (-1, 0): # left
                    arrow = ArrowObject((1, 1), movePath[index])
                elif directionTuple == (0, 1): # up
                    arrow = ArrowObject((0, 1), movePath[index])
                elif directionTuple == (0, -1): # down
                    arrow = ArrowObject((1, 0), movePath[index])
            elif index == len(movePath) - 1:
                directionTuple = (movePath[index][0] - movePath[index - 1][0], movePath[index][1] - movePath[index - 1][1])
                if directionTuple == (1, 0):
                    arrow = ArrowObject((0, 6), movePath[index])
                elif directionTuple == (-1, 0):
                    arrow = ArrowObject((1, 7), movePath[index])
                elif directionTuple == (0, -1):
                    arrow = ArrowObject((1, 6), movePath[index])
                elif directionTuple == (0, 1):
                    arrow = ArrowObject((0, 7), movePath[index])
            else: # Neither beginning nor end of arrow
                directionTuple = (movePath[index + 1][0] - movePath[index - 1][0], movePath[index + 1][1] - movePath[index - 1][1])
                modifierTuple = (movePath[index][0] - movePath[index - 1][0], movePath[index][1] - movePath[index - 1][1])
                if directionTuple == (2, 0) or directionTuple == (-2, 0): # right or left
                    arrow = ArrowObject((0, 3), movePath[index])
                elif directionTuple == (0, 2) or directionTuple == (0, -2): # up or down
                    arrow = ArrowObject((0, 2), movePath[index])
                elif directionTuple == (1, -1) or directionTuple == (-1, 1):
                    if modifierTuple == (0, -1) or modifierTuple == (-1, 0):
                        # print "topleft"
                        arrow = ArrowObject((0, 4), movePath[index])
                    else:
                        # print "bottomright"
                        arrow = ArrowObject((1, 5), movePath[index])
                elif directionTuple == (1, 1) or directionTuple == (-1, -1):
                    if modifierTuple == (0, -1) or modifierTuple == (1, 0):
                        # print "topright"
                        arrow = ArrowObject((0, 5), movePath[index])
                    else: # (0, 1) is one of the modifier tuples that does here.
                        # print "bottomleft"
                        arrow = ArrowObject((1, 4), movePath[index])
            gameStateObj.allarrows.append(arrow)
            
    def handleMovement(self, gameStateObj):
        # Handle Cursor movement   -   Move the cursor around
        # Refuses to move Cursor if not enough time has passed since the cursor has last moved. This is
        # a hack to slow down cursor movement rate.
        directions = self.fluid_helper.get_directions()
        if 'LEFT' in directions and self.position[0] > 0:
            self.move((-1, 0), gameStateObj)
            if self.position[0] <= gameStateObj.cameraOffset.get_x() + 2: # Cursor controls camera movement
                # Set x is move the camera. Move it to its x_pos - 1, cause we're moving left
                gameStateObj.cameraOffset.set_x(gameStateObj.cameraOffset.x - 1)
        elif 'RIGHT' in directions and self.position[0] < (gameStateObj.map.width - 1):
            self.move((1, 0), gameStateObj)
            if self.position[0] >= (GC.WINWIDTH/GC.TILEWIDTH + gameStateObj.cameraOffset.get_x() - 3):
                gameStateObj.cameraOffset.set_x(gameStateObj.cameraOffset.x + 1)
        if 'UP' in directions and self.position[1] > 0:
            self.move((0, -1), gameStateObj)
            if self.position[1] <= gameStateObj.cameraOffset.get_y() + 2:
                gameStateObj.cameraOffset.set_y(gameStateObj.cameraOffset.y - 1)
        elif 'DOWN' in directions and self.position[1] < (gameStateObj.map.height - 1):
            self.move((0, 1), gameStateObj)
            if self.position[1] >= (GC.WINHEIGHT/GC.TILEHEIGHT + gameStateObj.cameraOffset.get_y() - 3):
                gameStateObj.cameraOffset.set_y(gameStateObj.cameraOffset.y + 1)

    def setPosition(self, newposition, gameStateObj):
        if not newposition:
            return            
        logger.debug('Cursor new position %s', newposition)
        self.position = newposition
        # Recenter camera
        if self.position[0] <= gameStateObj.cameraOffset.get_x() + 2: # Too far left
            gameStateObj.cameraOffset.set_x(self.position[0] - 3) # Testing...
        if self.position[0] >= (GC.WINWIDTH/GC.TILEWIDTH + gameStateObj.cameraOffset.get_x() - 3):
            gameStateObj.cameraOffset.set_x(self.position[0] + 4 - GC.WINWIDTH/GC.TILEWIDTH)
        if self.position[1] <= gameStateObj.cameraOffset.get_y() + 2:
            gameStateObj.cameraOffset.set_y(self.position[1] - 2)
        if self.position[1] >= (GC.WINHEIGHT/GC.TILEHEIGHT + gameStateObj.cameraOffset.get_y() - 3):
            gameStateObj.cameraOffset.set_y(self.position[1] + 3 - GC.WINHEIGHT/GC.TILEHEIGHT)
        # Remove unit display
        self.remove_unit_display()

    def forcePosition(self, newposition, gameStateObj):
        if not newposition:
            return            
        logger.debug('Cursor new position %s', newposition)
        self.position = newposition
        # Recenter camera
        if self.position[0] <= gameStateObj.cameraOffset.get_x() + 2: # Too far left
            gameStateObj.cameraOffset.force_x(self.position[0] - 3) # Testing...
        if self.position[0] >= (GC.WINWIDTH/GC.TILEWIDTH + gameStateObj.cameraOffset.get_x() - 3):
            gameStateObj.cameraOffset.force_x(self.position[0] + 4 - GC.WINWIDTH/GC.TILEWIDTH)
        if self.position[1] <= gameStateObj.cameraOffset.get_y() + 2:
            gameStateObj.cameraOffset.force_y(self.position[1] - 2)
        if self.position[1] >= (GC.WINHEIGHT/GC.TILEHEIGHT + gameStateObj.cameraOffset.get_y() - 3):
            gameStateObj.cameraOffset.force_y(self.position[1] + 3 - GC.WINHEIGHT/GC.TILEHEIGHT)
        # Remove unit display
        self.remove_unit_display()

    def autocursor(self, gameStateObj, force=False):
        player_units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and unit.position]
        lord = [unit for unit in player_units if 'Lord' in unit.tags]
        if force:
            if lord:
                gameStateObj.cursor.forcePosition(lord[0].position, gameStateObj)
            elif player_units:
                gameStateObj.cursor.forcePosition(player_units[0].position, gameStateObj)
        else:
            if lord:
                gameStateObj.cursor.setPosition(lord[0].position, gameStateObj)
            elif player_units:
                gameStateObj.cursor.setPosition(player_units[0].position, gameStateObj)

    def formatSprite(self, sprite):
        # Sprites are in 64 x 64 boxes
        passivesprite = Engine.subsurface(sprite, (0, 0, GC.TILEWIDTH*2*4, GC.TILEHEIGHT*2))
        redsprite = Engine.subsurface(sprite, (0, GC.TILEHEIGHT*2, GC.TILEWIDTH*2*4, GC.TILEHEIGHT*2))
        activesprite = Engine.subsurface(sprite, (0, GC.TILEHEIGHT*4, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
        formationsprite = Engine.subsurface(sprite, (GC.TILEWIDTH*2*2, GC.TILEHEIGHT*4, GC.TILEWIDTH*2*2, GC.TILEHEIGHT*2))
        return passivesprite, activesprite, redsprite, formationsprite

    def drawPortraits(self, surf, gameStateObj):
        legal_states = ['free', 'prep_formation', 'prep_formation_select']
        # Unit Info handling
        if self.remove_unit_info:
            if gameStateObj.stateMachine.getState() in legal_states and self.currentHoveredUnit: # Get this 
                self.remove_unit_info = False
                self.unit_info_disp = self.currentHoveredUnit.createPortrait(gameStateObj)
                self.unit_info_offset = min(self.unit_info_disp.get_width(), self.unit_info_offset)
            elif self.unit_info_disp:
                self.unit_info_offset += 20
                if self.unit_info_offset >= 200:
                    self.unit_info_disp = None
        else:
            self.unit_info_offset -= 20
            self.unit_info_offset = max(0, self.unit_info_offset)

        # Tile Info Handling
        if gameStateObj.stateMachine.getState() in legal_states and cf.OPTIONS['Show Terrain']:
            gameStateObj.cursor.currentHoveredTile = gameStateObj.map.tiles[gameStateObj.cursor.position]
            if gameStateObj.cursor.currentHoveredTile:
                self.tile_info_disp = gameStateObj.cursor.currentHoveredTile.getDisplay(gameStateObj)
                self.tile_info_offset = min(self.tile_info_disp.get_width(), self.tile_info_offset)
            self.tile_info_offset -= 20
            self.tile_info_offset = max(0, self.tile_info_offset)
        elif self.tile_info_disp:
            self.tile_info_offset += 20
            if self.tile_info_offset >= 200:
                self.tile_info_disp = None

        # Objective Info Handling
        if gameStateObj.stateMachine.getState() in legal_states and cf.OPTIONS['Show Objective']:
            self.obj_info_disp = gameStateObj.objective.draw(gameStateObj)
            self.obj_info_offset -= 20
            self.obj_info_offset = max(0, self.obj_info_offset)
        elif self.obj_info_disp:
            self.obj_info_offset += 20
            if self.obj_info_offset >= 200:
                self.obj_info_disp = None

        # === Final blitting
        # Should be in topleft, unless cursor is in topleft, in which case it should be in bottomleft
        if self.unit_info_disp:
            if self.position[1] < GC.TILEY/2 + gameStateObj.cameraOffset.get_y() and \
                    not (self.position[0] > GC.TILEX/2 + gameStateObj.cameraOffset.get_x() - 1):
                surf.blit(self.unit_info_disp, (0 - self.unit_info_offset, GC.WINHEIGHT - 0 - self.unit_info_disp.get_height()))
            else:
                surf.blit(self.unit_info_disp, (0 - self.unit_info_offset, 0))

        if self.tile_info_disp:
            # Should be in bottom, no matter what. Can be in bottomleft or bottomright, depending on where cursor is
            if self.position[0] > GC.WINWIDTH/2/GC.TILEWIDTH + gameStateObj.cameraOffset.get_x() - 1: # If cursor is right
                if self.tile_left:
                    self.tile_left = False
                    self.tile_info_offset = self.tile_info_disp.get_width()
                surf.blit(self.tile_info_disp, (5 - self.tile_info_offset, GC.WINHEIGHT - self.tile_info_disp.get_height() - 3)) # Bottomleft
            else:
                if not self.tile_left:
                    self.tile_left = True
                    self.tile_info_offset = self.tile_info_disp.get_width()
                pos = (GC.WINWIDTH - self.tile_info_disp.get_width() - 5 + self.tile_info_offset, GC.WINHEIGHT - self.tile_info_disp.get_height() - 3)
                surf.blit(self.tile_info_disp, pos) # Bottomright

        if self.obj_info_disp:
            # Should be in topright, unless the cursor is in the topright
            # TopRight - I believe this has RIGHT precedence
            if self.position[1] < GC.WINHEIGHT/2/GC.TILEHEIGHT + gameStateObj.cameraOffset.get_y() - 1 and \
                    gameStateObj.cursor.position[0] > GC.WINWIDTH/2/GC.TILEWIDTH + gameStateObj.cameraOffset.get_x() - 1:
                # Gotta place in bottomright, because cursor is in topright
                if self.obj_top:
                    self.obj_top = False
                    self.obj_info_offset = self.obj_info_disp.get_width()
                pos = (GC.WINWIDTH - GC.TILEWIDTH/4 + self.obj_info_offset - self.obj_info_disp.get_width(), 
                       GC.WINHEIGHT - GC.TILEHEIGHT/4 - self.obj_info_disp.get_height())
                surf.blit(self.obj_info_disp, pos) # Should be bottom right
            else:
                # Place in topright
                if not self.obj_top:
                    self.obj_top = True
                    self.obj_info_offset = self.obj_info_disp.get_width()
                surf.blit(self.obj_info_disp, (GC.WINWIDTH - GC.TILEWIDTH/4 + self.obj_info_offset - self.obj_info_disp.get_width(), 1))

    def take_input(self, eventList, gameStateObj):
        if not self.fake:
            self.fluid_helper.update(gameStateObj)
            # Handle cursor movement
            self.handleMovement(gameStateObj)

    def update(self, gameStateObj):
        self.currentHoveredUnit = gameStateObj.grid_manager.get_unit_node(self.position)

        if not self.drawState:
            self.remove_unit_display()

        self.fluid_helper.update_speed(cf.OPTIONS['Cursor Speed'])

        if gameStateObj.stateMachine.getState() == 'prep_formation_select':
            if 'Formation' in gameStateObj.map.tile_info_dict[self.position]:
                self.image = Engine.subsurface(self.formationsprite, (0, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
            else:
                self.image = Engine.subsurface(self.formationsprite, (GC.CURSORSPRITECOUNTER.count/2*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
        elif self.drawState == 2 and gameStateObj.stateMachine.getState() != 'dialogue': # Red if it is selecting...
            self.image = Engine.subsurface(self.redsprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
        elif self.currentHoveredUnit and self.currentHoveredUnit.team == 'player' and not self.currentHoveredUnit.isDone():
            self.image = self.activesprite
        else:
            self.image = Engine.subsurface(self.passivesprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
             
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
        self.highlights = {t: set() for t in self.types.keys()}

        self.lasthighlightUpdate = 0
        self.updateIndex = 0

        self.current_hover = None

    def add_highlight(self, position, name, allow_overlap=False):
        if not allow_overlap:
            for t in self.types.keys():
                self.highlights[t].discard(position)
        self.highlights[name].add(position)
        self.types[name][1] = 7 # Reset transitions

    def remove_highlights(self, name=None):
        if name in self.types:
            self.highlights[name] = set()
            self.types[name][1] = 7 # Reset transitions
        else:
            self.highlights = {t: set() for t in self.types.keys()}
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
        for name in self.highlights.keys():
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
            # self.current_hover.remove_aura_highlights(gameStateObj)
        if cur_hover and cur_hover != self.current_hover:
            ValidMoves = cur_hover.getValidMoves(gameStateObj)
            if cur_hover.getMainSpell():
                cur_hover.displayExcessSpellAttacks(gameStateObj, ValidMoves, light=True)
            if cur_hover.getMainWeapon():
                cur_hover.displayExcessAttacks(gameStateObj, ValidMoves, light=True)
            cur_hover.displayMoves(gameStateObj, ValidMoves, light=True)
            cur_hover.add_aura_highlights(gameStateObj)
        self.current_hover = cur_hover

# === BOUNDARY MANAGER ============================================
class BoundaryManager(object):
    def __init__(self, tilemap):
        self.types = {'attack': GC.IMAGESDICT['RedBoundary'],
                      'all_attack': GC.IMAGESDICT['PurpleBoundary'],
                      'spell': GC.IMAGESDICT['GreenBoundary'],
                      'all_spell': GC.IMAGESDICT['BlueBoundary']}
        self.gridHeight = tilemap.height
        self.gridWidth = tilemap.width
        self.grids = {'attack': self.init_grid(),
                      'spell': self.init_grid(),
                      'movement': self.init_grid()}
        self.dictionaries = {'attack': {},
                             'spell': {},
                             'movement': {}}
        self.order = ['all_spell', 'all_attack', 'spell', 'attack']

        self.draw_flag = False
        self.all_on_flag = False

        self.displaying_units = set()

        self.surf = None

    def init_grid(self):
        cells = []
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                cells.append(set())
        return cells

    def check_bounds(self, pos):
        if pos[0] >= 0 and pos[1] >= 0 and pos[0] < self.gridWidth and pos[1] < self.gridHeight:
            return True
        return False

    def toggle_unit(self, unit, gameStateObj):
        if unit.id in self.displaying_units:
            self.displaying_units.discard(unit.id)
            unit.flickerRed = False
            # self.remove_unit(unit, gameStateObj)
        else:
            self.displaying_units.add(unit.id)
            unit.flickerRed = True
            # self.add_unit(unit, gameStateObj)
        self.surf = None

    def _set(self, positions, kind, u_id):
        this_grid = self.grids[kind]
        self.dictionaries[kind][u_id] = set()
        for pos in positions:
            this_grid[pos[0] * self.gridHeight + pos[1]].add(u_id)
            self.dictionaries[kind][u_id].add(pos)
        # self.print_grid(kind)

    def clear(self, kind=False):
        if kind:
            kinds = [kind]
        else:
            kinds = self.grids.keys()
        for k in kinds:
            for x in range(self.gridWidth):
                for y in range(self.gridHeight):
                    self.grids[k][x * self.gridHeight + y] = set()
        self.surf = None

    def _add_unit(self, unit, gameStateObj):
        ValidMoves = unit.getValidMoves(gameStateObj, force=True)
        ValidAttacks, ValidSpells = [], []
        if unit.getMainWeapon():
            ValidAttacks = unit.getExcessAttacks(gameStateObj, ValidMoves, boundary=True)
        if unit.getMainSpell():
            ValidSpells = unit.getExcessSpellAttacks(gameStateObj, ValidMoves, boundary=True)
        self._set(ValidAttacks, 'attack', unit.id)
        self._set(ValidSpells, 'spell', unit.id)
        # self._set(ValidMoves, 'movement', unit.id)
        area_of_influence = Utility.find_manhattan_spheres(range(1, unit.stats['MOV'] + 1), unit.position)
        area_of_influence = {pos for pos in area_of_influence if gameStateObj.map.check_bounds(pos)}
        self._set(area_of_influence, 'movement', unit.id)
        # print(unit.name, unit.position, unit.klass, unit.event_id)
        self.surf = None

    def _remove_unit(self, unit, gameStateObj):
        for kind, grid in self.grids.iteritems():
            if unit.id in self.dictionaries[kind]:
                for (x, y) in self.dictionaries[kind][unit.id]:
                    grid[x * self.gridHeight + y].discard(unit.id)
        self.surf = None

    def leave(self, unit, gameStateObj):
        if unit.team.startswith('enemy'):
            self._remove_unit(unit, gameStateObj)
        # Update ranges of other units that might be affected by my leaving
        if unit.position:
            x, y = unit.position
            other_units = gameStateObj.get_unit_from_id(self.grids['movement'][x * self.gridHeight + y])
            # other_units = set()
            # for key, grid in self.grids.iteritems():
            # What other units were affecting that position -- only enemies can affect position
            #    other_units |= gameStateObj.get_unit_from_id(grid[x * self.gridHeight + y])
            other_units = {other_unit for other_unit in other_units if not gameStateObj.compare_teams(unit.team, other_unit.team)} 
            for other_unit in other_units:
                self._remove_unit(other_unit, gameStateObj)
            for other_unit in other_units:
                self._add_unit(other_unit, gameStateObj)

    def arrive(self, unit, gameStateObj):
        if unit.position:
            if unit.team.startswith('enemy'):
                self._add_unit(unit, gameStateObj)

            # Update ranges of other units that might be affected by my arrival
            x, y = unit.position
            other_units = gameStateObj.get_unit_from_id(self.grids['movement'][x * self.gridHeight + y])
            # other_units = set()
            # for key, grid in self.grids.iteritems():
            # What other units were affecting that position -- only enemies can affect position
            #    other_units |= gameStateObj.get_unit_from_id(grid[x * self.gridHeight + y])
            other_units = {other_unit for other_unit in other_units if not gameStateObj.compare_teams(unit.team, other_unit.team)} 
            # print([(other_unit.name, other_unit.position, other_unit.event_id, other_unit.klass, x, y) for other_unit in other_units])
            for other_unit in other_units:
                self._remove_unit(other_unit, gameStateObj)
            for other_unit in other_units:
                self._add_unit(other_unit, gameStateObj)

    # Called when map changes
    def reset(self, gameStateObj):
        self.clear()
        for unit in gameStateObj.allunits:
            if unit.position and unit.team.startswith('enemy'):
                self._add_unit(unit, gameStateObj)

    """
    # Deprecated
    # Called when map changes
    def reset_pos(self, pos_group, gameStateObj):
        other_units = set()
        for key, grid in self.grids.iteritems():
            # What other units are affecting those positions -- need to check every grid because line of sight might change
            for (x, y) in pos_group:
                other_units |= gameStateObj.get_unit_from_id(grid[x * self.gridHeight + y])
        for other_unit in other_units:
            self._remove_unit(other_unit, gameStateObj)
        for other_unit in other_units:
            self._add_unit(other_unit, gameStateObj)
    """

    def toggle_all_enemy_attacks(self, gameStateObj):
        if self.all_on_flag:
            self.clear_all_enemy_attacks(gameStateObj)
        else:
            self.show_all_enemy_attacks(gameStateObj)

    def show_all_enemy_attacks(self, gameStateObj):
        self.all_on_flag = True
        self.surf = None

    def clear_all_enemy_attacks(self, gameStateObj):
        self.all_on_flag = False
        self.surf = None

    def draw(self, surf, (width, height)):
        if self.draw_flag:
            if not self.surf:
                self.surf = Engine.create_surface((width, height), transparent=True)
                for grid_name in self.order:
                    if grid_name == 'attack' and not self.displaying_units:
                        continue
                    elif grid_name == 'spell' and not self.displaying_units:
                        continue
                    elif grid_name == 'all_attack' and not self.all_on_flag:
                        continue
                    elif grid_name == 'all_spell' and not self.all_on_flag:
                        continue
                    if grid_name == 'all_attack' or grid_name == 'attack':
                        grid = self.grids['attack']
                    else:
                        grid = self.grids['spell']
                    for y in range(self.gridHeight):
                        for x in range(self.gridWidth):
                            cell = grid[x * self.gridHeight + y]
                            if cell:
                                display = any(u_id in self.displaying_units for u_id in cell) if self.displaying_units else False
                                # print(x, y, cell, display)
                                # If there's one above this
                                if grid_name == 'all_attack' and display:
                                    continue
                                if grid_name == 'all_spell' and display:
                                    continue
                                if grid_name == 'attack' and not display:
                                    continue
                                if grid_name == 'spell' and not display:
                                    continue
                                image = self.get_image(grid, x, y, grid_name)
                                topleft = x * GC.TILEWIDTH, y * GC.TILEHEIGHT
                                self.surf.blit(image, topleft)
                            # else:
                            #    print('- '),
                        # print('\n'),
            surf.blit(self.surf, (0, 0))

    def get_image(self, grid, x, y, grid_name):
        top_pos = (x, y - 1)
        left_pos = (x - 1, y)
        right_pos = (x + 1, y)
        bottom_pos = (x, y + 1)
        if grid_name == 'all_attack' or grid_name == 'all_spell':
            top = bool(grid[x * self.gridHeight + y - 1]) if self.check_bounds(top_pos) else False
            left = bool(grid[(x - 1) * self.gridHeight + y]) if self.check_bounds(left_pos) else False
            right = bool(grid[(x + 1) * self.gridHeight + y]) if self.check_bounds(right_pos) else False
            bottom = bool(grid[x * self.gridHeight + y + 1]) if self.check_bounds(bottom_pos) else False
        else:
            top = any(u_id in self.displaying_units for u_id in grid[x * self.gridHeight + y - 1]) if self.check_bounds(top_pos) else False
            left = any(u_id in self.displaying_units for u_id in grid[(x - 1) * self.gridHeight + y]) if self.check_bounds(left_pos) else False
            right = any(u_id in self.displaying_units for u_id in grid[(x + 1) * self.gridHeight + y]) if self.check_bounds(right_pos) else False
            bottom = any(u_id in self.displaying_units for u_id in grid[x * self.gridHeight + y + 1]) if self.check_bounds(bottom_pos) else False
        index = top*8 + left*4 + right*2 + bottom # Binary logic to get correct index
        # print(str(index) + ' '),
        return Engine.subsurface(self.types[grid_name], (index*GC.TILEWIDTH, 0, GC.TILEWIDTH, GC.TILEHEIGHT))

    def print_grid(self, grid_name):
        for y in range(self.gridHeight):
            for x in range(self.gridWidth):
                cell = self.grids[grid_name][x * self.gridHeight + y]
                if cell:
                    print(cell),
                else:
                    print('- '),
            print('\n'),

# === GENERIC ARROW OBJECT ===================================================
class ArrowObject(object):
    sprite = GC.IMAGESDICT['MovementArrows']

    def __init__(self, index, position):
        rindex, cindex = index
        left = 1+((GC.TILEWIDTH+2)*cindex)+(1*int(cindex/2))
        top = 1+((GC.TILEHEIGHT+2)*rindex)
        self.image = Engine.subsurface(self.sprite, (left, top, GC.TILEWIDTH, GC.TILEHEIGHT))
        self.position = position

    def draw(self, surf):
        x, y = self.position
        topleft = x * GC.TILEWIDTH, y * GC.TILEHEIGHT
        surf.blit(self.image, topleft)

# === GENERIC ANIMATION OBJECT ===================================
# for miss and no damage animations
class Animation(object):
    def __init__(self, sprite, position, frames, total_num_frames=None, animation_speed=75,
                 loop=False, hold=False, ignore_map=False, start_time=0, on=True, set_timing=None):
        self.sprite = sprite
        self.position = position
        self.frame_x = frames[0]
        self.frame_y = frames[1]
        self.total_num_frames = total_num_frames if total_num_frames else self.frame_x * self.frame_y
        self.frameCount = 0
        self.animation_speed = animation_speed
        self.loop = loop
        self.hold = hold
        self.start_time = start_time
        self.on = on
        self.tint = False
        self.ignore_map = ignore_map # Whether the position of the Animation sould be relative to the map
        self.lastUpdate = Engine.get_time()

        self.set_timing = set_timing
        if self.set_timing:
            assert len([timing for timing in self.set_timing if timing > 0]) == self.total_num_frames, \
                '%s %s'%(len(self.set_timing), len(self.total_num_frames))
        self.timing_count = -1

        self.indiv_width, self.indiv_height = self.sprite.get_width()/self.frame_x, self.sprite.get_height()/self.frame_y

        self.image = Engine.subsurface(self.sprite, (0, 0, self.indiv_width, self.indiv_height))

    def draw(self, surf, gameStateObj=None, blend=None):
        if self.on and self.frameCount >= 0 and Engine.get_time() > self.start_time:
            # The animation is too far to the right. Must move left. (" - 32")
            image = self.image
            x, y = self.position
            if self.ignore_map:
                topleft = x, y
            else:
                topleft = (x-gameStateObj.cameraOffset.x-1)*GC.TILEWIDTH, (y-gameStateObj.cameraOffset.y)*GC.TILEHEIGHT
            if blend:
                image = Image_Modification.change_image_color(image, blend)
            if self.tint:
                Engine.blit(surf, image, topleft, image.get_rect(), Engine.BLEND_RGB_ADD)
            else:
                surf.blit(image, topleft)

    def update(self, gameStateObj=None):
        currentTime = Engine.get_time()
        if self.on and currentTime > self.start_time:
            # If this animation has every frame's count defined
            if self.set_timing:
                num_frames = self.set_timing[self.frameCount]
                # If you get a -1 on set timing, switch to blend tint
                while num_frames < 0:
                    self.tint = not self.tint 
                    self.frameCount += 1
                    num_frames = self.set_timing[self.frameCount]
                self.timing_count += 1
                if self.timing_count >= num_frames:
                    self.timing_count = 0
                    self.frameCount += 1
                    if self.frameCount >= self.total_num_frames:
                        if self.loop:
                            self.frameCount = 0
                        elif self.hold:
                            self.frameCount = self.total_num_frames - 1
                        else:
                            if gameStateObj and self in gameStateObj.allanimations:
                                gameStateObj.allanimations.remove(self)
                            return True
                    if self.frameCount >= 0:
                        rect = (self.frameCount%self.frame_x * self.indiv_width, self.frameCount/self.frame_x * self.indiv_height, 
                                self.indiv_width, self.indiv_height)
                        self.image = Engine.subsurface(self.sprite, rect)
            # Otherwise
            elif currentTime - self.lastUpdate > self.animation_speed:
                self.frameCount += int((currentTime - self.lastUpdate)/self.animation_speed) # 1
                self.lastUpdate = currentTime
                if self.frameCount >= self.total_num_frames:
                    if self.loop: # Reset framecount
                        self.frameCount = 0
                    elif self.hold:
                        self.frameCount = self.total_num_frames - 1 # Hold on last frame
                    else:
                        if gameStateObj and self in gameStateObj.allanimations:
                            gameStateObj.allanimations.remove(self)
                        return True
                if self.frameCount >= 0:
                    rect = (self.frameCount%self.frame_x * self.indiv_width, self.frameCount/self.frame_x * self.indiv_height, 
                            self.indiv_width, self.indiv_height)
                    self.image = Engine.subsurface(self.sprite, rect)

# === PHASE OBJECT ============================================================
class Phase(object):
    def __init__(self, gameStateObj):
        self.phase_in = []
        self.phase_in.append(PhaseIn('player', 'PlayerTurnBanner', 800))
        self.phase_in.append(PhaseIn('enemy', 'EnemyTurnBanner', 800))
        self.phase_in.append(PhaseIn('enemy2', 'Enemy2TurnBanner', 800))
        self.phase_in.append(PhaseIn('other', 'OtherTurnBanner', 800))
        self.order = ('player', 'enemy', 'enemy2', 'other')

        self.current = 3 if gameStateObj.turncount == 0 else 0
        self.previous = 0

    def get_current_phase(self):
        return self.order[self.current]

    def get_previous_phase(self):
        return self.order[self.previous]

    def _next(self):
        self.current += 1
        if self.current >= len(self.order):
            self.current = 0

    def next(self, gameStateObj):
        self.previous = self.current
        # Actually change phase
        if gameStateObj.allunits:
            self._next()
            while not any(self.get_current_phase() == unit.team for unit in gameStateObj.allunits if unit.position) \
                    and self.current != 0: # Also, never skip player phase
                self._next()
        else:
            self.current = 0 # If no units at all, just default to player phase?

    def slide_in(self, gameStateObj):
        self.phase_in[self.current].begin(gameStateObj)

    def update(self):
        return self.phase_in[self.current].update()

    def draw(self, surf):
        self.phase_in[self.current].draw(surf)

class PhaseIn(object):
    def __init__(self, name, spritename, display_time):
        self.name = name
        self.spritename = spritename
        self.loadSprites()
        self.display_time = display_time
        self.topleft = ((GC.WINWIDTH - self.image.get_width())/2, (GC.WINHEIGHT - self.image.get_height())/2)
        self.start_time = None # Don't define it here. Define it at first update

    def loadSprites(self):
        self.image = GC.IMAGESDICT[self.spritename]
        self.transition = GC.IMAGESDICT['PhaseTransition'] # The Black Squares that happen during a phase transition
        self.transition_size = (16, 16)

    def removeSprites(self):
        self.image = None
        self.transition = None

    def update(self):
        if Engine.get_time() - self.start_time >= self.display_time:
            return True
        else:
            return False

    def begin(self, gameStateObj):
        currentTime = Engine.get_time()
        GC.SOUNDDICT['Next Turn'].play()
        if self.name == 'player':
            # Keeps track of where units started their turns (mainly)
            for unit in gameStateObj.allunits:
                unit.previous_position = unit.position

            # Set position over leader lord
            if cf.OPTIONS['Autocursor']:
                gameStateObj.cursor.autocursor(gameStateObj)
            else: # Set position to where it was when we ended turn
                gameStateObj.cursor.setPosition(gameStateObj.statedict['previous_cursor_position'], gameStateObj)
        self.start_time = currentTime

    def draw(self, surf):
        currentTime = Engine.get_time()
        time_passed = currentTime - self.start_time
        if cf.OPTIONS['debug'] and time_passed < 0:
            logger.error('This phase has a negative time_passed! %s %s %s', time_passed, currentTime, self.start_time)
        max_opaque = 160

        # Blit the banner
        # position
        if time_passed < 100:
            offset = self.topleft[0] + 100 - time_passed
            trans = 100 - time_passed
        elif time_passed > self.display_time - 100:
            offset = self.topleft[0] + self.display_time - 100 - time_passed 
            trans = -(self.display_time - 100 - time_passed)
        else:
            offset = self.topleft[0]
            trans = 0
        # transparency
        image = Image_Modification.flickerImageTranslucent(self.image.copy(), trans)
        surf.blit(image, (offset, self.topleft[1]))
        
        # === Handle the transition
        most_dark_surf = Engine.subsurface(self.transition, (8*self.transition_size[0], 0, self.transition_size[0], self.transition_size[1])).copy()
        # If we're in the first half
        if time_passed < self.display_time/2:
            transition_space = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT/2 - 75/2 + time_passed/(self.display_time/2/20)), transparent=True)
            # Make more transparent based on time.
            alpha = int(max_opaque * time_passed/float(self.display_time/2))
            Engine.fill(most_dark_surf, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)
        # If we're in the second half
        else:
            # Clamp time_passed at display time
            time_passed = min(self.display_time, time_passed)
            pos = (GC.WINWIDTH, GC.WINHEIGHT/2 - 75/2 + 40/2 - (time_passed - self.display_time/2)/(self.display_time/2/20))
            transition_space = Engine.create_surface(pos, transparent=True)
            # Make less transparent based on time.
            alpha = int(max_opaque - max_opaque*(time_passed - self.display_time/2)/float(self.display_time/2))
            alpha = min(255, max(0, alpha))
            Engine.fill(most_dark_surf, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)
        # transition_space.convert_alpha()
        # Tile
        for x in range(0, transition_space.get_width(), 16):
            for y in range(0, transition_space.get_height(), 16):
                transition_space.blit(most_dark_surf, (x, y))

        # Now blit transition space
        surf.blit(transition_space, (0, 0))
        # Other transition_space
        surf.blit(transition_space, (0, GC.WINHEIGHT - transition_space.get_height()))

# === WEAPON TRIANGLE OBJECT ==================================================
class Weapon_Triangle(object):
    def __init__(self, fp):
        self.types = []
        self.advantage = {}
        self.disadvantage = {}
        self.type_to_index = {}
        self.index_to_type = {}
        self.magic_types = []

        self.parse_file(fp)

    def number(self):
        return len(self.types)

    def parse_file(self, fp):
        lines = []
        with open(fp) as w_fp:
            lines = w_fp.readlines()

        for index, line in enumerate(lines):
            split_line = line.strip().split(';')
            name = split_line[0]
            advantage = split_line[1].split(',')
            disadvantage = split_line[2].split(',')
            magic = True if split_line[3] == 'M' else False
            # Ascend
            self.types.append(name)
            self.type_to_index[name] = index
            self.index_to_type[index] = name
            self.advantage[name] = advantage
            self.disadvantage[name] = disadvantage
            if magic:
                self.magic_types.append(name)

        self.type_to_index['Consumable'] = len(lines)
        self.index_to_type[len(lines)] = 'Consumable'

    def compute_advantage(self, weapon1, weapon2):
        """ Returns two-tuple describing advantage """
        if not weapon1 and not weapon2:
            return (0, 0) # If either does not have a weapon, neither has advantage
        if not weapon1:
            return (0, 2)
        if not weapon2:
            return (2, 0)

        weapon1_advantage, weapon2_advantage = 0, 0
        for weapon1_type in weapon1.TYPE:
            for weapon2_type in weapon2.TYPE:
                if weapon2_type in self.advantage[weapon1_type]:
                    weapon1_advantage += 1
                if weapon2_type in self.disadvantage[weapon1_type]:
                    weapon1_advantage -= 1
                if weapon1_type in self.advantage[weapon2_type]:
                    weapon2_advantage += 1
                if weapon1_type in self.disadvantage[weapon2_type]:
                    weapon2_advantage -= 1

        # Handle reverse (reaver) weapons
        if weapon1.reverse or weapon2.reverse:
            return (-2*weapon1_advantage, -2*weapon2_advantage)
        else:
            return (weapon1_advantage, weapon2_advantage)

    def isMagic(self, item):
        if item.magic or item.magic_at_range or any(w_type in self.magic_types for w_type in item.TYPE):
            return True
        return False

class Weapon_Exp(object):
    def __init__(self, fp):
        self.wexp_dict = {}
        self.sorted_list = []
        self.parse_file(fp)

    def parse_file(self, fp):
        lines = []
        with open(fp) as w_fp:
            lines = w_fp.readlines()

        for index, line in enumerate(lines):
            split_line = line.strip().split(';')
            letter = split_line[0]
            number = int(split_line[1])
            self.wexp_dict[letter] = number

        self.sorted_list = sorted(self.wexp_dict.items(), key=lambda x: x[1])

    def number_to_letter(self, wexp):
        current_letter = "--"
        for letter, number in self.sorted_list:
            if wexp >= number:
                current_letter = letter
            else:
                break
        return current_letter

    # Returns a float between 0 and 1 desribing how closes number is to next tier from previous tier
    def percentage(self, wexp):
        current_percentage = 0.0
        # print(wexp, self.sorted_list)
        for index, (letter, number) in enumerate(self.sorted_list):
            if index + 1 >= len(self.sorted_list):
                current_percentage = 1.0
                break
            elif wexp >= number:
                difference = float(self.sorted_list[index+1][1] - number)
                if wexp - number >= difference:
                    continue
                current_percentage = (wexp - number)/difference
                # print('WEXP', wexp, number, difference, current_percentage)
                break
        return current_percentage

# === SAVESLOTS ===============================================================
class SaveSlot(object):
    def __init__(self, metadata_fp, number):
        self.no_name = '--NO DATA--'
        self.name = self.no_name
        self.playtime = 0
        self.realtime = 0
        self.kind = None # Prep, Base, Suspend, Battle, Start
        self.number = number

        self.metadata_fp = metadata_fp
        self.true_fp = metadata_fp[:-4]

        self.read()

    def read(self):
        try:
            if os.path.exists(self.metadata_fp):
                with open(self.metadata_fp, 'rb') as loadFile:
                    save_metadata = pickle.load(loadFile)
                self.name = save_metadata['name']
                self.playtime = save_metadata['playtime']
                self.realtime = save_metadata['realtime']
                self.kind = save_metadata['kind']

        except ValueError as e:
            print('***Value Error: %s' % (e))
        except ImportError as e:
            print('***Import Error: %s' % (e))
        except TypeError as e:
            print('***Type Error: %s' % (e))
        except KeyError as e:
            print('***Key Error: %s' % (e))
        except IOError as e:
            print('***IO Error: %s' % (e))

    def get_name(self):
        return self.name + (' - ' + self.kind if self.kind else '')

    def loadGame(self):
        with open(self.true_fp, 'rb') as loadFile:
            saveObj = pickle.load(loadFile)
        return saveObj

# === MAPSELECTHELPER =========================================================
class MapSelectHelper(object):
    def __init__(self, pos_list):
        self.pos_list = pos_list

    # For a given position, determine which position in self.pos_list is closest
    def get_closest(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            dist = Utility.calculate_distance(pos, position)
            if dist < min_distance:
                closest = pos
                min_distance = dist
        return closest

    # For a given position, determine which position in self.pos_list is the closest position in the downward direction
    def get_down(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[1] > position[1]: # If further down than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_up(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[1] < position[1]: # If further up than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_right(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[0] > position[0]: # If further right than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_left(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[0] < position[0]: # If further left than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

class CameraOffset(object):
    def __init__(self, x, y):
        # Where the camera is supposed to be
        self.x = x
        self.y = y
        # Where the camera actually is
        self.current_x = x
        self.current_y = y
        # Where the camera was
        self.old_x = x
        self.old_y = y

        self.speed = 6.0 # Linear. 

        self.pan_flag = False
        self.pan_to = []

    def set_x(self, x):
        self.x = x
        self.old_x = x

    def set_y(self, y):
        self.y = y
        self.old_y = y

    def force_x(self, x):
        self.current_x = self.x = x

    def force_y(self, y):
        self.current_y = self.y = y

    def set_xy(self, x, y):
        self.x = x
        self.y = y
        self.old_x = x
        self.old_y = y

    def get_xy(self):
        return (self.current_x, self.current_y)

    def get_x(self):
        return self.current_x

    def get_y(self):
        return self.current_y

    def center2(self, old, new):
        x1, y1 = old
        x2, y2 = new
        # logger.debug('Camera Center: %s %s %s %s', (x1, y1), (x2, y2), self.x, self.y)
        max_x = max(x1, x2)
        max_y = max(y1, y2)
        min_x = min(x1, x2)
        min_y = min(y1, y2)

        if self.x > min_x - 4 or self.x + GC.TILEX < max_x + 4 or self.y > min_y - 3 or self.y + GC.TILEY < max_y + 3:
            self.x = (max_x + min_x)/2 - GC.TILEX/2
            self.y = (max_y + min_y)/2 - GC.TILEY/2
        
        # logger.debug('New Camera: %s %s', self.x, self.y)

    def check_loc(self):
        # logger.debug('Camera %s %s %s %s', self.current_x, self.current_y, self.x, self.y)
        if not self.pan_to and self.current_x == self.x and self.current_y == self.y:
            self.pan_flag = False
            return True
        return False

    def map_pan(self, tile_map, cursor_pos):
        corners = [(0, 0), (0, tile_map.height - 1), (tile_map.width - 1, tile_map.height - 1), (tile_map.width - 1, 0)]
        distance = [Utility.calculate_distance(cursor_pos, corner) for corner in corners]
        closest_corner, idx = min((val, idx) for (idx, val) in enumerate(distance))
        # print(self.current_x, self.current_y)
        # print(corners, distance, closest_corner, idx)
        self.pan_to = corners[idx:] + corners[:idx]
        # print(self.pan_to)

    def update(self, gameStateObj):
        gameStateObj.set_camera_limits()
        if self.current_x != self.x:
            if self.current_x > self.x:
                self.current_x -= 0.125 if self.pan_flag else (self.current_x - self.x)/self.speed
            elif self.current_x < self.x:
                self.current_x += 0.125 if self.pan_flag else (self.x - self.current_x)/self.speed
        if self.current_y != self.y:
            if self.current_y > self.y:
                self.current_y -= 0.125 if self.pan_flag else (self.current_y - self.y)/self.speed
            elif self.current_y < self.y:
                self.current_y += 0.125 if self.pan_flag else (self.y - self.current_y)/self.speed
        # If they are close enough, make them so.
        if abs(self.current_x - self.x) < 0.125:
            self.current_x = self.x
        if abs(self.current_y - self.y) < 0.125:
            self.current_y = self.y
        # Move to next place on the list
        if self.pan_to and self.current_y == self.y and self.current_x == self.x:
            self.x, self.y = self.pan_to.pop()

        # Make sure current_x and current_y do not go off screen
        if self.current_x < 0:
            self.current_x = 0
        elif self.current_x > (gameStateObj.map.width - GC.TILEX): # Need this minus to account for size of screen
            self.current_x = (gameStateObj.map.width - GC.TILEX)
        if self.current_y < 0:
            self.current_y = 0
        elif self.current_y > (gameStateObj.map.height - GC.TILEY):
            self.current_y = (gameStateObj.map.height - GC.TILEY)
        # logger.debug('Camera %s %s %s %s', self.current_x, self.current_y, self.x, self.y)

class Objective(object):
    def __init__(self, display_name, win_condition, loss_condition):
        self.display_name_string = display_name
        self.win_condition_string = win_condition
        self.loss_condition_string = loss_condition
        self.connectives = ['OR', 'AND']

        self.removeSprites()

    def removeSprites(self):
        # For drawing
        self.BGSurf = None
        self.surf_width = 0
        self.num_lines = 0

    def serialize(self):
        return (self.display_name_string, self.win_condition_string, self.loss_condition_string)

    @classmethod
    def deserialize(cls, info):
        return cls(*info[0])

    def eval_string(self, text, gameStateObj):
        # Parse evals
        to_evaluate = re.findall(r'\{[^}]*\}', text)
        evaluated = []
        for evaluate in to_evaluate:
            evaluated.append(str(eval(evaluate[1:-1])))
        for index in range(len(to_evaluate)):
            text = text.replace(to_evaluate[index], evaluated[index])
        return text

    def split_string(self, text):
        return text.split(',')

    def get_size(self, text_lines):
        longest_surf_width = 0
        for line in text_lines:
            guess = GC.FONT['text_white'].size(line)[0]
            if guess > longest_surf_width:
                longest_surf_width = guess
        return longest_surf_width

    # Mini-Objective that shows up in free state
    def draw(self, gameStateObj):
        text_lines = self.split_string(self.eval_string(self.display_name_string, gameStateObj))

        longest_surf_width = self.get_size(text_lines)

        if longest_surf_width != self.surf_width or len(text_lines) != self.num_lines:
            self.num_lines = len(text_lines)
            self.surf_width = longest_surf_width
            surf_height = 16 * self.num_lines + 8

            # Blit background
            BGSurf = MenuFunctions.CreateBaseMenuSurf((self.surf_width + 16, surf_height), 'BaseMenuBackgroundOpaque')
            if self.num_lines == 1:
                BGSurf.blit(GC.IMAGESDICT['Shimmer1'], (BGSurf.get_width() - 1 - GC.IMAGESDICT['Shimmer1'].get_width(), 4))
            elif self.num_lines == 2:
                BGSurf.blit(GC.IMAGESDICT['Shimmer2'], (BGSurf.get_width() - 1 - GC.IMAGESDICT['Shimmer2'].get_width(), 4))
            self.BGSurf = Engine.create_surface((BGSurf.get_width(), BGSurf.get_height() + 3), transparent=True, convert=True)
            self.BGSurf.blit(BGSurf, (0, 3))
            gem = GC.IMAGESDICT['BlueCombatGem']
            self.BGSurf.blit(gem, (BGSurf.get_width()/2 - gem.get_width()/2, 0))
            # Now make translucent
            self.BGSurf = Image_Modification.flickerImageTranslucent(self.BGSurf, 20)

        temp_surf = self.BGSurf.copy()
        for index, line in enumerate(text_lines):
            position = temp_surf.get_width()/2 - GC.FONT['text_white'].size(line)[0]/2, 16 * index + 6
            GC.FONT['text_white'].blit(line, temp_surf, position)

        return temp_surf

    def get_win_conditions(self, gameStateObj):
        text_list = self.split_string(self.eval_string(self.win_condition_string, gameStateObj))
        win_cons = [text for text in text_list if text not in self.connectives]
        connectives = [text for text in text_list if text in self.connectives]
        return win_cons, connectives

    def get_loss_conditions(self, gameStateObj):
        text_list = self.split_string(self.eval_string(self.loss_condition_string, gameStateObj))
        loss_cons = [text for text in text_list if text not in self.connectives]
        connectives = [text for text in text_list if text in self.connectives]
        return loss_cons, connectives

# === HANDLES PRESSING INFO AND APPLYING HELP MENU ===========================
def handle_info_key(gameStateObj, metaDataObj, chosen_unit=None, one_unit_only=False, scroll_units=None):
    gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
    if chosen_unit:
        my_unit = chosen_unit
    elif gameStateObj.cursor.currentHoveredUnit:
        my_unit = gameStateObj.cursor.currentHoveredUnit
    else:
        return
    GC.SOUNDDICT['Select 1'].play()
    gameStateObj.info_menu_struct['one_unit_only'] = one_unit_only
    gameStateObj.info_menu_struct['scroll_units'] = scroll_units
    gameStateObj.info_menu_struct['chosen_unit'] = my_unit
    gameStateObj.stateMachine.changeState('info_menu')
    gameStateObj.stateMachine.changeState('transition_out')

# === HANDLES PRESSING AUX ===================================================
def handle_aux_key(gameStateObj):
    avail_units = [unit.position for unit in gameStateObj.allunits if unit.team == 'player' and unit.position and not unit.isDone()]
    if avail_units:
        if handle_aux_key.counter > len(avail_units) - 1:
            handle_aux_key.counter = 0
        pos = avail_units[handle_aux_key.counter]
        GC.SOUNDDICT['Select 4'].play()
        gameStateObj.cursor.setPosition(pos, gameStateObj)

        # Increment counter
        handle_aux_key.counter += 1
# Initialize counter
handle_aux_key.counter = 0

class WeaponIcon(object):
    def __init__(self, name=None, idx=None, grey=False):
        if name:
            self.name = name
            self.idx = WEAPON_TRIANGLE.type_to_index[self.name]
        else:
            self.name = None
            self.idx = idx
        self.set_grey(grey)

    def set_grey(self, grey):
        self.grey = grey
        self.create_image()

    def create_image(self):
        # Weapon Icons Pictures
        if self.grey:
            weaponIcons = GC.ITEMDICT['Gray_Wexp_Icons']
        else:
            weaponIcons = GC.ITEMDICT['Wexp_Icons']
        self.image = Engine.subsurface(weaponIcons, (0, 16*self.idx, 16, 16))

    def draw(self, surf, topleft, cooldown=False):
        surf.blit(self.image, topleft)

class LevelStatistic(object):
    def __init__(self, gameStateObj, metaDataObj):
        self.name = metaDataObj['name']
        self.turncount = gameStateObj.turncount
        self.stats = self.get_records(gameStateObj)

    def get_records(self, gameStateObj):
        records = {}
        for unit in gameStateObj.allunits:
            if unit.team == 'player' and not unit.generic_flag:
                records[unit.name] = unit.records
        return records

    @staticmethod
    def formula(record):
        return record['kills']*cf.CONSTANTS['kill_worth'] + record['damage'] + record['healing']

    def get_mvp(self):
        tp = 0
        current_mvp = 'Ophie'
        for unit, record in self.stats.iteritems():
            test = self.formula(record)
            if test > tp:
                tp = test
                current_mvp = unit 

        return current_mvp

WEAPON_TRIANGLE = Weapon_Triangle(Engine.engine_constants['home'] + "Data/weapon_triangle.txt")
WEAPON_EXP = Weapon_Exp(Engine.engine_constants['home'] + "Data/weapon_exp.txt")
