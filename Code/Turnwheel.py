# Turnwheel & Event Log
try:
    import GlobalConstants as GC
    import configuration as cf
    import InputManager, StateMachine, Banner
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import InputManager, StateMachine, Banner

class ActionLog(object):
    def __init__(self):
        self.actions = []
        self.action_index = -1  # Means no actions

    def append(self, action):
        print(action)
        self.actions.append(action)
        self.action_index += 1

    def run_action_backward(self, action, gameStateObj):
        action.reverse(gameStateObj)

    def run_action_forward(self, action, gameStateObj):
        action.execute(gameStateObj)

    def backward(self, gameStateObj):
        if not self.actions or self.action_index < 0:
            return None
        action = self.actions[self.action_index]
        message = self.run_action_backward(action, gameStateObj)
        self.action_index -= 1
        return message

    def forward(self, gameStateObj):
        if not self.actions or self.action_index >= len(self.actions):
            return None
        self.action_index += 1
        action = self.actions[self.action_index]
        message = self.run_action_forward(action, gameStateObj)
        return message

    def finalize(self):
        # Remove all actions after where we turned back to
        self.actions = self.actions[:self.action_index]

class TurnwheelState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.pennant = Banner.Pennant(cf.WORDS["Turnwheel_desc"])
        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed'])
        self.hidden_menu = gameStateObj.activeMenu
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

        if action == 'BACK':
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
        gameStateObj.activeMenu = self.hidden_menu
