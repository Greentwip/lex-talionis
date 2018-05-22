#! usr/bin/env python2.7
from collections import OrderedDict
import os
def read_config_file():
    lines = OrderedDict([('debug', 1),
                         ('cheat', 1),
                         ('Screen Size', 2),
                         ('Animation', 'Always'),
                         ('Unit Speed', 120),
                         ('Text Speed', 10),
                         ('Cursor Speed', 80),
                         ('Show Terrain', 1),
                         ('Show Objective', 1),
                         ('Autocursor', 1),
                         ('Music Volume', 0.0),
                         ('Sound Volume', 1.0),
                         ('Autoend Turn', 1),
                         ('Confirm End', 1),
                         ('Display Hints', 1),
                         ('HP Map Team', 'All'),
                         ('HP Map Cull', 'All'),
                         ('key_SELECT', 120),
                         ('key_BACK', 122),
                         ('key_INFO', 99),
                         ('key_AUX', 97),
                         ('key_LEFT', 276),
                         ('key_RIGHT', 275),
                         ('key_UP', 273),
                         ('key_DOWN', 274),
                         ('key_START', 115)])

    # Try saves folder first
    if os.path.isfile('Saves/config.ini'):
        with open('Saves/config.ini') as config_file:
            for line in config_file:
                split_line = line.strip().split('=')
                lines[split_line[0]] = split_line[1]
    elif os.path.isfile('Data/config.ini'):
        with open('Data/config.ini') as config_file:
            for line in config_file:
                split_line = line.strip().split('=')
                lines[split_line[0]] = split_line[1]

    lines['debug'] = int(lines['debug'])
    lines['cheat'] = int(lines['cheat'])
    lines['Screen Size'] = int(lines['Screen Size'])
    lines['Unit Speed'] = int(lines['Unit Speed'])
    lines['Text Speed'] = int(lines['Text Speed'])
    lines['Cursor Speed'] = int(lines['Cursor Speed'])
    lines['Show Terrain'] = int(lines['Show Terrain'])
    lines['Show Objective'] = int(lines['Show Objective'])
    lines['Autocursor'] = int(lines['Autocursor'])
    lines['Music Volume'] = float(lines['Music Volume'])
    lines['Sound Volume'] = float(lines['Sound Volume'])
    lines['Autoend Turn'] = int(lines['Autoend Turn'])
    lines['Confirm End'] = int(lines['Confirm End'])
    lines['Display Hints'] = int(lines['Display Hints'])
    lines['key_SELECT'] = int(lines['key_SELECT'])
    lines['key_BACK'] = int(lines['key_BACK'])
    lines['key_INFO'] = int(lines['key_INFO'])
    lines['key_AUX'] = int(lines['key_AUX'])
    lines['key_LEFT'] = int(lines['key_LEFT'])
    lines['key_RIGHT'] = int(lines['key_RIGHT'])
    lines['key_UP'] = int(lines['key_UP'])
    lines['key_DOWN'] = int(lines['key_DOWN'])
    lines['key_START'] = int(lines['key_START'])

    return lines

def write_config_file():
    with open('Saves/config.ini', 'w') as config_file:
        write_out = '\n'.join([name + '=' + str(value) for name, value in OPTIONS.items()])
        config_file.write(write_out)

def read_constants_file():
    lines = {'max_items': 5, # How many items can a unit carry at maximum
             'speed_to_double': 4, # How much AS is needed to double
             'max_promotions': 10, # Allowed number of promotion options for a unit
             'mounted_aid': 15, # What a mounted units CON is subtracted from to determine AID
             'crit': 3, # 0 - No critting, 1 - 2x damage minus 1x defense, 2 - 2x damage minus 2x defense, 3 - 3x damage minus 3x defense
             'death': 2,
             'flying_mcost_column': 6, # What column flying units should use in mcost.txt (0 indexed)
             'fleet_mcost_column': 7, # What column units with fleet_of_foot should use in mcost.txt (0 indexed)
             'exp_curve': 2.3, # How linear the exp curve is. Higher = less linear
             'exp_magnitude': 0.0125, # Higher the number, the more exp gotten for each interaction overall
             'exp_offset': 0, # The exp curve indirectly keeps the player characters near the enemy's level + 0. Change this to change the "+0"
             'status_exp': 15, # How much exp is gotten for using a status spell
             'heal_curve': 1.0, # How much to multiply the amount healed by
             'heal_magnitude': 7, # Added to total amount healed 
             'heal_min': 5, # Minimum amount gained for healing
             'kill_multiplier': 2.5, # Normal exp is multiplied by this when you get a kill (Normal FE = 3.0)
             'boss_bonus': 40, # Added to total exp on killing a boss
             'min_exp': 1, # Minimum amount of experience gained for just existing in combat
             'kill_worth': 20, # How much damage is worth a kill in the Records
             'support_points': 12, # Number of points needed for one level of support
             'line_of_sight': 1, # Whether to use line of sight algorithm when choosing targets for weapons
             'spell_line_of_sight': 0, # Whether to use line of sight algorithm when choosing targets for spells
             'aura_los': 1, # Whether to use line of sight algorithm for auras
             'simultaneous_aoe': 1, # Whether AOE attacks on many targets are resolved simultaneously or in order
             'def_double': 1, # Whether units on defense can double their attackers
             'support': 1, # Whether this game has supports
             'enemy_leveling': 1, # How to level up non-player units
             'growths': 3,
             'rng': 'true_hit', # How hits are calculated ('classic', 'true_hit', 'true_hit+', 'no_rng', 'hybrid') # FE6-13 uses true_hit
             'set_roll': 49, # used for 'no_rng' mode. Determines threshold at which attacks miss. Ex. Any attack with hitrate <= set_roll, misses
             'num_skills': 5, # How many class_skills a fully ranked unit should have (not actually a hard limit, just for drawing)
             'max_stat': 20, # Maximum value that a non-HP stat can be. Irrespective of class caps. 
             'num_stats': 10, # Number of stats that a unit has (Includes HP, CON, and MOV)
             'stat_names': 'HP,STR,MAG,SKL,SPD,LCK,DEF,RES,CON,MOV', # Stat names. These are mostly hardset. Don't change them without consulting rainlash
             'difficulties': 'Normal,Hard,Lunatic',
             'only_difficulty': -1,
             'max_level': '20', # Maximum Level for class by tier ('10, 20, 20,')
             'auto_promote': 0, # Promote after max-level?
             'damage_str_coef': 1.0,
             'damage_mag_coef': 1.0,
             'avoid_speed_coef': 2.0,
             'avoid_luck_coef': 1.0,
             'accuracy_skill_coef': 2.0,
             'accuracy_luck_coef': 0.5,
             'crit_accuracy_skill_coef': 1.0,
             'crit_avoid_luck_coef': 1.0,
             'defense_coef': 1.0}

    if os.path.isfile('Data/constants.ini'):
        with open('Data/constants.ini') as constants_file:
            for line in constants_file:
                if not line.startswith(';'):
                    split_line = line.strip().split('=')
                    lines[split_line[0]] = split_line[1]

    lines['max_items'] = int(lines['max_items'])
    lines['max_promotions'] = int(lines['max_promotions'])
    lines['speed_to_double'] = int(lines['speed_to_double'])
    lines['mounted_aid'] = int(lines['mounted_aid'])
    lines['crit'] = int(lines['crit'])
    lines['death'] = int(lines['death'])
    lines['flying_mcost_column'] = int(lines['flying_mcost_column'])
    lines['fleet_mcost_column'] = int(lines['fleet_mcost_column'])
    lines['exp_curve'] = float(lines['exp_curve'])
    lines['exp_magnitude'] = float(lines['exp_magnitude'])
    lines['exp_offset'] = int(lines['exp_offset'])
    lines['status_exp'] = int(lines['status_exp'])
    lines['heal_curve'] = float(lines['heal_curve'])
    lines['heal_magnitude'] = float(lines['heal_magnitude'])
    lines['heal_min'] = float(lines['heal_min'])
    lines['kill_multiplier'] = float(lines['kill_multiplier'])
    lines['boss_bonus'] = float(lines['boss_bonus'])
    lines['min_exp'] = int(lines['min_exp'])
    lines['support_points'] = int(lines['support_points'])
    lines['line_of_sight'] = int(lines['line_of_sight'])
    lines['spell_line_of_sight'] = int(lines['spell_line_of_sight'])
    lines['aura_los'] = int(lines['aura_los'])
    lines['simultaneous_aoe'] = int(lines['simultaneous_aoe'])
    lines['def_double'] = int(lines['def_double'])
    lines['support'] = int(lines['support'])
    lines['enemy_leveling'] = int(lines['enemy_leveling'])
    lines['growths'] = int(lines['growths'])
    lines['set_roll'] = int(lines['set_roll'])
    lines['num_skills'] = int(lines['num_skills'])
    lines['max_stat'] = int(lines['max_stat'])
    lines['num_stats'] = int(lines['num_stats'])
    lines['stat_names'] = lines['stat_names'].split(',')
    lines['difficulties'] = lines['difficulties'].split(',')
    lines['max_level'] = [int(n) for n in lines['max_level'].split(',')]
    lines['auto_promote'] = int(lines['auto_promote'])
    lines['damage_str_coef'] = float(lines['damage_str_coef'])
    lines['damage_mag_coef'] = float(lines['damage_mag_coef'])
    lines['avoid_speed_coef'] = float(lines['avoid_speed_coef'])
    lines['avoid_luck_coef'] = float(lines['avoid_luck_coef'])
    lines['accuracy_skill_coef'] = float(lines['accuracy_skill_coef'])
    lines['accuracy_luck_coef'] = float(lines['accuracy_luck_coef'])
    lines['crit_accuracy_skill_coef'] = float(lines['crit_accuracy_skill_coef'])
    lines['crit_avoid_luck_coef'] = float(lines['crit_avoid_luck_coef'])
    lines['defense_coef'] = float(lines['defense_coef'])

    return lines

def read_growths_file():
    # HP, STR, MAG, SKL, SPD, LCK, DEF, RES, CON, MOV
    lines = {'enemy_growths': ','.join(['0'] * CONSTANTS['num_stats']),
             'player_growths': ','.join(['0'] * CONSTANTS['num_stats']),
             'enemy_bases': ','.join(['0'] * CONSTANTS['num_stats']),
             'player_bases': ','.join(['0'] * CONSTANTS['num_stats'])}

    if os.path.isfile('Data/growths.txt'):
        with open('Data/growths.txt') as growths_file:
            for line in growths_file:
                split_line = line.strip().split(';')
                lines[split_line[0]] = split_line[1]

    lines['enemy_growths'] = [int(num) for num in lines['enemy_growths'].split(',')]
    lines['player_growths'] = [int(num) for num in lines['player_growths'].split(',')]
    lines['enemy_bases'] = [int(num) for num in lines['enemy_bases'].split(',')]
    lines['player_bases'] = [int(num) for num in lines['player_bases'].split(',')]
    assert len(lines['enemy_growths']) == CONSTANTS['num_stats']
    assert len(lines['player_growths']) == CONSTANTS['num_stats']
    assert len(lines['enemy_bases']) == CONSTANTS['num_stats']
    assert len(lines['player_bases']) == CONSTANTS['num_stats']

    return lines

def read_words_file():
    # Dictionary that returns key if its not present
    class WordDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key, key)
    lines = WordDict()
    if os.path.isfile('Data/words.txt'):
        with open('Data/words.txt') as words_file:
            for line in words_file:
                split_line = line.strip().split(';')
                lines[split_line[0]] = split_line[1]
    else:
        print("ERROR! No words.txt file found in the data directory.")

    return lines

OPTIONS = read_config_file()
if not __debug__:
    OPTIONS['debug'] = False
print('Debug: %s' % (OPTIONS['debug']))
CONSTANTS = read_constants_file()
CONSTANTS['Unit Speed'] = OPTIONS['Unit Speed']
WORDS = read_words_file()
text_speed_options = list(reversed([1, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150]))
