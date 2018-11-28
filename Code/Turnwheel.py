# Turnwheel & Event Log
try:
    import GlobalConstants as GC
    import InputManager, StateMachine, MenuFunctions
    import Background, Action, Engine, Image_Modification
except ImportError:
    from . import GlobalConstants as GC
    from . import InputManager, StateMachine, MenuFunctions
    from . import Background, Action, Engine, Image_Modification

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
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
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
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
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
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
                return []
            # Actually run
            action = self.run_action_forward(gameStateObj)
            # Wait
            if isinstance(action, Action.Wait):
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
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
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
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
            bg = MenuFunctions.CreateBaseMenuSurf((240, 4 + 16*num_lines), 'ClearMenuBackground')
            for idx, line in enumerate(self.desc):
                GC.FONT['text_white'].blit(line, bg, (0, 2 + 16*idx))
            if self.transition != 0:
                bg = Image_Modification.flickerImageTranslucent(bg, -self.transition/24.*100.)
            surf.blit(bg, (0, 0))
        # Turncount
        golden_words_surf = GC.IMAGESDICT['GoldenWords']
        # Get Turn
        turn_surf = Engine.subsurface(golden_words_surf, (0, 17, 26, 10))
        turn_bg = MenuFunctions.CreateBaseMenuSurf((48, 24))
        turn_bg.blit(turn_surf, (4, 4))
        GC.FONT['text_blue'].blit(str(self.turn), turn_bg, (24, 4))
        surf.blit(turn_bg, (GC.WINWIDTH - 48, 4 + self.transition))
        # Unit Count
        count_bg = MenuFunctions.CreateBaseMenuSurf((48, 24))
        player_units = [unit for unit in gameStateObj.allunits if unit.team == "player" and unit.position and not unit.dead]
        unused_units = [unit for unit in player_units if not unit.finished]
        GC.FONT['text_blue'].blit(str(len(unused_units)) + "/" + str(len(player_units)), count_bg, (4, 4))
        surf.blit(count_bg, (4, GC.WINHEIGHT - 24 - 4 - self.transition))
        # Num Uses
        if gameStateObj.game_constants.get('current_turnwheel_uses', -1) > 0:
            uses_bg = MenuFunctions.CreateBaseMenuSurf((48, 24))
            GC.FONT['text_blue'].blit(str(gameStateObj.game_constants['current_turnwheel_uses']), (4, 4))
            surf.blit(uses_bg, GC.WINWIDTH - 48, GC.WINHEIGHT - 24 - 4 - self.transition)

class TurnwheelState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        # Lower volume
        self.current_volume = Engine.music_thread.volume
        Engine.music_thread.set_volume(self.current_volume/2)

        gameStateObj.background = Background.StaticBackground(GC.IMAGESDICT['FocusFade'], fade=True)
        turnwheel_desc = gameStateObj.action_log.get_last_unit_turn(gameStateObj)
        self.pennant = TurnwheelDisplay(turnwheel_desc, gameStateObj.turncount)
        self.fluid_helper = InputManager.FluidScroll(200)
        gameStateObj.activeMenu = None

    def take_input(self, actionList, gameStateObj, metaDataObj):
        action = gameStateObj.input_manager.process_input(actionList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions or 'RIGHT' in directions:
            # GC.SOUNDDICT['TurnwheelClick'].play()
            new_message = gameStateObj.action_log.forward(gameStateObj)
            if new_message is not None:
                self.pennant.change_text(new_message, gameStateObj.turncount)
        elif 'UP' in directions or 'LEFT' in directions:
            # GC.SOUNDDICT['TurnwheelClick'].play()
            new_message = gameStateObj.action_log.backward(gameStateObj)
            if new_message is not None:
                self.pennant.change_text(new_message, gameStateObj.turncount)

        if action == 'SELECT' or action == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.action_log.finalize()
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.back()  # Leave Options Menu

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.pennant:
            self.pennant.draw(mapSurf, gameStateObj)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        Engine.music_thread.set_volume(self.current_volume)
        self.pennant = None
