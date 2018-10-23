# Actions
# All permanent changes to game state are reified as actions.

try:
    import GlobalConstants as GC
    import configuration as cf
    import StatusObject, Banner, LevelUp
    import Utility
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import StatusObject, Banner, LevelUp
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
    def __init__(self, unit, new_pos, path=None):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos
        self.path = path

    def do(self, gameStateObj):
        gameStateObj.moving_units.add(self.unit)
        self.unit.lock_active()
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
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.old_pos
        self.unit.arrive(gameStateObj)

class ArriveOnMap(Action):
    pass

class LeaveMap(Action):
    pass

class Warp(Action):
    pass

class Wait(Action):
    def __init__(self, unit):
        self.unit = unit
        self.hasMoved = self.unit.hasMoved
        self.hasTraded = self.unit.hasTraded
        self.hasAttacked = self.unit.hasAttacked
        self.finished = self.unit.finished
        self.previous_position = self.unit.previous_position

    def do(self, gameStateObj):
        self.unit.hasMoved = True
        self.unit.hasTraded = True
        self.unit.hasAttacked = True
        self.unit.finished = True
        self.unit.previous_position = self.unit.position

    def reverse(self, gameStateObj):
        self.unit.hasMoved = self.hasMoved
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.unit.finished = self.finished
        self.unit.previous_position = self.previous_position

class Refresh(Action):
    def __init__(self, unit):
        self.unit = unit
        self.hasMoved = self.unit.hasMoved
        self.hasTraded = self.unit.hasTraded
        self.hasAttacked = self.unit.hasAttacked
        self.finished = self.unit.finished
        self.hasRunMoveAI = self.unit.hasRunMoveAI
        self.hasRunAttackAI = self.unit.hasRunAttackAI
        self.hasRunGeneralAI = self.unit.hasRunGeneralAI

    def do(self, gameStateObj):
        self.unit.reset()

    def reverse(self, gameStateObj):
        self.unit.hasMoved = self.hasMoved
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.unit.finished = self.finished
        self.unit.hasRunMoveAI = self.hasRunMoveAI
        self.unit.hasRunAttackAI = self.hasRunAttackAI
        self.unit.hasRunGeneralAI = self.hasRunGeneralAI

class CantoMove(Action):
    pass

# === RESCUE ACTIONS ==========================================================
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
        self.hasTraded = self.unit.hasTraded

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
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = False
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
        self.hasTraded = self.unit.hasTraded

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
        self.unit.hasTraded = self.hasTraded
        if 'savior' not in self.other_unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.other_unit, gameStateObj)
        self.unit.unrescue()

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

class DropItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self, gameStateObj):
        self.item.droppable = False
        self.unit.add_item(self.item)
        gameStateObj.banners.append(Banner.acquiredItemBanner(self.unit, self.item))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        self.item.droppable = False
        self.unit.add_item(self.item)

    def reverse(self, gameStateObj):
        self.item.droppable = True
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

class RemoveItem(DiscardItem):
    def do(self, gameStateObj):
        self.unit.remove_item(self.item)

    def reverse(self, gameStateObj):
        self.unit.insert_item(self.item_index, self.item)

class EquipItem(Action):
    """
    Assumes item is already in invetory
    """
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.old_idx = self.unit.items.index(self.item)

    def do(self, gameStateObj):
        self.unit.equip(self.item)

    def reverse(self, gameStateObj):
        self.unit.insert_item(self.old_idx, self.item)

class TradeItem(Action):
    def __init__(self, unit1, unit2, item1, item2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.item1 = item1
        self.item2 = item2
        self.item_index1 = unit1.items.index(item1)
        self.item_index2 = unit2.items.index(item2)

    def swap(self, unit1, unit2, item1, item2, item_index1, item_index2):
        # Do the swap
        if item1 and item1 is not "EmptySlot":
            unit1.remove_item(item1)
            unit2.insert_item(item_index2, item1)
        if item2 and item2 is not "EmptySlot":
            unit2.remove_item(item2)
            unit1.insert_item(item_index1, item2)   

    def do(self, gameStateObj):
        self.swap(self.unit1, self.unit2, self.item1, self.item2, self.item_index1, self.item_index2)

    def reverse(self, gameStateObj):
        self.swap(self.unit1, self.unit2, self.item2, self.item1, self.item_index2, self.item_index1)

class UseItem(Action):
    """
    Doesn't actually fully USE the item, just reduces the number of uses
    """
    def __init__(self, item):
        self.item = item

    def do(self, gameStateObj):
        if self.item.uses:
            self.item.uses.decrement()
        if self.item.c_uses:
            self.item.c_uses.decrement()

    def reverse(self, gameStateObj):
        if self.item.uses:
            self.item.uses.increment()
        if self.item.c_uses:
            self.item.c_uses.increment()

class GainExp(Action):
    def __init__(self, unit, exp):
        self.unit = unit
        self.exp_amount = exp
        self.old_exp = self.unit.exp
        self.current_stats = self.stats.items()

        self.promoted_to = None
        self.current_class = self.unit.klass

        self.current_skills = [s.id for s in self.unit.status_effects]
        self.added_skills = []  # Determined on reverse

        self.old_level = self.unit.level

    def forward_class_change(self, gameStateObj, promote=True):
        old_klass = gameStateObj.metaDataObj['class_dict'][self.current_class]
        new_klass = gameStateObj.metaDataObj['class_dict'][self.promoted_to]
        self.unit.leave(gameStateObj)
        self.unit.klass = self.promoted_to
        self.unit.removeSprites()
        self.unit.loadSprites()
        if promote:
            self.unit.level = 1
            self.levelup_list = new_klass['promotion']
            for index, stat in enumerate(self.levelup_list):
                self.levelup_list[index] = min(stat, new_klass['max'][index] - self.current_stats[index][1].base_stat)
            self.unit.apply_levelup(self.levelup_list)
            self.unit.increase_wexp(new_klass['wexp_gain'], gameStateObj, banner=False)
        self.unit.movement_group = new_klass['movement_group']
        # Handle tags
        if old_klass['tags']:
            self.unit.tags -= old_klass['tags']
        if new_klass['tags']:
            self.unit.tags |= new_klass['tags']
        self.unit.arrive(gameStateObj)

    def reverse_class_change(self, gameStateObj, promote=True):
        old_klass = gameStateObj.metaDataObj['class_dict'][self.current_class]
        new_klass = gameStateObj.metaDataObj['class_dict'][self.promoted_to]
        self.unit.leave(gameStateObj)
        self.unit.klass = self.current_class
        self.unit.removeSprites()
        self.unit.loadSprites()
        if promote:
            self.unit.level = self.old_level
            self.unit.apply_levelup([-x for x in self.levelup_list])
            self.unit.increase_wexp([-x for x in new_klass['wexp_gain']], gameStateObj, banner=False)
        self.unit.movement_group = old_klass['movement_group']
        # Handle tags
        if new_klass['tags']:
            self.unit.tags -= new_klass['tags']
        if old_klass['tags']:
            self.unit.tags |= old_klass['tags']
        self.unit.arrive(gameStateObj)

    def do(self, gameStateObj):
        gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.unit, exp=self.exp_amount))
        gameStateObj.stateMachine.changeState('expgain')

    def execute(self, gameStateObj):
        if self.exp_amount + self.unit.exp >= 100:
            klass_dict = gameStateObj.metaDataObj['class_dict'][self.unit.klass]
            max_level = Utility.find_max_level(klass_dict['tier'], cf.CONSTANTS['max_level'])
            # Level Up
            if self.unit.level >= max_level:
                if cf.CONSTANTS['auto_promote'] and klass_dict['turns_into']: # If has at least one class to turn into
                    self.forward_class_change(gameStateObj, True)
                else:
                    self.unit.exp = 99
            else:
                self.unit.exp = (self.unit.exp + self.exp_amount)%100
                self.unit.level += 1
                self.unit.apply_levelup(self.levelup_list)
                # If we don't already have this skill
                for skill in self.added_skills:
                    if skill.stack or skill.id not in (s.id for s in self.unit.status_effects):
                        StatusObject.HandleStatusAddition(skill, self.unit, gameStateObj)

        else:
            self.unit.exp += self.exp_amount

    def reverse(self, gameStateObj):
        if self.unit.exp < self.exp_amount: # Leveled up
            klass_dict = gameStateObj.metaDataObj['class_dict'][self.current_class]
            max_level = Utility.find_max_level(klass_dict['tier'], cf.CONSTANTS['max_level'])
            if self.unit.level == 1:  # Promoted here
                self.reverse_class_change(gameStateObj, True)
            elif self.unit.level >= max_level and self.unit.exp >= 99:
                self.unit.exp = self.unit.old_exp
            else:
                self.unit.exp = 100 - self.exp_amount + self.unit.exp
                self.unit.level -= 1
                self.unit.apply_levelup([-x for x in self.levelup_list])
                # If we don't already have this skill
                for skill in self.added_skills:
                    StatusObject.HandleStatusRemoval(skill, self.unit, gameStateObj)
        else:
            self.unit.exp -= self.exp_amount

class ChangeHP(Action):
    def __init__(self, unit, num):
        self.unit = unit
        self.num = num
        self.old_hp = self.unit.currenthp

    def do(self, gameStateObj):
        self.unit.change_hp(self.num)

    def reverse(self, gameStateObj):
        self.unit.set_hp(self.old_hp)

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

    def execute(self, gameStateObj):
        self.unit.isDying = False
        self.unit.set_hp(1)
        for status in self.unit.status_effects:
            if status.miracle and status.count and status.count.count > 0:
                status.count.count -= 1
                break

    def reverse(self, gameStateObj):
        self.unit.isDying = True
        self.unit.set_hp(self.old_hp)
        for status in self.unit.status_effects:
            if status.miracle and status.count:
                status.count.count += 1
                break

class Die(Action):
    pass

class Resurrect(Action):
    pass

class ApplyStatus(Action):
    def __init__(self, unit, status_obj):
        self.unit = unit
        self.status_obj = status_obj
        self.actually_added = True

    def do(self, gameStateObj):
        if not StatusObject.HandleStatusAddition(self.status_obj, self.unit, gameStateObj):
            self.actually_added = False

    def reverse(self, gameStateObj):
        if self.actually_added:
            StatusObject.HandleStatusRemoval(self.status_obj, self.unit, gameStateObj)

class RemoveStatus(Action):
    pass

# === GENERAL ACTIONS =========================================================
class ChangeTeam(Action):
    def __init__(self, unit, new_team):
        self.unit = unit
        self.new_team = new_team
        self.old_team = self.unit.team

    def _change_team(self, team, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.team = team
        gameStateObj.boundary_manager.reset_unit(self.unit)
        self.unit.loadSprites()
        self.unit.reset()
        self.unit.arrive(gameStateObj)

    def do(self, gameStateObj):
        self._change_team(self.new_team, gameStateObj)
        
    def reverse(self, gameStateObj):
        self._change_team(self.old_team, gameStateObj)

class ChangeAI(Action):
    def __init__(self, unit, new_ai):
        self.unit = unit
        self.old_ai = self.unit.ai_descriptor
        self.new_ai = new_ai

    def do(self, gameStateObj):
        self.unit.ai_descriptor = self.new_ai
        self.unit.get_ai(self.new_ai)

    def reverse(self, gameStateObj):
        self.unit.ai_descriptor = self.old_ai
        self.unit.get_ai(self.old_ai)

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

class ChangeGameConstant(Action):
    def __init__(self, constant, old_value, new_value):
        self.constant = constant
        self.old_value = old_value
        self.new_value = new_value

    def do(self, gameStateObj):
        gameStateObj.game_constants[self.constant] = self.new_value

    def reverse(self, gameStateObj):
        gameStateObj.game_constants[self.constant] = self.old_value        

class ChangeLevelConstant(Action):
    def __init__(self, constant, old_value, new_value):
        self.constant = constant
        self.old_value = old_value
        self.new_value = new_value

    def do(self, gameStateObj):
        gameStateObj.level_constants[self.constant] = self.new_value

    def reverse(self, gameStateObj):
        gameStateObj.level_constants[self.constant] = self.old_value

class AddTag(Action):
    def __init__(self, unit, new_tag):
        self.unit = unit
        self.new_tag = new_tag
        self.already_present = new_tag in unit.tags

    def do(self, gameStateObj):
        if not self.already_present:
            self.unit.tags.add(self.new_tag)

    def reverse(self, gameStateObj):
        if not self.already_present:
            self.unit.tags.remove(self.new_tag)

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
    pass

# === TILE ACTIONS ========================================================
class ChangeTileSprite(Action):
    pass

class ChangeTerrain(Action):
    pass

class LayerTileSprite(Action):
    pass

class LayerTerrain(Action):
    pass

class Destroy(Action):
    pass

class ShowLayer(Action):
    pass

class HideLayer(Action):
    pass

class SetTileInfo(Action):
    pass

# === SUPPORT ACTIONS =======================================================
class IncrementSupportLevel(Action):
    pass

class ActivateSupport(Action):
    pass

class InteractionCleanup(Action):
    pass

class UpdateAttackStatistics(Action):
    pass

class AutomaticSkillCharged(Action):
    def __init__(self, status, unit):
        self.status = status
        self.unit = unit
        self.current_charge = status.automatic.current_charge

    def do(self, gameStateObj):
        self.s = StatusObject.statusparser(self.status.automatic.status)
        StatusObject.HandleStatusAddition(self.s, self.unit, gameStateObj)
        self.status.automatic.reset_charge()

    def reverse(self, gameStateObj):
        StatusObject.HandleStatusRemoval(self.s, self.unit, gameStateObj)
        self.status.automatic.current_charge = self.current_charge

# === Master Functions for adding to action log ===
def do(action, gameStateObj):
    action.do(gameStateObj)
    gameStateObj.action_log.append(action)

def execute(action, gameStateObj):
    action.execute(gameStateObj)
    gameStateObj.action_log.append(action)
