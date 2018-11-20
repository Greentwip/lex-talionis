# Saving and Loading Functions
# === IMPORT MODULES =============================================
import copy, threading, shutil
try:
    import cPickle as pickle
except ImportError:
    import pickle
from collections import OrderedDict

# Custom imports
try:
    import GlobalConstants as GC
    import configuration as cf
    import static_random
    import TileObject, ItemMethods, UnitObject, StatusObject, CustomObjects, Utility, Weapons
    from StatObject import Stat, build_stat_dict
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import static_random
    from . import TileObject, ItemMethods, UnitObject, StatusObject, CustomObjects, Utility, Weapons
    from Code.StatObject import Stat, build_stat_dict

import logging
logger = logging.getLogger(__name__)

# === READS LEVEL FILE (BITMAP MODE) ==============================================================================
def load_level(levelfolder, gameStateObj, metaDataObj):
    # Done at the beginning of a new level and ONLY then
    GC.U_ID = 100
    # Assorted Files
    unitfilename = levelfolder + '/UnitLevel.txt'

    unitFile = open(unitfilename, 'r')
    unitcontent = unitFile.readlines()
    unitFile.close()
        
    # For gameStateObj
    reinforceUnits, prefabs = {}, {}

    # Read overview file
    overview_filename = levelfolder + '/overview.txt'
    overview_dict = read_overview_file(overview_filename)
    # Get objective
    starting_objective = CustomObjects.Objective(overview_dict['display_name'], overview_dict['win_condition'], overview_dict['loss_condition'])

    # MetaDataObj holds unchanging information for the level
    # And general abstraction information    
    get_metaDataObj(levelfolder, metaDataObj)

    starting_music = CustomObjects.PhaseMusic(overview_dict['player_phase_music'], overview_dict['enemy_phase_music'], \
                                              overview_dict['other_phase_music'] if 'other_phase_music' in overview_dict else None)

    # Get tiles
    currentMap = create_map(levelfolder, overview_dict)
    gameStateObj.start_map(currentMap)

    # === Process unit data ===
    current_mode = [mode['name'] for mode in GC.DIFFICULTYDATA.values()]
    for line in unitcontent:
        # Process each line that was in the level file.
        line = line.strip()
        # Skip empty or comment lines
        if not line or line.startswith('#'):
            continue
        # Process line
        unitLine = line.split(';')
        current_mode = parse_unit_line(unitLine, current_mode, gameStateObj.allunits, gameStateObj.factions, 
                                       reinforceUnits, prefabs, gameStateObj.triggers, metaDataObj, gameStateObj)
    handle_triggers(gameStateObj.allunits, reinforceUnits, gameStateObj.triggers, gameStateObj.map)
    gameStateObj.start(allreinforcements=reinforceUnits, prefabs=prefabs, objective=starting_objective, music=starting_music)

def create_map(levelfolder, overview_dict=None):
    if not overview_dict:
        overview_filename = levelfolder + '/overview.txt'
        overview_dict = read_overview_file(overview_filename)
    tilefilename = levelfolder + '/TileData.png'
    mapfilename = levelfolder + '/MapSprite.png'
    weather = overview_dict['weather'].split(',') if 'weather' in overview_dict else []
    currentMap = TileObject.MapObject(mapfilename, tilefilename, levelfolder, weather)
    return currentMap

def get_metaDataObj(levelfolder, metaDataObj):
    overview_filename = levelfolder + '/overview.txt'
    prebaseScript_filename = levelfolder + '/prebaseScript.txt'
    narrationScript_filename = levelfolder + '/narrationScript.txt'
    introScript_filename = levelfolder + '/introScript.txt'
    outroScript_filename = levelfolder + '/outroScript.txt'
    death_quote_filename = 'Data/death_quote_info.txt'

    portrait_dict = create_portrait_dict()

    # Grab general catalogs
    class_dict = create_class_dict()
    lore_dict = create_lore_dict()

    overview_dict = read_overview_file(overview_filename)

    metaDataObj['name'] = overview_dict['name']
    metaDataObj['preparationFlag'] = bool(int(overview_dict['prep_flag']))
    metaDataObj['prep_music'] = overview_dict['prep_music'] if int(overview_dict['prep_flag']) else None
    metaDataObj['pickFlag'] = bool(int(overview_dict['pick_flag']))
    metaDataObj['baseFlag'] = overview_dict['base_flag'] if overview_dict['base_flag'] != '0' else False
    metaDataObj['base_music'] = overview_dict['base_music'] if overview_dict['base_flag'] != '0' else None
    metaDataObj['marketFlag'] = bool(int(overview_dict['market_flag']))
    metaDataObj['transitionFlag'] = bool(int(overview_dict['transition_flag']))
    metaDataObj['prebaseScript'] = prebaseScript_filename
    metaDataObj['narrationScript'] = narrationScript_filename
    metaDataObj['introScript'] = introScript_filename
    metaDataObj['outroScript'] = outroScript_filename
    metaDataObj['overview'] = overview_filename
    metaDataObj['death_quotes'] = death_quote_filename
    metaDataObj['class_dict'] = class_dict
    metaDataObj['portrait_dict'] = portrait_dict
    metaDataObj['lore'] = lore_dict

def read_overview_file(overview_filename):
    overview_lines = {}
    with open(overview_filename, 'r') as mainInfo:
        for line in mainInfo:
            split_line = line.rstrip('\r\n').split(";", 1)
            overview_lines[split_line[0]] = split_line[1]
    return overview_lines

# === TRIGGER STUFF ===
class Trigger(object):
    def __init__(self):
        self.units = {}

    def add_unit(self, unit_id, pos1, pos2):
        if ',' in pos1:
            pos1 = tuple(int(n) for n in pos1.split(','))
        if ',' in pos2:
            pos2 = tuple(int(n) for n in pos2.split(','))
        self.units[unit_id] = (pos1, pos2)

def get_trigger_unit(unitLine, allunits, reinforceUnits):
    if ',' in unitLine[2]:
        position = tuple(int(n) for n in unitLine[2].split(','))
        for unit in allunits:
            if unit.position == position:
                return unit.id
    else:
        for unit in allunits:
            if unit.id == unitLine[2]:
                return unit.id
        for event_id, (unit_id, position) in reinforceUnits.items():
            if event_id == unitLine[2] or unit_id == unitLine[2]:
                return unit_id
    return None

def handle_triggers(allunits, reinforceUnits, triggers, level_map):
    def determine_first_position(unit, trigger_list):
        queue = [t for t in trigger_list]
        current_pos = unit.position
        counter = 0
        while queue and counter < 10:
            start, end = queue.pop()
            if end == current_pos:  # Running up the chain
                current_pos = start
                counter = 0
            else:
                queue.insert(0, (start, end))
                counter += 1
        # print("Determining First Position")
        # print(unit.id, current_pos)
        if not current_pos:
            unit.position = None
            reinforceUnits[unit.id] = (unit.id, current_pos)
        elif current_pos not in level_map.tiles:
            unit.position = None
            if current_pos[0] >= level_map.width:
                spawn_pos = level_map.width - 1, current_pos[1]
            elif current_pos[1] >= level_map.height:
                spawn_pos = current_pos[0], level_map.height - 1
            elif current_pos[0] < 0:
                spawn_pos = 0, current_pos[1]
            elif current_pos[1] < 0:
                spawn_pos = current_pos[0], 0
            reinforceUnits[unit.id] = (unit.id, spawn_pos)
        else:
            unit.position = current_pos
        # print("Unit Position")
        # print(unit.position)
        # print(reinforceUnits.get(unit.id))

    # create a new object with unit id as main and triggers in dict
    # This organizas all triggers to be organized by unit instead of by trigger name
    unit_triggers = {}
    for trigger_name, trigger in triggers.items():
        for unit_id, (start, end) in trigger.units.items():
            if unit_id not in unit_triggers:
                unit_triggers[unit_id] = []
            unit_triggers[unit_id].append((start, end))

    # Now for each unit id in unit_triggers, set the position correctly
    for unit_id, trigger_list in unit_triggers.items():
        for unit in allunits:
            if unit_id == unit.id:
                determine_first_position(unit, trigger_list)
                break

def parse_unit_line(unitLine, current_mode, allunits, factions, reinforceUnits, prefabs, triggers, metaDataObj, gameStateObj):
    logger.info('Reading unit line %s', unitLine)
    # New Faction
    if unitLine[0] == 'faction':
        factions[unitLine[1]] = (unitLine[2], unitLine[3], unitLine[4])
    elif unitLine[0] == 'mode':
        current_mode = unitLine[1].split(',')
    elif unitLine[0] == 'load_player_characters':
        pass
    #     for unit in allunits:
    #         if unit.team == 'player' and not unit.dead:
    #             # Event ID is unit name
    #             reinforceUnits[unit.name] = (unit.id, None)
    elif unitLine[0] == 'trigger':
        trigger_name = unitLine[1]
        if trigger_name not in triggers:
            triggers[trigger_name] = Trigger()
        unit_id = get_trigger_unit(unitLine, allunits, reinforceUnits)
        if unit_id:
            triggers[trigger_name].add_unit(unit_id, unitLine[3], unitLine[4])
    elif gameStateObj.check_mode(current_mode):
        # New Unit
        if unitLine[1] == "0":
            if len(unitLine) > 7:
                create_unit(unitLine, allunits, factions, reinforceUnits, metaDataObj, gameStateObj)
            else:
                add_unit(unitLine, allunits, reinforceUnits, metaDataObj, gameStateObj)
        # Saved Unit
        elif unitLine[1] == "1":
            for unit in allunits:
                if unit.id == unitLine[3]: # Saved units use their id (which normally is name)
                    if unitLine[4] == 'None':
                        position = None
                    else:
                        position = tuple([int(num) for num in unitLine[4].split(',')])
                    if unitLine[2] == "0": # Unit starts on board
                        unit.position = position
                    else: # Unit does not start on board
                        reinforceUnits[unitLine[2]] = (unit.id, position)
                    break
        # Created Unit
        elif unitLine[1] == "2":
            event_id = unitLine[2]
            prefabs[event_id] = unitLine
    else:
        pass
        # Unit is not used in this mode
    return current_mode

def default_previous_classes(cur_class, classes, class_dict):
    while class_dict[cur_class]['tier'] > len(classes) and class_dict[cur_class]['promotes_from']:
        prev_class = class_dict[cur_class]['promotes_from']
        if prev_class not in classes:
            classes.insert(0, prev_class)
            cur_class = prev_class

def add_unit(unitLine, allunits, reinforceUnits, metaDataObj, gameStateObj):
    assert len(unitLine) == 6, "unitLine %s must have length 6"%(unitLine)
    legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
              'unit_id': unitLine[3], 'position': unitLine[4], 'ai': unitLine[5]}
    return add_unit_from_legend(legend, allunits, reinforceUnits, metaDataObj, gameStateObj)

def add_unit_from_legend(legend, allunits, reinforceUnits, metaDataObj, gameStateObj):
    class_dict = metaDataObj['class_dict']
    for unit in GC.UNITDATA.getroot().findall('unit'):
        if unit.find('id').text == legend['unit_id']:
            u_i = {}
            u_i['u_id'] = unit.find('id').text
            u_i['event_id'] = legend['event_id']
            u_i['position'] = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None
            u_i['name'] = unit.get('name')
            u_i['team'] = legend['team']

            classes = unit.find('class').text.split(',')
            u_i['klass'] = classes[-1]
            # Give default previous class
            default_previous_classes(u_i['klass'], classes, class_dict)
            u_i['gender'] = int(unit.find('gender').text)
            u_i['level'] = int(unit.find('level').text)

            stats = intify_comma_list(unit.find('bases').text)
            for n in range(len(stats), cf.CONSTANTS['num_stats']):
                stats.append(class_dict[u_i['klass']]['bases'][n])
            if u_i['team'] == 'player' or u_i['team'] == 'other': # Modify stats
                mode_bases = gameStateObj.mode['player_bases']
                mode_growths = gameStateObj.mode['player_growths']
            else:
                mode_bases = gameStateObj.mode['enemy_bases']
                mode_growths = gameStateObj.mode['enemy_growths']
            stats = [sum(x) for x in zip(stats, mode_bases)]
            assert len(stats) == cf.CONSTANTS['num_stats'], "bases %s must be exactly %s integers long" % (stats, cf.CONSTANTS['num_stats'])

            u_i['growths'] = intify_comma_list(unit.find('growths').text)
            u_i['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(u_i['growths'])))
            u_i['growths'] = [sum(x) for x in zip(u_i['growths'], mode_growths)]
            assert len(u_i['growths']) == cf.CONSTANTS['num_stats'], "growths %s must be exactly %s integers long" % (stats, cf.CONSTANTS['num_stats'])

            num_levelups = u_i['level'] - 1 + (cf.CONSTANTS['promoted_level'] if class_dict[u_i['klass']]['tier'] > 1 else 0)
            stats, u_i['growth_points'] = auto_level(stats, mode_growths, num_levelups, class_dict[u_i['klass']]['max'], gameStateObj.mode)

            u_i['stats'] = build_stat_dict(stats)
            logger.debug("%s's stats: %s", u_i['name'], u_i['stats'])

            if 'items' in legend:
                u_i['items'] = legend['items']
            else:
                u_i['items'] = ItemMethods.itemparser(unit.find('inventory').text)
            # Parse wexp
            u_i['wexp'] = unit.find('wexp').text.split(',')
            for index, wexp in enumerate(u_i['wexp'][:]):
                if wexp in Weapons.EXP.wexp_dict:
                    u_i['wexp'][index] = Weapons.EXP.wexp_dict[wexp]
            u_i['wexp'] = [int(num) for num in u_i['wexp']]

            assert len(u_i['wexp']) == len(Weapons.TRIANGLE.types), "%s's wexp must have as many slots as there are weapon types."%(u_i['name'])
            
            u_i['desc'] = unit.find('desc').text
            # Tags
            class_tags = class_dict[u_i['klass']]['tags']
            personal_tags = set(unit.find('tags').text.split(',')) if unit.find('tags') is not None and unit.find('tags').text is not None else set()
            u_i['tags'] = class_tags | personal_tags

            u_i['ai'] = legend['ai']
            u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']

            cur_unit = UnitObject.UnitObject(u_i)

            if u_i['event_id'] != "0": # unit does not start on board
                cur_unit.position = None
                reinforceUnits[u_i['event_id']] = (u_i['u_id'], u_i['position'])
            else: # Unit does start on board
                cur_unit.position = u_i['position']

            # Status Effects and Skills
            get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj, feat=False)
            # Personal Skills
            personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []
            c_s = [StatusObject.statusparser(status) for status in personal_skills]
            for status in c_s:  
                if status:
                    StatusObject.HandleStatusAddition(status, cur_unit, gameStateObj)
            # handle having a status that gives stats['HP']
            cur_unit.set_hp(int(cur_unit.stats['HP']))

            allunits.append(cur_unit)
            return cur_unit

def create_unit(unitLine, allunits, factions, reinforceUnits, metaDataObj, gameStateObj):
    assert len(unitLine) in (9, 10), "unitLine %s must have length 9 or 10 (if optional status)"%(unitLine)
    legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
              'class': unitLine[3], 'level': unitLine[4], 'items': unitLine[5], 
              'position': unitLine[6], 'ai': unitLine[7], 'faction': unitLine[8]}
    class_dict = metaDataObj['class_dict']

    u_i = {}

    GC.U_ID += 1
    u_i['u_id'] = GC.U_ID

    u_i['team'] = legend['team']
    u_i['event_id'] = legend['event_id']
    if legend['class'].endswith('F'):
        legend['class'] = legend['class'][:-1] # strip off the F
        u_i['gender'] = 5  # Default female gender is 5
    else:
        u_i['gender'] = 0  # Default male gender is 0
    classes = legend['class'].split(',')
    u_i['klass'] = classes[-1]
    # Give default previous class
    default_previous_classes(u_i['klass'], classes, class_dict)

    force_fixed = False
    if(legend['level'].startswith('f')):  # Force fixed level up
        legend['level'] = legend['level'][1:]
        force_fixed = True
    u_i['level'] = int(legend['level'])
    u_i['position'] = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None
    u_i['name'], u_i['faction_icon'], u_i['desc'] = factions[legend['faction']]

    stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'], u_i['level'] = \
        get_unit_info(class_dict, u_i['team'], u_i['klass'], u_i['level'], legend['items'],
                      gameStateObj.mode, gameStateObj.game_constants, force_fixed=force_fixed)
    u_i['stats'] = build_stat_dict(stats)
    logger.debug("%s's stats: %s", u_i['name'], u_i['stats'])
    
    u_i['tags'] = class_dict[u_i['klass']]['tags']
    u_i['ai'] = legend['ai']
    u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']

    cur_unit = UnitObject.UnitObject(u_i)

    # Reposition units
    if u_i['event_id'] != "0": # Unit does not start on board
        cur_unit.position = None
        reinforceUnits[u_i['event_id']] = (cur_unit.id, u_i['position'])
    else: # Unit does start on board
        cur_unit.position = u_i['position']

    # Status Effects and Skills
    get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj, feat=False)

    # Extra Skills
    if len(unitLine) == 10:
        statuses = [StatusObject.statusparser(status) for status in unitLine[9].split(',')]
        for status in statuses:
            StatusObject.HandleStatusAddition(status, cur_unit, gameStateObj)

    allunits.append(cur_unit)
    return cur_unit

def create_summon(summon_info, summoner, position, metaDataObj, gameStateObj):
    # Important Info
    class_dict = metaDataObj['class_dict']
    u_i = {}

    GC.U_ID += 1
    u_i['u_id'] = GC.U_ID

    classes = summon_info.klass.split(',')
    u_i['level'] = summoner.level
    u_i['position'] = position
    u_i['team'] = summoner.team
    u_i['event_id'] = 0
    u_i['gender'] = 0
    classes = classes[:class_dict[summoner.klass]['tier'] + 1]
    u_i['klass'] = classes[-1]
    u_i['faction_icon'] = summoner.faction_icon
    u_i['name'] = summon_info.name
    u_i['desc'] = summon_info.desc
    u_i['ai'] = summon_info.ai
    u_i['tags'] = set(class_dict[u_i['klass']]['tags'].split(',')) if class_dict[u_i['klass']]['tags'] else set()
    u_i['tags'].add('Summon_' + str(summon_info.s_id) + '_' + str(summoner.id)) # Add unique identifier
    u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']

    stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'], u_i['level'] = \
        get_unit_info(class_dict, u_i['team'], u_i['klass'], u_i['level'], summon_info.item_line, gameStateObj.mode, gameStateObj.game_constants)
    u_i['stats'] = build_stat_dict(stats)
    unit = UnitObject.UnitObject(u_i)

    # Status Effects and Skills
    my_seed = sum(u_i['position']) if u_i['position'] else 0
    get_skills(class_dict, unit, classes, u_i['level'], gameStateObj, seed=my_seed)

    return unit

def get_unit_info(class_dict, team, klass, level, item_line, mode, game_constants, force_fixed=False):
    # Handle stats
    # hp, str, mag, skl, spd, lck, def, res, con, mov
    bases = class_dict[klass]['bases'][:] # Using copies    
    growths = class_dict[klass]['growths'][:] # Using copies

    if team == 'player' or team == 'other': # Modify stats
        mode_bases = mode['player_bases']
        mode_growths = mode['player_growths']
        hidden_levels = int(eval(mode['autolevel_players']))
        explicit_levels = 0
    else:
        mode_bases = mode['enemy_bases']
        mode_growths = mode['enemy_growths']
        if 'extra_enemy_growths' in game_constants:
            mode_growths = [g + int(game_constants['extra_enemy_growths']) for g in mode_growths]
        hidden_levels = int(eval(mode['autolevel_enemies']))
        explicit_levels = int(eval(mode['truelevel_enemies']))

    level += explicit_levels

    bases = [sum(x) for x in zip(bases, mode_bases)]
    growths = [sum(x) for x in zip(growths, mode_growths)]

    num_levelups = level - 1 + (cf.CONSTANTS['promoted_level'] if class_dict[klass]['tier'] > 1 else 0)
    stats, growth_points = auto_level(bases, growths, num_levelups + hidden_levels, class_dict[klass]['max'], mode, force_fixed=force_fixed)

    # Handle items
    items = ItemMethods.itemparser(item_line)

    # Handle required wexp
    wexp = class_dict[klass]['wexp_gain'][:]
    # print(klass, wexp)
    for item in items:
        if item.weapon:
            weapon_type = item.TYPE
            item_level = item.weapon.LVL
        elif item.spell:
            weapon_type = item.TYPE
            item_level = item.spell.LVL
        else:
            continue
        if weapon_type:
            wexp_index = Weapons.TRIANGLE.name_to_index[weapon_type]
            item_requirement = Weapons.EXP.wexp_dict[item_level]
            # print(item, weapon_type, wexp_index, item_requirement, wexp[wexp_index])
            if item_requirement > wexp[wexp_index] and wexp[wexp_index] > 0:
                wexp[wexp_index] = item_requirement
    # print(wexp)

    return stats, growths, growth_points, items, wexp, level

def get_skills(class_dict, unit, classes, level, gameStateObj, feat=True, seed=0):
    class_skills = []
    for index, klass in enumerate(classes):
        for level_needed, class_skill in class_dict[klass]['skills']:
            # If level is gte level needed for skill or gte max_level
            if level >= level_needed or index < len(classes) - 1:
                class_skills.append(class_skill)
    # === Handle Feats (Naive choice)
    if feat:
        for status in class_skills:
            if status == 'Feat':
                counter = 0
                while StatusObject.feat_list[(seed + counter)%len(StatusObject.feat_list)] in class_skills:
                    counter += 1
                class_skills.append(StatusObject.feat_list[(seed + counter)%len(StatusObject.feat_list)])
    class_skills = [status for status in class_skills if status != 'Feat']
    logger.debug('Class Skills %s', class_skills)
    # === Actually add statuses
    status_effects = [StatusObject.statusparser(status) for status in class_skills]
    for status in status_effects:
        if status:
            StatusObject.HandleStatusAddition(status, unit, gameStateObj)
    # handle having a status that gives stats['HP']
    unit.set_hp(int(unit.stats['HP']))

def auto_level(bases, growths, num_levelups, max_stats, mode, force_fixed=False):
    stats = bases[:]
    growth_points = [50 for growth in growths]
    leveling = cf.CONSTANTS['enemy_leveling']

    if leveling == 3:
        leveling = int(mode['growths'])

    if leveling == 1 or force_fixed:  # Fixed
        for index, growth in enumerate(growths):
            growth_sum = growth * num_levelups
            stats[index] += (growth_sum + growth_points[index])//100
            growth_points[index] += growth_sum%100

    elif leveling == 0 or leveling == 3:  # Random
        for index, growth in enumerate(growths):
            for _ in range(num_levelups):
                growth_rate = growth
                while growth_rate > 0:
                    stats[index] += 1 if static_random.get_growth() < growth_rate else 0
                    growth_rate -= 100

    elif leveling == 2:  # Hybrid
        growths = [growth * num_levelups if stats[index] < max_stats[index] else 0 for index, growth in enumerate(growths)]
        growth_sum = sum(growths)
        num_choice = growth_sum//100
        growth_points[0] = growth_sum%100
        while num_choice > 0:
            num_choice -= 1
            if sum(growths) <= 0:
                break
            idx = static_random.weighted_choice(growths)
            stats[idx] += 1
            growths[idx] = max(0, growths[idx] - 100)
            if stats[idx] >= max_stats[idx]:
                num_choice -= growths[idx]//100
                growths[idx] = 0

    else:
        logger.error('Unsupported leveling type %s', leveling)

    # Make sure we don't exceed max
    stats = [Utility.clamp(stat, 0, max_stats[index]) for index, stat in enumerate(stats)]
            
    return stats, growth_points

"""
def place_mount(mount_id, chosen_unit, reinforceUnits):
    my_mount = None
    for u_id, (unit, position) in reinforceUnits.items():
        if mount_id == u_id:
            my_mount = unit
            break
    if my_mount:
        chosen_unit.mount(my_mount, None)
    logger.warning('Could not find mount!')
"""

def intify_comma_list(comma_string):
    # Takes string, turns it into list of ints
    if comma_string:
        s_l = comma_string.split(',')
        s_l = [int(num) for num in s_l]
    else:
        s_l = []
    return s_l

# === PARSES A SKILL LINE =====================================================
def class_skill_parser(skill_text):
    if skill_text is not None:
        each_skill = skill_text.split(';')
        split_line = [(int(skill.split(',')[0]), skill.split(',')[1]) for skill in each_skill]
        return split_line
    else:
        return []

# === CREATE CLASS DICTIONARY ================================================
def create_class_dict():
    class_dict = OrderedDict()
    # For each class
    for klass in GC.CLASSDATA.getroot().findall('class'):
        c_id = klass.get('id')
        class_dict[c_id] = {'short_name': klass.find('short_name').text,
                            'long_name': klass.find('long_name').text,
                            'id': c_id,
                            'tier': int(klass.find('tier').text),
                            'wexp_gain': intify_comma_list(klass.find('wexp_gain').text),
                            'promotes_from': klass.find('promotes_from').text if klass.find('promotes_from').text is not None else None,
                            'turns_into': klass.find('turns_into').text.split(',') if klass.find('turns_into').text is not None else [],
                            'movement_group': int(klass.find('movement_group').text),
                            'tags': set(klass.find('tags').text.split(',')) if klass.find('tags').text is not None else set(),
                            'skills': class_skill_parser(klass.find('skills').text),
                            'growths': intify_comma_list(klass.find('growths').text),
                            'bases': intify_comma_list(klass.find('bases').text),
                            'promotion': intify_comma_list(klass.find('promotion').text) if klass.find('promotion') is not None else [0]*10,
                            'max': intify_comma_list(klass.find('max').text) if klass.find('max') is not None else [60],
                            'desc': klass.find('desc').text,
                            'exp_multiplier': float(klass.find('exp_multiplier').text) if klass.find('exp_multiplier') is not None else 1.,
                            'exp_when_attacked': float(klass.find('exp_when_attacked').text) if klass.find('exp_when_attacked') is not None else 1.}
        class_dict[c_id]['bases'].extend([0] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['bases'])))
        class_dict[c_id]['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['growths'])))
        class_dict[c_id]['promotion'].extend([0] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['promotion'])))
        class_dict[c_id]['max'].extend([cf.CONSTANTS['max_stat']] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['max'])))
    return class_dict

# === CREATE LORE DICTIONARY =================================================
def create_lore_dict():
    lore_dict = {}
    # For each lore
    for entry in GC.LOREDATA.getroot().findall('lore'):
        lore_dict[entry.get('name')] = {'long_name': entry.find('long_name').text,
                                        'short_name': entry.get('name'),
                                        'desc': entry.find('desc').text,
                                        'type': entry.find('type').text,
                                        'unread': True}

    return lore_dict

# === CREATE PORTRAIT_DICTIONARY =============================================
def create_portrait_dict():
    portrait_dict = OrderedDict()
    for portrait in GC.PORTRAITDATA.getroot().findall('portrait'):
        portrait_dict[portrait.get('name')] = {'mouth': [int(coord) for coord in portrait.find('mouth').text.split(',')],
                                               'blink': [int(coord) for coord in portrait.find('blink').text.split(',')]}
    return portrait_dict

# Save IO
def save_io(to_save, to_save_meta, old_slot, slot=None, hard_loc=None):
    if hard_loc:
        save_loc = 'Saves/' + hard_loc + '.p'
        meta_loc = 'Saves/' + hard_loc + '.pmeta'
    else:
        save_loc = 'Saves/SaveState' + str(slot) + '.p'
        meta_loc = 'Saves/SaveState' + str(slot) + '.pmeta'
    
    logger.info('Saving to %s', save_loc)

    with open(save_loc, 'wb') as suspendFile:
        pickle.dump(to_save, suspendFile)
    with open(meta_loc, 'wb') as metaFile:
        pickle.dump(to_save_meta, metaFile)

    # For restart
    if not hard_loc: # Hard loc is used for suspend, which doesn't need a restart
        r_save = 'Saves/Restart' + str(slot) + '.p'
        r_save_meta = 'Saves/Restart' + str(slot) + '.pmeta'
        if old_slot == 'Start':
            if save_loc != r_save:
                shutil.copy(save_loc, r_save)
                shutil.copy(meta_loc, r_save_meta)
        else:
            old_name = 'Saves/Restart' + str(old_slot) + '.p'
            if old_name != r_save:
                shutil.copy(old_name, r_save)
                shutil.copy(old_name + 'meta', r_save_meta)

    """
    # Take the temporary file we just created and make it an actual file
    # This is so if the saving fails, we do not lose the old savedata
    if os.path.isfile(save_loc):
        os.remove(save_loc)
    os.rename(save_loc + 'tmp', save_loc) # Put it in permanently
    """

# === SAVE FUNCTION ==========================================================
def suspendGame(gameStateObj, kind, slot=None, hard_loc=None):
    old_slot = gameStateObj.save_slot
    if kind == 'Start':
        gameStateObj.sweep() # This cleans_up, since we're done with level.
        old_slot = 'Start'
        gameStateObj.save_slot = slot

    # gameStateObj.removeSprites()
    to_save, to_save_meta = gameStateObj.save()
    to_save_meta['kind'] = kind
    to_save_meta['name'] = read_overview_file('Data/Level' + str(gameStateObj.game_constants['level']) + '/overview.txt')['name']

    gameStateObj.saving_thread = threading.Thread(target=save_io, args=(copy.deepcopy(to_save), copy.deepcopy(to_save_meta), old_slot, slot, hard_loc))
    gameStateObj.saving_thread.start()

    # gameStateObj.loadSprites()

# === LOAD FUNCTION ===========================================================
"""returns gameStateObj from a suspend"""
def loadGame(gameStateObj, metaDataObj, saveSlot):
    to_save = saveSlot.loadGame()
    # Rebuild gameStateObj
    gameStateObj.load(to_save)
    gameStateObj.save_slot = saveSlot.number

    levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
    get_metaDataObj(levelfolder, metaDataObj) 

    gameStateObj.loadSprites()

    if any(isinstance(unit.id, int) for unit in gameStateObj.allunits):
        GC.U_ID = max(unit.id for unit in gameStateObj.allunits if isinstance(unit.id, int))
    else:
        GC.U_ID = 100
