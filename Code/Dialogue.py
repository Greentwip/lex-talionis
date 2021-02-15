import re, math, itertools
# Custom imports
from . import GlobalConstants as GC
from . import configuration as cf
from . import static_random
from . import Engine, TextChunk, Utility, Image_Modification
from . import BaseMenuSurf, Background, UnitPortrait, WorldMap, Banner, Cursor
from . import StatusCatalog, ItemMethods, Action

import logging
logger = logging.getLogger(__name__)

hardset_positions = {'OffscreenLeft': -96, 'FarLeft': -24, 'Left': 0, 'MidLeft': 24,
                     'MidRight': 120, 'Right': 144, 'FarRight': 168, 'OffscreenRight': 240}

# === GET INFO FOR DIALOGUE SCENE ==================================================
class Dialogue_Scene(object):
    def __init__(self, scene, unit=None, unit2=None, name=None, tile_pos=None, if_flag=False):
        self.scene = scene
        if self.scene:
            with open(scene, encoding='utf-8', mode='r') as scenefp: # Open this scene's file database
                self.scene_lines = scenefp.readlines()
        else:
            self.scene_lines = []
        if cf.OPTIONS['debug']:
            if not self.count_if_statements():
                logger.error('ERROR: Incorrect number of if and end statements! %s', scene)

        # Background sprite
        self.background = None
        self.midground = None
        self.foreground = None
        # Dictionary of scene sprites
        self.unit_sprites = {}
        # Dialogs
        self.dialog = []

        # Optional unit
        self.unit = unit
        self.unit1 = unit  # Alternate name
        self.unit2 = unit2
        # Name -- What is the given event name for this tile
        self.name = name
        # Tile Pos -- What tile is being acted on, if any (applied in unlock, switch, village, destroy, search, etc. scripts)
        self.tile_pos = tile_pos
        # Next Position -- Saves a position
        self.next_position = None
        # Whether we are processing
        self.processingflag = 1
        # Whether we are done
        self.done = False
        # Whether we are waiting for user input
        self.waiting = False

        # For transition
        self.transition_state = 0  # 0 -- No change, 1 -- To black, 2 -- Away from black
        self.transition_speed = 15 * GC.FRAMERATE  # How long to transition for
        self.transition_color = (0, 0, 0)
        self.transition_transparency = 0  # Amount of alpha (255 fully dark)
        self.transition_last_update = Engine.get_time()

        self.scene_lines_index = 0 # Keeps track of where we are in the scene
        self.if_stack = [] # Keeps track of how many ifs we've encountered while searching for
        # the bad ifs 'end'.
        self.parse_stack = [] # Keeps track of whether we've encountered a truth this level or not

        self.current_state = "Processing" # Other options are "Waiting", "Transitioning"
        self.last_state = None
        self.do_skip = False
        self.turnwheel_flag: int = 0 # Whether to enter the turnwheel state after this scene
        self.battle_save_flag = False # Whether to enter the battle save state after this scene has completed
        self.reset_state_flag = False # Whether to reset state to free state after this scene has completed
        self.reset_boundary_manager = False # Whether to reset the boundary manager after this scene has completed. Set to true when tiles are changed

        # Handle waiting
        self.last_wait_update = Engine.get_time()
        self.waittime = 0

        # Handles skipping
        self.skippable_commands = {'s', 'u', 'qu', 't', 'wait', 'bop', 'mirror',
                                   'map_pan', 'set_expression', 'sound',
                                   'credits', 'endings', 'cinematic', 'start_move',
                                   'move_sprite', 'qmove_sprite', 'midground_movie',
                                   'foreground_movie'}

        # Handles unit face priority
        self.priority_counter = 1

        # Assumes all "if" statements evaluate to True?
        self.if_flag = if_flag

    def serialize(self):
        return self.scene

    def count_if_statements(self):
        if_count = 0
        for line in self.scene_lines:
            new_line = line.strip()
            if new_line.startswith('if;'):
                if_count += 1
            elif new_line == 'end':
                if_count -= 1
        return not bool(if_count) # Should be 0.

    def skip(self):
        self.do_skip = True
        if not self.current_state == "Paused":
            self.current_state = "Processing"
        # Reset transition
        self.transition_state = 0  # 0 -- No change, 1 -- To black, 2 -- Away from black
        self.transition_transparency = 0
        # Remove midground and foreground
        self.midground = None
        self.foreground = None

    def read_script(self, gameStateObj=None, metaDataObj=None):
        while(self.scene_lines_index < len(self.scene_lines) and self.current_state == "Processing"):
            line = self.scene_lines[self.scene_lines_index]
            # Doing some parsing of the lines
            if len(line) <= 0:
                self.scene_lines_index += 1
                continue

            line = line.strip()
            if line.startswith('#'):
                self.scene_lines_index += 1
                continue

            line = line.split(';')
            # logger.debug(line)
            if (self.if_flag or self.handle_if(line, gameStateObj, metaDataObj)) and (not self.do_skip or not (line[0] in self.skippable_commands)):
                self.parse_line(line, gameStateObj, metaDataObj)
            self.scene_lines_index += 1

    def handle_if(self, line, gameStateObj, metaDataObj):
        # if cf.OPTIONS['debug']: print(line[0], self.if_stack)
        # === CONDITIONALS PARSING
        if line[0] == 'if':
            if not self.if_stack or self.if_stack[-1]:
                truth = eval(line[1])
                self.if_stack.append(truth)
                self.parse_stack.append(truth) # Whether we've encountered a truth this level
            else:
                self.if_stack.append(False)
                self.parse_stack.append(True)
            return False
        elif line[0] == 'elif':
            if not self.if_stack:
                logger.error("Syntax Error somewhere in script. 'elif' needs to be after if statement.")
                return # Impossible. Must have at least parsed an if before hitting an elif
            # If we haven't encountered a truth yet
            if not self.parse_stack[-1]: # if not self.if_stack[-1] and (len(self.if_stack) == 1 or all(t_value for t_value in self.if_stack[:-1])):
                truth = eval(line[1])
                self.if_stack[-1] = truth
                self.parse_stack[-1] = truth
            else:
                self.if_stack[-1] = False
            return False
        elif line[0] == 'else':
            if not self.if_stack:
                logger.error("Syntax Error somewhere in script. 'else' needs to be after if statement.")
                return # Impossible. Must have at least parsed an if before hitting an else
            # If the most recent is False but the rest below are non-existent or true
            if not self.parse_stack[-1]: # not self.if_stack[-1] and (len(self.if_stack) == 1 or all(t_value for t_value in self.if_stack[:-1])):
                self.if_stack[-1] = True
                self.parse_stack[-1] = True
            else:
                self.if_stack[-1] = False # Parse stack stays the same
            return False
        elif line[0] == 'end':
            self.if_stack.pop()
            self.parse_stack.pop()
            return False

        if self.if_stack and not self.if_stack[-1]:
            return False
        return True

    def update(self, gameStateObj=None, metaDataObj=None):
        current_time = Engine.get_time()
        if self.current_state != self.last_state:
            self.last_state = self.current_state
            logger.debug('Dialogue Current State: %s', self.current_state)

        if self.current_state == "Waiting" or self.current_state == "FlashCursor":
            if current_time > self.last_wait_update + self.waittime:
                if self.current_state == "FlashCursor":
                    gameStateObj.cursor.drawState = 0
                self.current_state = "Processing" # Done waiting. Head back to processing
            else:
                return # Keep waiting. Do nothing

        elif self.current_state == "Processing":
            self.reset_unit_sprites() # Stop talking when grabbing data - probably only affected at end of file
            # parse sceneLines
            self.read_script(gameStateObj, metaDataObj)
            if self.scene_lines_index >= len(self.scene_lines):
                self.end()

        elif self.current_state == "Transitioning":
            progress = (current_time - self.transition_last_update) / self.transition_speed
            if self.transition_state == 1:  # Increasing transition
                self.transition_transparency = 255 * Utility.clamp(progress, 0, 1)
            elif self.transition_state == 2:  # Decreasing transition
                self.transition_transparency = 255 - (255 * Utility.clamp(progress, 0, 1))
            if progress > 1.33 or progress < 0:
                self.current_state = "Processing"
                if self.scene_lines_index >= len(self.scene_lines): # Check if we're done
                    self.end()

        elif self.current_state == "Displaying": # Don't dialog while transitioning or processing
            if self.dialog: # Only update dialog if it exists, could also just be waiting or not even in this state
                self.dialog[-1].update() # This runs the character generation...
                if self.dialog[-1].done and not self.dialog[-1].waiting:
                    self.current_state = "Processing"

        elif self.current_state == "Paused":
            pass

        if self.dialog and (self.dialog[-1].waiting or self.dialog[-1].done):
            self.reset_unit_sprites()

    def end(self):
        self.done = True
        return

    def parse_line(self, line, gameStateObj=None, metaDataObj=None):
        if line[0] == '':
            return
        # time = Engine.get_true_time()
        logger.info('Script line to parse: %s', line)
        # === SKIPPING DIALOGUE
        # End skip
        if line[0] == 'end_skip':
            self.do_skip = False

        # === PAUSE
        elif line[0] == 'wait':
            self.waittime = int(line[1])
            self.last_wait_update = Engine.get_time()
            self.current_state = "Waiting"

        # === BACKGROUND
        # Change the background
        elif line[0] == 'b':
            if 'map' in line:
                self.background = WorldMap.WorldMapBackground(GC.IMAGESDICT[line[1]], labels=False)
            elif 'advanced' in line:
                self.background = WorldMap.WorldMapBackground(GC.IMAGESDICT[line[1]])
            else:
                self.background = Background.StaticBackground(GC.IMAGESDICT[line[1]], fade=False)
        # Remove the background
        elif line[0] == 'remove_background':
            self.background = None

        # === FOREGROUND
        # Change the foreground
        elif line[0] == 'foreground':
            self.foreground = Background.StaticBackground(GC.IMAGESDICT[line[1]], fade=False)
        elif line[0] == 'remove_foreground':
            self.foreground = None

        # === MOVIES
        elif line[0] == 'foreground_movie' or line[0] == 'midground_movie':
            movie = Background.MovieBackground(
                line[1], speed='slow' in line, loop='loop' in line,
                fade_out='fade_out' in line)
            if line[0] == 'foreground_movie':
                self.foreground = movie
            elif line[0] == 'midground_movie':
                self.midground = movie
            if 'hold' in line:
                self.waittime = int(1e6)
                self.last_wait_update = Engine.get_time()
                self.current_state = "Waiting"

        # === WORLD MAP
        elif line[0] == 'wm_pan':
            new_position = self.parse_pos(line[1], gameStateObj)
            self.background.pan(new_position)
        elif line[0] == 'wm_qpan':
            new_position = self.parse_pos(line[1], gameStateObj)
            self.background.quick_pan(new_position)
        elif line[0] in ('wm_load', 'wm_qload', 'wm_add'):
            starting_position = self.parse_pos(line[2], gameStateObj)
            if line[0] == 'wm_add':
                starting_position = (starting_position[0]*16, starting_position[1]*16)
            for unit in gameStateObj.allunits:
                if unit.name == line[1]:
                    klass = unit.klass
                    gender = 'M' if unit.gender < 5 else 'F'
                    team = unit.team
                    break
            else:
                klass, gender, team = line[3:6]
            transition_in = line[0] == 'wm_load' and not self.do_skip
            self.background.add_sprite(line[1], klass, gender, team, starting_position, transition_in)
        elif line[0] == 'wm_remove':
            self.background.remove_sprite(line[1])
        elif line[0] == 'wm_qremove':
            self.background.quick_remove_sprite(line[1])
        elif line[0] == 'wm_move':
            new_position = self.parse_pos(line[2], gameStateObj)
            if self.do_skip:
                self.background.offset_sprite(line[1], new_position)
            else:
                self.background.move_sprite(line[1], new_position, slow='slow' in line)
        elif line[0] == 'wm_move_unit':
            new_position = self.parse_pos(line[2], gameStateObj)
            new_position = (new_position[0]*16, new_position[1]*16)
            if self.do_skip:
                self.background.offset_sprite(line[1], new_position)
            else:
                self.background.move_sprite(line[1], new_position, slow='slow' in line)
        elif line[0] == 'wm_set':
            new_position = self.parse_pos(line[2], gameStateObj)
            if self.do_skip:
                self.background.teleport_sprite(line[1], new_position)
            else:
                self.background.set_sprite(line[1], new_position, slow='slow' in line)
        elif line[0] == 'wm_set_unit':
            new_position = self.parse_pos(line[2], gameStateObj)
            new_position = (new_position[0]*16, new_position[1]*16)
            if self.do_skip:
                self.background.teleport_sprite(line[1], new_position)
            else:
                self.background.set_sprite(line[1], new_position, slow='slow' in line)
        elif line[0] == 'wm_focus_unit':
            self.background.focus_sprite(line[1])
        elif line[0] == 'wm_unfocus_unit':
            self.background.unfocus_sprite(line[1])
        elif line[0] == 'wm_label':
            name = line[1]
            position = self.parse_pos(line[2], gameStateObj)
            self.background.add_label(name, position)
        elif line[0] == 'wm_label_clear':
            self.background.clear_labels()
        elif line[0] == 'wm_highlight':
            if len(line) > 2:
                new_position = self.parse_pos(line[2], gameStateObj)
            else:
                new_position = (0, 0)
            self.background.add_highlight(GC.IMAGESDICT[line[1]], new_position)
        elif line[0] == 'wm_highlight_clear':
            self.background.clear_highlights()
        elif line[0] == 'wm_marker':
            new_pos = self.parse_pos(line[2], gameStateObj)
            self.background.add_marker(GC.IMAGESDICT[line[1]], new_pos)
        elif line[0] == 'wm_marker_clear':
            self.background.clear_markers()
        elif line[0] == 'wm_cursor':
            pos = self.parse_pos(line[1], gameStateObj)
            self.background.create_cursor(pos)
        elif line[0] == 'wm_remove_cursor':
            self.background.remove_cursor()

        # === OVERWORLD
        elif line[0] == 'show_overworld':
            self.background = gameStateObj.overworld
        elif line[0] == 'ow_trigger':
            gameStateObj.overworld.triggers.append(line[1])
        elif line[0] == 'force_ow_trigger':
            if len(line) > 1:
                gameStateObj.overworld.triggers.append(line[1])
            gameStateObj.stateMachine.changeState('overworld')
            self.current_state = "Paused"
        elif line[0] == 'force_leave_overworld':
            gameStateObj.stateMachine.back()  # Back to previous dialogue
            gameStateObj.stateMachine.back()
        elif line[0] == 'ow_location_show':
            if self.do_skip:
                gameStateObj.overworld.quick_show_location(line[1])
            else:
                gameStateObj.overworld.show_location(line[1])
                self.current_state = "Paused"
                gameStateObj.stateMachine.changeState('overworld_effects')
        elif line[0] == 'ow_location_quick_show':
            gameStateObj.overworld.quick_show_location(line[1])
        elif line[0] == 'ow_location_hide':
            gameStateObj.overworld.hide_location(line[1])
        elif line[0] == 'ow_next_location':
            if len(line) > 1:
                gameStateObj.overworld.set_next_location(line[1])
            else:
                gameStateObj.overworld.set_next_location(None)
        elif line[0] == 'ow_move_party' or line[0] == 'ow_quick_move_party':
            if len(line) > 2:
                party_id = line[2]
            else:
                party_id = '0'
            # Start move
            if line[0] == 'ow_quick_move_party' or self.do_skip:
                gameStateObj.overworld.quick_move_party(line[1], party_id, gameStateObj)
            else:
                gameStateObj.overworld.move_party(line[1], party_id, gameStateObj)
                self.current_state = "Paused"
                gameStateObj.stateMachine.changeState('overworld_effects')
        elif line[0] == 'ow_add_party':
            party_id = line[2]
            lords = line[3].split(',')  # Unit IDs
            gameStateObj.overworld.add_party(line[1], party_id, lords, gameStateObj)
        elif line[0] == 'ow_remove_party':
            gameStateObj.overworld.remove_party(line[2])
        # elif line[0] == 'ow_add_party_member':
        #     party_id = int(line[1])
        #     gameStateObj.overworld.add_party_member(party_id, line[2].split(','))
        elif line[0] == 'ow_set_cursor':
            new_pos = tuple([int(num) for num in line[1].split(',')])
            gameStateObj.overworld.set_cursor(new_pos)

        # === UNIT SPRITE
        # Add a unit to the scene
        elif line[0] == 'u':
            # This is a complicated method of parsing unit lines using 'u' as delimiter
            spl = []
            w = 'u'
            for x, y in itertools.groupby(line, lambda z: z == w):
                if x:
                    spl.append([])
                spl[-1].extend(y)

            for sub_command in spl:
                if self.add_unit_sprite(gameStateObj, sub_command, transition=True):
                    # Force wait after unit sprite is drawn to allow time to transition.
                    self.waittime = 266  # 16 frames
                    self.last_wait_update = Engine.get_time()
                    self.current_state = "Waiting"
        # Add a unit to the scene without transition
        elif line[0] == 'qu':
            self.add_unit_sprite(gameStateObj, line, transition=False)
        # Change a unit's expression
        elif line[0] == 'set_expression':
            # Legal commands (Smile, NoSmile, NormalBlink, OpenEyes, CloseEyes, HalfCloseEyes)
            # Default (NoSmile, NormalBlink)
            commands = line[2].split(',') if len(line) > 2 else []
            name = self.get_name(line[1])
            self.unit_sprites[name].set_expression(commands)
        # Remove a unit from the scene
        elif line[0] == 'r':
            for name in line[1:]:
                unit_name = self.get_name(name)
                if unit_name in self.unit_sprites:
                    self.unit_sprites[unit_name].remove()
                    # Force wait after unit sprite is drawn to allow time to transition.
                    self.waittime = 250
                    self.last_wait_update = Engine.get_time()
                    self.current_state = "Waiting"
        elif line[0] == 'qr': # No transition plox
            for name in line[1:]:
                unit_name = self.get_name(name)
                if unit_name in self.unit_sprites:
                    self.unit_sprites.pop(unit_name)
        # Move a unit sprite
        elif line[0] == 'move_sprite' or line[0] == 'qmove_sprite':
            name = self.get_name(line[1])
            if name in self.unit_sprites:
                unit_sprite = self.unit_sprites[name]
                if line[2] in hardset_positions:
                    new_x = hardset_positions[line[2]]
                    current_x = unit_sprite.position[0]
                    new_position = (new_x - current_x, 0)
                else:
                    new_position = self.parse_pos(line[2], gameStateObj)
                unit_sprite.move(new_position)
                # Wait after unit sprite is moved to allow time to transition
                if line[0] == 'move_sprite':
                    self.waittime = abs(new_position[0] // unit_sprite.unit_speed * unit_sprite.update_time) + 200
                    self.last_wait_update = Engine.get_time()
                    self.current_state = "Waiting"
        # Mirror the unit sprite
        elif line[0] == 'mirror':
            name = self.get_name(line[1])
            if name in self.unit_sprites:
                self.unit_sprites[name].mirror = not self.unit_sprites[name].mirror
        # Bop the unit sprite up and down
        elif line[0] == 'bop':
            name = self.get_name(line[1])
            if name in self.unit_sprites:
                self.unit_sprites[name].bop()

        # === MUSIC
        # Fade in this musical accompanienment
        elif line[0] == 'm':
            if line[1] in GC.MUSICDICT:
                logger.debug('Fade in %s', line[1])
                Engine.music_thread.fade_in(GC.MUSICDICT[line[1]])
            else:
                logger.warning("Couldn't find music matching %s", line[1])
        elif line[0] == 'mf':
            logger.debug('Fade out music')
            Engine.music_thread.fade_back()
        elif line[0] == 'sound':
            GC.SOUNDDICT[line[1]].play()
        elif line[0] == 'change_music':
            if gameStateObj.phase_music:
                # Phase name, musical piece
                gameStateObj.phase_music.change_music(line[1], line[2])
        elif line[0] == 'music_clear':
            logger.debug('Clear music stack')
            Engine.music_thread.fade_clear()
        # Music fade clear would just be
        # > music_clear
        # > mf

        # === HANDLE ITEMS
        # Give the optional unit an item or give the unit named in the line the item
        elif line[0] == 'give_item':
            # Find receiver
            if line[1] == '{unit}' and self.unit:
                receiver = self.unit
            elif line[1] == '{unit2}' and self.unit2:
                receiver = self.unit2
            elif line[1] == 'Convoy':
                receiver = None
            else:
                receiver = gameStateObj.get_unit(line[1])
            # Append item to list of units items
            if line[2] != "0":
                item = ItemMethods.itemparser(line[2], gameStateObj)
                if item:
                    self.add_item(receiver, item, gameStateObj, 'no_choice' not in line, 'no_banner' not in line)
                    tile = gameStateObj.map.tiles.get(self.tile_pos, None)
                    if self.unit and self.unit.team.startswith('enemy') and tile and tile.name == "Chest":
                        Action.do(Action.MakeItemDroppable(self.unit, item), gameStateObj)
                else:
                    logger.error("Could not find item matching %s", line[2])
            elif line[2] == "0" and 'no_banner' not in line:
                gameStateObj.banners.append(Banner.foundNothingBanner(receiver))
                gameStateObj.stateMachine.changeState('itemgain')
                self.current_state = "Paused"

        # Has the unit equip an item in their inventory if and only if that item is in their inventory by name
        elif line[0] == 'equip_item':
            receiver = self.get_unit(line[1], gameStateObj)
            if receiver:
                if len(line) > 2:
                    for item in receiver.items:
                        if item.id == line[2]:
                            receiver.equip(item, gameStateObj)
                            break
                else:
                    m = receiver.getMainWeapon()
                    receiver.equip(m, gameStateObj)

        # Give the player gold!
        elif line[0] == 'gold':
            if len(line) > 2 and line[2] != 'no_banner':
                party = line[2]
            else:
                party = gameStateObj.current_party
            if 'no_banner' in line:
                Action.execute(Action.GiveGold(int(line[1]), party), gameStateObj)
            else:
                Action.do(Action.GiveGold(int(line[1]), party), gameStateObj)
                self.current_state = "Paused"

        elif line[0] == 'remove_item':
            unit = self.get_unit(line[1], gameStateObj)
            if unit:
                valid_items = [item for item in unit.items if item.name == line[2] or item.id == line[2]]
                if valid_items:
                    item = valid_items[0]
                    Action.do(Action.DiscardItem(unit, item), gameStateObj)

        # Add a skill/status to a unit
        elif line[0] == 'give_skill':
            skill = StatusCatalog.statusparser(line[2], gameStateObj)
            unit = self.get_unit(line[1], gameStateObj)
            if unit and skill:
                Action.do(Action.AddStatus(unit, skill), gameStateObj)
                if 'no_display' not in line and 'no_banner' not in line:
                    gameStateObj.banners.append(Banner.gainedSkillBanner(unit, skill))
                    gameStateObj.stateMachine.changeState('itemgain')
                    self.current_state = "Paused"

        # Add a skill/status to a unit
        elif line[0] == 'remove_skill':
            unit = self.get_unit(line[1], gameStateObj)
            skill_id = line[2]
            if unit:
                Action.do(Action.RemoveStatus(unit, skill_id), gameStateObj)

        # Give exp to a unit
        elif line[0] == 'exp_gain' or line[0] == 'give_exp':
            exp = int(line[2])
            unit = self.get_unit(line[1], gameStateObj)
            if unit:
                gameStateObj.exp_gain_struct = (unit, exp, None, 'init')
                gameStateObj.stateMachine.changeState('exp_gain')
                self.current_state = "Paused"

        # Increment a single stat of a unit
        elif line[0] == 'inc_stat':
            unit = self.get_unit(line[1], gameStateObj)
            stat = line[2]
            amount = line[3]
            if unit:
                Action.do(Action.ChangeStat(unit, stat, amount), gameStateObj)

        # Modify fatigue of a unit
        elif line[0] == 'change_fatigue':
            amount = int(line[2])
            receiver = self.get_unit(line[1], gameStateObj)
            if receiver:
                Action.do(Action.ChangeFatigue(receiver, amount, True), gameStateObj)

        # destroy a destructible object
        elif line[0] == 'destroy':
            if len(line) > 1:
                pos = self.parse_pos(line[1], gameStateObj)
            else:
                pos = self.tile_pos
            tile_info = gameStateObj.map.tile_info_dict[pos]
            if 'Destructible' in tile_info:
                gameStateObj.map.destroy(gameStateObj.map.tiles[pos], gameStateObj)

        # === HANDLES UNITS ON MAP
        elif line[0] == 'add_unit':
            # Read input
            which_unit = line[1]
            to_which_position = line[2] if len(line) > 2 else None
            transition = line[3] if (len(line) > 3 and line[3]) else 'fade'
            placement = line[4] if (len(line) > 4 and line[4]) else 'give_up'
            order = True if len(line) > 5 else False
            self.add_unit(gameStateObj, metaDataObj, which_unit, to_which_position, transition, placement, shuffle=not order)
        elif line[0] == 'create_unit':
            # Read input
            which_unit = line[1]
            level = str(eval(line[2]))
            to_which_position = line[3] if len(line) > 3 else None
            transition = line[4] if (len(line) > 4 and line[4]) else 'fade'
            placement = line[5] if (len(line) > 5 and line[5]) else 'give_up'
            order = True if len(line) > 6 else False
            self.add_unit(gameStateObj, metaDataObj, which_unit, to_which_position, transition, placement, shuffle=not order, create=level)
        elif line[0] == 'move_unit':
            # Read input
            which_unit = line[1]
            to_which_position = line[2]
            transition = line[3] if (len(line) > 3 and line[3]) else 'normal'
            placement = line[4] if (len(line) > 4 and line[4]) else 'give_up'
            order = True if len(line) > 5 else False
            self.move_unit(gameStateObj, metaDataObj, which_unit, to_which_position, transition, placement, shuffle=not order)
        elif line[0] == 'start_move':
            self.current_state = "Paused"
            gameStateObj.stateMachine.changeState('movement')
            # Camera follow
            if len(line) > 1:
                unit = gameStateObj.get_unit(line[1])
                if unit:
                    gameStateObj.cursor.camera_follow = unit.id
        elif line[0] == 'interact_unit':
            # Read input
            attacker = line[1]
            defender = line[2]
            if len(line) > 3:
                event_combat = [command.lower() for command in reversed(line[3].split(','))]
            else:
                event_combat = ['--'] * 8  # Default event combat so that the Engine knows its an event combat
            self.interact_unit(gameStateObj, attacker, defender, event_combat)
        elif line[0] == 'remove_unit' or line[0] == 'kill_unit':
            # Read input
            which_unit = line[1]
            transition = line[2] if (len(line) > 2 and line[2]) else 'fade'
            event = (line[0] == 'remove_unit')
            self.remove_unit(gameStateObj, which_unit, transition, event=event)
        elif line[0] == 'resurrect_unit':
            unit = gameStateObj.get_unit(line[1])
            if unit and unit.dead:
                Action.do(Action.Resurrect(unit), gameStateObj)
            else:
                logger.warning('Unit %s either does not exist or was not dead!', line[1])
        elif line[0] == 'set_next_position':
            to_which_position = line[1]
            placement = line[2] if len(line) > 2 else 'give_up'
            order = True if len(line) > 3 else False
            self.find_next_position(gameStateObj, to_which_position, placement, shuffle=not order)
        elif line[0] == 'trigger':
            if line[1] in gameStateObj.triggers:
                trigger = gameStateObj.triggers[line[1]]
                for unit_id, (start, end) in trigger.units.items():
                    # print('In trigger:')
                    # print(unit_id, start, end)
                    # # First see if the unit is in reinforcements
                    # if unit_id in gameStateObj.allreinforcements:
                    #     self.add_unit(gameStateObj, metaDataObj, unit_id, None, 'fade', 'stack')
                    #     del gameStateObj.allreinforcements[unit_id]  # So we just move the unit now
                    #     self.move_unit(gameStateObj, metaDataObj, unit_id, end, 'normal', 'give_up')
                    # else:
                    #     self.move_unit(gameStateObj, metaDataObj, unit_id, end, 'normal', 'give_up')
                    unit = gameStateObj.get_unit_from_id(unit_id)
                    if not unit.position:
                        self.add_unit(gameStateObj, metaDataObj, unit_id, None, 'fade', 'stack')
                    self.move_unit(gameStateObj, metaDataObj, unit_id, end, 'normal', 'give_up')

                if trigger.units:
                    # Start move
                    self.current_state = "Paused"
                    gameStateObj.stateMachine.changeState('movement')

        # === HANDLE CURSOR
        elif line[0] == 'set_cursor' or line[0] == 'center_cursor':
            coord = self.get_cursor_coord(line[1], gameStateObj)
            if line[0] == 'center_cursor':
                gameStateObj.cursor.centerPosition(coord, gameStateObj)
            else:
                gameStateObj.cursor.setPosition(coord, gameStateObj)
            if 'immediate' not in line and not self.do_skip:
                gameStateObj.stateMachine.changeState('move_camera')
                self.current_state = "Paused"
        # Display Cursor 1 is yes, 0 is no
        elif line[0] == 'disp_cursor':
            choice_flag = int(line[1])
            if choice_flag:
                gameStateObj.cursor.drawState = 1
            else:
                gameStateObj.cursor.drawState = 0
        elif line[0] == 'flash_cursor':
            # Macro -- inserted backwards
            self.scene_lines.insert(self.scene_lines_index + 1, 'disp_cursor;0')
            self.scene_lines.insert(self.scene_lines_index + 1, 'wait;1000')
            self.scene_lines.insert(self.scene_lines_index + 1, 'disp_cursor;1')
            self.scene_lines.insert(self.scene_lines_index + 1, 'set_cursor;%s' % line[1])
        elif line[0] == 'set_camera':
            pos1 = self.parse_pos(line[1], gameStateObj)
            if len(line) > 2:
                pos2 = self.parse_pos(line[2], gameStateObj)
                gameStateObj.cameraOffset.center2(pos1, pos2)
            else:
                gameStateObj.cameraOffset.set_xy(pos1[0], pos1[1])
            if 'immediate' not in line and not self.do_skip:
                gameStateObj.stateMachine.changeState('move_camera')
                self.current_state = "Paused"
        elif line[0] == 'tutorial_mode':
            if line[1] == '0':
                gameStateObj.tutorial_mode_off()
            else:
                gameStateObj.tutorial_mode = line[1]
        elif line[0] == 'fake_cursor':
            coords = line[1:]
            for text_coord in coords:
                coord = self.parse_pos(text_coord, gameStateObj)
                gameStateObj.fake_cursors.append(Cursor.Cursor('Cursor', coord, fake=True))
        elif line[0] == 'remove_fake_cursors':
            gameStateObj.remove_fake_cursors()
        elif line[0] == 'set_camera_pan':
            choice_flag = int(line[1])
            if choice_flag:
                gameStateObj.cameraOffset.pan_flag = True
            else:
                gameStateObj.cameraOffset.pan_flag = False
        elif line[0] == 'map_pan':
            gameStateObj.cameraOffset.pan_flag = True
            gameStateObj.cameraOffset.map_pan(gameStateObj.map, gameStateObj.cursor.position)
            gameStateObj.stateMachine.changeState('move_camera')
            self.current_state = 'Paused'

        # === HANDLE OBJECTIVE
        elif line[0] == 'change_objective_display_name':
            Action.do(Action.ChangeObjective(display_name=line[1]), gameStateObj)
            # gameStateObj.objective.display_name_string = line[1]
        elif line[0] == 'change_objective_win_condition':
            Action.do(Action.ChangeObjective(win_condition=line[1]), gameStateObj)
            # gameStateObj.objective.win_condition_string = line[1]
        elif line[0] == 'change_objective_loss_condition':
            Action.do(Action.ChangeObjective(loss_condition=line[1]), gameStateObj)
            # gameStateObj.objective.loss_condition_string = line[1]
        elif line[0] == 'minimum_number_banner':
            gameStateObj.banners.append(Banner.tooFewUnitsBanner())
            gameStateObj.stateMachine.changeState('itemgain')
            self.current_state = "Paused"
        elif line[0] == 'switch_pulled_banner':
            gameStateObj.banners.append(Banner.switchPulledBanner())
            gameStateObj.stateMachine.changeState('itemgain')
            self.current_state = "Paused"
        elif line[0] == 'custom_banner':
            gameStateObj.banners.append(Banner.customBanner(line[1]))
            gameStateObj.stateMachine.changeState('itemgain')
            self.current_state = "Paused"
        elif line[0] == 'lose_game':
            gameStateObj.statedict['levelIsComplete'] = 'loss'
        elif line[0] == 'win_game':
            gameStateObj.statedict['levelIsComplete'] = 'win'
        elif line[0] == 'activate_turnwheel':
            if len(line) > 1: # Force turnwheel
                self.turnwheel_flag = 2
            else: # Optional Turnwheel
                self.turnwheel_flag = 1
        elif line[0] == 'battle_save':
            # Using a flag instead of just going to battle save state because if I save while
            # there's a dialogue state on the stack, the dialogue has a surface which crashes the save
            # This problem might not exist anymore, but...
            self.battle_save_flag = True
        elif line[0] == 'reset_state':
            self.reset_state_flag = True

        # === HANDLE TILE CHANGES -- These get put in the command list
        elif line[0] == 'set_origin':
            if len(line) > 1:
                gameStateObj.map.origin = self.parse_pos(line[1], gameStateObj)
            else:
                gameStateObj.map.origin = self.tile_pos
        # Change tile sprites. - command, pos, tile_sprite, size, transition
        elif line[0] == 'change_tile_sprite':
            coord = self.parse_pos(line[1], gameStateObj)
            transition = None
            if 'fade' in line or len(line) < 4:
                transition = 'fade'
            elif 'destroy' in line:
                transition = 'destroy'
            image_name = line[2]
            image = gameStateObj.map.loose_tile_sprites[image_name]
            size = image.get_width()//GC.TILEWIDTH, image.get_height()//GC.TILEHEIGHT
            Action.do(Action.ChangeTileSprite(coord, image_name, size, transition), gameStateObj)
        elif line[0] == 'layer_tile_sprite':
            layer = int(line[1])
            coord = self.parse_pos(line[2], gameStateObj)
            image_filename = line[3]
            Action.do(Action.LayerTileSprite(layer, coord, image_filename), gameStateObj)
            if len(line) > 4:
                Action.do(Action.LayerTerrain(layer, coord, line[4]), gameStateObj)
                self.reset_boundary_manager = True
        elif line[0] == 'layer_terrain':
            layer = int(line[1])
            coord = self.parse_pos(line[2], gameStateObj)
            image_filename = line[3]
            Action.do(Action.LayerTerrain(layer, coord, image_filename), gameStateObj)
            self.reset_boundary_manager = True
        elif line[0] == 'show_layer':
            layer = int(line[1])
            transition = line[2] if len(line) > 2 else 'fade'
            Action.do(Action.ShowLayer(layer, transition), gameStateObj)
            self.reset_boundary_manager = True
        elif line[0] == 'hide_layer':
            layer = int(line[1])
            transition = line[2] if len(line) > 2 else 'fade'
            Action.do(Action.HideLayer(layer, transition), gameStateObj)
            self.reset_boundary_manager = True
        elif line[0] == 'clear_layer':
            layer = int(line[1])
            Action.do(Action.ClearLayer(layer), gameStateObj)
        # Change one tile
        elif line[0] == 'replace_tile':
            pos_list = self.get_position(line[1], gameStateObj)
            tile_id = int(line[2])
            Action.do(Action.ReplaceTiles(pos_list, tile_id), gameStateObj)
            self.reset_boundary_manager = True
        # Change area of tile (must include pic instead of id)
        elif line[0] == 'area_replace_tile':
            coord = self.parse_pos(line[1], gameStateObj)
            image_fp = line[2]
            Action.do(Action.AreaReplaceTiles(coord, image_fp), gameStateObj)
            self.reset_boundary_manager = True
        # Change one tile's information
        elif line[0] == 'set_tile_info':
            coord = self.parse_pos(line[1], gameStateObj)
            property_list = line[2:] if len(line) > 2 else None
            if property_list:
                for tile_property in property_list:
                    Action.do(Action.AddTileProperty(coord, tile_property.split('=')), gameStateObj)
            else:
                for tile_property_name in list(gameStateObj.map.tile_info_dict[coord].keys()):
                    Action.do(Action.RemoveTileProperty(coord, tile_property_name), gameStateObj)
        elif line[0] == 'add_tile_property':
            coord = self.parse_pos(line[1], gameStateObj)
            tile_property = line[2]
            Action.do(Action.AddTileProperty(coord, tile_property.split('=')), gameStateObj)
        elif line[0] == 'remove_tile_property':
            coord = self.parse_pos(line[1], gameStateObj)
            tile_property_name = line[2]
            Action.do(Action.RemoveTileProperty(coord, tile_property_name), gameStateObj)
        # Add weather
        elif line[0] == 'add_weather':
            Action.do(Action.AddWeather(line[1]), gameStateObj)
        # Remove weather
        elif line[0] == 'remove_weather':
            Action.do(Action.RemoveWeather(line[1]), gameStateObj)
        # Add global status
        elif line[0] == 'add_global_status':
            Action.do(Action.AddGlobalStatus(line[1]), gameStateObj)
        # Remove global status
        elif line[0] == 'remove_global_status':
            Action.do(Action.RemoveGlobalStatus(line[1]), gameStateObj)
        # Load submap
        elif line[0] == 'load_submap':
            gameStateObj.load_submap(line[1])
        # Remove submap
        elif line[0] == 'close_submap':
            gameStateObj.close_submap()

        # === CLEANUP
        elif line[0] == 'arrange_formation':
            force = (len(line) > 1)
            if force:  # force arrange
                player_units = gameStateObj.get_units_in_party(gameStateObj.current_party)
                formation_spots = [pos for pos, value in gameStateObj.map.tile_info_dict.items()
                                   if 'Formation' in value]
            else:
                player_units = [unit for unit in gameStateObj.get_units_in_party(gameStateObj.current_party) if not unit.position]
                formation_spots = [pos for pos, value in gameStateObj.map.tile_info_dict.items()
                                   if 'Formation' in value and not gameStateObj.grid_manager.get_unit_node(pos)]
            
            if cf.CONSTANTS['fatigue'] and gameStateObj.game_constants['Fatigue'] == 1:
                player_units = [unit for unit in player_units if unit.fatigue < GC.EQUATIONS.get_max_fatigue(unit)]

            for index, unit in enumerate(player_units[:len(formation_spots)]):
                if force:
                    Action.do(Action.LeaveMap(unit), gameStateObj)
                new_pos = formation_spots[index]
                Action.do(Action.ArriveOnMap(unit, new_pos), gameStateObj)
        elif line[0] == 'reset_units':
            for unit in gameStateObj.allunits:
                Action.do(Action.Reset(unit), gameStateObj)
        elif line[0] == 'reset_unit':
            unit = self.get_unit(line[1], gameStateObj)
            Action.do(Action.Reset(unit), gameStateObj)
        elif line[0] == 'unit_wait':
            unit = self.get_unit(line[1], gameStateObj)
            unit.wait(gameStateObj)
        elif line[0] == 'remove_enemies':
            exception = line[1] if len(line) > 1 else None
            units_to_remove = [unit for unit in gameStateObj.allunits if unit.position and unit.team.startswith("enemy") and unit.id != exception]
            # Remove enemies
            for unit in units_to_remove:
                Action.do(Action.LeaveMap(unit), gameStateObj)
        elif line[0] == 'remove_all':
            for unit in [unit for unit in gameStateObj.allunits if unit.position]:
                Action.do(Action.LeaveMap(unit), gameStateObj)
        elif line[0] == 'kill_all':
            call_out = line[1] if len(line) > 1 else None
            for unit in gameStateObj.allunits:
                if unit.position and unit.team == call_out:
                    unit.isDying = True
                    gameStateObj.stateMachine.changeState('dying')

        # === GAME CONSTANTS
        # should be remembered for map
        elif line[0] == 'set_level_constant':
            if len(line) > 2:
                Action.do(Action.ChangeLevelConstant(line[1], int(eval(line[2]))), gameStateObj)
            else:
                Action.do(Action.ChangeLevelConstant(line[1], 1), gameStateObj)
        elif line[0] == 'inc_level_constant':
            if len(line) > 2:
                Action.do(Action.ChangeLevelConstant(line[1], gameStateObj.level_constants[line[1]] + int(eval(line[2]))), gameStateObj)
            else:
                Action.do(Action.ChangeLevelConstant(line[1], gameStateObj.level_constants[line[1]] + 1), gameStateObj)
        # should be remembered for all game
        elif line[0] == 'set_game_constant':
            if len(line) > 2:
                Action.do(Action.ChangeGameConstant(line[1], int(eval(line[2]))), gameStateObj)
            else:
                Action.do(Action.ChangeGameConstant(line[1], 1), gameStateObj)
        elif line[0] == 'inc_game_constant':
            if len(line) > 2:
                Action.do(Action.ChangeGameConstant(line[1], gameStateObj.game_constants[line[1]] + int(eval(line[2]))), gameStateObj)
            else:
                Action.do(Action.ChangeGameConstant(line[1], gameStateObj.game_constants[line[1]] + 1), gameStateObj)
        elif line[0] == 'unlock_lore':
            gameStateObj.unlocked_lore.append(line[1])
        elif line[0] == 'remove_lore':
            if line[1] in gameStateObj.unlocked_lore:
                del gameStateObj.unlocked_lore[line[1]]
        elif line[0] == 'add_to_market':
            gameStateObj.market_items.add(line[1])
        elif line[0] == 'remove_from_market':
            gameStateObj.market_items.discard(line[1])

        # === TRANSITIONS
        elif line[0] == 't': # Handle transition
            mode = line[1]
            if len(line) > 2 and line[2]:
                self.transition_color = tuple([int(num) for num in line[2].split(',')])
            if len(line) > 3:
                self.transition_speed = int(line[3])
            if mode == '1':
                self.transition_state = 1
                self.transition_transparency = 0
            elif mode == '2':
                self.transition_state = 2
                self.transition_transparency = 255
            elif mode == '3':
                self.transition_state = 1
                self.transition_transparency = 0
                self.transition_speed = 30 * GC.FRAMERATE
            elif mode == '4':
                self.transition_state = 2
                self.transition_transparency = 255
                self.transition_speed = 30 * GC.FRAMERATE
            self.transition_last_update = Engine.get_time()
            self.current_state = "Transitioning"

        # === CHANGING UNITS
        elif line[0] == 'change_name':
            unit = self.get_unit(line[1], gameStateObj)
            new_name = line[2]
            if unit:
                Action.do(Action.ChangeName(unit, new_name), gameStateObj)
            else:
                print("Cannot find unit with name/id: %s" % line[1])
        elif line[0] == 'change_portrait':
            unit = self.get_unit(line[1], gameStateObj)
            portrait_id = line[2]
            if unit and portrait_id in GC.PORTRAITDICT:
                Action.do(Action.ChangePortrait(unit, portrait_id), gameStateObj)
            elif unit:
                print("%s not in portrait dictionary. Need to assign blink and mouth positions to pic" % (portrait_id))
            else:
                print("Cannot find unit with name/id: %s" % line[1])
        elif line[0] == 'convert':
            assert len(line) == 3
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    Action.do(Action.ChangeTeam(unit, line[2]), gameStateObj)
        elif line[0] == 'change_ai':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    Action.do(Action.ChangeAI(unit, line[2]), gameStateObj)
        elif line[0] == 'change_party':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    Action.do(Action.ChangeParty(unit, line[2]), gameStateObj)
        elif line[0] == 'add_tag':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    Action.do(Action.AddTag(unit, line[2]), gameStateObj)
        elif line[0] == 'remove_tag':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    Action.do(Action.RemoveTag(unit, line[2]), gameStateObj)
        elif line[0] == 'merge_parties':
            host, guest = line[1], line[2]
            for unit in gameStateObj.allunits:
                if unit.party == guest:
                    Action.do(Action.ChangeParty(unit, host), gameStateObj)
            # Merge items
            if guest in gameStateObj._convoy and host in gameStateObj._convoy:
                for item in gameStateObj._convoy[guest]:
                    gameStateObj._convoy[host].append(item)
                gameStateObj._convoy[guest] = []
            # Merge money
            if guest in gameStateObj._money and host in gameStateObj._money:
                gameStateObj._money[host] += gameStateObj._money[guest]
                gameStateObj._money[guest] = 0
        elif line[0] == 'clear_turnwheel_history':
            gameStateObj.action_log.reset_first_free_action()

        # === HANDLE TALKING
        elif line[0] == 'add_talk':
            # Add to dictionary
            Action.do(Action.AddTalk(line[1], line[2]), gameStateObj)
        elif line[0] == 'remove_talk':
            if (line[1], line[2]) in gameStateObj.talk_options:
                Action.do(Action.RemoveTalk(line[1], line[2]), gameStateObj)
        elif line[0] == 'set_base_convo':
            # Add to dictionary
            gameStateObj.base_conversations[line[1]] = True
        elif line[0] == 'remove_base_convo':
            if line[1] in gameStateObj.base_conversations:
                del gameStateObj.base_conversations[line[1]]
        elif line[0] == 'grey_base_convo':
            if line[1] in gameStateObj.base_conversations:
                gameStateObj.base_conversations[line[1]] = False
        elif line[0] == 'inc_support':
            edge = gameStateObj.support.get_edge(self.unit.id, self.unit2.id)
            if edge and gameStateObj.support.can_support(self.unit.id, self.unit2.id) and \
                    edge.support_level == self.name:  # Only increment if we haven't read this before (IE we can support)
                Action.do(Action.IncrementSupportLevel(self.unit.id, self.unit2.id), gameStateObj)
        elif line[0] == 'choice':
            name = line[1]
            header = line[2]
            options = line[3].split(',')
            # Check for arrangement if specified.
            if len(line) > 4 and line[4] in ('v', 'vertical', 'h', 'horizontal'):
                arrangement = line[4]
            else:
                arrangement = 'h'
            # Save results to the game constants
            gameStateObj.game_constants['choice'] = (name, header, options, arrangement)
            self.current_state = "Paused"
            gameStateObj.stateMachine.changeState('dialog_options')

        # === DIALOGUE BOX
        # Add line of text
        elif line[0] == 's':
            self.evaluate_evals(line, gameStateObj)
            self.add_dialog(line)
        # === CINEMATIC TEXT
        elif line[0] == 'cinematic':
            self.add_cinematic(line)
        # === CREDITS BOX
        elif line[0] == 'credits':
            self.add_credits(line)
        # === ENDINGS BOX
        elif line[0] == 'endings':
            self.add_ending(line, gameStateObj)
        # === LOCATION CARD
        elif line[0] == 'location_card':
            self.add_location_card(line)
        # === Pop dialog off top
        elif line[0] == 'pop_dialog':
            if self.dialog:
                self.dialog.pop()
        elif line[0] == 'clear_dialog':
            self.dialog = []

        # === Show Victory Screen
        elif line[0] == 'victory_screen':
            gameStateObj.stateMachine.changeState('victory')
            self.current_state = 'Paused'
        # === ROLL CREDITS
        elif line[0] == 'roll_credits':
            gameStateObj.stateMachine.changeState('credits')
            self.current_state = "Paused"
        # === Display Records
        elif line[0] == 'records_display':
            gameStateObj.stateMachine.changeState('base_records')
            self.current_state = "Paused"

        # logger.info('Time taken: %s', Engine.get_true_time() - time)

    def evaluate_evals(self, line, gameStateObj):
        # Evaluate evals
        if '{eval:' in line[2]:
            dialog = line[2][:]
            last_index = None
            add = False
            command = []
            # Traverse backwards so we don't mess up the indexing
            for i, char in reversed(list(enumerate(dialog))):
                if char == '}':
                    last_index = i
                    add = True
                elif char == '{':
                    command = ''.join(command)
                    if command.startswith('eval:'):
                        to_eval = command[5:]
                        result = str(eval(to_eval))
                        line[2] = line[2][:i] + result + line[2][last_index+1:]
                    add = False
                    command = []
                elif add:
                    command.insert(0, char)
        return line[2]

    def add_dialog(self, line):
        speaker = self.get_name(line[1])
        tail = None
        waiting_cursor = True
        transition = False
        thought_bubble = False
        line[2] = line[2].replace('|', '{w}{br}')
        if 'hint' in line:
            if 'auto' in line:
                position = GC.WINWIDTH//4, GC.WINHEIGHT//4
                size = GC.WINWIDTH//2 + 8, GC.WINHEIGHT//2
            else:
                position = [int(line[3]), int(line[4])]
                size = ((int(line[5]) if line[5] else GC.WINWIDTH//2 + 8), GC.WINHEIGHT//2)
            back_surf = 'Parchment_Window'
            font = 'convo_black'
            num_lines = 4
        elif 'narration' in line:
            if 'auto' in line:
                position = 4, 110
                size = 232, 48
            elif 'auto_top' in line:
                position = 4, 2
                size = 232, 48
            else:
                position = [int(line[3]), int(line[4])]
                size = int(line[5]) if len(line) > 5 else 144, 48
            back_surf = 'BaseMenuBackground'
            font = 'convo_white'
            num_lines = 2
        elif 'cinematic' in line:
            position = 'center'
            size = GC.WINWIDTH, GC.WINHEIGHT
            back_surf = 'ActualTransparent'
            font = 'chapter_grey'
            num_lines = 5
            waiting_cursor = False
        else:
            owner = self.unit_sprites[speaker] if speaker in self.unit_sprites else None
            # --- Quick fix
            if len(line) == 3:
                # s, speaker, text -- Assume we forgot {w} auto
                line[2] += '{w}'
                line.append('auto')

            if 'auto' in line:
                position, size = self.auto_dialog_box(line[2], owner)
            else:
                position = [int(line[3]), int(line[4])]
                size = int(line[5]) if len(line) > 5 else 144, 48
            if 'noir' in line:
                back_surf = 'NoirMessageWindow'
            else:
                back_surf = 'MessageWindowBackground'
            if 'thought_bubble' in line:
                thought_bubble = True
            if 'noir' in line:
                tail = None
            elif thought_bubble:
                tail = GC.IMAGESDICT['ThoughtWindowTail'] if owner else None
            else:
                tail = GC.IMAGESDICT['MessageWindowTail'] if owner else None
            font = 'convo_black'
            if 'noir' in line:
                font = 'convo_white'
            num_lines = 2
            transition = True
        self.dialog.append(Dialog(line[2], speaker, position, size, font, back_surf, tail, num_lines,
                                  waiting_cursor_flag=waiting_cursor, transition=transition,
                                  unit_sprites=self.unit_sprites, slow_flag=3 if 'slow' in line else 1,
                                  talk=not thought_bubble, hold='hold' in line))

        self.reset_unit_sprites()
        if self.dialog[-1].owner in self.unit_sprites:
            self.unit_sprites[self.dialog[-1].owner].priority = self.priority_counter
            self.priority_counter += 1

        # Stop processing
        self.current_state = "Displaying"

    def auto_dialog_box(self, dialogue, owner):
        num_lines = 2
        if owner:
            size = TextChunk.command_chunk(dialogue, num_lines)
            desired_center = self.determine_desired_center(owner.position[0])
            pos_x = Utility.clamp(desired_center - size[0]//2, 8, GC.WINWIDTH - 8 - size[0])
            if pos_x % 8 != 0:
                pos_x += 4
            pos_y = 24
        else:  # Default value at bottom of screen
            pos_x = 4
            pos_y = 110
            size = 232, 48
        return (pos_x, pos_y), size

    def determine_desired_center(self, position):
        if position < 0:  # FarLeft
            return 8
        elif position < 24:  # Left
            return 80
        elif position < 56:  # MidLeft
            return 104
        elif position > 144:  # FarRight
            return 232
        elif position > 120:  # Right
            return 152
        elif position > 96:  # MidRight
            return 128
        else:
            return 120

    def add_credits(self, line):
        title = line[1]
        text = line[2:]
        if 'wait' in text:
            text.remove('wait')
            wait = True
        else:
            wait = False
        if 'center' in text:
            text.remove('center')
            center = True
        else:
            center = False
        title_font = 'credittitle_white'
        font = 'credit_white'

        new_credits = Credits(title, text, title_font, font, wait, center)
        # Wait a certain amount of time before next one
        self.waittime = new_credits.determine_wait()
        self.last_wait_update = Engine.get_time()
        self.current_state = "Waiting"

        self.dialog.append(new_credits)

    def add_cinematic(self, line):
        text = line[1]
        if len(line) > 2:
            flags = line[2:]
        else:
            flags = []
        font = 'chapter_white'

        new_cinematic = Cinematic(text, font, flags=flags)
        # Wait a certain amount of time before next one
        if 'infinite_wait' not in flags:
            self.waittime = new_cinematic.total_wait()
            self.last_wait_update = Engine.get_time()
            self.current_state = "Waiting"

        self.dialog.append(new_cinematic)

    def add_location_card(self, line):
        text = line[1]
        font = 'text_white'
        location_card = LocationCard(text, font)

        self.waittime = 2000
        self.last_wait_update = Engine.get_time()
        self.current_state = "Waiting"

        self.dialog.append(location_card)

    def add_ending(self, line, gameStateObj):
        portrait = line[1]
        title = line[2]
        text = line[3]
        font = 'text_white'

        new_ending = EndingsDisplay(self, portrait, title, text, gameStateObj.statistics, font)

        self.dialog.append(new_ending)

        # Stop processing
        self.current_state = "Displaying"

    def draw(self, surf):
        # Draw if background exists
        if self.background:
            self.background.draw(surf)

        # Draw if midground exists
        if self.midground:
            if self.midground.draw(surf) == 'Done':
                self.midground = None  # Done
                self.current_state = "Processing" # Done waiting. Head back to processing

        # Update unit sprites -- if results in true, delete the unit sprite. -- faciliates 'r' command fade out
        delete = [key for key, unit in self.unit_sprites.items() if unit.update()]
        for key in delete:
            del self.unit_sprites[key]

        # === SCENE SPRITES ===
        # Blit sprites, sort them by their priority (ascending, so 2 is pasted after and on top of 1)
        sorted_sprites = sorted([unit for key, unit in self.unit_sprites.items()], key=lambda x: x.priority)
        for unit in sorted_sprites:
            unit.draw(surf)

        if self.dialog and (self.current_state == "Displaying" or self.dialog[-1].hold):# Draw text (Don't draw text while transitioning)
            for dialog in reversed(self.dialog):
                dialog.draw(surf)
                if dialog.solo_flag:
                    break

        if self.foreground:
            if self.foreground.draw(surf) == 'Done':
                self.foreground = None  # Done
                self.current_state = "Processing" # Done waiting. Head back to processing

        s = GC.IMAGESDICT['BlackBackground'].copy()
        if len(self.transition_color) == 3:
            s.fill((*self.transition_color, self.transition_transparency))
        else:
            s.fill((0, 0, 0, self.transition_transparency))
        surf.blit(s, (0, 0))

    def add_unit_sprite(self, gameStateObj, line, transition=False):
        name = self.get_name(line[1])
        portrait_id = self.get_portrait_id(line[1], gameStateObj)
        if name in self.unit_sprites and not self.unit_sprites[name].remove_flag:
            return False
        if line[2] in hardset_positions:
            position = [hardset_positions[line[2]], 80]
            mirrorflag = True if line[2] in ('OffscreenLeft', 'FarLeft', 'Left', 'MidLeft') else False
            if 'mirror' in line:
                mirrorflag = not mirrorflag
        else:
            position = [int(line[2]), int(line[3])]
            mirrorflag = True if 'mirror' in line else False
        # Priority
        if 'LowPriority' in line:
            priority = self.priority_counter - 1000
        else:
            priority = self.priority_counter
        self.priority_counter += 1
        # Expressions
        legal_expressions = ("Smile", "OpenEyes", "CloseEyes", "HalfCloseEyes")
        expression = []
        for exp in legal_expressions:
            if exp in line:
                expression.append(exp)
        # Slide
        if 'SlideRight' in line:
            slide = 'right'
        elif 'SlideLeft' in line:
            slide = 'left'
        else:
            slide = None
        # Narration
        if 'Narration' in line:
            position[1] = 30
        # Blink/Mouth positions
        assert portrait_id in GC.PORTRAITDICT, "%s not in portrait dictionary. Need to assign blink and mouth positions to pic"%(portrait_id)
        blink = GC.PORTRAITDICT[portrait_id]['blink']
        mouth = GC.PORTRAITDICT[portrait_id]['mouth']
        self.unit_sprites[name] = UnitPortrait.UnitPortrait(
            portrait_name=portrait_id, blink_position=blink, mouth_position=mouth, transition=transition,
            position=position, priority=priority, mirror=mirrorflag, expression=expression, slide=slide)

        return True

    def reset_unit_sprites(self):
        for key, unit in self.unit_sprites.items():
            unit.stop_talking()

    def dialog_unpause(self):
        # Removes waiting from dialog
        if not self.dialog[-1].done and not self.dialog[-1].is_done():
            if self.dialog[-1].talk and self.dialog[-1].owner in self.unit_sprites:
                self.unit_sprites[self.dialog[-1].owner].talk()
        self.dialog[-1].waiting = False

    def add_unit(self, gameStateObj, metaDataObj, which_unit, new_pos, transition, placement, shuffle=True, create=None):
        from Code.SaveLoad import create_unit
        # Find unit
        if create:
            unitLine = gameStateObj.prefabs.get(which_unit)
            if not unitLine:
                logger.warning('Could not find %s in unitLine' % which_unit)
                return
            new_unitLine = unitLine[:]
            new_unitLine.insert(4, create)
            unit = create_unit(new_unitLine, gameStateObj.allunits, gameStateObj.factions, gameStateObj.allreinforcements, gameStateObj)
            position = self.parse_pos(unitLine[5], gameStateObj)
        else:
            context = gameStateObj.allreinforcements.get(which_unit)
            #print(gameStateObj.allreinforcements)
            #print(which_unit)
            #print(context)
            if context:
                u_id, position = context
                unit = gameStateObj.get_unit_from_id(u_id)
            else:
                unit = gameStateObj.get_unit_from_id(which_unit)
                position = None
                if not unit:
                    logger.warning('Could not find %s', which_unit)
                    return
            # print(unit.id, position)
            if unit.dead:
                logger.warning('Unit %s is dead!', unit.id)
                return
            if unit.position:
                logger.warning("Unit %s already has a position!", unit.id)
                return
        if not unit:
            logger.error('Could not find unit %s', which_unit)
            return

        # Determine where the unit will appear
        # If none, then use position in load
        if not new_pos:
            new_pos = [position]
        elif isinstance(new_pos, tuple):
            new_pos = [new_pos]
        # Using prev defined reinforcement positions
        elif new_pos.startswith('r'):
            new_pos = self.get_rein_position(new_pos[1:], gameStateObj)
        # Using next position
        elif new_pos == 'next':
            new_pos = [self.next_position]
        # If coord, use coord
        elif ',' in new_pos:
            new_pos = self.get_position(new_pos, gameStateObj)
        # If name, then we want to find a point adjacent to that characters position
        else:
            new_char = gameStateObj.get_unit_from_id(new_pos)
            if new_char:
                new_pos = [new_char.position]
            else:
                logger.error('Could not find unit %s', new_pos)
                return

        #print("Add Unit: New Pos")
        #print(new_pos)
        if None in new_pos:
            #print(context)
            #print(which_unit)
            logger.warning('Position for "add_unit" is not set!')
            return

        # Shuffle positions if necessary
        if shuffle:
            static_random.shuffle(new_pos)

        # Determine which positions I can't move onto
        bad_pos = {bad_unit.position for bad_unit in gameStateObj.allunits if bad_unit.position}

        final_pos = self.get_final_pos(gameStateObj, placement, new_pos, bad_pos)
        if not final_pos:
            logger.warning('Could not add to position %s', new_pos)
            return

        if self.do_skip:
            transition = 'immediate'
        # Now we have final pos
        if transition == 'warp':
            Action.do(Action.WarpIn(unit, final_pos), gameStateObj)
        elif transition == 'fade':
            Action.do(Action.FadeIn(unit, final_pos), gameStateObj)
        else:  # immediate
            Action.do(Action.ArriveOnMap(unit, final_pos), gameStateObj)

    def move_unit(self, gameStateObj, metaDataObj, which_unit, new_pos, transition, placement, shuffle=True):
        # Find unit
        if which_unit == '{unit}':
            unit = self.unit
        elif which_unit == '{unit2}' and self.unit2:
            unit = self.unit2
        elif isinstance(which_unit, int):
            unit = gameStateObj.get_unit_from_id(which_unit)
        elif ',' in which_unit:
            unit = gameStateObj.get_unit_from_pos(self.parse_pos(which_unit, gameStateObj))
        else:
            unit = gameStateObj.get_unit(which_unit)
        if not unit:
            logger.error('Move unit routine could not find unit %s', which_unit)
            return
        if not unit.position:
            logger.error('Unit does not have position! %s %s', which_unit, unit.name)
            print('Unit does not have position! %s %s' %(which_unit, unit.name))
            gameStateObj.display_all_units()
            return

        # Determine available positions to move to
        # Using prev defined reinforcement positions
        if isinstance(new_pos, tuple):
            new_pos = [new_pos]
        elif new_pos.startswith('r'):
            new_pos = self.get_rein_position(new_pos[1:], gameStateObj)
        # Using next position
        elif new_pos == 'next':
            new_pos = [self.next_position]
        # Using prev position
        elif new_pos == 'prev_pos':
            new_pos = [gameStateObj.action_log.get_previous_position(unit)]
        # If coord, use coord
        elif ',' in new_pos:
            new_pos = self.get_position(new_pos, gameStateObj)
        # If name, then we want to find a point adjacent to that characters position
        else:
            target = gameStateObj.get_unit_from_id(new_pos)
            if target and target.position:
                new_pos = [target.position]
            else:
                logger.warning('Could not find target %s. Target is not on map.', new_pos)
                return

        # Shuffle positions if necessary
        if shuffle:
            static_random.shuffle(new_pos)

        # Determine which positions I can't move onto
        bad_pos = {bad_unit.position for bad_unit in gameStateObj.allunits if bad_unit.position}

        final_pos = self.get_final_pos(gameStateObj, placement, new_pos, bad_pos)
        if not final_pos:
            logger.warning('Could not move to position %s', new_pos)
            return

        if self.do_skip:
            transition = 'immediate'
        if transition == 'normal':
            move_path = unit.getPath(gameStateObj, final_pos)
            Action.do(Action.Move(unit, final_pos, move_path), gameStateObj)
        elif transition == 'warp':
            Action.do(Action.Warp(unit, final_pos), gameStateObj)
        elif transition == 'fade':
            Action.do(Action.FadeMove(unit, final_pos), gameStateObj)
        elif transition == 'immediate':
            Action.do(Action.Teleport(unit, final_pos), gameStateObj)

    def remove_unit(self, gameStateObj, which_unit, transition, event=True):
        # Find unit
        if which_unit == '{unit}':
            unit = self.unit
        elif which_unit == '{unit2}' and self.unit2:
            unit = self.unit2
        elif ',' in which_unit:
            unit = gameStateObj.get_unit_from_pos(self.parse_pos(which_unit, gameStateObj))
        else:
            unit = gameStateObj.get_unit(which_unit)
        if not unit:
            logger.error('Remove unit routine could not find unit %s', which_unit)
            return
        if not unit.position:
            logger.warning('Remove unit routine - No position')
            return

        if self.do_skip:
            transition = 'immediate'
        if transition == 'warp':
            unit.sprite.set_transition('warp_out')
        elif transition == 'fade':
            if event:
                if gameStateObj.map.on_border(unit.position):
                    unit.sprite.spriteOffset = gameStateObj.map.which_border(unit.position)
                    unit.sprite.set_transition('fake_out')
                else:
                    unit.sprite.set_transition('fade_out_event')
            else:
                unit.sprite.set_transition('fade_out')
        elif transition == 'immediate':
            unit.die(gameStateObj, event=event)

    def interact_unit(self, gameStateObj, attacker, defender, event_combat=False):
        from . import Interaction
        if ',' in attacker:
            attacker = gameStateObj.get_unit_from_pos(self.parse_pos(attacker, gameStateObj))
        else:
            attacker = self.get_unit(attacker, gameStateObj)
        if not attacker:
            logger.error('Interact unit routine could not find %s', attacker)
            return

        if ',' in defender:
            def_pos = self.parse_pos(defender, gameStateObj)
        else:
            defender = self.get_unit(defender, gameStateObj)
            if not defender:
                logger.error('Interact unit routine could not find %s', defender)
                return
            if defender.position:
                def_pos = defender.position
            else:
                logger.error('Interact unit routine cannot target a unit without a position')
                return

        item = attacker.items[0]
        if not item:
            logger.warning("Attacker does not have a valid item to use in first slot.")
            return
        defender, splash = Interaction.convert_positions(gameStateObj, attacker, attacker.position, def_pos, item)
        gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, attacker, defender, def_pos, splash, item, event_combat=event_combat)
        gameStateObj.stateMachine.changeState('combat')
        self.current_state = "Paused"

    def find_next_position(self, gameStateObj, new_pos, placement, shuffle=True):
        # Determine where the unit will appear
        # Using prev defined reinforcement positions
        if new_pos.startswith('r'):
            new_pos = self.get_rein_position(new_pos[1:], gameStateObj)
        # If coord, use coord
        elif ',' in new_pos:
            new_pos = self.get_position(new_pos, gameStateObj)
        # If name, then we want to find a point adjacent to that characters position
        else:
            if new_pos in gameStateObj.allreinforcements:
                new_pos = [gameStateObj.allreinforcements[new_pos][1]]
            else:
                new_pos = [gameStateObj.get_unit_from_id(new_pos).position]

        # Shuffle positions if necessary
        if shuffle:
            static_random.shuffle(new_pos)

        # Determine which positions I can't move onto
        bad_pos = {bad_unit.position for bad_unit in gameStateObj.allunits if bad_unit.position}

        self.next_position = self.get_final_pos(gameStateObj, placement, new_pos, bad_pos)

    def get_final_pos(self, gameStateObj, placement, new_pos, bad_pos):
        if placement == 'give_up':
            for pos in new_pos:
                if pos not in bad_pos and gameStateObj.map.check_bounds(pos):
                    return pos
        elif placement == 'stack':
            for pos in new_pos:
                if pos not in bad_pos and gameStateObj.map.check_bounds(pos):
                    return pos
            # If we couldn't find a good position to place this unit, just place it anywhere
            return new_pos[0]
        elif placement == 'closest':
            return self.get_closest(new_pos, bad_pos, gameStateObj)
        elif placement == 'closest_f':
            return self.get_closest(new_pos, bad_pos, gameStateObj, flying=True)
        elif placement == 'push':
            for pos in new_pos:
                if pos not in bad_pos and gameStateObj.map.check_bounds(pos):
                    return pos
            # If we couldn't find a good position to place this unit, just push the dude out
            pos = new_pos[0]
            if gameStateObj.map.check_bounds(pos):
                other_unit = gameStateObj.get_unit_from_pos(pos)
                pos = other_unit.get_nearest_open_space(gameStateObj)
                return pos
            else:
                return None
        else:
            logger.warning('%s placement not supported.', placement)

    def get_closest(self, new_pos, bad_pos, gameStateObj, flying=False):
        r = 0
        while r < 10:
            for x in range(-r, r + 1):
                for y in [(r - abs(x)), -(r - abs(x))]:
                    for pos in new_pos:
                        check_pos = pos[0] + x, pos[1] + y
                        if check_pos not in bad_pos and gameStateObj.map.check_bounds(check_pos) and \
                           (gameStateObj.map.tiles[check_pos].get_mcost(0) < 5 or
                           (flying and gameStateObj.map.tiles[check_pos].get_mcost(cf.CONSTANTS['flying_mcost_column']) < 5)):
                            return check_pos
            r += 1

    def get_id(self, spec, gameStateObj):
        if "," in spec: # If is a coordinate
            return self.parse_pos(spec, gameStateObj)
        else:
            return spec

    def get_cursor_coord(self, pos, gameStateObj):
        if "," in pos: # If is a coordinate
            return self.parse_pos(pos, gameStateObj)
        elif pos == 'next' and self.next_position:
            return self.next_position
        elif pos == '{unit}' and self.unit:
            return self.unit.position
        elif pos == '{unit2}' and self.unit2:
            return self.unit2.position
        else:
            for unit in gameStateObj.allunits:
                if (unit.id == pos or unit.event_id == pos) and unit.position:
                    return unit.position
            else:
                logger.error("Couldn't find unit %s", pos)
                return

    def parse_pos(self, pos, gameStateObj):
        if pos.startswith('o'):
            coord = [int(num) for num in pos[1:].split(',')]
            if gameStateObj.map.origin:
                return (coord[0] + gameStateObj.map.origin[0], coord[1] + gameStateObj.map.origin[1])
        return tuple([int(num) for num in pos.split(',')])

    def get_position(self, pos_line, gameStateObj):
        position_list = [self.parse_pos(coord, gameStateObj) for coord in pos_line.split('.')]
        return position_list

    def get_rein_position(self, pos_line, gameStateObj):
        rein_positions = [position for position, value in gameStateObj.map.tile_info_dict.items() if 'Reinforcement' in value]
        position_list = [position for position in rein_positions if gameStateObj.map.tile_info_dict[position]['Reinforcement'] == pos_line]
        return position_list

    def get_name(self, name):
        if name == '{unit}':
            return self.unit.name
        elif name == '{unit2}' and self.unit2:
            return self.unit2.name
        else:
            return name

    def get_portrait_id(self, name, gameStateObj):
        if name == '{unit}':
            return self.unit.portrait_id
        elif name == '{unit2}' and self.unit2:
            return self.unit2.portrait_id
        else:
            unit = gameStateObj.get_unit(name)
            if unit:
                return unit.portrait_id
            else:
                return name

    def get_unit(self, uid, gameStateObj):
        if uid == '{unit}':
            return self.unit
        elif uid == '{unit2}' and self.unit2:
            return self.unit2
        else:
            return gameStateObj.get_unit(uid)

    def add_item(self, unit, item, gameStateObj, choice=True, banner=True):
        if banner:
            func = Action.do  # Displays banner
            self.current_state = "Paused"
        else:
            func = Action.execute  # Does not display banner
        if unit:
            if choice:  # You can make convoy decision here
                func(Action.GiveItem(unit, item), gameStateObj)
            elif len(unit.items) < cf.CONSTANTS['max_items']:
                func(Action.GiveItem(unit, item, False), gameStateObj)
            else:
                func(Action.PutItemInConvoy(item), gameStateObj)
        else:
            func(Action.PutItemInConvoy(item), gameStateObj)

# === DIALOG CLASS ============================================================
class Dialog(object):
    def __init__(self, text, owner, position, size, font,
                 background='MessageWindowBackground',
                 message_tail=None, num_lines=2, hold=False,
                 waiting_cursor_flag=True, transition=False, unit_sprites=None,
                 slow_flag=1, talk=True):
        self.truetext = text # The actual text this dialog box will display
        self.position = position # The position of the dialog box on its surf
        self.owner = owner # who is saying this
        if unit_sprites:
            self.unit_sprites = unit_sprites # Dictionary of all units on screen
        else:
            self.unit_sprites = {} # Empty dictionary
        self.text = [] # A holding list for the individual characters that will be displayed
        self.text_lines = [] # A holding list for each line that will be displayed
        self.num_lines = num_lines # the max number of lines that may be displayed at a time

        self.scroll_y = 0 # For scroll effect

        self.set_text() # Converts {} style constructs into commands. Adds truetext to text

        self.main_font = GC.FONT[font]
        self.current_font = font.split('_')[0]
        self.current_color = font.split('_')[1]

        self._next_line() # Add first line

        self.waiting_cursor = GC.IMAGESDICT['WaitingCursor']
        self.wait_width = self.waiting_cursor.get_width()
        self.waiting_cursor_offset = [0]*20 + [1]*2 + [2]*8 + [1]*2
        self.waiting_cursor_offset_index = 0
        self.waiting_cursor_flag = waiting_cursor_flag
        self.preempt_break = False

        self.dlog_box = BaseMenuSurf.CreateBaseMenuSurf(size, background) # Background of text box
        self.topleft = None
        self.text_width = self.dlog_box.get_width() - 16
        self.text_height = self.dlog_box.get_height() - 16
        self.text_surf = Engine.create_surface((self.text_width, self.text_height), transparent=True) # surface that text is drawn on

        self.waiting = False
        self.done = False
        self.talk = talk

        self.total_num_updates = 0

        self.message_tail = message_tail
        self.hold = hold

        # To match dialogue scene, so it can be used in the same place.
        self.transition_state = transition
        self.transition_transparency = 0
        self.dialog = False

        self.solo_flag = True # Only one of these on the screen at a time
        self.slow_flag = slow_flag # Whether to print the characters out slower than normal

    def get_width(self):
        return self.dlog_box.get_width()

    def get_height(self):
        return self.dlog_box.get_height()

    def set_text(self):
        if self.truetext == '':
            return

        command = None
        self.next_pos = [0, 0]
        for char in self.truetext:
            if char == '{' and command is None:
                command = '{'
            elif char == '}' and command is not None:
                command += '}'
                self.text.insert(0, command)
                command = None
            else:
                if command is not None:
                    command += char
                else:
                    self.text.insert(0, char)

    def _next_line(self):
        self.text_lines.append([])
        self._next_chunk()
        if len(self.text_lines) > self.num_lines:
            self.scroll_y += self.main_font.height

    def _clear(self):
        self.text_lines.append([])
        self._next_chunk()
        self.scroll_y += self.main_font.height*self.num_lines

    def _next_chunk(self):
        self.text_lines[-1].append(['', self.current_color])

    def _add_letter(self, letter):
        self.text_lines[-1][-1][0] += letter

    def _next_char(self):  # draw the next character
        if self.waiting:
            return True  # Wait!
        if self.is_done():
            return True
        text_string = ''.join(self.text)
        text_string = re.sub(r'\{[^}]*\}', ' ', text_string) # Removes things in brackets from the word
        words = text_string.split()
        if words:
            word = words[-1]
        else:
            word = ''
        letter = self.text.pop()
        # print(word[::-1], letter, self.text_width)
        # test for special commands
        if letter == "{br}": # if we've hit a line break command
            if not self.preempt_break:
                self._next_line() # go to next line
            self.preempt_break = False
        elif letter in ("{wait}", "{w}"):
            self.waiting = True
            both_width = self._get_word_width('')
            # print(both_width)
            if both_width >= self.text_width - self.wait_width: # if we've exceeded width
                self.preempt_break = True # We've essentially done the next line break
                self._next_line()
            return True # we're waiting
        elif letter == "{clear}":
            self.text_lines = []
            self._next_line()
        elif letter == "{erase}":
            self.text_lines = []
            self._next_line()
        elif letter == "{black}":
            self.current_color = "black"
            self._next_chunk()
        elif letter == "{red}":
            self.current_color = "red"
            self._next_chunk()
        elif letter == "{semicolon}":
            self._add_letter(";")
        else:
            both_width = self._get_word_width(word)
            # print(letter, previous_lines, word[::-1], both_width, self.text_width)
            if both_width > self.text_width: # if we've exceeded width
                self._next_line()
                if letter != ' ':
                    self._add_letter(letter)
            else:
                self._add_letter(letter) # Add the letter to the most recent chunk

        return False

    def _get_word_width(self, word):
        font = GC.FONT[self.current_font + '_' + self.current_color]
        # Get text for all chunks in this line
        previous_lines = ''
        for chunk, color in self.text_lines[-1]:
            if chunk != '':
                previous_lines = chunk + previous_lines

        return font.size(previous_lines + word[::-1])[0] # Can actually differ from above due to ligatures/digraphs.

    def draw_text(self, surf, pos):
        x, y = pos
        self.scroll_help = int(math.ceil(self.scroll_y/float(self.main_font.height)))
        my_lines = self.text_lines[-(self.num_lines+self.scroll_help):]
        num_lines = len(my_lines) # Used for center
        for index, line in enumerate(my_lines):
            total_length = x
            if self.position == 'center':
                total_length = 0
            for chunk, color in line:
                font = GC.FONT[self.current_font + '_' + color]
                chunk = chunk.strip()
                if chunk != '': # Ignore empty chunks, or else random spaces will appear
                    pos = [total_length, index * font.height + y]
                    total_length += font.size(chunk)[0] + font.size(' ')[0]
                    if self.position == 'center':
                        x_pos = surf.get_width()//2 - total_length//2
                        y_pos = index * font.height + surf.get_height()//2 - num_lines*font.height//2
                        pos = [x_pos, y_pos]
                    font.blit(chunk, surf, pos)
                    if self.position != 'center':
                        pos[0] = total_length
        return pos

    def add_message_tail(self, surf):
        if self.unit_sprites and self.owner in self.unit_sprites:
            unit_position = self.unit_sprites[self.owner].position
        else:
            return
        dialogue_position = self.topleft
        # Do we flip the tail?
        # unit's x _ position < halfway point of screen - half length of unit sprite
        if unit_position[0] < GC.WINWIDTH//2 - 96//2: # On left side
            mirror = True
        else:
            mirror = False
        if mirror:
            tail_surf = Engine.flip_horiz(self.message_tail)
        else:
            tail_surf = self.message_tail
        y_position = dialogue_position[1] + self.dlog_box.get_height() - 2
        # Solve for x_position
        x_position = unit_position[0] + 68 if mirror else unit_position[0] + 12
        # If we wouldn't actually be on the dialogue box
        if x_position > self.dlog_box.get_width() + self.topleft[0] - 24:
            x_position = self.topleft[0] + self.dlog_box.get_width() - 24
        elif x_position < self.topleft[0] + 8:
            x_position = self.topleft[0] + 8

        surf.blit(tail_surf, (x_position, y_position))

    def add_nametag(self, surf):
        if (not self.unit_sprites or self.owner not in self.unit_sprites) and self.owner != "Narrator":
            dialogue_position = self.topleft
            name_tag_surf = BaseMenuSurf.CreateBaseMenuSurf((64, 16), 'NameTagMenu')
            pos = (dialogue_position[0] - 4, dialogue_position[1] - 10)
            if pos[0] < 0:
                pos = dialogue_position[0] + 16, pos[1]
            position = (name_tag_surf.get_width()//2 - self.main_font.size(self.owner)[0]//2, name_tag_surf.get_height()//2 - self.main_font.size(self.owner)[1]//2)
            self.main_font.blit(self.owner, name_tag_surf, position)
            surf.blit(name_tag_surf, pos)

    def hurry_up(self):
        self.transition_state = False
        while not self._next_char():
            pass # while we haven't reached the end, process all the next chars...

    def is_done(self):
        if len(self.text) == 0:
            self.done = True
        return self.done

    def update(self):
        if self.transition_state:
            self.transition_transparency += 1 # 10 is max # 10 frames to load in
            if self.transition_transparency >= 10:
                # Done transitioning
                self.transition_state = False
                if self.talk and self.owner in self.unit_sprites:
                    self.unit_sprites[self.owner].talk()
        elif self.scroll_y > 0:
            self.scroll_y -= 1
        else:
            if cf.OPTIONS['Text Speed'] > 0:
                num_updates = Engine.get_delta() / float(cf.OPTIONS['Text Speed']*self.slow_flag)
                self.total_num_updates += num_updates

                while self.total_num_updates >= 1:
                    self.total_num_updates -= 1
                    if self._next_char():
                        self.total_num_updates = 0
                        break
            else:
                self.hurry_up()

        # handle the waiting marker's vertical offset
        self.waiting_cursor_offset_index += 1
        if self.waiting_cursor_offset_index > len(self.waiting_cursor_offset) - 1:
            self.waiting_cursor_offset_index = 0

    def draw(self, surf):
        text_surf = self.text_surf.copy()
        if self.transition_state:
            scroll = 0
        else:
            end_text_position = self.draw_text(text_surf, (0, 0))
            scroll = int(self.main_font.height*self.scroll_help - self.scroll_y)
        text_surf = Engine.subsurface(text_surf, (0, scroll, text_surf.get_width(), text_surf.get_height() - scroll))

        surf_pos = self.position
        if surf_pos == 'center':
            self.topleft = (GC.WINWIDTH//2 - self.dlog_box.get_width()//2, GC.WINHEIGHT//2 - self.dlog_box.get_height()//2)
        else:
            self.topleft = surf_pos

        if self.transition_state:
            dlog_box = Image_Modification.resize(self.dlog_box, (1, self.transition_transparency/20. + .5))
            dlog_box = Image_Modification.flickerImageTranslucent(dlog_box, 100 - self.transition_transparency*10)
            topleft = self.topleft[0], self.topleft[1] + self.dlog_box.get_height() - dlog_box.get_height()
        else:
            dlog_box = self.dlog_box
            topleft = self.topleft
        surf.blit(dlog_box, topleft)

        if not self.transition_state:
            if self.message_tail:
                self.add_message_tail(surf)
            self.add_nametag(surf)
            surf.blit(text_surf, (self.topleft[0] + 8, self.topleft[1] + 8))

            # Handle the waiting cursor
            # print(end_text_position, scroll)
            if self.waiting and self.waiting_cursor_flag and not self.scroll_y:
                cursor_surf = self.waiting_cursor
                # Make sure we're not placing this where it shouldn't be
                if end_text_position[0] > text_surf.get_width() - self.wait_width:
                    # if end_text_position[1] != 0:
                    #    self._next_line() # Don't do this because it messes up the next line.
                    # print(self.num_lines*self.main_font.height)
                    if end_text_position[1] >= (self.num_lines-1)*self.main_font.height:
                        # self._next_line()
                        pass # For now
                    else:
                        end_text_position[0] = 0 # Move to next line
                        end_text_position[1] += self.main_font.height
                pos = (surf_pos[0] + 8 + end_text_position[0],
                       surf_pos[1] + 16 + end_text_position[1] + self.waiting_cursor_offset[self.waiting_cursor_offset_index])
                surf.blit(cursor_surf, pos)

class Credits(object):
    def __init__(self, title, text, title_font, font, wait=False, center=False):
        self.title = title
        self.text = text
        self.center = center
        self.wait = wait
        self.wait_flag = False
        self.title_font = GC.FONT[title_font]
        self.main_font = GC.FONT[font]

        self.populate_surface()

        self.position = [0, GC.WINHEIGHT]
        self.speed = 0.35

        self.last_update = Engine.get_time()

        # To match dialog
        self.waiting = False # Never waiting on unit input
        self.done = True # Always ready to move on to next dialog object
        self.hold = True # Always show, even if waiting
        self.solo_flag = False # As many of these on the screen as possible
        self.talk = False

    def populate_surface(self):
        index = 0
        self.parsed_text = []
        for credit in self.text:
            x_bound = GC.WINWIDTH - 12 if self.center else GC.WINWIDTH - 88
            l = TextChunk.line_wrap(TextChunk.line_chunk(credit), x_bound, self.main_font)
            for line in l:
                text = ''.join(line)
                if self.center:
                    x_pos = GC.WINWIDTH//2 - self.main_font.size(text)[0]//2
                else:
                    x_pos = 88
                y_pos = self.main_font.height*index + self.title_font.height
                index += 1
                self.parsed_text.append((text, index, (x_pos, y_pos)))

        self.length = index

        # Create surface
        size = GC.WINWIDTH, self.title_font.height + self.main_font.height * self.length
        self.surface = Engine.create_surface(size, transparent=True)

        # title - center?
        # title_pos_x = GC.WINWIDTH/2 - self.title_font.size(self.title)[0]/2
        title_pos_x = 32
        self.title_font.blit(self.title, self.surface, (title_pos_x, 0))

        # rest of text
        for text, index, pos in self.parsed_text:
            self.main_font.blit(text, self.surface, pos)

    def determine_wait(self):
        time = (self.length + 2) * self.main_font.height // self.speed * 1000//GC.FPS
        if self.wait:
            time += self.get_pause() * 2
        return time

    def get_pause(self):
        return -~self.length * 1000 # 1500

    def hurry_up(self):
        pass

    def is_done(self):
        return self.done

    def update(self):
        # print(self.position)
        current_time = Engine.get_time()
        if not self.wait_flag or current_time - self.last_update > self.get_pause():
            self.wait_flag = False
            self.position[1] -= self.speed
            self.last_update = current_time
            if self.wait and GC.WINHEIGHT//2 - self.surface.get_height()//2 >= self.position[1]:
                self.wait_flag = True
                self.wait = False

    def draw(self, surf, unit_sprites=None):
        self.update()
        surf.blit(self.surface, self.position)

class Cinematic(object):
    def __init__(self, text, font, flags=None):
        self.flags = flags or []
        self.text = text.split('|')
        self.center = 'center' in self.flags
        self.wait_flag = False
        self.main_font = GC.FONT[font]

        if 'no_fade_in' in self.flags:
            self.transition_state = 'normal'
        else:
            self.transition_state = 'fade_in'
        self.start_time = Engine.get_time()
        self.transition_time = 1400
        if 'infinite_wait' in self.flags:
            self.wait_time = int(1e6)
        else:
            self.wait_time = len(text) * 54 + (1000 if 'extra_wait' in self.flags else 0)

        self.populate_surface()

        # To match dialog
        self.waiting = False # Never waiting on unit input
        self.done = True # Always ready to move on to next dialog object
        self.hold = True # Always show, even if waiting
        self.solo_flag = True # As many of these on the screen as possible
        self.talk = False

    def populate_surface(self):
        self.surface = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT), transparent=True)
        for idx, line in enumerate(self.text):
            if self.center:
                x_pos = GC.WINWIDTH//2 - self.main_font.size(line)[0]//2
            else:
                x_pos = 12
            half = len(self.text)//2
            if len(self.text)%2:  # If odd
                y_pos = GC.WINHEIGHT//2 + (idx - half)*24 - 6
            else:
                y_pos = GC.WINHEIGHT//2 + (idx - half)*24 + 6
            self.main_font.blit(line, self.surface, (x_pos, y_pos))

    def total_wait(self):
        return self.transition_time * 2 + self.wait_time

    def hurry_up(self):
        pass

    def is_done(self):
        return self.done

    def update(self):
        current_time = Engine.get_time()
        if current_time - self.start_time > self.wait_time + self.transition_time:
            if 'no_fade_out' in self.flags:
                self.done = True
            else:
                self.transition_state = 'fade_out'
                self.start_time = current_time

        if self.transition_state == 'fade_in':
            transition = int(Utility.linear_ease(100, 0, current_time - self.start_time, self.transition_time))
            self.image = Image_Modification.flickerImageTranslucent(self.surface, transition)
            if transition <= 0:
                self.transition_state = 'normal'
        elif self.transition_state == 'normal':
            self.image = self.surface.copy()
        elif self.transition_state == 'fade_out':
            transition = int(Utility.linear_ease(0, 100, current_time - self.start_time, self.transition_time))
            self.image = Image_Modification.flickerImageTranslucent(self.surface, transition)
            if transition >= 100:
                self.done = True

    def draw(self, surf, unit_sprites=None):
        self.update()
        surf.blit(self.image, (0, 0))

class LocationCard(object):
    def __init__(self, text, font):
        self.card = GC.IMAGESDICT['LocationCard']
        self.text = text
        self.main_font = GC.FONT[font]
        self.populate_surface()

        self.wait = int(100 * 16.66)  # 100 frames
        self.transition_time = int(15 * 16.66)  # 15 frames
        self.transition_state = 'fade_in'
        self.start_time = Engine.get_time()

        # To match dialog
        self.waiting = False # Never waiting on unit input
        self.done = True # Always ready to move on to next dialog object
        self.hold = True # Always show, even if waiting
        self.solo_flag = True # As many of these on the screen as possible
        self.talk = False

    def populate_surface(self):
        self.surface = Engine.copy_surface(self.card)
        x_pos = self.surface.get_width()//2 - self.main_font.size(self.text)[0]//2
        self.main_font.blit(self.text, self.surface, (x_pos, 5))

    def hurry_up(self):
        pass

    def is_done(self):
        return self.done

    def update(self):
        current_time = Engine.get_time()
        if current_time - self.start_time > self.wait + self.transition_time:
            self.transition_state = 'fade_out'
            self.start_time = current_time

        if self.transition_state == 'fade_in':
            transition = int(Utility.linear_ease(100, 0, current_time - self.start_time, self.transition_time))
            self.image = Image_Modification.flickerImageTranslucent(self.surface, transition)
            if transition <= 0:
                self.transition_state = 'normal'
        elif self.transition_state == 'normal':
            self.image = self.surface.copy()
        elif self.transition_state == 'fade_out':
            transition = int(Utility.linear_ease(0, 100, current_time - self.start_time, self.transition_time))
            self.image = Image_Modification.flickerImageTranslucent(self.surface, transition)
            if transition >= 100:
                self.done = True

    def draw(self, surf, unit_sprites=None):
        self.update()
        surf.blit(self.image, (8, 0))

class EndingsDisplay(object):
    def __init__(self, message_system, portrait1, title, text, stats, font='text_white'):
        self.message_system = message_system
        self.portrait = Engine.subsurface(GC.UNITDICT[portrait1 + 'Portrait'], (0, 0, 96, 80))
        self.title = title
        self.truetext = text
        self.text = []
        self.text_index = [0, 0] # Line num, character num within line
        self.font = GC.FONT[font]
        self.format_text(text)

        self.background = GC.IMAGESDICT['EndingsDisplay']
        self.populate_surface(portrait1, stats)

        self.x_position = GC.WINWIDTH

        self.wait_time = len(self.text) * 2000
        self.starting_update = Engine.get_time()
        self.last_update = 0

        # To match dialog
        self.waiting = False # Not waiting on unit input??
        self.done = False # Not always ready to move on to next dialog object
        self.hold = True # Always show, even if waiting
        self.solo_flag = True # Not as many of these as possible
        self.talk = False

    def populate_surface(self, name, stats):
        # Create surface
        size = GC.WINWIDTH, GC.WINHEIGHT
        self.surface = Engine.create_surface(size, transparent=True)

        self.surface.blit(self.background, (0, 0))
        self.surface.blit(self.portrait, (128 + 8, GC.WINHEIGHT - 80 - 24 + 1))

        title_pos_x = 68 - self.font.size(self.title)[0]//2
        self.font.blit(self.title, self.surface, (title_pos_x, 24))

        # === Stats
        # Get statistics
        kills, damage, healing = 0, 0, 0
        for level in stats:
            if name in level.stats:
                record = level.stats[name]
                kills += record['kills']
                damage += record['damage']
                healing += record['healing']

        # Print Statistics
        GC.FONT['text_yellow'].blit('K', self.surface, (136, 8))
        GC.FONT['text_yellow'].blit('D', self.surface, (168, 8))
        GC.FONT['text_yellow'].blit('H', self.surface, (200, 8))
        GC.FONT['text_blue'].blit(str(kills), self.surface, (144, 8))
        dam = str(damage)
        if damage >= 1000:
            dam = dam[:-3] + '.' + dam[-3] + 'k'
        heal = str(healing)
        if healing >= 1000:
            heal = heal[:-3] + '.' + dam[-3] + 'k'
        GC.FONT['text_blue'].blit(dam, self.surface, (176, 8))
        GC.FONT['text_blue'].blit(heal, self.surface, (208, 8))

    def format_text(self, text):
        l = TextChunk.line_wrap(TextChunk.line_chunk(text), GC.WINWIDTH - 32, self.font)
        for line in l:
            self.text.append(''.join(line))

    def hurry_up(self):
        self.text_index[0] = len(self.text)
        self.done = True
        self.waiting = True

    def is_done(self):
        return self.done

    def update(self):
        current_time = Engine.get_time()
        # Transition in
        if self.x_position > 0:
            self.x_position -= 8
            self.x_position = max(0, self.x_position)

        # Add text -- increment indices counter
        elif self.text_index[0] < len(self.text):
            if current_time - self.last_update > cf.OPTIONS['Text Speed']:
                self.last_update = current_time
                self.text_index[1] += 1
                if self.text_index[1] > len(self.text[self.text_index[0]]) - 1:
                    self.text_index[0] += 1
                    self.text_index[1] = 0

        else:
            self.done = True
            self.waiting = True
            # Only wait for so long
            if current_time - self.starting_update > self.wait_time:
                self.message_system.dialog_unpause() # Move further with process

    def draw(self, surf, unit_sprites=None):
        # self.update()
        surf.blit(self.surface, (self.x_position, 0))

        for index, line in enumerate(self.text[:self.text_index[0]+1]):
            if index == self.text_index[0]:
                new_line = line[:self.text_index[1]]
            else:
                new_line = line
            self.font.blit(new_line, surf, (self.x_position + 16, 48 + index*self.font.height))
