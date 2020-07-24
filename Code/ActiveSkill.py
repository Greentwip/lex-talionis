import enum

from . import ItemMethods

import logging
logger = logging.getLogger(__name__)

class ItemModComponent(object):
    def __init__(self, uid, conditional, effect_add=None, effect_change=None):
        self.uid = uid
        self.conditional = conditional
        self.effect_add = effect_add
        self.effect_change = effect_change

    def add_effect(self, item, gameStateObj):
        command = 'item.' + self.effect_add[0] + '.' + self.effect_add[1]
        logger.debug("Execute Command %s", command)
        exec(command)

    def reverse_effect(self, item, gameStateObj):
        command = 'item.' + self.effect_add[0] + '.' + self.effect_add[2]
        logger.debug("Execute Command %s", command)
        exec(command)

    def change_effect(self, item, gameStateObj):
        for i in range(len(self.effect_change)//2):
            orig_val = item[self.effect_change[i*2]]
            val = eval(self.effect_change[i*2 + 1], locals(), globals())
            logger.debug('Set %s to %s', self.effect_change[i*2], val)
            item['orig_' + self.effect_change[i*2]] = orig_val
            item[self.effect_change[i*2]] = val

    def change_effect_back(self, item, gameStateObj):
        for i in range(len(self.effect_change)//2):
            orig_val = item['orig_' + self.effect_change[i*2]]
            logger.debug('Set %s to %s', self.effect_change[i*2], orig_val)
            item[self.effect_change[i*2]] = orig_val

    def add_and_change_effect(self, item, gameStateObj):
        for i in range(len(self.effect_change)//2):
            orig_val = item[self.effect_change[i*2]]
            if orig_val:
                self.add_effect(item, gameStateObj)
            else:
                val = eval(self.effect_change[i*2 + 1], locals(), globals())
                logger.debug('Set %s to %s', self.effect_change[i*2], val)
                if orig_val is None:
                    # Need a non-null thing to save value as
                    item['orig_' + self.effect_change[i*2]] = 'None'  
                else:
                    item['orig_' + self.effect_change[i*2]] = orig_val
                item[self.effect_change[i*2]] = val

    def add_and_change_effect_back(self, item, gameStateObj):
        for i in range(len(self.effect_change)//2):
            # If we "changed" the value of this component
            orig_val = item['orig_' + self.effect_change[i*2]]
            if orig_val:
                if orig_val == 'None':
                    orig_val = None
                logger.debug('Set %s to %s', self.effect_change[i*2], orig_val)
                item[self.effect_change[i*2]] = orig_val
            else:
                self.reverse_effect(item, gameStateObj)

    def apply_mod(self, item, gameStateObj):
        self.reverse_mod(item, gameStateObj)
        if eval(self.conditional, locals()):
            item[self.uid] = True
            if self.effect_add and self.effect_change:
                self.add_and_change_effect(item, gameStateObj)
            elif self.effect_change:
                self.change_effect(item, gameStateObj)
            elif self.effect_add:
                self.add_effect(item, gameStateObj)
                
    def reverse_mod(self, item, gameStateObj):
        if item[self.uid]:
            item[self.uid] = False
            if self.effect_add and self.effect_change:
                self.add_and_change_effect_back(item, gameStateObj)
            elif self.effect_change:
                self.change_effect_back(item, gameStateObj)
            elif self.effect_add:
                self.reverse_effect(item, gameStateObj)

class ChargeComponent(object):
    def __init__(self, charge_method, charge_max):
        self.charge_method = charge_method
        self.current_charge = 0
        self.charge_max = charge_max

    def check_charged(self):
        return self.current_charge >= self.charge_max

    def reset_charge(self):
        self.current_charge = 0

    def set_to_max(self):
        self.current_charge = self.charge_max

    def get_max(self):
        return self.charge_max

    def increase_charge(self, unit, inc):
        self.current_charge += inc
        if self.check_charged():
            self.current_charge = self.charge_max
        logger.debug('%s increased charge to %s', self, self.current_charge)

    def decrease_charge(self, unit, dec):
        self.current_charge -= dec
        if self.current_charge < 0:
            self.current_charge = 0
        logger.debug('%s decreased charge to %s', self, self.current_charge)

# Charged means that the player does not control when the charge will be activated
# Activated Means that the player controls when the charge will be activated and reset to 0
# Percent Means there is a random chance in combat for the ability to activate
# 
# "charged" status -> Metamagic
# "activated" status (unreversible) / could just be activated item -> Rage
# "percent" status -> Pavise (resistance)
#                     Ignis (stat_change)
#                     Armsthrift (?)                      
#                     Despoil (call event) (needs trigger)
#                     Vengeance (mt)
#                     Miracle (enemy item mod) (needs trigger)
# "activated" item -> Heal, Shove, Rally
# "activated" item mod (could be status/but reversible) -> Luna, True Strike, Critical, Sol
# "percent" item mod (could be status) -> Luna, Lethality, True Strike, Devil Axe
# "charged" item mod -> NA
# "charged" item -> NA
# "percent" item -> NA
# How does Lex Talionis Miracle fit in?
# Do percent skills activate for all attack automatically? No they activate for one attack only
# Or do percent skills only activate for one phase YES
# Do percent skills only activate when you are going to hit? Depends on game -- Here NO
# Do percent skills activate on crits? YES
# Percent skills can have animations that replace Attack animation (Critical?)
# or percent skills can have animations that just add before the normal Attack animation (Pavise)
# Same with activated item mods

# Combat Arts (Activated Statuses that are reversible)
# Generally should be lost on interact but don't have to be
# Can also be automatic (like Metamagic) in which automatically activated on upkeep

# Proc (Percent-based status activations) -- always removed after the combat round
# Adept/Brave re-trigger effect

# Charged Item/Action (When fully charged, unit gains access to this item or action)
# Removed after use

class Mode(enum.Enum):
    ACTIVATED = 1
    AUTOMATIC = 2

class CombatArtComponent(ChargeComponent):
    def __init__(self, mode, status_id, valid_weapons_func, check_valid_func, 
                 charge_method, charge_max):
        self.mode = mode  # Activated vs Automatic
        ChargeComponent.__init__(self, charge_method, charge_max)
        self.status_id = status_id
        self.valid_weapons_func = valid_weapons_func
        self.check_valid_func = check_valid_func

    def is_activated(self):
        return self.mode == Mode.ACTIVATED

    def is_automatic(self):
        return self.mode == Mode.AUTOMATIC

    def valid_weapons(self, unit, weapons):
        return eval(self.valid_weapons_func, locals())

    def check_valid(self, unit, gameStateObj):
        return eval(self.check_valid_func, locals())

    def basic_check(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons(unit, [i for i in unit.items if i.weapon and unit.canWield(i) and unit.canUse(i)])
        for weapon in valid_weapons:
            if unit.getValidTargetPositions(gameStateObj, weapon):
                return True
        return False

class ActivatedItemComponent(ChargeComponent):
    def __init__(self, item_id, check_valid_func, get_choices_func,
                 charge_method, charge_max, can_still_act=False):
        ChargeComponent.__init__(self, charge_method, charge_max)
        self.can_still_act = can_still_act
        self.item = ItemMethods.itemparser(item_id)
        self.check_valid_func = check_valid_func
        self.get_choices_func = get_choices_func

    def check_valid(self, unit, gameStateObj):
        return eval(self.check_valid_func, locals())

    def get_choices(self, unit, gameStateObj):
        return eval(self.get_choices_func, locals())

class ProcComponent(object):
    def __init__(self, status_id, proc_rate='SKL', priority=10):
        self.status_id = status_id
        self.rate = proc_rate
        self.priority = priority
