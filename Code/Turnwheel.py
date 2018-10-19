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

class ActionLog(object):
    def __init__(self):
        self.actions = []
        self.action_index = -1  # Means no actions

        self.unborn_units = []
        self.unborn_items = []

        self.removed_units = []
        self.removed_items = []

    def add(self, action):
        print(action)
        self.actions.append(action)
        self.action_index += 1

    def parse_action_backward(self, action, gameStateObj):
        if action[0] == 'Equip':
            unit_id, old_index = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.insert_item(old_index, unit.items[0])
            # Need to rearrange to match old_items
            return "Equipped %s" % unit.items[0].name
        elif action[0] == 'Give Item':
            unit_id, item_u_id = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            item = [item for item in unit.items if id(item) == item_u_id][0]
            unit.remove_item(item)
            # Item is now UNBORN
            self.unborn_items.append(item)
        elif action[0] == 'Remove Item':
            unit_id, item_u_id = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            item = [item for item in self.removed_items if id(item) == item_u_id][0]
            unit.add_item(item)
        elif action[0] == 'Move':
            unit_id, old_pos, new_pos = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.leave(gameStateObj)
            unit.position = old_pos
            unit.arrive(gameStateObj)
            return "Moved to %s" % old_pos
        elif action[0] == 'Rescue':
            unit_id, rescue_id, old_pos = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.drop(old_pos, gameStateObj)
            return "Dropped %s" % rescue_id
        elif action[0] == 'Drop':
            unit_id, drop_id, new_pos = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            droppee = gameStateObj.get_unit_from_id(drop_id)
            unit.rescue(droppee, gameStateObj)
            return "Rescued %s" % droppee.name
        elif action[0] == 'Exp Gain':
            unit_id, exp, stats, rng = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            static_random.set_growth_rng(unit_id, rng)
            unit.set_stats(stats)
            if exp > unit.exp:
                unit.exp += 100 - exp
            else:
                unit.exp -= exp

    def backward(self, gameStateObj):
        if not self.actions or self.action_index < 0:
            return None
        action = self.actions[self.action_index]
        message = self.parse_action_backward(action, gameStateObj)
        self.action_index -= 1
        return message

    def parse_action_forward(self, action, gameStateObj):
        if action[0] == 'Equip':
            unit_id, old_index = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.equip(unit.items[old_index])
            # Need to rearrange to match new_items
            return "Equipped %s" % unit.items[0].name
        elif action[0] == 'Give Item':
            unit_id, item_u_id = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            item = [item for item in self.unborn_items if id(item) == item_u_id][0]
            unit.add_item(item)
        elif action[0] == 'Remove Item':
            unit_id, item_u_id = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.remove_item(item)
            self.removed_items.append(item)
        elif action[0] == 'Trade Item':
            pass
        elif action[0] == 'Use Item':
            pass
        elif action[0] == 'Move':
            unit_id, old_pos, new_pos = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.leave(gameStateObj)
            unit.position = new_pos
            unit.arrive(gameStateObj)
            return "Moved to %s" % old_pos
        elif action[0] == 'Rescue':
            unit_id, rescue_id, old_pos = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            rescuee = gameStateObj.get_unit_from_id(rescue_id)
            unit.rescue(rescuee, gameStateObj)
            return "Rescued %s" % rescuee.name
        elif action[0] == 'Drop':
            unit_id, drop_id, new_pos = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            unit.drop(new_pos, gameStateObj)
            return "Dropped %s" % drop_id
        elif action[0] == 'Give':
            pass
        elif action[0] == 'Take':
            pass
        elif action[0] == 'Exp Gain':
            unit_id, exp, stats, rng = action[1:]
            unit = gameStateObj.get_unit_from_id(unit_id)
            gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=unit, exp=exp))
            gameStateObj.stateMachine.changeState('expgain')
        elif action[0] == 'Class Change':
            pass
        elif action[0] == 'Team Change':
            pass
        elif action[0] == 'AI Change':
            pass
        elif action[0] == 'Die':
            pass
        elif action[0] == 'Resurrect':
            pass
        elif action[0] == 'Attack':
            pass
        elif action[0] == 'Damage':
            pass
        elif action[0] == 'Heal':
            pass
        elif action[0] == 'Add Status':
            pass
        elif action[0] == 'Remove Status':
            pass
        elif action[0] == 'Leave':
            pass
        elif action[0] == 'Arrive':
            pass
        elif action[0] == 'Tile Sprite Change':
            pass
        elif action[0] == 'Tile Terrain Change':
            pass
        elif action[0] == 'Change RNG':
            pass

    def forward(self, gameStateObj):
        if not self.actions or self.action_index >= len(self.actions):
            return None
        self.action_index += 1
        action = self.actions[self.action_index]
        message = self.parse_action_forward(action, gameStateObj)
        return message

    def finalize(self):
        # Remove all actions after where we turned back to
        self.actions = self.actions[:self.action_index]
        # Remove all unborn objects
        self.unborn_units = []
        self.unborn_items = []

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
