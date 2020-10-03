from . import GlobalConstants as GC
from . import configuration as cf
from . import Engine, InputManager

import logging
logger = logging.getLogger(__name__)

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

        self.back_pressed = False
        self.spriteOffset = [0, 0]
        self.already_stopped_at_move_border = False  # Only applies during MoveState in StateMachine
        self.border_position = None  # Where the arrow stopped at the border
        
    def draw(self, surf):
        if self.drawState or self.fake: # Only draws if cursor is on
            x, y = self.position
            # The space Rect is constructed like so so as to center the cursor sprite
            topleft = x * GC.TILEWIDTH - max(0, (self.image.get_width() - 16)//2), y * GC.TILEHEIGHT - max(0, (self.image.get_height() - 16)//2)
            topleft = topleft[0] - self.spriteOffset[0], topleft[1] - self.spriteOffset[1]
            surf.blit(self.image, topleft)
            # Reset sprite offset afterwards
            num = 8 if self.back_pressed else 4
            if self.spriteOffset[0] > 0:
                self.spriteOffset[0] = max(0, self.spriteOffset[0] - num)
            elif self.spriteOffset[0] < 0:
                self.spriteOffset[0] = min(0, self.spriteOffset[0] + num)
            if self.spriteOffset[1] > 0:
                self.spriteOffset[1] = max(0, self.spriteOffset[1] - num)
            elif self.spriteOffset[1] < 0:
                self.spriteOffset[1] = min(0, self.spriteOffset[1] + num)

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
        self.passivesprite, self.activesprite, self.redsprite, self.greensprite = None, None, None, None

        # Current displays
        self.init_displays()
        
    def loadSprites(self):
        # Load sprite
        self.sprite = GC.IMAGESDICT[self.spriteName]
        self.passivesprite, self.activesprite, self.redsprite, self.formationsprite, self.greensprite = self.formatSprite(self.sprite)
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
            if self.back_pressed:
                self.spriteOffset[0] += 8*dx
                self.spriteOffset[1] += 8*dy
            else:
                self.spriteOffset[0] += 12*dx
                self.spriteOffset[1] += 12*dy

    def place_arrows(self, gameStateObj):
        if gameStateObj.highlight_manager.check_arrow(self.position):
            self.border_position = self.position
        if gameStateObj.stateMachine.getState() == 'move':
            if self.border_position:
                self.movePath = self.currentSelectedUnit.getPath(gameStateObj, self.border_position)
                self.constructArrows(self.movePath[::-1], gameStateObj)
            elif gameStateObj.highlight_manager.check_arrow(self.position):
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
        if self.already_stopped_at_move_border:  # Must click again to keep moving
            self.fluid_helper.update(gameStateObj, hold=False)
        else:
            self.fluid_helper.update(gameStateObj)
        # Back doubles speed
        gameStateObj.cameraOffset.back_pressed(self.back_pressed)  # changes camera speed
        directions = self.fluid_helper.get_directions(double_speed=self.back_pressed)

        # This section tries to handle the case where the cursor should STOP when it reaches the units movement borders
        # However, it then needs to continue on when re-pressed
        if gameStateObj.highlight_manager.check_arrow(self.position):
            if directions:
                if ('LEFT' in directions and 'LEFT' not in gameStateObj.input_manager.key_down_events and not gameStateObj.highlight_manager.check_arrow((self.position[0] - 1, self.position[1]))) or \
                   ('RIGHT' in directions and 'RIGHT' not in gameStateObj.input_manager.key_down_events and not gameStateObj.highlight_manager.check_arrow((self.position[0] + 1, self.position[1]))) or \
                   ('UP' in directions and 'UP' not in gameStateObj.input_manager.key_down_events and not gameStateObj.highlight_manager.check_arrow((self.position[0], self.position[1] - 1))) or \
                   ('DOWN' in directions and 'DOWN' not in gameStateObj.input_manager.key_down_events and not gameStateObj.highlight_manager.check_arrow((self.position[0], self.position[1] + 1))):
                    if self.already_stopped_at_move_border:
                        self.already_stopped_at_move_border = False
                    else:
                        directions = []
                        self.fluid_helper.reset()  # Reset input so we don't keep going
                        self.already_stopped_at_move_border = True
                else:
                    self.already_stopped_at_move_border = False
        else:
            self.already_stopped_at_move_border = False

        # Normal movement
        if 'LEFT' in directions and self.position[0] > 0:
            self.move((-1, 0), gameStateObj)
            if self.position[0] <= gameStateObj.cameraOffset.get_x() + 2: # Cursor controls camera movement
                # Set x is move the camera. Move it to its x_pos - 1, cause we're moving left
                gameStateObj.cameraOffset.set_x(gameStateObj.cameraOffset.x - 1)
        elif 'RIGHT' in directions and self.position[0] < (gameStateObj.map.width - 1):
            self.move((1, 0), gameStateObj)
            if self.position[0] >= (GC.TILEX + gameStateObj.cameraOffset.get_x() - 3):
                gameStateObj.cameraOffset.set_x(gameStateObj.cameraOffset.x + 1)
        if 'UP' in directions and self.position[1] > 0:
            self.move((0, -1), gameStateObj)
            if self.position[1] <= gameStateObj.cameraOffset.get_y() + 2:
                gameStateObj.cameraOffset.set_y(gameStateObj.cameraOffset.y - 1)
        elif 'DOWN' in directions and self.position[1] < (gameStateObj.map.height - 1):
            self.move((0, 1), gameStateObj)
            if self.position[1] >= (GC.TILEY + gameStateObj.cameraOffset.get_y() - 3):
                gameStateObj.cameraOffset.set_y(gameStateObj.cameraOffset.y + 1)

    def _set_position(self, pos, func_x, func_y, gameStateObj):
        if not pos:
            return            
        logger.debug('Cursor new position %s', pos)
        self.position = pos
        # Recenter camera only if necessary
        if self.position[0] <= gameStateObj.cameraOffset.get_x() + 2: # Too far left
            func_x(self.position[0] - 3) # Testing...
        if self.position[0] >= (GC.TILEX + gameStateObj.cameraOffset.get_x() - 3):
            func_x(self.position[0] + 4 - GC.TILEX)
        if self.position[1] <= gameStateObj.cameraOffset.get_y() + 2:
            func_y(self.position[1] - 2)
        if self.position[1] >= (GC.TILEY + gameStateObj.cameraOffset.get_y() - 3):
            func_y(self.position[1] + 3 - GC.TILEY)
        # Remove unit display
        self.remove_unit_display()

    def setPosition(self, newposition, gameStateObj):
        self._set_position(newposition, gameStateObj.cameraOffset.set_x, gameStateObj.cameraOffset.set_y, gameStateObj)

    def forcePosition(self, newposition, gameStateObj):
        self._set_position(newposition, gameStateObj.cameraOffset.force_x, gameStateObj.cameraOffset.force_y, gameStateObj)

    def centerPosition(self, newposition, gameStateObj):
        if not newposition:
            return            
        logger.debug('Cursor new position %s', newposition)
        self.position = newposition
        gameStateObj.cameraOffset.set_x(self.position[0] - GC.TILEX//2)
        gameStateObj.cameraOffset.set_y(self.position[1] - GC.TILEY//2)
        self.remove_unit_display()

    def autocursor(self, gameStateObj, force=False):
        player_units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and unit.position]
        lord = [unit for unit in player_units if 'Lord' in unit.tags]
        if force:
            if lord:
                self.forcePosition(lord[0].position, gameStateObj)
            elif player_units:
                self.forcePosition(player_units[0].position, gameStateObj)
        else:
            if lord:
                self.setPosition(lord[0].position, gameStateObj)
            elif player_units:
                self.setPosition(player_units[0].position, gameStateObj)

    def formatSprite(self, sprite):
        # Sprites are in 32 x 32 boxes
        passivesprite = Engine.subsurface(sprite, (0, 0, 128, 32))
        redsprite = Engine.subsurface(sprite, (0, 32, 128, 32))
        activesprite = Engine.subsurface(sprite, (0, 64, 32, 32))
        formationsprite = Engine.subsurface(sprite, (64, 64, 64, 32))
        greensprite = Engine.subsurface(sprite, (0, 96, 128, 32))
        return passivesprite, activesprite, redsprite, formationsprite, greensprite

    def drawPortraits(self, surf, gameStateObj):
        legal_states = ('free', 'prep_formation', 'prep_formation_select')
        # Unit Info handling
        if self.remove_unit_info:
            if gameStateObj.stateMachine.getState() in legal_states and self.currentHoveredUnit: # Get this 
                self.remove_unit_info = False
                self.unit_info_disp = self.currentHoveredUnit.createPortrait()
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
            self.tile_info_disp = gameStateObj.map.getDisplay(self.position, gameStateObj)
            if self.tile_info_disp:
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
            if self.position[1] < GC.TILEY//2 + gameStateObj.cameraOffset.get_y() and \
                    not (self.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1):
                surf.blit(self.unit_info_disp, (0 - self.unit_info_offset, GC.WINHEIGHT - 0 - self.unit_info_disp.get_height()))
            else:
                surf.blit(self.unit_info_disp, (0 - self.unit_info_offset, 0))

        if self.tile_info_disp:
            # Should be in bottom, no matter what. Can be in bottomleft or bottomright, depending on where cursor is
            if self.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1: # If cursor is right
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
            if self.position[1] < GC.TILEY//2 + gameStateObj.cameraOffset.get_y() and \
                    gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1:
                # Gotta place in bottomright, because cursor is in topright
                if self.obj_top:
                    self.obj_top = False
                    self.obj_info_offset = self.obj_info_disp.get_width()
                pos = (GC.WINWIDTH - GC.TILEWIDTH//4 + self.obj_info_offset - self.obj_info_disp.get_width(), 
                       GC.WINHEIGHT - GC.TILEHEIGHT//4 - self.obj_info_disp.get_height())
                surf.blit(self.obj_info_disp, pos) # Should be bottom right
            else:
                # Place in topright
                if not self.obj_top:
                    self.obj_top = True
                    self.obj_info_offset = self.obj_info_disp.get_width()
                surf.blit(self.obj_info_disp, (GC.WINWIDTH - GC.TILEWIDTH//4 + self.obj_info_offset - self.obj_info_disp.get_width(), 1))

    def take_input(self, eventList, gameStateObj):
        if not self.fake:
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
                self.image = Engine.subsurface(self.formationsprite, (GC.CURSORSPRITECOUNTER.count//2*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
        elif self.drawState == 2 and gameStateObj.stateMachine.getState() != 'dialogue': # Red if it is selecting...
            self.image = Engine.subsurface(self.redsprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
        elif self.drawState == 3: # Green for turnwheel
            self.image = Engine.subsurface(self.greensprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))
        elif self.currentHoveredUnit and self.currentHoveredUnit.team == 'player' and \
                not self.currentHoveredUnit.isDone() and gameStateObj.stateMachine.getState() != 'dialogue':
            self.image = self.activesprite
        else:
            self.image = Engine.subsurface(self.passivesprite, (GC.CURSORSPRITECOUNTER.count*GC.TILEWIDTH*2, 0, GC.TILEWIDTH*2, GC.TILEHEIGHT*2))

# === GENERIC ARROW OBJECT ===================================================
class ArrowObject(object):
    sprite = GC.IMAGESDICT['MovementArrows']

    def __init__(self, index, position):
        rindex, cindex = index
        left = 1 + ((GC.TILEWIDTH + 2)*cindex) + cindex//2
        top = 1 + ((GC.TILEHEIGHT + 2)*rindex)
        self.image = Engine.subsurface(self.sprite, (left, top, GC.TILEWIDTH, GC.TILEHEIGHT))
        self.position = position

    def draw(self, surf):
        x, y = self.position
        topleft = x * GC.TILEWIDTH, y * GC.TILEHEIGHT
        surf.blit(self.image, topleft)
