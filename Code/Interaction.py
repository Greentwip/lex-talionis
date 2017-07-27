import random, math
from GlobalConstants import *
from configuration import *
import CustomObjects, UnitObject, Banner, TileObject
import StatusObject, LevelUp, SaveLoad, Utility, Dialogue, Utility, Engine

import logging
logger = logging.getLogger(__name__)

class Result(object):
    def __init__(self, attacker, defender):
        self.attacker = attacker # Which phase this belongs to (actual reference to unit)
        self.defender = defender # Who this is affecting
        self.outcome = 0 # 0 -- Miss, 1 -- Hit, 2 -- Crit
        self.atk_damage = 0 # Damage to the attacker
        self.def_damage = 0 # Damage to the defender
        self.atk_status = [] # Status to the attacker
        self.def_status = [] # Status to the defender
        self.atk_movement = None # Movement to the attacker
        self.def_movement = None # Movement to the defender
        self.summoning = None

# Does not check legality of attack, that is for other functions to do. Assumes attacker can attack all defenders using item and skill
class Solver(object):
    def __init__(self, attacker, defender, def_pos, splash, item, skill_used, event_combat=False):
        self.attacker = attacker
        self.defender = defender
        self.def_pos = def_pos
        # Have splash damage spiral out from position it started on...
        self.splash = sorted(splash, key=lambda s_unit: Utility.calculate_distance(self.def_pos, s_unit.position))
        self.item = item
        self.skill_used = skill_used
        self.event_combat = event_combat # Determines if everything automatically hits, because we're in an event
        # If the item being used has the event combat property, then that too.
        if self.item.event_combat or (self.defender and self.defender.getMainWeapon() and self.defender.getMainWeapon().event_combat):
            self.event_combat = True

        self.state = 'Init'
        self.atk_rounds = 0
        self.def_rounds = 0

        self.uses_count = 0

    def generate_roll(self):
        if self.event_combat or CONSTANTS['rng'] == 'hybrid':
            roll = 0
        elif CONSTANTS['rng'] == 'no_rng':
            roll = CONSTANTS['set_roll']
        elif CONSTANTS['rng'] == 'classic':
            roll = random.randint(0, 99)
        elif CONSTANTS['rng'] == 'true_hit':
            roll = (random.randint(0, 99) + random.randint(0, 99))/2
        elif CONSTANTS['rng'] == 'true_hit+':
            roll = (random.randint(0, 99) + random.randint(0, 99) + random.randint(0, 99))/3
        return roll

    def generate_crit_roll(self):
        if self.event_combat:
            roll = 100
        else:
            roll = random.randint(0, 99)
        return roll

    def handle_crit(self, result, attacker, defender, item, mode, gameStateObj, hybrid):
        to_crit = attacker.compute_crit_hit(defender, gameStateObj, item, mode=mode)
        crit_roll = self.generate_crit_roll()
        if crit_roll < to_crit and not (isinstance(defender, TileObject.TileObject) or 'ignore_crit' in defender.status_bundle):
            result.outcome = 2
            result.def_damage = attacker.compute_damage(defender, gameStateObj, item, mode=mode, hybrid=hybrid, crit=CONSTANTS['crit'])

    def generate_attacker_phase(self, gameStateObj, metaDataObj, defender):
        result = Result(self.attacker, defender)

        # Start
        assert isinstance(defender, UnitObject.UnitObject) or isinstance(defender, TileObject.TileObject), "Only Units and Tiles can engage in combat! %s"%(defender)
        
        to_hit = self.attacker.compute_hit(defender, gameStateObj, self.item, mode="Attack")
        roll = self.generate_roll()

        hybrid = to_hit if CONSTANTS['rng'] == 'hybrid' else None

        #if OPTIONS['debug']: print('To Hit:', to_hit, ' Roll:', roll)
        if self.item.weapon:
            if roll < to_hit and not (defender in self.splash and (isinstance(defender, TileObject.TileObject) or 'evasion' in defender.status_bundle)):
                result.outcome = True
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)
                if CONSTANTS['crit']: 
                    self.handle_crit(result, self.attacker, defender, self.item, 'Attack', gameStateObj, hybrid)
                    
            # Missed but does half damage
            elif self.item.half:
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)/2

        elif self.item.spell:
            if not self.item.hit or roll < to_hit:
                result.outcome = True
                if self.item.damage is not None:
                    result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)
                    if CONSTANTS['crit']: 
                        self.handle_crit(result, self.attacker, defender, self.item, 'Attack', gameStateObj, hybrid)
                elif self.item.heal is not None:
                    result.def_damage = -self.attacker.compute_heal(defender, gameStateObj, self.item, mode='Attack')
                if self.item.movement:
                    result.def_movement = self.item.movement
        else:
            result.outcome = True
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

        # Handle lifelink and vampire
        if result.def_damage > 0:
            if self.item.lifelink:
                result.atk_damage -= result.def_damage
            # Handle Vampire Status
            for status in self.attacker.status_effects:
                if status.vampire and defender.currenthp - result.def_damage <= 0 and \
                   not any(status.miracle and (not status.count or status.count.count > 0) for status in defender.status_effects):
                    result.atk_damage -= eval(status.vampire)
        
        return result

    def generate_defender_phase(self, gameStateObj):
        # Assumes Capable of counterattacking
        result = Result(self.defender, self.attacker)

        to_hit = self.defender.compute_hit(self.attacker, gameStateObj, self.defender.getMainWeapon(), mode="Defense")
        roll = self.generate_roll()

        hybrid = to_hit if CONSTANTS['rng'] == 'hybrid' else None
        #if OPTIONS['debug']: print('To Hit:', to_hit, ' Roll:', roll)
        if roll < to_hit:
            result.outcome = True
            result.def_damage = self.defender.compute_damage(self.attacker, gameStateObj, self.defender.getMainWeapon(), mode="Defense", hybrid=hybrid)
            if CONSTANTS['crit']: 
                self.handle_crit(result, self.defender, self.attacker, self.defender.getMainWeapon(), "Defense", gameStateObj, hybrid)

        # Missed but does half damage
        elif self.defender.getMainWeapon().half:
            result.def_damage = self.defender.compute_damage(self.attacker, gameStateObj, self.defender.getMainWeapon(), mode="Defense", hybrid=hybrid)/2

        if result.outcome:
            for s_id in self.defender.getMainWeapon().status:
                status_object = StatusObject.statusparser(s_id)
                result.def_status.append(status_object)

        # Handle lifelink and vampire
        if result.def_damage > 0:
            if self.defender.getMainWeapon().lifelink:
                result.atk_damage -= result.def_damage
            # Handle Vampire Status
            for status in self.defender.status_effects:
                if status.vampire and self.attacker.currenthp - result.def_damage <= 0 and not any(status.miracle and (not status.count or status.count.count > 0) for status in self.attacker.status_effects):
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
        if weapon and self.item_uses(weapon) and Utility.calculate_distance(self.attacker.position, self.defender.position) in weapon.RNG:
            return True
        else:
            return False

    def defender_has_vantage(self):
        return isinstance(self.defender, UnitObject.UnitObject) and self.outspeed(self.defender, self.attacker) and \
               'vantage' in self.defender.status_bundle and not self.item.cannot_be_countered and \
               self.defender_can_counterattack() and self.item.weapon

    def outspeed(self, unit1, unit2):
        """Whether unit1 outspeeds unit2"""
        return unit1.attackspeed() >= unit2.attackspeed() + CONSTANTS['speed_to_double']

    def def_double(self):
        return (CONSTANTS['def_double'] or 'vantage' in self.defender.status_bundle or 'def_double' in self.defender.status_bundle) and self.def_rounds < 2 and self.outspeed(self.defender, self.attacker)

    def determine_state(self, gameStateObj):
        logger.debug('Interaction State 1: %s', self.state)
        if self.state == 'Init':
            if self.defender:
                if self.defender_has_vantage():
                    self.state = 'Defender'
                else:
                    self.state = 'Attacker'
            elif self.splash:
                self.state = 'Splash'
                self.index = 0
            elif self.item.summon: # Hacky?
                self.state = 'Summon'
            else:
                self.state = 'Done'

        elif self.state == 'Attacker':
            if (not self.defender or isinstance(self.defender, TileObject.TileObject)) and not self.splash: # Just leave if tile mode
                self.state = 'Done'
            elif self.splash:
                self.state = 'Splash'
                self.index = 0
            elif self.defender.currenthp > 0:
                if self.item.brave and self.item_uses(self.item) and self.defender.currenthp > 0:
                    self.state = 'AttackerBrave'
                elif (self.def_rounds < 1 or self.def_double()) and \
                    self.item.weapon and not self.item.cannot_be_countered and isinstance(self.defender, UnitObject.UnitObject) and \
                    self.defender_can_counterattack():
                    self.state = 'Defender'
                elif self.atk_rounds < 2 and self.item.weapon and self.outspeed(self.attacker, self.defender) and self.item_uses(self.item):
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
                    self.state = 'AttackerBrave'
                else:
                    self.state = 'SplashBrave'
            elif (self.def_rounds < 1 or self.def_double()) and \
                self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                self.defender.currenthp > 0 and self.defender_can_counterattack() and not self.item.cannot_be_countered:
                self.state = 'Defender'
            elif self.defender and self.atk_rounds < 2 and self.outspeed(self.attacker, self.defender) and self.item_uses(self.item) and self.defender.currenthp > 0:
                self.state = 'Attacker'
            else:
                self.state = 'Done'

        elif self.state == 'AttackerBrave':
            if self.splash:
                self.state = 'SplashBrave'
                self.index = 0
            elif (self.def_rounds < 1 or self.def_double()) and \
                self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                not self.item.cannot_be_countered and self.defender.currenthp > 0 and self.defender_can_counterattack():
                self.state = 'Defender'
            elif self.atk_rounds < 2 and self.outspeed(self.attacker, self.defender) and self.item_uses(self.item) and self.defender.currenthp > 0:
                self.state = 'Attacker'
            else:
                self.state = 'Done'

        elif self.state == 'SplashBrave':
            if self.index < len(self.splash):
                self.state = 'SplashBrave'
            elif (self.def_rounds < 1 or self.def_double()) and \
                self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                self.defender.currenthp > 0 and self.defender_can_counterattack() and not self.item.cannot_be_countered:
                self.state = 'Defender'
            elif self.defender and self.atk_rounds < 2 and self.outspeed(self.attacker, self.defender) and self.item_uses(self.item) and self.defender.currenthp > 0:
                self.state = 'Attacker'
            else:
                self.state = 'Done'

        elif self.state == 'Defender':
            self.state = 'Done'
            if self.attacker.currenthp > 0:
                if self.defender.getMainWeapon().brave and self.item_uses(self.defender.getMainWeapon()):
                    self.state = 'DefenderBrave'
                elif self.def_rounds < 2 and self.defender_has_vantage():
                    self.state = 'Attacker'
                elif self.atk_rounds < 2 and self.outspeed(self.attacker, self.defender) and self.item_uses(self.item) and not self.item.no_double:
                    self.state = 'Attacker'
                elif self.def_double() and self.defender_can_counterattack() and not self.defender.getMainWeapon().no_double:
                    self.state = 'Defender'

        elif self.state == 'DefenderBrave':
            self.state = 'Done'
            if self.attacker.currenthp > 0:
                if self.def_rounds < 2 and self.defender_has_vantage():
                    self.state = 'Attacker'
                if self.atk_rounds < 2 and self.outspeed(self.attacker, self.defender) and self.item_uses(self.item) and not self.item.no_double:
                    self.state = 'Attacker'
                elif self.def_double() and self.defender_can_counterattack() and not self.defender.getMainWeapon().no_double:
                    self.state = 'Defender'

        elif self.state == 'Summon':
            self.state = 'Done'

    def use_item(self, item):
        if item.uses:
            item.uses.decrement()
        if item.c_uses:
            item.c_uses.decrement()

    def get_a_result(self, gameStateObj, metaDataObj):
        result = None

        self.determine_state(gameStateObj)
        logger.debug('Interaction State 2: %s', self.state)

        if self.state == 'Done':
            result = None

        elif self.state == 'Attacker':
            self.use_item(self.item)
            self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.defender)
            self.atk_rounds += 1

        elif self.state == 'Splash':
            if self.uses_count < 1:
                self.use_item(self.item)
                self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.splash[self.index])
            self.index += 1

        elif self.state == 'AttackerBrave':
            self.use_item(self.item)
            self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.defender)

        elif self.state == 'SplashBrave':
            if self.uses_count < 2:
                self.use_item(self.item)
                self.uses_count += 1
            result = self.generate_attacker_phase(gameStateObj, metaDataObj, self.splash[self.index])
            self.index += 1

        elif self.state == 'Defender':
            self.use_item(self.defender.getMainWeapon())
            self.def_rounds += 1
            result = self.generate_defender_phase(gameStateObj)

        elif self.state == 'DefenderBrave':
            self.use_item(self.defender.getMainWeapon())
            result = self.generate_defender_phase(gameStateObj)

        elif self.state == 'Summon':
            self.use_item(self.item)
            result = self.generate_summon_phase(gameStateObj, metaDataObj)
                
        return result

def convert_positions(gameStateObj, attacker, atk_position, position, item):
    logger.debug('attacker position: %s, position: %s, item: %s', atk_position, position, item)
    if item.weapon or item.spell:
        def_position, splash_positions = item.aoe.get_positions(atk_position, position, gameStateObj.map)
    else:
        def_position, splash_positions = position, []
    logger.debug('def pos: %s, splash pos: %s', def_position, splash_positions)
    if def_position:
        main_defender = [unit for unit in gameStateObj.allunits if unit.position == def_position] # Target units before tiles
        if not main_defender and 'HP' in gameStateObj.map.tile_info_dict[def_position]: # Check if the tile is valid to attack
            main_defender = [gameStateObj.map.tiles[def_position]]
        if main_defender:
            main_defender = main_defender[0]
        else:
            main_defender = None
    else:
        main_defender = None
    splash_units = [unit for unit in gameStateObj.allunits if unit.position in splash_positions]
    # Only attack enemies if we are using a weapon. If we are using a spell, attack all.
    if item.weapon:
        splash_units = [unit for unit in splash_units if attacker.checkIfEnemy(unit)]
    # Beneficial stuff only affects allies
    if item.beneficial and item.spell:
        splash_units = [unit for unit in splash_units if attacker.checkIfAlly(unit)]
        if item.heal: # Only heal allies who need it
            splash_units = [unit for unit in splash_units if unit.currenthp < unit.stats['HP']]
    if item.weapon or (item.spell and not item.beneficial):
        splash_units += [gameStateObj.map.tiles[position] for position in splash_positions if 'HP' in gameStateObj.map.tile_info_dict[position]]
    logger.debug('Main Defender: %s, Splash: %s', main_defender, splash_units)
    return main_defender, splash_units

def start_combat(attacker, defender, def_pos, splash, item, skill_used=None, event_combat=False):
    # Not implemented yet
    if OPTIONS['Animation']:
        pass
    else:
        return Map_Combat(attacker, defender, def_pos, splash, item, skill_used, event_combat)

# Abstract base class for combat - Handles clean up
class Combat(object):
    # Clean up everything
    def clean_up(self, gameStateObj, metaDataObj):
        # Remove combat state
        gameStateObj.stateMachine.back()
        # Reset states if you're not using a solo skill
        if self.skill_used and self.skill_used.active and self.skill_used.active.mode == 'Solo':
            self.p1.hasTraded = True # Can still attack, can't move
            self.p1.hasAttacked = False
        else:
            self.p1.hasAttacked = True
            if not self.p1.has_canto_plus() and not self.event_combat:
                gameStateObj.stateMachine.changeState('wait') # Event combats do not cause unit to wait

        # Handle items that were used
        a_broke_item, d_broke_item = False, False
        if self.item.uses and self.item.uses.uses <= 0:
            a_broke_item = True
        if self.p2 and self.p2.getMainWeapon() and self.p2.getMainWeapon().uses and self.p2.getMainWeapon().uses.uses <= 0:
            d_broke_item = True

        # Handle skills that were used
        if self.skill_used:
            self.skill_used.active.current_charge = 0
            # If no other active skills, can remove active skill charged
            if not any(skill.active and skill.active.required_charge > 0 and skill.active.current_charge >= skill.active.required_charge for skill in self.p1.status_effects):
                self.p1.tags.discard('ActiveSkillCharged')
            if self.skill_used.active.mode == 'Attack':
                self.skill_used.active.reverse_mod()

        # Create all_units list
        all_units = [unit for unit in self.splash] + [self.p1]
        if self.p2: all_units += [self.p2]

        # Handle death and sprite changing
        for unit in all_units:
            if unit.currenthp <= 0:
                unit.isDying = True
            if isinstance(unit, UnitObject.UnitObject):
                unit.sprite.change_state('normal', gameStateObj)

        # === HANDLE STATE STACK ==
        # Handle where we go at very end
        if self.event_combat:
            gameStateObj.message[-1].current_state = "Processing"
        else:
            if self.p1.team == 'player':
                # Check if this is an ai controlled player
                if gameStateObj.stateMachine.getPreviousState() == 'ai':
                    pass
                elif not self.p1.hasAttacked:
                    gameStateObj.stateMachine.changeState('menu')
                elif self.p1.has_canto_plus() and not self.p1.isDying:
                    gameStateObj.stateMachine.changeState('move')
                else:
                    #self.p1.wait(gameStateObj)
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('free')
                    gameStateObj.stateMachine.changeState('wait')
            #else:
                #gameStateObj.stateMachine.changeState('ai')

        ### Handle interact_script
        interact_script = Dialogue.Dialogue_Scene('Data/Level' + str(gameStateObj.counters['level']) + '/interactScript.txt', self.p1, self.p2 if self.p2 else None, event_flag=False)
        gameStateObj.message.append(interact_script)
        gameStateObj.stateMachine.changeState('dialogue')

        # Handle miracle
        for unit in all_units:
            if unit.isDying and isinstance(unit, UnitObject.UnitObject):
                if any(status.miracle and (not status.count or status.count.count > 0) for status in unit.status_effects):
                    unit.handle_miracle(gameStateObj)

        ### Handle item gain
        for unit in all_units:
            if unit.isDying and isinstance(unit, UnitObject.UnitObject):
                for item in unit.items:
                    if item.droppable:
                        item.droppable = False
                        if unit in self.splash or unit is self.p2:
                            self.p1.add_item(item)
                            gameStateObj.banners.append(Banner.acquiredItemBanner(self.p1, item))
                            gameStateObj.stateMachine.changeState('itemgain')
                        elif self.p2:
                            self.p2.add_item(item)
                            gameStateObj.banners.append(Banner.acquiredItemBanner(self.p2, item))
                            gameStateObj.stateMachine.changeState('itemgain')

        ### Handle item loss
        if a_broke_item and self.p1.team == 'player' and not self.p1.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.p1, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        if d_broke_item and self.p2.team == 'player' and not self.p2.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.p2, self.p2.getMainWeapon()))
            gameStateObj.stateMachine.changeState('itemgain')

        ### Handle exp and stat gain
        if not self.event_combat and (self.item.weapon or self.item.spell):
            attacker_results = [result for result in self.old_results if result.attacker is self.p1]
            if not self.p1.isDying and attacker_results and not self.skill_used:
                self.p1.charge()

            if self.p1.team == 'player' and not self.p1.isDying and not 'Mindless' in self.p1.tags and not self.p1.isSummon():
                if attacker_results: #and result.outcome for result in self.old_results):
                    self.p1.increase_wexp(self.item, gameStateObj)
                    
                my_exp = 0
                for other_unit in self.splash + [self.p2]:
                    applicable_results = [result for result in attacker_results if result.outcome and \
                                          result.defender is other_unit]
                    # Doesn't count if it did 0 damage
                    applicable_results = [result for result in applicable_results if not (self.item.weapon and result.def_damage <= 0)]
                    if isinstance(other_unit, UnitObject.UnitObject) and applicable_results:
                        damage_done = sum([result.def_damage_done for result in applicable_results])
                        if not self.item.heal:
                            self.p1.records['damage'] += damage_done

                        if self.item.exp:
                            normal_exp = self.item.exp
                        elif self.item.weapon or not self.p1.checkIfAlly(other_unit):
                            level_diff = other_unit.level - self.p1.level + CONSTANTS['exp_offset']
                            normal_exp = int(CONSTANTS['exp_magnitude']*math.exp(level_diff*CONSTANTS['exp_curve']))
                        elif self.item.spell:
                            if self.item.heal:
                                # Amount healed - exp drops off linearly based on level. But minimum is 5 exp
                                self.p1.records['healing'] += damage_done
                                normal_exp = max(5, int(CONSTANTS['heal_curve']*(damage_done-self.p1.level)+CONSTANTS['heal_magnitude']))
                            else: # Status (Fly, Mage Shield, etc.)
                                normal_exp = CONSTANTS['status_exp']
                        else:
                            normal_exp = 0
                            
                        if other_unit.isDying:
                            self.p1.records['kills'] += 1
                            my_exp += int(CONSTANTS['kill_multiplier']*normal_exp) + (40 if 'Boss' in other_unit.tags else 0)
                        else:
                            my_exp += normal_exp
                        if 'no_exp' in other_unit.status_bundle:
                            my_exp = 0
                        logger.debug('Attacker gained %s exp', my_exp)

                # No free exp for affecting myself or being affected by allies
                if not isinstance(self.p2, UnitObject.UnitObject) or self.p1.checkIfAlly(self.p2):
                    my_exp = int(Utility.clamp(my_exp, 0, 100))
                else:
                    my_exp = int(Utility.clamp(my_exp, 1, 100))

                gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.p1, exp=my_exp)) #Also handles actually adding the exp to the unit
                gameStateObj.stateMachine.changeState('expgain')

            if self.p2 and isinstance(self.p2, UnitObject.UnitObject) and not self.p2.isDying and not self.p2 is self.p1:
                defender_results = [result for result in self.old_results if result.attacker is self.p2]
                if defender_results:
                    self.p2.charge()
                if self.p2.team == 'player' and not 'Mindless' in self.p2.tags and not self.p2.isSummon():
                    if defender_results: # and result.outcome for result in self.old_results):
                        self.p2.increase_wexp(self.p2.getMainWeapon(), gameStateObj)
                        
                    my_exp = 0
                    applicable_results = [result for result in self.old_results if result.outcome and result.attacker is self.p2 \
                                          and result.defender is self.p1 and not result.def_damage <= 0]
                    if applicable_results:
                        damage_done = sum([result.def_damage_done for result in applicable_results])
                        self.p2.records['damage'] += damage_done
                        level_diff = self.p1.level - self.p2.level + CONSTANTS['exp_offset']
                        normal_exp = max(0, int(CONSTANTS['exp_magnitude']*math.exp(level_diff*CONSTANTS['exp_curve'])))
                        if self.p1.isDying:
                            self.p2.records['kills'] += 1
                            my_exp += int(CONSTANTS['kill_multiplier']*normal_exp) + (40 if 'Boss' in self.p1.tags else 0)
                        else:
                            my_exp += normal_exp 
                        if 'no_exp' in self.p1.status_bundle:
                            my_exp = 0

                    # No free exp for affecting myself or being affected by allies
                    if self.p1.checkIfAlly(self.p2):
                        my_exp = Utility.clamp(my_exp, 0, 100)
                    else:
                        my_exp = Utility.clamp(my_exp, 1, 100)

                    gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.p2, exp=my_exp)) #Also handles actually adding the exp to the unit
                    gameStateObj.stateMachine.changeState('expgain')

        # Handle after battle statuses
        for status in self.p1.status_effects:
            if status.status_after_battle and not (self.p1.isDying and status.tether):
                for unit in [self.p2] + self.splash:
                    if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfEnemy(unit) and not unit.isDying:
                        applied_status = StatusObject.statusparser(status.status_after_battle)
                        if status.tether:
                            status.children.append(unit.id)
                            applied_status.parent_id = self.p1.id
                        StatusObject.HandleStatusAddition(applied_status, unit, gameStateObj)
            if status.status_after_help and not self.p1.isDying:
                for unit in [self.p2] + self.splash:
                    if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfAlly(unit) and not unit.isDying:
                        applied_status = StatusObject.statusparser(status.status_after_help)
                        StatusObject.HandleStatusAddition(applied_status, unit, gameStateObj)
            if status.lost_on_attack and (self.item.weapon or self.item.detrimental):
                StatusObject.HandleStatusRemoval(status, self.p1, gameStateObj)
        if self.p2 and isinstance(self.p2, UnitObject.UnitObject) and self.p2.checkIfEnemy(self.p1) and not self.p1.isDying:
            for status in self.p2.status_effects:
                if status.status_after_battle and not (status.tether and self.p2.isDying):
                    applied_status = StatusObject.statusparser(status.status_after_battle)
                    if status.tether:
                        status.children.append(self.p1.id)
                        applied_status.parent_id = self.p2.id
                    StatusObject.HandleStatusAddition(applied_status, self.p1, gameStateObj)

        # Handle death
        for unit in all_units:
            if unit.isDying:
                logger.debug('%s is dying.', unit.name)
                if isinstance(unit, TileObject.TileObject):
                    gameStateObj.map.destroy(unit, gameStateObj)
                else:
                    gameStateObj.stateMachine.changeState('dying')
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(metaDataObj['death_quotes'], unit, event_flag=False))
                    gameStateObj.stateMachine.changeState('dialogue')

        ### Actually remove items
        if a_broke_item:
            self.p1.remove_item(self.item)
        if d_broke_item:
            self.p2.remove_item(self.p2.getMainWeapon())

class Map_Combat(Combat):
    def __init__(self, attacker, defender, def_pos, splash, item, skill_used, event_combat):
        self.p1 = attacker
        self.p2 = defender
        self.def_pos = def_pos
        self.splash = splash
        self.item = item
        self.skill_used = skill_used
        self.event_combat = event_combat

        self.solver = Solver(attacker, defender, def_pos, splash, item, skill_used, event_combat)
        self.results = []
        self.old_results = []

        self.last_update = Engine.get_time()
        self.length_of_combat = 2000
        self.additional_time = 0
        self.combat_state = 'Pre_Init'
        self.aoe_anim_flag = False # Have we shown the aoe animation yet?

        self.health_bars = {}

    def update(self, gameStateObj, metaDataObj, skip=False):
        current_time = Engine.get_time() - self.last_update
        # Get the results needed for this phase
        if not self.results:
            next_result = self.solver.get_a_result(gameStateObj, metaDataObj)
            if next_result is None:
                self.clean_up(gameStateObj, metaDataObj)
                return True
            self.results.append(next_result)
            if CONSTANTS['simultaneous_aoe']:
                while self.solver.state == 'Splash' and self.solver.index < len(self.solver.splash):
                    self.results.append(self.solver.get_a_result(gameStateObj, metaDataObj))

            self.begin_phase(gameStateObj)

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
                if not skip:
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

            elif self.combat_state == 'Init':
                if skip or current_time > self.length_of_combat/5 + self.additional_time:
                    gameStateObj.cursor.drawState = 0
                    gameStateObj.highlight_manager.remove_highlights()

                    if self.item.aoe_anim and not self.aoe_anim_flag:
                        self.aoe_anim_flag = True
                        num_frames = 12
                        if 'AOE_' + self.item.id in IMAGESDICT:
                            image = IMAGESDICT['AOE_' + self.item.id]
                            pos = gameStateObj.cursor.position[0] - image.get_width()/num_frames/TILEWIDTH/2 + 1, gameStateObj.cursor.position[1] - image.get_height()/TILEHEIGHT/2
                            #  
                            #print(gameStateObj.cursor.position, pos)
                            anim = CustomObjects.Animation(IMAGESDICT['AOE_' + self.item.id], pos, (num_frames, 1), num_frames, 32)
                            gameStateObj.allanimations.append(anim)
                        else:
                            logger.warning('%s not in IMAGESDICT. Skipping Animation', 'AOE_' + self.item.id)
                    # Weapons get extra time, spells and items do not need it, since they are one sided.
                    if not self.item.weapon:
                        self.additional_time -= self.length_of_combat/5
                    self.combat_state = '2'

            elif self.combat_state == '2':
                if skip or current_time > 2*self.length_of_combat/5 + self.additional_time:
                    self.combat_state = 'Anim'
                    if self.results[0].attacker.sprite.state in {'combat_attacker', 'combat_defender'}:
                        self.results[0].attacker.sprite.change_state('combat_anim', gameStateObj)

            elif self.combat_state == 'Anim':
                if skip or current_time > 3*self.length_of_combat/5 + self.additional_time:
                    if self.results[0].attacker.sprite.state == 'combat_anim':
                        self.results[0].attacker.sprite.change_state('combat_attacker', gameStateObj)
                    for result in self.results:
                        # TODO: Add offset to sound and animation
                        if result.outcome:
                            if result.attacker is self.p1:
                                item = self.item
                            else:
                                item = result.attacker.getMainWeapon()
                            if isinstance(result.defender, UnitObject.UnitObject):
                                color = item.map_hit_color if item.map_hit_color else (255, 255, 255) # default to white
                                result.defender.begin_flicker(self.length_of_combat/5, color)
                            # Sound
                            if item.sfx_on_hit and item.sfx_on_hit in SOUNDDICT:
                                SOUNDDICT[self.item.sfx_on_hit].play()
                            elif result.defender.currenthp - result.def_damage <= 0: # Lethal
                                SOUNDDICT['Final Hit'].play()
                                if result.outcome == 2: # Critical
                                    for health_bar in self.health_bars.values():
                                        health_bar.shake(3)
                                else:
                                    for health_bar in self.health_bars.values():
                                        health_bar.shake(2)
                            elif result.def_damage < 0: # Heal
                                SOUNDDICT['heal'].play()
                            elif result.def_damage == 0 and (item.weapon or (item.spell and item.damage)): # No Damage if weapon or spell with damage!
                                SOUNDDICT['No Damage'].play()
                            else:
                                if result.outcome == 2: # critical
                                    sound_to_play = 'Critical Hit ' + str(random.randint(1,2))
                                else:
                                    sound_to_play = 'Attack Hit ' + str(random.randint(1,4)) # Choose a random hit sound
                                SOUNDDICT[sound_to_play].play()
                                if result.outcome == 2: # critical
                                    for health_bar in self.health_bars.values():
                                        health_bar.shake(3)
                                else:
                                    for health_bar in self.health_bars.values():
                                        health_bar.shake(1)
                            # Animation
                            if self.item.self_anim:
                                name, x, y, num = item.self_anim.split(',')
                                pos = (result.defender.position[0], result.defender.position[1] - 1)
                                anim = CustomObjects.Animation(IMAGESDICT[name], pos, (int(x), int(y)), int(num), 24)
                                gameStateObj.allanimations.append(anim)
                            elif result.def_damage < 0: # Heal
                                pos = (result.defender.position[0], result.defender.position[1] - 1)
                                if result.def_damage <= -30:
                                   anim = CustomObjects.Animation(IMAGESDICT['MapBigHealTrans'], pos, (5, 4), 16, 24)
                                elif result.def_damage <= -15:
                                    anim = CustomObjects.Animation(IMAGESDICT['MapMediumHealTrans'], pos, (5, 4), 16, 24)
                                else:
                                    anim = CustomObjects.Animation(IMAGESDICT['MapSmallHealTrans'], pos, (5, 4), 16, 24)
                                gameStateObj.allanimations.append(anim)
                            elif result.def_damage == 0 and (item.weapon or (item.spell and item.damage)): # No Damage if weapon or spell with damage!
                                pos = result.defender.position[0] - 0.5, result.defender.position[1]
                                gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapNoDamage'], pos, (1, 12)))
                        elif result.summoning:
                            SOUNDDICT['Summon 2'].play()
                        else:
                            SOUNDDICT['Attack Miss 2'].play()
                            gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapMiss'], result.defender.position, (1, 13)))
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
                    # force update hp bars
                    for hp_bar in self.health_bars.values():
                        hp_bar.update()
                    self.additional_time += max(hp_bar.time_for_change for hp_bar in self.health_bars.values()) if self.health_bars else self.length_of_combat/5
                    self.combat_state = 'Clean'

            elif self.combat_state == 'Clean':
                if skip or current_time > 3*self.length_of_combat/5 + self.additional_time:
                    self.combat_state = 'Wait'

            elif self.combat_state == 'Wait': 
                if skip or current_time > 4*self.length_of_combat/5 + self.additional_time:
                    self.end_phase(gameStateObj)
                    self.old_results += self.results
                    self.results = []
                    self.combat_state = 'Pre_Init'

            if not self.combat_state in ['Pre_Init', 'Init1']:        
                for hp_bar in self.health_bars.values():
                    hp_bar.update()
        return False

    def skip(self):
        self.p1.sprite.reset_sprite_offset()
        if self.p2 and isinstance(self.p2, UnitObject.UnitObject):
            self.p2.sprite.reset_sprite_offset()

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

    def apply_result(self, result, gameStateObj):
        # Status
        for status_obj in result.def_status:
            status_obj.parent_id = result.attacker.id
            StatusObject.HandleStatusAddition(status_obj, result.defender, gameStateObj)
        for status_obj in result.atk_status:
            status_obj.parent_id = result.defender.id
            StatusObject.HandleStatusAddition(status_obj, result.attacker, gameStateObj)
        # Calculate true damage done
        self.calc_damage_done(result)
        # HP
        result.attacker.currenthp -= result.atk_damage
        result.attacker.currenthp = Utility.clamp(result.attacker.currenthp, 0, result.attacker.stats['HP'])
        if result.defender:
            result.defender.currenthp -= result.def_damage
            result.defender.currenthp = Utility.clamp(result.defender.currenthp, 0, result.defender.stats['HP'])
        # Movement
        #print(self.current_result)
        if result.atk_movement and result.defender.position:
            #print('ATK', self.current_result.atk_movement)
            def_position = result.defender.position
            result.attacker.handle_forced_movement(def_position, result.atk_movement, gameStateObj)
        if result.def_movement:
            #print('DEF', self.current_result.def_movement)
            atk_position = result.attacker.position
            result.defender.handle_forced_movement(atk_position, result.def_movement, gameStateObj)
        # Summoning
        if result.summoning:
            result.summoning.sprite.set_transition('warp_in')
            gameStateObj.allunits.append(result.summoning)

    def begin_phase(self, gameStateObj):
        players = set()
        for result in self.results:
            players.add(result.attacker)
            players.add(result.defender)

            # Calc stats
            a_mode = 'Attack' if result.attacker is self.p1 else 'Defense'
            a_weapon = self.item if result.attacker is self.p1 else result.attacker.getMainWeapon()
            a_hit = result.attacker.compute_hit(result.defender, gameStateObj, a_weapon, a_mode)
            a_mt = result.attacker.compute_damage(result.defender, gameStateObj, a_weapon, a_mode)
            a_stats = a_hit, a_mt

            if self.p2 in [result.attacker, result.defender] and self.item.weapon and self.solver.defender_can_counterattack():
                d_mode = 'Defense' if result.attacker is self.p1 else 'Attack'
                d_weapon = result.defender.getMainWeapon()
                d_hit = result.defender.compute_hit(result.attacker, gameStateObj, d_weapon, d_mode)
                d_mt = result.defender.compute_damage(result.attacker, gameStateObj, d_weapon, d_mode)
                d_stats = d_hit, d_mt
            else:
                d_stats = None
                d_weapon = None

            ### Build health bars
            # If the main defender is in this result
            if self.p2 in [result.attacker, result.defender]:
                if not result.attacker in self.health_bars and not result.defender in self.health_bars:
                    self.health_bars = {} # Clear
                if result.defender in self.health_bars:
                    self.health_bars[result.defender].update_stats(d_stats)
                else:
                    defender_hp = HealthBar('p1' if result.defender is self.p1 else 'p2', result.defender, d_weapon, other=result.attacker, stats=d_stats)
                    self.health_bars[result.defender] = defender_hp
                if result.attacker in self.health_bars:
                    self.health_bars[result.attacker].update_stats(a_stats)
                else:
                    attacker_hp = HealthBar('p1' if result.attacker is self.p1 else 'p2', result.attacker, a_weapon, other=result.defender, stats=a_stats)
                    self.health_bars[result.attacker] = attacker_hp
            else:
                #if not CONSTANTS['simultaneous_aoe']:
                self.health_bars = {} # Clear
                if not CONSTANTS['simultaneous_aoe'] or len(self.results) <= 1:
                    swap_stats = result.attacker.team if result.attacker.team != result.defender.team else None
                    a_stats = a_stats if result.attacker.team != result.defender.team else None
                    defender_hp = HealthBar('splash', result.defender, None, other=result.attacker, stats=a_stats, swap_stats=swap_stats)
                    self.health_bars[result.defender] = defender_hp
            
        # Small state changes
        for player in players:
            if isinstance(player, UnitObject.UnitObject):
                player.lock_active()

    # Clean up combat phase
    def end_phase(self, gameStateObj):
        players = set()
        for result in self.results:
            players.add(result.attacker)
            players.add(result.defender)
        # Small state changes
        for player in players:
            if isinstance(player, UnitObject.UnitObject):
                player.unlock_active()
        self.additional_time = 0

    def draw(self, surf, gameStateObj):
        for hp_bar in self.health_bars.values():
            hp_bar.draw(surf, gameStateObj)

class HealthBar(object):
    def __init__(self, draw_method, unit, item, other=None, stats=None, time_for_change=400, swap_stats=None):
        self.last_update = 0
        self.time_for_change = time_for_change
        self.transition_flag = False
        self.blind_speed = 1/8. # 8 frames to fully transition
        self.true_position = None

        self.reset()
        self.fade_in()
        self.change_unit(unit, item, other, stats, draw_method, swap_stats)

    def force_position_update(self, gameStateObj):
        if self.unit:
            width, height = self.bg_surf.get_width(), self.bg_surf.get_height()
            self.determine_position(gameStateObj, (width, height))

    def draw(self, surf, gameStateObj):
        if self.unit:
            width, height = self.bg_surf.get_width(), self.bg_surf.get_height()
            true_height = height + self.c_surf.get_height()
            if self.stats:
                bg_surf = Engine.create_surface((width, true_height))
            else:
                bg_surf = Engine.create_surface((width, height))
            bg_surf.blit(self.bg_surf, (0,0))
            # Blit Name
            name_size = FONT['text_numbers'].size(self.unit.name)
            position = width - name_size[0] - 4, 3
            FONT['text_numbers'].blit(self.unit.name, bg_surf, position)
            # Blit item -- Must be blit every frame
            if self.item:
                if self.other and isinstance(self.other, UnitObject.UnitObject):
                    white = True if (self.item.effective and any([comp in self.other.tags for comp in self.item.effective.against])) or \
                    any([status.weakness and status.weakness.damage_type in self.item.TYPE for status in self.other.status_effects]) else False
                else:
                    white = False
                self.item.draw(bg_surf, (2, 3), white)

                # Blit advantage -- This must be blit every frame
                if isinstance(self.other, UnitObject.UnitObject) and self.other.getMainWeapon() and self.unit.checkIfEnemy(self.other):
                    advantage, e_advantage = CustomObjects.WEAPON_TRIANGLE.compute_advantage(self.item, self.other.getMainWeapon())
                    if advantage > 0:
                        UpArrow = Engine.subsurface(IMAGESDICT['ItemArrows'], (self.unit.arrowAnim[self.unit.arrowCounter]*7, 0, 7, 10))
                        bg_surf.blit(UpArrow, (11, 7))
                    elif advantage < 0:
                        DownArrow = Engine.subsurface(IMAGESDICT['ItemArrows'], (self.unit.arrowAnim[self.unit.arrowCounter]*7, 10, 7, 10))
                        bg_surf.blit(DownArrow, (11, 7))

            # Blit health bars -- Must be blit every frame
            if self.unit.stats['HP']:
                fraction_hp = float(self.true_hp)/self.unit.stats['HP']
            else:
                fraction_hp = 0
            index_pixel = int(50*fraction_hp)
            position = 25, 22
            bg_surf.blit(Engine.subsurface(IMAGESDICT['HealthBar'], (0,0,index_pixel,2)), position)

            # Blit HP -- Must be blit every frame
            font = FONT['number_small2']
            if self.transition_flag:
                font = FONT['number_big2']
            position = 22 - font.size(str(int(self.true_hp)))[0], height - 17
            font.blit(str(int(self.true_hp)), bg_surf, position)

            # C surf
            if self.stats:
                if not self.stats_surf:
                    self.stats_surf = self.build_c_surf()
                bg_surf.blit(self.stats_surf, (0, height))

            if not self.true_position:
                self.determine_position(gameStateObj, (width, height))

            if self.stats:
                blit_surf = Engine.subsurface(bg_surf, (0, true_height/2 - int(true_height*self.blinds/2), width, int(true_height*self.blinds)))
                y_pos = self.true_position[1] + true_height/2 - int(true_height*self.blinds/2)
            else:
                blit_surf = Engine.subsurface(bg_surf, (0, height/2 - int(height*self.blinds/2), width, int(height*self.blinds)))
                y_pos = self.true_position[1] + height/2 - int(height*self.blinds/2)
            surf.blit(blit_surf, (self.true_position[0] + self.shake_offset[0], y_pos + self.shake_offset[1]))

            # blit Gem
            if self.blinds == 1 and self.gem and self.order:
                x, y = self.true_position[0] + self.shake_offset[0], self.true_position[1] + self.shake_offset[1]
                if self.order == 'left':
                    position = (x + 2, y - 3)
                elif self.order == 'right':
                    position = (x + 56, y - 3)
                elif self.order == 'middle':
                    position = (x + 27, y - 3)
                surf.blit(self.gem, position)

    def build_c_surf(self):
        c_surf = self.c_surf.copy()
        # Blit Hit
        if self.stats[0] is not None:
            hit = str(self.stats[0])
        else:
            hit = '--'
        position = c_surf.get_width()/2 - FONT['number_small2'].size(hit)[0] - 1, -2
        FONT['number_small2'].blit(hit, c_surf, position)
        # Blit Damage
        if self.stats[1] is not None:
            damage = str(self.stats[1])
        else:
            damage = '--'
        position = c_surf.get_width() - FONT['number_small2'].size(damage)[0] - 2, -2
        FONT['number_small2'].blit(damage, c_surf, position)
        return c_surf

    def determine_position(self, gameStateObj, (width, height)):
        # Determine position
        self.true_position = self.topleft
        #logger.debug("Topleft %s", self.topleft)
        if self.topleft in {'p1', 'p2'}:
            # Get the two positions, along with camera position
            pos1 = self.unit.position
            pos2 = self.other.position
            c_pos = gameStateObj.cameraOffset.get_xy()
            if self.topleft == 'p1':
                left = True if pos1[0] <= pos2[0] else False
            else:
                left = True if pos1[0] < pos2[0] else False
            self.order = 'left' if left else 'right'
            #logger.debug("%s %s %s", pos1, pos2, left)
            x_pos = WINWIDTH/2 - width if left else WINWIDTH/2
            rel_1 = pos1[1] - c_pos[1]
            rel_2 = pos2[1] - c_pos[1]
            #logger.debug("Health_Bar_Pos %s %s", rel_1, rel_2)
            # If both are on top of screen
            if rel_1 < 5 and rel_2 < 5:
                rel = max(rel_1, rel_2)
                y_pos = (rel+1)*TILEHEIGHT + 12
            # If both are on bottom of screen
            elif rel_1 >= 5 and rel_2 >= 5:
                rel = min(rel_1, rel_2)
                y_pos = rel*TILEHEIGHT - 12 - height - 13 # c_surf
            # Find largest gap and place it in the middle
            else:
                top_gap = min(rel_1, rel_2)
                bottom_gap = (TILEY-1) - max(rel_1, rel_2)
                middle_gap = abs(rel_1 - rel_2)
                #logger.debug("Gaps %s %s %s", top_gap, bottom_gap, middle_gap)
                if top_gap > bottom_gap and top_gap > middle_gap:
                    y_pos = top_gap * TILEHEIGHT - 12 - height - 13 # c_surf
                elif bottom_gap > top_gap and bottom_gap > middle_gap:
                    y_pos = (bottom_gap+1) * TILEHEIGHT + 12
                else:
                    y_pos = WINHEIGHT/4 - height/2 - 13/2 if rel_1 < 5 else 3*WINHEIGHT/4 - height/2 - 13/2
                    x_pos = WINWIDTH/4 - width/2 if pos1[0] - c_pos[0] > TILEX/2 else 3*WINWIDTH/4 - width/2
                    self.order = 'middle'
            self.true_position = (x_pos, y_pos)
            #logger.debug('True Position %s %s', x_pos, y_pos)
        elif self.topleft == 'splash': # self.topleft == 'auto':
            # Find x Position
            pos_x = self.unit.position[0] - gameStateObj.cameraOffset.get_x()
            pos_x = Utility.clamp(pos_x, 3, TILEX - 2)
            # Find y position
            if self.unit.position[1] - gameStateObj.cameraOffset.get_y() < TILEY/2: # IF unit is at top of screen
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() + 2
            else:
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() - 3
            self.true_position = pos_x*TILEWIDTH - width/2, pos_y*TILEHEIGHT - 8
            self.order = 'middle'
            #logger.debug('Other True Position %s %s', pos_x, pos_y)

    def fade_in(self):
        self.blinds = 0

    def fade_out(self):
        pass

    def shake(self, num):
        self.current_shake = 1
        if num == 1:
            self.shake_set = [(-3, -3), (0, 0), (3, 3), (0, 0)]
        elif num == 2:
            self.shake_set = [(3, 3), (0, 0), (0, 0), (3, 3), (-3, -3), (3, 3), (-3, -3), (0, 0)]
        elif num == 3:
            self.shake_set = [(3, 3), (0, 0), (0, 0), (-3, -3), (0, 0), (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), (3, 3), (0, 0), (-3, -3), (3, 3), (0, 0)]

    def update(self, status_obj=False):
        # Make blinds wider
        self.blinds = Utility.clamp(self.blinds, self.blinds + self.blind_speed, 1)
        # Handle HP bar
        if self.unit and self.blinds == 1:
            # Handle shake
            if self.current_shake:
                self.shake_offset = self.shake_set[self.current_shake - 1]
                self.current_shake += 1
                if self.current_shake > len(self.shake_set):
                    self.current_shake = 0
            if self.true_hp != self.unit.currenthp and not self.transition_flag:
                self.transition_flag = True
                self.time_for_change = max(400, abs(self.true_hp - self.unit.currenthp)*32)
                self.last_update = Engine.get_time() + (200 if status_obj else 0)
            if self.transition_flag and Engine.get_time() > self.last_update:
                self.true_hp = Utility.easing(Engine.get_time() - self.last_update, self.oldhp, self.unit.currenthp - self.oldhp, self.time_for_change)
                #print(self.true_hp, Engine.get_time(), self.oldhp, self.unit.currenthp, self.time_for_change)
                if self.unit.currenthp - self.oldhp > 0 and self.true_hp > self.unit.currenthp:
                    self.true_hp = self.unit.currenthp
                    self.oldhp = self.true_hp
                    self.transition_flag = False
                elif self.unit.currenthp - self.oldhp < 0 and self.true_hp < self.unit.currenthp:
                    self.true_hp = self.unit.currenthp
                    self.oldhp = self.true_hp
                    self.transition_flag = False

    def change_unit(self, unit, item, other=None, stats=None, draw_method=None, force_stats=None):
        self.stats_surf = None
        if draw_method:
            self.topleft = draw_method
            self.true_position = None # Reset true position

        if unit: 
            if unit != self.unit or other != self.other: # Only if truly new...
                self.fade_in()
            self.oldhp = unit.currenthp
            self.true_hp = unit.currenthp
            self.last_update = Engine.get_time()

            self.unit = unit
            self.item = item
            if other:
                self.other = other
            if stats:
                self.stats = stats

            if isinstance(unit, TileObject.TileObject):
                self.bg_surf = IMAGESDICT['RedHealth']
                self.c_surf = IMAGESDICT['RedCombatStats']
            elif unit.team == 'player':
                self.bg_surf = IMAGESDICT['BlueHealth']
                self.c_surf = IMAGESDICT['BlueCombatStats']
                self.gem = IMAGESDICT['BlueCombatGem']
            elif unit.team == 'enemy':
                self.bg_surf = IMAGESDICT['RedHealth']
                self.c_surf = IMAGESDICT['RedCombatStats']
                self.gem = IMAGESDICT['RedCombatGem']
            elif unit.team == 'enemy2':
                self.bg_surf = IMAGESDICT['PurpleHealth']
                self.c_surf = IMAGESDICT['PurpleCombatStats']
                self.gem = IMAGESDICT['PurpleCombatGem']
            elif unit.team == 'other':
                self.bg_surf = IMAGESDICT['GreenHealth']
                self.c_surf = IMAGESDICT['GreenCombatStats']
                self.gem = IMAGESDICT['GreenCombatGem']

            if force_stats:
                if force_stats == 'player':
                    self.c_surf = IMAGESDICT['BlueCombatStats']
                elif force_stats == 'enemy':
                    self.c_surf = IMAGESDICT['RedCombatStats']
                elif force_stats == 'enemy2':
                    self.c_surf = IMAGESDICT['PurpleCombatStats']
                elif force_stats == 'other':
                    self.c_surf = IMAGESDICT['GreenCombatStats']
        else:
            self.reset()


    def update_stats(self, stats):
        self.stats_surf = None
        self.stats = stats
        
    def reset(self):
        self.unit = None
        self.item = None
        self.other = None
        self.true_hp = 0
        self.bg_surf = None
        self.c_surf = None
        self.gem = None
        self.stats = None
        # for shake
        self.shake_set = [(0, 0)]
        self.shake_offset = (0, 0)
        self.current_shake = 0