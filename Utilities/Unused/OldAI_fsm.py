import pygame, random
from GlobalConstants import *
import Interaction, UnitObject, Dialogue, TileObject, Utility

class UnitAI(object):
    """
    # Class Name: UnitAI
    # Purpose: A Finite State Machine implementation of unit AI
    # This is the unit's personal AI. The unit can be forced to swap between
    # different AI states defined below
    """

    def __init__(self, unit, starting_state, purs_range=10, return_point = None):
        self.all_states = {'DoNothing': DoNothing(unit),
                           'Attack': Attack(unit),
                           'AttackVillage': AttackVillage(unit),
                           'Unlock': Unlock(unit, return_point),
                           'AttackWall': AttackWall(unit),
                           'AttackVillageWall': AttackVillageWall(unit),
                           'Pursue': Pursue(unit),
                           'PursueIgnoreOther': Pursue(unit, team_ignore='other'),
                           'SoftGuard': SoftGuard(unit),
                           'SoftGuardIgnoreOther': SoftGuard(unit, team_ignore='other'),
                           'HardGuard': HardGuard(unit),
                           'Escape': Escape(unit),
                           'Horse': Horse(unit),
                           'Fear': Fear(unit)}

        self.current_state = self.all_states[starting_state]

    def execute_turn(self, gameStateObj):
        """
        # Function Name: execute_turn
        # Purpose: Updates a unit's state and carries out the unit's turn
        """
        return self.current_state.act(gameStateObj)

    def clean_up(self):
        for state_name, state in self.all_states.iteritems():
            state.target_unit = None # Clean this

class AIState(object):
    def __init__(self, unit):
        """
        # Function Name: __init__
        # Purpose: Constructs the Generic AI State class
        # Input:   Unit - Unit to assign AI State to
        """
        self.unit = unit

        # This refers to a unit or tile that is being marked as this AI's target
        self.target_unit = None

    def think(self):
        pass

    def act(self, gameStateObj):
        pass

class Attack(AIState):
    """
    # Class Name: GeneralPurpose
    # Purpose: General Purpose state. Handles all AI, from Attacking, to Healing, to using a spell
    #          Currently does the work of Attack, Pursue, Healer. Needs an objective list maybe?
    # Objectives:  Attack, SoftGuard a point, HardGuard a point, Escape, Village, Wall 
    """
    def __init__(self, unit, name_ignore=[], team_ignore=[]):
        """
        # Function Name: __init__
        # Purpose: Constructs the General Purpose AI State class
        # Input:   unit - unit to assign AI State to
        #          range - range that the AI State should look around for
        """
        self.name = "Attack"
        self.range = 10
        self.name_ignore = name_ignore
        self.team_ignore = team_ignore
        AIState.__init__(self, unit) # Super

    def act(self, gameStateObj):
        if not self.unit.hasRunMoveAI:
            self.think(gameStateObj)
            if OPTIONS['debug']:
                print('Think', self.unit.name, self.unit.position, ('Target Unit: ', self.target_unit.name if self.target_unit else self.target_unit), ('Attack Position: ', self.attack_position))
            self.move(gameStateObj)
            self.unit.hasRunMoveAI = True
        elif not self.unit.hasRunAttackAI and self.unit.hasRunMoveAI:
            if OPTIONS['debug']:
                print('Attack', self.unit.name, self.unit.position)
            self.attack(gameStateObj)
            self.unit.hasRunAttackAI = True
            # If unit does not have canto, we're done
            if not any(status.canto for status in self.unit.status_effects):
                self.unit.hasRunGeneralAI = True
        elif self.unit.hasRunMoveAI and self.unit.hasRunAttackAI and not self.unit.hasRunGeneralAI and any(status.canto for status in self.unit.status_effects):
            if not self.unit.hasAttacked:
                self.canto_retreat(gameStateObj)
                self.move(gameStateObj)
            self.unit.hasRunGeneralAI = True
        else:
            if OPTIONS['debug']:
                print("Error: There's a problem with the AI.")

    def think(self, gameStateObj):
        # Purpose: Pre-action processing
        self.target_unit = None
        self.attack_position = None
        self.best_weapon = None
        self.select_target(gameStateObj)

    def canto_retreat(self, gameStateObj):
        valid_positions = self.get_true_valid_moves(gameStateObj)
        # get farthest away position from general direction of enemy units
        if valid_positions:
            avg_position = [0, 0]
            enemy_units = [unit for unit in gameStateObj.allunits if unit.position and self.unit.checkIfEnemy(unit)]
            if enemy_units:
                for unit in enemy_units:
                    avg_position[0] += unit.position[0]
                    avg_position[1] += unit.position[1]
                avg_position[0] = avg_position[0]/len(enemy_units)
                avg_position[1] = avg_position[1]/len(enemy_units)
                self.attack_position = sorted(valid_positions, key=lambda move:Utility.calculate_distance(avg_position, move))[-1]    

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        valid_moves = self.get_true_valid_moves(gameStateObj)
        self.main_algorithm(valid_moves, gameStateObj)

        available_targets = [target for target in gameStateObj.allunits if target.position and Utility.calculate_distance(self.unit.position, target.position) <= self.range \
                             and self.unit.checkIfEnemy(target) and target.team not in self.team_ignore and target.name not in self.name_ignore]
        if self.target_unit is None: # If we still haven't found anyone to act on in range
            self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)

        if self.attack_position is None: # If we still haven't found a legal path
            self.tertiary_algorithm(valid_moves, gameStateObj, available_targets, self.compute_priority_v1)
        
    def move(self, gameStateObj):
        """
        # Function Name: move
        # Purpose: Conducts the move action of a unit
        """
        # Acts only if a unit has a position to move to
        if self.attack_position:
            self.unit.path = self.unit.getPath(gameStateObj, self.attack_position)
            self.unit.isMoving = True
            self.unit.isActive = True
            return True
        else:
            return False

    def attack(self, gameStateObj):
        # Acts only if a unit has a defined best_weapon
        if self.best_weapon:
            if OPTIONS['debug']:
                print('Target Unit: ', self.target_unit.name)
            target_displacement = Utility.calculate_distance(self.unit.position, self.target_unit.position)

            # Checks if the target is in range of the equipped attack
            if target_displacement in self.best_weapon.RNG:
                self.unit.equip(self.best_weapon)
                defender, splash = Interaction.convert_positions(gameStateObj, self.unit, self.target_unit.position, self.best_weapon)
                gameStateObj.combatInstance = Interaction.start_combat(self.unit, defender, splash, self.best_weapon)
                gameStateObj.stateMachine.changeState('combat')
                if isinstance(defender, UnitObject.UnitObject) and self.unit.checkIfEnemy(defender):
                    self.unit.handle_fight_quote(defender, gameStateObj)
            else:
                self.check_mount(gameStateObj)
                self.check_dismount(gameStateObj)
                if OPTIONS['debug']:
                    print('No Attack...')
        else:
            self.check_mount(gameStateObj)
            self.check_dismount(gameStateObj)
            if OPTIONS['debug']:
                print('No Attack...')

    def check_mount(self, gameStateObj):
        if not self.unit.my_mount:
            adj_position = self.unit.getAdjacentPositions(gameStateObj)
            ally_units = [unit for unit in gameStateObj.allunits if unit.position and self.unit.checkIfAlly(unit) and unit.position in adj_position]
            for adjunit in ally_units:
                if 'Mount' in unit.components:
                    self.unit.mount(unit, gameStateObj)

    def check_dismount(self, gameStateObj):
        """Determines if unit should dismount from land-based mount to traverse water"""
        if self.unit.my_mount and not any(status.fleet_of_foot for status in self.unit.status_effects):
            adjtiles = self.unit.getAdjacentTiles(gameStateObj)
            # Determine which tile is closest to target
            closest_tile = sorted(adjtiles, key=lambda pos:Utility.calculate_distance(self.target_unit.position, pos.position))[0]
            if closest_tile.name in ['River', 'Coast', 'Bank', 'Floor']:
                self.unit.dismount(closest_tile.position, gameStateObj)
            elif all(adjtile.name in ['Floor', 'Throne', 'Wall'] for adjtile in adjtiles):
                self.unit.dismount(closest_tile.position, gameStateObj)
       
    def main_algorithm(self, valid_moves, gameStateObj):
        """
        # Determines what is the best action to take for each:
        # item
        # move
        # unit in range
        """
        max_target_priority = 0 # Default. Higher than 0 so really bad decisions don't get made (originally -100)
        # First looks for a target among those in range
        # For each item in inventory:
        for item in self.unit.items:
            for move in valid_moves:
                valid_targets = [unit for unit in self.unit.getTargets(gameStateObj, item, move) if unit.team not in self.team_ignore and unit.name not in self.name_ignore]
                if 0 in item.RNG: # Because the item is supposed to be used on oneself
                    valid_targets.append(self.unit) # But oneself is not actually at the move right now, but will be...
                for target in valid_targets:
                    target_priority = self.compute_priority(target, move, item, gameStateObj)
                    if OPTIONS['debug']:
                        print('TP', item.name, target.name, move, target_priority)
                    if target_priority > max_target_priority: # If new maximum, set all important values
                        self.target_unit = target
                        self.attack_position = move
                        self.best_weapon = item
                        max_target_priority = target_priority

    def compute_priority(self, target, move, item, gameStateObj):
        """
        # Function Name: compute_priority
        # Purpose: computes how good an action is. 0 is bad. 1 is great.
        """
        terms = []
        ### IF WEAPON
        if item.weapon and self.unit.checkIfEnemy(target):
            raw_damage = self.unit.compute_damage(target, gameStateObj, item)

            damage_term = Utility.clamp(raw_damage/float(target.stats['HP']), 0, 1)
            status_term = 1 if item.status else 0
            accuracy_term = Utility.clamp(self.unit.compute_hit(target, gameStateObj, item)/100.0, 0, 1)
            # Test to see if should just return 0.
            if (damage_term <= 0 and status_term <= 0) or accuracy_term <= 0:
                return 0
            terms.append((damage_term, 50))
            terms.append((accuracy_term, 30))
            weakness_term = Utility.clamp(1 - (target.currenthp - raw_damage)/float(target.stats['HP']), 0, 1)
            terms.append((weakness_term, 35))
            # Determine if I would be countered
            if target.getMainWeapon() and Utility.calculate_distance(move, target.position) in target.getMainWeapon().RNG:
                damage_i_would_take = target.compute_damage(self.unit, gameStateObj, target.getMainWeapon())
                accuracy_of_opponent = target.compute_hit(self.unit, gameStateObj, target.getMainWeapon())/100.0
                counter_term = Utility.clamp(1 - damage_i_would_take*accuracy_of_opponent/float(self.unit.stats['HP']), 0, 1)
            else:
                counter_term = 1
            terms.append((counter_term, 20))
            terms.append((status_term, 10))
            
        elif item.spell:
            if item.spell.targets == 'Ally':
                if self.unit.checkIfAlly(target):
                    if item.spell.heal:
                        closest_enemy_term = Utility.clamp(self.unit.distance_to_closest_enemy(gameStateObj, move)/100.0, 0, 1)
                        terms.append((closest_enemy_term, 30))
                        weakness_term = Utility.clamp((target.stats['HP'] - target.currenthp)/float(target.stats['HP']) - .5, 0, 1)
                        if weakness_term <= 0:
                            return 0
                        terms.append((weakness_term, 60))
                else:
                    return 0
            else: # TODO Not set up yet
                return 0
        elif item.heal:
            closest_enemy_term = Utility.clamp(self.unit.distance_to_closest_enemy(gameStateObj, move)/20.0, 0, 1)
            terms.append((closest_enemy_term, 30))
            weakness_term = Utility.clamp((self.unit.stats['HP'] - self.unit.currenthp)/float(self.unit.stats['HP']) - .5, 0, 1)
            if weakness_term <= 0:
                return 0
            terms.append((weakness_term, 30))

        # Process terms
        weight_sum = sum([term[1] for term in terms])
        if weight_sum <= 0:
            return 0
        if OPTIONS['debug']:
            print('Processed Terms: ', [term[0] for term in terms])
        return sum([float(term[0]*term[1]) for term in terms])/weight_sum

    def secondary_algorithm(self, gameStateObj, available_targets, priority_function):
        """
        # If no good action was available for targets in range by the main_algorithm,
        # the secondary algorithm determines which of the targets I should
        # move towards.
        """
        # Find best target
        max_tp = 0
        best_target = None
        best_path = None
        for target in available_targets:
            # Find a path to target
            my_path = None
            for nearby_position in [(target.position[0] + 1, target.position[1]), (target.position[0] - 1, target.position[1]),\
                                    (target.position[0], target.position[1] + 1), (target.position[0], target.position[1] - 1)]:
                if nearby_position[0] >= 0 and nearby_position[1] >= 0 and \
                    nearby_position[0] < gameStateObj.map.width and nearby_position[1] < gameStateObj.map.height and \
                    not any(unit.position == nearby_position for unit in gameStateObj.allunits if self.unit.checkIfEnemy(unit)):
                    my_path = self.unit.getPath(gameStateObj, nearby_position)
                    if my_path:
                        break
            # We didn't find a path, so ignore target and continue
            if not my_path:
                if OPTIONS['debug']:
                    print("No valid path to this target.", target.name)
                continue
            # We found a path
            tp = priority_function(target, gameStateObj, len(my_path))
            if tp > max_tp:
                max_tp = tp
                best_target = target
                best_path = my_path

        # Now we have the best target...
        if best_target:
            self.target_unit = best_target
            # So we have the position I will move to.
            self.attack_position = Utility.travel_algorithm(gameStateObj, best_path, self.unit.movement_left, self.unit)
            # Check to make sure there's not some better path if we take into account our ally's positions
            new_path = self.unit.getPath(gameStateObj, best_path[0], ally_block=True)
            if new_path:
                possible_position = Utility.travel_algorithm(gameStateObj, new_path, self.unit.movement_left, self.unit)
                # Now which is closer to target by raw distance?
                if Utility.calculate_distance(best_target.position, possible_position) < Utility.calculate_distance(best_target.position, self.attack_position):
                    self.attack_position = possible_position
        else:
            if OPTIONS['debug']:
                print('No good target for secondary_algorithm!')
        self.best_weapon = None

    def tertiary_algorithm(self, valid_moves, gameStateObj, available_targets, priority_function):
        """
        # If there are no legal paths to enemy units that are worth moving towards,
        # just move to the position closest to the average position of enemy units enemy unit
        """
        if valid_moves:
            avg_position = [0, 0]
            if available_targets:
                for unit in available_targets:
                    avg_position[0] += unit.position[0]
                    avg_position[1] += unit.position[1]
                avg_position[0] = avg_position[0]/len(available_targets)
                avg_position[1] = avg_position[1]/len(available_targets)
                self.attack_position = sorted(valid_moves, key=lambda move:Utility.calculate_distance(avg_position, move))[0]
        self.best_weapon = None
                
    def compute_priority_v1(self, target, gameStateObj, distance=None):
        """
        # Function Name: compute_priority_v1
        """

        # Distance Term: How close is the target to you?
        distance_term = 0
        if distance:
            distance_term = (self.range - distance)/float(self.range)
        else:
            target_distance = Utility.calculate_distance(self.unit.position, target.position)
            distance_term = (self.range - target_distance)/float((self.range))
        distance_weight = 60

        # Weakness Term: How weak is the target?
        # fraction of total target HP depleted
        if isinstance(target, UnitObject.UnitObject):
            weakness_term = float(target.stats['HP'] - target.currenthp)/float(target.stats['HP'])
            weakness_weight = 30

            # Damage Term: How much damage can I inflict on the target (fraction of total HP)?
            max_damage = 0
            for item in self.unit.items:
                if item.weapon:
                    raw_damage = self.unit.compute_damage(target, gameStateObj, item)
                    if raw_damage > max_damage:
                        max_damage = raw_damage

            if max_damage == 0:
                if OPTIONS['debug']:
                    print(target.name, 'Total:', 0, 'Damage dealt is 0')
                return 0 # If no damage could be dealt, ignore.
            damage_term = min(float(max_damage)/float(target.stats['HP']), 1.0)
            damage_weight = 30
        else:
            weakness_term = 0
            weakness_weight = 30
            damage_term = 0
            damage_weight = 30

        priority = (distance_term*distance_weight + weakness_term*weakness_weight + damage_term*damage_weight)
        if OPTIONS['debug']:
            print(target.name, 'Total:', priority, 'Distance:', distance_term, 'Weakness:', weakness_term, 'Damage:', damage_term)
        return priority

    def get_true_valid_moves(self, gameStateObj):
        valid_moves = self.unit.getValidMoves(gameStateObj)
        # Make sure we don't move on top of another unit... getValidMoves returns positions coincident with allied units
        other_unit_positions = [unit.position for unit in gameStateObj.allunits if unit.position and unit is not self.unit]
        valid_moves = [valid_move for valid_move in valid_moves if not valid_move in other_unit_positions]
        return valid_moves

class Pursue(Attack):
    """
    # Class Name: Pursue
    # Purpose: Modification of regular attack state
    #          Pursues really far out
    """
    def __init__(self, unit, name_ignore=[], team_ignore=[]):
        Attack.__init__(self, unit, name_ignore, team_ignore)
        self.name = "Pursue"
        self.range = 40

class SoftGuard(Attack):
    """
    # Class Name: SoftGuard
    # Purpose: Modification of regular attack state
    #          Will not move unless an enemy is in attack distance. 
    #          If no enemy in attack distance, move back to original position
    """
    def __init__(self, unit, name_ignore=[], team_ignore=[]):
        Attack.__init__(self, unit, name_ignore, team_ignore)
        self.name = "SoftGuard"
        self.range = 10
        self.position = self.unit.position

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        # Slightly modified available targets
        valid_moves = self.get_true_valid_moves(gameStateObj)
        self.main_algorithm(valid_moves, gameStateObj)

        # Replacement for secondary algorithm
        if self.target_unit is None: # If we still haven't found anyone, 
            self.attack_position = self.position

class HardGuard(Attack):
    """
    # Class Name: SoftGuard
    # Purpose: Modification of regular attack state
    #          Will not move
    """
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = "HardGuard"
        self.range = 10
        self.position = self.unit.position

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        valid_moves = [self.position]
        self.main_algorithm(valid_moves, gameStateObj)

        self.attack_position = self.unit.position

    def canto_retreat(self, gameStateObj):
        self.attack_position = self.unit.position

class DoNothing(AIState):
    def __init__(self, unit):
        self.name = "DoNothing"
        self.range = 0
        AIState.__init__(self, unit) # Super

    def act(self, gameStateObj):
        if self.unit.hasMoved:
            self.unit.hasAttacked = True
            self.unit.hasRunAttackAI = True
            self.unit.hasRunGeneralAI = True
        else:
            self.unit.hasMoved = True
            self.unit.hasRunMoveAI = True

class AttackVillage(Attack):
    """
    # Class Name: AttackVillage
    # Purpose: Modification of regular attack state
    #          Will seek out nearby villages and attempt to destroy them.
    #          However, it will also target enemies.
    """
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = "AttackVillage"
        self.range = 40

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        valid_moves = self.get_true_valid_moves(gameStateObj)
        self.main_algorithm(valid_moves, gameStateObj)
        # Then, if no target it looks for a village in range
        # For each village in range that is still open
        if self.target_unit is None:
            self.main_village_algorithm(valid_moves, gameStateObj)

        if self.target_unit is None: # If we still haven't found anyone, check out all villages in the area
            available_targets = [tile for position, tile in gameStateObj.map.tiles.iteritems() if tile.name in ['Village', 'House'] and 'Destructible' in gameStateObj.map.tile_info_dict[position]]
            self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)

        available_targets = [target for target in gameStateObj.allunits if target.position and self.unit.checkIfEnemy(target) and Utility.calculate_distance(self.unit.position, target.position) <= self.range]
        if self.attack_position is None:
            self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)
                                               
        if self.attack_position is None: # If we still haven't found a legal path
            self.tertiary_algorithm(valid_moves, gameStateObj, available_targets, self.compute_priority_v1)

    def main_village_algorithm(self, valid_moves, gameStateObj):
        villages_in_range = []
        # Unit can only attack villages that are also destructible
        possible_villages = [(position, tile) for position, tile in gameStateObj.map.tiles.iteritems() if tile.name in ['Village', 'House'] and 'Destructible' in gameStateObj.map.tile_info_dict[position]]
        for position, tile in possible_villages:
            if position in valid_moves:
                villages_in_range.append((position, tile))
        if villages_in_range:
            self.attack_position = villages_in_range[0][0] # First village found, and position of that village
            self.target_unit = villages_in_range[0][1] # First village found, and actual tile
            self.best_weapon = None

    def attack(self, gameStateObj):
        # Acts only if a unit has a defined best_weapon
        if self.best_weapon:
            if OPTIONS['debug']:
                print('Target Unit: ', self.target_unit.name)
            target_displacement = Utility.calculate_distance(self.unit.position, self.target_unit.position)

            # Checks if the target is in range of the equipped attack
            if target_displacement in self.best_weapon.RNG:
                self.unit.equip(self.best_weapon)
                defender, splash = Interaction.convert_positions(gameStateObj, self.unit, self.target_unit.position, self.best_weapon)
                gameStateObj.combatInstance = Interaction.start_combat(self.unit, defender, splash, self.best_weapon)
                gameStateObj.stateMachine.changeState('combat')
                if isinstance(defender, UnitObject.UnitObject) and self.unit.checkIfEnemy(defender):
                    self.unit.handle_fight_quote(defender, gameStateObj)
            else:
                if OPTIONS['debug']:
                    print('No Attack...')
        elif isinstance(self.target_unit, TileObject.TileObject):
            gameStateObj.map.destroy(self.target_unit, gameStateObj)
        else:
            if OPTIONS['debug']:
                print('No Attack...')

class Unlock(Attack):
    """
    # Class Name: Unlock
    # Purpose: Modification of regular attack state
    #          Will seek out nearby unlockable tiles and attempt to unlock them.
    #          Will not attack enemies unless no other options
    """

    def __init__(self, unit, return_point):
        Attack.__init__(self, unit)
        self.name = "Unlock"
        self.range = 40
        self.return_point = return_point

    def select_target(self, gameStateObj):
        valid_moves = self.get_true_valid_moves(gameStateObj)
        # First check for chests/doors in range
        self.main_unlock_algorithm(valid_moves, gameStateObj)
        # Then check for chests/doors outside of range that are possible to reach
        if self.target_unit is None:
            available_targets = [tile for position, tile in gameStateObj.map.tiles.iteritems() if 'Locked' in gameStateObj.map.tile_info_dict[position] and Utility.calculate_distance(position, self.return_point) < self.range]
            self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)
        # Then return to point
        if self.target_unit is None:
            self.attack_position = Utility.travel_algorithm(gameStateObj, self.unit.getPath(gameStateObj, self.return_point), self.unit.movement_left, self.unit)

    def attack(self, gameStateObj):
        # Attacks if unit has a defined best_weapon
        if self.best_weapon:
            self.unit.equip(self.best_weapon)
            defender, splash = Interaction.convert_positions(gameStateObj, self.unit, self.target_unit.position, self.best_weapon)
            gameStateObj.combatInstance = Interaction.start_combat(self.unit, defender, splash, self.best_weapon)
            gameStateObj.stateMachine.changeState('combat')
            if isinstance(defender, UnitObject.UnitObject) and self.unit.checkIfEnemy(defender):
                self.unit.handle_fight_quote(defender, gameStateObj)
        elif self.attack_position == self.return_point:
            self.unit.escape(gameStateObj)
        elif :
            # First check for treasure chest
            if 'Locked' in gameStateObj.map.tile_info_dict[self.unit.position]:
                locked_num = gameStateObj.map.tile_info_dict[self.unit.position]['Locked']
            else:
                locked_num = [gameStateObj.map.tile_info_dict[pos]['Locked'] for pos in self.unit.getAdjacentPositions(gameStateObj) if 'Locked' in gameStateObj.map.tile_info_dict[pos]][0]
            unlock_script = Dialogue.Dialogue_Scene('Data/Level' + str(gameStateObj.counters['level']) + '/unlockScript' + str(locked_num) + '.txt', gameStateObj, self.unit)
            gameStateObj.message.append(unlock_script)
            gameStateObj.stateMachine.changeState('dialogue')

    def main_unlock_algorithm(self, valid_moves, gameStateObj):
        locked_in_range = []
        possible_locked = [(position, tile) for position, tile in gameStateObj.map.tiles.iteritems() if 'Locked' in gameStateObj.map.tile_info_dict[position]]
        # Chests than doors
        for position, tile in possible_locked:
            if tile.name == "Chest":
                if position in valid_moves:
                    self.attack_position = position
                    self.target_unit = tile
                    self.best_weapon = None
                    return
        for position, tile in possible_locked:
            if tile.name == "Door":
                for valid_move in valid_moves:
                    if Utility.calculate_distance(position, valid_move) == 1:
                        self.attack_position = valid_move
                        self.target_unit = tile
                        self.best_weapon = None
                        return

class AttackWall(Attack):
    """
    # Class Name: AttackWall
    # Purpose: Modification of regular attack state
    #          Will seek out nearby walls and attempt to destroy them.
    #          However, it will also target enemies.
    """
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = "AttackWall"
        self.range = 10

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        valid_moves = self.get_true_valid_moves(gameStateObj)
        if self.target_unit is None:
            self.main_algorithm(valid_moves, gameStateObj)

        if self.target_unit is None: # If we still haven't found anyone, check out all other units in the area
            if OPTIONS['debug']:
                print('No targets in range')
            available_targets = [target for target in gameStateObj.allunits if target.position and Utility.calculate_distance(self.unit.position, target.position) <= self.range]
            if available_targets:
                self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)
                                               
            else: # Wow, just nobody is around
                # No target in range
                if OPTIONS['debug']:
                    print('No target in pursdist')

class AttackVillageWall(AttackVillage):
    """
    # Class Name: AttackVillageWall
    # Purpose: Modification of regular attack state
    #          Will seek out nearby villages and attempt to destroy them.
    #          However, it will also target enemies and walls.
    """
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = "AttackVillageWall"
        self.range = 40

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        valid_moves = self.get_true_valid_moves(gameStateObj)
        self.main_algorithm(valid_moves, gameStateObj)
        # Then, if no target it looks for a village in range
        # For each village in range that is still open
        if self.target_unit is None:
            if OPTIONS['debug']:
                print("Villages in range!")
            self.main_village_algorithm(valid_moves, gameStateObj)

        ### MODIFICATION! ###
        # Then it looks for walls in range
        if self.target_unit is None:
            if OPTIONS['debug']:
                print("Walls in range!")
            self.wall_algorithm(valid_moves, gameStateObj)

        if self.target_unit is None: # If we still haven't found anyone, check out all villages in the area
            available_targets = [tile for position, tile in gameStateObj.map.tiles.iteritems() if tile.name in ['Village', 'House'] and 'Destructible' in gameStateObj.map.tile_info_dict[position]]
            self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)

        available_targets = [target for target in gameStateObj.allunits if target.position and self.unit.checkIfEnemy(target) and Utility.calculate_distance(self.unit.position, target.position) <= self.range]
        if self.attack_position is None:
            self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)
                                               
        if self.attack_position is None: # If we still haven't found a legal path
            self.tertiary_algorithm(valid_moves, gameStateObj, available_targets, self.compute_priority_v1)

    def wall_algorithm(self, valid_moves, gameStateObj):
        """
        # Determines what is the best action to take for each:
        # item
        # move
        # wall in range
        """
        max_target_priority = 0 # Default. Higher than 0 so really bad decisions don't get made (originally -100)
        # First looks for a target among those in range
        # For each item in inventory:
        for item in self.unit.items:
            for move in valid_moves:
                valid_targets = self.unit.getWalls(gameStateObj, item, move)
                for target in valid_targets:
                    target_priority = self.compute_wall_priority(target, move, item, gameStateObj)
                    if OPTIONS['debug']:
                        print('TP', item.name, target.name, move, target_priority)
                    if target_priority > max_target_priority: # If new maximum, set all important values
                        self.target_unit = target
                        self.attack_position = move
                        self.best_weapon = item
                        max_target_priority = target_priority

    def compute_wall_priority(self, target, move, item, gameStateObj):
        if item.weapon and self.unit.canWield(item):
            return Utility.calculate_distance(self.unit.position, move) * item.weapon.MT
        else:
            return 0

class Escape(Attack):
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = "Escape"
        self.range = 50

    def select_target(self, gameStateObj):
        # Purpose: Selects a target among the targets in range y sorting priorities
        # along with a position to attack from
        valid_moves = self.get_true_valid_moves(gameStateObj)
        available_targets = [tile for (position, tile) in gameStateObj.map.tiles.iteritems() if \
                             position in gameStateObj.map.tile_info_dict and 'Escape' in gameStateObj.map.tile_info_dict[position]]
        self.secondary_algorithm(gameStateObj, available_targets, self.compute_priority_v1)

    def attack(self, gameStateObj):
        if 'Escape' in gameStateObj.map.tile_info_dict[self.unit.position]:
            self.unit.escape(gameStateObj)
        self.unit.hasRunGeneralAI = True

class Horse(Attack):
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = "Horse"
        self.range = 10

    def select_target(self, gameStateObj):
        # Purpose: Runs away from enemies
        valid_moves = self.get_true_valid_moves(gameStateObj)
        enemy_units = [unit for unit in gameStateObj.allunits if unit.position and self.unit.checkIfEnemy(unit) and Utility.calculate_distance(self.unit.position, unit.position) <= self.range]
        if valid_moves:
            if enemy_units:
                avg_position = [0, 0]
                for unit in enemy_units:
                    avg_position[0] += unit.position[0]
                    avg_position[1] += unit.position[1]
                avg_position[0] = avg_position[0]/len(available_targets)
                avg_position[1] = avg_position[1]/len(available_targets)
                self.attack_position = sorted(valid_moves, key=lambda move:Utility.calculate_distance(avg_position, move))[-1]
            else:
                ally_units = [unit for unit in gameStateObj.allunits if unit.position and self.unit.checkIfAlly(unit) and not unit.my_mount and not 'Mount' in unit.components]
                if ally_units:
                    avg_position = [0, 0]
                    for unit in ally_units:
                        avg_position[0] += unit.position[0]
                        avg_position[1] += unit.position[1]
                    avg_position[0] = avg_position[0]/len(available_targets)
                    avg_position[1] = avg_position[1]/len(available_targets)
                    self.attack_position = sorted(valid_moves, key=lambda move:Utility.calculate_distance(avg_position, move))[0]
                else:
                    self.attack_position = self.unit.position
        else:
            self.attack_position = self.unit.position
        self.best_weapon = None

    def attack(self, gameStateObj):
        self.unit.hasRunGeneralAI = True

class Fear(Attack):
    def __init__(self, unit):
        Attack.__init__(self, unit)
        self.name = 'Fear'
        self.range = 50

    def select_target(self, gameStateObj):
        # Purpose: Runs away from enemies
        valid_moves = self.get_true_valid_moves(gameStateObj)
        # Finds position furthest away from enemies
        dist_to_enemy = 0
        best_move = self.unit.position
        for move in valid_moves:
            new_dist = self.distance_to_closest_enemy(gameStateObj, move)
            if new_dist > dist_to_enemy:
                dist_to_enemy = new_dist
                best_move = move

        self.attack_position = best_move
        self.best_weapon = None

    def attack(self, gameStateObj):
        self.unit.hasRunGeneralAI = True
