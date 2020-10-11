from . import GlobalConstants as GC
from . import configuration as cf
from . import static_random
from . import UnitObject, TileObject, Action
from . import StatusCatalog, SaveLoad, Utility

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
        self.attacker_proc_used = None  # Proc skill used by the attacker
        self.defender_proc_used = None  # Proc skill used by the defender
        self.adept_proc = None
        self.summoning = None
        self.new_round = True

class SolverStateMachine(object):
    def __init__(self, starting_state):
        self.states = {'PreInit': PreInitState,
                       'Init': InitState,
                       'Attacker': AttackerState,
                       'AttackerBrave': AttackerBraveState,
                       'Defender': DefenderState,
                       'DefenderBrave': DefenderBraveState,
                       'Splash': SplashState,
                       'SplashBrave': SplashBraveState,
                       'Summon': SummonState,
                       'Done': DoneState}
        self.change_state(starting_state)

    def get_state(self):
        return self.state

    def get_state_name(self):
        return self.state_name

    def change_state(self, state):
        self.state_name = state
        self.state = self.states[state]() if state else None

    def ratchet(self, solver, gameStateObj, metaDataObj):   
        next_state = self.state.get_next_state(solver, gameStateObj)
        if next_state != self.state_name:
            self.change_state(next_state)
        if self.get_state():
            result = self.get_state().process(solver, gameStateObj, metaDataObj)
            return result
        return None

class SolverState(object):
    def __init__(self):
        pass

    def get_next_state(self, solver, gameStateObj):
        return None

    def process(self, solver, gameStateObj, metaDataObj):
        return None

class PreInitState(SolverState):
    def get_next_state(self, solver, gameStateObj):
        return 'Init'

class InitState(object):
    def get_next_state(self, solver, gameStateObj):
        if solver.defender:
            if solver.defender_has_vantage(gameStateObj):
                return 'Defender'
            else:
                return 'Attacker'
        elif solver.splash:
            return 'Splash'
        elif solver.item.summon:
            return 'Summon'
        else:
            return 'Done'

    def process(self, solver, gameStateObj, metaDataObj):
        solver.remove_pre_proc(gameStateObj)
        solver.reset()
        solver.atk_pre_proc = self.get_attacker_pre_proc(solver, solver.attacker, gameStateObj)
        if solver.defender and isinstance(solver.defender, UnitObject.UnitObject):
            solver.def_pre_proc = self.get_defender_pre_proc(solver, solver.defender, gameStateObj)
        return None

    def get_attacker_pre_proc(self, solver, unit, gameStateObj):
        proc_statuses = [s for s in unit.status_effects if s.attack_pre_proc]
        proc_statuses = sorted(proc_statuses, key=lambda x: x.attack_pre_proc.priority, reverse=True)
        for status in proc_statuses:
            if solver.has_nihil(solver.defender, status):
                continue
            roll = static_random.get_combat()
            expr = GC.EQUATIONS.get_expression(status.attack_pre_proc.rate, unit)
            if roll < expr:
                status_obj = StatusCatalog.statusparser(status.attack_pre_proc.status_id, gameStateObj)
                Action.do(Action.AddStatus(unit, status_obj), gameStateObj)
                return status_obj
        return None

    def get_defender_pre_proc(self, solver, unit, gameStateObj):
        proc_statuses = [s for s in unit.status_effects if s.defense_pre_proc]
        proc_statuses = sorted(proc_statuses, key=lambda x: x.defense_pre_proc.priority, reverse=True)
        for status in proc_statuses:
            if solver.has_nihil(solver.attacker, status):
                continue
            roll = static_random.get_combat()
            expr = GC.EQUATIONS.get_expression(status.defense_pre_proc.rate, unit)
            if roll < expr:
                status_obj = StatusCatalog.statusparser(status.defense_pre_proc.status_id, gameStateObj)
                Action.do(Action.AddStatus(unit, status_obj), gameStateObj)
                return status_obj
        return None

class AttackerState(SolverState):
    def is_brave(self, item):
        return item.brave or item.brave_attack

    def check_nihil(self, solver, status):
        return solver.has_nihil(solver.defender, status)

    def check_for_brave(self, solver, unit, item):
        if self.is_brave(item):
            return True
        for status in unit.status_effects:
            if status.adept_proc and not self.check_nihil(solver, status):
                roll = static_random.get_combat()
                expr = GC.EQUATIONS.get_expression(status.adept_proc.rate, unit)
                if roll < expr:
                    solver.adept_proc = status
                    return True
        return False

    def get_next_state(self, solver, gameStateObj):
        if solver.event_combat and solver.event_combat[-1] == 'quit':
            return 'Done'
        if solver.attacker.currenthp > 0:
            if solver.splash and any(s.currenthp > 0 for s in solver.splash):
                return 'Splash'
            elif solver.defender.currenthp > 0:
                if solver.item.weapon and solver.item_uses(solver.item) and self.check_for_brave(solver, solver.attacker, solver.item):
                    return 'AttackerBrave'
                elif solver.allow_counterattack(gameStateObj):
                    return 'Defender'
                elif solver.atk_rounds < 2 and solver.item.weapon and \
                        solver.attacker.outspeed(solver.defender, solver.item, gameStateObj, "Attack") and \
                        solver.item_uses(solver.item):
                    return 'Attacker'
                elif solver.next_round(gameStateObj):
                    return 'Init'
                else:
                    return 'Done'
        return 'Done'

    def increment_round(self, solver):
        solver.atk_rounds += 1

    def process(self, solver, gameStateObj, metaDataObj):
        Action.do(Action.UseItem(solver.item), gameStateObj)
        solver.uses_count += 1
        result = solver.generate_phase(gameStateObj, metaDataObj, solver.attacker, solver.defender, solver.item, 'Attack')
        result.adept_proc = solver.adept_proc
        solver.adept_proc = None
        result.new_round = solver.new_round
        solver.new_round = None
        self.increment_round(solver)
        return result

class AttackerBraveState(AttackerState):
    def get_next_state(self, solver, gameStateObj):
        if solver.event_combat and solver.event_combat[-1] == 'quit':
            return 'Done'
        if solver.attacker.currenthp > 0:
            if solver.splash and any(s.currenthp > 0 for s in solver.splash):
                return 'SplashBrave'
            elif solver.defender.currenthp > 0:
                if solver.allow_counterattack(gameStateObj):
                    return 'Defender'
                elif solver.atk_rounds < 2 and solver.item.weapon and \
                        solver.attacker.outspeed(solver.defender, solver.item, gameStateObj, "Attack") and \
                        solver.item_uses(solver.item):
                    return 'Attacker'
                elif solver.next_round(gameStateObj):
                    return 'Init'
                else:
                    return 'Done'
        return 'Done'

    def increment_round(self, solver):
        pass

class DefenderState(AttackerState):
    def is_brave(self, item):
        return item.brave or item.brave_defense

    def check_nihil(self, solver, status):
        return solver.has_nihil(solver.attacker, status)

    def get_next_state(self, solver, gameStateObj):
        if solver.event_combat and solver.event_combat[-1] == 'quit':
            return 'Done'
        if solver.attacker.currenthp > 0 and solver.defender.currenthp > 0:
            ditem = solver.p2_item
            if solver.item_uses(ditem) and self.check_for_brave(solver, solver.defender, ditem):
                return 'DefenderBrave'
            elif solver.def_rounds < 2 and solver.defender_has_vantage(gameStateObj):
                return 'Attacker'
            elif solver.atk_rounds < 2 and solver.attacker.outspeed(solver.defender, solver.item, gameStateObj, "Attack") and \
                    solver.item_uses(solver.item) and not solver.item.no_double:
                return 'Attacker'
            elif solver.def_double(gameStateObj) and solver.defender_can_counterattack() and \
                    not ditem.no_double:
                return 'Defender'
            elif solver.next_round(gameStateObj):
                return 'Init'
        return 'Done'

    def increment_round(self, solver):
        solver.def_rounds += 1

    def process(self, solver, gameStateObj, metaDataObj):
        ditem = solver.p2_item
        Action.do(Action.UseItem(ditem), gameStateObj)
        result = solver.generate_phase(gameStateObj, metaDataObj, solver.defender, solver.attacker, ditem, 'Defense')
        result.adept_proc = solver.adept_proc
        solver.adept_proc = None
        result.new_round = solver.new_round
        solver.new_round = None
        self.increment_round(solver)
        return result

class DefenderBraveState(DefenderState):
    def get_next_state(self, solver, gameStateObj):
        if solver.event_combat and solver.event_combat[-1] == 'quit':
            return 'Done'
        if solver.attacker.currenthp > 0 and solver.defender.currenthp > 0:
            ditem = solver.p2_item
            if solver.def_rounds < 2 and solver.defender_has_vantage(gameStateObj):
                return 'Attacker'
            elif solver.atk_rounds < 2 and solver.attacker.outspeed(solver.defender, solver.item, gameStateObj, "Attack") and \
                    solver.item_uses(solver.item) and not solver.item.no_double:
                return 'Attacker'
            elif solver.def_double(gameStateObj) and solver.defender_can_counterattack() and \
                    not ditem.no_double:
                return 'Defender'
            elif solver.next_round(gameStateObj):
                return 'Init'
        return 'Done'

    def increment_round(self, solver):
        pass

class SplashState(AttackerState):
    def __init__(self):
        self.index = 0

    def get_next_state(self, solver, gameStateObj):
        if solver.attacker.currenthp > 0:
            if self.index < len(solver.splash):
                return 'Splash'
            if solver.item.weapon and solver.item_uses(solver.item) and self.check_for_brave(solver, solver.attacker, solver.item):
                if solver.defender and solver.defender.currenthp > 0:
                    return 'AttackerBrave'
                elif any(s.currenthp > 0 for s in solver.splash):
                    return 'SplashBrave'
            if solver.allow_counterattack(gameStateObj):
                return 'Defender'
            elif solver.defender and solver.atk_rounds < 2 and \
                    solver.attacker.outspeed(solver.defender, solver.item, gameStateObj, "Attack") and \
                    solver.item_uses(solver.item) and solver.defender.currenthp > 0:
                return 'Attacker'
            elif solver.next_round(gameStateObj):
                return 'Init'
            else:
                return 'Done'
        else:
            return 'Done'

    def process(self, solver, gameStateObj, metaDataObj):
        if solver.uses_count < 1:
            Action.do(Action.UseItem(solver.item), gameStateObj)
            solver.uses_count += 1
        result = solver.generate_phase(gameStateObj, metaDataObj, solver.attacker, solver.splash[self.index], solver.item, 'Attack')
        result.adept_proc = solver.adept_proc
        solver.adept_proc = None
        result.new_round = solver.new_round
        solver.new_round = None
        self.index += 1
        return result

class SplashBraveState(SplashState):
    def get_next_state(self, solver, gameStateObj):
        if solver.attacker.currenthp > 0:
            if self.index < len(solver.splash):
                return 'SplashBrave'
            elif solver.allow_counterattack(gameStateObj):
                return 'Defender'
            elif solver.defender and solver.atk_rounds < 2 and \
                    solver.attacker.outspeed(solver.defender, solver.item. gameStateObj, "Attack") and \
                    solver.item_uses(solver.item) and solver.defender.currenthp > 0:
                return 'Attacker'
            elif solver.next_round(gameStateObj):
                return 'Init'
            else:
                return 'Done'
        else:
            return 'Done'

class SummonState(SolverState):
    def get_next_state(self, solver, gameStateObj):
        return 'Done'

    def process(self, solver, gameStateObj, metaDataObj):
        Action.do(Action.UseItem(solver.item), gameStateObj)
        result = solver.generate_summon_phase(gameStateObj, metaDataObj)
        return result

class DoneState(SolverState):
    def process(self, solver, gameStateObj, metaDataObj):
        return None

# Does not check legality of attack, that is for other functions to do. 
# Assumes attacker can attack all defenders using item and skill
class Solver(object):
    def __init__(self, attacker, defender, def_pos, splash, item, skill_used, event_combat=None, arena=False):
        self.attacker = attacker
        self.defender = defender
        self.def_pos = def_pos
        # Have splash damage spiral out from position it started on...
        self.splash = sorted(splash, key=lambda s_unit: Utility.calculate_distance(self.def_pos, s_unit.position))
        self.item = item
        self.p2_item = self.defender.getMainWeapon() if self.defender else None
        self.skill_used = skill_used
        if event_combat:
            # Must make a copy because we'll be modifying this list
            self.event_combat = [e.lower() for e in event_combat]
        else:
            self.event_combat = None
        # If the item being used has the event combat property, then that too.
        if not event_combat and (self.item.event_combat or (self.defender and self.p2_item and self.p2_item.event_combat)):
            self.event_combat = ['hit'] * 8  # Default event combat for evented items
        self.arena = arena

        self.state_machine = SolverStateMachine('PreInit')

        self.current_round = 0
        self.total_rounds = 1
        if self.arena:
            self.total_rounds = 20

        self.uses_count = 0

        self.atk_pre_proc = None
        self.def_pre_proc = None
        self.adept_proc = None  # Kept here until next result is created, then fed into next result
        self.atk_charge_proc = None
        self.def_charge_proc = None

    def reset(self):
        self.current_round += 1
        self.new_round = True
        self.atk_rounds = 0
        self.def_rounds = 0

    def get_state(self):
        return self.state_machine.get_state()

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

    def generate_phase(self, gameStateObj, metaDataObj, attacker, defender, item, mode):
        result = Result(attacker, defender)
        if self.event_combat:
            event_command = self.event_combat.pop()
        else:
            event_command = None
        if event_command == 'quit':
            return None

        # Start
        assert isinstance(defender, UnitObject.UnitObject) or isinstance(defender, TileObject.TileObject), \
            "Only Units and Tiles can engage in combat! %s" % (defender)
        
        # Add proc skills
        result.attacker_proc_used = self.get_attacker_proc(attacker, defender, gameStateObj)
        # Tiles cannot have proc effects
        if isinstance(defender, UnitObject.UnitObject):
            result.defender_proc_used = self.get_defender_proc(defender, attacker, gameStateObj)

        to_hit = attacker.compute_hit(defender, gameStateObj, item, mode=mode)
        rng_mode = gameStateObj.mode['rng']
        roll = self.generate_roll(rng_mode, event_command)

        hybrid = to_hit if rng_mode == 'hybrid' else None

        # if cf.OPTIONS['debug']: print('To Hit:', to_hit, ' Roll:', roll)
        if item.weapon and attacker is not defender:
            if roll < to_hit and (defender not in self.splash or 'evasion' not in defender.status_bundle):
                result.outcome = (2 if item.guaranteed_crit else 1)
                result.def_damage = attacker.compute_damage(defender, gameStateObj, item, mode=mode, hybrid=hybrid)
                if cf.CONSTANTS['crit']: 
                    self.handle_crit(result, attacker, defender, item, mode, gameStateObj, hybrid, event_command)
                if item.movement:
                    result.def_movement = item.movement
                if item.self_movement:
                    result.atk_movement = item.self_movement
                    
            # Missed but does half damage
            elif item.half_on_miss:
                result.def_damage = attacker.compute_damage(defender, gameStateObj, item, mode=mode, hybrid=hybrid) // 2
                # print(result.def_damage)

        elif item.spell:
            if not item.hit or (roll < to_hit and (defender not in self.splash or 'evasion' not in defender.status_bundle)):
                result.outcome = (2 if item.guaranteed_crit else 1)
                if item.damage is not None:
                    result.def_damage = attacker.compute_damage(defender, gameStateObj, item, mode=mode, hybrid=hybrid)
                    if cf.CONSTANTS['crit']: 
                        self.handle_crit(result, attacker, defender, item, mode, gameStateObj, hybrid, event_command)
                elif item.heal is not None:
                    result.def_damage = -attacker.compute_heal(defender, gameStateObj, item, mode=mode)
                    # Live to serve section
                    if attacker is not defender:
                        for status in attacker.status_effects:
                            if status.live_to_serve:
                                fraction = float(status.live_to_serve)
                                actual_healing_done = min(-result.def_damage, defender.stats['HP'] - defender.currenthp)
                                result.atk_damage -= int(fraction * actual_healing_done)
                if item.movement:
                    result.def_movement = item.movement
                if item.self_movement:
                    result.atk_movement = item.self_movement

            elif item.half_on_miss and item.hit is not None and item.damage is not None:
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, item, mode=mode, hybrid=hybrid) // 2

        else:
            result.outcome = 1
            result.def_damage = -int(eval(item.heal)) if item.heal else 0
            if attacker is not defender and item.heal:
                result.def_damage -= sum(status.caretaker for status in attacker.status_effects if status.caretaker)
            if item.movement:
                result.def_movement = item.movement
            if item.self_movement:
                result.atk_movement = item.self_movement

        if result.outcome:
            # Handle status
            if isinstance(defender, UnitObject.UnitObject):
                for s_id in item.status:
                    status_object = StatusCatalog.statusparser(s_id, gameStateObj)
                    result.def_status.append(status_object)
                # Handle fatigue
                if cf.CONSTANTS['fatigue'] and item.target_fatigue:
                    Action.do(Action.ChangeFatigue(defender, int(item.target_fatigue)), gameStateObj)

            # Handle summon
            if item.summon:
                result.summoning = SaveLoad.create_summon(item.summon, attacker, self.def_pos, gameStateObj)

        # Make last attack against a boss a crit!
        if cf.CONSTANTS['boss_crit'] and 'Boss' in defender.tags and result.outcome and result.def_damage >= defender.currenthp:
            result.outcome = 2

        # Handle lifelink and vampire and deflect_damage
        if result.def_damage > 0:
            if item.lifelink:
                result.atk_damage -= min(result.def_damage, defender.currenthp)
            if item.half_lifelink:
                result.atk_damage -= min(result.def_damage, defender.currenthp)//2
            # Handle Vampire and deflect_damage Status
            for status in attacker.status_effects:
                if status.vampire and defender.currenthp - result.def_damage <= 0 and \
                   not any(status.miracle and (not status.count or status.count.count > 0) for status in defender.status_effects):
                    result.atk_damage -= eval(status.vampire)
                if status.deflect_damage:
                    result.atk_damage += result.def_damage
                    result.def_damage = 0
        
        # Remove proc skills
        if result.attacker_proc_used:
            Action.do(Action.RemoveStatus(attacker, result.attacker_proc_used), gameStateObj)
        if result.defender_proc_used:
            Action.do(Action.RemoveStatus(defender, result.defender_proc_used), gameStateObj)

        return result

    def generate_summon_phase(self, gameStateObj, metaDataObj):
        the_summon = SaveLoad.create_summon(self.item.summon, self.attacker, self.def_pos, gameStateObj)

        result = Result(self.attacker, the_summon)
        result.summoning = the_summon

        return result

    def item_uses(self, item):
        if (item.uses and item.uses.uses <= 0) or \
           (item.c_uses and item.c_uses.uses <= 0) or \
           (item.cooldown and not item.cooldown.charged):
            return False
        return True

    def defender_can_counterattack(self):
        weapon = self.p2_item
        if self.arena and weapon:
            return True
        elif weapon and self.item_uses(weapon) and \
            (Utility.calculate_distance(self.attacker.position, self.defender.position) in weapon.get_range(self.defender) or 
             'distant_counter' in self.defender.status_bundle):
            return True
        else:
            return False

    def defender_has_vantage(self, gameStateObj):
        return isinstance(self.defender, UnitObject.UnitObject) and self.defender.outspeed(self.attacker, self.p2_item, gameStateObj, "Defense") and \
            'vantage' in self.defender.status_bundle and not self.item.cannot_be_countered and \
            self.defender_can_counterattack() and self.item.weapon

    def has_nihil(self, unit, status) -> bool:
        if isinstance(unit, UnitObject.UnitObject):
            for skill in unit.status_effects:
                if skill.nihil and ('All' in skill.nihil or status.id in skill.nihil):
                    return True
            return False

    def def_double(self, gameStateObj):
        return (cf.CONSTANTS['def_double'] or 'vantage' in self.defender.status_bundle or 'def_double' in self.defender.status_bundle) and \
            self.def_rounds < 2 and self.defender.outspeed(self.attacker, self.p2_item, gameStateObj, "Defense")

    def allow_counterattack(self, gameStateObj):
        return isinstance(self.defender, UnitObject.UnitObject) and \
            self.defender and self.item.weapon and not self.item.cannot_be_countered and \
            self.defender.currenthp > 0 and \
            (self.def_rounds < 1 or self.def_double(gameStateObj)) and \
            self.defender_can_counterattack()

    def check_charge(self, unit, unit2, item, status, gameStateObj):
        return eval(status.charge, globals(), locals())

    def next_round(self, gameStateObj):
        # Check for charge
        if self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                self.attacker.currenthp > 0 and self.defender.currenthp > 0:
            # Check for charge
            for status in self.attacker.status_effects:
                if status.charge and self.check_charge(self.attacker, self.defender, self.item, status, gameStateObj):
                    self.total_rounds += 1
                    self.atk_charge_proc = status
                    break
            else:
                for status in self.defender.status_effects:
                    if status.charge and self.check_charge(self.defender, self.attacker, self.p2_item, status, gameStateObj):
                        self.total_rounds += 1
                        self.def_charge_proc = status
                        break

            result = self.current_round < self.total_rounds
            return result
        return False

    def get_attacker_proc(self, attacker, defender, gameStateObj):
        if not isinstance(defender, UnitObject.UnitObject):
            return None
        proc_statuses = [s for s in attacker.status_effects if s.attack_proc]
        proc_statuses = sorted(proc_statuses, key=lambda x: x.attack_proc.priority, reverse=True)
        for status in proc_statuses:
            if self.has_nihil(defender, status):
                continue
            roll = static_random.get_combat()
            expr = GC.EQUATIONS.get_expression(status.attack_proc.rate, attacker)
            if roll < expr:
                status_obj = StatusCatalog.statusparser(status.attack_proc.status_id, gameStateObj)
                Action.do(Action.AddStatus(attacker, status_obj), gameStateObj)
                return status_obj
        return None

    def get_defender_proc(self, defender, attacker, gameStateObj):
        proc_statuses = [s for s in defender.status_effects if s.defense_proc]
        proc_statuses = sorted(proc_statuses, key=lambda x: x.defense_proc.priority, reverse=True)
        for status in proc_statuses:
            if self.has_nihil(attacker, status):
                continue
            roll = static_random.get_combat()
            expr = GC.EQUATIONS.get_expression(status.defense_proc.rate, defender)
            if roll < expr:
                status_obj = StatusCatalog.statusparser(status.defense_proc.status_id, gameStateObj)
                Action.do(Action.AddStatus(defender, status_obj), gameStateObj)
                return status_obj
        return None

    def remove_pre_proc(self, gameStateObj):
        if self.atk_pre_proc:
            Action.do(Action.RemoveStatus(self.attacker, self.atk_pre_proc), gameStateObj)
        if self.def_pre_proc:
            Action.do(Action.RemoveStatus(self.defender, self.def_pre_proc), gameStateObj)

    def get_a_result(self, gameStateObj, metaDataObj):
        old_random_state = static_random.get_combat_random_state()
        result = None
        while not result:
            result = self.state_machine.ratchet(self, gameStateObj, metaDataObj)
            
            new_random_state = static_random.get_combat_random_state()
            Action.do(Action.RecordRandomState(old_random_state, new_random_state), gameStateObj)
            
            if self.state_machine.get_state():
                pass
            else:
                break
        return result
