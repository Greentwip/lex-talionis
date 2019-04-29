try:
    import configuration as cf
    import static_random
    import UnitObject, TileObject, Action
    import StatusObject, SaveLoad, Utility
except ImportError:
    from . import configuration as cf
    from . import static_random
    from . import UnitObject, TileObject, Action
    from . import StatusObject, SaveLoad, Utility

import logging
logger = logging.getLogger(__name__)

class Result(object):
    def __init__(self, attacker, defender):
        self.attacker = attacker  # Which phase this belongs to (actual reference to unit)
        self.defender = defender  # Who this is affecting
        self.outcome = 0  # 0 -- Miss, 1 -- Hit, 2 -- Crit
        self.atk_damage = 0  # Damage to the attacker
        self.def_damage = 0  # Damage to the defender
        self.def_damage_done = 0  # Actual damage done to the defender (could be less than damage if the enemy's health is low)
        self.atk_status = []  # Status to the attacker
        self.def_status = []  # Status to the defender
        self.atk_movement = None  # Movement to the attacker
        self.def_movement = None  # Movement to the defender
        self.summoning = None

# Does not check legality of attack, that is for other functions to do. 
# Assumes attacker can attack all defenders using item and skill
class Solver(object):
    def __init__(self, attacker, defender, def_pos, splash, item, skill_used, event_combat=None):
        self.attacker = attacker
        self.defender = defender
        self.def_pos = def_pos
        # Have splash damage spiral out from position it started on...
        self.splash = sorted(splash, key=lambda s_unit: Utility.calculate_distance(self.def_pos, s_unit.position))
        self.item = item
        self.skill_used = skill_used
        if event_combat:
            # Must make a copy because other things use whether event_combat is full as True/False values
            self.event_combat = [e for e in event_combat]
        else:
            self.event_combat = None
        # If the item being used has the event combat property, then that too.
        if not event_combat and (self.item.event_combat or (self.defender and self.defender.getMainWeapon() and self.defender.getMainWeapon().event_combat)):
            self.event_combat = ['hit'] * 8  # Default event combat for evented items

        self.state = 'Init'
        self.atk_rounds = 0
        self.def_rounds = 0

        self.uses_count = 0
        self.index = 0

    def generate_roll(self, rng_mode, event_command=None):
        if event_command:
            if event_command in ('hit', 'crit'):
                return -1
            elif event_command == 'miss':
                return 100
        # Normal RNG
        if rng_mode == 'hybrid':
            roll = 0
        elif rng_mode == 'no_rng':
            roll = cf.CONSTANTS['set_roll']
        elif rng_mode == 'classic':
            roll = static_random.get_combat()
        elif rng_mode == 'true_hit':
            roll = (static_random.get_combat() + static_random.get_combat()) // 2
        elif rng_mode == 'true_hit+':
            roll = (static_random.get_combat() + static_random.get_combat() + static_random.get_combat()) // 3
        return roll

    def generate_crit_roll(self, event_command=None):
        if event_command and event_command == 'crit':
            return -1
        else:
            return static_random.get_combat()

    def handle_crit(self, result, attacker, defender, item, mode, gameStateObj, hybrid, event_command):
        to_crit = attacker.compute_crit(defender, gameStateObj, item, mode=mode)
        crit_roll = self.generate_crit_roll(event_command)
        if crit_roll < to_crit and not (isinstance(defender, TileObject.TileObject) or 'ignore_crit' in defender.status_bundle):
            result.outcome = 2
            result.def_damage = attacker.compute_damage(defender, gameStateObj, item, mode=mode, hybrid=hybrid, crit=cf.CONSTANTS['crit'])

    def generate_attacker_phase(self, gameStateObj, metaDataObj, defender):
        result = Result(self.attacker, defender)
        if self.event_combat:
            event_command = self.event_combat.pop()
        else:
            event_command = None
        if event_command == 'quit':
            return None

        # Start
        assert isinstance(defender, UnitObject.UnitObject) or isinstance(defender, TileObject.TileObject), \
            "Only Units and Tiles can engage in combat! %s" % (defender)
        
        to_hit = self.attacker.compute_hit(defender, gameStateObj, self.item, mode="Attack")
        rng_mode = gameStateObj.mode['rng']
        roll = self.generate_roll(rng_mode, event_command)

        hybrid = to_hit if rng_mode == 'hybrid' else None

        # if cf.OPTIONS['debug']: print('To Hit:', to_hit, ' Roll:', roll)
        if self.item.weapon:
            if roll < to_hit and (defender not in self.splash or 'evasion' not in defender.status_bundle):
                result.outcome = (2 if self.item.guaranteed_crit else 1)
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)
                if cf.CONSTANTS['crit']: 
                    self.handle_crit(result, self.attacker, defender, self.item, 'Attack', gameStateObj, hybrid, event_command)
                    
            # Missed but does half damage
            elif self.item.half:
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid) // 2
                # print(result.def_damage)

        elif self.item.spell:
            if not self.item.hit or (roll < to_hit and (defender not in self.splash or 'evasion' not in defender.status_bundle)):
                result.outcome = (2 if self.item.guaranteed_crit else 1)
                if self.item.damage is not None:
                    result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)
                    if cf.CONSTANTS['crit']: 
                        self.handle_crit(result, self.attacker, defender, self.item, 'Attack', gameStateObj, hybrid, event_command)
                elif self.item.heal is not None:
                    result.def_damage = -self.attacker.compute_heal(defender, gameStateObj, self.item, mode='Attack')
                if self.item.movement:
                    result.def_movement = self.item.movement

            elif self.item.half and self.item.hit is not None and self.item.damage is not None:
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)

        else:
            result.outcome = 1
            result.def_damage = -int(eval(self.item.heal)) if self.item.heal else 0
            if self.attacker is not defender and self.item.heal:
                result.def_damage -= sum(status.caretaker for status in self.attacker.status_effects if status.caretaker)
            if self.item.movement:
                result.def_movement = self.item.movement
            if self.item.self_movement:
                result.atk_movement = self.item.self_movement

        if result.outcome:
            # Handle status
            for s_id in self.item.status:
                status_object = StatusObject.statusparser(s_id)
                result.def_status.append(status_object)
            # Handle summon
            if self.item.summon:
                result.summoning = SaveLoad.create_summon(self.item.summon, self.attacker, self.def_pos, metaDataObj, gameStateObj)

        # Make last attack against a boss a crit!
        if cf.CONSTANTS['boss_crit'] and 'Boss' in defender.tags and result.outcome and result.def_damage >= defender.currenthp:
            result.outcome = 2

        # Handle lifelink and vampire
        if result.def_damage > 0:
            if self.item.lifelink:
                result.atk_damage -= result.def_damage
            if self.item.half_lifelink:
                result.atk_damage -= result.def_damage//2
            # Handle Vampire Status
            for status in self.attacker.status_effects:
                if status.vampire and defender.currenthp - result.def_damage <= 0 and \
                   not any(status.miracle and (not status.count or status.count.count > 0) for status in defender.status_effects):
                    result.atk_damage -= eval(status.vampire)
        
        return result

    def generate_defender_phase(self, gameStateObj):
        # Assumes Capable of counterattacking
        result = Result(self.defender, self.attacker)
        if self.event_combat:
            event_command = self.event_combat.pop()
        else:
            event_command = None
        if event_command == 'quit':
            return None

        to_hit = self.defender.compute_hit(self.attacker, gameStateObj, self.defender.getMainWeapon(), mode="Defense")
        rng_mode = gameStateObj.mode['rng']
        roll = self.generate_roll(rng_mode, event_command)

        hybrid = to_hit if rng_mode == 'hybrid' else None
        # if cf.OPTIONS['debug']: print('To Hit:', to_hit, ' Roll:', roll)
        if roll < to_hit:
            result.outcome = (2 if self.item.guaranteed_crit else 1)
            result.def_damage = self.defender.compute_damage(self.attacker, gameStateObj, self.defender.getMainWeapon(), mode="Defense", hybrid=hybrid)
            if cf.CONSTANTS['crit']: 
                self.handle_crit(result, self.defender, self.attacker, self.defender.getMainWeapon(), "Defense", gameStateObj, hybrid, event_command)

        # Missed but does half damage
        elif self.defender.getMainWeapon().half:
            result.def_damage = self.defender.compute_damage(self.attacker, gameStateObj, self.defender.getMainWeapon(), mode="Defense", hybrid=hybrid) // 2

        if result.outcome:
            for s_id in self.defender.getMainWeapon().status:
                status_object = StatusObject.statusparser(s_id)
                result.def_status.append(status_object)

        # Make last attack against a boss a crit!
        if cf.CONSTANTS['boss_crit'] and 'Boss' in self.attacker.tags and result.outcome and result.def_damage >= self.attacker.currenthp:
            result.outcome = 2

        # Handle lifelink and vampire
        if result.def_damage > 0:
            if self.defender.getMainWeapon().lifelink:
                result.atk_damage -= result.def_damage
            if self.defender.getMainWeapon().half_lifelink:
                result.atk_damage -= result.def_damage//2
            # Handle Vampire Status
            for status in self.defender.status_effects:
                if status.vampire and self.attacker.currenthp - result.def_damage <= 0 and \
                        not any(status.miracle and (not status.count or status.count.count > 0) for status in self.attacker.status_effects):
                    result.atk_damage -= eval(status.vampire)

        return result

    def generate_summon_phase(self, gameStateObj, metaDataObj):
        the_summon = SaveLoad.create_summon(self.item.summon, self.attacker, self.def_pos, metaDataObj, gameStateObj)

        result = Result(self.attacker, the_summon)
        result.summoning = the_summon

        return result

    def item_uses(self, item):
        if (item.uses and item.uses.uses <= 0) or (item.c_uses and item.c_uses.uses <= 0):
            return False
        return True

    def defender_can_counterattack(self):
        weapon = self.defender.getMainWeapon()
        if weapon and self.item_uses(weapon) and Utility.calculate_distance(self.attacker.position, self.defender.position) in weapon.get_range(self.defender):
            return True
        else:
            return False

    def defender_has_vantage(self, gameStateObj):
        return isinstance(self.defender, UnitObject.UnitObject) and self.defender.outspeed(self.attacker, self.defender.getMainWeapon(), gameStateObj) and \
            'vantage' in self.defender.status_bundle and not self.item.cannot_be_countered and \
            self.defender_can_counterattack() and self.item.weapon

    def def_double(self, gameStateObj):
        return (cf.CONSTANTS['def_double'] or 'vantage' in self.defender.status_bundle or 'def_double' in self.defender.status_bundle) and \
            self.def_rounds < 2 and self.defender.outspeed(self.attacker, self.defender.getMainWeapon(), gameStateObj)

    def determine_state(self, gameStateObj):
        logger.debug('Interaction State 1: %s', self.state)
        if self.state == 'Init':
            if self.defender:
                if self.defender_has_vantage(gameStateObj):
                    self.state = 'Defender'
                else:
                    self.state = 'Attacker'
            elif self.splash:
                self.state = 'Splash'
                self.index = 0
            elif self.item.summon:  # Hacky?
                self.state = 'Summon'
            else:
                self.state = 'Done'

        elif self.state == 'Attacker':
            if (not self.defender or isinstance(self.defender, TileObject.TileObject)) and not self.splash:  # Just leave if tile mode
                self.state = 'Done'
            elif self.splash:
                self.state = 'Splash'
                self.index = 0
            elif self.defender.currenthp > 0:
                if self.item.brave and self.item_uses(self.item) and self.defender.currenthp > 0:
                    self.state = 'AttackerBrave'
                elif (self.def_rounds < 1 or self.def_double(gameStateObj)) and \
                        self.item.weapon and not self.item.cannot_be_countered and isinstance(self.defender, UnitObject.UnitObject) and \
                        self.defender_can_counterattack():
                    self.state = 'Defender'
                elif self.atk_rounds < 2 and self.item.weapon and self.attacker.outspeed(self.defender, self.item, gameStateObj) and self.item_uses(self.item):
                    self.state = 'Attacker'
                else:
                    self.state = 'Done'
            else:
                self.state = 'Done'

        elif self.state == 'Splash':
            if self.index < len(self.splash):
                self.state = 'Splash'
            elif self.item.brave and self.item_uses(self.item):
                if self.defender and self.defender.currenthp > 0:
                    self.index = 0
                    self.state = 'AttackerBrave'
                else:
                    self.index = 0
                    self.state = 'SplashBrave'
            elif (self.def_rounds < 1 or self.def_double(gameStateObj)) and \
                    self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                    self.defender.currenthp > 0 and self.defender_can_counterattack() and not self.item.cannot_be_countered:
                self.index = 0
                self.state = 'Defender'
            elif self.defender and self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item, gameStateObj) and \
                    self.item_uses(self.item) and self.defender.currenthp > 0:
                self.index = 0
                self.state = 'Attacker'
            else:
                self.state = 'Done'

        elif self.state == 'AttackerBrave':
            if self.splash:
                self.state = 'SplashBrave'
                self.index = 0
            elif (self.def_rounds < 1 or self.def_double(gameStateObj)) and \
                    self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                    not self.item.cannot_be_countered and self.defender.currenthp > 0 and self.defender_can_counterattack():
                self.state = 'Defender'
            elif self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item, gameStateObj) and self.item_uses(self.item) and self.defender.currenthp > 0:
                self.state = 'Attacker'
            else:
                self.state = 'Done'

        elif self.state == 'SplashBrave':
            if self.index < len(self.splash):
                self.state = 'SplashBrave'
            elif (self.def_rounds < 1 or self.def_double(gameStateObj)) and \
                    self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                    self.defender.currenthp > 0 and self.defender_can_counterattack() and not self.item.cannot_be_countered:
                self.state = 'Defender'
            elif self.defender and self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item, gameStateObj) and \
                    self.item_uses(self.item) and self.defender.currenthp > 0:
                self.state = 'Attacker'
            else:
                self.state = 'Done'

        elif self.state == 'Defender':
            self.state = 'Done'
            if self.attacker.currenthp > 0:
                if self.defender.getMainWeapon().brave and self.item_uses(self.defender.getMainWeapon()):
                    self.state = 'DefenderBrave'
                elif self.def_rounds < 2 and self.defender_has_vantage(gameStateObj):
                    self.state = 'Attacker'
                elif self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item, gameStateObj) and self.item_uses(self.item) and not self.item.no_double:
                    self.state = 'Attacker'
                elif self.def_double(gameStateObj) and self.defender_can_counterattack() and not self.defender.getMainWeapon().no_double:
                    self.state = 'Defender'

        elif self.state == 'DefenderBrave':
            self.state = 'Done'
            if self.attacker.currenthp > 0:
                if self.def_rounds < 2 and self.defender_has_vantage(gameStateObj):
                    self.state = 'Attacker'
                if self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item, gameStateObj) and self.item_uses(self.item) and not self.item.no_double:
                    self.state = 'Attacker'
                elif self.def_double(gameStateObj) and self.defender_can_counterattack() and not self.defender.getMainWeapon().no_double:
                    self.state = 'Defender'

        elif self.state == 'Summon':
            self.state = 'Done'

    def get_a_result(self, gameStateObj, metaDataObj):
        result = None

        self.determine_state(gameStateObj)
        logger.debug('Interaction State 2: %s', self.state)

        old_random_state = static_random.get_combat_random_state()

        if self.state == 'Done':
            result = None

        elif self.state == 'Attacker':
            Action.do(Action.UseItem(self.item), gameStateObj)
            self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.defender)
            self.atk_rounds += 1

        elif self.state == 'Splash':
            if self.uses_count < 1:
                Action.do(Action.UseItem(self.item), gameStateObj)
                self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.splash[self.index])
            self.index += 1

        elif self.state == 'AttackerBrave':
            Action.do(Action.UseItem(self.item), gameStateObj)
            self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.defender)

        elif self.state == 'SplashBrave':
            if self.uses_count < 2:
                Action.do(Action.UseItem(self.item), gameStateObj)
                self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.splash[self.index])
            self.index += 1

        elif self.state == 'Defender':
            Action.do(Action.UseItem(self.defender.getMainWeapon()), gameStateObj)
            self.def_rounds += 1
            result = self.generate_defender_phase(gameStateObj)

        elif self.state == 'DefenderBrave':
            Action.do(Action.UseItem(self.defender.getMainWeapon()), gameStateObj)
            result = self.generate_defender_phase(gameStateObj)

        elif self.state == 'Summon':
            Action.do(Action.UseItem(self.item), gameStateObj)
            result = self.generate_summon_phase(gameStateObj, metaDataObj)

        # Event command must have been quit
        if result is None:
            self.state = 'Done'

        if self.state != "Done":
            new_random_state = static_random.get_combat_random_state()
            Action.do(Action.RecordRandomState(old_random_state, new_random_state), gameStateObj)
                
        return result
