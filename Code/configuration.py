#! usr/bin/env python2.7
from collections import OrderedDict
import os
def read_config_file():
    lines = OrderedDict([('debug', 1),
                         ('cheat', 1),
                         ('random_seed', -1),
                         ('Screen Size', 2),
                         ('Sound Buffer Size', 4),
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

    def parse_config(fn):
        with open(fn) as config_file:
            for line in config_file:
                split_line = line.strip().split('=')
                lines[split_line[0]] = split_line[1]

    # Try saves folder first
    try:
        parse_config('Saves/config.ini')
    except:
        if os.path.exists('Data/config.ini'):
            parse_config('Data/config.ini')

    lines['debug'] = int(lines['debug'])
    lines['cheat'] = int(lines['cheat'])
    lines['random_seed'] = int(lines['random_seed'])
    lines['Screen Size'] = int(lines['Screen Size'])
    lines['Sound Buffer Size'] = int(lines['Sound Buffer Size'])
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
             'crit': 3, # 0 - No critting, 1 - 2x damage minus 1x defense, 2 - 2x damage minus 2x defense, 3 - 3x damage minus 3x defense
             'turnwheel': 0, # Whether to use the turnwheel
             'overworld': 0, # Whether to have an overworld
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
             'line_of_sight': 1, # Whether to use line of sight algorithm when choosing targets for weapons
             'spell_line_of_sight': 0, # Whether to use line of sight algorithm when choosing targets for spells
             'aura_los': 1, # Whether to use line of sight algorithm for auras
             'simultaneous_aoe': 1, # Whether AOE attacks on many targets are resolved simultaneously or in order
             'def_double': 1, # Whether units on defense can double their attackers
             'enemy_leveling': 1, # How to level up non-player units
             'num_skills': 5, # How many class_skills a fully ranked unit should have (not actually a hard limit, just for drawing)
             'max_stat': 20, # Maximum value that a non-HP stat can be. Irrespective of class caps. 
             'num_stats': 10, # Number of stats that a unit has (Includes HP, CON, and MOV)
             'max_level': '10,20,20', # Maximum Level for class by tier ('10, 20, 20,')
             'promoted_level': 19, # Add this to a promoted units level to determine how many levels they've had
             'auto_promote': 0, # Promote after max-level?
             'minimum_damage': 0, # Minimum amount of damage that can be dealt (switch to 1 to make it like FE2 or FE15)
             'boss_crit': 0, # Whether the lethal hit on a boss shows a crit
             'steal_exp': 0, # Amount of exp gained from stealing
             'unarmed_punish': 0, # How much weapon disadvantage an unarmed unit gets
             'convoy_on_death': 0, # Should dead units give all of their items to the convoy at the end of each level?
             'fatal_wexp': 1, # Should units get double weapon experience on lethal hits
             'double_wexp': 1, # Give wexp for every hit (so if you double, you get 2x wexp)
             'miss_wexp': 1, # Give wexp even if you do no damage or miss
             'steal': 0, # 0 - Normal GBA Steal, 1 - Can steal everything but equipped weapons
             'save_slots': 3,
             'music_main': '',
             'music_game_over': '',
             'music_armory': '',
             'music_vendor': '',
             'music_promotion': '',
             'attribution': 'created by rainlash',
             'title': 'Lex Talionis Engine',
             'support': 1, # 0 - No supports, 1 - Conversations in combat, Conversations in base
             'support_bonus': 4, # 0 - No bonus, 1 - Use own affinity, 2 - Use other affinity, 3 - Use average of affinites, 4 - Use sum of affinities
             'support_range': 3, # 0 - Entire map
             'support_growth_range': 1, # 0 - Entire map
             'support_end_chapter': 0, # Points gained for ending a chapter with both alive
             'support_end_turn': 1, # Points gained for ending turn in range
             'support_combat': 0, # Points gained for combat in range
             'support_interact': 0, # Points for interacting
             'support_limit': 5, # Limit to number of support level: 0 - No limit
             'support_s_limit': 1, # Limit to number of s support levels (>4): 0 - No limit
             'arena_global_limit': 0, # Limit to number of times can use an arena in a level: 0 - No limit
             'arena_unit_limit': 0, # Limit to number of times each unit can use an arena in a level: 0 - No limit
             'arena_death': 1, # Units defeated in the arena are killed. Set to 0 to leave them with 1 HP
             'arena_weapons': 1, # Units will be provided with basic weapons in the arena. Set to 0 to have to bring your own
             'arena_basic_weapons': 'Iron Sword,Iron Lance,Iron Axe,Willow Bow,Fire,Glimmer,Flux',
             'arena_wager_min': 500,
             'arena_wager_max': 900,
             }

    if os.path.isfile('Data/constants.ini'):
        with open('Data/constants.ini') as constants_file:
            for line in constants_file:
                if not line.startswith(';'):
                    split_line = line.strip().split('=')
                    lines[split_line[0]] = split_line[1]

    float_lines = {'exp_curve', 'exp_magnitude', 'heal_curve', 'heal_magnitude', 
                   'heal_min', 'boss_bonus', 'kill_multiplier'}
    string_lines = {'title', 'music_main', 'music_game_over', 'music_armory',
                    'music_vendor', 'music_promotion', 'attribution'}
    int_list_lines = {'max_level'}
    string_list_lines = {'arena_basic_weapons'}
    for k, v in lines.items():
        if k in float_lines:
            lines[k] = float(v)
        elif k in string_lines:
            lines[k] = v
        elif k in int_list_lines:
            lines[k] = [int(n) for n in v.split(',')]
        elif k in string_list_lines:
            lines[k] = v.split(',')
        else:
            lines[k] = int(v)

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
                if len(split_line) == 2:
                    lines[split_line[0]] = split_line[1]
                else:
                    print('ERROR! unparseable words.txt line: %s' % line)
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
text_speed_options = list(reversed([0, 1, 5, 10, 15, 20, 32, 50, 80, 112, 150]))
