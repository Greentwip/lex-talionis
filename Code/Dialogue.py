import re, random, math, itertools
# Custom imports
try:
    import GlobalConstants as GC
    import configuration as cf
    import static_random
    import MenuFunctions, SaveLoad, Image_Modification, StatusObject, Counters, LevelUp, Cursor
    import Interaction, ItemMethods, WorldMap, Utility, UnitObject, Engine, Banner, TextChunk
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import static_random
    from . import MenuFunctions, SaveLoad, Image_Modification, StatusObject, Counters, LevelUp, Cursor
    from . import Interaction, ItemMethods, WorldMap, Utility, UnitObject, Engine, Banner, TextChunk

import logging
logger = logging.getLogger(__name__)

hardset_positions = {'OffscreenLeft': -96, 'FarLeft': -24, 'Left': 0, 'MidLeft': 24,
                     'MidRight': 120, 'Right': 144, 'FarRight': 168, 'OffscreenRight': 240}

# === GET INFO FOR DIALOGUE SCENE ==================================================
class Dialogue_Scene(object):
    def __init__(self, scene, unit=None, unit2=None, name=None, tile_pos=None, if_flag=False):
        self.scene = scene
        if self.scene:
            with open(scene, 'r') as scenefp: # Open this scene's file database
                self.scene_lines = scenefp.readlines()
        else:
            self.scene_lines = []
        if cf.OPTIONS['debug']: 
            if not self.count_if_statements():
                logger.error('ERROR: Incorrect number of if and end statements! %s', scene)

        # Background sprite
        self.background = None
        self.foreground = None
        # Dictionary of scene sprites
        self.unit_sprites = {}
        # Dialogs
        self.dialog = []
        
        # Optional unit
        self.unit = unit
        if self.unit and isinstance(self.unit, UnitObject.UnitObject):
            # logger.debug('locking %s', self.unit)
            self.unit.lock_active()
        self.unit1 = unit  # Alternate name
        self.unit2 = unit2
        if self.unit2 and isinstance(self.unit2, UnitObject.UnitObject):
            # logger.debug('locking %s', self.unit2)
            self.unit2.lock_active()
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
        self.transition = 0 # No transition
        self.transition_transparency = 0 # 0 is transparent
        self.transition_last_update = Engine.get_time()

        self.scene_lines_index = 0 # Keeps track of where we are in the scene
        self.if_stack = [] # Keeps track of how many ifs we've encountered while searching for
        # the bad ifs 'end'.
        self.parse_stack = [] # Keeps track of whether we've encountered a truth this level or not

        self.current_state = "Processing" # Other options are "Waiting", "Transitioning"
        self.last_state = None
        self.do_skip = False
        self.battle_save_flag = False # Whether to enter the battle save state after this scene has completed
        self.reset_state_flag = False # Whether to reset state to free state after this scene has completed
        self.reset_boundary_manager = False # Whether to reset the boundary manager after this scene has completed. Set to true when tiles are changed

        # Handle waiting
        self.last_wait_update = Engine.get_time()
        self.waittime = 0

        # Handles skipping
        self.skippable_commands = {'s', 'u', 'qu', 't', 'wait', 'bop', 'mirror',
                                   'wm_move_sprite', 'map_pan', 'set_expression',
                                   'credits', 'endings', 'start_move', 
                                   'move_sprite', 'qmove_sprite'}

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
        self.transition = 0
        self.transition_transparency = 0

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

        if self.current_state == "Waiting":
            if current_time > self.last_wait_update + self.waittime:
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
            if self.transition == 1: # Increasing
                self.transition_transparency = current_time - self.transition_last_update
            elif self.transition == 2:
                self.transition_transparency = 255 - (current_time - self.transition_last_update)
            elif self.transition == 3:
                self.transition_transparency = (current_time - self.transition_last_update)//2
            elif self.transition == 4:
                self.transition_transparency = 255 - (current_time - self.transition_last_update)//2
            if self.transition_transparency > 255 + 5*GC.FRAMERATE or self.transition_transparency < 0: # I want 5 extra frames in black
                self.current_state = "Processing"
                if self.scene_lines_index >= len(self.scene_lines): # Check if we're done
                    self.end()
            self.transition_transparency = Utility.clamp(self.transition_transparency, 0, 255)

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
        if self.unit and isinstance(self.unit, UnitObject.UnitObject):
            # logger.debug('Unlocking %s', self.unit)
            self.unit.unlock_active()
        if self.unit2 and isinstance(self.unit2, UnitObject.UnitObject):
            # logger.debug('Unlocking %s', self.unit2)
            self.unit2.unlock_active()
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
                self.background = MenuFunctions.StaticBackground(GC.IMAGESDICT[line[1]], fade=False)
        # Remove the background
        elif line[0] == 'remove_background':
            self.background = None

        # === FOREGROUND
        # Change the foreground
        elif line[0] == 'foreground':
            self.foreground = MenuFunctions.StaticBackground(GC.IMAGESDICT[line[1]], fade=False)
        elif line[0] == 'remove_foreground':
            self.foreground = None

        # === WORLD MAP
        elif line[0] == 'wm_move':
            new_position = self.parse_pos(line[1], gameStateObj)
            self.background.move(new_position)
        elif line[0] == 'wm_qmove':
            new_position = self.parse_pos(line[1], gameStateObj)
            self.background.quick_move(new_position)
        elif line[0] == 'wm_load_sprite' or line[0] == 'wm_load' or line[0] == 'wm_add':
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
            self.background.add_sprite(line[1], klass, gender, team, starting_position)
        elif line[0] == 'wm_remove_sprite' or line[0] == 'wm_remove':
            self.background.remove_sprite(line[1])
        elif line[0] == 'wm_move_sprite':
            new_position = self.parse_pos(line[2], gameStateObj)
            self.background.move_sprite(line[1], new_position)
        elif line[0] == 'wm_move_unit':
            new_position = self.parse_pos(line[2], gameStateObj)
            new_position = (new_position[0]*16, new_position[1]*16)
            self.background.move_sprite(line[1], new_position)
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
        elif line[0] == 'wm_cursor':
            pos = self.parse_pos(line[1], gameStateObj)
            self.background.create_cursor(pos)
        elif line[0] == 'wm_remove_cursor':
            self.background.remove_cursor()

        # === UNIT SPRITE
        # Add a unit to the scene
        elif line[0] == 'u':
            # This is a complicated method of parsing unit lines using 'u' as delimeter
            spl = []
            w = 'u'
            for x, y in itertools.groupby(line, lambda z: z == w):
                if x:
                    spl.append([])
                spl[-1].extend(y)

            for sub_command in spl:
                if self.add_unit_sprite(sub_command, metaDataObj, transition=True):
                    # Force wait after unit sprite is drawn to allow time to transition.
                    self.waittime = 266  # 16 frames
                    self.last_wait_update = Engine.get_time()
                    self.current_state = "Waiting"
        # Add a unit to the scene without transition
        elif line[0] == 'qu':
            self.add_unit_sprite(line, metaDataObj, transition=False)
        # Change a unit's expression
        elif line[0] == 'set_expression':
            self.unit_sprites[line[1]].expression = line[2]
        # Remove a unit from the scene
        elif line[0] == 'r':
            for name in line[1:]:
                unit_name = self.unit.name if name == '{unit}' else name
                if unit_name in self.unit_sprites:
                    self.unit_sprites[unit_name].remove()
                    # Force wait after unit sprite is drawn to allow time to transition.
                    self.waittime = 250
                    self.last_wait_update = Engine.get_time()
                    self.current_state = "Waiting"
        elif line[0] == 'qr': # No transition plox
            for name in line[1:]:
                unit_name = self.unit.name if name == '{unit}' else name
                if unit_name in self.unit_sprites:
                    self.unit_sprites.pop(unit_name)
        # Move a unit sprite
        elif line[0] == 'move_sprite' or line[0] == 'qmove_sprite':
            name = self.unit.name if line[1] == '{unit}' else line[1]
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
            name = self.unit.name if line[1] == '{unit}' else line[1]
            if name in self.unit_sprites:
                self.unit_sprites[name].mirror = not self.unit_sprites[name].mirror
        # Bop the unit sprite up and down
        elif line[0] == 'bop':
            name = self.unit.name if line[1] == '{unit}' else line[1]
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

        # === HANDLE ITEMS
        # Give the optional unit an item or give the unit named in the line the item
        elif line[0] == 'give_item':
            # Find receiver
            if line[1] == '{unit}' and self.unit:
                receiver = self.unit
            elif line[1] == 'Convoy':
                receiver = None
            else:
                receiver = gameStateObj.get_unit_from_name(line[1])
            # Append item to list of units items
            if line[2] != "0":
                item = ItemMethods.itemparser(line[2])
                if item:
                    item = item[0]
                    self.add_item(receiver, item, gameStateObj, 'no_banner' not in line)
                else:
                    logger.error("Could not find item matching %s", line[2])
            elif line[2] == "0" and 'no_banner' not in line:
                gameStateObj.banners.append(Banner.foundNothingBanner(receiver))
                gameStateObj.stateMachine.changeState('itemgain')
                self.current_state = "Paused"

        # Has the unit equip an item in their inventory if and only if that item is in their inventory by name
        elif line[0] == 'equip_item':
            receiver = self.unit if line[1] == '{unit}' else gameStateObj.get_unit_from_name(line[1])
            if receiver:
                if len(line) > 2:
                    for item in receiver.items:
                        if item.id == line[2]:
                            receiver.equip(item)
                            break
                else:
                    m = receiver.getMainWeapon()
                    receiver.equip(m)

        # Give the player gold!
        elif line[0] == 'gold':
            gameStateObj.game_constants['money'] += int(line[1])
            gameStateObj.banners.append(Banner.acquiredGoldBanner(int(line[1])))
            gameStateObj.stateMachine.changeState('itemgain')
            self.current_state = "Paused"

        elif line[0] == 'remove_item':
            unit = self.unit if line[1] == '{unit}' else gameStateObj.get_unit_from_name(line[1])
            if unit:
                valid_items = [item for item in unit.items if item.name == line[2] or item.id == line[2]]
                if valid_items:
                    item = valid_items[0]
                    self.unit.remove_item(item)

        # Add a skill/status to a unit
        elif line[0] == 'give_skill':
            skill = StatusObject.statusparser(line[2])
            unit = self.unit if line[1] == '{unit}' else gameStateObj.get_unit_from_name(line[1])
            if unit and skill:
                StatusObject.HandleStatusAddition(skill, unit, gameStateObj)
                if 'no_display' not in line:
                    gameStateObj.banners.append(Banner.gainedSkillBanner(self.unit, skill))
                    gameStateObj.stateMachine.changeState('itemgain')
                    self.current_state = "Paused"

        # Give exp to a unit
        elif line[0] == 'exp_gain' or line[0] == 'give_exp':
            exp = int(line[2])
            unit = self.unit if line[1] == '{unit}' else gameStateObj.get_unit_from_name(line[1])
            gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=unit, exp=exp))
            gameStateObj.stateMachine.changeState('expgain')
            self.current_state = "Paused"

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
        elif line[0] == 'interact_unit':
            # Read input
            attacker = line[1]
            defender = line[2]
            if len(line) > 3:
                event_combat = [command.lower() for command in reversed(line[3].split(','))]
            else:
                event_combat = None
            self.interact_unit(gameStateObj, attacker, defender, event_combat)
        elif line[0] == 'remove_unit' or line[0] == 'kill_unit':
            # Read input
            which_unit = line[1]
            transition = line[2] if (len(line) > 2 and line[2]) else 'fade'
            event = (line[0] == 'remove_unit')
            self.remove_unit(gameStateObj, which_unit, transition, event=event)
        elif line[0] == 'resurrect_unit':
            unit = gameStateObj.get_unit_from_name(line[1])
            if unit and unit.dead:
                unit.dead = False
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
                    print('In trigger:')
                    print(unit_id, start, end)
                    # First see if the unit is in reinforcements
                    if unit_id in gameStateObj.allreinforcements:
                        self.add_unit(gameStateObj, metaDataObj, unit_id, None, 'fade', 'stack')
                        del gameStateObj.allreinforcements[unit_id]  # So we just move the unit now
                        self.move_unit(gameStateObj, metaDataObj, unit_id, end, 'normal', 'give_up')
                    else:
                        self.move_unit(gameStateObj, metaDataObj, unit_id, end, 'normal', 'give_up')
                if trigger.units:
                    # Start move
                    self.current_state = "Paused"
                    gameStateObj.stateMachine.changeState('movement')

        # === HANDLE CURSOR
        elif line[0] == 'set_cursor':
            if "," in line[1]: # If is a coordinate
                coord = self.parse_pos(line[1], gameStateObj)
            elif line[1] == 'next' and self.next_position:
                coord = self.next_position
            elif line[1] == '{unit}' and self.unit:
                    coord = self.unit.position
            else:
                for unit in gameStateObj.allunits:
                    if (unit.id == line[1] or unit.event_id == line[1]) and unit.position:
                        coord = unit.position
                        break
                else:
                    logger.error("Couldn't find unit %s", line[1])
                    return
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
        elif line[0] == 'set_camera':
            pos1 = self.parse_pos(line[1], gameStateObj)
            pos2 = self.parse_pos(line[2], gameStateObj)
            gameStateObj.cameraOffset.center2(pos1, pos2)
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
            gameStateObj.objective.display_name_string = line[1]
        elif line[0] == 'change_objective_win_condition':
            gameStateObj.objective.win_condition_string = line[1]
        elif line[0] == 'change_objective_loss_condition':
            gameStateObj.objective.loss_condition_string = line[1]
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
        elif line[0] == 'change_music':
            if gameStateObj.phase_music:
                # Phase name, musical piece
                gameStateObj.phase_music.change_music(line[1], line[2])

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
                line = [line[0], self.parse_pos(line[1], gameStateObj)]
            else:
                gameStateObj.map.origin = self.tile_pos
                line.append(self.tile_pos)
            gameStateObj.map.command_list.append(line)
        # Change tile sprites. - command, pos, tile_sprite, size, transition
        elif line[0] == 'change_tile_sprite':
            # Add default transition
            if len(line) < 4:
                line.append('fade')
            gameStateObj.map.change_sprite(line)
            # Ways of destroying. Defaults to instantaneous in command list
            if 'fade' in line:
                line.remove('fade')
            elif 'destroy' in line:
                line.remove('destroy')
            gameStateObj.map.command_list.append(line)
        elif line[0] == 'layer_tile_sprite':
            gameStateObj.map.layer_tile_sprite(line)
            gameStateObj.map.command_list.append(line)
        elif line[0] == 'layer_terrain':
            gameStateObj.map.layer_terrain(line, gameStateObj.grid_manager)
            gameStateObj.map.command_list.append(line)
            self.reset_boundary_manager = True
        elif line[0] == 'show_layer':
            if len(line) < 3:
                line.append('fade')
            gameStateObj.map.show_layer(line, gameStateObj.grid_manager)
            if 'fade' in line:
                line.remove('fade')
            elif 'destroy' in line:
                line.remove('destroy')
            gameStateObj.map.command_list.append(line)
            self.reset_boundary_manager = True
        elif line[0] == 'hide_layer':
            if len(line) < 3:
                line.append('fade')
            gameStateObj.map.hide_layer(line, gameStateObj.grid_manager)
            if 'fade' in line:
                line.remove('fade')
            elif 'destroy' in line:
                line.remove('destroy')
            gameStateObj.map.command_list.append(line)
            self.reset_boundary_manager = True
        elif line[0] == 'clear_layer':
            gameStateObj.map.clear_layer(line[1])
            gameStateObj.map.command_list.append(line)
        # Change one tile
        elif line[0] == 'replace_tile':
            coords = gameStateObj.map.replace_tile(line, gameStateObj.grid_manager)
            gameStateObj.map.command_list.append(line)
            self.reset_boundary_manager = True
            # gameStateObj.boundary_manager.reset(gameStateObj)
        # Change area of tile (must include pic instead of id)
        elif line[0] == 'area_replace_tile':
            coord, size = gameStateObj.map.mass_replace_tile(line, gameStateObj.grid_manager)
            gameStateObj.map.command_list.append(line)
            self.reset_boundary_manager = True
            # width, height = size
            # gameStateObj.boundary_manager.reset(gameStateObj)
        # Change one tile's information
        elif line[0] == 'set_tile_info':
            gameStateObj.map.set_tile_info(line)
            gameStateObj.map.command_list.append(line)
        # Changing whole map tile data!
        elif line[0] == 'load_new_map_tiles':
            gameStateObj.map.load_new_map_tiles(line, gameStateObj.game_constants['level'])
            gameStateObj.map.command_list.append(line)
            gameStateObj.boundary_manager.reset(gameStateObj)
        # Changing whole map's sprites!
        elif line[0] == 'load_new_map_sprite':
            gameStateObj.map.load_new_map_sprite(line, gameStateObj.game_constants['level'])
            gameStateObj.map.command_list.append(line)
        # Reset whole map's tile_info!
        elif line[0] == 'reset_map_tile_info':
            gameStateObj.map.reset_tile_info()
            gameStateObj.map.command_list.append(line)
        # Add weather
        elif line[0] == 'add_weather':
            gameStateObj.map.add_weather(line[1])
            gameStateObj.map.command_list.append(line)
        # Remove weather
        elif line[0] == 'remove_weather':
            gameStateObj.map.remove_weather(line[1])
            gameStateObj.map.command_list.append(line)
        # Add global status
        elif line[0] == 'add_global_status':
            gameStateObj.map.add_global_status(line[1], gameStateObj)
            gameStateObj.map.command_list.append(line)
        # Remove global status
        elif line[0] == 'remove_global_status':
            gameStateObj.map.remove_global_status(line[1], gameStateObj)
            gameStateObj.map.command_list.append(line)
        # Remove global status
        # Clear command list
        elif line[0] == 'clear_command_list':
            if len(line) > 1:
                gameStateObj.map.command_list = [command for command in gameStateObj.map.command_list if command[0] != line[1]]
            else:
                gameStateObj.map.command_list = []
        elif line[0] == 'clear_command_list_except':
            gameStateObj.map.command_list = [command for command in gameStateObj.map.command_list if command[0] == line[1]]

        # === CLEANUP
        elif line[0] == 'arrange_formation':
            force = True if len(line) > 1 else False
            if force:  # force arrange
                player_units = [unit for unit in gameStateObj.allunits if 
                                unit.team == 'player' and not unit.dead]
                formation_spots = [pos for pos, value in gameStateObj.map.tile_info_dict.items()
                                   if 'Formation' in value]
            else:
                player_units = [unit for unit in gameStateObj.allunits if 
                                unit.team == 'player' and not unit.dead and not unit.position]
                formation_spots = [pos for pos, value in gameStateObj.map.tile_info_dict.items()
                                   if 'Formation' in value and not gameStateObj.grid_manager.get_unit_node(pos)]
            for index, unit in enumerate(player_units[:len(formation_spots)]):
                if force:
                    unit.leave(gameStateObj)
                    unit.remove_from_map(gameStateObj)
                unit.position = formation_spots[index]
                # print(unit.name, unit.position)
                unit.place_on_map(gameStateObj)
                unit.arrive(gameStateObj)
        elif line[0] == 'reset_units':
            for unit in gameStateObj.allunits:
                unit.reset()
        elif line[0] == 'reset_unit':
            if line[1] == '{unit}':
                self.unit.reset()
            else:
                for unit in gameStateObj.allunits:
                    if line[1] in (unit.id, unit.event_id, unit.team):
                        unit.reset()
        elif line[0] == 'remove_enemies':
            exception = line[1] if len(line) > 1 else None
            units_to_remove = [unit for unit in gameStateObj.allunits if unit.team != "enemy" and unit.id != exception]
            # Remove enemies
            for unit in units_to_remove:
                unit.leave(gameStateObj)
                unit.remove_from_map(gameStateObj)
                unit.position = None
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
                gameStateObj.level_constants[line[1]] = int(eval(line[2]))
            else:
                gameStateObj.level_constants[line[1]] = 1
        elif line[0] == 'inc_level_constant':
            if len(line) > 2:
                gameStateObj.level_constants[line[1]] += int(eval(line[2]))
            else:
                gameStateObj.level_constants[line[1]] += 1
        # should be remembered for all game
        elif line[0] == 'set_game_constant':
            if len(line) > 2:
                gameStateObj.game_constants[line[1]] = int(eval(line[2]))
            else:
                gameStateObj.game_constants[line[1]] = 1
        elif line[0] == 'inc_game_constant':
            if len(line) > 2:
                gameStateObj.game_constants[line[1]] += int(eval(line[2]))
            else:
                gameStateObj.game_constants[line[1]] += 1
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
            if line[1] == '1':
                self.transition = 1
                self.transition_transparency = 0 # Increasing
            elif line[1] == '2':
                self.transition = 2
                self.transition_transparency = 255 # Decreasing
            elif line[1] == '3':
                self.transition = 3
                self.transition_transparency = 0
            elif line[1] == '4':
                self.transition = 4
                self.transition_transparency = 255
            self.transition_last_update = Engine.get_time()
            self.current_state = "Transitioning"
        
        # === CHANGING UNITS
        elif line[0] == 'convert':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    unit.changeTeams(line[2], gameStateObj)
        elif line[0] == 'change_class':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    unit.changeClass(line[2], gameStateObj)
        elif line[0] == 'change_ai':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    unit.ai_descriptor = line[2]
                    unit.get_ai(line[2])
        elif line[0] == 'add_tag':
            unit_specifier = self.get_id(line[1], gameStateObj)
            for unit in gameStateObj.allunits:
                if unit_specifier in (unit.id, unit.event_id, unit.position):
                    unit.tags.add(line[2])

        # === HANDLE TALKING
        elif line[0] == 'add_talk':
            # Add to dictionary
            gameStateObj.talk_options.append((line[1], line[2]))
        elif line[0] == 'remove_talk':
            if (line[1], line[2]) in gameStateObj.talk_options:
                gameStateObj.talk_options.remove((line[1], line[2]))
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
            if edge and gameStateObj.support.can_support(self.unit.id, self.unit2.id) and edge.support_level == self.name:  # Only increment if we haven't read this before (IE we can support)
                edge.increment_support_level()
        elif line[0] == 'choice':
            name = line[1]
            header = line[2]
            options = line[3].split(',')
            # Save results to the game constants
            gameStateObj.game_constants['choice'] = (name, header, options)
            self.current_state = "Paused"
            gameStateObj.stateMachine.changeState('dialog_options')
            
        # === DIALOGUE BOX
        # Add line of text          
        elif line[0] == 's':
            self.evaluate_evals(line, gameStateObj)
            self.add_dialog(line)
        # === CREDITS BOX
        elif line[0] == 'credits':
            self.add_credits(line)
        # === ENDINGS BOX
        elif line[0] == 'endings':
            self.add_ending(line, gameStateObj)
        # === Pop dialog off top
        elif line[0] == 'pop_dialog':
            if self.dialog:
                self.dialog.pop()

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
        speaker = self.unit.name if line[1] == '{unit}' else line[1]
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
                                  talk=not thought_bubble))

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
            # Blit Background
            self.background.draw(surf)

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
            self.foreground.draw(surf)

        s = GC.IMAGESDICT['BlackBackground'].copy()
        s.fill((0, 0, 0, self.transition_transparency))
        surf.blit(s, (0, 0))

    def add_unit_sprite(self, line, metaDataObj, transition=False):
        name = self.unit.name if line[1] == '{unit}' else line[1]
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
        if 'LowPriority' in line:
            priority = self.priority_counter - 1000
        else:
            priority = self.priority_counter
        self.priority_counter += 1
        if 'Full_Blink' in line:
            expression = 'Full_Blink'
        elif 'Smiling' in line:
            expression = 'Smiling'
        else:
            expression = 'Normal'
        assert name in metaDataObj['portrait_dict'], "%s not in portrait dictionary. Need to assign blink and mouth positions to pic"%(name)
        blink = metaDataObj['portrait_dict'][name]['blink']
        mouth = metaDataObj['portrait_dict'][name]['mouth']
        self.unit_sprites[name] = UnitPortrait(portrait_name=name, blink_position=blink, mouth_position=mouth, transition=transition,
                                               position=position, priority=priority, mirror=mirrorflag, expression=expression)

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
        # Find unit
        if create:
            unitLine = gameStateObj.prefabs.get(which_unit)
            if not unitLine:
                logger.warning('Could not find %s' in unitLine)
                return
            new_unitLine = unitLine[:]
            new_unitLine.insert(4, create)
            unit = SaveLoad.create_unit(new_unitLine, gameStateObj.allunits, gameStateObj.factions, gameStateObj.allreinforcements, metaDataObj, gameStateObj)
            position = self.parse_pos(unitLine[5], gameStateObj)
        else:
            context = gameStateObj.allreinforcements.get(which_unit)
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
                logger.warning('Unit %s is dead', u_id)
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
        unit.position = final_pos
        if transition == 'warp':
            unit.sprite.set_transition('warp_in')
            gameStateObj.map.initiate_warp_flowers(final_pos)
        elif transition == 'fade':
            if gameStateObj.map.on_border(final_pos) and gameStateObj.map.tiles[final_pos].name not in ('Stairs', 'Fort'):
                unit.sprite.spriteOffset = [num*GC.TILEWIDTH for num in gameStateObj.map.which_border(final_pos)]
                unit.sprite.set_transition('fake_in')
            else:
                unit.sprite.set_transition('fade_in')
        elif transition == 'immediate':
            pass
        unit.place_on_map(gameStateObj)
        unit.arrive(gameStateObj)

    def move_unit(self, gameStateObj, metaDataObj, which_unit, new_pos, transition, placement, shuffle=True):
        # Find unit
        if which_unit == '{unit}':
            unit = self.unit
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
            new_pos = [unit.previous_position]
        # If coord, use coord
        elif ',' in new_pos:
            new_pos = self.get_position(new_pos, gameStateObj)
        # If name, then we want to find a point adjacent to that characters position
        else:
            new_pos = [gameStateObj.get_unit_from_id(new_pos).position]

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
            movePath = unit.getPath(gameStateObj, final_pos)
            unit.beginMovement(gameStateObj, movePath)
        elif transition == 'warp':
            unit.sprite.set_transition('warp_move')
            unit.sprite.set_next_position(final_pos)
            gameStateObj.map.initiate_warp_flowers(final_pos)
        elif transition == 'fade':
            unit.sprite.set_transition('fade_move')
            unit.sprite.set_next_position(final_pos)
        elif transition == 'immediate':
            unit.leave(gameStateObj)
            unit.position = final_pos
            unit.arrive(gameStateObj)

    def remove_unit(self, gameStateObj, which_unit, transition, event=True):
        # Find unit
        if which_unit == '{unit}':
            unit = self.unit
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
        if ',' in attacker:
            attacker = gameStateObj.get_unit_from_pos(self.parse_pos(attacker, gameStateObj))
        else:
            attacker = gameStateObj.get_unit(attacker)
        if not attacker:
            logger.error('Interact unit routine could not find %s', attacker)
            return

        if ',' in defender:
            def_pos = self.parse_pos(defender, gameStateObj)
        else:
            defender = gameStateObj.get_unit(defender)
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
                other_unit.push_to_nearest_open_space(gameStateObj)
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

    def add_item(self, unit, item, gameStateObj, banner=True):
        if unit:
            if len(unit.items) < cf.CONSTANTS['max_items']:
                unit.add_item(item)
                if banner:
                    gameStateObj.banners.append(Banner.acquiredItemBanner(unit, item))
                    gameStateObj.stateMachine.changeState('itemgain')
                    self.current_state = "Paused"
            elif unit.team == 'player':
                gameStateObj.convoy.append(item)
                if banner:
                    gameStateObj.banners.append(Banner.sent_to_convoyBanner(item))
                    gameStateObj.stateMachine.changeState('itemgain')
                    self.current_state = "Paused"
        else:
            gameStateObj.convoy.append(item)
            if banner:
                gameStateObj.banners.append(Banner.sent_to_convoyBanner(item))
                gameStateObj.stateMachine.changeState('itemgain')
                self.current_state = "Paused"
        
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

        self.dlog_box = MenuFunctions.CreateBaseMenuSurf(size, background) # Background of text box
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
        self.transition = transition
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
        
    def _next_char(self): # draw the next character
        if self.waiting:
            return True# Wait!
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
            self.text.append("{erase}")
            for x in range(self.num_lines-1):
                self.text.append("{br}")
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
            name_tag_surf = MenuFunctions.CreateBaseMenuSurf((64, 16), 'NameTagMenu')
            pos = (dialogue_position[0] - 4, dialogue_position[1] - 10)
            if pos[0] < 0:
                pos = dialogue_position[0] + 16, pos[1]
            position = (name_tag_surf.get_width()//2 - self.main_font.size(self.owner)[0]//2, name_tag_surf.get_height()//2 - self.main_font.size(self.owner)[1]//2)
            self.main_font.blit(self.owner, name_tag_surf, position)
            surf.blit(name_tag_surf, pos)

    def hurry_up(self):
        self.transition = False
        while not self._next_char():
            pass # while we haven't reached the end, process all the next chars...

    def is_done(self):
        if len(self.text) == 0:
            self.done = True
        return self.done

    def update(self):
        if self.transition:
            self.transition_transparency += 1 # 10 is max # 10 frames to load in
            if self.transition_transparency >= 10:
                # Done transitioning
                self.transition = False
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
        if self.transition:
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

        if self.transition:
            dlog_box = Image_Modification.resize(self.dlog_box, (1, self.transition_transparency/20. + .5))
            dlog_box = Image_Modification.flickerImageTranslucent(dlog_box, 100 - self.transition_transparency*10)
            topleft = self.topleft[0], self.topleft[1] + self.dlog_box.get_height() - dlog_box.get_height()
        else:
            dlog_box = self.dlog_box
            topleft = self.topleft
        surf.blit(dlog_box, topleft)

        if not self.transition:
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

class UnitPortrait(object):
    def __init__(self, portrait_name, blink_position, mouth_position, position, priority=0, mirror=False, transition=False, expression='Normal'):
        self.name = portrait_name
        try:
            portrait_sprite = GC.UNITDICT[portrait_name + 'Portrait'].copy()
        except KeyError:
            raise KeyError
        self.halfblink = Engine.subsurface(portrait_sprite, (96, 48, 32, 16))
        self.fullblink = Engine.subsurface(portrait_sprite, (96, 64, 32, 16))
        self.openmouth = Engine.subsurface(portrait_sprite, (0, 96, 32, 16))
        self.halfmouth = Engine.subsurface(portrait_sprite, (32, 96, 32, 16))
        self.closemouth = Engine.subsurface(portrait_sprite, (64, 96, 32, 16))
        self.opensmile = Engine.subsurface(portrait_sprite, (0, 80, 32, 16))
        self.halfsmile = Engine.subsurface(portrait_sprite, (32, 80, 32, 16))
        self.closesmile = Engine.subsurface(portrait_sprite, (64, 80, 32, 16))
        self.portrait = Engine.subsurface(portrait_sprite, (0, 0, 96, 80))

        self.blink_position = blink_position
        self.mouth_position = mouth_position

        self.position = position
        # For movement
        self.new_position = position
        self.isMoving = False
        self.last_move_update = 0
        self.unit_speed = 6
        self.update_time = 25

        self.priority = priority
        self.mirror = mirror
        self.remove_flag = False
        self.image = self.portrait.copy()

        # Talking setup
        self.talking = False
        self.talk_state = 0
        self.last_talk_update = 0
        self.next_talk_update = 0

        # Transition info
        self.transition = 'trans2color' if transition else 0
        self.transition_transparency = 100 if transition else 0  # 100 is most transparency
        self.transition_last_update = Engine.get_time()

        # Blinking set up
        self.blinking = 2 # 0- Don't blink, 1-hold blink, 2-Blink pseudorandomly
        self.offset_blinking = [x for x in range(-2000, 2000, 125)]
        self.blink_counter = Counters.generic3Counter(7000 + random.choice(self.offset_blinking), 40, 40) # 3 frames for each

        # Expression
        self.expression = expression

        # For bop
        self.bops_remaining = 0
        self.bop_state = False
        self.last_bop = None

    def talk(self):
        self.talking = True

    def stop_talking(self):
        self.talking = False

    def move(self, new_position):
        self.new_position = self.new_position[0] + new_position[0], self.new_position[1] + new_position[1]
        self.isMoving = True

    def bop(self):
        self.bops_remaining = 2
        self.bop_state = False
        self.last_bop = Engine.get_time()

    def update(self, current_time=None):
        if not current_time:
            current_time = Engine.get_time()
        # update mouth
        if self.talking and current_time - self.last_talk_update > self.next_talk_update:
            self.last_talk_update = current_time
            chance = random.randint(1, 10)
            if self.talk_state == 0:
                # 10% chance to skip to state 2    
                if chance == 1:
                    self.talk_state = 2
                    self.next_talk_update = random.randint(70, 160)
                else:
                    self.talk_state = 1
                    self.next_talk_update = random.randint(30, 50)
            elif self.talk_state == 1:
                # 10% chance to go back to state 0
                if chance == 1:
                    self.talk_state = 0
                    self.next_talk_update = random.randint(50, 100)
                else:
                    self.talk_state = 2
                    self.next_talk_update = random.randint(70, 160)
            elif self.talk_state == 2:
                # 10% chance to skip back to state 0
                # 10% chance to go back to state 1
                chance = random.randint(1, 10)
                if chance == 1:
                    self.talk_state = 0
                    self.next_talk_update = random.randint(50, 100)
                elif chance == 2:
                    self.talk_state = 1
                    self.next_talk_update = random.randint(30, 50)
                else:
                    self.talk_state = 3
                    self.next_talk_update = random.randint(30, 50)
            elif self.talk_state == 3:
                self.talk_state = 0
                self.next_talk_update = random.randint(50, 100)

        if not self.talking:
            self.talk_state = 0

        if self.blinking == 2:
            self.blink_counter.update(current_time)

        if self.transition:
            # 14 frames for Unit Face to appear
            perc = 100. * (current_time - self.transition_last_update) / 233
            if self.transition == 'trans2color':
                self.transition_transparency = 100 - perc 
            elif self.transition == 'color2trans':
                self.transition_transparency = perc
            if self.transition_transparency > 100 or self.transition_transparency < 0:
                self.transition = 0
                self.transition_transparency = max(0, min(100, self.transition_transparency))
                # Done transitioning to invisibility, so remove me!
                if self.remove_flag:
                    return True

        # Move unit if he/she needs to be moved
        if self.isMoving:
            if current_time - self.last_move_update > self.update_time:
                # Finds difference between new_position and position
                diff_pos = (self.new_position[0] - self.position[0], self.new_position[1] - self.position[1])
                # No longer moving if difference of position is small
                if diff_pos[0] <= self.unit_speed and diff_pos[0] >= -self.unit_speed and diff_pos[1] <= self.unit_speed and diff_pos[1] >= -self.unit_speed:
                    # Close enough for gov't work
                    self.position = self.new_position
                    self.isMoving = False
                else:
                    angle = math.atan2(diff_pos[1], diff_pos[0])
                    updated_position = (self.position[0] + self.unit_speed * math.cos(angle), self.position[1] + self.unit_speed * math.sin(angle))
                    self.position = updated_position

                self.last_move_update = current_time

        # Bop unit if he/she needs to be bopped
        if self.bops_remaining:
            if current_time - self.last_bop > 150:
                self.last_bop = current_time
                if self.bop_state:
                    self.position = self.position[0], self.position[1] - 2
                    self.bops_remaining -= 1
                else:
                    self.position = self.position[0], self.position[1] + 2
                self.bop_state = not self.bop_state
                
        return False

    def create_image(self):
        if self.blinking == 2:
            if self.blink_counter.count == 0:
                if self.expression == "Full_Blink":
                    self.image.blit(self.fullblink, self.blink_position)
                elif self.expression == "Half_Blink":
                    self.image.blit(self.halfblink, self.blink_position)
                else:
                    self.image = self.portrait.copy()
            elif self.blink_counter.count == 1:
                if self.expression == "Full_Blink":
                    self.image.blit(self.fullblink, self.blink_position)
                else:
                    self.image.blit(self.halfblink, self.blink_position)
            elif self.blink_counter.count == 2:
                self.image.blit(self.fullblink, self.blink_position)
        elif self.blinking == 1:
            self.image.blit(self.fullblink, self.blink_position)

        if self.talk_state == 0:
            if self.expression == "Smiling":
                self.image.blit(self.closesmile, self.mouth_position)
            else:
                self.image.blit(self.closemouth, self.mouth_position)
        elif self.talk_state == 1 or self.talk_state == 3:
            if self.expression == "Smiling":
                self.image.blit(self.halfsmile, self.mouth_position)
            else:
                self.image.blit(self.halfmouth, self.mouth_position)
        elif self.talk_state == 2:
            if self.expression == "Smiling":
                self.image.blit(self.opensmile, self.mouth_position) 
            else:
                self.image.blit(self.openmouth, self.mouth_position)
        
    def draw(self, surf):
        self.create_image()    
        # === MODS ===
        image_sprite = self.image.copy()

        if self.transition:
            image_sprite = Image_Modification.flickerImageBlackColorKey(image_sprite, self.transition_transparency)

        # Mirror if necessary...
        if self.mirror:
            image_sprite = Engine.flip_horiz(image_sprite)
        surf.blit(image_sprite, self.position)

    def remove(self):
        self.transition = 'color2trans'
        self.remove_flag = True
        self.transition_last_update = Engine.get_time()
