# Actions
# All permanent changes to game state are reified as actions.
import sys

from . import GlobalConstants as GC
from . import configuration as cf
from . import static_random
from . import Utility, Engine
from . import Banner, Weapons, ClassData, Aura
from . import StatusCatalog, ActiveSkill, PrepBase

import logging
logger = logging.getLogger(__name__)

class Action(object):
    run_on_load = False

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

    def serialize_obj(self, value, gameStateObj):
        from . import UnitObject, ItemMethods
        if isinstance(value, UnitObject.UnitObject):
            value = ('Unit', value.id)
        elif isinstance(value, ItemMethods.ItemObject):
            value = ('Item', value.uid)
        elif isinstance(value, StatusCatalog.Status):
            value = ('Status', value.uid)
        elif isinstance(value, list):
            value = ('List', [self.serialize_obj(v, gameStateObj) for v in value])
        elif isinstance(value, Action):  # This only works if two actions never refer to one another
            value = ('Action', value.serialize(gameStateObj))
        elif isinstance(value, PrepBase.ConvoyTrader):
            value = ('ConvoyTrader', None)  # List does not need to be reversible
        else:
            value = ('Generic', value)
        return value

    def serialize(self, gameStateObj):
        ser_dict = {}
        for attr in self.__dict__.items():
            # print(attr)
            name, value = attr
            value = self.serialize_obj(value, gameStateObj)
            ser_dict[name] = value
        # print(ser_dict)
        return (self.__class__.__name__, ser_dict)

    def deserialize_obj(self, value, gameStateObj):
        if value[0] == 'Unit':
            return gameStateObj.get_unit_from_id(value[1])
        elif value[0] == 'Item':
            return gameStateObj.get_item_from_uid(value[1])
        elif value[0] == 'Status':
            return gameStateObj.get_status_from_uid(value[1])
        elif value[0] == 'List':
            return [self.deserialize_obj(v, gameStateObj) for v in value[1]]
        elif value[0] == 'Action':
            name, value = value[1][0], value[1][1]
            action = getattr(sys.modules[__name__], name)
            return action.deserialize(value, gameStateObj)
        else:
            return value[1]

    @classmethod
    def deserialize(cls, ser_dict, gameStateObj):
        self = cls.__new__(cls)
        # print('Deserialize: %s' % cls.__name__)
        for name, value in ser_dict.items():
            setattr(self, name, self.deserialize_obj(value, gameStateObj))
        return self

class Move(Action):
    """
    A basic, user-directed move
    """
    def __init__(self, unit, new_pos, path=None):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

        self.prev_movement_left = self.unit.movement_left
        self.new_movement_left = None

        self.path = path
        self.hasMoved = self.unit.hasMoved

    def do(self, gameStateObj):
        gameStateObj.moving_units.add(self.unit)
        self.unit.sprite.change_state('moving', gameStateObj)
        # Remove tile statuses
        self.unit.leave(gameStateObj)
        if self.path is None:
            self.unit.path = gameStateObj.cursor.movePath
        else:
            self.unit.path = self.path
        self.unit.play_movement_sound(gameStateObj)

    def execute(self, gameStateObj):
        self.unit.leave(gameStateObj)
        if self.new_movement_left is not None:
            self.unit.movement_left = self.new_movement_left
        self.unit.hasMoved = True
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.new_movement_left = self.unit.movement_left
        self.unit.movement_left = self.prev_movement_left
        self.unit.hasMoved = self.hasMoved
        self.unit.position = self.old_pos
        self.unit.path = []
        self.unit.arrive(gameStateObj)

class MoveArrive(Action):
    def __init__(self, unit):
        self.unit = unit

    def do(self, gameStateObj):
        self.unit.arrive(gameStateObj)

    def execute(self, gameStateObj):
        pass

    def reverse(self, gameStateObj):
        pass

# Just another name for move
class CantoMove(Move):
    pass

class SimpleMove(Action):
    """
    A script directed move, no animation
    """
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

    def do(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.old_pos
        self.unit.arrive(gameStateObj)

class Teleport(SimpleMove):
    pass

class ForcedMovement(SimpleMove):
    pass

class SwapMovement(SimpleMove):
    def __init__(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.unit1_pos = unit1.position
        self.unit2_pos = unit2.position

    def do(self, gameStateObj):
        self.unit1.leave(gameStateObj)
        self.unit2.leave(gameStateObj)
        self.unit1.position = self.unit2_pos
        self.unit2.position = self.unit1_pos
        self.unit1.arrive(gameStateObj)
        self.unit2.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit1.leave(gameStateObj)
        self.unit2.leave(gameStateObj)
        self.unit1.position = self.unit1_pos
        self.unit2.position = self.unit2_pos
        self.unit1.arrive(gameStateObj)
        self.unit2.arrive(gameStateObj)

class Warp(Action):
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

    def do(self, gameStateObj):
        self.unit.sprite.set_transition('warp_move')
        self.unit.sprite.set_next_position(self.new_pos)
        gameStateObj.map.initiate_warp_flowers(self.unit.position)

    def execute(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.old_pos
        self.unit.arrive(gameStateObj)

class FadeMove(Warp):
    def do(self, gameStateObj):
        self.unit.sprite.set_transition('fade_move')
        self.unit.sprite.set_next_position(self.new_pos)

class SimpleArrive(Action):
    def __init__(self, unit, pos):
        self.unit = unit
        self.pos = pos
        self.place_on_map = PlaceOnMap(unit, pos)

    def do(self, gameStateObj):
        self.place_on_map.do(gameStateObj)
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.place_on_map.reverse(gameStateObj)

class ArriveOnMap(SimpleArrive):
    pass

class WarpIn(ArriveOnMap):
    def do(self, gameStateObj):
        self.place_on_map.do(gameStateObj)
        self.unit.sprite.set_transition('warp_in')
        gameStateObj.map.initiate_warp_flowers(self.pos)
        self.unit.arrive(gameStateObj)

class FadeIn(ArriveOnMap):
    def do(self, gameStateObj):
        self.place_on_map.do(gameStateObj)
        if gameStateObj.map.on_border(self.pos) and gameStateObj.map.tiles[self.pos].name not in ('Stairs', 'Fort'):
            self.unit.sprite.spriteOffset = [num*GC.TILEWIDTH for num in gameStateObj.map.which_border(self.pos)]
            self.unit.sprite.set_transition('fake_in')
        else:
            self.unit.sprite.set_transition('fade_in')
        self.unit.arrive(gameStateObj)

class LeaveMap(Action):
    def __init__(self, unit):
        self.unit = unit
        self.remove_from_map = RemoveFromMap(self.unit)

    def do(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.remove_from_map.do(gameStateObj)

    def reverse(self, gameStateObj):
        self.remove_from_map.reverse(gameStateObj)
        self.unit.arrive(gameStateObj)

class RemoveFromMap(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_pos = self.unit.position

        # Yeah this is janky, but right now is required to nest an action
        # within another action
        self.untether_actions = [UnTetherStatus(s, self.unit.id) for s in self.unit.status_effects if s.tether]
        self.global_remove_actions = []

    def do(self, gameStateObj):
        if self.unit.position:
            # Global Statuses
            for status in gameStateObj.map.status_effects:
                remove = RemoveStatus(self.unit, status)
                remove.do(gameStateObj)
                self.global_remove_actions.append(remove)
            for action in self.untether_actions:
                action.do(gameStateObj)
        self.unit.position = None

    def reverse(self, gameStateObj):
        self.unit.position = self.old_pos
        if self.unit.position:
            # Global Statuses
            for remove in self.global_remove_actions:
                remove.reverse(gameStateObj)
            for action in self.untether_actions:
                action.reverse(gameStateObj)
            self.unit.previous_position = self.unit.position

class PlaceOnMap(Action):
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.new_pos = new_pos

        self.global_add_actions = []

    def do(self, gameStateObj):
        self.unit.position = self.new_pos
        if self.unit.position:
            for status in gameStateObj.map.status_effects:
                add = AddStatus(self.unit, status)
                add.do(gameStateObj)
                self.global_add_actions.append(add)
            self.unit.previous_position = self.unit.position

    def reverse(self, gameStateObj):
        if self.unit.position:
            # Global Statuses
            # for status in gameStateObj.map.status_effects:
            for add in self.global_add_actions:
                add.reverse(gameStateObj)
        self.unit.position = None

class Wait(Action):
    def __init__(self, unit):
        self.unit = unit
        self.hasMoved = unit.hasMoved
        self.hasTraded = unit.hasTraded
        self.hasAttacked = unit.hasAttacked
        self.finished = unit.finished

    def do(self, gameStateObj):
        self.unit.hasMoved = True
        self.unit.hasTraded = True
        self.unit.hasAttacked = True
        self.unit.finished = True
        self.unit.current_move_action = None
        self.unit.current_arrive_action = None

    def reverse(self, gameStateObj):
        self.unit.hasMoved = self.hasMoved
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.unit.finished = self.finished
        # print(self.unit.hasMoved, self.unit.hasTraded, self.unit.hasAttacked)

class Reset(Action):
    def __init__(self, unit):
        self.unit = unit
        self.hasMoved = unit.hasMoved
        self.hasTraded = unit.hasTraded
        self.hasAttacked = unit.hasAttacked
        self.finished = unit.finished
        # self.hasRunMoveAI = unit.hasRunMoveAI
        # self.hasRunAttackAI = unit.hasRunAttackAI
        # self.hasRunGeneralAI = unit.hasRunGeneralAI

    def do(self, gameStateObj):
        self.unit.reset()

    def reverse(self, gameStateObj):
        self.unit.hasMoved = self.hasMoved
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.unit.finished = self.finished
        # self.unit.hasRunMoveAI = self.hasRunMoveAI
        # self.unit.hasRunAttackAI = self.hasRunAttackAI
        # self.unit.hasRunGeneralAI = self.hasRunGeneralAI

class ResetAll(Action):
    def __init__(self, units):
        self.units = units
        self.actions = [Reset(unit) for unit in self.units]

    def do(self, gameStateObj):
        for action in self.actions:
            action.do(gameStateObj)

    def reverse(self, gameStateObj):
        for action in self.actions:
            action.reverse(gameStateObj)

# === RESCUE ACTIONS ==========================================================
class Rescue(Action):
    def __init__(self, unit, rescuee):
        self.unit = unit
        self.rescuee = rescuee
        self.old_pos = self.rescuee.position
        self.rescue_status = None

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
            if not self.rescue_status:
                self.rescue_status = StatusCatalog.statusparser("Rescue", gameStateObj)
            AddStatus(self.unit, self.rescue_status).do(gameStateObj)

    def execute(self, gameStateObj):
        self.unit.TRV = self.rescuee.id
        self.unit.strTRV = self.rescuee.name
        self.rescuee.leave(gameStateObj)
        self.rescuee.position = None
        self.unit.hasAttacked = True
        if 'savior' not in self.unit.status_bundle:
            AddStatus(self.unit, self.rescue_status).execute(gameStateObj)

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
        self.hasTraded = self.unit.hasTraded
        self.hasAttacked = self.unit.hasAttacked
        self.droppee_wait_action = Wait(self.droppee)
        self.rescue_status = None

    def do(self, gameStateObj):
        self.droppee.position = self.pos
        self.droppee.arrive(gameStateObj)
        # self.droppee.wait(gameStateObj, script=False)
        self.droppee.sprite.change_state('normal')
        self.droppee_wait_action.do(gameStateObj)
        self.unit.hasTraded = True  # Can no longer do everything
        self.unit.hasAttacked = True  # Can no longer do everything
        if Utility.calculate_distance(self.unit.position, self.pos) == 1:
            self.droppee.sprite.set_transition('fake_in')
            self.droppee.sprite.spriteOffset = [(self.unit.position[0] - self.pos[0])*GC.TILEWIDTH,
                                                (self.unit.position[1] - self.pos[1])*GC.TILEHEIGHT]
        self.unit.unrescue(gameStateObj)

    def execute(self, gameStateObj):
        self.droppee.position = self.pos
        self.droppee.arrive(gameStateObj)
        # self.droppee.wait(gameStateObj, script=False)
        self.droppee.sprite.change_state('normal')
        self.droppee_wait_action.execute(gameStateObj)
        self.droppee.hasAttacked = True
        self.unit.hasTraded = True  # Can no longer do everything
        self.unit.hasAttacked = True  # Can no longer do everything
        self.unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.TRV = self.droppee.id
        self.unit.strTRV = self.droppee.name
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.droppee_wait_action.reverse(gameStateObj)
        self.droppee.leave(gameStateObj)
        self.droppee.position = None
        if 'savior' not in self.unit.status_bundle:
            if not self.rescue_status:
                self.rescue_status = StatusCatalog.statusparser("Rescue", gameStateObj)
            AddStatus(self.unit, self.rescue_status).do(gameStateObj)

class Give(Action):
    def __init__(self, unit, other_unit):
        self.unit = unit
        self.other_unit = other_unit
        self.rescue_status = [status for status in self.unit.status_effects if status.id == 'Rescue']
        if self.rescue_status:
            self.rescue_status = self.rescue_status[0]
        self.other_rescue_status = None

    def do(self, gameStateObj):
        self.other_unit.TRV = self.unit.TRV
        self.other_unit.strTRV = self.unit.strTRV
        self.unit.hasAttacked = True
        if 'savior' not in self.other_unit.status_bundle:
            if not self.other_rescue_status:
                self.other_rescue_status = StatusCatalog.statusparser("Rescue", gameStateObj)
            AddStatus(self.other_unit, self.other_rescue_status).do(gameStateObj)
        self.unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.TRV = self.other_unit.TRV
        self.unit.strTRV = self.other_unit.strTRV
        self.unit.hasAttacked = False
        if 'savior' not in self.unit.status_bundle:
            AddStatus(self.unit, self.rescue_status).do(gameStateObj)
        self.other_unit.unrescue(gameStateObj)

class Take(Action):
    def __init__(self, unit, other_unit):
        self.unit = unit
        self.other_unit = other_unit
        self.hasTraded = self.unit.hasTraded
        self.rescue_status = None
        self.other_rescue_status = [status for status in self.other_unit.status_effects if status.id == 'Rescue']
        if self.other_rescue_status:
            self.other_rescue_status = self.other_rescue_status[0]

    def do(self, gameStateObj):
        self.unit.TRV = self.other_unit.TRV
        self.unit.strTRV = self.other_unit.strTRV
        self.unit.hasTraded = True
        if 'savior' not in self.unit.status_bundle:
            if not self.rescue_status:
                self.rescue_status = StatusCatalog.statusparser("Rescue", gameStateObj)
            AddStatus(self.unit, self.rescue_status).do(gameStateObj)
        self.other_unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.other_unit.TRV = self.unit.TRV
        self.other_unit.strTRV = self.unit.strTRV
        self.unit.hasTraded = self.hasTraded
        if 'savior' not in self.other_unit.status_bundle:
            AddStatus(self.other_unit, self.other_rescue_status).do(gameStateObj)
        self.unit.unrescue(gameStateObj)

# === ITEM ACTIONS ==========================================================
class PutItemInConvoy(Action):
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
    def __init__(self, unit, item, choice=True):
        self.unit = unit
        self.item = item
        self.choice = choice

    # with banner
    def do(self, gameStateObj):
        if self.unit.team == 'player' or len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item, gameStateObj)
            if self.choice:
                gameStateObj.banners.append(Banner.acquiredItemBanner(self.unit, self.item))
            else:
                gameStateObj.banners.append(Banner.nochoiceItemBanner(self.unit, self.item))
            gameStateObj.stateMachine.changeState('itemgain')

    # there shouldn't be any time this is called where the player has not already checked 
    # that there are less than cf.CONSTANTS['max_items'] items in their inventory
    def execute(self, gameStateObj):
        if self.unit.team == 'player' or len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item, gameStateObj)

    def reverse(self, gameStateObj):
        if self.item in self.unit.items:
            self.unit.remove_item(self.item, gameStateObj)

class DropItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self, gameStateObj):
        self.item.droppable = False
        if self.unit.team == 'player':
            self.unit.add_item(self.item, gameStateObj)
            gameStateObj.banners.append(Banner.acquiredItemBanner(self.unit, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        elif len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item, gameStateObj)

    def execute(self, gameStateObj):
        self.item.droppable = False
        if self.unit.team == 'player' or len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item, gameStateObj)

    def reverse(self, gameStateObj):
        self.item.droppable = True
        if self.item in self.unit.items:
            self.unit.remove_item(self.item, gameStateObj)

class DiscardItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.item_index = self.unit.items.index(self.item)

    def do(self, gameStateObj):
        self.unit.remove_item(self.item, gameStateObj)
        gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        gameStateObj.convoy.remove(self.item)
        self.unit.insert_item(self.item_index, self.item, gameStateObj)

class TakeItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self, gameStateObj):
        gameStateObj.convoy.remove(self.item)
        self.unit.add_item(self.item, gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.remove_item(self.item, gameStateObj)
        gameStateObj.convoy.append(self.item)

class RemoveItem(DiscardItem):
    def do(self, gameStateObj):
        self.unit.remove_item(self.item, gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.insert_item(self.item_index, self.item, gameStateObj)

class EquipItem(Action):
    """
    Assumes item is already in inventory
    """
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.old_idx = self.unit.items.index(self.item)

    def do(self, gameStateObj):
        self.unit.equip(self.item, gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.insert_item(self.old_idx, self.item, gameStateObj)

class UnequipItem(Action):
    """
    Used when an item should not be equipped any more
    Ex. If an item with per-chapter uses has no more uses
    """
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.was_mainweapon = False
        self.equip_item = None

    def _get_old_weapon(self, unit):
        return next((item for item in unit.items if item.weapon and unit.canWield(item)), None)

    def do(self, gameStateObj):
        self.was_mainweapon = self._get_old_weapon(self.unit) == self.item
        if self.was_mainweapon:
            if self.unit.getMainWeapon():
                self.equip_item = EquipItem(self.unit, self.unit.getMainWeapon())
                self.equip_item.do(gameStateObj)
            else:
                self.unit.unequip_item(self.item, gameStateObj)

    def reverse(self, gameStateObj):
        if self.was_mainweapon:
            if self.equip_item:
                self.equip_item.reverse(gameStateObj)
            else:
                self.unit.equip_item(self.item, gameStateObj)

class TradeItem(Action):
    def __init__(self, unit1, unit2, item1, item2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.item1 = item1
        self.item2 = item2
        self.item_index1 = unit1.items.index(item1) if item1 != "EmptySlot" else 4
        self.item_index2 = unit2.items.index(item2) if item2 != "EmptySlot" else 4

    def swap(self, unit1, unit2, item1, item2, item_index1, item_index2, gameStateObj):
        # Do the swap
        if item1 and item1 != "EmptySlot":
            unit1.remove_item(item1, gameStateObj)
            unit2.insert_item(item_index2, item1, gameStateObj)
        if item2 and item2 != "EmptySlot":
            unit2.remove_item(item2, gameStateObj)
            unit1.insert_item(item_index1, item2, gameStateObj)   

    def do(self, gameStateObj):
        self.swap(self.unit1, self.unit2, self.item1, self.item2, self.item_index1, self.item_index2, gameStateObj)

    def reverse(self, gameStateObj):
        self.swap(self.unit1, self.unit2, self.item2, self.item1, self.item_index2, self.item_index1, gameStateObj)

class OwnerHasTraded(Action):
    def __init__(self, owner):
        self.owner = owner
        self.hasTraded = self.owner.hasTraded
        self.hasMoved = self.owner.hasMoved

    def do(self, gameStateObj):
        self.owner.hasTraded = True
        self.owner.hasMoved = True

    def reverse(self, gameStateObj):
        self.owner.hasTraded = self.hasTraded
        self.owner.hasMoved = self.hasMoved

class UseItem(Action):
    """
    Doesn't actually fully USE the item, just reduces the number of uses
    """
    def __init__(self, item):
        self.item = item

    def do(self, gameStateObj):
        if not self.item:
            return
        if self.item.uses:
            self.item.uses.decrement()
        if self.item.c_uses:
            self.item.c_uses.decrement()
        if self.item.cooldown:
            self.item.cooldown.decrement(self.item, gameStateObj)
            self.prior_cd = self.item.cooldown.cd_turns

    def reverse(self, gameStateObj):
        if not self.item:
            return
        if self.item.uses:
            self.item.uses.increment()
        if self.item.c_uses:
            self.item.c_uses.increment()
        if self.item.cooldown:
            self.item.cooldown.increment(self.prior_cd)

class RepairItem(Action):
    def __init__(self, item):
        self.item = item
        self.item_old_uses = self.item.uses.uses if self.item.uses else 0
        self.item_old_c_uses = self.item.c_uses.uses if self.item.c_uses else 0

    def do(self, gameStateObj):
        if self.item.uses:
            self.item.uses.reset()
        if self.item.c_uses:
            self.item.c_uses.reset()

    def reverse(self, gameStateObj):
        if self.item.uses:
            self.item.uses.set(self.item_old_uses)
        if self.item.c_uses:
            self.item.c_uses.set(self.item.item_old_c_uses)

class CooloffItem(Action):
    def __init__(self, item):
        self.item = item
        self.prior_turns = self.item.cooldown.total_cd_turns

    def do(self, gameStateObj):
        if self.item.cooldown:
            self.item.cooldown.recharge()

    def reverse(self, gameStateObj):
        if self.item.cooldown:
            self.item.cooldown.discharge(self.prior_turns)
            
class GainExp(Action):
    def __init__(self, unit, exp):
        self.unit = unit
        self.old_exp = self.unit.exp
        self.exp = exp

    def do(self, gameStateObj):
        self.unit.set_exp((self.old_exp + self.exp)%100)

    def reverse(self, gameStateObj):
        self.unit.set_exp(self.old_exp)

class SetExp(GainExp):
    def do(self, gameStateObj):
        self.unit.set_exp(self.exp)

class RecordGrowthPoints(Action):
    def __init__(self, unit, old_growth_points):
        self.unit = unit
        self.old_growth_points = old_growth_points
        self.new_growth_points = self.unit.growth_points

    def do(self, gameStateObj):
        pass

    def execute(self, gameStateObj):
        self.unit.growth_points = self.new_growth_points

    def reverse(self, gameStateObj):
        self.unit.growth_points = self.old_growth_points

class IncLevel(Action):  # Assumes unit did not promote
    def __init__(self, unit):
        self.unit = unit

    def do(self, gameStateObj):
        self.unit.level += 1

    def reverse(self, gameStateObj):
        self.unit.level -= 1

class Promote(Action):
    def __init__(self, unit, new_klass):
        self.unit = unit
        self.old_exp = self.unit.exp
        self.old_level = self.unit.level
        self.old_klass = ClassData.class_dict[unit.klass]
        self.new_klass = ClassData.class_dict[new_klass]
        self.levelup_list = self.new_klass['promotion']
        self.new_wexp = self.new_klass['wexp_gain']
        current_stats = list(self.unit.stats.values())
        # Any stat that's not defined, fill in with new classes bases - current stats
        if len(self.levelup_list) < len(self.new_klass['bases']):
            missing_idxs = range(len(self.levelup_list), len(self.new_klass['bases']))
            new_bases = [self.new_klass['bases'][i] - current_stats[i].base_stat for i in missing_idxs]
            self.levelup_list.extend(new_bases)
        assert len(self.levelup_list) == len(self.new_klass['max']) == len(current_stats), "%s %s %s" % (self.levelup_list, self.new_klass['max'], current_stats)
        # check maxes
        for index, stat in enumerate(self.levelup_list):
            self.levelup_list[index] = min(stat, self.new_klass['max'][index] - current_stats[index].base_stat)
        # For removing statuses on promotion
        self.sub_actions = []

    def get_data(self):
        return self.levelup_list, self.new_wexp

    def do(self, gameStateObj):
        self.sub_actions.clear()
        # Find the skills to remove from the previous class
        if not cf.CONSTANTS['inherit_class_skills']:
            for level_needed, skill in self.old_klass['skills']:
                for status in self.unit.status_effects:
                    if status.id == skill:
                        new_action = RemoveStatus(self.unit, status)
                        self.sub_actions.append(new_action)
        for action in self.sub_actions:
            action.do(gameStateObj)

        self.unit.removeSprites()
        self.unit.klass = self.new_klass['id']
        self.unit.set_exp(0)
        self.unit.level = 1
        self.unit.movement_group = self.new_klass['movement_group']
        self.unit.apply_levelup(self.levelup_list, True)
        self.unit.loadSprites()

    def reverse(self, gameStateObj):
        self.unit.removeSprites()
        self.unit.klass = self.old_klass['id']
        self.unit.set_exp(self.old_exp)
        self.unit.level = self.old_level
        self.unit.movement_group = self.old_klass['movement_group']
        self.unit.apply_levelup([-x for x in self.levelup_list], True)
        self.unit.loadSprites()

        for action in self.sub_actions:
            action.reverse(gameStateObj)
        self.sub_actions.clear()

class ApplyLevelUp(Action):
    def __init__(self, unit, stat_increase):
        self.unit = unit
        current_stats = [stat.base_stat for stat in self.unit.stats.values()]
        self.stat_increase = stat_increase
        klass = ClassData.class_dict[self.unit.klass]
        for index, stat in enumerate(self.stat_increase):
            self.stat_increase[index] = min(stat, klass['max'][index] - current_stats[index])

    def do(self, gameStateObj):
        self.unit.apply_levelup(self.stat_increase)

    def reverse(self, gameStateObj):
        self.unit.apply_levelup([-x for x in self.stat_increase])

class PermanentStatIncrease(ApplyLevelUp):
    def do(self, gameStateObj):
        self.previous_hp = self.unit.currenthp
        self.unit.apply_levelup(self.stat_increase, True)

    def reverse(self, gameStateObj):
        self.unit.apply_levelup([-x for x in self.stat_increase], True)
        # Since hp_up...
        self.unit.set_hp(self.previous_hp)

class PermanentGrowthIncrease(Action):
    def __init__(self, unit, stat_increase):
        self.unit = unit
        self.current_growths = self.unit.growths
        self.stat_increase = stat_increase

    def do(self, gameStateObj):
        self.unit.apply_growth_mod(self.stat_increase)

    def reverse(self, gameStateObj):
        self.unit.apply_growth_mod([-x for x in self.stat_increase])

class GainWexp(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self, gameStateObj):
        self.unit.increase_wexp(self.item, gameStateObj)

    def execute(self, gameStateObj):
        self.unit.increase_wexp(self.item, gameStateObj, banner=False)

    def reverse(self, gameStateObj):
        if isinstance(self.item, list):
            self.unit.increase_wexp([-x for x in self.item], gameStateObj, banner=False)
        else:
            change = -self.item.wexp if self.item.wexp else -1
            if self.item.TYPE in Weapons.TRIANGLE.name_to_index:
                self.unit.wexp[Weapons.TRIANGLE.name_to_index[self.item.TYPE]] += change

class ChangeHP(Action):
    def __init__(self, unit, num):
        self.unit = unit
        self.num = num
        self.old_hp = self.unit.currenthp

    def do(self, gameStateObj=None):
        self.unit.change_hp(self.num)

    def reverse(self, gameStateObj=None):
        self.unit.set_hp(self.old_hp)

class ChangeTileHP(Action):
    def __init__(self, pos, num):
        self.position = pos
        self.num = num
        self.old_hp = 1

    def do(self, gameStateObj):
        tile = gameStateObj.map.tiles[self.position]
        self.old_hp = tile.currenthp
        tile.change_hp(self.num)

    def reverse(self, gameStateObj):
        tile = gameStateObj.map.tiles[self.position]
        tile.set_hp(self.old_hp)

class ChangeFatigue(Action):
    def __init__(self, unit, fatigue, ignore_tags=False):
        self.unit = unit
        self.fatigue = fatigue
        self.old_fatigue = self.unit.fatigue
        self.ignore_tags = ignore_tags
        self.actions = []

    def do(self, gameStateObj):
        if not self.ignore_tags: 
            if 'Tireless' in self.unit.tags or 'tireless' in self.unit.status_bundle:
                return
        self.unit.fatigue += self.fatigue
        if self.unit.fatigue < 0:
            self.unit.fatigue = 0
            
        # Handle adding statuses whenever Fatigue changes
        if gameStateObj.game_constants['Fatigue'] == 4:
            if self.unit.fatigue >= GC.EQUATIONS.get_max_fatigue(self.unit):
                fatigue_status = StatusCatalog.statusparser("Fatigued", gameStateObj)
                self.actions.append(AddStatus(self.unit, fatigue_status))
            else:
                if any(status.id == "Fatigued" for status in self.unit.status_effects):
                    self.actions.append(RemoveStatus(self.unit, "Fatigued"))
        elif gameStateObj.game_constants['Fatigue'] == 5:
            if self.unit.fatigue < GC.EQUATIONS.get_max_fatigue(self.unit):
                fatigue_status = StatusCatalog.statusparser("Fatigued", gameStateObj)
                self.actions.append(AddStatus(self.unit, fatigue_status))
            else:
                if any(status.id == "Fatigued" for status in self.unit.status_effects):
                    self.actions.append(RemoveStatus(self.unit, "Fatigued"))

        for action in self.actions:
            action.do(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.fatigue = self.old_fatigue

        for action in self.actions:
            action.reverse(gameStateObj)

class Miracle(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_hp = self.unit.currenthp

    def do(self, gameStateObj):
        self.unit.isDying = False
        self.unit.set_hp(1)
        miracle_status = None
        for status in self.unit.status_effects:
            if status.miracle and status.count and status.count.count > 0:
                status.count.count -= 1
                miracle_status = status
                break
        gameStateObj.banners.append(Banner.miracleBanner(self.unit, miracle_status))
        gameStateObj.stateMachine.changeState('itemgain')
        self.unit.sprite.change_state('normal', gameStateObj)

    def execute(self, gameStateObj):
        self.unit.isDying = False
        self.unit.set_hp(1)
        for status in self.unit.status_effects:
            if status.miracle and status.count and status.count.count > 0:
                status.count.count -= 1
                break

    def reverse(self, gameStateObj):
        # self.unit.isDying = True
        self.unit.set_hp(self.old_hp)
        for status in self.unit.status_effects:
            if status.miracle and status.count:
                status.count.count += 1
                break

class Die(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_pos = self.unit.position
        self.leave_map = LeaveMap(self.unit)
        self.drop = None

    def do(self, gameStateObj):
        # Drop any travelers
        if self.unit.TRV:
            drop_me = gameStateObj.get_unit_from_id(self.unit.TRV)
            self.drop = Drop(self.unit, drop_me, self.unit.position)
            self.drop.do(gameStateObj)
            GC.SOUNDDICT['RescuedFalling'].play()

        # I no longer have a position
        self.leave_map.do(gameStateObj)
        ##
        self.unit.dead = True
        self.unit.isDying = False

    def reverse(self, gameStateObj):
        self.unit.dead = False
        self.unit.sprite.set_transition('normal')
        self.unit.sprite.change_state('normal', gameStateObj)

        self.leave_map.reverse(gameStateObj)

        if self.drop:
            self.drop.reverse(gameStateObj)

class Resurrect(Action):
    def __init__(self, unit):
        self.unit = unit

    def do(self, gameStateObj):
        self.unit.dead = False

    def reverse(self, gameStateObj):
        self.unit.dead = True

# === GENERAL ACTIONS =========================================================
class ChangeName(Action):
    def __init__(self, unit, new_name):
        self.unit = unit
        self.old_name = self.unit.name
        self.new_name = new_name

    def do(self, gameStateObj):
        self.unit.name = self.new_name

    def reverse(self, gameStateObj):
        self.unit.name = self.old_name

class ChangePortrait(Action):
    def __init__(self, unit, new_portrait_id):
        self.unit = unit
        self.old_portrait_id = self.unit.portrait_id
        self.new_portrait_id = new_portrait_id

    def do(self, gameStateObj):
        self.unit.portrait_id = self.new_portrait_id
        self.unit.bigportrait = Engine.subsurface(GC.UNITDICT[str(self.unit.portrait_id) + 'Portrait'], (0, 0, 96, 80))
        self.unit.portrait = Engine.subsurface(GC.UNITDICT[str(self.unit.portrait_id) + 'Portrait'], (96, 16, 32, 32))

    def reverse(self, gameStateObj):
        self.unit.portrait_id = self.old_portrait_id
        self.unit.bigportrait = Engine.subsurface(GC.UNITDICT[str(self.unit.portrait_id) + 'Portrait'], (0, 0, 96, 80))
        self.unit.portrait = Engine.subsurface(GC.UNITDICT[str(self.unit.portrait_id) + 'Portrait'], (96, 16, 32, 32))

class ChangeTeam(Action):
    def __init__(self, unit, new_team):
        self.unit = unit
        self.new_team = new_team
        self.old_team = self.unit.team
        self.reset_action = Reset(self.unit)

    def _change_team(self, team, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.team = team
        gameStateObj.boundary_manager.reset_unit(self.unit)
        self.unit.loadSprites()

    def do(self, gameStateObj):
        self._change_team(self.new_team, gameStateObj)
        self.reset_action.do(gameStateObj)
        self.unit.arrive(gameStateObj)
        
    def reverse(self, gameStateObj):
        self._change_team(self.old_team, gameStateObj)
        self.reset_action.reverse(gameStateObj)
        self.unit.arrive(gameStateObj)

class ChangeAI(Action):
    def __init__(self, unit, new_ai):
        self.unit = unit
        self.old_ai = self.unit.ai_descriptor
        self.new_ai = new_ai

    def do(self, gameStateObj):
        self.unit.get_ai(self.new_ai)
        logger.info('New AI: %s', self.unit.ai_descriptor)

    def reverse(self, gameStateObj):
        self.unit.get_ai(self.old_ai)
        logger.info('New AI: %s', self.unit.ai_descriptor)

class ModifyAI(Action):
    def __init__(self, unit, new_primary_ai, new_secondary_ai):
        self.unit = unit
        self.old_primary_ai = self.unit.ai.ai1_state
        self.old_secondary_ai = self.unit.ai.ai2_state
        self.new_primary_ai = new_primary_ai
        self.new_secondary_ai = new_secondary_ai

    def do(self, gameStateObj):
        self.unit.ai.change_ai(self.new_primary_ai, self.new_secondary_ai)

    def reverse(self, gameStateObj):
        self.unit.ai.change_ai(self.old_primary_ai, self.old_secondary_ai)

class AIGroupPing(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_range = self.unit.ai.view_range
        self.old_ai_group_flag = self.unit.ai.ai_group_flag

    def do(self, gameStateObj):
        self.unit.ai.view_range = 2 # allow group to see whole universe
        self.unit.ai.ai_group_flag = True # Don't need to do this more than once

    def reverse(self, gameStateObj):
        self.unit.ai.view_range = self.old_range
        self.unit.ai.ai_group_flag = self.old_ai_group_flag

class ChangeParty(Action):
    def __init__(self, unit, new_party):
        self.unit = unit
        self.old_party = self.unit.party
        self.new_party = new_party

    def do(self, gameStateObj):
        self.unit.party = self.new_party

    def reverse(self, gameStateObj):
        self.unit.party = self.old_party

class GiveGold(Action):
    def __init__(self, amount, party):
        self.amount = amount
        self.party = party

    def do(self, gameStateObj):
        gameStateObj.inc_money(self.amount, self.party)
        gameStateObj.banners.append(Banner.acquiredGoldBanner(self.amount))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        gameStateObj.inc_money(self.amount, self.party)

    def reverse(self, gameStateObj):
        gameStateObj.inc_money(-self.amount, self.party)

class MakeItemDroppable(Action):
    """ 
    Done after adding item to unit
    """
    def __init__(self, unit, item):
        self.unit = unit
        self.item_to_drop = item
        self.drop = [i.droppable for i in self.unit.items]

    def do(self, gameStateObj):
        for item in self.unit.items:
            item.droppable = False
        self.item_to_drop.droppable = True

    def reverse(self, gameStateObj):
        for idx, item in enumerate(self.unit.items):
            item.droppable = self.drop[idx]

class ChangeGameConstant(Action):
    def __init__(self, constant, new_value):
        self.constant = constant
        self.already_present = False
        self.old_value = None
        self.new_value = new_value

    def do(self, gameStateObj):
        self.already_present = self.constant in gameStateObj.game_constants
        self.old_value = gameStateObj.game_constants[self.constant]
        gameStateObj.game_constants[self.constant] = self.new_value

    def reverse(self, gameStateObj):
        gameStateObj.game_constants[self.constant] = self.old_value        
        if not self.already_present:
            del gameStateObj.game_constants[self.constant]

class ChangeLevelConstant(Action):
    def __init__(self, constant, new_value):
        self.constant = constant
        self.already_present = False
        self.old_value = None
        self.new_value = new_value

    def do(self, gameStateObj):
        self.already_present = self.constant in gameStateObj.level_constants
        self.old_value = gameStateObj.level_constants[self.constant]   
        gameStateObj.level_constants[self.constant] = self.new_value

    def reverse(self, gameStateObj):
        gameStateObj.level_constants[self.constant] = self.old_value
        if not self.already_present:
            del gameStateObj.level_constants[self.constant]

class IncrementTurn(Action):
    def __init__(self):
        pass

    def do(self, gameStateObj):
        gameStateObj.turncount += 1

    def reverse(self, gameStateObj):
        gameStateObj.turncount -= 1

class ChangePhase(Action):
    def __init__(self):
        pass

    def do(self, gameStateObj):
        gameStateObj.phase._next()

    def reverse(self, gameStateObj):
        gameStateObj.phase._prev()

class MarkPhase(Action):
    def __init__(self, phase_name):
        self.phase_name = phase_name

class LockTurnwheel(Action):
    def __init__(self, lock):
        self.lock = lock

class Message(Action):
    def __init__(self, message):
        self.message = message

class AddTag(Action):
    def __init__(self, unit, new_tag):
        self.unit = unit
        self.new_tag = new_tag
        self.already_present = new_tag in unit._tags

    def do(self, gameStateObj):
        if not self.already_present:
            self.unit._tags.add(self.new_tag)

    def reverse(self, gameStateObj):
        if not self.already_present:
            self.unit._tags.remove(self.new_tag)

class RemoveTag(Action):
    def __init__(self, unit, tag):
        self.unit = unit
        self.tag = tag
        self.already_present = tag in unit._tags

    def do(self, gameStateObj):
        if self.already_present:
            self.unit._tags.remove(self.tag)

    def reverse(self, gameStateObj):
        if self.already_present:
            self.unit._tags.add(self.tag)

class AddTalk(Action):
    def __init__(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2

    def do(self, gameStateObj):
        gameStateObj.talk_options.append((self.unit1, self.unit2))

    def reverse(self, gameStateObj):
        gameStateObj.talk_options.remove((self.unit1, self.unit2))

class RemoveTalk(Action):
    def __init__(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2

    def do(self, gameStateObj):
        gameStateObj.talk_options.remove((self.unit1, self.unit2))

    def reverse(self, gameStateObj):
        gameStateObj.talk_options.append((self.unit1, self.unit2))

class ChangeObjective(Action):
    def __init__(self, display_name=None, win_condition=None, loss_condition=None):
        self.display_name = display_name
        self.win_condition = win_condition
        self.loss_condition = loss_condition

    def do(self, gameStateObj):
        obj = gameStateObj.objective
        self.old_values = obj.display_name_string, obj.win_condition_string, obj.loss_condition_string
        if self.display_name:
            obj.display_name_string = self.display_name
        if self.win_condition:
            obj.win_condition_string = self.win_condition
        if self.loss_condition:
            obj.loss_condition_string = self.loss_condition

    def reverse(self, gameStateObj):
        obj = gameStateObj.objective
        if self.display_name:
            obj.display_name_string = self.old_values[0]
        if self.win_condition:
            obj.win_condition_string = self.old_values[1]
        if self.loss_condition:
            obj.loss_condition_string = self.old_values[2]

# === SUPPORT ACTIONS =======================================================
class IncrementSupportLevel(Action):
    def __init__(self, unit1_id, unit2_id):
        self.unit1_id = unit1_id
        self.unit2_id = unit2_id

    def do(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        edge.increment_support_level()

    def reverse(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        edge.support_level -= 1
        edge.support_levels_this_chapter -= 1

class SupportGain(Action):
    def __init__(self, unit1_id, unit2_id, gain):
        self.unit1_id = unit1_id
        self.unit2_id = unit2_id
        self.gain = gain

        self.current_value = 0
        self.value_added_this_chapter = 0

    def do(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        self.current_value = edge.current_value
        self.value_added_this_chapter = edge.value_added_this_chapter
        edge.increment(self.gain)     

    def reverse(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        edge.current_value = self.current_value
        edge.value_added_this_chapter = self.value_added_this_chapter

class HasAttacked(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_value = self.unit.hasAttacked

    def do(self, gameStateObj):
        self.unit.hasAttacked = True

    def reverse(self, gameStateObj):
        self.unit.hasAttacked = self.old_value

class HasTraded(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_value = self.unit.hasTraded

    def do(self, gameStateObj):
        self.unit.hasTraded = True

    def reverse(self, gameStateObj):
        self.unit.hasTraded = self.old_value

class UpdateUnitRecords(Action):
    def __init__(self, unit, record):
        self.unit = unit
        self.record = record  # damage, healing, kills

    def do(self, gameStateObj=None):
        self.unit.records['damage'] += self.record[0]
        self.unit.records['healing'] += self.record[1]
        self.unit.records['kills'] += self.record[2]

    def reverse(self, gameStateObj=None):
        self.unit.records['damage'] -= self.record[0]
        self.unit.records['healing'] -= self.record[1]
        self.unit.records['kills'] -= self.record[2]

class RecordRandomState(Action):
    run_on_load = True
    
    def __init__(self, old, new):
        self.old = old
        self.new = new

    def do(self, gameStateObj):
        pass

    def execute(self, gameStateObj):
        static_random.set_combat_random_state(self.new)

    def reverse(self, gameStateObj):
        static_random.set_combat_random_state(self.old)

class RecordOtherRandomState(Action):
    run_on_load = True
    
    def __init__(self, old, new):
        self.old = old
        self.new = new

    def do(self, gameStateObj):
        pass

    def execute(self, gameStateObj):
        static_random.set_other_random_state(self.new)

    def reverse(self, gameStateObj):
        static_random.set_other_random_state(self.old)

# === SKILL AND STATUS ACTIONS ===================================================
class AddStatus(Action):
    def __init__(self, unit, status_obj):
        self.unit = unit
        self.status_obj = status_obj
        self.actions = []

    def do(self, gameStateObj):
        self.actions = []
        if self.status_obj.uid not in gameStateObj.allstatuses:
            print('Major problem!')
            print('%s not found in allstatuses!' % self.status_obj)
            logger.error("%s not found in allstatuses", self.status_obj)
            
        logger.info('Adding Status %s to %s at %s', self.status_obj.id, self.unit.name, self.unit.position)

        if not self.status_obj.stack:
            for status in self.unit.status_effects:
                if status.id == self.status_obj.id:
                    logger.info('Status %s already present', status.id)
                    if status.time:
                        self.actions.append(RemoveStatus(self.unit, status))
                    else:
                        return  # just ignore this new one

        if not self.status_obj.momentary:
            self.actions.append(GiveStatus(self.unit, self.status_obj))

        # --- Momentary status ---
        if self.status_obj.refresh:
            self.actions.append(Reset(self.unit))
            current_phase = gameStateObj.phase.get_current_phase()
            if current_phase != 'player' and self.unit.team == current_phase:
                gameStateObj.ai_unit_list.append(self.unit)  # Move him up to next on the list
                self.unit.reset_ai()
            # for status in self.unit.status_effects:
            #     if status.charged_status and status.charged_status.check_charged():
            #         self.actions.append(FinalizeChargedStatus(status, self.unit))

        if self.status_obj.skill_restore:
            self.actions.append(ChargeAllSkills(self.unit, 1000))

        if self.status_obj.clear:
            for status in self.unit.status_effects:
                if self.status_obj.clear is True or status.id in self.status_obj.clear.split(','):
                    if status.time or status.clearable:
                        self.actions.append(RemoveStatus(self.unit, status))

        # --- Non-momentary status ---
        if self.status_obj.mind_control:
            self.status_obj.data['original_team'] = self.unit.team
            p_unit = gameStateObj.get_unit_from_id(self.status_obj.giver_id)
            self.actions.append(ChangeTeam(self.unit, p_unit.team))

        if self.status_obj.ai_change:
            self.status_obj.data['original_ai'] = self.unit.ai_descriptor
            logger.info('%s %s', self.unit, self.status_obj.ai_change)
            self.actions.append(ChangeAI(self.unit, self.status_obj.ai_change))

        if self.status_obj.stat_change:
            self.actions.append(ApplyStatChange(self.unit, self.status_obj.stat_change))
        if self.status_obj.growth_mod:
            self.actions.append(ApplyGrowthMod(self.unit, self.status_obj.growth_mod))

        if self.status_obj.stat_halve:
            penalties = [(-stat.base_stat//2 if name in self.status_obj.stat_halve.stats else 0)
                         for name, stat in self.unit.stats.items()]
            self.status_obj.stat_halve.penalties = penalties
            self.actions.append(ApplyStatChange(self.unit, penalties))

        if self.status_obj.tireless:
            # Make sure if a unit becomes tireless, their fatigue is set to 0
            self.actions.append(ChangeFatigue(self.unit, -9999, True))

        if self.status_obj.flying:
            self.unit.remove_tile_status(gameStateObj, force=True)

        if self.status_obj.item_mod:
            for item in self.unit.items:
                self.status_obj.item_mod.apply_mod(item, gameStateObj)

        if self.status_obj.aura:
            Aura.propagate_aura(self.unit, self.status_obj, gameStateObj)

        if self.status_obj.shrug_off:
            for status in self.unit.status_effects:
                if status.time and status.negative and status.time.time_left > 1:
                    self.actions.append(ShrugOff(status))

        # If you have shrug off...
        if 'shrug_off' in self.unit.status_bundle and \
                self.status_obj.time and self.status_obj.time.total_time > 1:
            self.actions.append(ShrugOff(self.status_obj))

        for action in self.actions:
            action.do(gameStateObj)

        # Does not need to be reversed -- turnwheel takes care of this
        if self.status_obj.affects_movement:
            if self.unit.team.startswith('enemy'):
                gameStateObj.boundary_manager._remove_unit(self.unit, gameStateObj)
                if self.unit.position:
                    gameStateObj.boundary_manager._add_unit(self.unit, gameStateObj)

    def reverse(self, gameStateObj):
        for action in self.actions:
            action.reverse(gameStateObj)

        if self.status_obj.aura:
            Aura.release_aura(self.unit, self.status_obj, gameStateObj)

        if self.status_obj.item_mod:
            for item in self.unit.items:
                self.status_obj.item_mod.reverse_mod(item, gameStateObj)

        if self.status_obj.flying:
            self.unit.acquire_tile_status(gameStateObj, force=True)

class GiveStatus(Action):
    def __init__(self, unit, status_obj):
        self.unit = unit
        self.status_obj = status_obj

    def do(self, gameStateObj):
        self.unit.status_bundle.update(list(self.status_obj.components)) 
        self.unit.status_effects.append(self.status_obj)
        self.status_obj.owner_id = self.unit.id

    def reverse(self, gameStateObj):
        if self.status_obj in self.unit.status_effects:
            self.status_obj.owner_id = None
            self.unit.status_effects.remove(self.status_obj)
            self.unit.status_bundle.subtract(list(self.status_obj.components))
        else:
            logger.error("Status Object %s not in %s's status effects", self.status_obj.id, self.unit.name)

class RemoveStatus(Action):
    def __init__(self, unit, status_obj, clean_up=False):
        self.unit = unit
        self.status_obj = status_obj
        self.actions = []
        self.clean_up = clean_up

    def do(self, gameStateObj):
        self.actions = []
        if not isinstance(self.status_obj, StatusCatalog.Status):
            # Then it must be an integer (the status id)
            for status in self.unit.status_effects:
                if self.status_obj == status.id:
                    self.status_obj = status
                    break
            else:
                logger.warning('Status ID %s not present...', self.status_obj)
                logger.warning(self.unit.status_effects)
                return

        logger.info('Removing status %s from %s at %s', self.status_obj.id, self.unit.name, self.unit.position)
        if self.status_obj in self.unit.status_effects:
            self.actions.append(TakeStatus(self.unit, self.status_obj))
        else:
            logger.warning('Status %s %s %s not present...', self.status_obj.id, self.status_obj.name, self.status_obj.uid)
            logger.warning(self.unit.status_effects)
            logger.warning([s.uid for s in self.unit.status_effects])
            return

        # --- Non-momentary status ---
        if self.status_obj.mind_control:
            self.actions.append(ChangeTeam(self.unit, self.status_obj.data['original_team']))

        if self.status_obj.ai_change:
            logger.info('%s %s %s', self.unit, self.unit.ai_descriptor, self.status_obj.data['original_ai'])
            self.actions.append(ChangeAI(self.unit, self.status_obj.data['original_ai']))

        if self.status_obj.upkeep_stat_change:
            stat_change = [-stat*(self.status_obj.upkeep_stat_change.count) for stat in 
                           self.status_obj.upkeep_stat_change.stat_change]
            self.actions.append(ApplyStatChange(self.unit, stat_change))
        if self.status_obj.stat_change:
            stat_change = [-stat for stat in self.status_obj.stat_change]
            self.actions.append(ApplyStatChange(self.unit, stat_change))
        if self.status_obj.growth_mod:
            growth_mod = [-growth for growth in self.status_obj.growth_mod]
            self.actions.append(ApplyStatChange(self.unit, growth_mod))

        if self.status_obj.stat_halve:
            penalties = [-stat for stat in self.status_obj.stat_halve.penalties]
            self.actions.append(ApplyStatChange(self.unit, penalties))

        if self.status_obj.flying and not self.clean_up:
            self.unit.acquire_tile_status(gameStateObj, force=True)

        if self.status_obj.item_mod:
            for item in self.unit.items:
                self.status_obj.item_mod.reverse_mod(item, gameStateObj)

        if self.status_obj.aura:
            Aura.release_aura(self.unit, self.status_obj, gameStateObj)

        if self.status_obj.tether:
            self.actions.append(UnTetherStatus(self.status_obj, self.unit.id))

        if self.status_obj.status_chain and not self.clean_up:
            new_status = StatusCatalog.statusparser(self.status_obj.status_chain, gameStateObj)
            self.actions.append(AddStatus(self.unit, new_status))

        # TODO. Replace this with custom event script on remove
        if self.status_obj.ephemeral:
            self.unit.isDying = True
            self.actions.append(ChangeHP(self.unit, -10000))

        for action in self.actions:
            action.do(gameStateObj)

        # Does not need to be reversed -- turnwheel takes care of this
        if self.status_obj.affects_movement:
            if self.unit.team.startswith('enemy'):
                gameStateObj.boundary_manager._remove_unit(self.unit, gameStateObj)
                if self.unit.position:
                    gameStateObj.boundary_manager._add_unit(self.unit, gameStateObj)

    def reverse(self, gameStateObj):
        if not isinstance(self.status_obj, StatusCatalog.Status):
            logger.warning('Status ID %s not present...', self.status_obj)
            return

        for action in self.actions:
            action.reverse(gameStateObj)
        
        if self.status_obj.flying:
            self.unit.remove_tile_status(gameStateObj, force=True)

        if self.status_obj.item_mod:
            for item in self.unit.items:
                self.status_obj.item_mod.apply_mod(item, gameStateObj)

        if self.status_obj.aura:
            Aura.propagate_aura(self.unit, self.status_obj, gameStateObj)

        if self.status_obj.ephemeral:
            self.unit.isDying = False

class TakeStatus(Action):
    def __init__(self, unit, status_obj):
        self.unit = unit
        self.status_obj = status_obj

    def do(self, gameStateObj):
        self.status_obj.owner_id = None
        self.unit.status_effects.remove(self.status_obj)
        self.unit.status_bundle.subtract(list(self.status_obj.components))

    def reverse(self, gameStateObj):
        self.unit.status_bundle.update(list(self.status_obj.components)) 
        self.unit.status_effects.append(self.status_obj)
        self.status_obj.owner_id = self.unit.id

class TetherStatus(Action):
    def __init__(self, status_obj, applied_status_obj, parent, child):
        self.status_obj = status_obj
        self.applied_status_obj = applied_status_obj
        self.parent = parent
        self.child = child

    def do(self, gameStateObj):
        self.status_obj.add_child(self.child.id)
        self.applied_status_obj.giver_id = self.parent.id

    def reverse(self, gameStateObj):
        self.status_obj.remove_child(self.child.id)
        self.applied_status_obj.giver_id = None

# Also removes child statii
class UnTetherStatus(Action):
    def __init__(self, status_obj, unit_id):
        self.status_obj = status_obj
        self.true_children = []
        self.child_status = []
        self.unit_id = unit_id

    def do(self, gameStateObj):
        self.true_children.clear()
        self.child_status.clear()
        children = list(self.status_obj.children)
        for u_id in reversed(children):
            child_unit = gameStateObj.get_unit_from_id(u_id)
            if child_unit:
                for c_status in child_unit.status_effects:
                    # print(c_status, c_status.id, self.status_obj.tether)
                    # Only remove the statuses that come from the right unit
                    if c_status.id == self.status_obj.tether and c_status.giver_id == self.unit_id:
                        self.child_status.append(c_status)
                        self.true_children.append(u_id)
                        RemoveStatus(child_unit, c_status).do(gameStateObj)
                        break
        # assert len(self.children) == len(self.child_status), "UnTetherStatus Action is broken"
        # Sometimes a tether child status can be removed (Like remove_range or Restore staff)
        # This is not a problem, the tether child status does not inform the parent tether status
        # So the parent tether status still thinks that the child tether status still exists
        # But it doesn't
        self.status_obj.children.clear()

    def reverse(self, gameStateObj):
        # assert len(self.children) == len(self.child_status), "UnTetherStatus Action is broken"
        for idx, u_id in enumerate(self.true_children):
            child_unit = gameStateObj.get_unit_from_id(u_id)
            if child_unit:
                self.status_obj.add_child(u_id)
                applied_status = self.child_status[idx]
                AddStatus(child_unit, applied_status).do(gameStateObj)
        self.true_children.clear()
        self.child_status.clear()  # Clear the child status to restore statefulness

class ApplyStatChange(Action):
    def __init__(self, unit, stat_change):
        self.unit = unit
        self.stat_change = stat_change
        self.movement_left = self.unit.movement_left
        self.currenthp = self.unit.currenthp

    def do(self, gameStateObj):
        self.unit.apply_stat_change(self.stat_change)

    def reverse(self, gameStateObj):
        self.unit.apply_stat_change([-i for i in self.stat_change])
        self.unit.movement_left = self.movement_left
        self.unit.set_hp(self.currenthp)

class ChangeStat(Action):
    def __init__(self, unit, stat, amount):
        self.unit = unit
        self.stat = stat
        self.amount = int(amount)

    def do(self, gameStateObj):
        if self.stat in self.unit.stats:
            class_info = ClassData.class_dict[self.unit.klass]
            index = list(self.unit.stats.keys()).index(self.stat)
            stat_max = class_info['max'][index]
            stat_value = self.unit.stats[self.stat].base_stat
            self.amount = Utility.clamp(self.amount, -stat_value, stat_max - stat_value)
            self.unit.stats[self.stat].base_stat += self.amount

    def reverse(self, gameStateObj):
        if self.stat in self.unit.stats:
            self.unit.stats[self.stat].base_stat -= self.amount

class ApplyGrowthMod(Action):
    def __init__(self, unit, growth_mod):
        self.unit = unit
        self.growth_mod = growth_mod

    def do(self, gameStateObj):
        self.unit.apply_growth_mod(self.growth_mod)

    def reverse(self, gameStateObj):
        self.unit.apply_growth_mod([-i for i in self.growth_mod])

class ChangeStatusCount(Action):
    def __init__(self, status, new_count):
        self.status = status
        self.old_count = status.count
        self.new_count = new_count

    def do(self, gameStateObj=None):
        self.status.count = self.new_count

    def reverse(self, gameStateObj=None):
        self.status.count = self.old_count

class DecrementStatusTime(Action):
    def __init__(self, status):
        self.status = status

    def do(self, gameStateObj=None):
        self.status.time.decrement()

    def reverse(self, gameStateObj=None):
        self.status.time.increment()

class ChargeAllSkills(Action):
    def __init__(self, unit, new_charge=None):
        self.unit = unit
        self.old_charge = []
        self.new_charge = []
        for status in self.unit.status_effects:
            for component in status.components.values():
                if isinstance(component, ActiveSkill.ChargeComponent):
                    self.old_charge.append(component.current_charge)
                    if new_charge:
                        expr = new_charge
                    else:
                        expr = GC.EQUATIONS.get_expression(component.charge_method, self.unit)
                    self.new_charge.append(expr)
                    break
            else:
                self.old_charge.append(0)
                self.new_charge.append(0)

    def do(self, gameStateObj):
        for idx, status in enumerate(self.unit.status_effects):
            for component in status.components.values():
                if isinstance(component, ActiveSkill.ChargeComponent):
                    component.increase_charge(self.unit, self.new_charge[idx])
                    break

    def reverse(self, gameStateObj):
        for idx, status in enumerate(self.unit.status_effects):
            for component in status.components.values():
                if isinstance(component, ActiveSkill.ChargeComponent):
                    component.current_charge = self.old_charge[idx]

class ResetCharge(Action):
    def __init__(self, status):
        self.status = status
        self.old_charge = 0  # Placeholder -- updated by do()

    def do(self, gameStateObj):
        for component in self.status.components.values():
            if isinstance(component, ActiveSkill.ChargeComponent):
                self.old_charge = component.current_charge
                component.reset_charge()
                break

    def reverse(self, gameStateObj):
        for component in self.status.components.values():
            if isinstance(component, ActiveSkill.ChargeComponent):
                component.current_charge = self.old_charge
                break

class ShrugOff(Action):
    def __init__(self, status):
        self.status = status
        self.old_time = self.status.time.time_left

    def do(self, gameStateObj=None):
        self.status.time.time_left = 1

    def reverse(self, gameStateObj=None):
        self.status.time.time_left = self.old_time

# === TILE ACTIONS ========================================================
class ChangeTileSprite(Action):
    run_on_load = True

    def __init__(self, pos, sprite_name, size, transition):
        self.pos = pos
        self.sprite_name = sprite_name
        self.size = size
        self.transition = transition

        self.old_image_name = None

    def do(self, gameStateObj):
        if self.pos in gameStateObj.map.tile_sprites:
            self.old_image_name = gameStateObj.map.tile_sprites[self.pos].image_name
        gameStateObj.map.change_tile_sprites(self.pos, self.sprite_name, self.size, self.transition)

    def execute(self, gameStateObj):
        gameStateObj.map.change_tile_sprites(self.pos, self.sprite_name, self.size, None)

    def reverse(self, gameStateObj):
        if self.old_image_name:  # If it was previously another name
            gameStateObj.map.change_tile_sprites(self.pos, self.old_image_name, self.size, None)
        else:  # It was previously the default map
            gameStateObj.map.change_tile_sprites(self.pos, None, self.size, None)

class ReplaceTiles(Action):
    run_on_load = True

    def __init__(self, pos_list, terrain_id):
        self.pos_list = pos_list
        self.terrain_id = terrain_id

        self.old_ids = {}

    def do(self, gameStateObj):
        for position in self.pos_list:
            self.old_ids[position] = gameStateObj.map.tiles[position].tile_id
            gameStateObj.map.replace_tile(position, self.terrain_id, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        for position, tile_id in self.old_ids.items():
            gameStateObj.map.replace_tile(position, tile_id, gameStateObj.grid_manager)

class AreaReplaceTiles(Action):
    run_on_load = True

    def __init__(self, top_left_coord, image_name):
        self.top_left_coord = top_left_coord
        self.image_name = image_name

        self.old_ids = {}
 
    def do(self, gameStateObj):
        image = gameStateObj.map.loose_tile_sprites[self.image_name] 
        width = image.get_width()
        height = image.get_height()
        for x in range(self.top_left_coord[0], self.top_left_coord[0] + width):
            for y in range(self.top_left_coord[1], self.top_left_coord[1] + height):
                self.old_ids[(x, y)] = gameStateObj.map.tiles[(x, y)].tile_id
        gameStateObj.map.area_replace(self.top_left_coord, self.image_name, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        for position, tile_id in self.old_ids.items():
            gameStateObj.map.replace_tile(position, tile_id, gameStateObj.grid_manager)

class LayerTileSprite(Action):
    run_on_load = True

    def __init__(self, layer, coord, image_name):
        self.layer = layer
        self.coord = coord
        self.image_name = image_name

    def do(self, gameStateObj):
        gameStateObj.map.layer_tile_sprite(self.layer, self.coord, self.image_name)

    def reverse(self, gameStateObj):
        gameStateObj.map.layers[self.layer].remove(self.image_name, self.coord)

class LayerTerrain(Action):
    run_on_load = True

    def __init__(self, layer, coord, image_name):
        self.layer = layer
        self.coord = coord
        self.image_name = image_name

        self.old_terrain_ids = {}

    def do(self, gameStateObj):
        if self.layer < len(gameStateObj.map.terrain_layers):
            terrain_layer = gameStateObj.map.terrain_layers[self.layer]
            for position, tile in terrain_layer._tiles.items():
                self.old_terrain_ids[position] = tile.tile_id
        gameStateObj.map.layer_terrain(self.layer, self.coord, self.image_name, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        terrain_layer = gameStateObj.map.terrain_layers[self.layer]
        terrain_layer.reset(self.old_terrain_ids)
        # Make sure this works right
        if terrain_layer.show:
            gameStateObj.map.true_tiles = None  # Reset tiles if we made changes while showing
            gameStateObj.map.true_opacity_map = None
            if gameStateObj.grid_manager:
                gameStateObj.map.handle_grid_manager_with_layer(self.layer, gameStateObj.grid_manager)

class ShowLayer(Action):
    run_on_load = True

    def __init__(self, layer, transition):
        self.layer = layer
        self.transition = transition

    def do(self, gameStateObj):
        gameStateObj.map.show_layer(self.layer, self.transition, gameStateObj.grid_manager)

    def execute(self, gameStateObj):
        gameStateObj.map.show_layer(self.layer, None, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        gameStateObj.map.hide_layer(self.layer, None, gameStateObj.grid_manager)

class HideLayer(Action):
    run_on_load = True

    def __init__(self, layer, transition):
        self.layer = layer
        self.transition = transition

    def do(self, gameStateObj):
        gameStateObj.map.hide_layer(self.layer, self.transition, gameStateObj.grid_manager)

    def execute(self, gameStateObj):
        gameStateObj.map.hide_layer(self.layer, None, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        gameStateObj.map.show_layer(self.layer, None, gameStateObj.grid_manager)

class ClearLayer(Action):
    run_on_load = True

    # Assume layer is hidden !!!
    def __init__(self, layer):
        self.layer = layer

        self.old_sprites = []
        self.old_terrain_ids = {}

    def do(self, gameStateObj):
        for sprite in gameStateObj.map.layers[self.layer]:
            self.old_sprites.append((sprite.position, sprite.image_name))
        for position, tile in gameStateObj.map.terrain_layers[self.layer]._tiles.items():
            self.old_terrain_ids[position] = tile.tile_id
        gameStateObj.map.clear_layer(self.layer)

    def reverse(self, gameStateObj):
        for position, image_name in self.old_sprites:
            gameStateObj.map.layer_terrain(self.layer, position, image_name, gameStateObj.grid_manager)
        gameStateObj.map.terrain_layers[self.layer].reset(self.old_terrain_ids)

class AddTileProperty(Action):
    run_on_load = True

    def __init__(self, coord, tile_property):
        self.coord = coord
        self.tile_property = tile_property  # Already split

    def do(self, gameStateObj):
        gameStateObj.map.add_tile_property(self.coord, self.tile_property, gameStateObj)

    def reverse(self, gameStateObj):
        gameStateObj.map.remove_tile_property_from_name(self.coord, self.tile_property[0])

class RemoveTileProperty(Action):
    run_on_load = True

    def __init__(self, coord, tile_property_name):
        self.coord = coord
        self.tile_property_name = tile_property_name
        self.tile_property_value = None

    def do(self, gameStateObj):
        self.tile_property_value = gameStateObj.map.tile_info_dict[self.coord][self.tile_property_name]
        gameStateObj.map.remove_tile_property_from_name(self.coord, self.tile_property_name)

    def reverse(self, gameStateObj):
        tile_property = (self.tile_property_name, self.tile_property_value)
        gameStateObj.map.add_tile_property(self.coord, tile_property, gameStateObj)

class AddWeather(Action):
    run_on_load = True

    def __init__(self, weather):
        self.weather = weather

    def do(self, gameStateObj):
        gameStateObj.map.add_weather(self.weather)

    def reverse(self, gameStateObj):
        gameStateObj.map.remove_weather(self.weather)

class RemoveWeather(Action):
    run_on_load = True

    def __init__(self, weather):
        self.weather = weather

    def do(self, gameStateObj):
        gameStateObj.map.remove_weather(self.weather)

    def reverse(self, gameStateObj):
        gameStateObj.map.add_weather(self.weather)

class AddGlobalStatus(Action):
    # run_on_load = True

    def __init__(self, status):
        self.status = status

    def do(self, gameStateObj):
        gameStateObj.map.add_global_status(self.status, gameStateObj)

    def reverse(self, gameStateObj):
        gameStateObj.map.remove_global_status(self.status, gameStateObj)

class RemoveGlobalStatus(Action):
    # run_on_load = True

    def __init__(self, status):
        self.status = status

    def do(self, gameStateObj):
        gameStateObj.map.remove_global_status(self.status, gameStateObj)

    def reverse(self, gameStateObj):
        gameStateObj.map.add_global_status(self.status, gameStateObj)

# === Master Functions for adding to action log ===
def do(action, gameStateObj):
    gameStateObj.action_log.action_depth += 1
    action.do(gameStateObj)
    gameStateObj.action_log.action_depth -= 1
    if gameStateObj.action_log.record and gameStateObj.action_log.action_depth <= 0:
        gameStateObj.action_log.append(action)

def execute(action, gameStateObj):
    gameStateObj.action_log.action_depth += 1
    action.execute(gameStateObj)
    gameStateObj.action_log.action_depth -= 1
    if gameStateObj.action_log.record and gameStateObj.action_log.action_depth <= 0:
        gameStateObj.action_log.append(action)

def reverse(action, gameStateObj):
    gameStateObj.action_log.action_depth += 1
    action.reverse(gameStateObj)
    gameStateObj.action_log.action_depth -= 1
    if gameStateObj.action_log.record and gameStateObj.action_log.action_depth <= 0:
        gameStateObj.action_log.remove(action)
