# Turnwheel & Event Log
import os, math
try:
    import GlobalConstants as GC
    import InputManager, StateMachine, MenuFunctions, BattleAnimation
    import Background, Action, Engine, Image_Modification, Weather, Dialogue
except ImportError:
    from . import GlobalConstants as GC
    from . import InputManager, StateMachine, MenuFunctions, BattleAnimation
    from . import Background, Action, Engine, Image_Modification, Weather, Dialogue

class ActionLog(object):
    def __init__(self):
        self.actions = []
        self.action_index = -1  # Means no actions
        self.first_free_action = -1

    def append(self, action):
        print("Add Action: %s" % action.__class__.__name__)
        self.actions.append(action)
        self.action_index += 1

    def remove(self, action):
        print("Remove Action: %s" % action.__class__.__name__)
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

    def backward(self, gameStateObj):
        if not self.actions or self.action_index < self.first_free_action + 1:
            return None

        # Get where we should stop next
        starting_index = self.action_index
        while self.action_index >= self.first_free_action + 1:
            action = self.actions[self.action_index]
            # Wait
            if isinstance(action, Action.Wait) and self.action_index != starting_index:
                gameStateObj.cursor.centerPosition(action.unit.position, gameStateObj)
                # Get content of unit's turn
                text_list = self.get_unit_turn(action.unit, self.action_index)
                return text_list
            # Mark PHase
            elif isinstance(action, Action.MarkPhase) and self.action_index != starting_index:
                if action.phase_name == 'player':
                    gameStateObj.cursor.autocursor(gameStateObj)
                return ["Start of %s phase" % action.phase_name.capitalize()]
            # Actually Run backwards
            action = self.run_action_backward(gameStateObj)
            # Move
            if isinstance(action, Action.Move):
                gameStateObj.cursor.centerPosition(action.unit.position, gameStateObj)
                if self.action_index == self.first_free_action:
                    return ["Start of Player Phase"]
                return []
        
        # return action.__class__.__name__ + ": " + str(self.action_index + 1) + ' / ' + str(len(self.actions))
        return None

    def forward(self, gameStateObj):
        if not self.actions or self.action_index + 1 >= len(self.actions):
            return None

        starting_index = self.action_index
        while self.action_index + 1 < len(self.actions):
            action = self.actions[self.action_index + 1]
            # Move
            if isinstance(action, Action.Move) and self.action_index != starting_index:
                gameStateObj.cursor.centerPosition(action.unit.position, gameStateObj)
                return []
            # Actually run
            action = self.run_action_forward(gameStateObj)
            # Wait
            if isinstance(action, Action.Wait):
                gameStateObj.cursor.centerPosition(action.unit.position, gameStateObj)
                # Get content of unit's turn
                text_list = self.get_unit_turn(action.unit, self.action_index)
                return text_list
            # Mark Phase
            elif isinstance(action, Action.MarkPhase):
                if action.phase_name == 'player':
                    gameStateObj.cursor.autocursor(gameStateObj)
                return ["Start of %s Phase" % action.phase_name.capitalize()]

        # return action.__class__.__name__ + ': ' + str(self.action_index + 1) + ' / ' + str(len(self.actions))
        return None

    def finalize(self):
        # Remove all actions after where we turned back to
        self.actions = self.actions[:self.action_index + 1]

    def is_turned_back(self):
        return self.action_index + 1 < len(self.actions)

    def get_unit_turn(self, unit, wait_index):
        cur_index = wait_index
        text = []
        while True:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.Message):
                text.insert(0, cur_action.message)
            elif isinstance(cur_action, Action.Move):
                return text

    def get_last_unit_turn(self, gameStateObj):
        if not self.actions or self.action_index < self.first_free_action + 1:
            return []

        while self.action_index >= self.first_free_action + 1:
            action = self.actions[self.action_index]
            if isinstance(action, Action.Wait):
                gameStateObj.cursor.centerPosition(action.unit.position, gameStateObj)
                text_list = self.get_unit_turn(action.unit, self.action_index)
                return text_list
            self.action_index -= 1

        return []

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
            self.first_free_action = self.action_index

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

        # Turnwheel message
        if self.desc:
            num_lines = len(self.desc)
            bg = MenuFunctions.CreateBaseMenuSurf((GC.WINWIDTH, 8 + 16*num_lines), 'ClearMenuBackground')
            for idx, line in enumerate(self.desc):
                GC.FONT['text_white'].blit(line, bg, (4, 4 + 16*idx))
            if self.transition != 0:
                bg = Image_Modification.flickerImageTranslucent(bg, -self.transition/24.*100.)
            surf.blit(bg, (0, 0))
        # Turncount
        golden_words_surf = GC.IMAGESDICT['GoldenWords']
        # Get Turn
        turn_surf = Engine.subsurface(golden_words_surf, (0, 17, 26, 10))
        turn_bg = MenuFunctions.CreateBaseMenuSurf((48, 24), 'TransMenuBackground')
        turn_bg.blit(turn_surf, (4, 6))
        turn_str = str(self.turn)
        turn_size = GC.FONT['text_blue'].size(turn_str)[0]
        GC.FONT['text_blue'].blit(turn_str, turn_bg, (48 - 4 - turn_size, 3))
        surf.blit(turn_bg, (GC.WINWIDTH - 48 - 4, 4 + self.transition))
        # Unit Count
        count_bg = MenuFunctions.CreateBaseMenuSurf((48, 24), 'TransMenuBackground')
        player_units = [unit for unit in gameStateObj.allunits if unit.team == "player" and unit.position and not unit.dead]
        unused_units = [unit for unit in player_units if not unit.finished]
        count_str = str(len(unused_units)) + "/" + str(len(player_units))
        count_size = GC.FONT['text_blue'].size(count_str)[0]
        GC.FONT['text_blue'].blit(count_str, count_bg, (24 - count_size/2, 3))
        surf.blit(count_bg, (4, GC.WINHEIGHT - 24 - 4 - self.transition))
        # Num Uses
        if gameStateObj.game_constants.get('max_turnwheel_uses', -1) > 0:
            uses_bg = MenuFunctions.CreateBaseMenuSurf((48, 24), 'TransMenuBackground')
            GC.FONT['text_blue'].blit(str(gameStateObj.game_constants['current_turnwheel_uses']), (4, 4))
            surf.blit(uses_bg, GC.WINWIDTH - 48 - 4, GC.WINHEIGHT - 24 - 4 - self.transition)

class TurnwheelState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        GC.SOUNDDICT['TurnwheelIn2'].play()
        # Lower volume
        self.current_volume = Engine.music_thread.volume
        Engine.music_thread.set_volume(self.current_volume/2)

        gameStateObj.background = Background.StaticBackground(GC.IMAGESDICT['FocusFade'], fade=True)
        turnwheel_desc = gameStateObj.action_log.get_last_unit_turn(gameStateObj)
        self.display = TurnwheelDisplay(turnwheel_desc, gameStateObj.turncount)
        self.fluid_helper = InputManager.FluidScroll(200)
        gameStateObj.activeMenu = None
        self.transition_out = 0

        # For darken backgrounds and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.end_effect = None
        self.particles = []

    def take_input(self, actionList, gameStateObj, metaDataObj):
        action = gameStateObj.input_manager.process_input(actionList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions or 'RIGHT' in directions:
            GC.SOUNDDICT['Select 1'].play()
            new_message = gameStateObj.action_log.forward(gameStateObj)
            if new_message is not None:
                self.display.change_text(new_message, gameStateObj.turncount)
        elif 'UP' in directions or 'LEFT' in directions:
            GC.SOUNDDICT['Select 2'].play()
            new_message = gameStateObj.action_log.backward(gameStateObj)
            if new_message is not None:
                self.display.change_text(new_message, gameStateObj.turncount)

        if action == 'SELECT':
            if gameStateObj.action_log.is_turned_back():
                GC.SOUNDDICT['TurnwheelOut'].play()
                # Play Big Turnwheel WOOSH Animation
                gameStateObj.action_log.finalize()
                self.transition_out = 60
                self.display.fade_out()
                self.turnwheel_effect()
                gameStateObj.background.fade_out()
                gameStateObj.game_constants['current_turnwheel_uses'] -= 1
            else:
                GC.SOUNDDICT['Error'].play()

        elif action == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            self.transition_out = 24
            self.display.fade_out()
            gameStateObj.background.fade_out()

    def turnwheel_effect(self):
        image, script = GC.ANIMDICT.get_effect('TurnwheelFlash', None)
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
                gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.back()
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
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.display:
            self.display.draw(mapSurf, gameStateObj)
        if self.darken_background or self.target_dark:
            bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - int(self.darken_background * 12.5))
            mapSurf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 1
            elif self.target_dark < self.darken_background:
                self.darken_background -= 1
        for particle in self.particles:
            particle.draw(mapSurf)
        if self.end_effect:
            self.end_effect.draw(mapSurf, (0, 0), 0, 0)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        Engine.music_thread.set_volume(self.current_volume)
        self.display = None
