#! usr/bin/env python2.7
from collections import OrderedDict
import os
def read_config_file():
    lines = OrderedDict([('debug', True),
                         ('screen_scale', 2),
                         ('Animation', 0),
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

    if os.path.isfile('Data/config.txt'):
        with open('Data/config.txt') as config_file:
            for line in config_file:
                split_line = line.strip().split(';')
                lines[split_line[0]] = split_line[1]

    lines['debug'] = bool(lines['debug'])
    lines['screen_scale'] = int(lines['screen_scale'])
    lines['Animation'] = int(lines['Animation'])
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
    #with open('Data/config.txt', 'w') as config_file:
    with open('Data/config.txt', 'w') as config_file:
        write_out = '\n'.join([name + ';' + str(value) for name, value in OPTIONS.iteritems()])
        config_file.write(write_out)
        #for name, value in OPTIONS.iteritems():
        #    config_file.write(name + ';' + str(value) + '\n')

def read_constants_file():
    lines = {'max_items': 5, # How many items can a unit carry at maximum
             'speed_to_double': 4, # How much AS is needed to double
             'normal_movement': 1, # How many movement points does a normal tile cost to traverse
             'flying_mcost_column': 6, # What column flying units should use in mcost.txt (0 indexed)
             'fleet_mcost_column': 7, # What column units with fleet_of_foot should use in mcost.txt (0 indexed)
             'num_levels': 11, # Number of levels in game
             'exp_curve': 2.3, # How linear the exp curve is. Higher = less linear
             'exp_magnitude': 0.0125, # Higher the number, the more exp gotten for each interaction overall
             'exp_offset': 0, # The exp curve indirectly keeps the player characters near the enemy's level + 0. Change this to change the "+0"
             'status_exp': 15, # How much exp is gotten for using a status spell
             'heal_curve': 1.0, # How much to multiply the amount healed by.
             'heal_magnitude': 7, # Added to total amount healed 
             'kill_multiplier': 2.5, # Normal exp is multiplied by this when you get a kill (Normal FE = 3.0)
             'kill_worth': 20, # How much damage is worth a kill in the Records
             'support_points': 12, # Number of points needed for one level of support
             'line_of_sight': 1, # Whether to use line of sight algorithm when choosing targets for weapons
             'spell_line_of_sight': 0, # Whether to use line of sight algorithm when choosing targets for spells
             'aura_los': 1, # Whether to use line of sight algorithm for auras
             'simultaneous_aoe': 0, # Whether AOE attacks on many targets are resolved simultaneously or in order
             'def_double': 1, # Whether units on defense can double their attackers
             'support': 1, # Whether this game has supports
             'casual': 0, # Whether player units die when they are killed (1 - casual, 0 - classic)
             'player_leveling': 'random', # How to level up player units ('fixed', 'random', and 'hybrid' are valid choices) # Normal FE uses random
             'enemy_leveling': 'fixed', # How to level up non-player units
             'rng': 'true_hit', # How hits are calculated ('classic', 'true_hit', 'true_hit+', 'no_rng', 'hybrid') # FE6-13 uses true_hit
             'set_roll': 49, # used for 'no_rng' mode. Determines threshold at which attacks miss. Ex. Any attack with hitrate <= set_roll, misses
             'num_skills': 5, # How many class_skills a fully ranked unit should have (not actually a hard limit, just for drawing)
             'max_stat': 20, # Maximum value that a non-HP stat can be. Irrespective of class caps. 
             'max_level': 10} # Maximum Level for any class. Any higher and you auto-promote

    if os.path.isfile('Data/constants.txt'):
        with open('Data/constants.txt') as constants_file:
            for line in constants_file:
                split_line = line.strip().split(';')
                lines[split_line[0]] = split_line[1]

    lines['max_items'] = int(lines['max_items'])
    lines['speed_to_double'] = int(lines['speed_to_double'])
    lines['normal_movement'] = int(lines['normal_movement'])
    lines['flying_mcost_column'] = int(lines['flying_mcost_column'])
    lines['fleet_mcost_column'] = int(lines['fleet_mcost_column'])
    lines['num_levels'] = int(lines['num_levels'])
    lines['exp_curve'] = float(lines['exp_curve'])
    lines['exp_magnitude'] = float(lines['exp_magnitude'])
    lines['exp_offset'] = int(lines['exp_offset'])
    lines['status_exp'] = int(lines['status_exp'])
    lines['heal_curve'] = float(lines['heal_curve'])
    lines['heal_magnitude'] = float(lines['heal_magnitude'])
    lines['kill_multiplier'] = float(lines['kill_multiplier'])
    lines['support_points'] = int(lines['support_points'])
    lines['line_of_sight'] = int(lines['line_of_sight'])
    lines['spell_line_of_sight'] = int(lines['spell_line_of_sight'])
    lines['aura_los'] = int(lines['aura_los'])
    lines['simultaneous_aoe'] = int(lines['simultaneous_aoe'])
    lines['def_double'] = int(lines['def_double'])
    lines['support'] = int(lines['support'])
    lines['casual'] = int(lines['casual'])
    lines['set_roll'] = int(lines['set_roll'])
    lines['num_skills'] = int(lines['num_skills'])
    lines['max_level'] = int(lines['max_level'])
    lines['max_stat'] = int(lines['max_stat'])

    return lines

def read_growths_file():
    # HP, STR, MAG, SKL, SPD, LCK, DEF, RES, CON, MOV
    lines = {'enemy_growths': '0,0,0,0,0,0,0,0,0,0',
             'player_growths': '0,0,0,0,0,0,0,0,0,0',
             'enemy_bases': '0,0,0,0,0,0,0,0,0,0',
             'player_bases': '0,0,0,0,0,0,0,0,0,0'}

    if os.path.isfile('Data/growths.txt'):
        with open('Data/growths.txt') as growths_file:
            for line in growths_file:
                split_line = line.strip().split(';')
                lines[split_line[0]] = split_line[1]

    lines['enemy_growths'] = [int(num) for num in lines['enemy_growths'].split(',')]
    lines['player_growths'] = [int(num) for num in lines['player_growths'].split(',')]
    lines['enemy_bases'] = [int(num) for num in lines['enemy_bases'].split(',')]
    lines['player_bases'] = [int(num) for num in lines['player_bases'].split(',')]

    return lines

def read_words_file():
    lines = {}
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
print('Debug: %s'%(OPTIONS['debug']))
CONSTANTS = read_constants_file()
CONSTANTS['Unit Speed'] = OPTIONS['Unit Speed']
GROWTHS = read_growths_file()
WORDS = read_words_file()