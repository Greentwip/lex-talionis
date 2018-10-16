# Turnwheel & Event Log
try:
    import GlobalConstants as GC
    import configuration as cf
    import InputManager, StateMachine, Banner
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import InputManager, StateMachine, Banner

class EventLog(object):
    def __init__(self):
        self.events = []
        self.event_index = -1  # Means no events

    def add(self, event):
        print(event)
        self.events.append(event)
        self.event_index += 1

    def parse_event_backward(self, event, gameStateObj):
        if event[0] == 'Equip':
            unit_id, old_items, new_items = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            # Equip old first item
            old_item = next((i for i in unit.items if id(i) == old_items[0]), None)
            if old_item:
                unit.equip(old_item)
            return "Equipped %s" % unit.items[0].name

    def backward(self, gameStateObj):
        if not self.events or self.event_index < 0:
            return None
        event = self.events[self.event_index]
        message = self.parse_event_backward(event, gameStateObj)
        self.event_index -= 1
        return message

    def parse_event_forward(self, event, gameStateObj):
        if event[0] == 'Equip':
            unit_id, old_items, new_items = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            # Equip new first item
            new_item = next((i for i in unit.items if id(i) == new_items[0]), None)
            if new_item:
                unit.equip(new_item)  # Equip old first item
            return "Equipped %s" % unit.items[0].name

    def forward(self, gameStateObj):
        if not self.events or self.event_index >= len(self.events):
            return None
        self.event_index += 1
        event = self.events[self.event_index]
        message = self.parse_event_forward(event, gameStateObj)
        return message

    def finalize(self):
        # Remove all events after where we turned back to
        self.events = self.events[:self.event_index]

class TurnwheelState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.pennant = Banner.Pennant(cf.WORDS["Turnwheel_desc"])
        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed'])
        self.hidden_menu = gameStateObj.activeMenu
        gameStateObj.activeMenu = None

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions or 'RIGHT' in directions:
            new_message = gameStateObj.event_log.forward(gameStateObj)
            if new_message:
                self.pennant.change_text(new_message)
        elif 'UP' in directions or 'LEFT' in directions:
            new_message = gameStateObj.event_log.backward(gameStateObj)
            if new_message:
                self.pennant.change_text(new_message)

        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.event_log.finalize()
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.back()  # Leave Options Menu

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.pennant:
            self.pennant.draw(mapSurf, gameStateObj)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = self.hidden_menu
