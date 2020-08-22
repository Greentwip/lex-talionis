# Turnwheel & Event Log
import os, math

from . import GlobalConstants as GC
from . import InputManager, StateMachine, BaseMenuSurf, BattleAnimation
from . import Background, Action, Engine, Image_Modification, Weather, Dialogue

import logging
logger = logging.getLogger(__name__)

class ActionLog(object):
    def __init__(self):
        self.actions = []
        self.action_index = -1  # Means no actions
        self.first_free_action = -1
        self.locked = False
        self.record = True  # whether the action log is currently recording
        self.action_depth = 0

        # For playback
        self.current_unit = None
        self.hovered_unit = None
        self.current_move = None
        self.current_move_index = 0
        self.unique_moves = []

    def append(self, action):
        logger.info("Add Action %d: %s", self.action_index + 1, action.__class__.__name__)
        self.actions.append(action)
        self.action_index += 1

    def remove(self, action):
        logger.info("Remove Action %d: %s", self.action_index, action.__class__.__name__)
        self.actions.remove(action)
        self.action_index -= 1

    def run_action_backward(self, gameStateObj):
        action = self.actions[self.action_index]
        action.reverse(gameStateObj)
        self.action_index -= 1
        return action

    def run_action_forward(self, gameStateObj):
        self.action_index += 1
        action = self.actions[self.action_index]
        action.execute(gameStateObj)
        return action

    def at_far_past(self):
        return not self.actions or self.action_index < self.first_free_action + 1

    def at_far_future(self):
        return not self.actions or self.action_index + 1 >= len(self.actions)

    class Move(object):
        def __init__(self, unit, begin, end=None):
            self.unit = unit
            self.begin = begin
            self.end = end

        def __repr__(self):
            return 'Move: %s %s %s' % (self.unit.name, self.begin, self.end)

    def set_up(self):
        def finalize(move):
            if isinstance(move, self.Move) and move.end is None:
                move.end = move.begin
            self.unique_moves.append(move)

        self.unique_moves = []
        current_move = None
        for action_index in range(self.first_free_action, len(self.actions)):
            action = self.actions[action_index]
            if type(action) == Action.Move or type(action) == Action.Teleport:
                if current_move:
                    finalize(current_move)
                current_move = self.Move(action.unit, action_index)
            elif isinstance(action, Action.Wait) or isinstance(action, Action.Die):
                if current_move and action.unit == current_move.unit:
                    current_move.end = action_index
                    finalize(current_move)
                    current_move = None
            # Arriving on the map is just not an action :(
            # elif isinstance(action, Action.ArriveOnMap):
            #     if current_move:
            #         finalize(current_move)
            #         current_move = None
            #     self.unique_moves.append(('Arrive', action_index, action.unit.id))                    
            elif isinstance(action, Action.MarkPhase):
                if current_move:
                    finalize(current_move)
                    current_move = None
                self.unique_moves.append(('Phase', action_index, action.phase_name))
            elif isinstance(action, Action.LockTurnwheel):
                if current_move:
                    finalize(current_move)
                    current_move = None
                self.unique_moves.append(('Lock', action_index, action.lock))

        # Handle extra actions off the right of the action log (like equipping an item)
        if self.unique_moves:
            last_move = self.unique_moves[-1]
            last_action_index = len(self.actions) - 1
            if isinstance(last_move, self.Move):
                if last_move.end < last_action_index:
                    self.unique_moves.append(('Extra', last_move.end + 1, last_action_index))
            elif last_move[1] < last_action_index:
                self.unique_moves.append(('Extra', last_move[1] + 1, last_action_index))

        logger.info('*** Turnwheel Begin! ***')
        logger.info(self.unique_moves)

        self.current_move_index = len(self.unique_moves)

        # Determine starting lock
        self.locked = self.get_last_lock()

        # Get the text message
        for move in reversed(self.unique_moves):
            if isinstance(move, self.Move):
                if move.end:
                    text_list = self.get_unit_turn(move.unit, move.end)
                    return text_list
                return []
            elif move[0] == 'Phase':
                return ["Start of %s Phase" % move[2].capitalize()]
        return []

    def backward(self, gameStateObj):
        if self.current_move_index < 1:
            return None
        # self.fore_current_unit = None
        self.current_move = self.unique_moves[self.current_move_index - 1]
        logger.info("Backward %s %s %s", self.current_move_index, self.current_move, self.action_index)
        self.current_move_index -= 1
        action = None
        if isinstance(self.current_move, self.Move):
            if self.current_unit:
                while self.action_index >= self.current_move.begin:
                    action = self.run_action_backward(gameStateObj)
                gameStateObj.cursor.centerPosition(self.current_unit.position, gameStateObj) 
                self.current_unit = None
                return []
            else:
                if self.hovered_unit:
                    self.hover_off(gameStateObj)      
                self.current_unit = self.current_move.unit
                if self.current_move.end:
                    while self.action_index > self.current_move.end:
                        action = self.run_action_backward(gameStateObj)
                    prev_action = None
                    if self.action_index >= 1:
                        prev_action = self.actions[self.action_index]
                        logger.info("Prev action %s", prev_action)
                    if self.current_unit.position:
                        gameStateObj.cursor.centerPosition(self.current_unit.position, gameStateObj)
                    elif isinstance(prev_action, Action.Die):
                        gameStateObj.cursor.centerPosition(prev_action.old_pos, gameStateObj)
                    self.hover_on(self.current_unit, gameStateObj)
                    text_list = self.get_unit_turn(self.current_unit, self.action_index)
                    self.current_move_index += 1  # Make sure we don't skip first half of this
                    logger.info("In Backward %s %s %s %s", text_list, self.current_unit.name, self.current_unit.position, prev_action)
                    return text_list
                else:
                    while self.action_index >= self.current_move.begin:
                        action = self.run_action_backward(gameStateObj)
                    gameStateObj.cursor.centerPosition(self.current_unit.position, gameStateObj)                    
                    self.hover_on(self.current_unit, gameStateObj)
                    return []
        elif self.current_move[0] == 'Phase':
            while self.action_index > self.current_move[1]:
                action = self.run_action_backward(gameStateObj)
            if self.hovered_unit:
                self.hover_off(gameStateObj)
            if self.current_move[2] == 'player':
                gameStateObj.cursor.autocursor(gameStateObj)
            return ["Start of %s Phase" % self.current_move[2].capitalize()]
        elif self.current_move[0] == 'Arrive':
            while self.action_index >= self.current_move[1]:
                action = self.run_action_backward(gameStateObj)
            if self.hovered_unit:
                self.hover_off(gameStateObj)
            next_move = self.unique_moves[self.current_move_index - 1]
            if isinstance(next_move, tuple) and next_move[0] == 'Arrive':
                return self.backward(gameStateObj)
            else:
                return []
        elif self.current_move[0] == 'Lock':
            while self.action_index >= self.current_move[1]:
                action = self.run_action_backward(gameStateObj)
            self.locked = self.get_last_lock()
            return self.backward(gameStateObj)  # Go again
        elif self.current_move[0] == 'Extra':
            while self.action_index >= self.current_move[1]:
                action = self.run_action_backward(gameStateObj)
            return self.backward(gameStateObj)  # Go again

    def forward(self, gameStateObj):
        if self.current_move_index >= len(self.unique_moves):
            return None
        # self.back_current_unit = None
        self.current_move = self.unique_moves[self.current_move_index]
        logger.info("Forward %s %s %s", self.current_move_index, self.current_move, self.action_index)
        self.current_move_index += 1
        action = None
        if isinstance(self.current_move, self.Move):
            if self.current_unit:
                while self.action_index < self.current_move.end:
                    action = self.run_action_forward(gameStateObj)
                if self.current_unit.position:
                    gameStateObj.cursor.centerPosition(self.current_unit.position, gameStateObj)
                elif isinstance(action, Action.Die):
                    gameStateObj.cursor.centerPosition(action.old_pos, gameStateObj)
                text_list = self.get_unit_turn(self.current_unit, self.action_index)
                logger.info("In Forward %s %s %s", text_list, self.current_unit.name, action)
                self.current_unit = None
                # Extra Moves
                if self.current_move_index < len(self.unique_moves):
                    next_move = self.unique_moves[self.current_move_index]
                    if isinstance(next_move, tuple) and next_move[0] == 'Extra':
                        self.forward(gameStateObj)  # Skip through the extra move
                return text_list
            else:
                if self.hovered_unit:
                    self.hover_off(gameStateObj)
                self.current_unit = self.current_move.unit
                while self.action_index < self.current_move.begin - 1:
                    # Does next action, so -1 is necessary
                    action = self.run_action_forward(gameStateObj)
                gameStateObj.cursor.centerPosition(self.current_unit.position, gameStateObj)
                self.hover_on(self.current_unit, gameStateObj)
                self.current_move_index -= 1  # Make sure we don't skip second half of this
                return []
        elif self.current_move[0] == 'Phase':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward(gameStateObj)
            if self.hovered_unit:
                self.hover_off(gameStateObj)
            if self.current_move[2] == 'player':
                gameStateObj.cursor.autocursor(gameStateObj)
            return ["Start of %s Phase" % self.current_move[2].capitalize()]
        elif self.current_move[0] == 'Arrive':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward(gameStateObj)
            if self.hovered_unit:
                self.hover_off(gameStateObj)                    
            if self.current_move_index < len(self.unique_moves):
                next_move = self.unique_moves[self.current_move_index]
            else:
                next_move = None
            if isinstance(next_move, tuple) and next_move[0] == 'Arrive':
                return self.forward(gameStateObj)
            else:
                return []
        elif self.current_move[0] == 'Lock':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward(gameStateObj)
            self.locked = self.current_move[2]
            return self.forward(gameStateObj)  # Go again
        elif self.current_move[0] == 'Extra':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward(gameStateObj)
            return []

    def finalize(self):
        # Remove all actions after where we turned back to
        self.current_unit = None
        if self.hovered_unit:
            self.hovered_unit.sprite.turnwheel_indicator = False
        self.actions = self.actions[:self.action_index + 1]

    def reset(self, gameStateObj):
        self.current_unit = None
        if self.hovered_unit:
            self.hovered_unit.sprite.turnwheel_indicator = False
        while not self.at_far_future():
            self.run_action_forward(gameStateObj)

    def get_last_lock(self):
        cur_index = self.action_index
        while cur_index > self.first_free_action:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.LockTurnwheel):
                return cur_action.lock
        return False

    def get_current_phase(self):
        cur_index = self.action_index
        while cur_index > 0:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.MarkPhase):
                return cur_action.phase_name
        return 'player'

    def is_turned_back(self):
        return self.action_index + 1 < len(self.actions)

    def can_use(self, gameStateObj):
        player_units = [unit for unit in gameStateObj.allunits if unit.team == "player" and unit.position and not unit.dead]
        unused_units = [unit for unit in player_units if not unit.isDone()]
        # Make sure that there is at least one unit that can still move.
        return self.is_turned_back() and not self.locked and len(unused_units) >= 1

    def get_unit_turn(self, unit, wait_index):
        cur_index = wait_index
        text = []
        while cur_index > self.first_free_action:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.Message):
                text.insert(0, cur_action.message)
            elif isinstance(cur_action, Action.Move):
                return text

    def replay_map_commands(self, gameStateObj):
        for action in self.actions:
            if action.run_on_load:
                action.execute(gameStateObj)

    def get_previous_position(self, unit):
        for action in reversed(self.actions):
            if isinstance(action, Action.Move):
                if action.unit == unit:
                    return action.old_pos
        return unit.position

    def set_first_free_action(self):
        if self.first_free_action == -1:
            logger.info("*** First Free Action ***")
            self.first_free_action = self.action_index

    def reset_first_free_action(self):
        logger.info("*** First Free Action ***")
        self.first_free_action = self.action_index

    def hover_on(self, unit, gameStateObj):
        unit.sprite.turnwheel_indicator = True
        gameStateObj.cursor.drawState = 3
        self.hovered_unit = unit

    def hover_off(self, gameStateObj):
        self.hovered_unit.sprite.turnwheel_indicator = False
        gameStateObj.cursor.drawState = 0
        self.hovered_unit = None

    def serialize(self, gameStateObj):
        return ([action.serialize(gameStateObj) for action in self.actions], self.first_free_action)

    @classmethod
    def deserialize(cls, serial, gameStateObj):
        self = cls()
        actions, first_free_action = serial
        for name, action in actions:
            self.append(getattr(Action, name).deserialize(action, gameStateObj))
        self.first_free_action = first_free_action
        return self

class TurnwheelDisplay(object):
    def __init__(self, desc, turn):
        self.desc = desc
        self.turn = turn
        self.state = "in"
        self.transition = -24

    def change_text(self, desc, turn):
        self.desc = desc
        self.turn = turn

    def fade_out(self):
        self.state = "out"

    def draw(self, surf, gameStateObj):
        if self.state == "in":
            self.transition += 2
            if self.transition >= 0:
                self.transition = 0
                self.state = "normal"
        elif self.state == "out":
            self.transition -= 2

        if gameStateObj.action_log.locked:
            surf.blit(GC.IMAGESDICT['FocusFadeRed'], (0, 0))
        else:
            surf.blit(GC.IMAGESDICT['FocusFadeGreen'], (0, 0))

        # Turnwheel message
        if self.desc:
            num_lines = len(self.desc)
            bg = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH, 8 + 16*num_lines), 'ClearMenuBackground')
            for idx, line in enumerate(self.desc):
                GC.FONT['text_white'].blit(line, bg, (4, 4 + 16*idx))
            if self.transition != 0:
                bg = Image_Modification.flickerImageTranslucent(bg, -self.transition/24.*100.)
            surf.blit(bg, (0, 0))
        # Turncount
        golden_words_surf = GC.IMAGESDICT['GoldenWords']
        # Get Turn
        turn_surf = Engine.subsurface(golden_words_surf, (0, 17, 26, 10))
        turn_bg = BaseMenuSurf.CreateBaseMenuSurf((48, 24), 'TransMenuBackground')
        turn_bg.blit(turn_surf, (4, 6))
        turn_str = str(self.turn)
        turn_size = GC.FONT['text_blue'].size(turn_str)[0]
        GC.FONT['text_blue'].blit(turn_str, turn_bg, (48 - 4 - turn_size, 3))
        surf.blit(turn_bg, (GC.WINWIDTH - 48 - 4, 4 + self.transition))
        # Unit Count
        count_bg = BaseMenuSurf.CreateBaseMenuSurf((48, 24), 'TransMenuBackground')
        player_units = [unit for unit in gameStateObj.allunits if unit.team == "player" and unit.position and not unit.dead]
        unused_units = [unit for unit in player_units if not unit.isDone()]
        count_str = str(len(unused_units)) + "/" + str(len(player_units))
        count_size = GC.FONT['text_blue'].size(count_str)[0]
        GC.FONT['text_blue'].blit(count_str, count_bg, (24 - count_size/2, 3))
        surf.blit(count_bg, (4, GC.WINHEIGHT - 24 - 4 - self.transition))
        # Num Uses
        if gameStateObj.game_constants.get('max_turnwheel_uses', -1) > 0:
            uses_bg = BaseMenuSurf.CreateBaseMenuSurf((48, 24), 'TransMenuBackground')
            uses_text = str(gameStateObj.game_constants['current_turnwheel_uses']) + ' Left'
            x = 48 - GC.FONT['text_blue'].size(uses_text)[0] - 8
            GC.FONT['text_blue'].blit(uses_text, uses_bg, (x, 4))
            surf.blit(uses_bg, (GC.WINWIDTH - 48 - 4, GC.WINHEIGHT - 24 - 4 - self.transition))

class TurnwheelState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        # Kill off any units who are currently dying
        for unit in gameStateObj.allunits:
            if unit.isDying:
                unit.die(gameStateObj, event=False)
        gameStateObj.action_log.record = False
        GC.SOUNDDICT['TurnwheelIn2'].play()
        # Lower volume
        self.current_volume = Engine.music_thread.volume
        Engine.music_thread.set_volume(self.current_volume/2)

        gameStateObj.background = Background.StaticBackground(GC.IMAGESDICT['FocusFade'], fade=True)
        # turnwheel_desc = gameStateObj.action_log.get_last_unit_turn(gameStateObj)
        turnwheel_desc = gameStateObj.action_log.set_up()
        self.display = TurnwheelDisplay(turnwheel_desc, gameStateObj.turncount)
        self.fluid_helper = InputManager.FluidScroll(200)
        gameStateObj.activeMenu = None
        self.transition_out = 0

        # For darken backgrounds and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.end_effect = None
        self.particles = []

        self.last_direction = 'FORWARD'

    def take_input(self, actionList, gameStateObj, metaDataObj):
        action = gameStateObj.input_manager.process_input(actionList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if self.transition_out > 0:  # Don't take input after a choice has been made
            return

        if 'DOWN' in directions or 'RIGHT' in directions:
            GC.SOUNDDICT['Select 1'].play()
            old_message = None
            if self.last_direction == 'BACKWARD':
                gameStateObj.action_log.current_unit = None
                old_message = gameStateObj.action_log.forward(gameStateObj)
            new_message = gameStateObj.action_log.forward(gameStateObj)
            if new_message is None:
                new_message = old_message
            if new_message is not None:
                self.display.change_text(new_message, gameStateObj.turncount)
            self.last_direction = 'FORWARD'
        elif 'UP' in directions or 'LEFT' in directions:
            GC.SOUNDDICT['Select 2'].play()
            self.go_backwards(gameStateObj)

        if action == 'SELECT':
            if gameStateObj.action_log.can_use(gameStateObj):
                GC.SOUNDDICT['TurnwheelOut'].play()
                # Play Big Turnwheel WOOSH Animation
                gameStateObj.action_log.finalize()
                self.transition_out = 60
                self.display.fade_out()
                self.turnwheel_effect()
                gameStateObj.background.fade_out()
                gameStateObj.game_constants['current_turnwheel_uses'] -= 1
            elif self.name != 'force_turnwheel' and not gameStateObj.action_log.locked:
                self.back_out(gameStateObj)
            else:
                GC.SOUNDDICT['Error'].play()

        elif action == 'BACK':
            if self.name != 'force_turnwheel':
                self.back_out(gameStateObj)
            else:
                GC.SOUNDDICT['Error'].play()

    def go_backwards(self, gameStateObj):
        old_message = None
        if self.last_direction == 'FORWARD':
            gameStateObj.action_log.current_unit = None
            old_message = gameStateObj.action_log.backward(gameStateObj)
        new_message = gameStateObj.action_log.backward(gameStateObj)
        if new_message is None:
            new_message = old_message
        if new_message is not None:
            self.display.change_text(new_message, gameStateObj.turncount)
        self.last_direction = 'BACKWARD'

    def back_out(self, gameStateObj):
        GC.SOUNDDICT['Select 4'].play()
        gameStateObj.action_log.reset(gameStateObj)
        self.transition_out = 24
        self.display.fade_out()
        gameStateObj.background.fade_out()

    def turnwheel_effect(self):
        image, script = GC.ANIMDICT.get_effect('TurnwheelFlash', None)
        if image and script:
            self.end_effect = BattleAnimation.BattleAnimation(None, image, script, None, None)
            self.end_effect.awake(self, None, True, False)
            self.end_effect.start_anim('Attack')
        self.initiate_warp_flowers()

    def initiate_warp_flowers(self):
        self.particles = []
        angle_frac = math.pi/8
        true_pos = GC.WINWIDTH//2, GC.WINHEIGHT//2
        for speed in (0.5, 1.0, 2.0, 2.5, 3.5, 4.0):
            for num in range(0, 16):
                angle = num*angle_frac + angle_frac/2
                self.particles.append(Weather.WarpFlower(true_pos, speed, angle))

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)

        if self.transition_out > 0:
            self.transition_out -= 1
            if self.transition_out <= 0:
                # Let's leave now 
                # gameStateObj.stateMachine.back()
                # gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('free')
                # Called whenever the turnwheel is used
                turnwheel_script_name = 'Data/turnwheelScript.txt'
                if self.end_effect and os.path.exists(turnwheel_script_name):
                    turnwheel_script = Dialogue.Dialogue_Scene(turnwheel_script_name)
                    gameStateObj.message.append(turnwheel_script)
                    gameStateObj.stateMachine.changeState('dialogue')

        if self.end_effect:
            self.end_effect.update()
        for particle in self.particles:
            particle.update(gameStateObj)

    def darken(self):
        self.target_dark += 4

    def lighten(self):
        self.target_dark -= 4

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.display:
            self.display.draw(surf, gameStateObj)
        if self.darken_background or self.target_dark:
            bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - int(self.darken_background * 12.5))
            surf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 1
            elif self.target_dark < self.darken_background:
                self.darken_background -= 1
        for particle in self.particles:
            particle.draw(surf)
        if self.end_effect:
            self.end_effect.draw(surf, (0, 0), 0, 0)
        return surf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.boundary_manager.reset(gameStateObj)
        Engine.music_thread.set_volume(self.current_volume)
        self.display = None
        gameStateObj.action_log.record = True
