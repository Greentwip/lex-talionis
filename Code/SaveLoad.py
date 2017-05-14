# Saving and Loading Functions
# === IMPORT MODULES =============================================
import os, random, copy, threading, shutil
import cPickle as pickle
from collections import OrderedDict

# Custom imports
from imagesDict import getImages
from GlobalConstants import *
from configuration import *
import TileObject, ItemMethods, UnitObject, StatusObject, GameStateObj, CustomObjects, Utility
from UnitObject import Stat

import logging # logging needs to be the last import that is done
logger = logging.getLogger(__name__)

# === READS LEVEL FILE (BITMAP MODE) ==============================================================================
def load_level(levelfolder, gameStateObj, metaDataObj):
    # Done at the beginning of a new level and ONLY then
    U_ID = 100
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

    # MetaDataObj holds unhanging information for the level
    # And general abstraction information    
    get_metaDataObj(levelfolder, metaDataObj)

    # Get tiles
    currentMap = create_map(levelfolder, overview_dict)
    gameStateObj.start_map(currentMap)

    # === Process unit data ===
    for line in unitcontent:
        # Process each line that was in the level file.
        line = line.strip()
        # Skip empty or comment lines
        if not line or line.startswith('#'):
            continue
        # Process line
        unitLine = line.split(';')
        parse_unit_line(unitLine, gameStateObj.allunits, gameStateObj.groups, reinforceUnits, prefabs, metaDataObj, gameStateObj)
    
    gameStateObj.start(allreinforcements=reinforceUnits, prefabs=prefabs, objective=starting_objective)

def create_map(levelfolder,overview_dict=None):
    if not overview_dict:
        overview_filename = levelfolder + '/overview.txt'
        overview_dict = read_overview_file(overview_filename)
    tilefilename = levelfolder + '/TileData.png'
    mapfilename = levelfolder + '/MapSprite.png'
    weather = overview_dict['weather'].split(',') if 'weather' in overview_dict else []
    currentMap = TileObject.MapObject(mapfilename, tilefilename, levelfolder, weather)
    return currentMap

def get_metaDataObj(levelfolder, metaDataObj, changes=[]):
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
    metaDataObj['playerPhaseMusic'] = MUSICDICT[overview_dict['player_phase_music']]
    metaDataObj['enemyPhaseMusic'] = MUSICDICT[overview_dict['enemy_phase_music']]
    metaDataObj['otherPhaseMusic'] = MUSICDICT[overview_dict['other_phase_music']] if 'other_phase_music' in overview_dict else None
    metaDataObj['prebaseScript'] = prebaseScript_filename
    metaDataObj['narrationScript'] = narrationScript_filename
    metaDataObj['introScript'] = introScript_filename
    metaDataObj['outroScript'] = outroScript_filename
    metaDataObj['overview'] = overview_filename
    metaDataObj['death_quotes'] = death_quote_filename
    metaDataObj['class_dict'] = class_dict
    metaDataObj['portrait_dict'] = portrait_dict
    metaDataObj['lore'] = lore_dict

    for line in changes:
        print(line)
        if line[1].endswith('Music'):
            line[2] = MUSICDICT[line[2]]
        metaDataObj[line[1]] = line[2]

def read_overview_file(overview_filename):
    overview_lines = {}
    with open(overview_filename, 'r') as mainInfo:
        for line in mainInfo:
            split_line = line.rstrip('\r\n').split(";", 1)
            overview_lines[split_line[0]] = split_line[1]
    return overview_lines

def parse_unit_line(unitLine, allunits, groups, reinforceUnits, prefabs, metaDataObj, gameStateObj):
    logger.info('Reading unit line %s', unitLine)
    # New Group
    if unitLine[0] == 'group':
        groups[unitLine[1]] = (unitLine[2], unitLine[3], unitLine[4])
    # New Unit
    elif unitLine[1] == "0":
        if len(unitLine) > 7:
            create_unit(unitLine, allunits, groups, reinforceUnits, metaDataObj, gameStateObj)
        else:
            add_unit(unitLine, allunits, reinforceUnits, metaDataObj, gameStateObj)
    elif unitLine[1] == "1":
        for unit in allunits:
            if unit.name == unitLine[3]: # Saved units use their name...\
                if unitLine[4] == 'None':
                    position = None
                else:
                    position = tuple([int(num) for num in unitLine[4].split(',')])
                if unitLine[2] == "0": # Unit starts on board
                    unit.position = position
                else: # Unit does not start on board
                    reinforceUnits[unitLine[2]] = (unit.id, position)
    elif unitLine[1] == "2":
        event_id = unitLine[2]
        prefabs[unitLine[2]] = unitLine

def add_unit(unitLine, allunits, reinforceUnits, metaDataObj, gameStateObj):
    assert len(unitLine) == 6 or len(unitLine) == 7, "unitLine %s must have length 6 or 7"%(unitLine)
    class_dict = metaDataObj['class_dict']
    for unit in UNITDATA.getroot().findall('unit'):
        if unit.find('id').text == unitLine[3]:
            u_i = {}
            u_i['u_id'] = unit.find('id').text
            u_i['event_id'] = unitLine[2]
            u_i['position'] = tuple([int(num) for num in unitLine[4].split(',')]) if ',' in unitLine[4] else None
            u_i['name'] = unit.get('name')
            u_i['team'] = unitLine[0]

            classes = unit.find('class').text.split(',')
            u_i['klass'] = classes[-1]
            # Give default previous class
            if class_dict[u_i['klass']]['tier'] > len(classes) and class_dict[u_i['klass']]['promotes_from']:
                prev_class = class_dict[u_i['klass']]['promotes_from'][0]
                if prev_class not in classes:
                    classes.insert(0, prev_class)
            u_i['gender'] = unit.find('gender').text
            u_i['level'] = int(unit.find('level').text)
            u_i['faction'] = unit.find('faction').text

            stats = intify_comma_list(unit.find('bases').text)
            if u_i['team'] == 'player': # Modify stats
                stats = [sum(x) for x in zip(stats, GROWTHS['player_bases'])]
            else:
                stats = [sum(x) for x in zip(stats, GROWTHS['enemy_bases'])]
            if len(stats) == 8: # Add con if not present
                stats.append(int(class_dict[u_i['klass']]['bases'][8]))
            assert len(stats) == 9, "bases %s must be exactly 9 integers long"%(stats)
            stats.append(int(class_dict[u_i['klass']]['movement']))
            u_i['stats'] = build_stat_dict(stats)
            logger.debug("%s's stats: %s", u_i['name'], u_i['stats'])
            u_i['growths'] = intify_comma_list(unit.find('growths').text)
            u_i['growth_points'] = [50, 50, 50, 50, 50, 50, 50, 50]

            u_i['items'] = ItemMethods.itemparser(unit.find('inventory').text)
            # Parse wexp
            u_i['wexp'] = unit.find('wexp').text.split(',')
            for index, wexp in enumerate(u_i['wexp'][:]):
                if wexp in CustomObjects.WEAPON_EXP.wexp_dict:
                    u_i['wexp'][index] = CustomObjects.WEAPON_EXP.wexp_dict[wexp]
            u_i['wexp'] = [int(_) for _ in u_i['wexp']]

            assert len(u_i['wexp']) == len(CustomObjects.WEAPON_TRIANGLE.types), "%s's wexp must have as many slots as there are weapon types."%(u_i['name'])
            
            u_i['desc'] = unit.find('desc').text
            # Tags
            class_tags = class_dict[u_i['klass']]['tags'].split(',') if class_dict[u_i['klass']]['tags'] else []
            personal_tags = unit.find('tags').text.split(',') if unit.find('tags') is not None and unit.find('tags').text is not None else []
            u_i['tags'] = class_tags + personal_tags

            u_i['ai'] = unitLine[5]
            u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']

            cur_unit = UnitObject.UnitObject(u_i)

            # Status Effects and Skills
            get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj, feat=False)
            # Personal Skills
            personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []    ### Actually add statuses
            c_s = [StatusObject.statusparser(status) for status in personal_skills]
            for status in c_s:  
                if status:
                    StatusObject.HandleStatusAddition(status, cur_unit, gameStateObj)
            # handle having a status that gives stats['HP']
            cur_unit.currenthp = int(cur_unit.stats['HP'])
            cur_unit.position = u_i['position'] # Reposition units

            if u_i['event_id'] != "0": # unit does not start on board
                cur_unit.position = None
                reinforceUnits[u_i['event_id']] = (u_i['u_id'], u_i['position'])

            allunits.append(cur_unit)
    return allunits, reinforceUnits

def create_unit(unitLine, allunits, groups, reinforceUnits, metaDataObj, gameStateObj):
    assert len(unitLine) in [9, 10], "unitLine %s must have length 9 or 10 (if optional status)"%(unitLine)
    class_dict = metaDataObj['class_dict']

    u_i = {}

    global U_ID
    U_ID += 1
    u_i['u_id'] = U_ID

    u_i['team'] = unitLine[0]
    u_i['event_id'] = unitLine[2]
    if unitLine[3].endswith('F'):
        unitLine[3] = unitLine[3][:-1] # strip off the F
        u_i['gender'] = 'F'
    else:
        u_i['gender'] = 'M'
    classes = unitLine[3].split(',')
    u_i['klass'] = classes[-1]
    # Give default previous class
    if class_dict[u_i['klass']]['tier'] > len(classes) and class_dict[u_i['klass']]['promotes_from']:
        prev_class = class_dict[u_i['klass']]['promotes_from'][0]
        if prev_class not in classes:
            classes.insert(0, prev_class)

    u_i['level'] = int(unitLine[4])
    u_i['position'] = tuple([int(num) for num in unitLine[6].split(',')])
    u_i['name'], u_i['faction'], u_i['desc'] = groups[unitLine[8]]

    stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = get_unit_info(class_dict, u_i['klass'], u_i['level'], unitLine[5])
    u_i['stats'] = build_stat_dict(stats)
    logger.debug("%s's stats: %s", u_i['name'], u_i['stats'])
    
    u_i['tags'] = class_dict[u_i['klass']]['tags'].split(',') if class_dict[u_i['klass']]['tags'] else []
    u_i['ai'] = unitLine[7]
    u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']

    cur_unit = UnitObject.UnitObject(u_i)

    # Reposition units
    cur_unit.position = u_i['position']

    # Status Effects and Skills
    get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj)

    if u_i['event_id'] != "0": # Unit does not start on board
        cur_unit.position = None
        reinforceUnits[u_i['event_id']] = (cur_unit.id, u_i['position'])

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

    global U_ID
    U_ID += 1
    u_i['u_id'] = U_ID

    classes = summon_info.klass.split(',')
    u_i['level'] = summoner.level
    u_i['position'] = position
    u_i['team'] = summoner.team
    u_i['event_id'] = 0
    u_i['gender'] = 'M'
    classes = classes[:summoner.level/CONSTANTS['max_level']+1]
    u_i['klass'] = classes[-1]
    u_i['faction'] = summoner.faction
    u_i['name'] = summon_info.name
    u_i['desc'] = summon_info.desc
    u_i['ai'] = summon_info.ai
    u_i['tags'] = class_dict[u_i['klass']]['tags'].split(',') if class_dict[u_i['klass']]['tags'] else []
    u_i['tags'].append('Summon_' + str(summon_info.s_id) + '_' + str(summoner.id)) # Add unique identifier
    u_i['movement_group'] = class_dict[u_i['klass']]['movement_group']

    stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = get_unit_info(class_dict, u_i['klass'], u_i['level'], summon_info.item_line)
    u_i['stats'] = build_stat_dict(stats)
    unit = UnitObject.UnitObject(u_i)

    # Status Effects and Skills
    get_skills(class_dict, unit, classes, u_i['level'], gameStateObj)

    return unit

def build_stat_dict(stats):
    st = OrderedDict()
    st['HP'] = Stat(stats[0])
    st['STR'] = Stat(stats[1])
    st['MAG'] = Stat(stats[2])
    st['SKL'] = Stat(stats[3])
    st['SPD'] = Stat(stats[4])
    st['LCK'] = Stat(stats[5])
    st['DEF'] = Stat(stats[6])
    st['RES'] = Stat(stats[7])
    st['CON'] = Stat(stats[8])
    st['MOV'] = Stat(stats[9])
    return st

def build_stat_dict_plus(stats):
    st = OrderedDict()
    st['HP'] = Stat(stats[0][0], stats[0][1])
    st['STR'] = Stat(stats[1][0], stats[1][1])
    st['MAG'] = Stat(stats[2][0], stats[2][1])
    st['SKL'] = Stat(stats[3][0], stats[3][1])
    st['SPD'] = Stat(stats[4][0], stats[4][1])
    st['LCK'] = Stat(stats[5][0], stats[5][1])
    st['DEF'] = Stat(stats[6][0], stats[6][1])
    st['RES'] = Stat(stats[7][0], stats[7][1])
    st['CON'] = Stat(stats[8][0], stats[8][1])
    st['MOV'] = Stat(stats[9][0], stats[9][1])
    return st

def get_unit_info(class_dict, klass, level, item_line):
    # Handle stats
    movement = class_dict[klass]['movement']
    # hp, str, mag, skl, spd, lck, def, res, con
    growths = class_dict[klass]['growths'][:] # Using copies
    bases = class_dict[klass]['bases'][:] # Using copies
    stats, growth_points = auto_level(bases, growths, level, class_dict[klass]['max'])
    # Make sure we don't exceed max
    stats = [Utility.clamp(stat, 0, class_dict[klass]['max'][index]) for index, stat in enumerate(stats)]
    stats.append(movement)

    # Handle items
    items = ItemMethods.itemparser(item_line)

    # Handle required wexp
    wexp = class_dict[klass]['wexp_gain'][:]
    #print(klass, wexp)
    for item in items:
        if item.weapon:
            weapon_types = item.TYPE
            item_level = item.weapon.LVL
        elif item.spell:
            weapon_types = item.TYPE
            item_level = item.spell.LVL
        else:
            continue
        for weapon_type in weapon_types:
            wexp_index = CustomObjects.WEAPON_TRIANGLE.type_to_index[weapon_type]
            item_requirement = CustomObjects.WEAPON_EXP.wexp_dict[item_level]
            #print(item, weapon_type, wexp_index, item_requirement, wexp[wexp_index])
            if item_requirement > wexp[wexp_index] and wexp[wexp_index] > 0:
                wexp[wexp_index] = item_requirement
    #print(wexp)

    return stats, growths, growth_points, items, wexp

def get_skills(class_dict, unit, classes, level, gameStateObj, feat=True):
    position = unit.position
    class_skills = []
    for index, klass in enumerate(classes):
        for level_needed, class_skill in class_dict[klass]['skills']:
            if index < len(classes) - 1 or level%CONSTANTS['max_level'] >= level_needed or level%CONSTANTS['max_level'] == 0:
                class_skills.append(class_skill)
    ### Handle Feats (Naive choice)
    if feat:
        for status in class_skills:
            if status == 'Feat':
                counter = 0
                while StatusObject.feat_list[(position[0] + position[1] + counter)%10] in class_skills:
                    counter += 1
                class_skills.append(StatusObject.feat_list[(position[0] + position[1] + counter)%10])
    class_skills = [status for status in class_skills if status != 'Feat']
    logger.debug('Class Skills %s', class_skills)
    ### Actually add statuses
    status_effects = [StatusObject.statusparser(status) for status in class_skills]
    for status in status_effects:
        if status:
            StatusObject.HandleStatusAddition(status, unit, gameStateObj)
    # handle having a status that gives stats['HP']
    unit.currenthp = int(unit.stats['HP'])

def auto_level(bases, growths, level, max_stats):
    stats = [sum(x) for x in zip(bases, GROWTHS['enemy_bases'])]
    growths = [sum(x) for x in zip(growths, GROWTHS['enemy_growths'])]
    growth_points = [0 for growth in growths]

    if CONSTANTS['leveling'] == 'fixed':
        for index, growth in enumerate(growths):
            growth_sum = growth * (level - 1)
            stats[index] += growth_sum/100
            growth_points[index] += growth_sum%100

    elif CONSTANTS['leveling'] == 'random': # Random
        for index, growth in enumerate(growths):
            for _ in range(level - 1):
                growth_rate = growth
                while growth_rate > 0:
                    stats[index] += 1 if random.randint(0, 99) < growth_rate else 0
                    growth_rate -= 100

    elif CONSTANTS['leveling'] == 'hybrid': # Like Radiant Dawn Bonus Exp Method
        growths = [growth * (level - 1) if stats[index] < max_stats[index] else 0 for index, growth in enumerate(growths)]
        growth_sum = sum(growths)
        num_choice = growth_sum/100
        growth_points[0] = growth_sum%100
        while num_choice > 0:
            num_choice -= 1
            idx = Utility.weighted_choice(growths)
            stats[idx] += 1
            growths[idx] = max(0, growths[idx] - 100)
            if stats[idx] >= max_stats[idx]:
                num_choice -= growths[idx]/100
                growths[idx] = 0
            
    return stats, growth_points

"""
def place_mount(mount_id, chosen_unit, reinforceUnits):
    my_mount = None
    for u_id, (unit, position) in reinforceUnits.iteritems():
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
    class_dict = {}
    # For each class
    for klass in CLASSDATA.getroot().findall('class'):
        class_dict[klass.get('name')] = {'id': klass.find('id').text,
                                         'tier': klass.find('tier').text,
                                         'wexp_gain': intify_comma_list(klass.find('wexp_gain').text),
                                         'promotes_from': klass.find('promotes_from').text.split(',') if klass.find('promotes_from').text is not None else [],
                                         'turns_into': klass.find('turns_into').text.split(',') if klass.find('turns_into').text is not None else [],
                                         'movement': int(klass.find('movement').text),
                                         'movement_group': int(klass.find('movement_group').text),
                                         'tags': klass.find('tags').text,
                                         'skills': class_skill_parser(klass.find('skills').text),
                                         'growths': intify_comma_list(klass.find('growths').text),
                                         'bases': intify_comma_list(klass.find('bases').text),
                                         'promotion': intify_comma_list(klass.find('promotion').text) if klass.find('promotion') is not None else [0,0,0,0,0,0,0,0],
                                         'max': intify_comma_list(klass.find('max').text) if klass.find('max') is not None else [60, 20, 20, 20, 20, 20, 20, 20],
                                         'desc': klass.find('desc').text}

    return class_dict

# === CREATE LORE DICTIONARY =================================================
def create_lore_dict():
    lore_dict = {}
    # For each lore
    for entry in LOREDATA.getroot().findall('lore'):
        lore_dict[entry.get('name')] = {'long_name': entry.find('long_name').text,
                                        'short_name': entry.get('name'),
                                        'desc': entry.find('desc').text,
                                        'type': entry.find('type').text,
                                        'unread': True}

    return lore_dict

# === CREATE PORTRAIT_DICTIONARY =============================================
def create_portrait_dict():
    portrait_dict = {}
    for portrait in PORTRAITDATA.getroot().findall('portrait'):
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
    
    logging.info('Saving to %s', save_loc)

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
            if 'Saves/Restart' + str(old_slot) + '.p' != r_save:
                shutil.copy('Saves/Restart' + str(old_slot) + '.p', r_save)
                shutil.copy('Saves/Restart' + str(old_slot) + '.pmeta', r_save_meta)

    """
    # Take the temporary file we just created and make it an actual file
    # This is so if the saving fails, we do not lose the old savedata
    if os.path.isfile(save_loc):
        os.remove(save_loc)
    os.rename(save_loc + 'tmp', save_loc) # Put it in permanently
    """

# === SAVE FUNCTION ==========================================================
def suspendGame(gameStateObj, kind, slot = None, hard_loc = None):
    old_slot = gameStateObj.save_slot
    if kind == 'Start':
        gameStateObj.sweep() # This cleans_up, since we're done with level.
        old_slot = 'Start'
        gameStateObj.save_slot = slot

    #gameStateObj.removeSprites()
    to_save, to_save_meta = gameStateObj.save()
    to_save_meta['kind'] = kind
    to_save_meta['name'] = read_overview_file('Data/Level' + str(gameStateObj.counters['level']) + '/overview.txt')['name']

    gameStateObj.saving_thread = threading.Thread(target=save_io, args=(copy.deepcopy(to_save), copy.deepcopy(to_save_meta), old_slot, slot, hard_loc))
    gameStateObj.saving_thread.start()

    #gameStateObj.loadSprites()

# === LOAD FUNCTION ===========================================================
"""returns gameStateObj from a suspend"""
def loadGame(gameStateObj, metaDataObj, saveSlot):
    to_save = saveSlot.loadGame()
    # Rebuild gameStateObj
    gameStateObj.load(to_save)
    gameStateObj.save_slot = saveSlot.number

    levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
    get_metaDataObj(levelfolder, metaDataObj, gameStateObj.metaDataObj_changes) 

    gameStateObj.loadSprites()

    # Get the U_ID
    global U_ID
    if any(isinstance(unit.id, int) for unit in gameStateObj.allunits):
        U_ID = max(unit.id for unit in gameStateObj.allunits if isinstance(unit.id, int))
    else:
        U_ID = 100