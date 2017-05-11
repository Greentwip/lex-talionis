from GlobalConstants import *
import SaveLoad, ItemMethods, Utility, StatusObject, CustomObjects

import logging
logger = logging.getLogger(__name__)

class Active_Skill(object):
    def __init__(self, name, required_charge):
        self.name = name
        self.required_charge = required_charge
        self.mode = 'Solo'
        self.current_charge = 0
        self.item = None

    def check_valid(self, unit, gameStateObj):
        return True

    def increase_charge(self, unit):
        self.current_charge += unit.stats['SKL']
        if self.current_charge > self.required_charge:
            self.current_charge = self.required_charge

    def valid_weapons(self, weapons):
        return weapons

class Critical(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = "Attack"

    def check_valid(self, unit, gameStateObj):
        if unit.canAttack(gameStateObj):
            return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.orig_crit = weapon.crit
        weapon.crit = True

    def reverse_mod(self):
        self.item.crit = self.orig_crit
        self.item = None

class Charge(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons([item for item in unit.items if weapon.weapon])
        if not unit.hasAttacked and valid_weapons:
            enemy_positions = [unit.position for unit in gameStateObj.allunits if self.checkIfEnemy(unit)] + \
                              [position for position, tile in gameStateObj.map.tiles.iteritems() if 'HP' in gameStateObj.map.tile_info_dict[position]]
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
        weapon.weapon.MT += 2*Utility.calculate_distance(unit.position, unit.previous_position)
        weapon.RNG = [1]

    def reverse_mod(self):
        self.item.weapon.MT = self.original_might
        self.item.RNG = self.original_range
        self.item = None

    def valid_weapons(self, weapons):
        return [weapon for weapon in weapons if any(TYPE == 'Lance' for TYPE in weapon.TYPE) and 1 in weapon.RNG]

class Knock_Out(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons([item for item in unit.items if weapon.weapon])
        if unit.canAttack(gameStateObj) and valid_weapons:
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

    def valid_weapons(self, weapons):
        return [weapon for weapon in weapons if any(TYPE in ['Axe', 'Lance', 'Sword', 'Bow'] for TYPE in weapon.TYPE)]

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
        valid_weapons = self.valid_weapons([item for item in unit.items if item.weapon])
        if not unit.hasAttacked and valid_weapons:
            enemy_positions = [enemy.position for enemy in gameStateObj.allunits if enemy.position and unit.checkIfEnemy(enemy)] + \
                              [position for position, tile in gameStateObj.map.tiles.iteritems() if 'HP' in gameStateObj.map.tile_info_dict[position]]
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
        weapon.RNG = [1]
        weapon.no_double = True

    def reverse_mod(self):
        self.item.aoe = self.original_aoe
        self.item.RNG = self.original_range
        self.item.no_double = self.original_no_double
        self.item = None

    def valid_weapons(self, weapons):
        return [weapon for weapon in weapons if any(TYPE in ['Axe', 'Sword'] for TYPE in weapon.TYPE) and 1 in weapon.RNG]

class Metamagic(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Attack'

    def check_valid(self, unit, gameStateObj):
        valid_weapons = self.valid_weapons([item for item in unit.items if item.weapon or item.spell])
        if not unit.hasAttacked and valid_weapons:
            return True
        return False

    def apply_mod(self, unit, weapon, gameStateObj):
        if self.item:
            self.reverse_mod()
        self.item = weapon
        self.original_aoe = weapon.aoe
        if self.original_aoe:
            weapon.aoe.num += 1
        else:
            weapon.aoe = ItemMethods.AOEComponent('Blast', 1)

    def reverse_mod(self):
        self.item.aoe = self.original_aoe
        self.item = None

    def valid_weapons(self, weapons):
        return [weapon for weapon in weapons if CustomObjects.WEAPON_TRIANGLE.isMagic(weapon) and (not weapon.aoe or weapon.aoe.mode == 'Blast')]

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
        self.item = ItemMethods.itemparser('so_Refresh')[0]

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and any(Utility.calculate_distance(ally_unit.position, unit.position) == 1 for ally_unit in gameStateObj.allunits if ally_unit.position and unit.team == ally_unit.team and ally_unit.isDone()):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj) if unit.isDone()]

class Command(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Command')[0]

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
        self.item = ItemMethods.itemparser('so_Heal')[0]

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and any(Utility.calculate_distance(ally_unit.position, unit.position) == 1 and ally_unit.currenthp < ally_unit.stats['HP'] for ally_unit in gameStateObj.allunits if ally_unit.position and unit.team == ally_unit.team):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj) if unit.currenthp < unit.stats['HP']]

class Shove(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Interact'
        self.item = ItemMethods.itemparser('so_Shove')[0]

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
        self.item = ItemMethods.itemparser('so_Swap')[0]

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
        self.item = ItemMethods.itemparser('so_Aegis')[0]

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
        self.item = ItemMethods.itemparser('so_Revelation')[0]

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and self.get_choices(unit, gameStateObj):
            return True
        return False

    def get_choices(self, cur_unit, gameStateObj):
        return [unit.position for unit in cur_unit.getTeamPartners(gameStateObj)]

class Gate(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Tile'
        self.item = ItemMethods.itemparser('so_Summon_1')[0]

    def get_choices(self, summoner, gameStateObj):
        return [position for position in summoner.getAdjacentPositions(gameStateObj) if not any(position == a_unit.position for a_unit in gameStateObj.allunits)]

    def check_valid(self, summoner, gameStateObj):
        if not summoner.hasAttacked and self.get_choices(summoner, gameStateObj):
            return True
        return False

class Wildcall(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Tile'
        self.item = ItemMethods.itemparser('so_Summon_2')[0]

    def already_present(self, summoner, unit):
        summon_tag = [tag for tag in unit.tags if tag.startswith('Summon_')][0]
        owner = int(summon_tag.split('_')[2])
        summon_type = summon_tag.split('_')[1]
        if owner == summoner.id and summon_type == self.item.summon.s_id:
            return True
        return False

    def get_choices(self, summoner, gameStateObj):
        return [position for position in summoner.getAdjacentPositions(gameStateObj) if not any(position == a_unit.position for a_unit in gameStateObj.allunits)]

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
        self.item = ItemMethods.itemparser('so_Refresh')[0]

class Rage(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Solo'
        self.item = ItemMethods.itemparser('so_Rage')[0]

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and not any(status.id in ['Weakened', 'Rage_Status'] for status in unit.status_effects):
            return True
        return False

class Fade(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Solo'
        self.item = ItemMethods.itemparser('so_Fade')[0]

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked and not any(status.id == 'Fade_Status' for status in unit.status_effects):
            return True
        return False

class Rally(Active_Skill):
    def __init__(self, name, required_charge):
        Active_Skill.__init__(self, name, required_charge)
        self.mode = 'Solo'
        self.item = ItemMethods.itemparser('so_Rally')[0]

    def check_valid(self, unit, gameStateObj):
        if not unit.hasAttacked:
            return True
        return False

# PASSIVE SKILLS
class PassiveSkill(object):
    def __init__(self, name):
        self.name = name

class Swordfaire(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if 'Sword' in item.TYPE:
            item.swordfaire = True
            item.orig_brave = item.brave
            item.brave = True

    def reverse_mod(self, item):
        if item.swordfaire:
            item.swordfaire = False
            item.brave = item.orig_brave  

class Lancefaire(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if 'Lance' in item.TYPE:
            item.lancefaire = True
            item.orig_counter = item.cannot_be_countered
            item.cannot_be_countered = True

    def reverse_mod(self, item):
        if item.lancefaire:
            item.lancefaire = False
            item.cannot_be_countered = item.orig_counter

class Axefaire(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if 'Axe' in item.TYPE:
            item.axefaire = True
            item.orig_ignore_half_def = item.ignore_half_def
            item.ignore_half_def = True

    def reverse_mod(self, item):
        if item.axefaire:
            item.axefaire = False
            item.ignore_half_def = item.orig_ignore_half_def

class Longshot(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if 'Bow' in item.TYPE:
            item.longshot = True
            item.orig_RNG = item.RNG[:]
            item.RNG.append(max(item.RNG) + 1)

    def reverse_mod(self, item):
        if item.longshot:
            item.longshot = False
            item.RNG = item.orig_RNG

class Celeste(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if item.weapon:
            item.status.append('Weakened')
            item.celeste = True

    def reverse_mod(self, item):
        if item.celeste:
            item.celeste = False
            item.status = [s_id for s_id in item.status if s_id != 'Weakened']

class Immobilize(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if item.weapon:
            item.status.append('Immobilized')
            item.immobilize = True

    def reverse_mod(self, item):
        if item.immobilize:
            item.immobilize = False
            item.status = [s_id for s_id in item.status if s_id != 'Immobilized']

class Slow(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if item.weapon:
            item.status.append('Slowed')
            item.slow = True

    def reverse_mod(self, item):
        if item.slow:
            item.slow = False
            item.status = [s_id for s_id in item.status if s_id != 'Slowed']

class Nosferatu(PassiveSkill):
    def apply_mod(self, item):
        self.reverse_mod(item)
        if 'Dark' in item.TYPE:
            item.nosferatu = True
            item.old_lifelink = item.lifelink
            item.lifelink = True

    def reverse_mod(self, item):
        if item.nosferatu:
            item.lifelink = item.old_lifelink
            item.nosferatu = False

# AURAS
class Aura(object):
    def __init__(self, aura_range, target, child):
        self.aura_range = int(aura_range)
        self.child = child
        self.target = target
        self.children = []

    def remove_child(self, affected_unit):
        logger.debug("Aura parent is removing a child.")
        l_c = len(self.children)
        self.children = [u_id for u_id in self.children if u_id is not affected_unit.id]
        if l_c == len(self.children):
            print("Remove Child did not work!", affected_unit.name, affected_unit.position)
            print(self.children)

    def apply(self, parent_unit, unit, gameStateObj):
        if (self.target == 'Ally' and parent_unit.checkIfAlly(unit) and parent_unit is not unit) or \
           (self.target == 'Enemy' and parent_unit.checkIfEnemy(unit)) or \
           (self.target == 'Weakened_Enemy' and parent_unit.checkIfEnemy(unit) and unit.currenthp < unit.stats['HP']/2):
            child_status = StatusObject.statusparser(self.child)
            child_status.parent_status = self
            child_status.parent_id = parent_unit.id
            success = StatusObject.HandleStatusAddition(child_status, unit, gameStateObj)
            if success:
                self.children.append(unit.id)
                logger.debug('Applying Aura %s to %s at %s', child_status.name, unit.name, unit.position)