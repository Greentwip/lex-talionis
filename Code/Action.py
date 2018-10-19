# Actions
# All permanent changes to game state are reified as actions.

try:
    import GlobalConstants as GC
    import configuration as cf
    import StatusObject, Banner
    import Utility
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import StatusObject, Banner
    from . import Utility

class Action(object):
    def __init__(self):
        pass

    # When used normally
    def do(self, gameStateObj):
        pass

    # When put in forward motion by the turnwheel
    def execute(self, gameStateObj):
        self.do(gameStateObj)

    # When put in reverse motion by the turnwheel
    def reverse(self, gameStateObj):
        pass

    def update(self, gameStateObj):
        pass

class Move(Action):
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

    def do(self, gameStateObj, path=None):
        gameStateObj.moving_units.add(self.unit)
        self.unit.lock_active()
        self.unit.sprite.change_state('moving', gameStateObj)
        # Remove tile statuses
        self.unit.leave(gameStateObj)
        if path is None:
            self.unit.path = gameStateObj.cursor.movePath
        else:
            self.unit.path = path
        self.unit.play_movement_sound(gameStateObj)

    def execute(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.old_pos
        self.unit.arrive(gameStateObj)

class Rescue(Action):
    def __init__(self, unit, rescuee):
        self.unit = unit
        self.rescuee = rescuee
        self.old_pos = self.rescuee.position

    def do(self, gameStateObj):
        self.unit.TRV = self.rescuee.id
        self.unit.strTRV = self.rescuee.name
        if Utility.calculate_distance(self.unit.position, self.rescuee.position) == 1:
            self.rescuee.sprite.set_transition('rescue')
            self.rescuee.sprite.spriteOffset = [(self.unit.position[0] - self.old_pos[0]), 
                                                (self.unit.position[1] - self.old_pos[1])]
        else:
            self.rescuee.leave(gameStateObj)
            self.rescuee.position = None
        self.unit.hasAttacked = True
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)

    def execute(self, gameStateObj):
        self.unit.TRV = self.rescuee.id
        self.unit.strTRV = self.rescuee.name
        self.rescuee.leave(gameStateObj)
        self.rescuee.position = None
        self.unit.hasAttacked = True
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)

    def reverse(self, gameStateObj):
        self.rescuee.position = self.old_pos
        self.rescuee.arrive(gameStateObj)
        self.unit.hasAttacked = False
        self.unit.unrescue(gameStateObj)

class Drop(Action):
    def __init__(self, unit, droppee, pos):
        self.unit = unit
        self.droppee = droppee
        self.pos = pos

    def do(self, gameStateObj):
        self.droppee.position = self.pos
        self.droppee.arrive(gameStateObj)
        self.droppee.wait(gameStateObj, script=False)
        self.droppee.hasAttacked = True
        self.unit.hasTraded = True  # Can no longer do everything
        if Utility.calculate_distance(self.unit.position, self.pos) == 1:
            self.droppee.sprite.set_transition('fake_in')
            self.droppee.sprite.spriteOffset = [(self.unit.position[0] - self.pos[0])*GC.TILEWIDTH,
                                                (self.unit.position[1] - self.pos[1])*GC.TILEHEIGHT]
        self.unit.unrescue(gameStateObj)

    def execute(self, gameStateObj):
        self.droppee.position = self.pos
        self.droppee.arrive(gameStateObj)
        self.droppee.wait(gameStateObj, script=False)
        self.droppee.hasAttacked = True
        self.unit.hasTraded = True  # Can no longer do everything
        self.unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.TRV = self.droppee.id
        self.unit.strTRV = self.droppee.name
        self.unit.hasTraded = False
        self.droppee.position = None
        self.droppee.leave(gameStateObj)
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)

class Give(Action):
    def __init__(self, unit, other_unit):
        self.unit = unit
        self.other_unit = other_unit

    def do(self, gameStateObj):
        self.other_unit.TRV = self.unit.TRV
        self.other_unit.strTRV = self.unit.strTRV
        self.unit.hasAttacked = True
        if 'savior' not in self.other_unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.other_unit, gameStateObj)
        self.unit.unrescue()

    def reverse(self, gameStateObj):
        self.unit.TRV = self.other_unit.TRV
        self.unit.strTRV = self.other_unit.strTRV
        self.unit.hasAttacked = False
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)
        self.other_unit.unrescue()

class Take(Action):
    def __init__(self, unit, other_unit):
        self.unit = unit
        self.other_unit = other_unit

    def do(self, gameStateObj):
        self.unit.TRV = self.other_unit.TRV
        self.unit.strTRV = self.other_unit.strTRV
        self.unit.hasTraded = True
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)
        self.other_unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.other_unit.TRV = self.unit.TRV
        self.other_unit.strTRV = self.unit.strTRV
        self.unit.hasTraded = False
        if 'savior' not in self.other_unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.other_unit, gameStateObj)
        self.unit.unrescue()

class ChangeTeam(Action):
    def __init__(self, unit, new_team):
        self.unit = unit
        self.new_team = new_team
        self.old_team = self.unit.team

    def _change_team(self, team, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.team = team
        gameStateObj.boundary_manager.reset_unit(self.unit)
        self.unit.reset_sprite()
        self.unit.loadSprites()
        self.unit.reset()
        self.unit.arrive(gameStateObj)

    def do(self, gameStateObj):
        self._change_team(self.new_team, gameStateObj)
        
    def reverse(self, gameStateObj):
        self._change_team(self.old_team, gameStateObj)

class ChangeClass(Action):
    def __init__(self, unit, new_klass):
        self.unit = unit
        self.new_klass = new_klass
        self.old_klass = self.unit.klass

    def _change_class(self, klass, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.klass = klass
        self.unit.reset_sprite()
        self.unit.loadSprites()
        self.unit.arrive(gameStateObj)

    def do(self, gameStateObj):
        self._change_class(self.new_klass, gameStateObj)

    def reverse(self, gameStateObj):
        self._change_class(self.old_klass, gameStateObj)

class GiveGold(Action):
    def __init__(self, amount):
        self.amount = amount

    def do(self, gameStateObj):
        gameStateObj.game_constants['money'] += self.amount
        gameStateObj.banners.append(Banner.acquiredGoldBanner(self.amount))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        gameStateObj.game_constants['money'] += self.amount

    def reverse(self, gameStateObj):
        gameStateObj.game_constants['money'] -= self.amount

class ItemConvoy(Action):
    def __init__(self, item):
        self.item = item

    def do(self, gameStateObj):
        gameStateObj.convoy.append(self.item)
        gameStateObj.banners.append(Banner.sent_to_convoyBanner(self.item))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        gameStateObj.convoy.remove(self.item)

class GiveItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.convoy = False

    def do(self, gameStateObj):
        if len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item)
            gameStateObj.banners.append(Banner.acquiredItemBanner(self.unit, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        elif self.unit.team == 'player':
            self.convoy = True
            gameStateObj.convoy.append(self.item)
            gameStateObj.banners.append(Banner.sent_to_convoyBanner(self.item))
            gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        if len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item)
        elif self.unit.team == 'player':
            self.convoy = True
            gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        if self.convoy:
            self.convoy.remove(self.item)
        else:
            self.unit.remove_item(self.item)

class DiscardItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.item_index = self.unit.items.index(self.item)

    def do(self, gameStateObj):
        self.unit.remove_item(self.item)
        gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        gameStateObj.convoy.remove(self.item)
        self.unit.insert_item(self.item_index, self.item)
