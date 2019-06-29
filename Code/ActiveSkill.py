try:
    import ItemMethods, Utility, Weapons
except ImportError:
    from . import ItemMethods, Utility, Weapons

import logging
logger = logging.getLogger(__name__)

class Critical(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = "Attack"

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons(unit, [item for item in unit.items if item.weapon])
        # Needs to be done this way to handle the case where you have a weapon that can crit
        # and a weapon that can't crit, but only the weapon that can't crit can reach an enemy unit
        if not unit.hasAttacked:
            for weapon in valid_weapons:
                if unit.getValidTargetPositions(gameStateObj, weapon):
                    return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.orig_crit = weapon.crit
        weapon.guaranteed_crit = True

    def reverse_mod(self):
        self.item.guaranteed_crit = self.orig_crit
        self.item = None

    def valid_weapons(self, unit, weapons):
        return [weapon for weapon in weapons if not weapon.magic]

class Charge(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons(unit, [item for item in unit.items if item.weapon])
        if not unit.hasAttacked:
            for weapon in valid_weapons:
                # Essentially get valid targets
                enemy_positions = [u.position for u in gameStateObj.allunits if self.checkIfEnemy(u)] + \
                                  [position for position, tile in gameStateObj.map.tiles.items() if 'HP' in gameStateObj.map.tile_info_dict[position]]
                if any(Utility.calculate_distance(position, unit.position) == 1 for position in enemy_positions):
                    return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        # Reverse previous changes to item. As it is not the currently selected weapon...
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.original_range = weapon.RNG
        self.original_might = weapon.weapon.MT
        previous_position = gameStateObj.action_log.get_previous_position(unit)
        weapon.weapon.MT += 2*Utility.calculate_distance(unit.position, previous_position)
        weapon.RNG = ['1']

    def reverse_mod(self):
        self.item.weapon.MT = self.original_might
        self.item.RNG = self.original_range
        self.item = None

    def valid_weapons(self, unit, weapons):
        return [weapon for weapon in weapons if weapon.TYPE == 'Lance' and 1 in weapon.get_range(unit)]

class Knock_Out(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons(unit, [item for item in unit.items if item.weapon])
        if not unit.hasAttacked:
            for weapon in valid_weapons:
                if unit.getValidTargetPositions(gameStateObj, weapon):
                    return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.s_id = 'Stun'
        weapon.status.append(self.s_id)

    def reverse_mod(self):
        self.item.status.remove(self.s_id)
        self.item = None

    def valid_weapons(self, unit, weapons):
        return [weapon for weapon in weapons if weapon.TYPE in ('Axe', 'Lance', 'Sword', 'Bow')]

class Twin_Strike(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        if unit.canAttack(gameStateObj):
            return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.orig_brave = weapon.brave
        weapon.brave = True

    def reverse_mod(self):
        self.item.brave = self.orig_brave
        self.item = None

class Cleave(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons(unit, [item for item in unit.items if item.weapon])
        if not unit.hasAttacked and valid_weapons:
            # Essentially get valid targets
            enemy_positions = [enemy.position for enemy in gameStateObj.allunits if enemy.position and unit.checkIfEnemy(enemy)] + \
                              [position for position, tile in gameStateObj.map.tiles.items() if 'HP' in gameStateObj.map.tile_info_dict[position]]
            if any(Utility.calculate_distance(position, unit.position) == 1 for position in enemy_positions):
                return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.original_range = weapon.RNG
        self.original_aoe = weapon.aoe
        self.original_no_double = weapon.no_double
        weapon.aoe = ItemMethods.AOEComponent('Cleave', 1)
        weapon.RNG = ['1']
        weapon.no_double = True

    def reverse_mod(self):
        self.item.aoe = self.original_aoe
        self.item.RNG = self.original_range
        self.item.no_double = self.original_no_double
        self.item = None

    def valid_weapons(self, unit, weapons):
        return [weapon for weapon in weapons if weapon.TYPE in ('Axe', 'Sword') and 1 in weapon.get_range(unit)]

class True_Strike(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        if unit.canAttack(gameStateObj):
            return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.orig_hit = weapon.weapon.HIT
        weapon.weapon.HIT += 100

    def reverse_mod(self):
        self.item.weapon.HIT = self.orig_hit
        self.item = None

class Luna(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        if unit.canAttack(gameStateObj):
            return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.orig_ignore_def = weapon.ignore_def
        weapon.ignore_def = True

    def reverse_mod(self):
        self.item.ignore_def = self.orig_ignore_def
        self.item = None

class Sol(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        if unit.canAttack(gameStateObj):
            return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.orig_lifelink = weapon.lifelink
        weapon.lifelink = True

    def reverse_mod(self):
        self.item.lifelink = self.orig_lifelink
        self.item = None

class Refresh(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Refresh')

    def check_valid(self, unit, gameStateObj):
        adj_units = unit.getTeamPartners(gameStateObj)
        if not unit.hasAttacked:
            for adj_unit in adj_units:
                if adj_unit.isDone():
                    return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj) if unit.isDone()]

class Command(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Command')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and any(ally_unit.isDone() for ally_unit in gameStateObj.allunits if ally_unit.position and unit.team == ally_unit.team):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj) if unit.isDone()]

class Heal(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Heal')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and any(Utility.calculate_distance(ally_unit.position, unit.position) == 1 and
                                        ally_unit.currenthp < ally_unit.stats['HP'] for ally_unit in gameStateObj.allunits
                                        if ally_unit.position and unit.team == ally_unit.team):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj) if unit.currenthp < unit.stats['HP']]

class Shove(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Shove')

    def check_valid(self, unit, gameStateObj):
        adj_units = unit.getAdjacentUnits(gameStateObj)
        if not unit.hasAttacked and adj_units:
            for adj_unit in adj_units:
                if adj_unit.check_shove(unit.position, 1, gameStateObj):
                    return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getAdjacentUnits(gameStateObj) if unit.check_shove(cur_unit.position, 1, gameStateObj)]

class Swap(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Swap')

    def check_valid(self, unit, gameStateObj):
        adj_units = unit.getAdjacentUnits(gameStateObj)
        if not unit.hasAttacked and adj_units:
            for adj_unit in adj_units:
                if unit.checkIfAlly(adj_unit) and self.check_swap(unit, adj_unit, gameStateObj.map.tiles):
                    return True
        return False

    def check_swap(self, unit1, unit2, tile_map):
        return tile_map[unit2.position].get_mcost(unit1) <= unit1.stats['MOV'] and \
            tile_map[unit1.position].get_mcost(unit2) <= unit2.stats['MOV']

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getAdjacentUnits(gameStateObj) if self.check_swap(cur_unit, unit, gameStateObj.map)]

class Aegis(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Aegis')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and self.get_choices(unit, gameStateObj):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj)]

class Revelation(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Revelation')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and self.get_choices(unit, gameStateObj):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj)]

class Rally(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Rally')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked:
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return None

class Summon(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Tile'
        self.item = ItemMethods.itemparser('so_Summon_1')

    def get_choices(self, summoner, gameStateObj):
        return [position for position in summoner.getAdjacentPositions(gameStateObj)
                if not any(position == a_unit.position for a_unit in gameStateObj.allunits)]

    def check_valid(self, summoner, gameStateObj):
        if not summoner.hasAttacked and self.get_choices(summoner, gameStateObj):
            return True
        return False

class Wildcall(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Tile'
        self.item = ItemMethods.itemparser('so_Summon_2')

    def already_present(self, summoner, unit):
        summon_tag = [tag for tag in unit.tags if tag.startswith('Summon_')][0]
        owner = int(summon_tag.split('_')[2])
        summon_type = summon_tag.split('_')[1]
        if owner == summoner.id and summon_type == self.item.summon.s_id:
            return True
        return False

    def get_choices(self, summoner, gameStateObj):
        return [position for position in summoner.getAdjacentPositions(gameStateObj)
                if not any(position == a_unit.position for a_unit in gameStateObj.allunits)]

    def check_valid(self, summoner, gameStateObj):
        all_summons = [unit for unit in gameStateObj.allunits if unit.position and any(tag.startswith('Summon_') for tag in unit.tags)]
        # If the unit hasn't attacked, there's a free space nearby, and there isn't already a summon of the same type on the field owned by this unit
        if not summoner.hasAttacked and self.get_choices(summoner, gameStateObj) and not any(self.already_present(summoner, unit) for unit in all_summons):
            return True
        return False

class Dash(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Solo'
        self.item = ItemMethods.itemparser('so_Refresh')

class Rage(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Solo'
        self.item = ItemMethods.itemparser('so_Rage')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and not any(status.id in ('Weakened', 'Rage_Status') for status in unit.status_effects):
            return True
        return False

class Fade(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Solo'
        self.item = ItemMethods.itemparser('so_Fade')

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and not any(status.id == 'Fade_Status' for status in unit.status_effects):
            return True
        return False

class ItemModComponent(object):
    def __init__(self, uid, conditional, effect_add=None, effect_change=None):
        self.uid = uid
        self.conditional = conditional
        self.effect_add = effect_add
        self.effect_change = effect_change

    def add_effect(self, item):
        command = 'item.' + self.effect_add[0] + '.' + self.effect_add[1]
        logger.debug("Execute Command %s", command)
        exec(command)

    def reverse_effect(self, item):
        command = 'item.' + self.effect_add[0] + '.' + self.effect_add[2]
        logger.debug("Execute Command %s", command)
        exec(command)

    def change_effect(self, item):
        orig_val = item[self.effect_change[0]]
        val = eval(self.effect_change[1])
        logger.debug('Set %s to %s', self.effect_change[0], val)
        item['orig_' + self.effect_change[0]] = orig_val
        item[self.effect_change[0]] = val

    def change_effect_back(self, item):
        orig_val = item['orig_' + self.effect_change[0]]
        logger.debug('Set %s to %s', self.effect_change[0], orig_val)
        item[self.effect_change[0]] = orig_val

    def apply_mod(self, item):
        self.reverse_mod(item)
        if eval(self.conditional):
            item[self.uid] = True
            if self.effect_add and self.effect_change:
                if item[self.effect_add[0]]:
                    self.add_effect(item)
                else:
                    self.change_effect(item)
            elif self.effect_change:
                self.change_effect(item)
            elif self.effect_add:
                self.add_effect(item)
                
    def reverse_mod(self, item):
        if item[self.uid]:
            item[self.uid] = False
            if self.effect_add and self.effect_change:
                if item['orig_' + self.effect_change[0]]:
                    self.change_effect_back(item)
                else:
                    self.reverse_effect(item)
            elif self.effect_change:
                self.change_effect_back(item)
            elif self.effect_add:
                self.reverse_effect(item)

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
# "activated" status -> Rage
# "percent" status -> Luna (item mod)
#                     Lethality (item mod)
#                     Pavise (enemy item mod)
#                     True Strike (item mod)
#                     Devil Axe (item mod)
#                     Ignis (stat_change)
#                     Armsthrift (?)                      
#                     Sol (item mod)
#                     Despoil (call event)
#                     Vengeance (mt)
#                     Miracle (enemy item mod)
class ChargedStatusComponent(ChargeComponent):
    def __init__(self, mode, status_id, charge_method, charge_max):
        self.mode = mode
        ChargeComponent.__init__(self, charge_method, charge_max)
        self.status_id = status_id

class ActivatedItemComponent(ChargeComponent):
    def __init__(self, mode, item_id, charge_method, charge_max):
        ChargeComponent.__init__(self, charge_method, charge_max)
        self.item = ItemMethods.itemparser(item_id)

class ActivatedItemModComponent(ItemModComponent, ChargeComponent):
    def __init__(self, mode, uid, charge_method, charge_max, conditional, effect_add=None, effect_change=None):
        self.uid = uid
        ChargeComponent.__init__(self, charge_method, charge_max)
        self.conditional = conditional
        self.effect_add = effect_add
        self.effect_change = effect_change

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons(unit, [item for item in unit.items if item.weapon])
        if not unit.hasAttacked:
            for weapon in valid_weapons:
                if unit.getValidTargetPositions(gameStateObj, weapon):
                    return True
        return False

    def valid_weapons(self, items):
        valid_weapons = []
        for item in items:
            if eval(self.conditional):
                valid_weapons.append(item)
        return valid_weapons
