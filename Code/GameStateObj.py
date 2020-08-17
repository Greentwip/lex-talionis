#! usr/bin/env python
import random
from collections import OrderedDict, Counter

# Custom imports
from . import GlobalConstants as GC
from . import configuration as cf
from . import static_random
from . import InputManager, Engine
from . import CustomObjects, StateMachine, AStar, Support, Dialogue, Cursor
from . import StatusCatalog, UnitObject, SaveLoad, ItemMethods, Turnwheel
from . import Boundary, Objective, Overworld, TileObject, Action
from . import Highlight, Aura

import logging
logger = logging.getLogger(__name__)

class GameStateObj(object):
    # needed for main menu
    def __init__(self):
        self.game_constants = Counter()
        self.game_constants['level'] = 0
        # Set up blitting surfaces
        self.generic_surf = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT))
        # Set up input handling
        self.input_manager = InputManager.InputManager()
        # Build starting stateMachine
        self.stateMachine = StateMachine.StateMachine(['start_start'], [])
        # Menu slots
        self.activeMenu = None
        self.childMenu = None
        self.background = None
        self.shared_state_data = {}
        # Surface holder
        self.info_surf = None
        # playtime
        self.playtime = 0
        # mode
        self.mode = self.default_mode()
        # Messages
        # self.message = []

    # Things that change between levels always
    def start(self, allreinforcements, prefabs, objective, music):
        logger.info("Start")
        self.allreinforcements = allreinforcements
        self.prefabs = prefabs
        self.objective = objective
        self.phase_music = music
        self.turncount = 0

        for unit in self.allunits:
            if unit.position:
                Action.ArriveOnMap(unit, unit.position).do(self)

        self.generic()

    def start_map(self, tilemap):
        self.map = tilemap
        self.build_map_surf()
        self.build_grid()

    def build_map_surf(self):
        mapSurfWidth = max(self.map.width * GC.TILEWIDTH, GC.WINWIDTH)
        mapSurfHeight = max(self.map.height * GC.TILEHEIGHT, GC.WINHEIGHT)
        self.mapSurf = Engine.create_surface((mapSurfWidth, mapSurfHeight))

    def build_grid(self):
        self.grid_manager = AStar.Grid_Manager(self.map)
        self.boundary_manager = Boundary.BoundaryInterface(self.map)

    def load_submap(self, name):
        if not self.old_map:
            self.old_map = self.map
            units = [unit for unit in self.allunits if unit.position]
            self.leave_actions = [Action.LeaveMap(unit) for unit in units]
            for action in self.leave_actions:
                action.do(self)
        tilefilename = 'Data/Level' + name + '/TileData.png'
        mapfilename = 'Data/Level' + name + '/MapSprite.png'
        levelfolder = 'Data/Level' + name
        submap = TileObject.MapObject(self, mapfilename, tilefilename, levelfolder, self.map.weather)
        self.start_map(submap)

    def close_submap(self):
        print(self.old_map)
        if not self.old_map:
            return
        print("closing submap!")
        self.start_map(self.old_map)
        for action in self.leave_actions:
            action.reverse(self)
        self.leave_actions = None
        self.old_map = None

    def get_convoy(self, party=None):
        if party is None:
            party = self.current_party
        if party not in self._convoy:
            self._convoy[party] = []
        return self._convoy[party]

    convoy = property(get_convoy)

    def get_money(self, party=None):
        if party is None:
            party = self.current_party
        return self._money[party]

    def inc_money(self, amount, party=None):
        if party is None:
            party = self.current_party
        self._money[party] += amount
        
    # Start a new game
    def build_new(self):
        logger.info("Build New")
        self.allunits = []
        self.allitems = {}
        self.allstatuses = {}
        self.factions = {}
        self.allreinforcements = {}
        self.prefabs = []
        self.objective = None
        self.phase_music = None
        self.map = None
        self.game_constants = Counter()
        self.game_constants['level'] = 0
        # Set up random seed
        if cf.OPTIONS['random_seed'] >= 0:
            random_seed = int(cf.OPTIONS['random_seed'])
        else:
            random_seed = random.randint(0, 1023)
        static_random.set_seed(random_seed)
        logger.debug('Random Seed: %d', random_seed)
        self.game_constants['_random_seed'] = random_seed

        self._money = Counter()
        self._convoy = {0: []}
        self.current_party = '0'  # Party is always a string, not an integer
        self.play_time = 0
        if cf.CONSTANTS['support']:
            self.support = Support.Support_Graph('Data/support_nodes.txt', 'Data/support_edges.txt')
        else:
            self.support = None
        if cf.CONSTANTS['overworld']:
            self.overworld = Overworld.Overworld()
        else:
            self.overworld = None
        self.unlocked_lore = []
        self.statistics = []
        self.market_items = set()

        self.sweep()
        self.generic()

        # Turn tutorial mode off if the difficulty does not start with a tutorial
        if not int(self.mode['tutorial']):
            cf.OPTIONS['Display Hints'] = 0

    def default_mode(self):
        return list(GC.DIFFICULTYDATA.values())[0].copy()

    def set_generic_mode(self):
        self.mode = self.default_mode()  # Need to make sure its got a mode ready
        self.default_mode_choice()

    def default_mode_choice(self):
        if self.mode['growths'] == '?':
            self.mode['growths'] = 1  # Fixed
        if self.mode['death'] == '?':
            self.mode['death'] = 1  # Classic

    def check_mode(self, legal_modes):
        return 'All' in legal_modes or self.mode['name'] in legal_modes or self.mode['id'] in legal_modes

    def sweep(self):
        # None of these are kept through different levels
        self.level_constants = Counter()
        self.triggers = {}
        self.talk_options = []
        self.base_conversations = OrderedDict()
        self.message = []
        self.turncount = 0
        self.action_log = Turnwheel.ActionLog()

    def display_all_units(self):
        for unit in self.allunits:
            print(unit.name, unit.event_id, unit.position)

    def set_next_uids(self):
        if self.allitems:
            ItemMethods.ItemObject.next_uid = max(self.allitems.keys()) + 1
        else:
            ItemMethods.ItemObject.next_uid = 100
        if self.allstatuses:
            StatusCatalog.Status.next_uid = max(self.allstatuses.keys()) + 1
        else:
            StatusCatalog.Status.next_uid = 100

    def load(self, load_info):
        logger.info("Load")
        # Rebuild gameStateObj
        self.allunits = [UnitObject.UnitObject(info) for info in load_info['allunits']]
        self.allitems = {info['uid']: ItemMethods.deserialize(info) for info in load_info['allitems']}
        self.allstatuses = {info['uid']: StatusCatalog.deserialize(info) for info in load_info['allstatuses']}
        self.set_next_uids()
        self.factions = load_info['factions'] if 'factions' in load_info else (load_info['groups'] if 'groups' in load_info else {})
        self.allreinforcements = load_info['allreinforcements'] 
        self.prefabs = load_info['prefabs']
        self.triggers = load_info.get('triggers', dict())
        map_info = load_info['map']
        self.playtime = load_info['playtime']
        self._convoy = {party_id: [self.get_item_from_uid(uid) for uid in party_convoy] for party_id, party_convoy in load_info['convoy'].items()}
        self._convoy = {party_id: [item for item in party_convoy if item] for party_id, party_convoy in self._convoy.items()}
        self._money = Counter({party_id: money for party_id, money in load_info['money'].items()})
        self.current_party = load_info['current_party']
        self.turncount = load_info['turncount']
        self.game_constants = load_info['game_constants']
        static_random.set_seed(self.game_constants.get('_random_seed', 0))
        self.level_constants = load_info['level_constants']
        self.objective = Objective.Objective.deserialize(load_info['objective']) if load_info['objective'] else None
        self.phase_music = CustomObjects.PhaseMusic.deserialize(load_info['phase_music']) if load_info['phase_music'] else None
        support_dict = load_info['support']
        self.talk_options = load_info['talk_options']
        self.base_conversations = load_info['base_conversations']
        self.stateMachine = StateMachine.StateMachine(load_info['state_list'][0], load_info['state_list'][1])
        self.statistics = load_info['statistics']
        self.message = [Dialogue.Dialogue_Scene(scene) for scene in load_info.get('message', [])]
        # self.message = []
        if cf.CONSTANTS['overworld']:
            self.overworld = Overworld.Overworld.deserialize(load_info.get('overworld'), self)
        else:
            self.overworld = None
        self.unlocked_lore = load_info['unlocked_lore']
        self.market_items = load_info.get('market_items', set())
        self.mode = load_info.get('mode', self.default_mode())

        # Child Statuses
        for status in self.allstatuses.values():
            if status.aura and status.aura.child_uid is not None:
                status.aura.child_status = self.get_status_from_uid(status.aura.child_uid)
        # Unit Items and Statuses
        for idx, unit in enumerate(self.allunits):
            for item_uid in load_info['allunits'][idx]['items']:
                unit.items.append(self.get_item_from_uid(item_uid))
            for status_uid in load_info['allunits'][idx]['status_effects']:
                status = self.get_status_from_uid(status_uid)
                StatusCatalog.attach_to_unit(status, unit, self)

        # Statuses
        # for index, info in enumerate(load_info['allunits']):
        #     for s_dict in info['status_effects']:
        #         if isinstance(s_dict, dict):
        #             StatusObject.deserialize(s_dict, self.allunits[index])
        #         else:
        #             self.allunits[index].status_effects.append(s_dict)

        # Action Log
        self.action_log = Turnwheel.ActionLog.deserialize(load_info['action_log'], self)

        # Map
        logger.info('Creating map...')
        self.map = SaveLoad.create_map(self, 'Data/Level' + str(self.game_constants['level']))
        logger.info('Done creating map...')
        # Set up blitting surface
        if self.map:
            mapSurfWidth = self.map.width * GC.TILEWIDTH
            mapSurfHeight = self.map.height * GC.TILEHEIGHT
            self.mapSurf = Engine.create_surface((mapSurfWidth, mapSurfHeight))

            self.grid_manager = AStar.Grid_Manager(self.map)

        if map_info:
            self.action_log.replay_map_commands(self)
            for position, current_hp in map_info.get('HP', []):
                self.map.tiles[position].set_hp(current_hp)
            # for position, serialized_item in map_info.get('Weapons', []):
            #     self.map.tile_info_dict[position]['Weapon'] = ItemMethods.deserialize(serialized_item)

        if self.map:
            self.boundary_manager = Boundary.BoundaryInterface(self.map)

            for unit in self.allunits:
                if unit.position:
                    self.grid_manager.set_unit_node(unit.position, unit)
                    for status in unit.status_effects:
                        if status.aura:
                            Aura.update_grid_manager_on_load(unit, status, self)

            self.boundary_manager.reset(self)

        # Support
        if cf.CONSTANTS['support']:
            self.support = Support.Support_Graph('Data/support_nodes.txt', 'Data/support_edges.txt')
            self.support.deserialize(support_dict)
        else:
            self.support = None

        self.generic()
        if 'phase_info' in load_info:
            self.phase.current, self.phase.previous = load_info['phase_info']

    def generic(self):
        logger.info("Generic")

        lord_units = [unit for unit in self.allunits if unit.position and 'Lord' in unit.tags and unit.team == 'player']
        lord_position = lord_units[0].position if lord_units else (0, 0)
        # Certain variables change if this is being initialized at beginning of game, and not a save state
        self.phase = CustomObjects.Phase(self)
        self.statedict = {'previous_cursor_position': lord_position,
                          'levelIsComplete': False, # Whether the level is complete
                          'outroScriptDone': False} # Whether the outro script has been played
        # For hiding menus
        self.hidden_active = None
        self.hidden_child = None
        self.main_menu = None
        # Combat slots
        self.combatInstance = None
        # Banner slots
        self.banners = []
        # Status slots
        self.status = None
        # AI slots
        self.ai_current_unit = None
        self.ai_unit_list = None
        self.ai_build_flag = True
        # Movement manager
        self.moving_units = set()

        # Handle cursor
        if any(unit.team == 'player' and unit.position for unit in self.allunits):
            # cursor_position = [unit.position for unit in self.allunits if unit.team == 'player' and unit.position][0]
            cursor_position = lord_position
        else:
            cursor_position = (0, 0)
        self.cursor = Cursor.Cursor('Cursor', cursor_position)
        self.fake_cursors = []
        self.tutorial_mode = False

        # Handle cameraOffset
        # Track how much camera has moved in pixels:
        self.cameraOffset = CustomObjects.CameraOffset(self.cursor.position[0], self.cursor.position[1])
        self.cursor.autocursor(self, force=True)
        # Other slots
        self.highlight_manager = Highlight.HighlightController()
        self.allarrows = []
        self.allanimations = []

        # Reset the units updates on load
        # And have the units arrive on map
        for unit in self.allunits:
            unit.resetUpdates()
            # if unit.position:
                # Action.ArriveOnMap(unit, unit.position).do(self)
        
        self.old_map = None

        self.exp_gain_struct = None  # Used to pass in information to the GainExpState
        self.info_menu_struct = {'current_state': 0,
                                 'scroll_units': [],
                                 'one_unit_only': False,
                                 'chosen_unit': None}

    def get_total_party_members(self):
        return len(self.get_units_in_party(self.current_party))

    def get_units_in_party(self, party=None):
        if party is None:
            party = self.current_party
        return [unit for unit in self.allunits if unit.team == 'player' and not unit.dead and not unit.generic_flag and unit.party == party]

    def check_rout(self):
        return not any(unit.team.startswith('enemy') and unit.position for unit in self.allunits)

    def check_dead(self, name):
        return any(unit.name == name and unit.dead for unit in self.allunits)

    def check_alive(self, name):
        return any(unit.name == name and not unit.dead for unit in self.allunits)

    def get_unit_from_id(self, u_id):
        if isinstance(u_id, set):
            return {unit for unit in self.allunits if unit.id in u_id}
        else:
            for unit in self.allunits:
                if unit.id == u_id:
                    return unit

    def get_unit_from_pos(self, pos):
        if isinstance(pos, set):
            return {unit for unit in self.allunits if unit.position in pos}
        else:
            for unit in self.allunits:
                if unit.position == pos:
                    return unit

    def get_unit_from_name(self, name):
        if isinstance(name, set):
            return {unit for unit in self.allunits if unit.name in name}
        else:
            for unit in self.allunits:
                if unit.name == name:
                    return unit

    def get_unit(self, any_id):
        if isinstance(any_id, set):
            return {unit for unit in self.allunits if unit.name in any_id or unit.id in any_id or unit.event_id in any_id}
        else:
            for unit in self.allunits:
                if any_id in (unit.name, unit.id, unit.event_id):
                    return unit

    def get_item_from_uid(self, u_id):
        return self.allitems.get(u_id)

    def register_item(self, item):
        logger.info('Registering item %s as %s', item, item.uid)
        self.allitems[item.uid] = item

    def register_items(self, items):
        for item in items:
            self.allitems[item.uid] = item

    def get_status_from_uid(self, u_id):
        return self.allstatuses.get(u_id)

    def register_status(self, status):
        logger.info('Registering status %s as %s', status, status.uid)
        self.allstatuses[status.uid] = status
        # We need to remember to register an aura's child status
        if status.aura:
            self.register_status(status.aura.child_status)

    def check_formation_spots(self):
        # Returns None if no spot available
        # Returns a spot if a spot is available
        list_of_spots = [position for position, value in self.map.tile_info_dict.items() if 'Formation' in value]
        list_of_unit_positions = [unit.position for unit in self.allunits if unit.team == 'player']
        for position in list_of_spots:
            if position not in list_of_unit_positions:
                return position
        return None

    def set_camera_limits(self):
        self.cameraOffset.set_travel_limits(self.map)
        self.cameraOffset.set_limits(self.map)

    def remove_fake_cursors(self):
        self.fake_cursors = []

    def tutorial_mode_off(self):
        self.remove_fake_cursors()
        self.tutorial_mode = False

    def arena_closed(self, unit):
        if cf.CONSTANTS['arena_global_limit'] > 0 and \
                self.level_constants['_global_arena_uses'] >= cf.CONSTANTS['arena_global_limit']:
            return True
        elif cf.CONSTANTS['arena_unit_limit'] > 0 and \
                self.level_constants['_' + str(unit.id) + '_arena_uses'] >= cf.CONSTANTS['arena_unit_limit']:
            return True
        return False

    # def removeSprites(self):
    #     # Decouple sprites
    #     for unit in self.allunits:
    #         unit.sweep()
    #         for item in unit.items:
    #             item.removeSprites()
    #         for status in unit.status_effects:
    #             status.removeSprites()
    #     # if self.map:
    #     #    self.map.removeSprites() I don't think this is actually necessary..., since we save a serialized version of the map now
    #     if self.objective:
    #         self.objective.removeSprites()
    #     for item in self.convoy:
    #         item.removeSprites()

    def save(self):
        self.action_log.record = False
        # # Reset all position dependant voodoo -- Done by gameStateObj at once instead of one at a time...
        # for unit in self.allunits:
        #     unit.leave(self, serializing=True)
        # ser_units = [unit.serialize(self) for unit in self.allunits]
        # for unit in self.allunits:
        #     unit.arrive(self, serializing=True)
        to_save = {'allunits': [unit.serialize(self) for unit in self.allunits],
                   'allitems': [item.serialize() for item in self.allitems.values()],
                   'allstatuses': [status.serialize() for status in self.allstatuses.values()],
                   'factions': self.factions,
                   'allreinforcements': self.allreinforcements,
                   'prefabs': self.prefabs,
                   'triggers': self.triggers,
                   'map': self.map.serialize() if self.map else None,
                   'playtime': self.playtime,
                   'turncount': self.turncount,
                   'convoy': {party_id: [item.uid for item in party_convoy] for party_id, party_convoy in self._convoy.items()},
                   'money': self._money,
                   'current_party': self.current_party,
                   'objective': self.objective.serialize() if self.objective else None,
                   'phase_music': self.phase_music.serialize() if self.phase_music else None,
                   'support': self.support.serialize() if self.support else None,
                   'action_log': self.action_log.serialize(self),
                   'overworld': self.overworld.serialize() if self.overworld else None,
                   'game_constants': self.game_constants,
                   'level_constants': self.level_constants,
                   'unlocked_lore': self.unlocked_lore,
                   'talk_options': self.talk_options,
                   'base_conversations': self.base_conversations,
                   'state_list': self.stateMachine.serialize(),
                   'statistics': self.statistics,
                   'market_items': self.market_items,
                   'mode': self.mode,
                   'message': [message.serialize() for message in self.message],
                   'phase_info': (self.phase.current, self.phase.previous)
                   }
        import time
        to_save_meta = {'playtime': self.playtime,
                        'realtime': time.time(),
                        'version': GC.version,
                        'mode_id': self.mode['id'],
                        'save_slot': self.save_slot}
        self.action_log.record = True
        return to_save, to_save_meta

    def loadSprites(self):
        # Reload sprites
        for unit in self.allunits:
            unit.resetUpdates()
            unit.loadSprites()
            for item in unit.items:
                item.loadSprites()
            for status in unit.status_effects:
                status.loadSprites()
        if self.map:
            self.map.loadSprites()
        for party in self._convoy.values():
            for item in party:
                item.loadSprites()

    def clean_up(self):
        # Units should leave (first, because clean_up removes position)
        for unit in self.allunits:
            unit.leave(self)
            Action.RemoveFromMap(unit).do(self)
        for unit in self.allunits:
            unit.clean_up(self)

        # Remove non player team units
        self.allunits = [unit for unit in self.allunits if unit.team == 'player' and not unit.generic_flag]

        # Handle player death
        for unit in self.allunits:
            if unit.dead:
                unit.fatigue = 0
                if not int(self.mode['death']): # Casual
                    unit.dead = False
                elif cf.CONSTANTS['convoy_on_death']:
                    # Give all of the unit's items to the convoy
                    for item in unit.items:
                        if not item.locked:
                            unit.remove_item(item, self)
                            item.owner = 0
                            self.convoy.append(item)

        # Handle fatigue
        self.clean_up_fatigue()

        # Remove unnecessary information between levels
        self.sweep()
        self.map = None
        self.factions = {}
        self.allreinforcements = {}
        self.prefabs = []
        self.objective = None
        self.phase_music = None

    def compare_teams(self, team1, team2):
        # Returns True if allies, False if enemies
        if team1 == team2:
            return True
        elif (team1 == 'player' and team2 == 'other') or (team2 == 'player' and team1 == 'other'):
            return True
        return False

    # Should only be called when moving to next level
    def update_statistics(self, metaDataObj):
        self.statistics.append(CustomObjects.LevelStatistic(self, metaDataObj))
        for unit in self.allunits:
            unit.records = unit.default_records()

    def increment_supports(self):
        if self.support and cf.CONSTANTS['support_end_chapter']:
            units = [unit for unit in self.allunits if unit.position and not unit.dead and unit.id in self.support.node_dict]
            for unit in units:
                node = self.support.node_dict[unit.id]
                other_ids = [other.id for other in units if unit.checkIfAlly(other)]
                for other_id, edge in node.adjacent.items():
                    if other_id in other_ids:
                        edge.increment(cf.CONSTANTS['support_end_chapter'])
        if self.support:  # Reset max number of support levels that can be gotten in one chapter
            units = [unit for unit in self.allunits if unit.id in self.support.node_dict]
            for unit in units:
                node = self.support.node_dict[unit.id]
                for edge in node.adjacent.values():
                    edge.reset()

    def refresh_fatigue(self):
        party_units = self.get_units_in_party()
        refresh_these = [unit for unit in party_units if not unit.position]

        for unit in refresh_these:
            unit.fatigue = 0

    def clean_up_fatigue(self):
        party_units = self.get_units_in_party()
        penalize_these = [unit for unit in party_units if unit.fatigue >= GC.EQUATIONS.get_max_fatigue(unit)]
        help_these = [unit for unit in party_units if unit.fatigue < GC.EQUATIONS.get_max_fatigue(unit)]
        
        if self.game_constants['Fatigue'] == 2:
            fatigue_status = StatusCatalog.statusparser("Fatigued", self)
            # Give a status to those units who are fatigued
            for unit in penalize_these:
                Action.do(Action.AddStatus(unit, fatigue_status), self)
            # Remove status from those units who are not fatigued
            for unit in help_these:
                for status in unit.status_effects:
                    if status.id == "Fatigued":
                        Action.do(Action.RemoveStatus(unit, status), self)

        elif self.game_constants['Fatigue'] == 3:
            fatigue_status = StatusCatalog.statusparser("Fatigued", self)
            # Give a status to those units who are not fatigued    
            for unit in help_these:
                Action.do(Action.AddStatus(unit, fatigue_status), self)
            # Remove status from those units who are fatigued
            for unit in penalize_these:
                for status in unit.status_effects:
                    if status.id == "Fatigued":
                        Action.do(Action.RemoveStatus(unit, status), self)

    def restock_convoy(self):
        cur_convoy = self._convoy[self.current_party]
        items_with_uses = sorted((item for item in cur_convoy if item.uses), key=lambda item: item.id)
        # Actually restock
        current_item = items_with_uses[0]
        for item in items_with_uses[1:]:
            if item.id == current_item.id:
                diff_needed = current_item.uses.total_uses - current_item.uses.uses
                if diff_needed > 0:
                    if item.uses.uses >= diff_needed:
                        item.uses.uses -= diff_needed
                        current_item.uses.uses += diff_needed
                        # Get a new current_item
                        current_item = item
                    else:
                        current_item.uses.uses += item.uses.uses
                        item.uses.uses = 0
                        # Do not get a new current_item
                else:
                    current_item = item
            else:
                current_item = item
        # remove all items with <= 0 uses
        self._convoy[self.current_party] = [item for item in cur_convoy if not item.uses or item.uses.uses > 0]

    def quick_sort_inventories(self, units):
        logger.debug("Quicksorting Inventories")
        my_units = self.get_units_in_party()
        random.shuffle(my_units)
        # print([my_unit.name for my_unit in my_units])
        # First, give all
        for unit in my_units:
            for item in reversed(unit.items):
                unit.remove_item(item, self)
                self.convoy.append(item)
        # Now restock convoy
        self.restock_convoy()
        # For item in convoy
        # Distribute Weapons
        weapons = sorted([item for item in self.convoy if item.weapon], key=lambda i: (i.weapon.LVL, 100 - i.uses.uses if i.uses else 0))
        # weapons = sorted(weapons, key=lambda i: i.uses.uses if i.uses else 100, reverse=True) # Now sort by uses, so we use weapons with more uses first
        # print(weapons)
        for weapon in weapons:
            units_that_can_wield = [unit for unit in my_units if len(unit.items) < cf.CONSTANTS['max_items'] - 1 and
                                    unit.canWield(weapon) and weapon.id not in [item.id for item in unit.items]]
            units_that_can_wield = sorted(units_that_can_wield, key=lambda u: len(u.items), reverse=True)
            # print([unit.name for unit in units_that_can_wield])
            if units_that_can_wield:
                # Give randomly
                unit = units_that_can_wield.pop()
                unit.add_item(weapon, self)
                self.convoy.remove(weapon)
                # print(unit.name, weapon)
        # Distribute spells
        spells = sorted([item for item in self.convoy if item.spell], key=lambda i: (i.spell.LVL, 100 - i.uses.uses if i.uses else 0))
        # print(spells)
        for spell in spells:
            units_that_can_wield = [u for u in my_units if len(u.items) < cf.CONSTANTS['max_items'] - 1 and
                                    u.canWield(spell) and spell.id not in [item.id for item in u.items]]
            units_that_can_wield = sorted(units_that_can_wield, key=lambda u: len(u.items), reverse=True)
            # print([unit.name for unit in units_that_can_wield])
            if units_that_can_wield:
                # Give randomly
                unit = units_that_can_wield.pop()
                unit.add_item(spell, self)
                self.convoy.remove(spell)
                # print(unit.name, spell)
        # Distribute healing items
        healing_items = sorted([item for item in self.convoy if item.usable and item.heal], key=lambda i: (i.heal, i.uses.uses if i.uses else 100))
        # print(healing_items)
        # Sort by max hp
        units_that_can_wield = [u for u in my_units if len(unit.items) < cf.CONSTANTS['max_items'] and not any(item.heal for item in u.items)]
        units_that_can_wield = sorted(units_that_can_wield, key=lambda u: u.stats['HP'])
        for healing_item in reversed(healing_items):
            if units_that_can_wield:
                unit = units_that_can_wield.pop()
                unit.add_item(healing_item, self)
                self.convoy.remove(healing_item)
        # Done

    def output_progress_xml(self):
        with open('Saves/progress_log.xml', mode='a', encoding='utf-8') as p_log:
            p_log.write('<level name="' + str(self.game_constants['level']) + '">\n')
            p_log.write('\t<mode>' + self.mode['name'] + '</mode>\n')
            # Game Constants
            p_log.write('\t<game_constants>')
            p_log.write(';'.join([str(k) + ',' + str(v) for k, v in self.game_constants.items()]))
            p_log.write('</game_constants>\n')
            # Convoy
            p_log.write('\t<convoy>')
            p_log.write(','.join([item.id + ' ' + str(item.uses.uses if item.uses else '--') for item in self.convoy]))
            p_log.write('</convoy>\n')
            # Units
            p_log.write('\t<units>\n')
            for unit in self.allunits:
                p_log.write('\t\t<unit name="' + str(unit.id) + '">\n')
                p_log.write('\t\t\t<party>' + str(unit.party) + '</party>\n')
                p_log.write('\t\t\t<class>' + str(unit.klass) + '</class>\n')
                p_log.write('\t\t\t<level>' + str(unit.level) + '</level>\n')
                p_log.write('\t\t\t<exp>' + str(unit.exp) + '</exp>\n')
                p_log.write('\t\t\t<items>' + ','.join([item.id + ' ' + str(item.uses.uses if item.uses else '--') for item in unit.items]) + '</items>\n')
                p_log.write('\t\t\t<wexp>' + ','.join([str(wexp) for wexp in unit.wexp]) + '</wexp>\n')
                p_log.write('\t\t\t<skills>' + ','.join([skill.id for skill in unit.status_effects]) + '</skills>\n')
                p_log.write('\t\t\t<dead>' + str(1 if unit.dead else 0) + '</dead>\n')
                p_log.write('\t\t</unit>\n')
            p_log.write('\t</units>\n')
            p_log.write('</level>\n\n')

    def drawMap(self):
        """Draw the map to a Surface object."""

        # mapSurf will be the single Surface object that the tiles are drawn
        # on, so that is is easy to position the entire map on the GC.DISPLAYSURF
        # Surface object. First, the width and height must be calculated
        mapSurf = self.mapSurf
        # mapSurf.fill(GC.COLORDICT['bg_color']) # Start with a blank color on the surface
        # Draw the tile sprites onto this surface
        self.map.draw(mapSurf, self)
        self.boundary_manager.draw(mapSurf, (mapSurf.get_width(), mapSurf.get_height()))
        self.highlight_manager.draw(mapSurf)
        for arrow in self.allarrows:
            arrow.draw(mapSurf)
        # Reorder units so they are drawn in correct order, from top to bottom, so that units on bottom are blit over top
        # Only draw units that will be in the camera's field of view
        # unitSurf = gameStateObj.generic_surf.copy()
        camera_x = int(self.cameraOffset.get_x())
        camera_y = int(self.cameraOffset.get_y())
        culled_units = [unit for unit in self.allunits if unit.position and
                        ((camera_x - 1 <= unit.position[0] <= camera_x + GC.TILEX + 1 and
                         camera_y - 1 <= unit.position[1] <= camera_y + GC.TILEY + 1) or
                         unit.sprite.draw_anyway())]
        draw_me = sorted(culled_units, key=lambda unit: unit.position[1])
        for unit in draw_me:
            unit.draw(mapSurf, self)
        for unit_hp in draw_me:
            unit_hp.draw_hp(mapSurf, self)
        # draw cursor
        if self.cursor:
            self.cursor.draw(mapSurf)
        for cursor in self.fake_cursors:
            cursor.draw(mapSurf)
        # Draw weather
        pos_x, pos_y = self.cameraOffset.get_x() * GC.TILEWIDTH, self.cameraOffset.get_y() * GC.TILEHEIGHT
        for weather in self.map.weather:
            weather.draw(mapSurf, pos_x, pos_y)
        return mapSurf
