# Turnwheel & Event Log
try:
    import GlobalConstants as GC
    import configuration as cf
    import InputManager, StateMachine, Banner, Action
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import InputManager, StateMachine, Banner, Action

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
                text = self.get_unit_turn(action.unit, self.action_index)
                return '  '.join(text)
            # Mark PHase
            elif isinstance(action, Action.MarkPhase) and self.action_index != starting_index:
                if action.phase_name == 'player':
                    gameStateObj.cursor.autocursor(gameStateObj)
                return "Start of %s phase" % action.phase_name.capitalize()
            # Actually Run backwards
            action = self.run_action_backward(gameStateObj)
            # Move
            if isinstance(action, Action.Move):
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
                if self.action_index == self.first_free_action:
                    return "Start of Player Phase"
                return ""
        
        # return action.__class__.__name__ + ": " + str(self.action_index + 1) + ' / ' + str(len(self.actions))
        return ""

    def forward(self, gameStateObj):
        if not self.actions or self.action_index + 1 >= len(self.actions):
            return None

        starting_index = self.action_index
        while self.action_index + 1 < len(self.actions):
            action = self.actions[self.action_index + 1]
            # Move
            if isinstance(action, Action.Move) and self.action_index != starting_index:
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
                return ""
            # Actually run
            action = self.run_action_forward(gameStateObj)
            # Wait
            if isinstance(action, Action.Wait):
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
                # Get content of unit's turn
                text = self.get_unit_turn(action.unit, self.action_index)
                return '  '.join(text)
            # Mark Phase
            elif isinstance(action, Action.MarkPhase):
                if action.phase_name == 'player':
                    gameStateObj.cursor.autocursor(gameStateObj)
                return "Start of %s Phase" % action.phase_name.capitalize()

        # return action.__class__.__name__ + ': ' + str(self.action_index + 1) + ' / ' + str(len(self.actions))
        return ""

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
            return ""

        while self.action_index >= self.first_free_action + 1:
            action = self.actions[self.action_index]
            if isinstance(action, Action.Wait):
                gameStateObj.cursor.setPosition(action.unit.position, gameStateObj)
                text = self.get_unit_turn(action.unit, self.action_index)
                return '  '.join(text)
            self.action_index -= 1

        return ""

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

class TurnwheelState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        turnwheel_desc = gameStateObj.action_log.get_last_unit_turn(gameStateObj)
        self.pennant = Banner.Pennant(turnwheel_desc)
        self.fluid_helper = InputManager.FluidScroll(200)
        gameStateObj.activeMenu = None

    def take_input(self, actionList, gameStateObj, metaDataObj):
        action = gameStateObj.input_manager.process_input(actionList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions or 'RIGHT' in directions:
            new_message = gameStateObj.action_log.forward(gameStateObj)
            if new_message:
                self.pennant.change_text(new_message)
        elif 'UP' in directions or 'LEFT' in directions:
            new_message = gameStateObj.action_log.backward(gameStateObj)
            if new_message:
                self.pennant.change_text(new_message)

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
