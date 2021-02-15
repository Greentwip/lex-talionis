import random, math, os

from . import GlobalConstants as GC
from . import configuration as cf
from . import Engine, Image_Modification, Utility
from . import ClassData, Banner, Background, Weapons, BattleAnimation, GUIObjects
from . import CustomObjects, UnitObject
from . import StatusCatalog, Dialogue
from . import Action, Solver
from . import HealthBar

import logging
logger = logging.getLogger(__name__)

def convert_positions(gameStateObj, attacker, atk_position, position, item):
    logger.debug('attacker position: %s, position: %s, item: %s', atk_position, position, item)
    if item.weapon or item.spell:
        def_position, splash_positions = item.aoe.get_positions(atk_position, position, gameStateObj, item)
    else:
        def_position, splash_positions = position, []
    logger.debug('def pos: %s, splash pos: %s', def_position, splash_positions)
    if def_position:
        main_defender = [unit for unit in gameStateObj.allunits if unit.position == def_position]  # Target units before tiles
        if not main_defender and 'HP' in gameStateObj.map.tile_info_dict[def_position]:  # Check if the tile is valid to attack
            main_defender = [gameStateObj.map.tiles[def_position]]
        if main_defender:
            main_defender = main_defender[0]
        else:
            main_defender = None
    else:
        main_defender = None
    splash_units = [unit for unit in gameStateObj.allunits if unit.position in splash_positions]
    # Only attack enemies if we are using a weapon. If we are using a spell, attack all.
    # if item.weapon:
    #     splash_units = [unit for unit in splash_units if attacker.checkIfEnemy(unit)]
    # Above Removed. Replaced with better Cleave code in the AOE Component
    # Beneficial stuff only affects allies
    if item.beneficial and item.spell:
        splash_units = [unit for unit in splash_units if attacker.checkIfAlly(unit)]
        if item.heal:  # Only heal allies who need it
            splash_units = [unit for unit in splash_units if unit.currenthp < unit.stats['HP']]
    if item.weapon or (item.spell and not item.beneficial):
        splash_units += [gameStateObj.map.tiles[pos] for pos in splash_positions if 'HP' in gameStateObj.map.tile_info_dict[pos]]
    logger.debug('Main Defender: %s, Splash: %s', main_defender, splash_units)
    return main_defender, splash_units

def get_battle_anim(unit, item, distance) -> bool:
    magic = False
    if item:
        magic = item.is_magic()
        if magic and item.magic_at_range and distance <= 1:
            magic = False
    anim = GC.ANIMDICT.partake(unit.klass, unit.gender, item, magic, distance)
    if not anim:
        return False
    # Build animation
    script = anim['script']
    color = Utility.get_color(unit.team)
    name = None
    if unit.id in anim['images']:
        name = unit.id
        frame_dir = anim['images'][name]
    elif unit.name in anim['images']:
        name = unit.name
        frame_dir = anim['images'][name]
    elif 'Generic' + color in anim['images']:
        name = 'Generic' + color
        frame_dir = anim['images'][name]
    else:  # Just a map combat
        return False
    unit.battle_anim = BattleAnimation.BattleAnimation(unit, frame_dir, script, name, item)
    return True

def start_combat(gameStateObj, attacker, defender, def_pos, splash, item, 
                 skill_used=None, event_combat=None, ai_combat=False, 
                 toggle_anim=False, arena=False):
    def animation_wanted(attacker, defender):
        return (cf.OPTIONS['Animation'] == 'Always' or
                (cf.OPTIONS['Animation'] == 'Your Turn' and attacker.team == 'player') or
                (cf.OPTIONS['Animation'] == 'Combat Only' and attacker.checkIfEnemy(defender)))

    toggle_anim = gameStateObj.input_manager.is_pressed('AUX')
    # Whether animation combat is even allowed
    if (not splash and attacker is not defender and isinstance(defender, UnitObject.UnitObject) and not item.movement and not item.self_movement):
        # XOR below and ALWAYS use animations with the arena
        if arena or animation_wanted(attacker, defender) != toggle_anim:
            distance = Utility.calculate_distance(attacker.position, def_pos)
            attacker_anim = get_battle_anim(attacker, item, distance)
            defender_anim = get_battle_anim(defender, defender.getMainWeapon(), distance)
            if attacker_anim and defender_anim:
                return AnimationCombat(attacker, defender, def_pos, item, skill_used, event_combat, ai_combat, arena)
    # default
    return MapCombat(attacker, defender, def_pos, splash, item, skill_used, event_combat, arena)

# Abstract base class for combat
class Combat(object):
    # Determines actual damage done
    def calc_damage_done(self, result):
        if result.atk_damage > 0:
            result.atk_damage_done = min(result.atk_damage, result.attacker.currenthp)
        elif result.atk_damage < 0:
            result.atk_damage_done = min(-result.atk_damage, result.attacker.stats['HP'] - result.attacker.currenthp)
        else:
            result.atk_damage_done = 0

        result.def_damage_done = 0
        if result.defender:
            if result.def_damage > 0:
                result.def_damage_done = min(result.def_damage, result.defender.currenthp)
            elif result.def_damage < 0:
                result.def_damage_done = min(-result.def_damage, result.defender.stats['HP'] - result.defender.currenthp)

    def _handle_reflect(self, attacker, defender, status_obj, gameStateObj):
        if 'reflect' in defender.status_bundle:
            status_copy = StatusCatalog.statusparser(status_obj.id, gameStateObj)
            status_copy.giver_id = defender.id
            Action.do(Action.AddStatus(attacker, status_copy), gameStateObj)

    def _apply_result(self, result, gameStateObj):
        # Status
        if isinstance(result.defender, UnitObject.UnitObject) and 'immune' not in result.defender.status_bundle:
            for status_obj in result.def_status:
                status_obj.giver_id = result.attacker.id
                Action.do(Action.AddStatus(result.defender, status_obj), gameStateObj)
                self._handle_reflect(result.attacker, result.defender, status_obj, gameStateObj)
        if 'immune' not in result.attacker.status_bundle:
            for status_obj in result.atk_status:
                status_obj.giver_id = result.defender.id
                Action.do(Action.AddStatus(result.attacker, status_obj), gameStateObj)
                self._handle_reflect(result.defender, result.attacker, status_obj, gameStateObj)
        # Calculate true damage done
        self.calc_damage_done(result)
        # HP
        Action.do(Action.ChangeHP(result.attacker, -result.atk_damage), gameStateObj)
        if result.defender:
            if isinstance(result.defender, UnitObject.UnitObject):
                Action.do(Action.ChangeHP(result.defender, -result.def_damage), gameStateObj)
            else:  # TileObject
                Action.do(Action.ChangeTileHP(result.defender.position, -result.def_damage), gameStateObj)

    def handle_unusable_items(self, gameStateObj):
        if self.item.c_uses and self.item.c_uses.uses <= 0:
            Action.do(Action.UnequipItem(self.p1, self.item), gameStateObj)
        if self.p2 and self.p2_item and self.p2_item.c_uses and self.p2_item.c_uses.uses <= 0:
            Action.do(Action.UnequipItem(self.p2, self.p2_item), gameStateObj)
        if self.item.cooldown and not self.item.cooldown.charged:
            Action.do(Action.UnequipItem(self.p1, self.item), gameStateObj)
        if self.p2 and self.p2_item and self.p2_item.cooldown and not self.p2_item.cooldown.charged:
            Action.do(Action.UnequipItem(self.p2, self.p2_item), gameStateObj)

    def find_broken_items(self):
        # Handle items that were used
        a_broke_item, d_broke_item = False, False
        if self.item.uses and self.item.uses.uses <= 0:
            a_broke_item = True
        if self.p2 and self.p2_item and self.p2_item.uses and self.p2_item.uses.uses <= 0:
            d_broke_item = True
        return a_broke_item, d_broke_item

    def remove_broken_items(self, a_broke_item, d_broke_item, gameStateObj):
        if a_broke_item:
            Action.do(Action.RemoveItem(self.p1, self.item), gameStateObj)
            gameStateObj.boundary_manager.recalculate_unit(self.p1, gameStateObj)
        if d_broke_item:
            Action.do(Action.RemoveItem(self.p2, self.p2_item), gameStateObj)
            gameStateObj.boundary_manager.recalculate_unit(self.p2, gameStateObj)

    def summon_broken_item_banner(self, a_broke_item, d_broke_item, gameStateObj):
        if a_broke_item and self.p1.team == 'player' and not self.p1.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.p1, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        if d_broke_item and self.p2.team == 'player' and not self.p2.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.p2, self.p2_item))
            gameStateObj.stateMachine.changeState('itemgain')

    def handle_fatigue(self, results, gameStateObj):
        if cf.CONSTANTS['fatigue'] in (1, 2, 3) and not self.event_combat:
            if self.item:
                fatigue_gain = self._compute_fatigue(self.p1, self.item, gameStateObj)
                if cf.CONSTANTS['fatigue'] == 2:
                    for result in results:
                        if self.p1 is result.attacker:
                            Action.do(Action.ChangeFatigue(self.p1, fatigue_gain), gameStateObj)
                else:
                    Action.do(Action.ChangeFatigue(self.p1, fatigue_gain), gameStateObj)
            if self.p2 and self.p2_item and self.p2 is not self.p1:
                fatigue_gain = self._compute_fatigue(self.p2, self.p2_item, gameStateObj)
                if cf.CONSTANTS['fatigue'] == 2:
                    for result in results:
                        if self.p2 is result.attacker:
                            Action.do(Action.ChangeFatigue(self.p2, fatigue_gain), gameStateObj)
                else:
                    Action.do(Action.ChangeFatigue(self.p2, 1), gameStateObj)
            if cf.CONSTANTS['fatigue'] == 1:
                for splash in self.splash:
                    Action.do(Action.ChangeFatigue(splash, 1), gameStateObj)

    def _compute_fatigue(self, unit, item, gameStateObj):
        if cf.CONSTANTS['fatigue'] in (1, 2) and (item.weapon or item.spell):
            return item.fatigue or 1
        else:
            return item.fatigue or 0

    def handle_wexp(self, results, item, gameStateObj):
        if not cf.CONSTANTS['miss_wexp']:  # If miss wexp is not on, only include hits
            results = [result for result in results if result.outcome]
        if cf.CONSTANTS['double_wexp']:
            already_fatal = False
            for result in results:
                Action.do(Action.GainWexp(result.attacker, item), gameStateObj)
                if not already_fatal and cf.CONSTANTS['fatal_wexp'] and result.defender.isDying:
                    Action.do(Action.GainWexp(result.attacker, item), gameStateObj)
                    already_fatal = True
        elif results:
            unit = results[0].attacker
            Action.do(Action.GainWexp(unit, item), gameStateObj)
            if cf.CONSTANTS['fatal_wexp'] and any(result.defender.isDying for result in results):
                Action.do(Action.GainWexp(unit, item), gameStateObj)
    
    def calc_init_exp_p1(self, my_exp, other_unit, applicable_results):
        p1_klass = ClassData.class_dict[self.p1.klass]
        other_unit_klass = ClassData.class_dict[other_unit.klass]
        exp_multiplier = p1_klass['exp_multiplier']

        for status in self.p1.status_effects:
            if status.exp_multiplier:
                exp_multiplier *= float(status.exp_multiplier)

        damage, healing, kills = 0, 0, 0

        damage_done = sum([result.def_damage_done for result in applicable_results])
        
        if self.item.heal:
            healing += damage_done
        else:
            damage += damage_done

        if self.item.exp:
            normal_exp = int(self.item.exp)
        elif self.item.weapon or not self.p1.checkIfAlly(other_unit):
            level_diff = other_unit.get_internal_level() - self.p1.get_internal_level() + cf.CONSTANTS['exp_offset']
            exp_mult = exp_multiplier*other_unit_klass['exp_when_attacked']
            normal_exp = int(exp_mult*cf.CONSTANTS['exp_magnitude']*math.exp(level_diff*cf.CONSTANTS['exp_curve']))
        elif self.item.spell:
            if self.item.heal:
                # Amount healed - exp drops off linearly based on level. But minimum is 5 exp
                normal_exp = max(5, int(exp_multiplier*cf.CONSTANTS['heal_curve']*(damage_done-self.p1.get_internal_level()) + cf.CONSTANTS['heal_magnitude']))
            else: # Status (Fly, Mage Shield, etc.)
                normal_exp = int(exp_multiplier*cf.CONSTANTS['status_exp'])
        else:
            normal_exp = 0
            
        if other_unit.isDying:
            kills += 1
            my_exp += int(cf.CONSTANTS['kill_multiplier']*normal_exp) + (cf.CONSTANTS['boss_bonus'] if 'Boss' in other_unit.tags else 0)
        else:
            my_exp += normal_exp
        if 'no_exp' in other_unit.status_bundle:
            my_exp = 0
        if self.item.max_exp:
            my_exp = min(my_exp, int(self.item.max_exp))
        logger.debug('Attacker gained %s exp', my_exp)
        return my_exp, (damage, healing, kills)

    def calc_init_exp_p2(self, defender_results):
        p2_klass = ClassData.class_dict[self.p2.klass]
        other_unit_klass = ClassData.class_dict[self.p1.klass]
        exp_multiplier = p2_klass['exp_multiplier']*other_unit_klass['exp_when_attacked']
        for status in self.p2.status_effects:
            if status.exp_multiplier:
                exp_multiplier *= float(status.exp_multiplier)

        damage, healing, kills = 0, 0, 0

        my_exp = 0
        applicable_results = [result for result in self.old_results if result.outcome and result.attacker is self.p2 and
                              result.defender is self.p1 and not result.def_damage <= 0]
        if applicable_results:
            damage_done = sum([result.def_damage_done for result in applicable_results])
            damage += damage_done
            level_diff = self.p1.get_internal_level() - self.p2.get_internal_level() + cf.CONSTANTS['exp_offset']
            normal_exp = max(0, int(exp_multiplier*cf.CONSTANTS['exp_magnitude']*math.exp(level_diff*cf.CONSTANTS['exp_curve'])))
            if self.p1.isDying:
                kills += 1
                my_exp += int(cf.CONSTANTS['kill_multiplier']*normal_exp) + (cf.CONSTANTS['boss_bonus'] if 'Boss' in self.p1.tags else 0)
            else:
                my_exp += normal_exp 
            if 'no_exp' in self.p1.status_bundle:
                my_exp = 0

        # No free exp for affecting myself or being affected by allies
        if self.p1.checkIfAlly(self.p2):
            my_exp = Utility.clamp(my_exp, 0, 100)
        else:
            my_exp = Utility.clamp(my_exp, cf.CONSTANTS['min_exp'], 100)
        return my_exp, (damage, healing, kills)

    def handle_interact_script(self, gameStateObj):
        script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/interactScript.txt'
        if os.path.exists(script_name):
            interact_script = Dialogue.Dialogue_Scene(script_name, unit=self.p1, unit2=(self.p2 if self.p2 else None))
            gameStateObj.message.append(interact_script)
            gameStateObj.stateMachine.changeState('dialogue')

    def handle_miracle(self, gameStateObj, all_units):
        for unit in all_units:
            if unit.isDying and isinstance(unit, UnitObject.UnitObject):
                # Check for arena miracle
                if self.arena and unit.team == 'player' and not cf.CONSTANTS['arena_death']:
                    Action.execute(Action.Miracle(unit), gameStateObj)
                    if self.arena == 'arena_base':
                        # Doesn't count as a fight if you lose
                        gameStateObj.level_constants['_' + str(unit.id) + '_arena_uses'] -= 1
                        
                # check for regular miracle
                elif any(status.miracle and (not status.count or status.count.count > 0) for status in unit.status_effects):
                    Action.do(Action.Miracle(unit), gameStateObj)
                    Action.do(Action.Message("%s activated Miracle" % unit.name), gameStateObj)

    def handle_item_gain(self, gameStateObj, all_units):
        units = [u for u in all_units if isinstance(u, UnitObject.UnitObject)]
        for unit in units:
            if unit.isDying:
                for item in unit.items:
                    if item.droppable:
                        if unit in self.splash or unit is self.p2:
                            Action.do(Action.DropItem(self.p1, item), gameStateObj)
                        elif self.p2:
                            Action.do(Action.DropItem(self.p2, item), gameStateObj)

        if self.arena and self.p2.currenthp <= 0 and gameStateObj.level_constants['_wager'] > 0:
            action = Action.GiveGold(gameStateObj.level_constants['_wager']*2, gameStateObj.current_party)
            Action.do(action, gameStateObj)

    def handle_state_stack(self, gameStateObj):
        if self.event_combat:
            gameStateObj.message[-1].current_state = "Processing"
            if not self.p1.isDying:
                self.p1.sprite.change_state('normal', gameStateObj)
        else:
            if self.p1.team == 'player':
                # Check if this is an ai controlled player
                if gameStateObj.stateMachine.getPreviousState() == 'ai':
                    pass
                elif self.arena == 'arena_base':
                    # gameStateObj.stateMachine.changeState('base_arena_choice')
                    pass
                elif not self.p1.hasAttacked:
                    gameStateObj.stateMachine.changeState('menu')
                elif self.p1.has_canto_plus() and not self.p1.isDying:
                    gameStateObj.stateMachine.changeState('move')
                else:
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('free')
                    gameStateObj.stateMachine.changeState('wait')

    def handle_statuses(self, gameStateObj):
        for status in self.p1.status_effects:
            if status.status_after_battle and not (self.p1.isDying and status.tether):
                for unit in [self.p2] + self.splash:
                    if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfEnemy(self.p2) and not unit.isDying and 'immune' not in unit.status_bundle:
                        applied_status = StatusCatalog.statusparser(status.status_after_battle, gameStateObj)
                        if status.tether:
                            Action.do(Action.TetherStatus(status, applied_status, self.p1, unit), gameStateObj)
                        Action.do(Action.AddStatus(unit, applied_status), gameStateObj)
            if status.status_after_help and not self.p1.isDying:
                for unit in [self.p2] + self.splash:
                    if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfAlly(unit) and not unit.isDying and 'immune' not in unit.status_bundle:
                        applied_status = StatusCatalog.statusparser(status.status_after_help, gameStateObj)
                        Action.do(Action.AddStatus(unit, applied_status), gameStateObj)
            if status.lost_on_attack and (self.item.weapon or self.item.detrimental):
                Action.do(Action.RemoveStatus(self.p1, status), gameStateObj)
            elif status.lost_on_interact and (self.item.weapon or self.item.spell):
                Action.do(Action.RemoveStatus(self.p1, status), gameStateObj)
            if status.gain_status_after_attack and not self.p1.isDying:
                applied_status = StatusCatalog.statusparser(status.gain_status_after_attack, gameStateObj)
                Action.do(Action.AddStatus(self.p1, applied_status), gameStateObj)
            if status.gain_status_after_kill and not self.p1.isDying:
                if any(unit.isDying for unit in [self.p2] + self.splash if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfEnemy(unit)):
                    applied_status = StatusCatalog.statusparser(status.gain_status_after_kill, gameStateObj)
                    Action.do(Action.AddStatus(self.p1, applied_status), gameStateObj)
            if status.gain_status_after_active_kill and not self.p1.isDying:
                if any(unit.isDying for unit in [self.p2] + self.splash if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfEnemy(unit)):
                    applied_status = StatusCatalog.statusparser(status.gain_status_after_active_kill, gameStateObj)
                    Action.do(Action.AddStatus(self.p1, applied_status), gameStateObj)
        if self.p2 and isinstance(self.p2, UnitObject.UnitObject) and self.p2.checkIfEnemy(self.p1):
            for status in self.p2.status_effects:
                if status.status_after_battle and not self.p1.isDying and not (status.tether and self.p2.isDying) and 'immune' not in self.p1.status_bundle: 
                    applied_status = StatusCatalog.statusparser(status.status_after_battle, gameStateObj)
                    if status.tether:
                        Action.do(Action.TetherStatus(status, applied_status, self.p2, self.p1), gameStateObj)
                    Action.do(Action.AddStatus(self.p1, applied_status), gameStateObj)
                if status.gain_status_after_kill and not self.p2.isDying and self.p1.isDying and self.p2.checkIfEnemy(self.p1):
                    applied_status = StatusCatalog.statusparser(status.gain_status_after_kill, gameStateObj)
                    Action.do(Action.AddStatus(self.p2, applied_status), gameStateObj)

    def handle_supports(self, all_units, gameStateObj):
        if gameStateObj.support and cf.CONSTANTS['support'] and self.arena != 'arena_base':
            gameStateObj.support.check_interact(self.p1, all_units, gameStateObj)
            if not self.p1.isDying:
                gameStateObj.support.end_combat(self.p1, gameStateObj)

    def handle_skill_used(self, gameStateObj):
        if self.skill_used:
            if self.skill_used.combat_art:
                Action.do(Action.RemoveStatus(self.p1, self.skill_used.combat_art.status_id), gameStateObj)
            Action.do(Action.ResetCharge(self.skill_used), gameStateObj)

    def handle_death(self, gameStateObj, metaDataObj, all_units):
        for unit in all_units:
            if unit.isDying:
                logger.debug('%s is dying.', unit.name)
                if isinstance(unit, UnitObject.UnitObject):
                    gameStateObj.stateMachine.changeState('dying')
                    killer = None
                    if unit is self.p1:
                        killer = self.p2
                    else:
                        killer = self.p1
                    scene = Dialogue.Dialogue_Scene(metaDataObj['death_quotes'], unit=unit, unit2=killer)
                    gameStateObj.message.append(scene)
                    gameStateObj.stateMachine.changeState('dialogue')
                else:
                    gameStateObj.map.destroy(unit, gameStateObj)

    def arena_cleanup(self, gameStateObj):
        # Remove non-player characters from the game permanently
        if self.arena:
            if self.arena == 'arena_base':
                if self.p1.position == (0, 0):
                    self.p1.position = None
                if self.solver.total_rounds == 0 and self.p2.currenthp > 0:  # Arena was cancelled
                    # Doesn't count as a fight if you leave
                    gameStateObj.level_constants['_' + str(self.p1.id) + '_arena_uses'] -= 1
            # self.p2.position = None
            self.p2.dead = True  # Forget about this unit permanently!
            Action.execute(Action.LeaveMap(self.p2), gameStateObj)
            # Reset player 1's position now that we've removed his fighter
            Action.execute(Action.SimpleMove(self.p1, self.p1.position), gameStateObj)

    def arena_stop(self, gameStateObj):
        if self.arena:
            # Set the solvers total rounds low
            # self.arena_cancelled = True
            self.solver.total_rounds = 0

    def turnwheel_death_messages(self, all_units, gameStateObj):
        messages = []
        dying_units = [u for u in all_units if isinstance(u, UnitObject.UnitObject) and u.isDying]
        any_player_dead = any(not u.team.startswith('enemy') for u in dying_units)
        for unit in dying_units:
            if unit.team.startswith('enemy'):
                if any_player_dead:
                    messages.append("%s was defeated" % unit.name)
                else:
                    messages.append("Prevailed over %s" % unit.name)
            else:
                messages.append("%s was defeated" % unit.name)

        for message in messages:
            Action.do(Action.Message(message), gameStateObj)

class AnimationCombat(Combat):
    def __init__(self, attacker, defender, def_pos, item, skill_used, 
                 event_combat, ai_combat, arena):
        self.p1 = attacker
        self.p2 = defender
        # The attacker is always on the right unless the defender is a player and the attacker is not
        if self.p2.team == 'player' and self.p1.team != 'player':
            self.right = self.p2
            self.right_item = self.right.getMainWeapon()
            self.left = self.p1
            self.left_item = item
        elif self.p1.team.startswith('enemy') and self.p2.team in ('player', 'other'):
            self.right = self.p2
            self.right_item = self.right.getMainWeapon()
            self.left = self.p1
            self.left_item = item
        else:
            self.right = self.p1
            self.right_item = item
            self.left = self.p2
            self.left_item = self.left.getMainWeapon()
        self.def_pos = def_pos
        if arena:
            self.distance = 1
        else:
            self.distance = Utility.calculate_distance(self.p1.position, self.p2.position)
        self.at_range = self.distance - 1 if self.distance > 1 else 0 
        self.item = item
        self.p2_item = self.p2.getMainWeapon()
        self.skill_used = skill_used
        self.event_combat = event_combat
        self.ai_combat = ai_combat
        self.arena = arena

        self.solver = Solver.Solver(attacker, defender, def_pos, [], item, skill_used, event_combat, arena)

        self.old_results = []

        self.left_stats, self.right_stats = None, None
        self.left_hp_bar, self.right_hp_bar = SimpleHPBar(self.left), SimpleHPBar(self.right)

        self.combat_state = 'Start' # Start, Fade, Entrance, (Pre_Init, Anim, HP_Change, Anim), (Init, Anim, Hp_Change, Anim)
        self.skip = False

        # For fade to black viewbox
        self.viewbox_clamp_state = 0
        self.total_viewbox_clamp_states = 15
        self.viewbox = None

        # For darken backgrounds and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.darken_ui_background = 0
        self.foreground = Background.Foreground()
        self.combat_surf = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT), transparent=True)

        # For positioning UI
        self.name_offset = 0
        self.bar_offset = 0
        self.max_position_offset = 8

        # for Panning platforms
        self.focus_right = True if self.p1 == self.right else False
        self.pan_dir = 0

        if self.at_range == 1:
            self.pan_max = 16
            self.pan_move = 4
        elif self.at_range == 2:
            self.pan_max = 32
            self.pan_move = 8
        elif self.at_range >= 3:
            self.pan_max = 120
            self.pan_move = 25
        else:
            self.pan_max = 0
            self.pan_move = 0

        if self.focus_right: # For range 2
            self.pan_offset = -self.pan_max
        else:
            self.pan_offset = self.pan_max

        # for shake
        self.shake_set = [(0, 0)]
        self.shake_offset = (0, 0)
        self.current_shake = 0
        self.platform_shake_set = [(0, 0)]
        self.platform_shake_offset = (0, 0)
        self.platform_current_shake = 0

        # For display damage number animations
        self.damage_numbers = []

        # For display skill icons
        self.skill_icons = []
        self.proc_effects = []
        self.proc_wait = 0

        # For music
        self.music_fade_in = None

        # To match MapCombat
        self.health_bars = {self.left: self.left_hp_bar, self.right: self.right_hp_bar}
        self.splash = []  # This'll never be used

    def init_draw(self, gameStateObj, metaDataObj):
        def mod_name(name):
            while GC.FONT['text_brown'].size(name)[0] > 60:
                s_n = name.split(' ')
                if len(s_n) <= 1:
                    return name
                name = ' '.join(s_n[:-1])
            return name

        self.gameStateObj = gameStateObj  # Dependency Injection
        self.metaDataObj = metaDataObj  # Dependency Injection
        crit = 'Crit' if cf.CONSTANTS['crit'] else ''
        # Left
        left_color = Utility.get_color(self.left.team)
        # Name Tag
        self.left_name = GC.IMAGESDICT[left_color + 'LeftCombatName'].copy()
        size_x = GC.FONT['text_brown'].size(self.left.name)[0]
        GC.FONT['text_brown'].blit(self.left.name, self.left_name, (30 - size_x // 2, 8))
        # Bar
        self.left_bar = GC.IMAGESDICT[left_color + 'LeftMainCombat' + crit].copy()
        if self.left_item:
            name = self.left_item.name
            name = mod_name(name)
            size_x = GC.FONT['text_brown'].size(name)[0]
            GC.FONT['text_brown'].blit(name, self.left_bar, (91 - size_x // 2, 5 + (8 if cf.CONSTANTS['crit'] else 0)))

        # Right
        right_color = Utility.get_color(self.right.team)
        # Name Tag
        self.right_name = GC.IMAGESDICT[right_color + 'RightCombatName'].copy()
        size_x = GC.FONT['text_brown'].size(self.right.name)[0]
        GC.FONT['text_brown'].blit(self.right.name, self.right_name, (36 - size_x // 2, 8))
        # Bar
        self.right_bar = GC.IMAGESDICT[right_color + 'RightMainCombat' + crit].copy()
        if self.right_item:
            name = self.right_item.name
            name = mod_name(name)
            size_x = GC.FONT['text_brown'].size(name)[0]
            GC.FONT['text_brown'].blit(name, self.right_bar, (47 - size_x // 2, 5 + (8 if cf.CONSTANTS['crit'] else 0)))

        # Platforms
        if self.arena:
            left_platform_type = right_platform_type = "Arena"
        else:
            left_platform_type = gameStateObj.map.tiles[self.left.position].platform
            right_platform_type = gameStateObj.map.tiles[self.right.position].platform
        if self.at_range:
            suffix = '-Ranged'
        else:
            suffix = '-Melee'
        self.left_platform = GC.IMAGESDICT[left_platform_type + suffix].copy()
        self.right_platform = Engine.flip_horiz(GC.IMAGESDICT[right_platform_type + suffix].copy())

    def update(self, gameStateObj, metaDataObj):
        # logger.debug(self.combat_state)
        current_time = Engine.get_time()
        if self.combat_state == 'Start':
            self.current_result = self.solver.get_a_result(gameStateObj, metaDataObj)
            self.next_result = None
            self.set_stats(gameStateObj)
            self.old_results.append(self.current_result)
            # set up
            gameStateObj.cursor.setPosition(self.def_pos, gameStateObj)
            self.p1.sprite.change_state('combat_attacker', gameStateObj)
            self.p2.sprite.change_state('combat_defender', gameStateObj)
            if not self.skip:
                gameStateObj.stateMachine.changeState('move_camera')

            self.init_draw(gameStateObj, metaDataObj)
            if self.arena == 'arena_base':
                self.combat_state = 'ArenaFromBase'
            elif self.arena:
                self.combat_state = 'Fade'
            elif self.ai_combat:
                self.combat_state = 'RedOverlay_Init'
            else:
                self.combat_state = 'Fade'

        elif self.combat_state == 'RedOverlay_Init':
            gameStateObj.cursor.drawState = 2
            self.last_update = current_time
            self.combat_state = 'RedOverlay'

        elif self.combat_state == 'RedOverlay':
            if self.skip or current_time - self.last_update > 400:
                gameStateObj.cursor.drawState = 0
                gameStateObj.highlight_manager.remove_highlights()
                self.combat_state = 'Fade'

        elif self.combat_state == 'ArenaFromBase':
            self.viewbox_clamp_state = self.total_viewbox_clamp_states
            self.build_viewbox(gameStateObj)
            self.combat_state = 'Entrance'
            left_pos = (self.left.position[0] - gameStateObj.cameraOffset.get_x()) * GC.TILEWIDTH, \
                (self.left.position[1] - gameStateObj.cameraOffset.get_y()) * GC.TILEHEIGHT
            right_pos = (self.right.position[0] - gameStateObj.cameraOffset.get_x()) * GC.TILEWIDTH, \
                (self.right.position[1] - gameStateObj.cameraOffset.get_y()) * GC.TILEHEIGHT
            self.left.battle_anim.awake(self, self.right.battle_anim, False, self.at_range, self.max_position_offset, left_pos) # Stand
            self.right.battle_anim.awake(self, self.left.battle_anim, True, self.at_range, self.max_position_offset, right_pos) # Stand

        elif self.combat_state == 'Fade':
            # begin viewbox clamping
            if self.skip:
                self.viewbox_clamp_state = self.total_viewbox_clamp_states
                self.build_viewbox(gameStateObj)
            self.viewbox_clamp_state += 1
            if self.viewbox_clamp_state <= self.total_viewbox_clamp_states:
                self.build_viewbox(gameStateObj)
            else:
                self.combat_state = 'Entrance'
                left_pos = (self.left.position[0] - gameStateObj.cameraOffset.get_x()) * GC.TILEWIDTH, \
                    (self.left.position[1] - gameStateObj.cameraOffset.get_y()) * GC.TILEHEIGHT
                right_pos = (self.right.position[0] - gameStateObj.cameraOffset.get_x()) * GC.TILEWIDTH, \
                    (self.right.position[1] - gameStateObj.cameraOffset.get_y()) * GC.TILEHEIGHT
                self.left.battle_anim.awake(self, self.right.battle_anim, False, self.at_range, self.max_position_offset, left_pos) # Stand
                self.right.battle_anim.awake(self, self.left.battle_anim, True, self.at_range, self.max_position_offset, right_pos) # Stand
                # Unit should be facing down
                self.p1.sprite.change_state('selected')

        elif self.combat_state == 'Entrance':
            # Translate in names, stats, hp, and platforms
            self.bar_offset += 1
            self.name_offset += 1
            if self.skip or self.bar_offset >= self.max_position_offset:
                self.bar_offset = self.max_position_offset
                self.name_offset = self.max_position_offset
                self.last_update = current_time
                self.combat_state = 'Pre_Init'
                self.start_battle_music(gameStateObj)

        elif self.combat_state == 'Pre_Init':
            if self.skip or current_time - self.last_update > 410: # 25 frames
                self.last_update = current_time
                if self.left_item and self.left_item.transform and self.left.battle_anim.has_pose('Transform'):
                    self.left.battle_anim.start_anim('Transform')
                if self.right_item and self.right_item.transform and self.right.battle_anim.has_pose('Transform'):
                    self.right.battle_anim.start_anim('Transform')
                self.combat_state = 'TransformAnim'

        elif self.combat_state == 'TransformAnim':
            if self.left.battle_anim.done() and self.right.battle_anim.done():
                if self.solver.atk_pre_proc:
                    self.set_up_proc_animation(self.solver.attacker, self.solver.atk_pre_proc)
                if self.solver.def_pre_proc:
                    self.set_up_proc_animation(self.solver.defender, self.solver.def_pre_proc)
                if self.solver.atk_charge_proc:
                    self.set_up_proc_animation(self.solver.attacker, self.solver.atk_charge_proc)
                if self.solver.def_charge_proc:
                    self.set_up_proc_animation(self.solver.defender, self.solver.def_charge_proc)
                self.combat_state = "PreProcSkill"

        elif self.combat_state == 'Init':
            # self.current_result = self.solver.get_a_result(gameStateObj, metaDataObj)
            self.current_result = self.next_result
            self.next_result = None
            # print('Interaction: Getting a new result')
            if self.current_result is None:
                # End Battle and End Round
                if self.left_item and self.left_item.transform and self.left.battle_anim.has_pose('Revert'):
                    self.left.battle_anim.start_anim('Revert')
                if self.right_item and self.right_item.transform and self.right.battle_anim.has_pose('Revert'):
                    self.right.battle_anim.start_anim('Revert')
                self.combat_state = "RevertAnim"
            else:
                self.set_stats(gameStateObj)
                self.old_results.append(self.current_result)
                self.last_update = current_time
                if self.current_result.new_round:
                    self.combat_state = "TransformAnim"
                else:
                    self.set_up_animation(self.current_result)

        elif self.combat_state == 'PreProcSkill':
            if self.left.battle_anim.done() and self.right.battle_anim.done():
                if self.right_item and self.right_item.combat_effect:
                    effect = self.right.battle_anim.get_effect(self.right_item.combat_effect)
                    if effect:
                        self.right.battle_anim.add_effect(effect, 'Effect')
                elif self.left_item and self.left_item.combat_effect:
                    effect = self.left.battle_anim.get_effect(self.left_item.combat_effect)
                    if effect:
                        self.left.battle_anim.add_effect(effect, 'Effect')
                if self.skill_used:  # For command skills
                    self.add_skill_icon(self.p1, self.skill_used)
                self.combat_state = "InitialEffects"

        elif self.combat_state == 'InitialEffects':
            if not self.left.battle_anim.effect_playing() and not self.right.battle_anim.effect_playing():
                self.set_up_animation(self.current_result)  # To Proc Skill or Anim

        elif self.combat_state == 'AdeptProcSkill':
            if self.left.battle_anim.done() and self.right.battle_anim.done() and \
                    current_time - self.proc_wait > 400:
                self.set_up_animation(self.current_result)

        elif self.combat_state == 'AttackProcSkill':
            if self.left.battle_anim.done() and self.right.battle_anim.done() and \
                    current_time - self.proc_wait > 400:
                self.set_up_animation(self.current_result)

        elif self.combat_state == 'DefenseProcSkill':
            if self.left.battle_anim.done() and self.right.battle_anim.done() and \
                    current_time - self.proc_wait > 400:
                self.set_up_animation(self.current_result)

        elif self.combat_state == 'Anim':
            if self.left.battle_anim.done() and self.right.battle_anim.done():
                # Remove proc effects from this result
                self.left.battle_anim.remove_effects(self.proc_effects)
                self.right.battle_anim.remove_effects(self.proc_effects)
                self.proc_effects = []

                self.combat_state = 'Init'

        elif self.combat_state == 'HP_Change':
            proceed = self.current_result.attacker.battle_anim.can_proceed()
            # Wait at least 20 frames
            if current_time - self.last_update > 450 and self.left_hp_bar.done() and self.right_hp_bar.done() and proceed:
                # print('HP Bar Done!')
                self.current_result.attacker.battle_anim.resume()
                if self.left_hp_bar.true_hp <= 0:
                    self.left.battle_anim.start_dying_animation()
                if self.right_hp_bar.true_hp <= 0:
                    self.right.battle_anim.start_dying_animation()
                if self.left_hp_bar.true_hp <= 0 or self.right_hp_bar.true_hp <= 0 and self.current_result.attacker.battle_anim.state != 'Dying':
                    self.current_result.attacker.battle_anim.wait_for_dying()
                self.combat_state = 'Anim'

        elif self.combat_state == 'RevertAnim':
            if self.left.battle_anim.done() and self.right.battle_anim.done():
                self.last_update = current_time
                self.combat_state = 'ExpWait'
                self.focus_exp()
                self.move_camera()

        elif self.combat_state == 'ExpWait':
            if self.skip or current_time - self.last_update > 450:
                self.handle_exp(gameStateObj)
                self.combat_state = 'Exp'

        elif self.combat_state == 'Exp':
            # Waits here for exp gain state to finish
            self.last_update = current_time
            self.combat_state = 'OutWait'

        elif self.combat_state == 'OutWait':
            if self.skip or current_time - self.last_update > 820:
                self.p1.battle_anim.finish()
                self.p2.battle_anim.finish()
                self.combat_state = 'Out1'

        elif self.combat_state == 'Out1': # Nametags move out
            self.name_offset -= 1
            if self.skip or self.name_offset <= 0:
                self.name_offset = 0
                self.combat_state = 'Out2'

        elif self.combat_state == 'Out2': # Rest of the goods move out
            self.bar_offset -= 1
            if self.skip or self.bar_offset <= 0:
                self.bar_offset = 0
                self.combat_state = 'FadeOut'
                self.arena_cleanup(gameStateObj) 

        elif self.combat_state == 'FadeOut':
            # end viewbox clamping
            if self.skip:
                self.viewbox_clamp_state = 0
                self.build_viewbox(gameStateObj)
            self.viewbox_clamp_state -= 1
            if self.viewbox_clamp_state > 0:
                self.build_viewbox(gameStateObj)
            else:
                self.finish(gameStateObj)
                self.clean_up(gameStateObj, metaDataObj)
                self.end_skip()
                return True

        self.left_hp_bar.update(self.skip or self.combat_state == 'Exp')
        self.right_hp_bar.update(self.skip or self.combat_state == 'Exp')
        if self.left.battle_anim:
            self.left.battle_anim.update()
        if self.right.battle_anim:
            self.right.battle_anim.update()

        # Handle shake
        if self.current_shake:
            self.shake_offset = self.shake_set[self.current_shake - 1]
            self.current_shake += 1
            if self.current_shake > len(self.shake_set):
                self.current_shake = 0
        if self.platform_current_shake:
            self.platform_shake_offset = self.platform_shake_set[self.platform_current_shake - 1]
            self.platform_current_shake += 1
            if self.platform_current_shake > len(self.platform_shake_set):
                self.platform_current_shake = 0

    def start_skip(self):
        self.skip = True
        BattleAnimation.speed = 0.25

    def end_skip(self):
        self.skip = False
        BattleAnimation.speed = 1

    def start_hit(self, sound=True, miss=False):
        self.apply_result(self.current_result, self.gameStateObj, self.metaDataObj)
        if self.current_result.outcome or self.current_result.def_damage != 0 or self.current_result.atk_damage != 0:
            self.last_update = Engine.get_time()
            self.combat_state = 'HP_Change'
            self.start_damage_num_animation(self.current_result)
        # Sound
        if sound:
            if miss:
                GC.SOUNDDICT['Miss'].play()
            else:
                self.play_hit_sound()

    def start_damage_num_animation(self, result):
        def build_numbers(damage, left):
            str_damage = str(min(999, abs(damage)))
            for idx, num in enumerate(str_damage):
                if result.outcome == 2 and damage > 0:  # Crit
                    d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'Yellow')
                    self.damage_numbers.append(d)
                elif damage < 0:
                    d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'Cyan')
                    self.damage_numbers.append(d)
                elif damage > 0:
                    d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'Red')
                    self.damage_numbers.append(d)

        # Damage dealt to defender
        damage = result.def_damage
        left = self.left == result.defender
        build_numbers(damage, left)
        
        # Damage dealt to attacker
        # damage = result.atk_damage
        # left = self.left == result.attacker
        # build_numbers(damage, left)

    def play_hit_sound(self):
        if self.current_result.defender.currenthp <= 0:
            if self.current_result.outcome == 2: # critical
                GC.SOUNDDICT['Critical Kill'].play()
            else:
                GC.SOUNDDICT['Final Hit'].play()
        elif self.current_result.def_damage == 0 and (self.item.weapon or (self.item.spell and self.item.damage)):
            GC.SOUNDDICT['No Damage'].play()
        else:
            if self.current_result.outcome == 2: # critical
                sound_to_play = 'Critical Hit ' + str(random.randint(1, 2))
            else:
                sound_to_play = 'Attack Hit ' + str(random.randint(1, 5)) # Choose a random hit sound
            GC.SOUNDDICT[sound_to_play].play()
                                
    def build_viewbox(self, gameStateObj):
        vb_multiplier = self.viewbox_clamp_state / float(self.total_viewbox_clamp_states)
        # x, y, width, height
        true_x, true_y = self.def_pos[0] - gameStateObj.cameraOffset.get_x(), self.def_pos[1] - gameStateObj.cameraOffset.get_y()
        vb_x = vb_multiplier * true_x * GC.TILEWIDTH
        vb_y = vb_multiplier * true_y * GC.TILEHEIGHT
        vb_width = GC.WINWIDTH - vb_x - (vb_multiplier * (GC.TILEX - true_x)) * GC.TILEWIDTH
        vb_height = GC.WINHEIGHT - vb_y - (vb_multiplier * (GC.TILEY - true_y)) * GC.TILEHEIGHT
        self.viewbox = (vb_x, vb_y, vb_width, vb_height)

    def start_battle_music(self, gameStateObj):
        # Start Battle Music
        ditem = self.p2_item
        if self.item.battle_music and GC.MUSICDICT.get(self.item.battle_music):
            item_music = GC.MUSICDICT.get(self.item.battle_music)
            self.music_fade_in = Engine.music_thread.fade_in(item_music)
        elif ditem and ditem.battle_music and GC.MUSICDICT.get(ditem.battle_music):
            item_music = GC.MUSICDICT.get(ditem.battle_music)
            self.music_fade_in = Engine.music_thread.fade_in(item_music)
        elif self.p1.team in ('player', 'other') and gameStateObj.phase_music.player_battle_music:
            self.music_fade_in = Engine.music_thread.fade_in(gameStateObj.phase_music.player_battle_music)
        elif gameStateObj.phase_music.enemy_battle_music:
            self.music_fade_in = Engine.music_thread.fade_in(gameStateObj.phase_music.enemy_battle_music)

    def set_stats(self, gameStateObj):
        result = self.current_result
        # Calc stats
        a_mode = 'Attack' if result.attacker is self.p1 else 'Defense'
        a_weapon = self.item if result.attacker is self.p1 else self.p2_item
        a_hit = result.attacker.compute_hit(result.defender, gameStateObj, a_weapon, a_mode)
        a_mt = result.attacker.compute_damage(result.defender, gameStateObj, a_weapon, a_mode)
        if cf.CONSTANTS['crit']:
            a_crit = result.attacker.compute_crit(result.defender, gameStateObj, a_weapon, a_mode)
        else:
            a_crit = 0
        a_stats = a_hit, a_mt, a_crit

        if self.item.weapon and self.solver.defender_can_counterattack():
            d_mode = 'Defense' if result.attacker is self.p1 else 'Attack'
            d_weapon = self.p2_item if result.attacker is self.p1 else self.item
            d_hit = result.defender.compute_hit(result.attacker, gameStateObj, d_weapon, d_mode)
            d_mt = result.defender.compute_damage(result.attacker, gameStateObj, d_weapon, d_mode)
            if cf.CONSTANTS['crit']:
                d_crit = result.defender.compute_crit(result.attacker, gameStateObj, d_weapon, d_mode)
            else:
                d_crit = 0
            d_stats = d_hit, d_mt, d_crit
        else:
            d_stats = None
            d_weapon = None

        # Build stats
        if result.attacker is self.right:
            self.left_stats = d_stats
            self.right_stats = a_stats
        else:
            self.left_stats = a_stats
            self.right_stats = d_stats

    def apply_result(self, result, gameStateObj, metaDataObj):
        self._apply_result(result, gameStateObj)
        # Sometimes this can cause the need to spawn a new battle animation
        if not self.left.battle_anim:
            get_battle_anim(self.left, self.left_item, self.distance)
            self.left.battle_anim.awake(self, self.right.battle_anim, False, self.at_range) # Stand
        if not self.right.battle_anim:
            get_battle_anim(self.right, self.right_item, self.distance)
            self.right.battle_anim.awake(self, self.left.battle_anim, True, self.at_range) # Stand

        # Get next result in preparation for next combat
        self.next_result = self.solver.get_a_result(gameStateObj, metaDataObj)

    def set_up_animation(self, result):
        if result.adept_proc and self.combat_state not in ("AdeptProcSkill", "AttackProcSkill", "DefenseProcSkill"):
            self.combat_state = "AdeptProcSkill"
            self.set_up_proc_animation(result.attacker, result.adept_proc)
        elif result.attacker_proc_used and self.combat_state not in ("AttackProcSkill", "DefenseProcSkill"):
            self.combat_state = 'AttackProcSkill'
            self.set_up_proc_animation(result.attacker, result.attacker_proc_used)
        elif result.defender_proc_used and self.combat_state != "DefenseProcSkill":
            self.combat_state = 'DefenseProcSkill'
            self.set_up_proc_animation(result.defender, result.defender_proc_used)
        else:
            self.combat_state = 'Anim'
            self.set_up_combat_animation(result)

    def set_up_proc_animation(self, unit, skill):
        effect = unit.battle_anim.get_effect(skill.name)
        if unit.battle_anim.has_pose(skill.name):
            unit.battle_anim.start_anim(skill.name)
        elif unit.battle_anim.has_pose('Generic Proc'):
            unit.battle_anim.start_anim(skill.name)
        elif effect:
            self.proc_wait = Engine.get_time()
            unit.battle_anim.add_effect(effect, 'Effect')
            self.proc_effects.append(effect)
        else:
            self.proc_wait = Engine.get_time()

        self.add_skill_icon(unit, skill)
        # Handle pan
        if unit == self.right:
            self.focus_right = True
        else:
            self.focus_right = False
        self.move_camera()

    def set_up_combat_animation(self, result):
        # print(result.outcome)
        if result.outcome == 2:
            result.attacker.battle_anim.start_anim('Critical')
        elif result.outcome:
            result.attacker.battle_anim.start_anim('Attack')
        else:
            result.attacker.battle_anim.start_anim('Miss')
        # Handle pan
        if result.attacker == self.right:
            self.focus_right = True
        else:
            self.focus_right = False
        self.move_camera()

    def add_skill_icon(self, unit, skill):
        self.skill_icons.append(GUIObjects.SkillIcon(skill, unit == self.right))

    def finish(self, gameStateObj):
        # fade back music IF AND ONLY IF it was faded in!
        if self.music_fade_in:
            Engine.music_thread.fade_back()

    def shake(self, num):
        self.current_shake = 1
        if num == 1: # Normal Hit
            self.shake_set = [(3, 3), (0, 0), (0, 0), (-3, -3), (0, 0), (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), 
                              (3, 3), (0, 0), (-3, -3), (3, 3), (0, 0)]
        elif num == 2: # No Damage
            self.shake_set = [(1, 1), (1, 1), (1, 1), (-1, -1), (-1, -1), (-1, -1), (0, 0)]
        elif num == 3: # Spell Hit
            self.shake_set = [(0, 0), (-3, -3), (0, 0), (0, 0), (0, 0), (3, 3), (0, 0), (0, 0), (-3, -3), (0, 0),
                              (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), (3, 3), (0, 0), (-3, -3), (3, 3), (3, 3), 
                              (0, 0)]
        elif num == 4: # Critical Hit
            self.shake_set = [(-6, -6), (0, 0), (0, 0), (0, 0), (6, 6), (0, 0), (0, 0), (-6, -6), (0, 0), (0, 0),
                              (6, 6), (0, 0), (-6, -6), (0, 0), (6, 6), (0, 0), (4, 4), (0, 0), (-4, -4), (0, 0),
                              (4, 4), (0, 0), (-4, -4), (0, 0), (4, 4), (0, 0), (-2, -2), (0, 0), (2, 2), (0, 0),
                              (-2, -2), (0, 0), (2, 2), (0, 0), (-1, -1), (0, 0), (1, 1), (0, 0)]

    def platform_shake(self):
        self.platform_current_shake = 1
        self.platform_shake_set = [(0, 1), (0, 0), (0, -1), (0, 0), (0, 1), (0, 0), (-1, -1), (0, 1), (0, 0)]

    def flash_color(self, num_frames, fade_out=0, color=(248, 248, 248)):
        self.foreground.flash(num_frames, fade_out, color)

    def darken(self):
        self.target_dark += 4

    def lighten(self):
        self.target_dark -= 4

    def darken_ui(self):
        self.darken_ui_background = 1

    def lighten_ui(self):
        self.darken_ui_background = -3

    def pan_away(self):
        self.focus_right = not self.focus_right
        self.move_camera()

    def pan_back(self):
        if self.next_result:
            self.focus_right = (self.next_result.attacker == self.right)
        else:
            self.focus_exp()
        self.move_camera()

    def focus_exp(self):
        # Handle pan
        if self.p1.team == 'player':
            self.focus_right = (self.p1 == self.right)
        elif self.p2.team == 'player':
            self.focus_right = (self.p2 == self.right)

    def move_camera(self):
        if self.focus_right and self.pan_offset != -self.pan_max:
            self.pan_dir = -self.pan_move
        elif not self.focus_right and self.pan_offset != self.pan_max:
            self.pan_dir = self.pan_move

    def def_damage(self):
        return self.current_result.def_damage

    def outcome(self):
        return self.current_result.outcome

    def draw(self, surf, gameStateObj):
        bar_multiplier = self.bar_offset / float(self.max_position_offset)
        platform_trans = 100
        platform_top = 88
        if self.darken_background or self.target_dark:
            bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - int(self.darken_background * 12.5))
            surf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 1
            elif self.target_dark < self.darken_background:
                self.darken_background -= 1
        # Pan
        if self.pan_dir != 0:
            self.pan_offset += self.pan_dir
            if self.pan_offset > self.pan_max:
                self.pan_offset = self.pan_max
                self.pan_dir = 0
            elif self.pan_offset < -self.pan_max:
                self.pan_offset = -self.pan_max
                self.pan_dir = 0
        total_shake_x = self.shake_offset[0] + self.platform_shake_offset[0]
        total_shake_y = self.shake_offset[1] + self.platform_shake_offset[1]
        # Platform
        top = platform_top + (platform_trans - bar_multiplier * platform_trans) + total_shake_y
        if self.at_range:
            surf.blit(self.left_platform, (9 - self.pan_max + total_shake_x + self.pan_offset, top)) # Tested for attacker == right
            surf.blit(self.right_platform, (131 + self.pan_max + total_shake_x + self.pan_offset, top)) # Tested for attacker == right
        else:
            surf.blit(self.left_platform, (GC.WINWIDTH // 2 - self.left_platform.get_width() + total_shake_x, top))
            surf.blit(self.right_platform, (GC.WINWIDTH // 2 + total_shake_x, top))
        # Animation
        if self.at_range:
            right_range_offset = 24 + self.pan_max  # Tested
            left_range_offset = -24 - self.pan_max
        else:
            right_range_offset, left_range_offset = 0, 0
        if self.current_result:
            if self.right is self.current_result.attacker:
                self.right.battle_anim.draw_under(surf, (-total_shake_x, total_shake_y), right_range_offset, self.pan_offset)
                self.left.battle_anim.draw(surf, (-total_shake_x, total_shake_y), left_range_offset, self.pan_offset)
                self.right.battle_anim.draw(surf, (-total_shake_x, total_shake_y), right_range_offset, self.pan_offset)
                self.right.battle_anim.draw_over(surf, (-total_shake_x, total_shake_y), right_range_offset, self.pan_offset)
                self.left.battle_anim.draw_over(surf, (-total_shake_x, total_shake_y), left_range_offset, self.pan_offset)
            else:
                self.left.battle_anim.draw_under(surf, (-total_shake_x, total_shake_y), left_range_offset, self.pan_offset)
                self.right.battle_anim.draw(surf, (-total_shake_x, total_shake_y), right_range_offset, self.pan_offset)
                self.left.battle_anim.draw(surf, (-total_shake_x, total_shake_y), left_range_offset, self.pan_offset)
                self.left.battle_anim.draw_over(surf, (-total_shake_x, total_shake_y), left_range_offset, self.pan_offset)
                self.right.battle_anim.draw_over(surf, (-total_shake_x, total_shake_y), right_range_offset, self.pan_offset)
        else:
            self.left.battle_anim.draw(surf, (0, 0), left_range_offset, self.pan_offset)
            self.right.battle_anim.draw(surf, (0, 0), right_range_offset, self.pan_offset)

        # Skill icon animations
        for skill_icon in self.skill_icons:
            skill_icon.update()
            skill_icon.draw(surf)
        self.skill_icons = [s for s in self.skill_icons if not s.done]

        # Damage number animations
        for damage_num in self.damage_numbers:
            damage_num.update()
            if damage_num.left:
                x_pos = 94 + left_range_offset - total_shake_x + self.pan_offset
            else:
                x_pos = 146 + right_range_offset - total_shake_x + self.pan_offset
            damage_num.draw(surf, (x_pos, 40))
        self.damage_numbers = [d for d in self.damage_numbers if not d.done]

        # Make combat surf
        combat_surf = Engine.copy_surface(self.combat_surf)
        # Bar
        left_bar = self.left_bar.copy()
        right_bar = self.right_bar.copy()
        crit = 7 if cf.CONSTANTS['crit'] else 0
        # HP Bar
        self.left_hp_bar.draw(left_bar, (27, 30 + crit))
        self.right_hp_bar.draw(right_bar, (25, 30 + crit))
        # Item
        if self.left_item:
            self.draw_item(left_bar, self.left_item, self.right_item, self.left, self.right, (45, 2 + crit))
        if self.right_item:
            self.draw_item(right_bar, self.right_item, self.left_item, self.right, self.left, (1, 2 + crit))
        # Stats
        self.draw_stats(left_bar, self.left_stats, (42, 1))
        self.draw_stats(right_bar, self.right_stats, (GC.WINWIDTH // 2 - 3, 1))

        bar_trans = 80
        left_pos = (-3 + self.shake_offset[0], GC.WINHEIGHT - self.left_bar.get_height() + (bar_trans - bar_multiplier * bar_trans) + self.shake_offset[1])
        right_pos = (GC.WINWIDTH // 2 + self.shake_offset[0], 
                     GC.WINHEIGHT - self.right_bar.get_height() + (bar_trans - bar_multiplier * bar_trans) + self.shake_offset[1])
        combat_surf.blit(left_bar, left_pos)
        combat_surf.blit(right_bar, right_pos)
        # Nametag
        name_multiplier = self.name_offset / float(self.max_position_offset)
        top = -60 + name_multiplier * 60 + self.shake_offset[1]
        combat_surf.blit(self.left_name, (-3 + self.shake_offset[0], top))
        combat_surf.blit(self.right_name, (GC.WINWIDTH + 3 - self.right_name.get_width() + self.shake_offset[0], top))

        if self.darken_ui_background:
            self.darken_ui_background = min(self.darken_ui_background, 4)
            # bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - abs(int(self.darken_ui_background*11.5)))
            color = 255 - abs(self.darken_ui_background * 24)
            Engine.fill(combat_surf, (color, color, color), None, Engine.BLEND_RGB_MULT)
            # combat_surf.blit(bg, (0, 0))
            self.darken_ui_background += 1

        surf.blit(combat_surf, (0, 0))

        self.foreground.draw(surf)

    def draw_item(self, surf, item, other_item, unit, other, topleft):
        white = other.check_effective(item)
        item.draw(surf, (topleft[0] + 2, topleft[1] + 3), white)

        # Blit advantage -- This must be blit every frame
        if unit.checkIfEnemy(other):
            advantage, e_advantage = Weapons.TRIANGLE.compute_advantage(item, other_item)
            if advantage > 0:
                UpArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (unit.arrowAnim[unit.arrowCounter] * 7, 0, 7, 10))
                surf.blit(UpArrow, (topleft[0] + 11, topleft[1] + 7))
            elif advantage < 0:
                DownArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (unit.arrowAnim[unit.arrowCounter] * 7, 10, 7, 10))
                surf.blit(DownArrow, (topleft[0] + 11, topleft[1] + 7))

    def draw_stats(self, surf, stats, topright):
        right, top = topright
        # Blit Hit
        hit = '--'
        if stats is not None and stats[0] is not None:
            hit = str(stats[0])
        GC.FONT['number_small2'].blit(hit, surf, (right - GC.FONT['number_small2'].size(hit)[0], top))
        # Blit Damage
        damage = '--'
        if stats is not None and stats[1] is not None:
            damage = str(stats[1])
        GC.FONT['number_small2'].blit(damage, surf, (right - GC.FONT['number_small2'].size(damage)[0], top + 8))
        if cf.CONSTANTS['crit']:
            crit = '--'
            if stats is not None and stats[2] is not None:
                crit = str(stats[2])
            GC.FONT['number_small2'].blit(crit, surf, (right - GC.FONT['number_small2'].size(crit)[0], top + 16))

    def handle_exp(self, gameStateObj):
        self.check_death()
        # Handle exp and stat gain
        if not self.event_combat and (self.item.weapon or self.item.spell) and (not self.arena or self.p2.currenthp <= 0):
            attacker_results = [result for result in self.old_results if result.attacker is self.p1]
            # Wexp and Skill Charge
            if attacker_results and not self.p1.isDying:
                if not self.skill_used:
                    Action.do(Action.ChargeAllSkills(self.p1), gameStateObj)
                self.handle_wexp(attacker_results, self.item, gameStateObj)

            # EXP and Records
            if self.p1.team == 'player' and not self.p1.isDying and not self.p1.isSummon():
                my_exp = 0
                applicable_results = [result for result in attacker_results if result.outcome and
                                      result.defender is self.p2]
                # Doesn't count if it did 0 damage
                applicable_results = [result for result in applicable_results if not (self.item.weapon and result.def_damage <= 0)]
                if applicable_results:
                    my_exp, records = self.calc_init_exp_p1(my_exp, self.p2, applicable_results)
                    Action.do(Action.UpdateUnitRecords(self.p1, records), gameStateObj)

                # No free exp for affecting myself or being affected by allies
                if self.p1.checkIfAlly(self.p2):
                    my_exp = int(Utility.clamp(my_exp, 0, 100))
                else:
                    my_exp = int(Utility.clamp(my_exp, cf.CONSTANTS['min_exp'], 100))

                if my_exp > 0:
                    gameStateObj.exp_gain_struct = (self.p1, my_exp, self, 'init')
                    gameStateObj.stateMachine.changeState('exp_gain')

            if self.p2 and not self.p2.isDying:
                defender_results = [result for result in self.old_results if result.attacker is self.p2]
                # WEXP and Skills
                if defender_results:
                    Action.do(Action.ChargeAllSkills(self.p2), gameStateObj)
                    self.handle_wexp(defender_results, self.p2_item, gameStateObj)
                # Exp and Records
                if self.p2.team == 'player' and not self.p2.isSummon():
                    my_exp, records = self.calc_init_exp_p2(defender_results)
                    Action.do(Action.UpdateUnitRecords(self.p2, records), gameStateObj)
                    if my_exp > 0:
                        gameStateObj.exp_gain_struct = (self.p2, my_exp, self, 'init')
                        gameStateObj.stateMachine.changeState('exp_gain')

    def check_death(self):
        if self.p1.currenthp <= 0:
            self.p1.isDying = True
        if self.p2.currenthp <= 0:
            self.p2.isDying = True

    # Clean up everything
    def clean_up(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.back()
        # self.p1.hasAttacked = True
        Action.do(Action.HasAttacked(self.p1), gameStateObj)

        if self.p1.checkIfEnemy(self.p2):
            Action.do(Action.Message("%s attacked %s" % (self.p1.name, self.p2.name)), gameStateObj)
        elif self.p1 is not self.p2:
            Action.do(Action.Message("%s helped %s" % (self.p1.name, self.p2.name)), gameStateObj)
        else:
            Action.do(Action.Message("%s used %s" % (self.p1.name, self.item)), gameStateObj)

        if not self.p1.has_canto_plus() and not self.event_combat:
            gameStateObj.stateMachine.changeState('wait') # Event combats do not cause unit to wait

        a_broke_item, d_broke_item = self.find_broken_items()

        # Create all_units list
        all_units = [self.p1]
        if self.p2 is not self.p1:
            all_units.append(self.p2)

        # Handle death and sprite changing
        self.check_death()
        if not self.p1.isDying:
            self.p1.sprite.change_state('normal', gameStateObj)
        if not self.p2.isDying:
            self.p2.sprite.change_state('normal', gameStateObj)

        self.turnwheel_death_messages(all_units, gameStateObj)

        # === HANDLE STATE STACK ==
        # Handle where we go at very end
        self.handle_state_stack(gameStateObj)

        self.handle_interact_script(gameStateObj)
        
        self.handle_miracle(gameStateObj, all_units)

        self.handle_item_gain(gameStateObj, all_units)

        # Handle item loss
        if self.p1 is not self.p2:
            self.summon_broken_item_banner(a_broke_item, d_broke_item, gameStateObj)

        # Handle after battle statuses
        self.handle_statuses(gameStateObj)

        self.handle_supports(all_units, gameStateObj)

        self.handle_fatigue(self.old_results, gameStateObj)

        # Handle skills that were used
        self.handle_skill_used(gameStateObj)

        self.handle_death(gameStateObj, metaDataObj, all_units)

        # Actually remove items
        self.handle_unusable_items(gameStateObj)
        self.remove_broken_items(a_broke_item, d_broke_item, gameStateObj)

class SimpleHPBar(object):
    full_hp_blip = GC.IMAGESDICT['FullHPBlip']
    empty_hp_blip = GC.IMAGESDICT['EmptyHPBlip']
    end_hp_blip = Engine.subsurface(full_hp_blip, (0, 0, 1, full_hp_blip.get_height()))
    colors = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 3, 3, 2, 2, 1, 1]

    def __init__(self, unit):
        self.unit = unit
        self.desired_hp = unit.currenthp
        self.true_hp = unit.currenthp
        self.max_hp = unit.stats['HP']
        self.last_update = 0
        self.color_tick = 0
        self.is_done = True
        self.big_number = False

    def update(self, skip=False):
        self.desired_hp = self.unit.currenthp
        if skip:
            self.true_hp = self.desired_hp
        if self.true_hp < self.desired_hp:
            self.is_done = False
            self.true_hp += .25 # Every 4 frames
            if self.true_hp == int(self.true_hp):  # Every four frames, play sound
                GC.SOUNDDICT['HealBoop'].play()
        elif self.true_hp > self.desired_hp:
            self.is_done = False
            self.big_number = True
            self.true_hp -= .5
        elif self.true_hp == self.desired_hp:
            self.is_done = True
            self.big_number = False
        self.color_tick += 1
        if self.color_tick >= len(self.colors):
            self.color_tick = 0
        return self.true_hp == self.desired_hp

    def done(self):
        return self.is_done

    def draw(self, surf, pos):
        t_hp = max(int(self.true_hp), 0)
        # Blit HP -- Must be blit every frame
        font = GC.FONT['number_small2']
        top = pos[1] - 4
        if self.big_number:
            font = GC.FONT['number_big2']
            top = pos[1]
        if t_hp <= 80:
            position = pos[0] - font.size(str(t_hp))[0], top
            font.blit(str(t_hp), surf, position)
        else:
            position = pos[0] - font.size('??')[0], top
            font.blit('??', surf, position)
        full_hp_blip = Engine.subsurface(self.full_hp_blip, (self.colors[self.color_tick] * 2, 0, 2, self.full_hp_blip.get_height()))
        if self.max_hp <= 40:
            for index in range(t_hp):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] + 1))
            for index in range(self.max_hp - t_hp):
                surf.blit(self.empty_hp_blip, (pos[0] + (index + t_hp) * 2 + 5, pos[1] + 1))
            surf.blit(self.end_hp_blip, (pos[0] + (self.max_hp) * 2 + 5, pos[1] + 1)) # End HP Blip
        else:
            # Lower 40 hp  
            for index in range(min(t_hp, 40)):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] + 4))
            for index in range(max(40 - t_hp, 0)):
                surf.blit(self.empty_hp_blip, (pos[0] + (index + t_hp) * 2 + 5, pos[1] + 4))
            surf.blit(self.end_hp_blip, (pos[0] + (40) * 2 + 5, pos[1] + 4)) # End HP Blip
            # Upper 40 hp
            for index in range(Utility.clamp(t_hp - 40, 0, 40)):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] - 4))
            right = Utility.clamp(self.max_hp, 0, 80)
            for index in range(right - max(40, t_hp)):
                surf.blit(self.empty_hp_blip, (pos[0] + (index + max(t_hp - 40, 0)) * 2 + 5, pos[1] - 4))
            surf.blit(self.end_hp_blip, (pos[0] + (right - 40) * 2 + 5, pos[1] - 4)) # End HP Blip

class MapCombat(Combat):
    def __init__(self, attacker, defender, def_pos, splash, item, skill_used, 
                 event_combat, arena):
        self.p1 = attacker
        self.p2 = defender
        self.def_pos = def_pos
        self.splash = splash
        self.item = item
        self.p2_item = self.p2.getMainWeapon() if self.p2 else None
        self.skill_used = skill_used
        self.event_combat = event_combat
        self.arena = arena

        self.solver = Solver.Solver(attacker, defender, def_pos, splash, item, skill_used, event_combat, arena)
        if self.arena:
            self.solver.total_rounds = 20
        self.results = []
        self.old_results = []

        self.last_update = Engine.get_time()
        self.length_of_combat = 2000
        self.additional_time = 0
        self.combat_state = 'Pre_Init'
        self.skip = False
        self.aoe_anim_flag = False # Have we shown the aoe animation yet?

        self.damage_numbers = []
        self.pre_proc_done = False

        self.health_bars = {}

    def update(self, gameStateObj, metaDataObj):
        def add_skill_icon(unit, skill):
            if unit in self.health_bars:
                hp_bar = self.health_bars[unit]
                hp_bar.force_position_update(gameStateObj)
                right = hp_bar.order == 'right' or hp_bar.order == 'middle'
                skill_icon = GUIObjects.SkillIcon(skill, right)
                hp_bar.add_skill_icon(skill_icon)

        current_time = Engine.get_time() - self.last_update
        # Get the results needed for this phase
        if not self.results:
            next_result = self.solver.get_a_result(gameStateObj, metaDataObj)
            if next_result is None:
                self.clean_up(gameStateObj, metaDataObj)
                return True
            self.results.append(next_result)
            if cf.CONSTANTS['simultaneous_aoe']:
                if self.solver.state_machine.get_state_name().startswith('Attacker') and \
                        self.solver.splash:
                    self.results.append(self.solver.get_a_result(gameStateObj, metaDataObj))
                while self.solver.state_machine.get_state() and \
                        self.solver.state_machine.get_state_name().startswith('Splash') and \
                        self.solver.state_machine.get_state().index < len(self.solver.splash):
                    self.results.append(self.solver.get_a_result(gameStateObj, metaDataObj))

            self.begin_phase(gameStateObj)

            # Animate Pre-Proc skills (Vantage, Charge)
            if self.results[0].new_round:
                if self.solver.atk_pre_proc:
                    add_skill_icon(self.p1, self.solver.atk_pre_proc)    
                if self.solver.def_pre_proc:
                    add_skill_icon(self.p2, self.solver.def_pre_proc)
                if self.solver.atk_charge_proc:
                    add_skill_icon(self.p1, self.solver.atk_charge_proc)    
                if self.solver.def_charge_proc:
                    add_skill_icon(self.p2, self.solver.def_charge_proc)

        elif self.results:
            if self.combat_state == 'Pre_Init':
                # Move Camera
                if len(self.results) > 1:
                    gameStateObj.cursor.setPosition(self.def_pos, gameStateObj)
                else:
                    gameStateObj.cursor.setPosition(self.results[0].defender.position, gameStateObj)
                # sprite changes
                if self.results[0].defender == self.p1:
                    if self.p2 and self.p1.checkIfEnemy(self.p2):
                        self.p2.sprite.change_state('combat_attacker', gameStateObj)
                        self.p1.sprite.change_state('combat_counter', gameStateObj)
                    else:
                        self.p1.sprite.change_state('combat_active', gameStateObj)
                else:
                    self.p1.sprite.change_state('combat_attacker', gameStateObj)
                    if isinstance(self.p2, UnitObject.UnitObject):
                        self.p2.sprite.change_state('combat_defender', gameStateObj)
                for unit in self.splash:
                    if isinstance(unit, UnitObject.UnitObject):
                        unit.sprite.change_state('combat_defender', gameStateObj)
                if not self.skip:
                    gameStateObj.stateMachine.changeState('move_camera')
                self.combat_state = 'Init1'

            elif self.combat_state == 'Init1':
                self.last_update = Engine.get_time()
                self.combat_state = 'Init'
                if not any(result.defender.position == gameStateObj.cursor.position for result in self.results):
                    gameStateObj.cursor.drawState = 0
                else:
                    gameStateObj.cursor.drawState = 2
                for hp_bar in self.health_bars.values():
                    hp_bar.force_position_update(gameStateObj)
                for result in self.results:
                    if result.attacker_proc_used:
                        add_skill_icon(result.attacker, result.attacker_proc_used)
                    if result.defender_proc_used:
                        add_skill_icon(result.defender, result.defender_proc_used)
                    if result.adept_proc:
                        add_skill_icon(result.attacker, result.adept_proc)
                        
            elif self.combat_state == 'Init':
                if self.skip or current_time > self.length_of_combat // 5 + self.additional_time:
                    gameStateObj.cursor.drawState = 0
                    gameStateObj.highlight_manager.remove_highlights()

                    if self.item.aoe_anim and not self.aoe_anim_flag:
                        self.aoe_anim_flag = True
                        num_frames = 12
                        if 'AOE_' + self.item.id in GC.IMAGESDICT:
                            image = GC.IMAGESDICT['AOE_' + self.item.id]
                            pos = gameStateObj.cursor.position[0] - (image.get_width() // num_frames // GC.TILEWIDTH // 2) + 1, \
                                gameStateObj.cursor.position[1] - (image.get_height() // GC.TILEHEIGHT // 2)
                            #  
                            # print(gameStateObj.cursor.position, pos)
                            anim = CustomObjects.Animation(GC.IMAGESDICT['AOE_' + self.item.id], pos, (num_frames, 1), num_frames, 32)
                            gameStateObj.allanimations.append(anim)
                        else:
                            logger.warning('%s not in GC.IMAGESDICT. Skipping Animation', 'AOE_' + self.item.id)
                    # Weapons get extra time, spells and items do not need it, since they are one sided.
                    if not self.item.weapon:
                        self.additional_time -= self.length_of_combat // 5
                    self.combat_state = '2'

            elif self.combat_state == '2':
                if self.skip or current_time > 2 * self.length_of_combat // 5 + self.additional_time:
                    self.combat_state = 'Anim'
                    if self.results[0].attacker.sprite.state in {'combat_attacker', 'combat_defender'}:
                        self.results[0].attacker.sprite.change_state('combat_anim', gameStateObj)
                    for result in self.results:
                        if result.attacker is self.p1:
                            item = self.item
                        elif result.attacker is self.p2:
                            item = self.p2_item
                        else:
                            item = result.attacker.getMainWeapon()
                        if item.sfx_on_cast and item.sfx_on_cast in GC.SOUNDDICT:
                            GC.SOUNDDICT[item.sfx_on_cast].play()

            elif self.combat_state == 'Anim':
                if self.skip or current_time > 3 * self.length_of_combat // 5 + self.additional_time:
                    if self.results[0].attacker.sprite.state == 'combat_anim':
                        self.results[0].attacker.sprite.change_state('combat_attacker', gameStateObj)
                    for result in self.results:
                        self.handle_result_anim(result, gameStateObj)
                    # force update hp bars
                    for hp_bar in self.health_bars.values():
                        hp_bar.update()
                    self.additional_time += \
                        max(hp_bar.time_for_change for hp_bar in self.health_bars.values()) if self.health_bars else self.length_of_combat // 5
                    self.combat_state = 'Clean'

            elif self.combat_state == 'Clean':
                if self.skip or current_time > (3 * self.length_of_combat // 5) + self.additional_time:
                    self.combat_state = 'Wait'

            elif self.combat_state == 'Wait': 
                if self.skip or current_time > (4 * self.length_of_combat // 5) + self.additional_time:
                    self.end_phase(gameStateObj)
                    self.old_results += self.results
                    self.results = []
                    self.combat_state = 'Pre_Init'

            if self.combat_state not in ('Pre_Init', 'Init1'):        
                for hp_bar in self.health_bars.values():
                    hp_bar.update()
        return False

    def handle_result_anim(self, result, gameStateObj):
        if result.outcome:
            if result.attacker is self.p1:
                item = self.item
            elif result.attacker is self.p2:
                item = self.p2_item
            else:
                item = result.attacker.getMainWeapon()
            if isinstance(result.defender, UnitObject.UnitObject):
                color = item.map_hit_color if item.map_hit_color else (255, 255, 255) # default to white
                result.defender.begin_flicker(self.length_of_combat // 5, color)
            # Sound
            if item.sfx_on_hit and item.sfx_on_hit in GC.SOUNDDICT:
                GC.SOUNDDICT[item.sfx_on_hit].play()
            elif result.defender.currenthp - result.def_damage <= 0: # Lethal
                GC.SOUNDDICT['Final Hit'].play()
                if result.outcome == 2: # Critical
                    for health_bar in self.health_bars.values():
                        health_bar.shake(3)
                else:
                    for health_bar in self.health_bars.values():
                        health_bar.shake(2)
            elif result.def_damage < 0: # Heal
                GC.SOUNDDICT['MapHeal'].play()
            elif result.def_damage == 0 and (item.weapon or (item.spell and item.damage)): # No Damage if weapon or spell with damage!
                GC.SOUNDDICT['No Damage'].play()
            else:
                if result.outcome == 2: # critical
                    sound_to_play = 'Critical Hit ' + str(random.randint(1, 2))
                else:
                    sound_to_play = 'Attack Hit ' + str(random.randint(1, 5)) # Choose a random hit sound
                GC.SOUNDDICT[sound_to_play].play()
                if result.outcome == 2 or result.attacker_proc_used: # critical
                    for health_bar in self.health_bars.values():
                        health_bar.shake(3)
                else:
                    for health_bar in self.health_bars.values():
                        health_bar.shake(1)
            # Animation
            if self.item.self_anim:
                name, x, y, num = item.self_anim.split(',')
                pos = (result.attacker.position[0], result.attacker.position[1] - 1)
                anim = CustomObjects.Animation(GC.IMAGESDICT[name], pos, (int(x), int(y)), int(num), 24)
                gameStateObj.allanimations.append(anim)
            if self.item.other_anim:
                name, x, y, num = item.other_anim.split(',')
                pos = (result.defender.position[0], result.defender.position[1] - 1)
                anim = CustomObjects.Animation(GC.IMAGESDICT[name], pos, (int(x), int(y)), int(num), 24)
                gameStateObj.allanimations.append(anim)
            if result.def_damage < 0: # Heal
                pos = (result.defender.position[0], result.defender.position[1] - 1)
                if result.def_damage <= -30:
                    anim = CustomObjects.Animation(GC.IMAGESDICT['MapBigHealTrans'], pos, (5, 4), 16, 24)
                elif result.def_damage <= -15:
                    anim = CustomObjects.Animation(GC.IMAGESDICT['MapMediumHealTrans'], pos, (5, 4), 16, 24)
                else:
                    anim = CustomObjects.Animation(GC.IMAGESDICT['MapSmallHealTrans'], pos, (5, 4), 16, 24)
                gameStateObj.allanimations.append(anim)
            elif result.def_damage == 0 and (item.weapon or (item.spell and item.damage)): # No Damage if weapon or spell with damage!
                pos = result.defender.position[0] - 0.5, result.defender.position[1]
                anim = CustomObjects.Animation(GC.IMAGESDICT['MapNoDamage'], pos, (1, 12), set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 10, 3, 3, 3))
                gameStateObj.allanimations.append(anim)
            # Damage Num
            self.start_damage_num_animation(result)

        elif result.summoning:
            GC.SOUNDDICT['Summon 2'].play()
        else:
            GC.SOUNDDICT['Attack Miss 2'].play()
            anim = CustomObjects.Animation(GC.IMAGESDICT['MapMiss'], result.defender.position, 
                                           (1, 13), set_timing=(1, 1, 1, 1, 1, 1, 1, 1, 1, 10, 3, 3, 3))
            gameStateObj.allanimations.append(anim)
        # Handle status one time animations
        for status in result.def_status:
            if status.one_time_animation:
                stota = status.one_time_animation
                pos = result.defender.position[0], result.defender.position[1] - 1
                gameStateObj.allanimations.append(CustomObjects.Animation(stota.sprite, pos, (stota.x, stota.y), stota.num_frames))
        for status in result.atk_status:
            if status.one_time_animation:
                stota = status.one_time_animation
                pos = result.attacker.position[0], result.attacker.position[1] - 1
                gameStateObj.allanimations.append(CustomObjects.Animation(stota.sprite, pos, (stota.x, stota.y), stota.num_frames))
        self.apply_result(result, gameStateObj)

    def start_damage_num_animation(self, result):
        damage = result.def_damage
        str_damage = str(min(999, abs(damage)))
        left = result.defender.position
        for idx, num in enumerate(str_damage):
            if result.outcome == 2 and result.def_damage > 0:  # Crit
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'SmallYellow')
                self.damage_numbers.append(d)
            elif result.def_damage < 0:
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'SmallCyan')
                self.damage_numbers.append(d)
            elif result.def_damage > 0:
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'SmallRed')
                self.damage_numbers.append(d)

    def start_skip(self):
        self.skip = True
        self.p1.sprite.reset_sprite_offset()
        if self.p2 and isinstance(self.p2, UnitObject.UnitObject):
            self.p2.sprite.reset_sprite_offset()

    def end_skip(self):
        self.skip = False

    def apply_result(self, result, gameStateObj):
        self._apply_result(result, gameStateObj)
        def_pos = result.defender.position
        atk_pos = result.attacker.position
        # Handle Swap Movement!!!
        if result.atk_movement and result.def_movement and def_pos and \
                isinstance(result.defender, UnitObject.UnitObject) and \
                result.atk_movement.mode == "Swap" and result.def_movement.mode == "Swap" and \
                'grounded' not in result.attacker.status_bundle and \
                'grounded' not in result.defender.status_bundle: 
            Action.do(Action.SwapMovement(result.attacker, result.defender), gameStateObj)
        else:
            if result.atk_movement and def_pos and 'grounded' not in result.attacker.status_bundle:
                result.attacker.handle_forced_movement(def_pos, result.atk_movement, gameStateObj)
            if isinstance(result.defender, UnitObject.UnitObject) and result.def_movement and \
                    'grounded' not in result.defender.status_bundle:
                result.defender.handle_forced_movement(atk_pos, result.def_movement, gameStateObj, self.def_pos)
        # Summoning
        if result.summoning:
            result.summoning.sprite.set_transition('warp_in')
            gameStateObj.allunits.append(result.summoning)
            Action.do(Action.SimpleArrive(result.summoning, result.summoning.position), gameStateObj)
        if self.item.call_item_script:
            call_item_script = 'Data/callItemScript.txt'
            if os.path.isfile(call_item_script):
                self.end_skip()
                scene = Dialogue.Dialogue_Scene(call_item_script, unit=self.p1, unit2=self.item, tile_pos=self.p1.position)
                gameStateObj.message.append(scene)
                gameStateObj.stateMachine.changeState('dialogue')

    def begin_phase(self, gameStateObj):
        players = set()
        for result in self.results:
            players.add(result.attacker)
            players.add(result.defender)

            # Calc stats
            a_mode = 'Attack' if result.attacker is self.p1 else 'Defense'
            if result.attacker is self.p1:
                a_weapon = self.item
            elif result.attacker is self.p2:
                a_weapon = self.p2_item
            else:
                a_weapon = self.result.attacker.getMainWeapon()
            a_hit = result.attacker.compute_hit(result.defender, gameStateObj, a_weapon, a_mode)
            a_mt = result.attacker.compute_damage(result.defender, gameStateObj, a_weapon, a_mode)
            a_stats = a_hit, a_mt

            if self.p2 in (result.attacker, result.defender) and self.item.weapon and self.solver.defender_can_counterattack():
                d_mode = 'Defense' if result.attacker is self.p1 else 'Attack'
                if result.defender is self.p1:
                    d_weapon = self.item
                elif result.defender is self.p2:
                    d_weapon = self.p2_item
                else:
                    d_weapon = result.defender.getMainWeapon()
                d_hit = result.defender.compute_hit(result.attacker, gameStateObj, d_weapon, d_mode)
                d_mt = result.defender.compute_damage(result.attacker, gameStateObj, d_weapon, d_mode)
                d_stats = d_hit, d_mt
            else:
                d_stats = None
                d_weapon = None

            # Build health bars
            # If the main defender is in this result
            if self.p2 in (result.attacker, result.defender):
                if result.attacker not in self.health_bars and result.defender not in self.health_bars:
                    self.health_bars = {}  # Clear
                if result.defender in self.health_bars:
                    self.health_bars[result.defender].update_stats(d_stats)
                else:
                    defender_hp = HealthBar.HealthBar('p1' if result.defender is self.p1 else 'p2', result.defender, d_weapon, other=result.attacker, stats=d_stats)
                    self.health_bars[result.defender] = defender_hp
                if result.attacker in self.health_bars:
                    self.health_bars[result.attacker].update_stats(a_stats)
                    if result.attacker is result.defender:
                        self.health_bars[result.attacker].item = a_weapon  # Update item
                else:
                    attacker_hp = HealthBar.HealthBar('p1' if result.attacker is self.p1 else 'p2', result.attacker, a_weapon, other=result.defender, stats=a_stats)
                    self.health_bars[result.attacker] = attacker_hp
            else:
                # if not cf.CONSTANTS['simultaneous_aoe']:
                self.health_bars = {}  # Clear
                if not cf.CONSTANTS['simultaneous_aoe'] or len(self.results) <= 1:
                    swap_stats = result.attacker.team if result.attacker.team != result.defender.team else None
                    a_stats = a_stats if result.attacker.team != result.defender.team else None
                    defender_hp = HealthBar.HealthBar('splash', result.defender, None, other=result.attacker, stats=a_stats, swap_stats=swap_stats)
                    self.health_bars[result.defender] = defender_hp

    # Clean up combat phase
    def end_phase(self, gameStateObj):
        players = set()
        for result in self.results:
            players.add(result.attacker)
            players.add(result.defender)
        self.additional_time = 0

    def draw(self, surf, gameStateObj):
        # Health Bars
        for hp_bar in self.health_bars.values():
            hp_bar.draw(surf, gameStateObj)

        # Damage numbers    
        for damage_num in self.damage_numbers:
            damage_num.update()
            position = damage_num.left
            c_pos = gameStateObj.cameraOffset.get_xy()
            rel_x = position[0] - c_pos[0]
            rel_y = position[1] - c_pos[1]
            damage_num.draw(surf, (rel_x * GC.TILEWIDTH + 4, rel_y * GC.TILEHEIGHT))
        self.damage_numbers = [d for d in self.damage_numbers if not d.done]

    # Clean up everything
    def clean_up(self, gameStateObj, metaDataObj):
        # Remove combat state
        gameStateObj.stateMachine.back()

        if self.skill_used and self.skill_used.combat_art:
            Action.do(Action.Message("%s activated %s" % (self.p1.name, self.skill_used.name)), gameStateObj)

        # Reset states if you're not using a solo skill
        if self.skill_used and self.skill_used.activated_item and self.skill_used.activated_item.can_still_act:
            # Can still attack, can't move
            Action.do(Action.HasTraded(self.p1), gameStateObj)
        else:
            Action.do(Action.HasAttacked(self.p1), gameStateObj)
            if self.p2:
                if isinstance(self.p2, UnitObject.UnitObject):
                    if self.p1.checkIfEnemy(self.p2):
                        Action.do(Action.Message("%s attacked %s" % (self.p1.name, self.p2.name)), gameStateObj)
                    elif self.p1 is not self.p2:
                        Action.do(Action.Message("%s helped %s" % (self.p1.name, self.p2.name)), gameStateObj)
                    else:
                        Action.do(Action.Message("%s used %s" % (self.p1.name, self.item)), gameStateObj)
                else:
                    Action.do(Action.Message("%s attacked a tile" % self.p1.name), gameStateObj)
            else:
                Action.do(Action.Message("%s attacked" % self.p1.name), gameStateObj)

            if not self.p1.has_canto_plus() and not self.event_combat:
                gameStateObj.stateMachine.changeState('wait')  # Event combats do not cause unit to wait

        a_broke_item, d_broke_item = self.find_broken_items()

        # Create all_units list
        all_units = [unit for unit in self.splash] + [self.p1]
        if self.p2 and self.p2 is not self.p1: 
            all_units += [self.p2]

        # Handle death and sprite changing
        for unit in all_units:
            if unit.currenthp <= 0:
                unit.isDying = True
            if isinstance(unit, UnitObject.UnitObject):
                unit.sprite.change_state('normal', gameStateObj)

        self.turnwheel_death_messages(all_units, gameStateObj)

        # === HANDLE STATE STACK ==
        # Handle where we go at very end
        self.handle_state_stack(gameStateObj)

        self.handle_interact_script(gameStateObj)

        self.handle_miracle(gameStateObj, all_units)

        self.handle_item_gain(gameStateObj, all_units)

        # Handle item loss
        if self.p1 is not self.p2:
            self.summon_broken_item_banner(a_broke_item, d_broke_item, gameStateObj)

        # Handle exp and stat gain
        if not self.event_combat and (self.item.weapon or self.item.spell):
            attacker_results = [result for result in self.old_results if result.attacker is self.p1]
            # WEXP and Skills
            if attacker_results and not self.p1.isDying:
                if not self.skill_used:
                    Action.do(Action.ChargeAllSkills(self.p1), gameStateObj)
                self.handle_wexp(attacker_results, self.item, gameStateObj)

            # Exp and Records
            if self.p1.team == 'player' and not self.p1.isDying and not self.p1.isSummon():
                my_exp = 0
                for other_unit in self.splash + [self.p2]:
                    applicable_results = [result for result in attacker_results if result.outcome and
                                          result.defender is other_unit]
                    # Doesn't count if it did 0 damage
                    applicable_results = [result for result in applicable_results if not (self.item.weapon and result.def_damage <= 0)]
                    # Doesn't count if you attacked an ally
                    applicable_results = [result for result in applicable_results if not 
                                          ((self.item.weapon or self.item.detrimental) and result.attacker.checkIfAlly(result.defender))]
                    if isinstance(other_unit, UnitObject.UnitObject) and applicable_results:
                        my_exp, records = self.calc_init_exp_p1(my_exp, other_unit, applicable_results)
                        Action.do(Action.UpdateUnitRecords(self.p1, records), gameStateObj)

                # No free exp for affecting myself or being affected by allies
                if not isinstance(self.p2, UnitObject.UnitObject) or self.p1.checkIfAlly(self.p2):
                    my_exp = int(Utility.clamp(my_exp, 0, 100))
                else:
                    my_exp = int(Utility.clamp(my_exp, cf.CONSTANTS['min_exp'], 100))

                # Also handles actually adding the exp to the unit
                if my_exp > 0:
                    gameStateObj.exp_gain_struct = (self.p1, my_exp, None, 'init')
                    gameStateObj.stateMachine.changeState('exp_gain')

            if self.p2 and isinstance(self.p2, UnitObject.UnitObject) and not self.p2.isDying and self.p2 is not self.p1:
                defender_results = [result for result in self.old_results if result.attacker is self.p2]
                # WEXP and Skills
                if defender_results:
                    Action.do(Action.ChargeAllSkills(self.p2), gameStateObj)
                    self.handle_wexp(defender_results, self.p2_item, gameStateObj)
                # EXP and Records
                if self.p2.team == 'player' and not self.p2.isSummon():  
                    my_exp, records = self.calc_init_exp_p2(defender_results)
                    Action.do(Action.UpdateUnitRecords(self.p2, records), gameStateObj)
                    if my_exp > 0:
                        gameStateObj.exp_gain_struct = (self.p2, my_exp, None, 'init')
                        gameStateObj.stateMachine.changeState('exp_gain')

        # Handle after battle statuses
        self.handle_statuses(gameStateObj)

        self.handle_supports(all_units, gameStateObj)

        self.handle_fatigue(self.old_results, gameStateObj)

        # Handle skills that were used
        self.handle_skill_used(gameStateObj)

        self.arena_cleanup(gameStateObj)
        self.handle_death(gameStateObj, metaDataObj, all_units)

        # Actually remove items
        self.handle_unusable_items(gameStateObj)
        self.remove_broken_items(a_broke_item, d_broke_item, gameStateObj)
