# Turnwheel & Event Log
try:
    import GlobalConstants as GC
    import configuration as cf
    import static_random
    import InputManager, StateMachine, Banner
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import static_random
    from . import InputManager, StateMachine, Banner

class EventLog(object):
    def __init__(self):
        self.events = []
        self.event_index = -1  # Means no events

        self.unborn_units = []
        self.unborn_items = []

        self.removed_units = []
        self.removed_items = []

    def add(self, event):
        print(event)
        self.events.append(event)
        self.event_index += 1

    def parse_event_backward(self, event, gameStateObj):
        if event[0] == 'Equip':
            unit_id, old_index = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.insert_item(old_index, unit.items[0])
            # Need to rearrange to match old_items
            return "Equipped %s" % unit.items[0].name
        elif event[0] == 'Give Item':
            unit_id, item_u_id = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            item = [item for item in unit.items if id(item) == item_u_id][0]
            unit.remove_item(item)
            # Item is now UNBORN
            self.unborn_items.append(item)
        elif event[0] == 'Remove Item':
            unit_id, item_u_id = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            item = [item for item in self.removed_items if id(item) == item_u_id][0]
            unit.add_item(item)
        elif event[0] == 'Move':
            unit_id, old_pos, new_pos = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.leave(gameStateObj)
            unit.position = old_pos
            unit.arrive(gameStateObj)
            return "Moved to %s" % old_pos
        elif event[0] == 'Rescue':
            unit_id, rescue_id, old_pos = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.drop(old_pos, gameStateObj)
            return "Dropped %s" % rescue_id
        elif event[0] == 'Drop':
            unit_id, drop_id, new_pos = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            droppee = gameStateObj.get_unit_from_id(drop_id)
            unit.rescue(droppee, gameStateObj)
            return "Rescued %s" % droppee.name
        elif event[0] == 'Exp Gain':
            unit_id, exp, stats, rng = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            static_random.set_growth_rng(unit_id, rng)
            unit.set_stats(stats)
            if exp > unit.exp:
                unit.exp += 100 - exp
            else:
                unit.exp -= exp

    def backward(self, gameStateObj):
        if not self.events or self.event_index < 0:
            return None
        event = self.events[self.event_index]
        message = self.parse_event_backward(event, gameStateObj)
        self.event_index -= 1
        return message

    def parse_event_forward(self, event, gameStateObj):
        if event[0] == 'Equip':
            unit_id, old_index = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.equip(unit.items[old_index])
            # Need to rearrange to match new_items
            return "Equipped %s" % unit.items[0].name
        elif event[0] == 'Give Item':
            unit_id, item_u_id = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            item = [item for item in self.unborn_items if id(item) == item_u_id][0]
            unit.add_item(item)
        elif event[0] == 'Remove Item':
            unit_id, item_u_id = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.remove_item(item)
            self.removed_items.append(item)
        elif event[0] == 'Trade Item':
            pass
        elif event[0] == 'Use Item':
            pass
        elif event[0] == 'Move':
            unit_id, old_pos, new_pos = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.leave(gameStateObj)
            unit.position = new_pos
            unit.arrive(gameStateObj)
            return "Moved to %s" % old_pos
        elif event[0] == 'Rescue':
            unit_id, rescue_id, old_pos = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            rescuee = gameStateObj.get_unit_from_id(rescue_id)
            unit.rescue(rescuee, gameStateObj)
            return "Rescued %s" % rescuee.name
        elif event[0] == 'Drop':
            unit_id, drop_id, new_pos = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.drop(new_pos, gameStateObj)
            return "Dropped %s" % drop_id
        elif event[0] == 'Give':
            pass
        elif event[0] == 'Take':
            pass
        elif event[0] == 'Exp Gain':
            unit_id, exp, stats, rng = event[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=unit, exp=exp))
            gameStateObj.stateMachine.changeState('expgain')
        elif event[0] == 'Class Change':
            pass
        elif event[0] == 'Team Change':
            pass
        elif event[0] == 'AI Change':
            pass
        elif event[0] == 'Die':
            pass
        elif event[0] == 'Resurrect':
            pass
        elif event[0] == 'Attack':
            pass
        elif event[0] == 'Damage':
            pass
        elif event[0] == 'Heal':
            pass
        elif event[0] == 'Add Status':
            pass
        elif event[0] == 'Remove Status':
            pass
        elif event[0] == 'Leave':
            pass
        elif event[0] == 'Arrive':
            pass
        elif event[0] == 'Tile Sprite Change':
            pass
        elif event[0] == 'Tile Terrain Change':
            pass
        elif event[0] == 'Change RNG':
            pass

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
        # Remove all unborn objects
        self.unborn_units = []
        self.unborn_items = []

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
