import random, math, os

try:
    import GlobalConstants as GC
    import configuration as cf
    import static_random
    import CustomObjects, UnitObject, Banner, TileObject, BattleAnimation
    import StatusObject, LevelUp, SaveLoad, Utility, Dialogue, Engine, Image_Modification
    import MenuFunctions, GUIObjects, Weapons
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import static_random
    from . import CustomObjects, UnitObject, Banner, TileObject, BattleAnimation
    from . import StatusObject, LevelUp, SaveLoad, Utility, Dialogue, Engine, Image_Modification
    from . import MenuFunctions, GUIObjects, Weapons

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
                return 0
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
            return 0
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
        if weapon and self.item_uses(weapon) and Utility.calculate_distance(self.attacker.position, self.defender.position) in weapon.RNG:
            return True
        else:
            return False

    def defender_has_vantage(self):
        return isinstance(self.defender, UnitObject.UnitObject) and self.defender.outspeed(self.attacker, self.defender.getMainWeapon()) and \
            'vantage' in self.defender.status_bundle and not self.item.cannot_be_countered and \
            self.defender_can_counterattack() and self.item.weapon

    def def_double(self):
        return (cf.CONSTANTS['def_double'] or 'vantage' in self.defender.status_bundle or 'def_double' in self.defender.status_bundle) and \
            self.def_rounds < 2 and self.defender.outspeed(self.attacker, self.defender.getMainWeapon())

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
                elif (self.def_rounds < 1 or self.def_double()) and \
                        self.item.weapon and not self.item.cannot_be_countered and isinstance(self.defender, UnitObject.UnitObject) and \
                        self.defender_can_counterattack():
                    self.state = 'Defender'
                elif self.atk_rounds < 2 and self.item.weapon and self.attacker.outspeed(self.defender, self.item) and self.item_uses(self.item):
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
            elif (self.def_rounds < 1 or self.def_double()) and \
                    self.item.weapon and self.defender and isinstance(self.defender, UnitObject.UnitObject) and \
                    self.defender.currenthp > 0 and self.defender_can_counterattack() and not self.item.cannot_be_countered:
                self.index = 0
                self.state = 'Defender'
            elif self.defender and self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item) and \
                    self.item_uses(self.item) and self.defender.currenthp > 0:
                self.index = 0
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
            elif self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item) and self.item_uses(self.item) and self.defender.currenthp > 0:
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
            elif self.defender and self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item) and \
                    self.item_uses(self.item) and self.defender.currenthp > 0:
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
                elif self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item) and self.item_uses(self.item) and not self.item.no_double:
                    self.state = 'Attacker'
                elif self.def_double() and self.defender_can_counterattack() and not self.defender.getMainWeapon().no_double:
                    self.state = 'Defender'

        elif self.state == 'DefenderBrave':
            self.state = 'Done'
            if self.attacker.currenthp > 0:
                if self.def_rounds < 2 and self.defender_has_vantage():
                    self.state = 'Attacker'
                if self.atk_rounds < 2 and self.attacker.outspeed(self.defender, self.item) and self.item_uses(self.item) and not self.item.no_double:
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
        def_position, splash_positions = item.aoe.get_positions(atk_position, position, gameStateObj.map, item)
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
    if item.weapon:
        splash_units = [unit for unit in splash_units if attacker.checkIfEnemy(unit)]
    # Beneficial stuff only affects allies
    if item.beneficial and item.spell:
        splash_units = [unit for unit in splash_units if attacker.checkIfAlly(unit)]
        if item.heal:  # Only heal allies who need it
            splash_units = [unit for unit in splash_units if unit.currenthp < unit.stats['HP']]
    if item.weapon or (item.spell and not item.beneficial):
        splash_units += [gameStateObj.map.tiles[pos] for pos in splash_positions if 'HP' in gameStateObj.map.tile_info_dict[pos]]
    logger.debug('Main Defender: %s, Splash: %s', main_defender, splash_units)
    return main_defender, splash_units

def start_combat(gameStateObj, attacker, defender, def_pos, splash, item, skill_used=None, event_combat=None, ai_combat=False, toggle_anim=False):
    def animation_wanted(attacker, defender):
        return (cf.OPTIONS['Animation'] == 'Always' or
                (cf.OPTIONS['Animation'] == 'Your Turn' and attacker.team == 'player') or
                (cf.OPTIONS['Animation'] == 'Combat Only' and attacker.checkIfEnemy(defender)))

    toggle_anim = gameStateObj.input_manager.is_pressed('AUX')
    # Whether animation combat is even allowed
    if (not splash and attacker is not defender and isinstance(defender, UnitObject.UnitObject) and not item.movement and not item.self_movement):
        # XOR below
        if animation_wanted(attacker, defender) != toggle_anim:
            distance = Utility.calculate_distance(attacker.position, def_pos)
            magic = Weapons.TRIANGLE.isMagic(item)
            if magic and item.magic_at_range and distance <= 1:
                magic = False
            attacker_anim = GC.ANIMDICT.partake(attacker.klass, attacker.gender, item, magic, distance)
            defender_item = defender.getMainWeapon()
            if defender_item:
                magic = Weapons.TRIANGLE.isMagic(defender_item)
                # Not magic animation at close combat for a magic at range item
                if magic and defender_item.magic_at_range and distance <= 1:
                    magic = False
            else:
                magic = False
            defender_anim = GC.ANIMDICT.partake(defender.klass, defender.gender, defender.getMainWeapon(), magic, distance)
            if attacker_anim and defender_anim:
                # Build attacker animation
                attacker_script = attacker_anim['script']
                attacker_color = Utility.get_color(attacker.team)
                name = None
                if attacker.name in attacker_anim['images']:
                    name = attacker.name
                    attacker_frame_dir = attacker_anim['images'][name]
                elif 'Generic' + attacker_color in attacker_anim['images']:
                    name = 'Generic' + attacker_color
                    attacker_frame_dir = attacker_anim['images'][name]
                else:  # Just a map combat
                    return MapCombat(attacker, defender, def_pos, splash, item, skill_used, event_combat)
                attacker.battle_anim = BattleAnimation.BattleAnimation(attacker, attacker_frame_dir, attacker_script, name, item)
                # Build defender animation
                defender_script = defender_anim['script']
                defender_color = Utility.get_color(defender.team)
                if defender.name in defender_anim['images']:
                    name = defender.name
                    defender_frame_dir = defender_anim['images'][name]
                elif 'Generic' + defender_color in defender_anim['images']:
                    name = 'Generic' + defender_color
                    defender_frame_dir = defender_anim['images'][name]
                else:
                    return MapCombat(attacker, defender, def_pos, splash, item, skill_used, event_combat)
                defender.battle_anim = BattleAnimation.BattleAnimation(defender, defender_frame_dir, defender_script, name, defender.getMainWeapon())
                return AnimationCombat(attacker, defender, def_pos, item, skill_used, event_combat, ai_combat)
    # default
    return MapCombat(attacker, defender, def_pos, splash, item, skill_used, event_combat)

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

    def _apply_result(self, result, gameStateObj):
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
        result.attacker.change_hp(-result.atk_damage)
        # result.attacker.currenthp -= result.atk_damage
        # result.attacker.currenthp = Utility.clamp(result.attacker.currenthp, 0, result.attacker.stats['HP'])
        if result.defender:
            result.defender.change_hp(-result.def_damage)
            # result.defender.currenthp -= result.def_damage
            # print(result.defender.currenthp, result.def_damage)
            # result.defender.currenthp = Utility.clamp(result.defender.currenthp, 0, result.defender.stats['HP'])

    def find_broken_items(self):
        # Handle items that were used
        a_broke_item, d_broke_item = False, False
        if self.item.uses and self.item.uses.uses <= 0:
            a_broke_item = True
        if self.p2 and self.p2.getMainWeapon() and self.p2.getMainWeapon().uses and self.p2.getMainWeapon().uses.uses <= 0:
            d_broke_item = True
        return a_broke_item, d_broke_item

    def remove_broken_items(self, a_broke_item, d_broke_item):
        if a_broke_item:
            self.p1.remove_item(self.item)
        if d_broke_item:
            self.p2.remove_item(self.p2.getMainWeapon())

    def summon_broken_item_banner(self, a_broke_item, d_broke_item, gameStateObj):
        if a_broke_item and self.p1.team == 'player' and not self.p1.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.p1, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        if d_broke_item and self.p2.team == 'player' and not self.p2.isDying:
            gameStateObj.banners.append(Banner.brokenItemBanner(self.p2, self.p2.getMainWeapon()))
            gameStateObj.stateMachine.changeState('itemgain')
    
    def calc_init_exp_p1(self, my_exp, other_unit, applicable_results, gameStateObj):
        p1_klass = gameStateObj.metaDataObj['class_dict'][self.p1.klass]
        other_unit_klass = gameStateObj.metaDataObj['class_dict'][other_unit.klass]
        exp_multiplier = p1_klass['exp_multiplier']*other_unit_klass['exp_when_attacked']

        damage_done = sum([result.def_damage_done for result in applicable_results])
        if not self.item.heal:
            self.p1.records['damage'] += damage_done

        if self.item.exp:
            normal_exp = int(self.item.exp)
        elif self.item.weapon or not self.p1.checkIfAlly(other_unit):
            level_diff = other_unit.get_comparison_level(gameStateObj.metaDataObj) - self.p1.get_comparison_level(gameStateObj.metaDataObj) + cf.CONSTANTS['exp_offset']
            normal_exp = int(exp_multiplier*cf.CONSTANTS['exp_magnitude']*math.exp(level_diff*cf.CONSTANTS['exp_curve']))
        elif self.item.spell:
            if self.item.heal:
                # Amount healed - exp drops off linearly based on level. But minimum is 5 exp
                self.p1.records['healing'] += damage_done
                normal_exp = max(5, int(p1_klass['exp_multiplier']*cf.CONSTANTS['heal_curve']*(damage_done-self.p1.get_comparison_level(gameStateObj.metaDataObj)) + cf.CONSTANTS['heal_magnitude']))
            else: # Status (Fly, Mage Shield, etc.)
                normal_exp = int(p1_klass['exp_multiplier']*cf.CONSTANTS['status_exp'])
        else:
            normal_exp = 0
            
        if other_unit.isDying:
            self.p1.records['kills'] += 1
            my_exp += int(cf.CONSTANTS['kill_multiplier']*normal_exp) + (cf.CONSTANTS['boss_bonus'] if 'Boss' in other_unit.tags else 0)
        else:
            my_exp += normal_exp
        if 'no_exp' in other_unit.status_bundle:
            my_exp = 0
        logger.debug('Attacker gained %s exp', my_exp)
        return my_exp

    def calc_init_exp_p2(self, defender_results, gameStateObj):
        p2_klass = gameStateObj.metaDataObj['class_dict'][self.p2.klass]
        other_unit_klass = gameStateObj.metaDataObj['class_dict'][self.p1.klass]
        exp_multiplier = p2_klass['exp_multiplier']*other_unit_klass['exp_when_attacked']

        my_exp = 0
        applicable_results = [result for result in self.old_results if result.outcome and result.attacker is self.p2 and
                              result.defender is self.p1 and not result.def_damage <= 0]
        if applicable_results:
            damage_done = sum([result.def_damage_done for result in applicable_results])
            self.p2.records['damage'] += damage_done
            level_diff = self.p1.get_comparison_level(gameStateObj.metaDataObj) - self.p2.get_comparison_level(gameStateObj.metaDataObj) + cf.CONSTANTS['exp_offset']
            normal_exp = max(0, int(exp_multiplier*cf.CONSTANTS['exp_magnitude']*math.exp(level_diff*cf.CONSTANTS['exp_curve'])))
            if self.p1.isDying:
                self.p2.records['kills'] += 1
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
        return my_exp

    def handle_interact_script(self, gameStateObj):
        script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/interactScript.txt'
        if os.path.exists(script_name):
            interact_script = Dialogue.Dialogue_Scene(script_name, unit=self.p1, unit2=(self.p2 if self.p2 else None))
            gameStateObj.message.append(interact_script)
            gameStateObj.stateMachine.changeState('dialogue')

    def handle_miracle(self, gameStateObj, all_units):
        for unit in all_units:
            if unit.isDying and isinstance(unit, UnitObject.UnitObject):
                if any(status.miracle and (not status.count or status.count.count > 0) for status in unit.status_effects):
                    unit.handle_miracle(gameStateObj)

    def handle_item_gain(self, gameStateObj, all_units):
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
                    if isinstance(unit, UnitObject.UnitObject) and self.p1.checkIfEnemy(self.p2) and not unit.isDying:
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
            elif status.lost_on_interact and (self.item.weapon or self.item.spell):
                StatusObject.HandleStatusRemoval(status, self.p1, gameStateObj)
        if self.p2 and isinstance(self.p2, UnitObject.UnitObject) and self.p2.checkIfEnemy(self.p1) and not self.p1.isDying:
            for status in self.p2.status_effects:
                if status.status_after_battle and not (status.tether and self.p2.isDying):
                    applied_status = StatusObject.statusparser(status.status_after_battle)
                    if status.tether:
                        status.children.append(self.p1.id)
                        applied_status.parent_id = self.p2.id
                    StatusObject.HandleStatusAddition(applied_status, self.p1, gameStateObj)

    def handle_skill_used(self):
        if self.skill_used and self.skill_used.active:
            self.skill_used.active.current_charge = 0
            # If no other active skills, can remove active skill charged
            if not any(skill.active and skill.active.required_charge > 0 and 
                       skill.active.current_charge >= skill.active.required_charge for skill in self.p1.status_effects):
                self.p1.tags.discard('ActiveSkillCharged')
            if self.skill_used.active.mode == 'Attack':
                self.skill_used.active.reverse_mod()

    def handle_death(self, gameStateObj, metaDataObj, all_units):
        for unit in all_units:
            if unit.isDying:
                logger.debug('%s is dying.', unit.name)
                if isinstance(unit, TileObject.TileObject):
                    gameStateObj.map.destroy(unit, gameStateObj)
                else:
                    gameStateObj.stateMachine.changeState('dying')
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(metaDataObj['death_quotes'], unit=unit))
                    gameStateObj.stateMachine.changeState('dialogue')

class AnimationCombat(Combat):
    def __init__(self, attacker, defender, def_pos, item, skill_used, event_combat, ai_combat):
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
        distance = Utility.calculate_distance(self.p1.position, self.p2.position)
        self.at_range = distance - 1 if distance > 1 else 0 
        self.item = item
        self.skill_used = skill_used
        self.event_combat = event_combat
        self.ai_combat = ai_combat

        self.solver = Solver(attacker, defender, def_pos, [], item, skill_used, event_combat)
        self.old_results = []

        self.left_stats, self.right_stats = None, None
        self.left_hp_bar, self.right_hp_bar = SimpleHPBar(self.left), SimpleHPBar(self.right)

        self.combat_state = 'Start' # Start, Fade, Entrance, (Pre_Init, Anim, HP_Change, Anim), (Init, Anim, Hp_Change, Anim)

        # Since AnimationCombat always has exactly 2 participants
        self.p1.lock_active()
        self.p2.lock_active()

        # For fade to black viewbox
        self.viewbox_clamp_state = 0
        self.total_viewbox_clamp_states = 15
        self.viewbox = None

        # For darken backgrounds and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.darken_ui_background = 0
        self.foreground = MenuFunctions.Foreground()
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
        left_platform_type = gameStateObj.map.tiles[self.left.position].platform
        right_platform_type = gameStateObj.map.tiles[self.right.position].platform
        if self.at_range:
            suffix = '-Ranged'
        else:
            suffix = '-Melee'
        self.left_platform = GC.IMAGESDICT[left_platform_type + suffix].copy()
        self.right_platform = Engine.flip_horiz(GC.IMAGESDICT[right_platform_type + suffix].copy())

    def update(self, gameStateObj, metaDataObj, skip=False):
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
            if not skip:
                gameStateObj.stateMachine.changeState('move_camera')

            self.init_draw(gameStateObj, metaDataObj)
            if self.ai_combat:
                self.combat_state = 'RedOverlay_Init'
            else:
                self.combat_state = 'Fade'

        elif self.combat_state == 'RedOverlay_Init':
            gameStateObj.cursor.drawState = 2
            self.last_update = current_time
            self.combat_state = 'RedOverlay'

        elif self.combat_state == 'RedOverlay':
            if skip or current_time - self.last_update > 400:
                gameStateObj.cursor.drawState = 0
                gameStateObj.highlight_manager.remove_highlights()
                self.combat_state = 'Fade'

        elif self.combat_state == 'Fade':
            # begin viewbox clamping
            if skip:
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
            if skip or self.bar_offset >= self.max_position_offset:
                self.bar_offset = self.max_position_offset
                self.name_offset = self.max_position_offset
                self.last_update = current_time
                self.combat_state = 'Pre_Init'

        elif self.combat_state == 'Pre_Init':
            if skip or current_time - self.last_update > 410: # 25 frames
                self.combat_state = 'Anim'
                self.last_update = current_time
                # Set up animation
                self.current_animation = self.set_up_animation(self.current_result)

        elif self.combat_state == 'Init':
            # self.current_result = self.solver.get_a_result(gameStateObj, metaDataObj)
            self.current_result = self.next_result
            self.next_result = None
            # print('Interaction: Getting a new result')
            if self.current_result is None:
                self.last_update = current_time
                self.combat_state = 'ExpWait'
                self.focus_exp()
                self.move_camera()
            else:
                self.set_stats(gameStateObj)
                self.old_results.append(self.current_result)
                self.combat_state = 'Anim'
                self.last_update = current_time
                self.current_animation = self.set_up_animation(self.current_result)

        elif self.combat_state == 'Anim':
            if self.left.battle_anim.done() and self.right.battle_anim.done():
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

        elif self.combat_state == 'ExpWait':
            if skip or current_time - self.last_update > 450:
                self.handle_exp(gameStateObj)
                self.combat_state = 'Exp'

        elif self.combat_state == 'Exp':
            if not gameStateObj.levelUpScreen:
                self.last_update = current_time
                self.combat_state = 'OutWait'

        elif self.combat_state == 'OutWait':
            if skip or current_time - self.last_update > 820:
                self.p1.battle_anim.finish()
                self.p2.battle_anim.finish()
                self.combat_state = 'Out1'

        elif self.combat_state == 'Out1': # Nametags move out
            self.name_offset -= 1
            if skip or self.name_offset <= 0:
                self.name_offset = 0
                self.combat_state = 'Out2'

        elif self.combat_state == 'Out2': # Rest of the goods move out
            self.bar_offset -= 1
            if skip or self.bar_offset <= 0:
                self.bar_offset = 0
                self.combat_state = 'FadeOut'

        elif self.combat_state == 'FadeOut':
            # end viewbox clamping
            if skip:
                self.viewbox_clamp_state = 0
                self.build_viewbox(gameStateObj)
            self.viewbox_clamp_state -= 1
            if self.viewbox_clamp_state > 0:
                self.build_viewbox(gameStateObj)
            else:
                self.finish()
                self.clean_up(gameStateObj, metaDataObj)
                self.end_skip()
                return True

        self.left_hp_bar.update(skip or self.combat_state == 'Exp')
        self.right_hp_bar.update(skip or self.combat_state == 'Exp')
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

    def skip(self):
        BattleAnimation.speed = 0.25

    def end_skip(self):
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
        damage = result.def_damage
        str_damage = str(abs(damage))
        left = self.left == result.defender
        for idx, num in enumerate(str_damage):
            if result.outcome == 2:  # Crit
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'Yellow')
                self.damage_numbers.append(d)
            elif result.def_damage < 0:
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'Cyan')
                self.damage_numbers.append(d)
            elif result.def_damage > 0:
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'Red')
                self.damage_numbers.append(d)

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

    def set_stats(self, gameStateObj):
        result = self.current_result
        # Calc stats
        a_mode = 'Attack' if result.attacker is self.p1 else 'Defense'
        a_weapon = self.item if result.attacker is self.p1 else result.attacker.getMainWeapon()
        a_hit = result.attacker.compute_hit(result.defender, gameStateObj, a_weapon, a_mode)
        a_mt = result.attacker.compute_damage(result.defender, gameStateObj, a_weapon, a_mode)
        if cf.CONSTANTS['crit']:
            a_crit = result.attacker.compute_crit(result.defender, gameStateObj, a_weapon, a_mode)
        else:
            a_crit = 0
        a_stats = a_hit, a_mt, a_crit

        if self.item.weapon and self.solver.defender_can_counterattack():
            d_mode = 'Defense' if result.attacker is self.p1 else 'Attack'
            d_weapon = result.defender.getMainWeapon()
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

        # Get next result in preparation for next combat
        self.next_result = self.solver.get_a_result(gameStateObj, metaDataObj)

    def set_up_animation(self, result):
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

    def finish(self):
        self.p1.unlock_active()
        self.p2.unlock_active()

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

        # Damage number animations
        for damage_num in self.damage_numbers:
            damage_num.update()
            if damage_num.left:
                left_pos = 94 + left_range_offset - total_shake_x + self.pan_offset
                damage_num.draw(surf, (left_pos, 40))
            else:
                right_pos = 146 + right_range_offset - total_shake_x + self.pan_offset
                damage_num.draw(surf, (right_pos, 40))
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
        white = True if (item.effective and any(comp in other.tags for comp in item.effective.against)) or \
            any(status.weakness and status.weakness.damage_type == self.item.TYPE for status in other.status_effects) else False
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
        if not self.event_combat and (self.item.weapon or self.item.spell):
            attacker_results = [result for result in self.old_results if result.attacker is self.p1]
            if not self.p1.isDying and attacker_results and not self.skill_used:
                self.p1.charge()

            if self.p1.team == 'player' and not self.p1.isDying and 'Mindless' not in self.p1.tags \
               and not self.p1.isSummon():
                if attacker_results: # and result.outcome for result in self.old_results):
                    self.p1.increase_wexp(self.item, gameStateObj)
                    
                my_exp = 0
                applicable_results = [result for result in attacker_results if result.outcome and
                                      result.defender is self.p2]
                # Doesn't count if it did 0 damage
                applicable_results = [result for result in applicable_results if not (self.item.weapon and result.def_damage <= 0)]
                if applicable_results:
                    my_exp = self.calc_init_exp_p1(my_exp, self.p2, applicable_results, gameStateObj)

                # No free exp for affecting myself or being affected by allies
                if self.p1.checkIfAlly(self.p2):
                    my_exp = int(Utility.clamp(my_exp, 0, 100))
                else:
                    my_exp = int(Utility.clamp(my_exp, cf.CONSTANTS['min_exp'], 100))

                if my_exp > 0:
                    # Also handles actually adding the exp to the unit
                    gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.p1, exp=my_exp, in_combat=self))
                    gameStateObj.stateMachine.changeState('expgain')

            if self.p2 and not self.p2.isDying:
                defender_results = [result for result in self.old_results if result.attacker is self.p2]
                if defender_results:
                    self.p2.charge()
                if self.p2.team == 'player' and 'Mindless' not in self.p2.tags and not self.p2.isSummon():
                    if defender_results: # and result.outcome for result in self.old_results):
                        self.p2.increase_wexp(self.p2.getMainWeapon(), gameStateObj)
                        
                    my_exp = self.calc_init_exp_p2(defender_results, gameStateObj)
                    if my_exp > 0:
                        # Also handles actually adding the exp to the unit
                        gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.p2, exp=my_exp, in_combat=self))
                        gameStateObj.stateMachine.changeState('expgain')

    def check_death(self):
        if self.p1.currenthp <= 0:
            self.p1.isDying = True
        if self.p2.currenthp <= 0:
            self.p2.isDying = True

    # Clean up everything
    def clean_up(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.back()
        self.p1.hasAttacked = True
        if not self.p1.has_canto_plus() and not self.event_combat:
            gameStateObj.stateMachine.changeState('wait') # Event combats do not cause unit to wait

        a_broke_item, d_broke_item = self.find_broken_items()

        # Handle skills that were used
        self.handle_skill_used()

        # Create all_units list
        all_units = [self.p1, self.p2]

        # Handle death and sprite changing
        self.check_death()
        if not self.p2.isDying:
            self.p2.sprite.change_state('normal', gameStateObj)

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

        self.handle_death(gameStateObj, metaDataObj, all_units)

        # Actually remove items
        self.remove_broken_items(a_broke_item, d_broke_item)

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
        t_hp = int(self.true_hp)
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
        if self.max_hp > 80:
            # First 40 hp
            for index in range(40):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] + 4))
            surf.blit(self.end_hp_blip, (pos[0] + 40 * 2 + 5, pos[1] + 4)) # End HP Blip
            # Second 40 hp
            for index in range(40):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] - 4))
            surf.blit(self.end_hp_blip, (pos[0] + 40 * 2 + 5, pos[1] - 4)) # End HP Blip
        elif self.max_hp <= 40:
            for index in range(t_hp):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] + 1))
            for index in range(self.max_hp - t_hp):
                surf.blit(self.empty_hp_blip, (pos[0] + (index + t_hp) * 2 + 5, pos[1] + 1))
            surf.blit(self.end_hp_blip, (pos[0] + (self.max_hp) * 2 + 5, pos[1] + 1)) # End HP Blip
        else:
            # First 40 hp
            for index in range(min(t_hp, 40)):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] + 4))
            if t_hp < 40:
                for index in range(40 - t_hp):
                    surf.blit(self.empty_hp_blip, (pos[0] + (index + t_hp) * 2 + 5, pos[1] + 4))
            surf.blit(self.end_hp_blip, (pos[0] + (40) * 2 + 5, pos[1] + 4)) # End HP Blip
            # Second 40 hp
            for index in range(max(0, t_hp - 40)):
                surf.blit(full_hp_blip, (pos[0] + index * 2 + 5, pos[1] - 4))
            for index in range(self.max_hp - max(40, t_hp)):
                surf.blit(self.empty_hp_blip, (pos[0] + (index + max(t_hp - 40, 0)) * 2 + 5, pos[1] - 4))
            surf.blit(self.end_hp_blip, (pos[0] + (self.max_hp - 40) * 2 + 5, pos[1] - 4)) # End HP Blip

class MapCombat(Combat):
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

        self.damage_numbers = []

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
            if cf.CONSTANTS['simultaneous_aoe']:
                if self.solver.state == 'Attacker' and self.solver.index < len(self.solver.splash):
                    self.results.append(self.solver.get_a_result(gameStateObj, metaDataObj))
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
                if skip or current_time > self.length_of_combat // 5 + self.additional_time:
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
                if skip or current_time > 2 * self.length_of_combat // 5 + self.additional_time:
                    self.combat_state = 'Anim'
                    if self.results[0].attacker.sprite.state in {'combat_attacker', 'combat_defender'}:
                        self.results[0].attacker.sprite.change_state('combat_anim', gameStateObj)
                    for result in self.results:
                        if result.attacker is self.p1:
                            item = self.item
                        else:
                            item = result.attacker.getMainWeapon()
                        if item.sfx_on_cast and item.sfx_on_cast in GC.SOUNDDICT:
                            GC.SOUNDDICT[item.sfx_on_cast].play()

            elif self.combat_state == 'Anim':
                if skip or current_time > 3 * self.length_of_combat // 5 + self.additional_time:
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
                if skip or current_time > (3 * self.length_of_combat // 5) + self.additional_time:
                    self.combat_state = 'Wait'

            elif self.combat_state == 'Wait': 
                if skip or current_time > (4 * self.length_of_combat // 5) + self.additional_time:
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
                GC.SOUNDDICT['heal'].play()
            elif result.def_damage == 0 and (item.weapon or (item.spell and item.damage)): # No Damage if weapon or spell with damage!
                GC.SOUNDDICT['No Damage'].play()
            else:
                if result.outcome == 2: # critical
                    sound_to_play = 'Critical Hit ' + str(random.randint(1, 2))
                else:
                    sound_to_play = 'Attack Hit ' + str(random.randint(1, 5)) # Choose a random hit sound
                GC.SOUNDDICT[sound_to_play].play()
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
                anim = CustomObjects.Animation(GC.IMAGESDICT[name], pos, (int(x), int(y)), int(num), 24)
                gameStateObj.allanimations.append(anim)
            elif result.def_damage < 0: # Heal
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
        str_damage = str(abs(damage))
        left = result.defender.position
        for idx, num in enumerate(str_damage):
            if result.outcome == 2:  # Crit
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'SmallYellow')
                self.damage_numbers.append(d)
            elif result.def_damage < 0:
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'SmallCyan')
                self.damage_numbers.append(d)
            elif result.def_damage > 0:
                d = GUIObjects.DamageNumber(int(num), idx, len(str_damage), left, 'SmallRed')
                self.damage_numbers.append(d)

    def skip(self):
        self.p1.sprite.reset_sprite_offset()
        if self.p2 and isinstance(self.p2, UnitObject.UnitObject):
            self.p2.sprite.reset_sprite_offset()

    def apply_result(self, result, gameStateObj):
        self._apply_result(result, gameStateObj)
        # Movement
        if result.atk_movement and result.defender.position:
            def_position = result.defender.position
            result.attacker.handle_forced_movement(def_position, result.atk_movement, gameStateObj)
        if result.def_movement:
            atk_position = result.attacker.position
            result.defender.handle_forced_movement(atk_position, result.def_movement, gameStateObj, self.def_pos)
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

            if self.p2 in (result.attacker, result.defender) and self.item.weapon and self.solver.defender_can_counterattack():
                d_mode = 'Defense' if result.attacker is self.p1 else 'Attack'
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
                    defender_hp = HealthBar('p1' if result.defender is self.p1 else 'p2', result.defender, d_weapon, other=result.attacker, stats=d_stats)
                    self.health_bars[result.defender] = defender_hp
                if result.attacker in self.health_bars:
                    self.health_bars[result.attacker].update_stats(a_stats)
                    if result.attacker is result.defender:
                        self.health_bars[result.attacker].item = a_weapon  # Update item
                else:
                    attacker_hp = HealthBar('p1' if result.attacker is self.p1 else 'p2', result.attacker, a_weapon, other=result.defender, stats=a_stats)
                    self.health_bars[result.attacker] = attacker_hp
            else:
                # if not cf.CONSTANTS['simultaneous_aoe']:
                self.health_bars = {}  # Clear
                if not cf.CONSTANTS['simultaneous_aoe'] or len(self.results) <= 1:
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
        # Reset states if you're not using a solo skill
        if self.skill_used and self.skill_used.active and self.skill_used.active.mode == 'Solo':
            self.p1.hasTraded = True  # Can still attack, can't move
            self.p1.hasAttacked = False
        else:
            self.p1.hasAttacked = True
            if not self.p1.has_canto_plus() and not self.event_combat:
                gameStateObj.stateMachine.changeState('wait')  # Event combats do not cause unit to wait

        a_broke_item, d_broke_item = self.find_broken_items()

        # Handle skills that were used
        self.handle_skill_used()

        # Create all_units list
        all_units = [unit for unit in self.splash] + [self.p1]
        if self.p2: 
            all_units += [self.p2]

        # Handle death and sprite changing
        for unit in all_units:
            if unit.currenthp <= 0:
                unit.isDying = True
            if isinstance(unit, UnitObject.UnitObject):
                unit.sprite.change_state('normal', gameStateObj)

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
            if not self.p1.isDying and attacker_results and not self.skill_used:
                self.p1.charge()

            if self.p1.team == 'player' and not self.p1.isDying and 'Mindless' not in self.p1.tags and not self.p1.isSummon():
                if attacker_results: # and result.outcome for result in self.old_results):
                    self.p1.increase_wexp(self.item, gameStateObj)
                    
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
                        my_exp = self.calc_init_exp_p1(my_exp, other_unit, applicable_results, gameStateObj)

                # No free exp for affecting myself or being affected by allies
                if not isinstance(self.p2, UnitObject.UnitObject) or self.p1.checkIfAlly(self.p2):
                    my_exp = int(Utility.clamp(my_exp, 0, 100))
                else:
                    my_exp = int(Utility.clamp(my_exp, cf.CONSTANTS['min_exp'], 100))

                # Also handles actually adding the exp to the unit
                gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.p1, exp=my_exp)) 
                gameStateObj.stateMachine.changeState('expgain')

            if self.p2 and isinstance(self.p2, UnitObject.UnitObject) and not self.p2.isDying and self.p2 is not self.p1:
                defender_results = [result for result in self.old_results if result.attacker is self.p2]
                if defender_results:
                    self.p2.charge()
                if self.p2.team == 'player' and 'Mindless' not in self.p2.tags and not self.p2.isSummon():
                    if defender_results: # and result.outcome for result in self.old_results):
                        self.p2.increase_wexp(self.p2.getMainWeapon(), gameStateObj)
                        
                    my_exp = self.calc_init_exp_p2(defender_results, gameStateObj)

                    # Also handles actually adding the exp to the unit
                    gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.p2, exp=my_exp)) 
                    gameStateObj.stateMachine.changeState('expgain')

        # Handle after battle statuses
        self.handle_statuses(gameStateObj)

        self.handle_death(gameStateObj, metaDataObj, all_units)

        # Actually remove items
        self.remove_broken_items(a_broke_item, d_broke_item)

class HealthBar(object):
    def __init__(self, draw_method, unit, item, other=None, stats=None, swap_stats=None):
        self.last_update = 0
        self.time_for_change = 200
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
            bg_surf.blit(self.bg_surf, (0, 0))
            # Blit Name
            name_size = GC.FONT['text_numbers'].size(self.unit.name)
            position = width - name_size[0] - 4, 3
            GC.FONT['text_numbers'].blit(self.unit.name, bg_surf, position)
            # Blit item -- Must be blit every frame
            if self.item:
                if self.other:
                    if isinstance(self.other, UnitObject.UnitObject):
                        white = True if (self.item.effective and any(comp in self.other.tags for comp in self.item.effective.against)) or \
                            any(status.weakness and status.weakness.damage_type == self.item.TYPE for status in self.other.status_effects) else False
                    else:  # Tile Object
                        white = True if self.item.extra_tile_damage else False
                else:
                    white = False
                self.item.draw(bg_surf, (2, 3), white)

                # Blit advantage -- This must be blit every frame
                if isinstance(self.other, UnitObject.UnitObject) and self.other.getMainWeapon() and self.unit.checkIfEnemy(self.other):
                    advantage, e_advantage = Weapons.TRIANGLE.compute_advantage(self.item, self.other.getMainWeapon())
                    if advantage > 0:
                        UpArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (self.unit.arrowAnim[self.unit.arrowCounter]*7, 0, 7, 10))
                        bg_surf.blit(UpArrow, (11, 7))
                    elif advantage < 0:
                        DownArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (self.unit.arrowAnim[self.unit.arrowCounter]*7, 10, 7, 10))
                        bg_surf.blit(DownArrow, (11, 7))

            # Blit health bars -- Must be blit every frame
            if self.unit.stats['HP']:
                fraction_hp = float(self.true_hp)/self.unit.stats['HP']
            else:
                fraction_hp = 0
            index_pixel = int(50*fraction_hp)
            position = 25, 22
            bg_surf.blit(Engine.subsurface(GC.IMAGESDICT['HealthBar'], (0, 0, index_pixel, 2)), position)

            # Blit HP -- Must be blit every frame
            font = GC.FONT['number_small2']
            if self.transition_flag:
                font = GC.FONT['number_big2']
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
                blit_surf = Engine.subsurface(bg_surf, (0, true_height//2 - int(true_height*self.blinds//2), width, int(true_height*self.blinds)))
                y_pos = self.true_position[1] + true_height//2 - int(true_height*self.blinds//2)
            else:
                blit_surf = Engine.subsurface(bg_surf, (0, height//2 - int(height*self.blinds//2), width, int(height*self.blinds)))
                y_pos = self.true_position[1] + height//2 - int(height*self.blinds//2)
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
        position = c_surf.get_width()//2 - GC.FONT['number_small2'].size(hit)[0] - 1, -2
        GC.FONT['number_small2'].blit(hit, c_surf, position)
        # Blit Damage
        if self.stats[1] is not None:
            damage = str(self.stats[1])
        else:
            damage = '--'
        position = c_surf.get_width() - GC.FONT['number_small2'].size(damage)[0] - 2, -2
        GC.FONT['number_small2'].blit(damage, c_surf, position)
        return c_surf

    def determine_position(self, gameStateObj, pos):
        width, height = pos
        # Determine position
        self.true_position = self.topleft
        # logger.debug("Topleft %s", self.topleft)
        if self.topleft in ('p1', 'p2'):
            # Get the two positions, along with camera position
            pos1 = self.unit.position
            pos2 = self.other.position
            c_pos = gameStateObj.cameraOffset.get_xy()
            if self.topleft == 'p1':
                left = True if pos1[0] <= pos2[0] else False
            else:
                left = True if pos1[0] < pos2[0] else False
            self.order = 'left' if left else 'right'
            # logger.debug("%s %s %s", pos1, pos2, left)
            x_pos = GC.WINWIDTH//2 - width if left else GC.WINWIDTH//2
            rel_1 = pos1[1] - c_pos[1]
            rel_2 = pos2[1] - c_pos[1]
            # logger.debug("Health_Bar_Pos %s %s", rel_1, rel_2)
            # If both are on top of screen
            if rel_1 < 5 and rel_2 < 5:
                rel = max(rel_1, rel_2)
                y_pos = (rel+1)*GC.TILEHEIGHT + 12
            # If both are on bottom of screen
            elif rel_1 >= 5 and rel_2 >= 5:
                rel = min(rel_1, rel_2)
                y_pos = rel*GC.TILEHEIGHT - 12 - height - 13 # c_surf
            # Find largest gap and place it in the middle
            else:
                top_gap = min(rel_1, rel_2)
                bottom_gap = (GC.TILEY-1) - max(rel_1, rel_2)
                middle_gap = abs(rel_1 - rel_2)
                # logger.debug("Gaps %s %s %s", top_gap, bottom_gap, middle_gap)
                if top_gap > bottom_gap and top_gap > middle_gap:
                    y_pos = top_gap * GC.TILEHEIGHT - 12 - height - 13 # c_surf
                elif bottom_gap > top_gap and bottom_gap > middle_gap:
                    y_pos = (bottom_gap+1) * GC.TILEHEIGHT + 12
                else:
                    y_pos = GC.WINHEIGHT//4 - height//2 - 13//2 if rel_1 < 5 else 3*GC.WINHEIGHT//4 - height//2 - 13//2
                    x_pos = GC.WINWIDTH//4 - width//2 if pos1[0] - c_pos[0] > GC.TILEX//2 else 3*GC.WINWIDTH//4 - width//2
                    self.order = 'middle'
            self.true_position = (x_pos, y_pos)
            # logger.debug('True Position %s %s', x_pos, y_pos)
        elif self.topleft == 'splash': # self.topleft == 'auto':
            # Find x Position
            pos_x = self.unit.position[0] - gameStateObj.cameraOffset.get_x()
            pos_x = Utility.clamp(pos_x, 3, GC.TILEX - 2)
            # Find y position
            if self.unit.position[1] - gameStateObj.cameraOffset.get_y() < GC.TILEY//2: # IF unit is at top of screen
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() + 2
            else:
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() - 3
            self.true_position = pos_x*GC.TILEWIDTH - width//2, pos_y*GC.TILEHEIGHT - 8
            self.order = 'middle'
            # logger.debug('Other True Position %s %s', pos_x, pos_y)

    def fade_in(self):
        self.blinds = 0

    def fade_out(self):
        pass

    def shake(self, num):
        self.current_shake = 1
        if num == 1: # Normal hit
            self.shake_set = [(-3, -3), (0, 0), (3, 3), (0, 0)]
        elif num == 2: # Kill
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
                if status_obj:
                    self.time_for_change = max(400, abs(self.true_hp - self.unit.currenthp)*4*GC.FRAMERATE)
                    self.last_update = Engine.get_time() + 200
                else: # Combat
                    self.time_for_change = max(200, abs(self.true_hp - self.unit.currenthp)*2*GC.FRAMERATE)
                    self.last_update = Engine.get_time()
            if self.transition_flag and Engine.get_time() > self.last_update:
                self.true_hp = Utility.easing(Engine.get_time() - self.last_update, self.oldhp, self.unit.currenthp - self.oldhp, self.time_for_change)
                # print(self.true_hp, Engine.get_time(), self.oldhp, self.unit.currenthp, self.time_for_change)
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

            team_dict = {'player': 'Blue',
                         'enemy': 'Red',
                         'enemy2': 'Purple',
                         'other': 'Green'}
            team = 'enemy' if isinstance(unit, TileObject.TileObject) else unit.team
            self.bg_surf = GC.IMAGESDICT[team_dict[team] + 'Health']
            self.c_surf = GC.IMAGESDICT[team_dict[team] + 'CombatStats']
            self.gem = GC.IMAGESDICT[team_dict[team] + 'CombatGem'] 

            # Swaps combat stat color
            if force_stats:
                self.c_surf = GC.IMAGESDICT[team_dict[force_stats] + 'CombatStats']
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
