import random, math
from imagesDict import getImages
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
        self.outcome = False
        self.atk_damage = 0 # Damage to the attacker
        self.def_damage = 0 # Damage to the defender
        self.atk_status = [] # Status to the attacker
        self.def_status = [] # Status to the defender
        self.atk_movement = None # Movement to the attacker
        self.def_movement = None # Movement to the defender
        self.summoning = []

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

    def generate_attacker_phase(self, gameStateObj, metaDataObj, defender):
        result = Result(self.attacker, defender)

        # Start
        assert isinstance(defender, UnitObject.UnitObject) or isinstance(defender, TileObject.TileObject), "Only Units and Tiles can engage in combat! %s"%(defender)
        
        to_hit = self.attacker.compute_hit(defender, gameStateObj, self.item, mode="Attack")
        roll = self.generate_roll()

        hybrid = to_hit if CONSTANTS['rng'] == 'hybrid' else None

        #if OPTIONS['debug']: print('To Hit:', to_hit, ' Roll:', roll)
        if self.item.weapon:
            if roll < to_hit and not (defender in self.splash and (isinstance(defender, TileObject.TileObject) or any(status.evasion for status in defender.status_effects))):
                result.outcome = True
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)
            # Missed but does half damage
            elif self.item.half:
                result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)/2

        elif self.item.spell:
            if not self.item.hit or roll < to_hit:
                result.outcome = True
                if self.item.damage is not None:
                    result.def_damage = self.attacker.compute_damage(defender, gameStateObj, self.item, mode='Attack', hybrid=hybrid)
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
                result.summoning.append(SaveLoad.create_summon(self.item.summon, self.attacker, self.def_pos, metaDataObj))

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
        the_summon = SaveLoad.create_summon(self.item.summon, self.attacker, self.def_pos, metaDataObj)

        result = Result(self.attacker, the_summon)
        result.summoning.append(the_summon)

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
               any(status.vantage for status in self.defender.status_effects) and not self.item.cannot_be_countered and \
               self.defender_can_counterattack() and self.item.weapon

    def outspeed(self, unit1, unit2):
        """Whether unit1 outspeeds unit2"""
        return unit1.attackspeed() >= unit2.attackspeed() + CONSTANTS['speed_to_double']

    def def_double(self):
        return (CONSTANTS['def_double'] or any(status.vantage or status.def_double for status in self.defender.status_effects)) and self.def_rounds < 2 and self.outspeed(self.defender, self.attacker)

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

class Combat(object):
    def __init__(self, attacker, defender, def_pos, splash, item, skill_used=None, event_combat=False): 
        self.attacker = attacker
        self.defender = defender
        #print('Combat', attacker, defender, attacker.position, defender.position)
        self.def_pos = def_pos
        self.splash = splash
        self.item = item
        self.skill_used = skill_used
        self.event_combat = event_combat

        self.solver = Solver(attacker, defender, def_pos, splash, item, skill_used, event_combat)
        self.current_result = None
        
        self.last_update = Engine.get_time()
        self.length_of_combat = 2000
        self.combat_state = 'Pre_Init'

        # Get mode
        if self.splash:
            self.mode = 'splash'
        elif self.defender and self.defender is not self.attacker:
            self.mode = 'defender'
        else:
            self.mode = 'auto'

        if self.defender and self.defender is not self.attacker:
            self.atk_health_bar = HealthBar('atkauto', attacker, item, defender)
            self.def_health_bar = HealthBar('defauto', defender, defender.getMainWeapon(), attacker)
        elif self.splash:
            self.atk_health_bar = HealthBar('atkauto', attacker, item, splash[0])
            self.def_health_bar = HealthBar('defauto', splash[0], splash[0].getMainWeapon())
        else:
            self.atk_health_bar = HealthBar('atkauto', attacker, item)
            self.def_health_bar = HealthBar('auto', None, None)

        self.old_results = []

    def update(self, gameStateObj, metaDataObj, skip=False):
        current_time = Engine.get_time() - self.last_update
        if not self.current_result:
            self.current_result = self.solver.get_a_result(gameStateObj, metaDataObj)
            if self.current_result is None:
                self.clean_up(gameStateObj, metaDataObj)
                return True

            self.begin_a_result(gameStateObj)

        elif self.current_result:
            if self.combat_state == 'Pre_Init':
                # Move camera
                if self.current_result.defender:
                    gameStateObj.cursor.setPosition(self.current_result.defender.position, gameStateObj)
                else:
                    gameStateObj.cursor.setPosition(self.def_pos, gameStateObj)
                if not skip:
                    gameStateObj.stateMachine.changeState('move_camera')
                self.combat_state = 'Init1'
            elif self.combat_state == 'Init1':
                self.last_update = Engine.get_time()
                self.combat_state = 'Init'
                gameStateObj.cursor.drawState = 2
                self.atk_health_bar.force_position_update(gameStateObj)
                self.def_health_bar.force_position_update(gameStateObj)

            elif self.combat_state == 'Init':
                if skip or current_time > self.length_of_combat/5:
                    gameStateObj.cursor.drawState = 0
                    gameStateObj.highlight_manager.remove_highlights()
                    self.combat_state = '2'

            elif self.combat_state == '2':
                if skip or current_time > 2*self.length_of_combat/5:
                    self.combat_state = 'Anim'
            
            elif self.combat_state == 'Anim':
                if skip or current_time > 3*self.length_of_combat/5:
                    if self.current_result.defender:
                        if self.current_result.outcome:
                            if isinstance(self.current_result.defender, UnitObject.UnitObject):
                                self.current_result.defender.begin_flicker_white(self.length_of_combat/5)
                            if self.current_result.defender.currenthp - self.current_result.def_damage <= 0: # Lethal
                                SOUNDDICT['Final Hit'].play()
                            elif self.current_result.def_damage < 0: # Heal
                                SOUNDDICT['heal'].play()
                                pos = (self.current_result.defender.position[0], self.current_result.defender.position[1] - 1)
                                if self.current_result.def_damage <= -30:
                                    gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapBigHealTrans'], pos, (5, 4), 16, 24))
                                elif self.current_result.def_damage <= -15:
                                    gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapMediumHealTrans'], pos, (5, 4), 16, 24))
                                else:
                                    gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapSmallHealTrans'], pos, (5, 4), 16, 24))
                            elif self.current_result.def_damage == 0 and (self.item.weapon or (self.item.spell and self.item.damage)): # No Damage if weapon or spell with damage!
                                SOUNDDICT['No Damage'].play()
                                pos = self.current_result.defender.position[0] - 0.5, self.current_result.defender.position[1]
                                gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapNoDamage'], pos, (1, 12)))
                            else:
                                sound_to_play = 'Attack Hit ' + str(random.randint(1,4)) # Choose a random hit sound
                                SOUNDDICT[sound_to_play].play()
                        elif self.current_result.summoning:
                            # Play sound for summoning
                            pass
                        else:
                            SOUNDDICT['Attack Miss 2'].play()
                            gameStateObj.allanimations.append(CustomObjects.Animation(IMAGESDICT['MapMiss'], self.current_result.defender.position, (1, 13)))
                        # Handle status one time animations
                        for status in self.current_result.def_status:
                            if status.one_time_animation:
                                stota = status.one_time_animation
                                pos = self.current_result.defender.position[0], self.current_result.defender.position[1] - 1
                                gameStateObj.allanimations.append(CustomObjects.Animation(stota.sprite, pos, (stota.x, stota.y), stota.num_frames))
                        for status in self.current_result.atk_status:
                            if status.one_time_animation:
                                stota = status.one_time_animation
                                pos = self.current_result.attacker.position[0], self.current_result.attacker.position[1] - 1
                                gameStateObj.allanimations.append(CustomObjects.Animation(stota.sprite, pos, (stota.x, stota.y), stota.num_frames))
                    self.apply_result(gameStateObj)
                    self.combat_state = 'Clean'

            elif self.combat_state == 'Clean':
                if skip or current_time > 4*self.length_of_combat/5:
                    self.combat_state = 'Wait'

            elif self.combat_state == 'Wait': 
                if skip or current_time > self.length_of_combat:
                    self.end_a_result(gameStateObj)
                    self.old_results.append(self.current_result)
                    self.current_result = None
                    self.combat_state = 'Pre_Init'

            if not self.combat_state in ['Pre_Init', 'Init1']:        
                self.atk_health_bar.update()
                self.def_health_bar.update()
        return False

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

    def apply_result(self, gameStateObj):
        # Status
        for status_obj in self.current_result.def_status:
            status_obj.parent_id = self.current_result.attacker.id
            StatusObject.HandleStatusAddition(status_obj, self.current_result.defender, gameStateObj)
            if status_obj.aura: # Re-arrive at where you are at so you can give your friendos their status
                self.current_result.defender.arrive(gameStateObj)
        for status_obj in self.current_result.atk_status:
            status_obj.parent_id = self.current_result.defender.id
            StatusObject.HandleStatusAddition(status_obj, self.current_result.attacker, gameStateObj)
            if status_obj.aura: # Re-arrive at where you are at so you can give your friendos their status
                self.current_result.attacker.arrive(gameStateObj)
        # Calculate true damage done
        self.calc_damage_done(self.current_result)
        # HP
        self.current_result.attacker.currenthp -= self.current_result.atk_damage
        self.current_result.attacker.currenthp = Utility.clamp(self.current_result.attacker.currenthp, 0, self.current_result.attacker.stats['HP'])
        if self.current_result.defender:
            self.current_result.defender.currenthp -= self.current_result.def_damage
            self.current_result.defender.currenthp = Utility.clamp(self.current_result.defender.currenthp, 0, self.current_result.defender.stats['HP'])
        # Movement
        #print(self.current_result)
        if self.current_result.atk_movement and self.current_result.defender.position:
            #print('ATK', self.current_result.atk_movement)
            def_position = self.current_result.defender.position
            self.current_result.attacker.handle_forced_movement(def_position, self.current_result.atk_movement, gameStateObj)
        if self.current_result.def_movement:
            #print('DEF', self.current_result.def_movement)
            atk_position = self.current_result.attacker.position
            self.current_result.defender.handle_forced_movement(atk_position, self.current_result.def_movement, gameStateObj)
        # Summoning
        for unit in self.current_result.summoning:
            unit.sprite.set_transition('warp_in')
        gameStateObj.allunits += self.current_result.summoning

    def begin_a_result(self, gameStateObj):
        if self.mode == 'defender':
            # Attacker
            a_hit = self.attacker.compute_hit(self.defender, gameStateObj, self.item, 'Attack')
            a_mt = self.attacker.compute_damage(self.defender, gameStateObj, self.item, 'Attack')
            self.atk_health_bar.change_unit(self.attacker, self.item, other=self.defender, stats=(a_hit, a_mt))
            # Defender
            if self.item.weapon and self.solver.defender_can_counterattack():
                d_hit = self.defender.compute_hit(self.attacker, gameStateObj, self.defender.getMainWeapon(), 'Defense')
                d_mt = self.defender.compute_damage(self.attacker, gameStateObj, self.defender.getMainWeapon(), 'Defense')
                d_stats = d_hit, d_mt
            else:
                d_stats = None
            self.def_health_bar.change_unit(self.defender, self.defender.getMainWeapon(), other=self.attacker, stats=d_stats, topleft='defauto')
        elif self.mode == 'splash':
            # Attacker
            a_hit = self.attacker.compute_hit(self.current_result.defender, gameStateObj, self.item, 'Attack')
            a_mt = self.attacker.compute_damage(self.current_result.defender, gameStateObj, self.item, 'Attack')
            self.atk_health_bar.change_unit(self.attacker, self.item, other=self.current_result.defender, stats=(a_hit, a_mt))
            # Defender
            if self.item.weapon and self.solver.defender_can_counterattack() and self.current_result.defender in [self.defender, self.attacker]:
                d_hit = self.defender.compute_hit(self.attacker, gameStateObj, self.defender.getMainWeapon(), 'Defense')
                d_mt = self.defender.compute_damage(self.attacker, gameStateObj, self.defender.getMainWeapon(), 'Defense')
                d_stats = d_hit, d_mt
                self.def_health_bar.change_unit(self.defender, self.defender.getMainWeapon(), other=self.attacker, stats=d_stats, topleft='defauto')
            else:
                d_stats = None
                self.def_health_bar.change_unit(self.current_result.defender, self.current_result.defender.getMainWeapon(), other=self.current_result.attacker, stats=d_stats, topleft='defauto')
        elif self.mode == 'auto':
            #self.atk_health_bar.change_unit()
            pass

        self.current_result.attacker.lock_active()
        if self.current_result.defender and isinstance(self.current_result.defender, UnitObject.UnitObject):
            self.current_result.defender.lock_active()
        self.current_result.attacker.isAttacking = True

    # Clean up one combat round
    def end_a_result(self, gameStateObj):
        # if OPTIONS['debug']: print("End Result")
        self.current_result.attacker.unlock_active()
        if self.current_result.defender and isinstance(self.current_result.defender, UnitObject.UnitObject):
            self.current_result.defender.unlock_active()
        self.current_result.attacker.isAttacking = False

        self.applied_flag = False

    def draw(self, surf, gameStateObj):
        #if not self.combat_state in ['Pre_Init', 'Init1']:  
        self.atk_health_bar.draw(surf, gameStateObj)
        if self.defender is not self.attacker:
            self.def_health_bar.draw(surf, gameStateObj)

    # Clean up everything
    def clean_up(self, gameStateObj, metaDataObj):
        # Remove combat state
        gameStateObj.stateMachine.back()
        # Reset states if you're not using a solo skill
        if self.skill_used and self.skill_used.active and self.skill_used.active.mode == 'Solo':
            self.attacker.hasTraded = True # Can still attack, can't move
            self.attacker.hasAttacked = False
        else:
            self.attacker.hasAttacked = True
            if not self.attacker.has_canto_plus() and not self.event_combat:
                gameStateObj.stateMachine.changeState('wait') # Event combats do not cause unit to wait

        # Handle items that were used
        a_broke_item, d_broke_item = False, False
        if self.item.uses and self.item.uses.uses <= 0:
            a_broke_item = True
        if self.defender and self.defender.getMainWeapon() and self.defender.getMainWeapon().uses and self.defender.getMainWeapon().uses.uses <= 0:
            d_broke_item = True

        # Handle skills that were used
        if self.skill_used:
            self.skill_used.active.current_charge = 0
            if self.skill_used.active.mode == 'Attack':
                self.skill_used.active.reverse_mod()

        # Create all_units list
        all_units = [unit for unit in self.splash] + [self.attacker]
        if self.defender: all_units += [self.defender]

        # Handle death
        for unit in all_units:
            if unit.currenthp <= 0:
                unit.isDying = True

        # === HANDLE STATE STACK ==
        # Handle where we go at very end
        if self.event_combat:
            gameStateObj.message[-1].current_state = "Processing"
        else:
            if self.attacker.team == 'player':
                if not self.attacker.hasAttacked:
                    gameStateObj.stateMachine.changeState('menu')
                elif self.attacker.has_canto_plus() and not self.attacker.isDying:
                    gameStateObj.stateMachine.changeState('move')
                else:
                    #self.attacker.wait(gameStateObj)
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('free')
                    gameStateObj.stateMachine.changeState('wait')
            #else:
                #gameStateObj.stateMachine.changeState('ai')

        ### Handle interact_script
        interact_script = Dialogue.Dialogue_Scene('Data/Level' + str(gameStateObj.counters['level']) + '/interactScript.txt', self.attacker, self.defender if self.defender else None, event_flag=False)
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
                        if unit in self.splash or unit is self.defender:
                            self.attacker.add_item(item)
                            gameStateObj.banners.append(Banner.acquiredItemBanner(self.attacker, item))
                            gameStateObj.stateMachine.changeState('itemgain')
                        elif self.defender:
                            self.defender.add_item(item)
                            gameStateObj.banners.append(Banner.acquiredItemBanner(self.defender, item))
                            gameStateObj.stateMachine.changeState('itemgain')

        ### Handle item loss
        if a_broke_item and self.attacker.team == 'player' and not self.attacker.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.attacker, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        if d_broke_item and self.defender.team == 'player' and not self.defender.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.defender, self.defender.getMainWeapon()))
            gameStateObj.stateMachine.changeState('itemgain')

        ### Handle exp and stat gain
        if not self.event_combat and (self.item.weapon or self.item.spell):
            attacker_results = [result for result in self.old_results if result.attacker is self.attacker]
            if not self.attacker.isDying and attacker_results and not self.skill_used:
                self.attacker.charge()

            if self.attacker.team == 'player' and not self.attacker.isDying and not 'Mindless' in self.attacker.tags and not self.attacker.isSummon():
                if attacker_results: #and result.outcome for result in self.old_results):
                    self.attacker.increase_wexp(self.item, gameStateObj)
                    
                my_exp = 0
                for other_unit in self.splash + [self.defender]:
                    applicable_results = [result for result in attacker_results if result.outcome and \
                                          result.defender is other_unit]
                    # Doesn't count if it did 0 damage
                    applicable_results = [result for result in applicable_results if not (self.item.weapon and result.def_damage <= 0)]
                    if isinstance(other_unit, UnitObject.UnitObject) and applicable_results:
                        damage_done = sum([result.def_damage_done for result in applicable_results])
                        if not self.item.heal:
                            self.attacker.records['damage'] += damage_done
                        if self.item.exp:
                            normal_exp = self.item.exp
                        elif self.item.weapon or not self.attacker.checkIfAlly(other_unit):
                            level_diff = other_unit.level - self.attacker.level + CONSTANTS['exp_offset']
                            normal_exp = int(CONSTANTS['exp_magnitude']*math.exp(level_diff*CONSTANTS['exp_curve']))
                        elif self.item.spell:
                            if self.item.heal:
                                # Amount healed - exp drops off linearly based on level. But minimum is 5 exp
                                self.attacker.records['healing'] += damage_done
                                normal_exp = max(5, int(CONSTANTS['heal_curve']*(damage_done-self.attacker.level)+CONSTANTS['heal_magnitude']))
                            else: # Status (Fly, Mage Shield, etc.)
                                normal_exp = CONSTANTS['status_exp']
                        else:
                            normal_exp = 0
                        if other_unit.isDying:
                            self.attacker.records['kills'] += 1
                            my_exp += int(CONSTANTS['kill_multiplier']*normal_exp) + (40 if 'Boss' in other_unit.tags else 0)
                        else:
                            my_exp += normal_exp
                        if any(status.no_exp for status in other_unit.status_effects):
                            my_exp = 0
                        logger.debug('Attacker gained %s exp', my_exp)

                # No free exp for affecting myself or being affected by allies
                if not isinstance(self.defender, UnitObject.UnitObject) or self.attacker.checkIfAlly(self.defender):
                    my_exp = int(Utility.clamp(my_exp, 0, 100))
                else:
                    my_exp = int(Utility.clamp(my_exp, 1, 100))

                gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.attacker, exp=my_exp)) #Also handles actually adding the exp to the unit
                gameStateObj.stateMachine.changeState('expgain')

            if self.defender and isinstance(self.defender, UnitObject.UnitObject) and not self.defender.isDying and not self.defender is self.attacker:
                defender_results = [result for result in self.old_results if result.attacker is self.defender]
                if defender_results:
                    self.defender.charge()
                if self.defender.team == 'player' and not 'Mindless' in self.defender.tags and not self.defender.isSummon():
                    if defender_results: # and result.outcome for result in self.old_results):
                        self.defender.increase_wexp(self.defender.getMainWeapon(), gameStateObj)
                        
                    my_exp = 0
                    applicable_results = [result for result in self.old_results if result.outcome and result.attacker is self.defender \
                                          and result.defender is self.attacker and not result.def_damage <= 0]
                    if applicable_results:
                        damage_done = sum([result.def_damage_done for result in applicable_results])
                        self.defender.records['damage'] += damage_done
                        level_diff = self.attacker.level - self.defender.level + CONSTANTS['exp_offset']
                        normal_exp = max(0, int(CONSTANTS['exp_magnitude']*math.exp(level_diff*CONSTANTS['exp_curve'])))
                        if self.attacker.isDying:
                            self.defender.records['kills'] += 1
                            my_exp += int(CONSTANTS['kill_multiplier']*normal_exp) + (40 if 'Boss' in self.attacker.tags else 0)
                        else:
                            my_exp += normal_exp 
                        if any(status.no_exp for status in self.attacker.status_effects):
                            my_exp = 0

                    # No free exp for affecting myself or being affected by allies
                    if self.attacker.checkIfAlly(self.defender):
                        my_exp = Utility.clamp(my_exp, 0, 100)
                    else:
                        my_exp = Utility.clamp(my_exp, 1, 100)

                    gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.defender, exp=my_exp)) #Also handles actually adding the exp to the unit
                    gameStateObj.stateMachine.changeState('expgain')

        # Handle after battle statuses
        for status in self.attacker.status_effects:
            if status.status_after_battle and not (self.attacker.isDying and status.tether):
                for unit in [self.defender] + self.splash:
                    if isinstance(unit, UnitObject.UnitObject) and self.attacker.checkIfEnemy(unit) and not unit.isDying:
                        applied_status = StatusObject.statusparser(status.status_after_battle)
                        if status.tether:
                            status.children.append(unit.id)
                            applied_status.parent_id = self.attacker.id
                        StatusObject.HandleStatusAddition(applied_status, unit, gameStateObj)
            if status.status_after_help and not self.attacker.isDying:
                for unit in [self.defender] + self.splash:
                    if isinstance(unit, UnitObject.UnitObject) and self.attacker.checkIfAlly(unit) and not unit.isDying:
                        applied_status = StatusObject.statusparser(status.status_after_help)
                        StatusObject.HandleStatusAddition(applied_status, unit, gameStateObj)
            if status.lost_on_attack and (self.item.weapon or self.item.detrimental):
                StatusObject.HandleStatusRemoval(status, self.attacker, gameStateObj)
        if self.defender and isinstance(self.defender, UnitObject.UnitObject) and self.defender.checkIfEnemy(self.attacker) and not self.attacker.isDying:
            for status in self.defender.status_effects:
                if status.status_after_battle and not (status.tether and self.defender.isDying):
                    applied_status = StatusObject.statusparser(status.status_after_battle)
                    if status.tether:
                        status.children.append(self.attacker.id)
                        applied_status.parent_id = self.defender.id
                    StatusObject.HandleStatusAddition(applied_status, self.attacker, gameStateObj)

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
            self.attacker.remove_item(self.item)
        if d_broke_item:
            self.defender.remove_item(self.defender.getMainWeapon())

class HealthBar(object):
    def __init__(self, topleft, unit, item, other=None, stats=None, time_for_change=300):
        self.last_update = 0
        self.time_for_change = time_for_change
        self.transition_flag = False
        self.blind_speed = 0.125 # 8 frames to fully transition
        self.true_position = None

        self.reset()
        self.fade_in()
        self.change_unit(unit, item, other, stats, topleft)

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
            surf.blit(blit_surf, (self.true_position[0], y_pos))

            # blit Gem
            if self.blinds == 1 and self.gem and self.order:
                if self.order == 'left':
                    position = (self.true_position[0] + 2, self.true_position[1] - 3)
                elif self.order == 'right':
                    position = (self.true_position[0] + 56, self.true_position[1] - 3)
                elif self.order == 'middle':
                    position = (self.true_position[0] + 27, self.true_position[1] - 3)
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
        if self.topleft in ['atkauto', 'defauto'] and self.other:
            # Get the two positions, along with camera position
            pos1 = self.unit.position
            pos2 = self.other.position
            c_pos = gameStateObj.cameraOffset.get_xy()
            if self.topleft == 'atkauto':
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
        else: # self.topleft == 'auto':
            # Find x Position
            pos_x = self.unit.position[0] - gameStateObj.cameraOffset.get_x()
            pos_x = Utility.clamp(pos_x, 3, TILEX - 2)
            # Find y position
            if self.unit.position[1] - gameStateObj.cameraOffset.get_y() < TILEY/2: # IF unit is at top of screen
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() + 1
            else:
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() - 2
            self.true_position = pos_x*TILEWIDTH - width/2, pos_y*TILEHEIGHT - 8
            self.order = 'middle'
            #logger.debug('Other True Position %s %s', pos_x, pos_y)

    def fade_in(self):
        self.blinds = 0

    def fade_out(self):
        pass

    def update(self):
        # Make blinds wider
        self.blinds = Utility.clamp(self.blinds, self.blinds + self.blind_speed, 1)
        # Handle HP bar
        if self.unit:
            if self.true_hp != self.unit.currenthp and not self.transition_flag:
                self.transition_flag = True
                self.time_for_change = max(100, abs(self.true_hp - self.unit.currenthp)*32)
                self.last_update = Engine.get_time()
            if self.transition_flag:
                self.true_hp = Utility.easing(Engine.get_time() - self.last_update, self.oldhp, self.unit.currenthp - self.oldhp, self.time_for_change)
                if self.unit.currenthp - self.oldhp > 0 and self.true_hp > self.unit.currenthp:
                    self.true_hp = self.unit.currenthp
                    self.oldhp = self.true_hp
                    self.transition_flag = False
                elif self.unit.currenthp - self.oldhp < 0 and self.true_hp < self.unit.currenthp:
                    self.true_hp = self.unit.currenthp
                    self.oldhp = self.true_hp
                    self.transition_flag = False

    def change_unit(self, unit, item, other=None, stats=None, topleft=None):
        self.stats_surf = None
        if topleft:
            self.topleft = topleft
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
        else:
            self.reset()

    def reset(self):
        self.unit = None
        self.item = None
        self.other = None
        self.true_hp = 0
        self.bg_surf = None
        self.stats = None