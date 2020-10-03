import os

from . import static_random

from . import GlobalConstants as GC
from . import configuration as cf
from . import MenuFunctions, Dialogue, CustomObjects, UnitObject, SaveLoad
from . import Interaction, StatusCatalog, ItemMethods, Background
from . import Minimap, InputManager, Banner, Engine, Utility, Image_Modification
from . import StateMachine, Action, Aura, BaseMenuSurf, ClassData

import logging
logger = logging.getLogger(__name__)

class TurnChangeState(StateMachine.State):
    name = 'turn_change'

    def begin(self, gameStateObj, metaDataObj):
        # gameStateObj.boundary_manager.draw_flag = 0
        # If player phase, save last position of cursor
        if gameStateObj.phase.get_current_phase() == 'player':
            # Handle support increment
            if gameStateObj.support and cf.CONSTANTS['support_end_turn']:
                gameStateObj.support.end_turn(gameStateObj)
            gameStateObj.statedict['previous_cursor_position'] = gameStateObj.cursor.position
        # Clear all previous states in stateMachine except me - Loose the memory.
        current_state = gameStateObj.stateMachine.state[-1]
        gameStateObj.stateMachine.state = [current_state]
        gameStateObj.stateMachine.back()
        # Remove activeMenu?
        gameStateObj.activeMenu = None

    def end(self, gameStateObj, metaDataObj):
        # Replace previous phase
        gameStateObj.phase.next(gameStateObj)

        if gameStateObj.phase.get_current_phase() == 'player':
            # gameStateObj.turncount += 1
            Action.do(Action.IncrementTurn(), gameStateObj)
            gameStateObj.stateMachine.changeState('free')
            gameStateObj.stateMachine.changeState('status')
            gameStateObj.stateMachine.changeState('phase_change')
            # === TURN EVENT SCRIPT ===
            turn_event_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/turnChangeScript.txt'
            if os.path.isfile(turn_event_script):
                gameStateObj.message.append(Dialogue.Dialogue_Scene(turn_event_script))
                gameStateObj.stateMachine.changeState('dialogue')
            # === INTRO SCRIPTS ===
            if (gameStateObj.turncount - 1) <= 0: # If it is the beginning of the game
                for unit in gameStateObj.get_units_in_party():
                    # Give out fatigue statuses if necessary
                    Action.ChangeFatigue(unit, 0).do(gameStateObj)
                # Prep Screen
                if metaDataObj['preparationFlag']:
                    gameStateObj.stateMachine.changeState('prep_main')
                # Run the intro_script
                if os.path.exists(metaDataObj['introScript']):
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(metaDataObj['introScript']))
                    gameStateObj.stateMachine.changeState('dialogue')
                # Chapter transition
                if metaDataObj['transitionFlag']:
                    gameStateObj.stateMachine.changeState('chapter_transition')
                # Run the narration_script - in opposite order because this is a stack
                if os.path.exists(metaDataObj['narrationScript']):
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(metaDataObj['narrationScript']))
                    gameStateObj.stateMachine.changeState('dialogue')
                # Base Screen
                if metaDataObj['baseFlag']:
                    gameStateObj.stateMachine.changeState('base_main')
                # Prebase script
                if os.path.exists(metaDataObj['prebaseScript']):
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(metaDataObj['prebaseScript']))
                    gameStateObj.stateMachine.changeState('dialogue')
            else: # If it is not the beginning of the game
                gameStateObj.stateMachine.changeState('end_step')
            # === END INTRO SCRIPTS ===

        else:
            gameStateObj.stateMachine.changeState('ai')
            gameStateObj.stateMachine.changeState('status')
            gameStateObj.stateMachine.changeState('phase_change')
            # === TURN EVENT SCRIPT ===
            if gameStateObj.phase.get_current_phase() == 'enemy':
                enemy_turn_event_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/enemyTurnChangeScript.txt'
                if os.path.isfile(enemy_turn_event_script):
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(enemy_turn_event_script))
                    gameStateObj.stateMachine.changeState('dialogue')
            gameStateObj.stateMachine.changeState('end_step')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        gameStateObj.input_manager.process_input(eventList)
        return 'repeat'

class FreeState(StateMachine.State):
    name = 'free'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 1
        gameStateObj.boundary_manager.draw_flag = 1
        if gameStateObj.background:
            gameStateObj.background.fade_out()
        # Remove any currentSelectedUnit
        if gameStateObj.cursor.currentSelectedUnit:
            gameStateObj.cursor.currentSelectedUnit.sprite.change_state('normal')
            gameStateObj.cursor.currentSelectedUnit = None
        Engine.music_thread.fade_to_normal(gameStateObj)
        self.info_counter = 0
        # So the turnwheel cannot go back before this moment
        if gameStateObj.turncount == 1:
            gameStateObj.action_log.set_first_free_action()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        # Check to see if all ally units have completed their turns and no unit is active and the game is in the free state.
        if cf.OPTIONS['Autoend Turn'] and any(unit.position for unit in gameStateObj.allunits) and \
                all(unit.isDone() for unit in gameStateObj.allunits if unit.position and unit.team == 'player'):
            # End the turn
            logger.info('Autoending turn.')
            gameStateObj.stateMachine.changeState('turn_change')
            return 'repeat'

        if any(unit.isDying for unit in gameStateObj.allunits):
            gameStateObj.stateMachine.changeState('dying')

        event = gameStateObj.input_manager.process_input(eventList)
        # Check if both L and R are pressed down, if so, debug state!
        if cf.OPTIONS['cheat'] and 'AUX' in gameStateObj.input_manager.key_down_events and 'INFO' in gameStateObj.input_manager.key_down_events:
            gameStateObj.stateMachine.changeState('debug')
        # Show R unit status screen
        elif event == 'INFO':
            if gameStateObj.cursor.getHoveredUnit(gameStateObj):
                CustomObjects.handle_info_key(gameStateObj, metaDataObj)
            else:  # Show enemy attacks otherwise
                GC.SOUNDDICT['Select 3'].play()
                gameStateObj.boundary_manager.toggle_all_enemy_attacks()
        elif event == 'AUX':
            CustomObjects.handle_aux_key(gameStateObj)
        # Enter movement state
        elif event == 'SELECT':
            # If is a unit that is not done with its turn
            gameStateObj.cursor.currentSelectedUnit = [unit for unit in gameStateObj.allunits if
                                                       unit.position == gameStateObj.cursor.position and not unit.isDone()]
            if gameStateObj.cursor.currentSelectedUnit: # Unit must exist at that spot
                gameStateObj.cursor.currentSelectedUnit = gameStateObj.cursor.currentSelectedUnit[0]
                # Ie a player controlled character
                if gameStateObj.cursor.currentSelectedUnit.team == 'player' and \
                        'un_selectable' not in gameStateObj.cursor.currentSelectedUnit.status_bundle:
                    GC.SOUNDDICT['Select 3'].play()
                    gameStateObj.stateMachine.changeState('move')
                else:
                    GC.SOUNDDICT['Select 2'].play()
                    if gameStateObj.cursor.currentSelectedUnit.team.startswith('enemy'):
                        gameStateObj.boundary_manager.toggle_unit(gameStateObj.cursor.currentSelectedUnit)
                    else:
                        GC.SOUNDDICT['Error'].play()
            else: # No unit
                GC.SOUNDDICT['Select 2'].play()
                gameStateObj.stateMachine.changeState('optionsmenu')
        elif event == 'BACK':
            # GC.SOUNDDICT['Select 3'].play()
            # gameStateObj.boundary_manager.toggle_all_enemy_attacks(gameStateObj)
            pass  # While held doubles cursor movement speed
        elif event == 'START':
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.stateMachine.changeState('minimap')

        # Moved down here so it is done last
        gameStateObj.cursor.back_pressed = gameStateObj.input_manager.is_pressed('BACK')
        gameStateObj.cursor.take_input(eventList, gameStateObj)

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.highlight_manager.handle_hover(gameStateObj)

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.highlight_manager.remove_highlights()
        gameStateObj.cursor.remove_unit_display()
        gameStateObj.cursor.back_pressed = False

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.cursor.drawPortraits(mapSurf, gameStateObj)
        return mapSurf

class OptionsMenuState(StateMachine.State):
    name = 'optionsmenu'
    re_load = True

    def begin(self, gameStateObj, metaDataObj):
        if self.re_load:
            gameStateObj.cursor.drawState = 0
            options = [cf.WORDS['Unit'], cf.WORDS['Objective'], cf.WORDS['Options']]
            info_desc = [cf.WORDS['Unit_desc'], cf.WORDS['Objective_desc'], cf.WORDS['Options_desc']]
            if not gameStateObj.tutorial_mode:
                if gameStateObj.mode['death']:  # If classic mode
                    options.append(cf.WORDS['Suspend'])
                    info_desc.append(cf.WORDS['Suspend_desc'])
                else:  # If casual mode
                    options.append(cf.WORDS['Save'])
                    info_desc.append(cf.WORDS['Save_desc'])
            if not gameStateObj.tutorial_mode or all(unit.isDone() for unit in gameStateObj.allunits if unit.team == 'player'):
                options.append(cf.WORDS['End'])
                info_desc.append(cf.WORDS['End_desc'])
            if cf.CONSTANTS['turnwheel'] and 'Turnwheel' in gameStateObj.game_constants:
                options.insert(1, cf.WORDS['Turnwheel'])
                info_desc.insert(1, cf.WORDS['Turnwheel_desc'])
            gameStateObj.activeMenu = \
                MenuFunctions.ChoiceMenu(None, options, 'auto',
                                         gameStateObj=gameStateObj, info_desc=info_desc)
        else:
            self.re_load = True

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)

        # Back - to free state
        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.activeMenu = None # Remove menu
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            selection = gameStateObj.activeMenu.getSelection()
            GC.SOUNDDICT['Select 1'].play()
            if selection == cf.WORDS['End']:
                if cf.OPTIONS['Confirm End']:
                    gameStateObj.shared_state_data['option_owner'] = selection
                    gameStateObj.stateMachine.changeState('optionchild')
                else:
                    gameStateObj.stateMachine.changeState('ai')
            elif selection == cf.WORDS['Suspend'] or selection == cf.WORDS['Save']:
                # Create child menu with additional options
                gameStateObj.shared_state_data['option_owner'] = selection
                gameStateObj.stateMachine.changeState('optionchild')
            elif selection == cf.WORDS['Objective']:
                gameStateObj.stateMachine.changeState('status_menu')
                gameStateObj.stateMachine.changeState('transition_out')
                self.re_load = False
            elif selection == cf.WORDS['Options']:
                gameStateObj.stateMachine.changeState('config_menu')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Unit']:
                gameStateObj.stateMachine.changeState('unit_menu')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Turnwheel']:
                if cf.OPTIONS['cheat'] or gameStateObj.game_constants.get('current_turnwheel_uses', 1) > 0:
                # if gameStateObj.game_constants.get('current_turnwheel_uses', 1) > 0:
                    gameStateObj.stateMachine.changeState('turnwheel')
                else:
                    banner = Banner.customBanner(cf.WORDS['Turnwheel_empty'])
                    banner.sound = GC.SOUNDDICT['Error']
                    gameStateObj.banners.append(banner)
                    gameStateObj.stateMachine.changeState('itemgain')
                    self.re_load = False

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.drawInfo(mapSurf)
        gameStateObj.cursor.drawPortraits(mapSurf, gameStateObj)
        return mapSurf

class OptionChildState(StateMachine.State):
    name = 'optionchild'

    def begin(self, gameStateObj, metaDataObj):
        # Create child menu with additional options
        if gameStateObj.activeMenu:
            options = [cf.WORDS['Yes'], cf.WORDS['No']]
            selection = gameStateObj.shared_state_data['option_owner']
            self.menu = MenuFunctions.ChoiceMenu(selection, options, 'child', gameStateObj=gameStateObj)
        else:
            # gameStateObj.stateMachine.back()
            self.menu = None

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveUp()

        # Back - to optionsmenu state
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            selection = self.menu.getSelection()
            if selection == cf.WORDS['Yes']:
                GC.SOUNDDICT['Select 1'].play()
                if self.menu.owner == cf.WORDS['End']:
                    # gameStateObj.stateMachine.changeState('turn_change')
                    gameStateObj.stateMachine.changeState('ai')
                    gameStateObj.activeMenu = None
                elif self.menu.owner == cf.WORDS['Suspend']:
                    gameStateObj.stateMachine.back() # Go all the way back if we choose YES
                    gameStateObj.stateMachine.back()
                    logger.info('Suspending game...')
                    SaveLoad.suspendGame(gameStateObj, 'Suspend', hard_loc='Suspend')
                    gameStateObj.save_slots = None # Reset save slots
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('start_start')
                    gameStateObj.activeMenu = None
                elif self.menu.owner == cf.WORDS['Save']:
                    gameStateObj.stateMachine.back()
                    gameStateObj.stateMachine.back()
                    logger.info('Creating battle save...')
                    gameStateObj.save_kind = 'Battle'
                    gameStateObj.stateMachine.changeState('start_save')
                    gameStateObj.stateMachine.changeState('transition_out')
                    gameStateObj.activeMenu = None
                elif self.menu.owner in (cf.WORDS['Discard'], cf.WORDS['Storage']):
                    item = gameStateObj.shared_state_data['option_item']
                    cur_unit = gameStateObj.shared_state_data['option_unit']
                    if item in cur_unit.items:
                        Action.do(Action.DiscardItem(gameStateObj.activeMenu.owner, item), gameStateObj)
                    gameStateObj.activeMenu.currentSelection = 0 # Reset selection?
                    if cur_unit.items: # If the unit still has some items
                        gameStateObj.stateMachine.back()
                        gameStateObj.stateMachine.back()
                    else: # If the unit has no more items, head all the way back to menu.
                        gameStateObj.activeMenu = None
                        gameStateObj.stateMachine.back()
                        gameStateObj.stateMachine.back()
                        gameStateObj.stateMachine.back()
            else:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        self.menu = None # Remove menu

class MoveState(StateMachine.State):
    name = 'move'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 1
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        cur_unit.sprite.change_state('selected', gameStateObj)
        # Set moves
        # gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
        self.validMoves = cur_unit.getValidMoves(gameStateObj)
        if not cur_unit.hasAttacked and not cur_unit.hasTraded:
            if cur_unit.getMainSpell():
                cur_unit.displayExcessSpellAttacks(gameStateObj, self.validMoves)
            if cur_unit.getMainWeapon():
                cur_unit.displayExcessAttacks(gameStateObj, self.validMoves)
        cur_unit.displayMoves(gameStateObj, self.validMoves)
        Aura.add_aura_highlights(cur_unit, gameStateObj)

        gameStateObj.cursor.place_arrows(gameStateObj)

        # Play move script if it exists
        if not self.started:
            global_move_script_name = 'Data/global_moveScript.txt'
            if os.path.exists(global_move_script_name):
                global_move_script = Dialogue.Dialogue_Scene(global_move_script_name, unit=cur_unit)
                gameStateObj.message.append(global_move_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')
            move_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/moveScript.txt'
            if os.path.exists(move_script_name):
                move_script = Dialogue.Dialogue_Scene(move_script_name, unit=cur_unit)
                gameStateObj.message.append(move_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        gameStateObj.cursor.take_input(eventList, gameStateObj)
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        # Show R unit status screen
        if event == 'INFO':
            unit = gameStateObj.grid_manager.get_unit_node(gameStateObj.cursor.position)
            if unit:
                CustomObjects.handle_info_key(gameStateObj, metaDataObj, unit, no_movement=True)

        elif event == 'AUX':
            gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
            gameStateObj.allarrows = []

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('free')
            if cur_unit.hasAttacked or cur_unit.hasTraded: # If canto already attacked or traded, can't bizz out.
                cur_unit.wait(gameStateObj)
            else:
                cur_unit.sprite.change_state('normal', gameStateObj)
            # gameStateObj.stateMachine.back() does not work, cause sometimes the last state is actually menu, not free

        elif event == 'SELECT':
            # If cursor is in same position
            if gameStateObj.cursor.position == cur_unit.position:
                GC.SOUNDDICT['Select 2'].play()
                if cur_unit.hasAttacked or cur_unit.hasTraded: # If canto already attacked.
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('free')
                    cur_unit.wait(gameStateObj)
                else:
                    cur_unit.current_move_action = Action.Move(cur_unit, gameStateObj.cursor.position)
                    Action.execute(cur_unit.current_move_action, gameStateObj)
                    gameStateObj.stateMachine.changeState('menu')

            # If the cursor is on a validMove that is not contiguous with a unit
            elif gameStateObj.cursor.position in self.validMoves:
                if gameStateObj.grid_manager.get_unit_node(gameStateObj.cursor.position):
                    GC.SOUNDDICT['Error'].play()
                else:
                    # SOUND - Footstep sounds but no select sound
                    if cur_unit.hasAttacked or cur_unit.hasTraded:
                        cur_unit.current_move_action = Action.CantoMove(cur_unit, gameStateObj.cursor.position)
                        """gameStateObj.stateMachine.clear()
                        gameStateObj.stateMachine.changeState('free')
                        cur_unit.wait(gameStateObj) # Canto"""
                        # Instead go to wait select
                        gameStateObj.stateMachine.changeState('canto_wait')
                    else:
                        cur_unit.current_move_action = Action.Move(cur_unit, gameStateObj.cursor.position)
                        gameStateObj.stateMachine.changeState('menu')
                    gameStateObj.stateMachine.changeState('movement')
                    Action.do(cur_unit.current_move_action, gameStateObj)

            else:
                GC.SOUNDDICT['Error'].play()

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.border_position = None
        gameStateObj.allarrows = []
        gameStateObj.remove_fake_cursors()
        gameStateObj.highlight_manager.remove_highlights()
        # gameStateObj.boundary_manager.draw_flag = 0

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.cursor.drawPortraits(mapSurf, gameStateObj)
        return mapSurf

class CantoWaitState(StateMachine.State):
    name = 'canto_wait'

    def begin(self, gameStateObj, metaDataObj):
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        cur_unit.sprite.change_state('selected', gameStateObj)
        # Create menu
        gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(cur_unit, [cf.WORDS['Wait']], 'auto', gameStateObj=gameStateObj)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        # Show R unit status screen
        if event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, cur_unit, one_unit_only=True)

        elif event == 'SELECT':
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('free')
            cur_unit.wait(gameStateObj) # Canto

        elif event == 'BACK':
            cur_unit.move_back(gameStateObj)
            gameStateObj.stateMachine.back()

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None

class MenuState(StateMachine.State):
    name = 'menu'
    normal_options = {cf.WORDS[word] for word in ['Item', 'Wait', 'Take', 'Give', 'Rescue', 'Trade', 'Drop', 
        'Convoy', 'Visit', 'Armory', 'Vendor', 'Spells', 'Attack', 'Steal', 'Shove']}

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        # gameStateObj.boundary_manager.draw_flag = 1
        # Somehow?
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        if not cur_unit:
            logger.error('Somehow ended up in MenuState without a current selected unit...')
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('free')
            return

        #if cur_unit.has_canto():
        #    ValidMoves = cur_unit.getValidMoves(gameStateObj)
        #else:
        ValidMoves = [cur_unit.position]

        if not cur_unit.hasAttacked:
            cur_unit.sprite.change_state('menu', gameStateObj)
            spell_targets = cur_unit.getAllSpellTargetPositions(gameStateObj)
            atk_targets = cur_unit.getAllTargetPositions(gameStateObj)
        else:
            cur_unit.sprite.change_state('selected', gameStateObj)
            spell_targets = None
            atk_targets = None

        if spell_targets:
            cur_unit.displayExcessSpellAttacks(gameStateObj, ValidMoves)
        if atk_targets:
            cur_unit.displayExcessAttacks(gameStateObj, ValidMoves)
        if cur_unit.has_canto():
            # Shows the canto moves in the menu
            # if not gameStateObj.allhighlights:
            CantoMoves = cur_unit.getValidMoves(gameStateObj)
            cur_unit.displayMoves(gameStateObj, CantoMoves)
        Aura.add_aura_highlights(cur_unit, gameStateObj)

        # Play menu script if it exists
        if not self.started:
            menu_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/menuScript.txt'
            if os.path.exists(menu_script_name):
                menu_script = Dialogue.Dialogue_Scene(menu_script_name, unit=cur_unit)
                gameStateObj.message.append(menu_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')

        # Play sound on first creation
        GC.SOUNDDICT['Select 2'].play()
        options = []
        # Find adjacent positions
        gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
        cur_unit.current_skill = None

        adjtiles = cur_unit.getAdjacentTiles(gameStateObj)
        adjpositions = cur_unit.getAdjacentPositions(gameStateObj)
        current_unit_positions = [unit.position for unit in gameStateObj.allunits]
        adjunits = [unit for unit in gameStateObj.allunits if unit.position in adjpositions]
        adjallies = [unit for unit in adjunits if cur_unit.checkIfAlly(unit)]

        # If the unit is standing on a throne
        if 'Seize' in gameStateObj.map.tile_info_dict[cur_unit.position]:
            options.append(cf.WORDS['Seize'])
        elif 'Lord_Seize' in gameStateObj.map.tile_info_dict[cur_unit.position] and 'Lord' in cur_unit.tags:
            options.append(cf.WORDS['Seize'])
        # If the unit is standing on an escape tile
        if 'Escape' in gameStateObj.map.tile_info_dict[cur_unit.position]:
            options.append(cf.WORDS['Escape'])
        elif 'Arrive' in gameStateObj.map.tile_info_dict[cur_unit.position]:
            options.append(cf.WORDS['Arrive'])
        if 'Weapon' in gameStateObj.map.tile_info_dict[cur_unit.position]:
            weapon = gameStateObj.map.tile_info_dict[cur_unit.position]['Weapon']
            if cur_unit.canWield(weapon) and cur_unit.canUse(weapon):
                options.append(weapon.name)
        # If the unit is standing on a switch
        if 'Switch' in gameStateObj.map.tile_info_dict[cur_unit.position]:
            options.append(cf.WORDS['Switch'])
        # If the unit has validTargets
        if atk_targets:
            options.append(cf.WORDS['Attack'])
        # If the unit has a spell
        if spell_targets:
            options.append(cf.WORDS['Spells'])
        # Active Skills
        if not cur_unit.hasAttacked:
            for status in cur_unit.status_effects:
                if status.combat_art and status.combat_art.is_activated() and status.combat_art.check_charged():
                    if status.combat_art.basic_check(cur_unit, gameStateObj) and \
                            status.combat_art.check_valid(cur_unit, gameStateObj):
                        options.append(status.name)
                if status.activated_item and status.activated_item.check_charged():
                    if status.activated_item.check_valid(cur_unit, gameStateObj):
                        options.append(status.name)
                if status.steal and len(cur_unit.items) < cf.CONSTANTS['max_items'] and cur_unit.getStealPartners(gameStateObj):
                    options.append(cf.WORDS['Steal'])
        if 'Mindless' not in cur_unit.tags:
            # If the unit is adjacent to a unit it can talk to
            for adjunit in adjunits:
                if (cur_unit.name, adjunit.name) in gameStateObj.talk_options:
                    options.append(cf.WORDS['Talk'])
                    break
            # If supports happen in battle
            if cf.CONSTANTS['support'] == 1 and 'Supports' in gameStateObj.game_constants:
                for adjunit in adjunits:
                    if gameStateObj.support.can_support(cur_unit.id, adjunit.id):
                        options.append(cf.WORDS['Support'])
                        break
            # If the unit is on an arena tile
            if 'Arena' in gameStateObj.map.tile_info_dict[cur_unit.position]:
                options.append(cf.WORDS['Arena'])
            # If the unit is on a village tile
            if 'Village' in gameStateObj.map.tile_info_dict[cur_unit.position]:
                options.append(cf.WORDS['Visit'])
            # If the unit is on a shop tile
            if 'Shop' in gameStateObj.map.tile_info_dict[cur_unit.position]:
                if gameStateObj.map.tiles[cur_unit.position].name == cf.WORDS['Armory']:
                    options.append(cf.WORDS['Armory'])
                else:
                    options.append(cf.WORDS['Vendor'])
            # If the unit is on a repair shop tile
            if 'Repair' in gameStateObj.map.tile_info_dict[cur_unit.position]:
                options.append(cf.WORDS['Repair'])
            # If the unit is on or adjacent to an unlockable door or on a treasure chest
            if not cur_unit.hasAttacked:
                tile_info = gameStateObj.map.tile_info_dict
                tiles = gameStateObj.map.tiles
                unlock_key = cur_unit.get_unlock_key()
                if 'locktouch' in cur_unit.status_bundle:
                    if cf.WORDS['Locked'] in tile_info[cur_unit.position]:
                        options.append(cf.WORDS['Unlock'])
                    elif any(cf.WORDS['Locked'] in tile_info[tile.position] for tile in adjtiles):
                        options.append(cf.WORDS['Unlock'])
                elif unlock_key:
                    if cf.WORDS['Locked'] in tile_info[cur_unit.position] and tiles[cur_unit.position].name in unlock_key.key.split(','):
                        options.append(cf.WORDS['Unlock'])
                    else:
                        for tile in adjtiles:
                            if cf.WORDS['Locked'] in tile_info[tile.position] and tile.name in unlock_key.key.split(','):
                                options.append(cf.WORDS['Unlock'])
                                break
            # If the unit is on a searchable tile
            if 'Search' in gameStateObj.map.tile_info_dict[cur_unit.position] and not cur_unit.hasAttacked:
                options.append(cf.WORDS['Search'])
            # If the unit has a traveler
            if cur_unit.TRV and not cur_unit.hasAttacked: # (len(set(adjposition) | set(current_unit_positions)) > len(set(current_unit_positions)))
                for adjposition in adjpositions:
                    # if at least one adjacent, passable position is free of units
                    tile = gameStateObj.map.tiles[adjposition]
                    trv = gameStateObj.get_unit_from_id(cur_unit.TRV)
                    if not (adjposition in current_unit_positions) and tile.get_mcost(trv) < trv.stats['MOV']:
                        options.append(cf.WORDS['Drop'])
                        break
            if adjallies:
                # If the unit does not have a traveler
                if not cur_unit.TRV and not cur_unit.hasAttacked:
                    # AID has to be higher than CON
                    if any((adjally.getWeight() <= cur_unit.getAid() and not adjally.TRV) for adjally in adjallies):
                        options.append(cf.WORDS['Rescue'])
                    if any((adjally.TRV and gameStateObj.get_unit_from_id(adjally.TRV).getWeight() <= cur_unit.getAid()) for adjally in adjallies):
                        options.append(cf.WORDS['Take'])
                # If the unit has a traveler
                if cur_unit.TRV and not cur_unit.hasAttacked:
                    if any((adjally.getAid() >= gameStateObj.get_unit_from_id(cur_unit.TRV).getWeight() and not adjally.TRV) for adjally in adjallies):
                        options.append(cf.WORDS['Give'])
            # If the unit has an item
            if cur_unit.items:
                options.append(cf.WORDS['Item'])
            if adjallies:
                # Check rescued units also
                for unit in adjallies:
                    if unit.TRV:
                        adjallies.append(gameStateObj.get_unit_from_id(unit.TRV))
                if any([unit.team == cur_unit.team for unit in adjallies]):
                    options.append(cf.WORDS['Trade'])
            # If the unit has access to the convoy
            if gameStateObj.game_constants['Convoy'] and 'Convoy' in cur_unit.tags:
                options.append(cf.WORDS['Convoy'])
            elif gameStateObj.game_constants['Convoy'] and adjallies:
                if any(['AdjConvoy' in unit.tags and unit.team == cur_unit.team for unit in adjallies]):
                    options.append(cf.WORDS['Convoy'])
        options.append(cf.WORDS['Wait'])

        # Filter by legal options here
        if gameStateObj.tutorial_mode:
            t_options = [option for option in options if option == gameStateObj.tutorial_mode]
            if t_options:
                options = t_options

        if options:
            opt_color = ['text_green' if option not in self.normal_options else 'text_white' for option in options]
            gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(cur_unit, options, 'auto', limit=8, color_control=opt_color, gameStateObj=gameStateObj)
        else:
            logger.error('Somehow ended up in menu with no options!')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        cur_unit = gameStateObj.cursor.currentSelectedUnit

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)

        # Back - Put unit back to where he/she started
        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if cur_unit.hasAttacked or cur_unit.hasTraded:
                if cur_unit.has_canto():
                    # Don't display excess attacks, because I have already attacked...
                    gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
                    gameStateObj.stateMachine.changeState('move')
                else:
                    # I've already done something that qualifies for taking away my attack, which means I don't get to move back to where I started
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('free')
                    cur_unit.wait(gameStateObj)
            else:
                # puts unit back - handles status
                cur_unit.move_back(gameStateObj)
                # cur_unit.reset()
                gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
                gameStateObj.stateMachine.changeState('move')

        # Show R unit status screen
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, cur_unit, one_unit_only=True)

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            cur_unit = cur_unit
            selection = gameStateObj.activeMenu.getSelection()
            logger.debug('Player selected %s', selection)
            gameStateObj.highlight_manager.remove_highlights()

            # Only applies to statuses that are combat arts or have activated items
            if selection in [status.name for status in cur_unit.status_effects if status.combat_art or status.activated_item]:
                for status in cur_unit.status_effects:
                    if selection == status.name:
                        if status.combat_art:
                            status_obj = StatusCatalog.statusparser(status.combat_art.status_id, gameStateObj)
                            status.add_action = Action.AddStatus(cur_unit, status_obj)
                            Action.do(status.add_action, gameStateObj)
                            cur_unit.current_skill = status
                            gameStateObj.stateMachine.changeState('weapon')
                        elif status.activated_item:
                            valid_choices = status.activated_item.get_choices(cur_unit, gameStateObj)
                            if valid_choices:
                                cur_unit.validPartners = CustomObjects.MapSelectHelper(valid_choices)
                                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                                cur_unit.current_skill = status
                                gameStateObj.stateMachine.changeState('skillselect')
                            else:
                                skill_item = status.activated_item.item
                                main_defender, splash_units = Interaction.convert_positions(gameStateObj, cur_unit, cur_unit.position, cur_unit.position, skill_item)
                                gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, cur_unit, main_defender, cur_unit.position, splash_units, skill_item, status)
                                gameStateObj.stateMachine.changeState('combat')

            elif 'Weapon' in gameStateObj.map.tile_info_dict[cur_unit.position] and selection == gameStateObj.map.tile_info_dict[cur_unit.position]['Weapon'].name:
                gameStateObj.stateMachine.changeState('tileattack')
            elif selection == cf.WORDS['Attack']:
                gameStateObj.stateMachine.changeState('weapon')
            elif selection == cf.WORDS['Spells']:
                gameStateObj.stateMachine.changeState('spellweapon')
            elif selection == cf.WORDS['Item']:
                gameStateObj.stateMachine.changeState('item')
            elif selection == cf.WORDS['Trade']:
                valid_choices = [unit.position for unit in cur_unit.getTeamPartners(gameStateObj)]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(valid_choices)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('tradeselect')
            elif selection == cf.WORDS['Steal']:
                valid_choices = [unit.position for unit in cur_unit.getStealPartners(gameStateObj)]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(valid_choices)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('stealselect')
            elif selection == cf.WORDS['Rescue']:
                good_positions = [unit.position for unit in cur_unit.getValidPartners(gameStateObj)
                                  if unit.getWeight() <= cur_unit.getAid() and not unit.TRV]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(good_positions)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('rescueselect')
            elif selection == cf.WORDS['Take']:
                good_positions = [unit.position for unit in cur_unit.getValidPartners(gameStateObj) if unit.TRV and
                                  gameStateObj.get_unit_from_id(unit.TRV).getWeight() <= cur_unit.getAid()]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(good_positions)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('takeselect')
            elif selection == cf.WORDS['Drop']:
                good_positions = []
                for pos in cur_unit.getAdjacentPositions(gameStateObj):
                    tile = gameStateObj.map.tiles[pos]
                    trv = gameStateObj.get_unit_from_id(cur_unit.TRV)
                    if tile.get_mcost(trv) < trv.stats['MOV'] and not any(pos == unit.position for unit in gameStateObj.allunits):
                        good_positions.append(pos)
                cur_unit.validPartners = CustomObjects.MapSelectHelper(good_positions)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('dropselect')
            elif selection == cf.WORDS['Give']:
                good_positions = [unit.position for unit in cur_unit.getTeamPartners(gameStateObj) if not unit.TRV and
                                  unit.getAid() >= gameStateObj.get_unit_from_id(cur_unit.TRV).getWeight()]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(good_positions)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('giveselect')
            elif selection == cf.WORDS['Visit']:
                village_name = gameStateObj.map.tile_info_dict[cur_unit.position][cf.WORDS['Village']]
                village_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/villageScript.txt'
                if os.path.exists(village_script):
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(village_script, unit=cur_unit, name=village_name, tile_pos=cur_unit.position))
                    gameStateObj.stateMachine.changeState('dialogue')
                else:
                    logger.error("%s does not exist!", village_script)
                Action.do(Action.HasAttacked(cur_unit), gameStateObj)
            elif selection == cf.WORDS['Arena']:
                gameStateObj.stateMachine.changeState('arena')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Armory']:
                gameStateObj.stateMachine.changeState('armory')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Vendor']:
                gameStateObj.stateMachine.changeState('vendor')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Repair']:
                gameStateObj.stateMachine.changeState('repair_shop')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Seize']:
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('free')
                cur_unit.seize(gameStateObj)
            elif selection in (cf.WORDS['Escape'], cf.WORDS['Arrive']):
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('free')
                cur_unit.escape(gameStateObj)
            elif selection == cf.WORDS['Switch']:
                Action.do(Action.HasAttacked(cur_unit), gameStateObj)
                switch_name = gameStateObj.map.tile_info_dict[cur_unit.position][cf.WORDS['Switch']]
                switch_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/switchScript.txt'
                if os.path.exists(switch_script):
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(switch_script, unit=cur_unit, name=switch_name, tile_pos=cur_unit.position))
                    gameStateObj.stateMachine.changeState('dialogue')
                else:
                    logger.error('%s does not exist!', switch_script)
            elif selection == cf.WORDS['Unlock']:
                avail_pos = [pos for pos in cur_unit.getAdjacentPositions(gameStateObj) + [cur_unit.position] if cf.WORDS['Locked'] in gameStateObj.map.tile_info_dict[pos]]
                if len(avail_pos) > 1:
                    cur_unit.validPartners = CustomObjects.MapSelectHelper(avail_pos)
                    closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                    gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                    gameStateObj.stateMachine.changeState('unlockselect')
                elif len(avail_pos) == 1:
                    item = cur_unit.get_unlock_key()
                    cur_unit.unlock(avail_pos[0], item, gameStateObj)
                else:
                    logger.error('Made a mistake in allowing unit to access Unlock!')
            elif selection == cf.WORDS['Search']:
                search_name = gameStateObj.map.tile_info_dict[cur_unit.position][cf.WORDS['Search']]
                search_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/searchScript.txt'
                gameStateObj.message.append(Dialogue.Dialogue_Scene(search_script, unit=cur_unit, name=search_name, tile_pos=cur_unit.position))
                gameStateObj.stateMachine.changeState('dialogue')
                Action.do(Action.HasAttacked(cur_unit), gameStateObj)
            elif selection == cf.WORDS['Talk']:
                positions = [unit.position for unit in gameStateObj.allunits if unit.position in cur_unit.getAdjacentPositions(gameStateObj) and
                             (cur_unit.name, unit.name) in gameStateObj.talk_options]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(positions)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('talkselect')
            elif selection == cf.WORDS['Support']:
                positions = [unit.position for unit in gameStateObj.allunits if unit.position in cur_unit.getAdjacentPositions(gameStateObj) and
                             gameStateObj.support.can_support(cur_unit.id, unit.id)]
                cur_unit.validPartners = CustomObjects.MapSelectHelper(positions)
                closest_position = cur_unit.validPartners.get_closest(cur_unit.position)
                gameStateObj.cursor.setPosition(closest_position, gameStateObj)
                gameStateObj.stateMachine.changeState('supportselect')
            elif selection == cf.WORDS['Convoy']:
                gameStateObj.stateMachine.changeState('convoy_transfer')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Wait']:
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('free')
                cur_unit.wait(gameStateObj)

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        gameStateObj.highlight_manager.remove_highlights()

class ItemState(StateMachine.State):
    name = 'item'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.info_surf = None
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        options = [item for item in cur_unit.items]
        if not gameStateObj.activeMenu:
            gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(cur_unit, options, 'auto', gameStateObj=gameStateObj)
        else:
            gameStateObj.activeMenu.updateOptions(options)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        gameStateObj.activeMenu.updateOptions(gameStateObj.cursor.currentSelectedUnit.items)
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
            gameStateObj.info_surf = None
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)
            gameStateObj.info_surf = None

        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.activeMenu = None
            gameStateObj.stateMachine.changeState('menu')

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            gameStateObj.stateMachine.changeState('itemchild')

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            gameStateObj.cursor.currentSelectedUnit.drawItemDescription(mapSurf, gameStateObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.drawInfo(mapSurf)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.info_surf = None

class ItemChildState(StateMachine.State):
    name = 'itemchild'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.info_surf = None
        selection = gameStateObj.activeMenu.getSelection()
        current_unit = gameStateObj.cursor.currentSelectedUnit
        # Create child menu with additional options
        options = []
        if selection.weapon and current_unit.canWield(selection) and current_unit.canUse(selection):
            options.append(cf.WORDS['Equip'])
        if selection.usable and current_unit.canUse(selection):
            use = True
            if selection.heal and current_unit.currenthp >= current_unit.stats['HP']:
                use = False
            elif selection.c_uses and selection.c_uses.uses <= 0:
                use = False
            elif selection.cooldown and not selection.cooldown.charged:
                use = False
            elif selection.booster and not current_unit.can_use_booster(selection):
                use = False
            elif selection.target_restrict and not eval(selection.target_restrict):
                use = False
            if use:
                options.append(cf.WORDS['Use'])
        if not selection.locked:
            if 'Convoy' in gameStateObj.game_constants:
                options.append(cf.WORDS['Storage'])
            else:
                options.append(cf.WORDS['Discard'])

        if not options:
            options.append(cf.WORDS['Placeholder'])

        self.menu = MenuFunctions.ChoiceMenu(selection, options, 'child', gameStateObj=gameStateObj)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        cur_unit = gameStateObj.activeMenu.owner

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play(first_push)
            self.menu.moveDown()
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play(first_push)
            self.menu.moveUp()

        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            item = self.menu.owner
            if selection == cf.WORDS['Use']:
                if item.booster: # Does not use interact object
                    if cur_unit.items: # If the unit still has some items
                        gameStateObj.stateMachine.back()
                    else: # If the unit has no more items, head all the way back to menu.
                        gameStateObj.activeMenu = None
                        gameStateObj.stateMachine.back()
                        gameStateObj.stateMachine.back()
                    # Using a booster counts as an action
                    Action.do(Action.HasAttacked(cur_unit), gameStateObj)
                    gameStateObj.stateMachine.changeState('free')
                    gameStateObj.stateMachine.changeState('wait')
                    gameStateObj.activeMenu = None
                    self.menu = None
                    gameStateObj.cursor.currentSelectedUnit.handle_booster(item, gameStateObj)
                else: # Uses interaction object
                    cur_unit = gameStateObj.cursor.currentSelectedUnit
                    gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, cur_unit, cur_unit, cur_unit.position, [], self.menu.owner)
                    gameStateObj.activeMenu = None
                    gameStateObj.stateMachine.changeState('combat')
            elif selection == cf.WORDS['Equip']:
                Action.do(Action.EquipItem(cur_unit, item), gameStateObj)
                gameStateObj.activeMenu.currentSelection = 0 # Reset selection?
                gameStateObj.stateMachine.back()
            elif selection == cf.WORDS['Storage'] or selection == cf.WORDS['Discard']:
                gameStateObj.shared_state_data['option_owner'] = selection
                gameStateObj.shared_state_data['option_item'] = item
                gameStateObj.shared_state_data['option_unit'] = cur_unit
                gameStateObj.stateMachine.changeState('optionchild')

    def end(self, gameStateObj, metaDataObj):
        self.menu = None
        gameStateObj.info_surf = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            gameStateObj.cursor.currentSelectedUnit.drawItemDescription(mapSurf, gameStateObj)
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)
        return mapSurf

class WeaponState(StateMachine.State):
    name = 'weapon'

    def get_options(self, unit, gameStateObj):
        options = [item for item in unit.items if item.weapon and unit.canWield(item) and unit.canUse(item)]  # Apply straining for skill
        if unit.current_skill:
            options = unit.current_skill.combat_art.valid_weapons(unit, options)
        # Only shows options I can use now
        options = [item for item in options if unit.getValidTargetPositions(gameStateObj, item)]
        return options

    def disp_attacks(self, unit, gameStateObj):
        unit.displayAttacks(gameStateObj, gameStateObj.activeMenu.getSelection())

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.info_surf = None
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        cur_unit.sprite.change_state('chosen', gameStateObj)
        options = self.get_options(cur_unit, gameStateObj)
        gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(cur_unit, options, 'auto', gameStateObj=gameStateObj)
        self.disp_attacks(cur_unit, gameStateObj)

    def proceed(self, gameStateObj):
        gameStateObj.stateMachine.changeState('attack')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.info_surf = None
            gameStateObj.activeMenu.moveDown(first_push)
            gameStateObj.highlight_manager.remove_highlights()
            self.disp_attacks(cur_unit, gameStateObj)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.info_surf = None
            gameStateObj.activeMenu.moveUp(first_push)
            gameStateObj.highlight_manager.remove_highlights()
            self.disp_attacks(cur_unit, gameStateObj)

        if event == 'BACK' and not gameStateObj.tutorial_mode:
            GC.SOUNDDICT['Select 4'].play()
            if cur_unit.current_skill:
                Action.reverse(cur_unit.current_skill.add_action, gameStateObj)
                cur_unit.current_skill = None
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            Action.do(Action.EquipItem(cur_unit, selection), gameStateObj)
            self.proceed(gameStateObj)

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            gameStateObj.cursor.currentSelectedUnit.drawItemDescription(mapSurf, gameStateObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.drawInfo(mapSurf)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        gameStateObj.highlight_manager.remove_highlights()
        gameStateObj.info_surf = None

class SpellWeaponState(WeaponState):
    name = 'spellweapon'

    def get_options(self, unit, gameStateObj):
        options = [item for item in unit.items if item.spell and unit.canWield(item) and unit.canUse(item)]
        # Only shows options I can use
        options = [item for item in options if unit.getValidSpellTargetPositions(gameStateObj, item)]
        return options

    def disp_attacks(self, unit, gameStateObj):
        unit.displaySpellAttacks(gameStateObj, gameStateObj.activeMenu.getSelection())

    def proceed(self, gameStateObj):
        gameStateObj.stateMachine.changeState('spell')

class AttackState(StateMachine.State):
    name = 'attack'

    def get_weapon(self, unit, gameStateObj):
        return unit.getMainWeapon()

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 2
        self.attacker = gameStateObj.cursor.currentSelectedUnit
        weapon = self.get_weapon(self.attacker, gameStateObj)
        self.validTargets = CustomObjects.MapSelectHelper(self.attacker.getValidTargetPositions(gameStateObj, weapon))
        closest_position = self.validTargets.get_closest(gameStateObj.cursor.position)
        gameStateObj.cursor.setPosition(closest_position, gameStateObj)
        gameStateObj.highlight_manager.remove_highlights()
        gameStateObj.info_surf = None
        self.attacker.attack_info_offset = 80
        self.attacker.displaySingleAttack(gameStateObj, gameStateObj.cursor.position)

        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed'])

        # Play attack script if it exists
        attack_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/attackScript.txt'
        if os.path.exists(attack_script_name):
            attack_script = Dialogue.Dialogue_Scene(attack_script_name, unit=self.attacker)
            gameStateObj.message.append(attack_script)
            gameStateObj.stateMachine.changeState('transparent_dialogue')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            # Get closest unit in down position
            new_position = self.validTargets.get_down(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        elif 'UP' in directions:
            # Get closet unit in up position
            new_position = self.validTargets.get_up(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        if 'LEFT' in directions:
            # Get closest unit in left position
            new_position = self.validTargets.get_left(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        elif 'RIGHT' in directions:
            # Get closest unit in right position
            new_position = self.validTargets.get_right(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)

        # Go back to weapon choice
        if event == 'BACK':
            GC.SOUNDDICT['Select 2'].play()
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            attacker = gameStateObj.cursor.currentSelectedUnit
            defender, splash = Interaction.convert_positions(gameStateObj, attacker, attacker.position, gameStateObj.cursor.position, attacker.getMainWeapon())
            gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, attacker, defender, gameStateObj.cursor.position, splash, attacker.getMainWeapon(), attacker.current_skill)
            gameStateObj.stateMachine.changeState('combat')
            attacker.current_skill = None
            # Handle fight quote
            if defender and isinstance(defender, UnitObject.UnitObject):
                defender.handle_fight_quote(attacker, gameStateObj)

        if directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.info_surf = None
            gameStateObj.highlight_manager.remove_highlights()
            self.attacker.displaySingleAttack(gameStateObj, gameStateObj.cursor.position)

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.highlight_manager.remove_highlights()
        gameStateObj.info_surf = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.cursor.currentSelectedUnit and gameStateObj.cursor.currentHoveredUnit:
            gameStateObj.cursor.currentSelectedUnit.displayAttackInfo(mapSurf, gameStateObj, gameStateObj.cursor.currentHoveredUnit)
        gameStateObj.cursor.currentHoveredTile = gameStateObj.map.tiles[gameStateObj.cursor.position]
        if gameStateObj.cursor.currentHoveredTile and 'HP' in gameStateObj.map.tile_info_dict[gameStateObj.cursor.currentHoveredTile.position]:
            gameStateObj.cursor.currentSelectedUnit.displayAttackInfo(mapSurf, gameStateObj, gameStateObj.cursor.currentHoveredTile)
        return mapSurf

class TileAttackState(AttackState):
    name = 'tileattack'

    def get_weapon(self, unit, gameStateObj):
        weapon = gameStateObj.map.tile_info_dict[unit.position]['Weapon']
        return weapon

class SpellState(StateMachine.State):
    name = 'spell'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 2
        gameStateObj.info_surf = None
        attacker = gameStateObj.cursor.currentSelectedUnit
        spell = attacker.getMainSpell()
        valid_targets = attacker.getValidSpellTargetPositions(gameStateObj)
        # If there are valid targets for this weapon
        if valid_targets:
            attacker.validSpellTargets = CustomObjects.MapSelectHelper(valid_targets)
            if spell.heal:
                units = sorted([gameStateObj.grid_manager.get_unit_node(pos) for pos in valid_targets],
                               key=lambda unit: unit.currenthp)
                closest_position = units[0].position
            else:
                closest_position = attacker.validSpellTargets.get_closest(attacker.position)
            gameStateObj.cursor.setPosition(closest_position, gameStateObj)
        else: # syntactic sugar
            logger.error('SpellState has no valid targets! Mistakes were made.')
            # No valid targets, means this stays the same. They can choose another weapon or something
        attacker.displaySpellAttacks(gameStateObj)
        attacker.displaySingleAttack(gameStateObj, gameStateObj.cursor.position, item=spell)

        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed'])

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        attacker = gameStateObj.cursor.currentSelectedUnit
        if 'DOWN' in directions:
            # Get closet unit in down position
            new_position = attacker.validSpellTargets.get_down(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        elif 'UP' in directions:
            # Get closet unit in up position
            new_position = attacker.validSpellTargets.get_up(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        if 'LEFT' in directions:
            # Get closest unit in left position
            new_position = attacker.validSpellTargets.get_left(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        elif 'RIGHT' in directions:
            # Get closest unit in right position
            new_position = attacker.validSpellTargets.get_right(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)

        # Show R unit status screen
        if event == 'INFO':
            pass
            # TODO Display information about spell

        # Go back to weapon choice
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            spell = attacker.getMainSpell()
            self.reapply_old_values(spell)
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            spell = attacker.getMainSpell()
            targets = spell.spell.targets
            gameStateObj.cursor.currentHoveredUnit = [unit for unit in gameStateObj.allunits if unit.position == gameStateObj.cursor.position]
            gameStateObj.cursor.currentHoveredTile = gameStateObj.map.tiles[gameStateObj.cursor.position]
            if targets in ('Enemy', 'Ally', 'Unit') and gameStateObj.cursor.currentHoveredUnit:
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.currentHoveredUnit[0]
                cur_unit = gameStateObj.cursor.currentHoveredUnit
                if (targets == 'Enemy' and attacker.checkIfEnemy(cur_unit)) \
                        or (targets == 'Ally' and attacker.checkIfAlly(cur_unit)) \
                        or targets == 'Unit':
                    if spell.extra_select and spell.extra_select_index < len(spell.extra_select):
                        self.handle_extra_select(gameStateObj, spell)
                        spell.extra_select_targets.append(cur_unit)  # Must be done after handle_extra_select
                        self.end(gameStateObj, metaDataObj)
                        self.begin(gameStateObj, metaDataObj)
                    elif spell.repair:
                        self.reapply_old_values(spell)
                        Action.do(Action.EquipItem(attacker, spell), gameStateObj)
                        gameStateObj.stateMachine.changeState('repair')
                        GC.SOUNDDICT['Select 1'].play()
                    else:
                        self.reapply_old_values(spell)
                        defender, splash = Interaction.convert_positions(gameStateObj, attacker, attacker.position, cur_unit.position, spell)
                        if spell.extra_select:
                            splash += spell.extra_select_targets
                            spell.extra_select_targets = []
                        gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, attacker, defender, cur_unit.position, splash, spell)
                        gameStateObj.stateMachine.changeState('combat')
                        GC.SOUNDDICT['Select 1'].play()
                        # Handle fight quote
                        if defender and isinstance(defender, UnitObject.UnitObject):
                            defender.handle_fight_quote(attacker, gameStateObj)

            elif targets == 'Tile' or targets == 'TileNoUnit':
                if spell.extra_select and spell.extra_select_index < len(spell.extra_select):
                    self.handle_extra_select(gameStateObj, spell)
                    spell.extra_select_targets.append(gameStateObj.cursor.position)
                    self.end(gameStateObj, metaDataObj)  # Faking moving to a new spell state
                    self.begin(gameStateObj, metaDataObj)
                else:
                    self.reapply_old_values(spell)
                    defender, splash = Interaction.convert_positions(gameStateObj, attacker, attacker.position, gameStateObj.cursor.position, spell)
                    if spell.extra_select:
                        splash += spell.extra_select_targets
                        spell.extra_select_targets = []
                    if spell.unlock:
                        gameStateObj.stateMachine.changeState('menu')
                        attacker.unlock(gameStateObj.cursor.position, spell, gameStateObj)
                    elif not spell.hit or defender or splash:
                        if not spell.detrimental or (defender and attacker.checkIfEnemy(defender)) or any(attacker.checkIfEnemy(unit) for unit in splash):
                            gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, attacker, defender, gameStateObj.cursor.position, splash, spell)
                            gameStateObj.stateMachine.changeState('combat')
                            GC.SOUNDDICT['Select 1'].play()
                        else:
                            GC.SOUNDDICT['Select 4'].play()
                    else:
                        GC.SOUNDDICT['Select 4'].play()

        if directions:
            spell = attacker.getMainSpell()
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.info_surf = None
            gameStateObj.highlight_manager.remove_highlights('attack')
            gameStateObj.highlight_manager.remove_highlights('splash')
            gameStateObj.highlight_manager.remove_highlights('spell2')
            attacker.displaySingleAttack(gameStateObj, gameStateObj.cursor.position, item=spell)

    def handle_extra_select(self, gameStateObj, spell):
        idx = spell.extra_select_index
        if idx == 0:  # Save true values so we can re-apply them later
            spell.true_targets = spell.spell.targets
            spell.true_RNG = spell.RNG
            spell.extra_select_targets = []
        spell.RNG = spell.extra_select[idx].RNG
        spell.spell.targets = spell.extra_select[idx].targets
        spell.extra_select_index += 1
        # gameStateObj.stateMachine.changeState('spell')
        GC.SOUNDDICT['Select 1'].play()

    def reapply_old_values(self, spell):
        if spell.extra_select and spell.extra_select_index > 0:  # Time to re-apply old values
            spell.extra_select_index = 0
            spell.spell.targets = spell.true_targets
            spell.RNG = spell.true_RNG

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.highlight_manager.remove_highlights()
        gameStateObj.info_surf = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        attacker = gameStateObj.cursor.currentSelectedUnit
        spell = attacker.getMainSpell()
        targets = spell.spell.targets
        if gameStateObj.cursor.currentSelectedUnit:
            if targets == 'Tile' or targets == 'TileNoUnit':
                attacker.displaySpellInfo(mapSurf, gameStateObj)
            elif gameStateObj.cursor.currentHoveredUnit:
                attacker.displaySpellInfo(mapSurf, gameStateObj, gameStateObj.cursor.currentHoveredUnit)
        return mapSurf

class SelectState(StateMachine.State):
    name = 'select'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 2
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        cur_unit.sprite.change_state('chosen', gameStateObj)
        self.pennant = None
        if self.name in cf.WORDS:
            self.pennant = Banner.Pennant(cf.WORDS[self.name])
        self.fluid_helper = InputManager.FluidScroll(cf.OPTIONS['Cursor Speed'])
        self.TRV_select: bool = False

    def take_input(self, eventList, gameStateObj, metaDataObj):
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.TRV_select = False
            # Get closet unit in down position
            if self.name == 'tradeselect':
                target_unit = gameStateObj.grid_manager.get_unit_node(gameStateObj.cursor.position)
                traveler = None
                if target_unit.TRV:
                    traveler = gameStateObj.get_unit_from_id(target_unit.TRV)
                if traveler and traveler.team == cur_unit.team:
                    self.TRV_select = True
                else:
                    new_position = cur_unit.validPartners.get_down(gameStateObj.cursor.position)
                    gameStateObj.cursor.setPosition(new_position, gameStateObj)
            else:
                new_position = cur_unit.validPartners.get_down(gameStateObj.cursor.position)
                gameStateObj.cursor.setPosition(new_position, gameStateObj)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.TRV_select = False
            # Get closet unit in up position
            new_position = cur_unit.validPartners.get_up(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        if 'LEFT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.TRV_select = False
            # Get closest unit in left position
            new_position = cur_unit.validPartners.get_left(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.TRV_select = False
            # Get closest unit in right position
            new_position = cur_unit.validPartners.get_right(gameStateObj.cursor.position)
            gameStateObj.cursor.setPosition(new_position, gameStateObj)

        # INFO button does nothing!
        # Go back to menu choice
        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            if self.name == 'skillselect':
                active_skill = cur_unit.current_skill
                skill_item = active_skill.activated_item.item
                main_defender, splash_units = Interaction.convert_positions(gameStateObj, cur_unit, cur_unit.position, gameStateObj.cursor.position, skill_item)
                gameStateObj.combatInstance = Interaction.start_combat(gameStateObj, cur_unit, main_defender, gameStateObj.cursor.position, splash_units, skill_item, active_skill)
                gameStateObj.stateMachine.changeState('combat')
                cur_unit.current_skill = None
            elif self.name == 'tradeselect':
                if self.TRV_select:
                    target = gameStateObj.grid_manager.get_unit_node(gameStateObj.cursor.position)
                    traveler = gameStateObj.get_unit_from_id(target.TRV)
                    gameStateObj.info_menu_struct['trade_partner'] = traveler
                gameStateObj.stateMachine.changeState('trade')
            elif self.name == 'stealselect':
                gameStateObj.stateMachine.changeState('steal')
            elif self.name == 'rescueselect':
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
                if gameStateObj.cursor.currentHoveredUnit:
                    Action.do(Action.Rescue(cur_unit, gameStateObj.cursor.currentHoveredUnit), gameStateObj)
                    if cur_unit.has_canto():
                        gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
                        gameStateObj.stateMachine.changeState('move')
                    else:
                        gameStateObj.stateMachine.changeState('free')
                        cur_unit.wait(gameStateObj)
                        gameStateObj.cursor.setPosition(cur_unit.position, gameStateObj)
            elif self.name == 'takeselect':
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
                if gameStateObj.cursor.currentHoveredUnit:
                    Action.do(Action.Take(cur_unit, gameStateObj.cursor.currentHoveredUnit), gameStateObj)
                    # Take does not count as a MAJOR action
                    gameStateObj.stateMachine.changeState('menu') # Should this be inside or outside the if statement - Is an error to not get here
            elif self.name == 'giveselect':
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
                if gameStateObj.cursor.currentHoveredUnit:
                    Action.do(Action.Give(cur_unit, gameStateObj.cursor.currentHoveredUnit), gameStateObj)
                    gameStateObj.stateMachine.changeState('menu')
            elif self.name == 'dropselect':
                gameStateObj.stateMachine.changeState('menu')
                drop_me = gameStateObj.get_unit_from_id(cur_unit.TRV)
                Action.do(Action.Drop(cur_unit, drop_me, gameStateObj.cursor.position), gameStateObj)
            elif self.name == 'talkselect':
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
                if gameStateObj.cursor.currentHoveredUnit:
                    # cur_unit.hasTraded = True  # Unit can no longer move back, but can still attack
                    Action.do(Action.HasTraded(cur_unit), gameStateObj)
                    talk_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/talkScript.txt'
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(talk_script, unit=cur_unit, unit2=gameStateObj.cursor.currentHoveredUnit))
                    gameStateObj.stateMachine.changeState('menu')
                    gameStateObj.stateMachine.changeState('dialogue')
            elif self.name == 'supportselect':
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
                if gameStateObj.cursor.currentHoveredUnit:
                    Action.do(Action.HasTraded(cur_unit), gameStateObj)
                    # cur_unit.hasTraded = True  # Unit can no longer move back, but can still attack
                    edge = gameStateObj.support.get_edge(cur_unit.id, gameStateObj.cursor.currentHoveredUnit.id)
                    if os.path.exists(edge.script):
                        support_script = edge.script
                    else:
                        support_script = 'Data/SupportConvos/GenericScript.txt'
                    level = edge.get_support_level()
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(support_script, unit=cur_unit, unit2=gameStateObj.cursor.currentHoveredUnit, name=level))
                    gameStateObj.stateMachine.changeState('menu')
                    gameStateObj.stateMachine.changeState('dialogue')
            elif self.name == 'unlockselect':
                gameStateObj.stateMachine.changeState('menu')
                item = cur_unit.get_unlock_key()
                cur_unit.unlock(gameStateObj.cursor.position, item, gameStateObj)
            else:
                logger.warning('SelectState does not have valid name: %s', self.name)
                gameStateObj.stateMachine.back() # Shouldn't happen

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.pennant:
            self.pennant.draw(mapSurf, gameStateObj)
        if self.name == 'tradeselect':
            MenuFunctions.drawTradePreview(mapSurf, gameStateObj, display_traveler=self.TRV_select)
        elif self.name == 'stealselect':
            MenuFunctions.drawTradePreview(mapSurf, gameStateObj, steal=True)
        elif self.name == 'rescueselect':
            MenuFunctions.drawRescuePreview(mapSurf, gameStateObj)
        return mapSurf

class TradeState(StateMachine.State):
    name = 'trade'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.info_surf = None
        self.initiator = gameStateObj.cursor.currentSelectedUnit
        self.initiator.sprite.change_state('chosen', gameStateObj)
        if gameStateObj.info_menu_struct.get('trade_partner'):  # can force a trade partner
            self.partner = gameStateObj.info_menu_struct.get('trade_partner')
        else:
            self.partner = gameStateObj.cursor.getHoveredUnit(gameStateObj)
        options1 = self.initiator.items
        options2 = self.partner.items
        gameStateObj.activeMenu = MenuFunctions.TradeMenu(self.initiator, self.partner, options1, options2)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        gameStateObj.activeMenu.updateOptions(self.initiator.items, self.partner.items)

        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            if gameStateObj.activeMenu.moveDown(first_push):
                GC.SOUNDDICT['Select 6'].play()
        elif 'UP' in directions:
            if gameStateObj.activeMenu.moveUp(first_push):
                GC.SOUNDDICT['Select 6'].play()

        if event == 'RIGHT':
            if gameStateObj.activeMenu.moveRight():
                GC.SOUNDDICT['TradeRight'].play() # TODO NOT the exact SOuND
        elif event == 'LEFT':
            if gameStateObj.activeMenu.moveLeft():
                GC.SOUNDDICT['TradeRight'].play()

        elif event == 'BACK':
            if gameStateObj.activeMenu.is_selection_set():
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.activeMenu.unsetSelection()
            else:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.activeMenu = None
                gameStateObj.stateMachine.changeState('menu')

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            if gameStateObj.activeMenu.is_selection_set():
                gameStateObj.activeMenu.tradeItems(gameStateObj)
            else:
                gameStateObj.activeMenu.setSelection()

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.drawInfo(mapSurf)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.info_surf = None

class StealState(StateMachine.State):
    name = 'steal'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.info_surf = None
        self.initiator = gameStateObj.cursor.currentSelectedUnit
        self.initiator.sprite.change_state('chosen', gameStateObj)
        self.rube = gameStateObj.cursor.getHoveredUnit(gameStateObj)
        options = self.rube.getStealables()
        gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(self.rube, options, 'auto', gameStateObj=gameStateObj)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)

        if event == 'BACK':
            GC.SOUNDDICT['Select 2'].play()
            gameStateObj.activeMenu = None
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            # selection.droppable = False
            # self.rube.remove_item(selection)
            Action.do(Action.RemoveItem(self.rube, selection), gameStateObj)
            Action.execute(Action.DropItem(self.initiator, selection), gameStateObj)
            # self.initiator.add_item(selection)
            Action.do(Action.HasAttacked(self.initiator), gameStateObj)
            if self.initiator.has_canto():
                gameStateObj.cursor.setPosition(self.initiator.position, gameStateObj)
                gameStateObj.stateMachine.changeState('move')
            else:
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('free')
                self.initiator.wait(gameStateObj)
            gameStateObj.activeMenu = None
            # Give exp
            exp = cf.CONSTANTS['steal_exp']
            if exp > 0:
                gameStateObj.exp_gain_struct = (self.initiator, exp, None, 'init')
                gameStateObj.stateMachine.changeState('exp_gain')
            # Display banner -- opposite order
            self.initiator.handle_steal_banner(selection, gameStateObj)

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.drawInfo(mapSurf)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.info_surf = None

class RepairState(StealState):
    name = 'repair'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.info_surf = None
        self.initiator = gameStateObj.cursor.currentSelectedUnit
        self.initiator.sprite.change_state('chosen', gameStateObj)
        self.customer = gameStateObj.cursor.getHoveredUnit(gameStateObj)
        self.item = self.initiator.items[0]
        options = self.customer.getRepairables()
        gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(self.customer, options, 'auto', gameStateObj=gameStateObj, disp_total_uses=True)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)

        if event == 'BACK':
            GC.SOUNDDICT['Select 2'].play()
            gameStateObj.activeMenu = None
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            Action.do(Action.RepairItem(selection), gameStateObj)
            Action.do(Action.HasAttacked(self.initiator), gameStateObj)
            if self.initiator.has_canto():
                gameStateObj.cursor.setPosition(self.initiator.position, gameStateObj)
                gameStateObj.stateMachine.changeState('move')
            else:
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('free')
                self.initiator.wait(gameStateObj)
            gameStateObj.activeMenu = None
            # Give exp -- cleanup
            Action.do(Action.GainWexp(self.initiator, self.item), gameStateObj)
            if self.item.exp:
                gameStateObj.exp_gain_struct = (self.initiator, self.item.exp, None, 'init')
                gameStateObj.stateMachine.changeState('exp_gain')
            Action.do(Action.UseItem(self.item), gameStateObj)
            if self.item.uses and self.item.uses.uses <= 0:
                Action.do(Action.RemoveItem(self.initiator, self.item), gameStateObj)

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

class ArenaState(StateMachine.State):
    name = 'arena'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # Get data needed
            self.unit = gameStateObj.cursor.currentSelectedUnit
            if not self.unit.position:
                self.unit.position = (0, 0)
            self.opponent = None
            self.legend, self.opponent_weapon_id, self.wager = self.get_arena_info(self.unit, gameStateObj)

            # Set up assuming things go to plan
            self.state_machine = CustomObjects.StateMachine('wager')
            if self.wager > 0:
                self.display_message = self.get_dialog(cf.WORDS['Arena_open'] % self.wager)
            else:
                self.display_message = self.get_dialog(cf.WORDS['Arena_open_no_wager'])
            self.wager_menu = MenuFunctions.ChoiceMenu(
                self.unit, [cf.WORDS['Yes'], cf.WORDS['No']], (112, 28),
                background='ActualTransparent', horizontal=True)

            # Set up draw
            if 'ArenaBackground' in GC.IMAGESDICT:
                self.background = Background.StaticBackground(GC.IMAGESDICT['ArenaBackground'], fade=False)
            else:
                self.background = Background.StaticBackground(GC.IMAGESDICT['RuneBackground'], fade=False)
            bg = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH+8, 48), 'ClearMenuBackground')
            self.bg = Engine.subsurface(bg, (4, 0, GC.WINWIDTH, 48))
            self.portrait = GC.IMAGESDICT.get('ArenaPortrait')
            self.money_counter_disp = MenuFunctions.BriefPopUpDisplay((223, 32))
            Engine.music_thread.fade_in(GC.MUSICDICT[cf.CONSTANTS.get('music_arena')])

            if gameStateObj.arena_closed(self.unit):
                self.state_machine = CustomObjects.StateMachine('close')
                self.wager_menu = None
                self.display_message = self.get_dialog(cf.WORDS['Arena_limit'])

            elif cf.CONSTANTS['arena_weapons']:
                self.unit_weapon = self.get_weapon_from_unit(self.unit, gameStateObj)
                if not self.unit_weapon:
                    self.state_machine = CustomObjects.StateMachine('close')
                    self.wager_menu = None
                    self.display_message = self.get_dialog(cf.WORDS['Arena_noweapon'])
            else:
                self.unit_weapon = self.unit.getMainWeapon()
                if not self.unit_weapon:
                    self.state_machine = CustomObjects.StateMachine('close')
                    self.wager_menu = None
                    self.display_message = self.get_dialog(cf.WORDS['Arena_noweapon'])

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def get_random_legend(self, unit, gameStateObj):
        my_klass = self.unit.klass
        my_tier = ClassData.class_dict[my_klass]['tier']
        max_level = ClassData.class_dict[my_klass]['max_level']
        classes_in_my_tier = [c for c, v in ClassData.class_dict.items() if v['tier'] == my_tier and
                              'ArenaIgnore' not in v['tags'] and v['max_level'] == max_level]
        legend = None
        old = static_random.get_other_random_state()
        while not legend:
            class_rng = static_random.get_other(0, len(classes_in_my_tier) - 1)
            low_level = max(1, self.unit.level - cf.CONSTANTS['arena_level_range'])
            high_level = min(max_level, self.unit.level + cf.CONSTANTS['arena_level_range'])
            level_rng = static_random.get_other(low_level, high_level)
            percent = (level_rng - low_level) / float(high_level - low_level)
            new_klass = classes_in_my_tier[class_rng]
            weapon_id = self.get_weapon_id_from_klass(new_klass, gameStateObj)
            if not weapon_id:
                continue
            legend = {'team': 'enemy', 'event_id': "0", 'class': new_klass,
                      'level': str(level_rng), 'items': weapon_id, 'position': self.unit.position,
                      'ai': 'None'}
        
        new = static_random.get_other_random_state()
        Action.do(Action.RecordOtherRandomState(old, new), gameStateObj)

        return legend, weapon_id, percent

    def get_arena_info(self, unit, gameStateObj):
        num_times_visited = int(gameStateObj.level_constants['_' + str(unit.id) + '_arena_uses'])
        event_id = 'arena%d' % num_times_visited
        if event_id in gameStateObj.allreinforcements:
            uid, pos = gameStateObj.allreinforcements[event_id]
            enemy = gameStateObj.get_unit(uid)
            items = ','.join([item.id for item in enemy.items])
            legend = {'team': 'enemy', 'event_id': "0", 'class': enemy.klass,
                      'level': str(enemy.level), 'items': items, 'position': self.unit.position,
                      'ai': 'None'}
            weapon_id = enemy.getMainWeapon().id if enemy.getMainWeapon() else None
            percent = 1.
            if not weapon_id:
                legend, weapon_id, percent = self.get_random_legend(unit, gameStateObj)
        else:
            legend, weapon_id, percent = self.get_random_legend(unit, gameStateObj)

        wager = int(percent * (cf.CONSTANTS['arena_wager_max'] - cf.CONSTANTS['arena_wager_min']) + cf.CONSTANTS['arena_wager_min'])
        wager = min(gameStateObj.get_money(), wager)

        return legend, weapon_id, wager

    def get_weapon_id_from_klass(self, klass, gameStateObj):
        class_data = ClassData.class_dict[klass]
        wexp_gain = class_data['wexp_gain']
        max_index = wexp_gain.index(max(wexp_gain))
        new_weapon_id = cf.CONSTANTS['arena_basic_weapons'][max_index]
        return new_weapon_id

    def get_weapon_from_unit(self, unit, gameStateObj):
        max_index = unit.wexp.index(max(unit.wexp))
        new_weapon_id = cf.CONSTANTS['arena_basic_weapons'][max_index]
        return ItemMethods.itemparser(new_weapon_id, gameStateObj)

    def get_dialog(self, text):
        return Dialogue.Dialog(text, 'Narrator', (60, 8), (160, 48), 'text_white', 'ActualTransparent', waiting_cursor_flag=False)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if self.state_machine.getState() == 'wager':
            if 'DOWN' in directions or 'RIGHT' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.wager_menu.moveDown(first_push)
            elif 'UP' in directions or 'LEFT' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.wager_menu.moveUp(first_push)

            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                self.display_message = self.get_dialog(cf.WORDS['Arena_back'])
                self.wager_menu = None
                self.state_machine.changeState('close')

            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                selection = self.wager_menu.getSelection()
                if selection == cf.WORDS['Yes']:
                    if self.wager > 0:
                        GC.SOUNDDICT['GoldExchange'].play()
                        Action.execute(Action.GiveGold(-self.wager, gameStateObj.current_party), gameStateObj)
                        self.money_counter_disp.start(-self.wager)

                    # Actually create unit here!
                    self.opponent = SaveLoad.create_unit_from_legend(self.legend, gameStateObj.allunits, None, None, gameStateObj)
                    self.opponent_weapon = self.opponent.items[0] if self.opponent.items else None
                    Action.do(Action.SimpleArrive(self.opponent, self.opponent.position), gameStateObj)

                    self.display_message = self.get_dialog(cf.WORDS['Arena_combat'])
                    self.wager_menu = None
                    self.state_machine.changeState('combat')
                elif selection == cf.WORDS['No']:
                    GC.SOUNDDICT['Select 4'].play()
                    self.display_message = self.get_dialog(cf.WORDS['Arena_back'])
                    self.wager_menu = None
                    self.state_machine.changeState('close')

        elif self.state_machine.getState() == 'combat':
            if event:
                GC.SOUNDDICT['Select 1'].play()
                if self.display_message.done:
                    gameStateObj.level_constants['_wager'] = self.wager
                    gameStateObj.level_constants['_global_arena_uses'] += 1
                    gameStateObj.level_constants['_' + str(self.unit.id) + '_arena_uses'] += 1
                    gameStateObj.combatInstance = \
                        Interaction.start_combat(
                            gameStateObj, self.unit, self.opponent, self.unit.position,
                            [], self.unit_weapon, arena=self.name)
                    gameStateObj.stateMachine.back()
                    gameStateObj.stateMachine.changeState('combat')
                if self.display_message.waiting: # Remove waiting check
                    self.display_message.waiting = False

        elif self.state_machine.getState() == 'close':
            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.changeState('transition_pop')
            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                if self.display_message.done:
                    gameStateObj.stateMachine.changeState('transition_pop')
                if self.display_message.waiting: # Remove waiting check
                    self.display_message.waiting = False

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.wager_menu:
            self.wager_menu.update()
        self.display_message.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        # Draw background
        self.background.draw(surf)

        surf.blit(self.bg, (0, 8))

        if self.display_message:
            self.display_message.draw(surf)

        if self.wager_menu and self.display_message.done:
            self.wager_menu.draw(surf)

        if self.portrait:
            surf.blit(self.portrait, (3, 0))

        surf.blit(GC.IMAGESDICT['MoneyBG'], (172, 48))
        money = str(gameStateObj.get_money())
        GC.FONT['text_blue'].blit(money, surf, (223 - GC.FONT['text_blue'].size(money)[0], 48))
        self.money_counter_disp.draw(surf)

        if self.state_machine.getState() == 'combat':
            # Display duelist info
            duelist_info_bg = BaseMenuSurf.CreateBaseMenuSurf((120, 40))
            GC.FONT['text_white'].blit('LV', duelist_info_bg, (4, 4))
            GC.FONT['text_blue'].blit(str(self.opponent.level), duelist_info_bg, (28, 4))
            GC.FONT['text_white'].blit(self.opponent.klass, duelist_info_bg, (60, 4))
            GC.FONT['text_white'].blit('Duelist', duelist_info_bg, (4, 20))
            GC.FONT['text_white'].blit(self.opponent_weapon.name, duelist_info_bg, (60, 20))

            surf.blit(duelist_info_bg, (GC.WINWIDTH//2 - 120//2, 76))

        return surf

    def finish(self, gameStateObj, metaDataObj):
        self.background = None
        gameStateObj.activeMenu = gameStateObj.hidden_active

class FeatChoiceState(StateMachine.State):
    name = 'feat_choice'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        initiator = gameStateObj.cursor.currentSelectedUnit
        if initiator is None:
            initiator = gameStateObj.cursor.currentHoveredUnit
        options = []
        for feat in StatusCatalog.feat_list:
            options.append(StatusCatalog.statusparser(feat, gameStateObj))
        self.menu = MenuFunctions.FeatChoiceMenu(initiator, options)
        self.info = False

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveUp(first_push)
        if 'RIGHT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveRight(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveLeft(first_push)

        # Show R unit status screen
        if event == 'BACK':
            self.info = not self.info

        elif event == 'INFO':
            GC.SOUNDDICT['Select 2'].play()
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.cursor.currentSelectedUnit, one_unit_only=True)

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            gameStateObj.stateMachine.back()
            Action.do(Action.AddStatus(gameStateObj.cursor.currentSelectedUnit, selection), gameStateObj)
            gameStateObj.banners.append(Banner.gainedSkillBanner(gameStateObj.cursor.currentSelectedUnit, selection))
            gameStateObj.stateMachine.changeState('itemgain')
            self.menu = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)

        # To handle combat and promotion
        under_state = gameStateObj.stateMachine.get_under_state(self)
        if under_state and (under_state.name == 'exp_gain' or under_state.name == 'promotion'):
            mapSurf = under_state.draw(gameStateObj, metaDataObj)

        # Draw Menu
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)

        # Draw current info
        if self.info and self.menu:
            selection = self.menu.getSelection()
            position = (16, 16*self.menu.currentSelection%5 + 48)
            selection.get_help_box().draw(mapSurf, position)
        return mapSurf

class AIState(StateMachine.State):
    name = 'ai'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0

        if gameStateObj.ai_build_flag:
            # Get list of units to process for this turn
            gameStateObj.ai_unit_list = [unit for unit in gameStateObj.allunits if unit.position and not unit.isDone()
                                         and unit.team == gameStateObj.phase.get_current_phase()]
            # Sort by distance to closest enemy (ascending)
            gameStateObj.ai_unit_list = sorted(gameStateObj.ai_unit_list, key=lambda unit: unit.distance_to_closest_enemy(gameStateObj))
            gameStateObj.ai_unit_list = sorted(gameStateObj.ai_unit_list, key=lambda unit: unit.ai.ai_group or '')
            gameStateObj.ai_unit_list = sorted(gameStateObj.ai_unit_list, key=lambda unit: unit.ai.priority, reverse=True)
            # Reverse, because we will be popping them off the end
            gameStateObj.ai_unit_list.reverse()

            gameStateObj.ai_build_flag = False
            gameStateObj.ai_current_unit = None

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if not any(unit.isDying for unit in gameStateObj.allunits):
            # Get new unit from list if no unit or unit is not on map anymore
            if (not gameStateObj.ai_current_unit or not gameStateObj.ai_current_unit.position) and gameStateObj.ai_unit_list:
                gameStateObj.ai_current_unit = gameStateObj.ai_unit_list.pop()

            logger.debug('current_ai: %s', gameStateObj.ai_current_unit)
            if gameStateObj.ai_current_unit:
                logger.debug('%s %s %s', gameStateObj.ai_current_unit.hasRunMoveAI,
                             gameStateObj.ai_current_unit.hasRunAttackAI,
                             gameStateObj.ai_current_unit.hasRunGeneralAI)

            # If we got a new unit
            if gameStateObj.ai_current_unit:
                did_something = gameStateObj.ai_current_unit.ai.act(gameStateObj)
                # Center camera on the current unit
                if did_something and gameStateObj.ai_current_unit.position:
                    other_pos = gameStateObj.ai_current_unit.ai.target_to_interact_with
                    if gameStateObj.ai_current_unit.ai.position_to_move_to and \
                            gameStateObj.ai_current_unit.ai.position_to_move_to != gameStateObj.ai_current_unit.position:
                        gameStateObj.cameraOffset.center2(gameStateObj.ai_current_unit.position, gameStateObj.ai_current_unit.ai.position_to_move_to)
                    elif other_pos and Utility.calculate_distance(gameStateObj.ai_current_unit.position, other_pos) <= GC.TILEY - 2: # Leeway
                        gameStateObj.cameraOffset.center2(gameStateObj.ai_current_unit.position, other_pos)
                    else:
                        gameStateObj.cursor.setPosition(gameStateObj.ai_current_unit.position, gameStateObj)
                    gameStateObj.stateMachine.changeState('move_camera')
                if gameStateObj.ai_current_unit.hasRunAI():
                    logger.debug('current_ai %s done with turn.', gameStateObj.ai_current_unit)
                    # The unit is now done with AI
                    # If the unit actually did something, doesn't have canto plus, and isn't going into combat, then can now wait.
                    if did_something and not gameStateObj.ai_current_unit.has_canto_plus() and not gameStateObj.stateMachine.inList('combat'):
                        gameStateObj.ai_current_unit.wait(gameStateObj)
                    gameStateObj.ai_current_unit = None

            else: # Done
                logger.debug('Done with AI')
                self.finish(gameStateObj, metaDataObj)
                gameStateObj.stateMachine.changeState('turn_change')
                return 'repeat'

    def finish(self, gameStateObj, metaDataObj):
        for unit in gameStateObj.ai_unit_list:
            unit.reset_ai()
        gameStateObj.ai_build_flag = True
        gameStateObj.ai_unit_list = []
        gameStateObj.ai_current_unit = None

class DialogueState(StateMachine.State):
    name = 'dialogue'

    def __init__(self, name='dialogue'):
        StateMachine.State.__init__(self, name)
        self.message = None
        self.text_speed_change = MenuFunctions.BriefPopUpDisplay((GC.WINWIDTH, GC.WINHEIGHT - 16))
        self.hurry_up_time = 0

    def begin(self, gameStateObj, metaDataObj):
        logger.info('Begin Dialogue State')
        cf.CONSTANTS['Unit Speed'] = 120
        if self.name != 'transparent_dialogue':
            gameStateObj.cursor.drawState = 0
        if gameStateObj.message:
            self.message = gameStateObj.message[-1]
        if self.message:
            self.message.current_state = "Processing"

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)

        if (event == 'START' or event == 'BACK') and self.message and not self.message.do_skip: # SKIP
            GC.SOUNDDICT['Select 4'].play()
            self.message.skip()

        elif event == 'SELECT' or event == 'RIGHT' or event == 'DOWN': # Get it to move along...
            if self.message.current_state == "Displaying" and self.message.dialog:
                last_hit = Engine.get_time() - self.hurry_up_time
                if last_hit > 200:  # How long it will pause before moving on to next section
                    if self.message.dialog[-1].waiting:
                        GC.SOUNDDICT['Select 1'].play()
                        # GC.SOUNDDICT['Talk_Boop'].play()
                        self.message.dialog_unpause()
                        self.hurry_up_time = 0
                    else:
                        self.message.dialog[-1].hurry_up()
                        self.hurry_up_time = Engine.get_time()

        elif event == 'AUX':  # Increment the text speed to be faster
            if cf.OPTIONS['Text Speed'] in cf.text_speed_options:
                GC.SOUNDDICT['Select 4'].play()
                current_index = cf.text_speed_options.index(cf.OPTIONS['Text Speed'])
                current_index += 1
                if current_index >= len(cf.text_speed_options):
                    current_index = 0
                cf.OPTIONS['Text Speed'] = cf.text_speed_options[current_index]
                self.text_speed_change.start('Changed Text Speed!')

    def end_dialogue_state(self, gameStateObj, metaDataObj):
        logger.debug('Ending dialogue state')
        last_message = None
        if self.message and gameStateObj.message:
            last_message = gameStateObj.message.pop()
        # Did any tiles change?
        if self.message.reset_boundary_manager:
            gameStateObj.boundary_manager.reset(gameStateObj)
        # HANDLE WINNING AND LOSING
        # Things done upon completion of level
        if gameStateObj.statedict['levelIsComplete'] == 'win':
            logger.info('Player wins!')
            # Run the outro_script
            if not gameStateObj.statedict['outroScriptDone'] and os.path.exists(metaDataObj['outroScript']):
                # Update statistics first
                gameStateObj.update_statistics(metaDataObj)
                outro_script = Dialogue.Dialogue_Scene(metaDataObj['outroScript'])
                gameStateObj.message.append(outro_script)
                gameStateObj.stateMachine.changeState('dialogue')
                gameStateObj.statedict['outroScriptDone'] = True
            elif not os.path.exists(metaDataObj['outroScript']) or last_message.scene == metaDataObj['outroScript']:  # We can only leave from an outroScript
                # Prevents leaving from an internal interactScript within the outroScript
                gameStateObj.increment_supports()
                gameStateObj.clean_up()
                if not cf.CONSTANTS['overworld'] and isinstance(gameStateObj.game_constants['level'], int):
                    gameStateObj.game_constants['level'] += 1
                gameStateObj.game_constants['current_turnwheel_uses'] = gameStateObj.game_constants.get('max_turnwheel_uses', -1)
                gameStateObj.output_progress_xml()  # Done after level change so that it will load up the right level next time

                # Determines the number of levels in the game
                num_levels = 0
                level_directories = [x[0] for x in os.walk('Data/') if os.path.split(x[0])[1].startswith('Level')]
                for directory in level_directories:
                    try:
                        num = int(os.path.split(directory)[1][5:])
                        if num > num_levels:
                            num_levels = num
                    except:
                        continue

                gameStateObj.stateMachine.clear()
                if cf.CONSTANTS['overworld']:
                    gameStateObj.stateMachine.changeState('overworld')
                    gameStateObj.save_kind = 'Overworld'
                    gameStateObj.stateMachine.changeState('start_save')
                elif (not isinstance(gameStateObj.game_constants['level'], int)) or gameStateObj.game_constants['level'] > num_levels:
                    gameStateObj.stateMachine.changeState('start_start')
                else:
                    gameStateObj.stateMachine.changeState('turn_change') # after we're done waiting, go to turn_change, start the GAME!
                    gameStateObj.save_kind = 'Start'
                    gameStateObj.stateMachine.changeState('start_save')
        elif gameStateObj.statedict['levelIsComplete'] == 'loss':
            logger.info('Player loses!')
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('start_start')
            gameStateObj.stateMachine.changeState('game_over')
        elif self.message.turnwheel_flag:
            if self.message.turnwheel_flag == 2:
                gameStateObj.stateMachine.changeState('force_turnwheel')
            else:
                gameStateObj.stateMachine.changeState('turnwheel')
        elif self.message.battle_save_flag:
            gameStateObj.stateMachine.changeState('battle_save')
        elif self.message.reset_state_flag:
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('free')

        # Don't need to fade to normal if we're just heading back to a event script
        # Engine.music_thread.fade_to_normal(gameStateObj, metaDataObj)

        logger.info('Repeat Dialogue State!')
        return 'repeat'

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        # Handle state transparency
        if self.name == 'transparent_dialogue' and gameStateObj.stateMachine.get_under_state(self):
            gameStateObj.stateMachine.get_under_state(self).update(gameStateObj, metaDataObj)
        # Only if top of state stack
        if not gameStateObj.stateMachine.state or gameStateObj.stateMachine.state[-1] == self:
            if self.message:
                self.message.update(gameStateObj, metaDataObj)
            else:
                logger.info('Done with Dialogue State!')
                gameStateObj.stateMachine.back()
                return 'repeat'

            if self.message.done and self.message.current_state == "Processing":
                gameStateObj.stateMachine.back()
                return self.end_dialogue_state(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        if self.name == 'transparent_dialogue' and gameStateObj.stateMachine.get_under_state(self):
            mapSurf = gameStateObj.stateMachine.get_under_state(self).draw(gameStateObj, metaDataObj)
        elif not self.message or not self.message.background:
            mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        else:
            mapSurf = gameStateObj.generic_surf
        if self.message:
            self.message.draw(mapSurf)
        self.text_speed_change.draw(mapSurf)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        cf.CONSTANTS['Unit Speed'] = cf.OPTIONS['Unit Speed']

class VictoryState(StateMachine.State):
    name = 'victory'
    victory_surf = GC.IMAGESDICT['Victory1']
    vic_width, vic_height = victory_surf.get_size()
    num_transition_frames = 20

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.background = Background.StaticBackground(GC.IMAGESDICT['FocusFade'], fade=True)
        if gameStateObj.statistics:
            level_statistic = gameStateObj.statistics[-1]
        else:
            level_statistic = None
            print("You need to call 'victory_screen' in a different script than the one you call 'win_game' in!")
            print("'win_game' isn't processed until the end of the script it is called in.")
        self.state = 'init'
        self.stat_surf = self.create_stat_surf(level_statistic)
        self.stat_surf_target = self.stat_surf.get_height() + 4
        self.num_frame = 0
        # Engine.music_thread.stop()
        Engine.music_thread.lower()
        GC.SOUNDDICT['StageClear'].play()

    def create_stat_surf(self, stats):
        if stats:
            turns = str(stats.turncount)
            mvp = stats.get_mvp()
        else:
            turns = '0'
            mvp = 'None'
        menu_width = 96
        bg = BaseMenuSurf.CreateBaseMenuSurf((menu_width, 40), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        bg.blit(img, (bg.get_width() - 1 - img.get_width(), bg.get_height() - 5 - img.get_height()))
        bg = Image_Modification.flickerImageTranslucent(bg, 10)

        GC.FONT['text_yellow'].blit('Turns', bg, (4, 4))
        GC.FONT['text_yellow'].blit('MVP', bg, (4, 20))
        turns_size = GC.FONT['text_blue'].size(turns)[0]
        mvp_size = GC.FONT['text_blue'].size(mvp)[0]
        GC.FONT['text_blue'].blit(turns, bg, (menu_width - 40 - turns_size//2, 4))
        GC.FONT['text_blue'].blit(mvp, bg, (menu_width - 40 - mvp_size//2, 20))

        return bg

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if self.state == 'allow_input' and (event == 'SELECT' or event == 'START' or event == 'BACK'):
            self.state = 'leave'
            Engine.music_thread.unmute()
            gameStateObj.background.fade_out()
            gameStateObj.stateMachine.changeState('transition_pop')
            return 'repeat'

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.state == 'init':
            self.num_frame += 1
            if self.num_frame >= self.num_transition_frames:
                self.num_frame = self.num_transition_frames
                self.state = 'allow_input'

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        offset = self.num_frame/float(self.num_transition_frames)

        # Stat surf draw
        pos = (GC.WINWIDTH//2 - self.stat_surf.get_width()//2, GC.WINHEIGHT - (offset * self.stat_surf_target))
        mapSurf.blit(self.stat_surf, pos)
        # Victory draw
        vic_surf = Engine.copy_surface(self.victory_surf)
        vic_surf = Image_Modification.flickerImageTranslucent(vic_surf, 100 - (offset * 100))
        height = int(self.vic_height * offset)
        vic_surf = Engine.transform_scale(vic_surf, (GC.WINWIDTH, height))
        mapSurf.blit(vic_surf, (0, self.victory_surf.get_height()//2 - height//2))

        return mapSurf

class CombatState(StateMachine.State):
    name = 'combat'
    fuzz_background = Image_Modification.flickerImageTranslucent255(GC.IMAGESDICT['BlackBackground'], 56)
    dark_fuzz_background = Image_Modification.flickerImageTranslucent255(GC.IMAGESDICT['BlackBackground'], 112)

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        self.skip = False
        self.unit_surf = Engine.create_surface((gameStateObj.map.width * GC.TILEWIDTH, gameStateObj.map.height * GC.TILEHEIGHT), transparent=True)
        self.animation_combat = isinstance(gameStateObj.combatInstance, Interaction.AnimationCombat)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'START':
            self.skip = True
            gameStateObj.combatInstance.skip()
        elif event == 'BACK':
            if gameStateObj.combatInstance.arena:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.combatInstance.arena_stop(gameStateObj)

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        combatisover = gameStateObj.combatInstance.update(gameStateObj, metaDataObj, self.skip)
        while self.skip and not combatisover and not self.animation_combat:
            combatisover = gameStateObj.combatInstance.update(gameStateObj, metaDataObj, self.skip)
        if combatisover: # StateMachine.State changing is handled in combat's clean_up function
            gameStateObj.combatInstance = None
            # gameStateObj.stateMachine.back() NOT NECESSARY! DONE BY the COMBAT INSTANCES CLEANUP!

    def draw(self, gameStateObj, metaDataObj):
        if gameStateObj.combatInstance and self.animation_combat:
            mapSurf = self.drawCombat(gameStateObj) # Creates mapSurf
            gameStateObj.set_camera_limits()
            rect = (gameStateObj.cameraOffset.get_x()*GC.TILEWIDTH, gameStateObj.cameraOffset.get_y()*GC.TILEHEIGHT, GC.WINWIDTH, GC.WINHEIGHT)
            mapSurf = Engine.subsurface(mapSurf, rect)
            gameStateObj.combatInstance.draw(mapSurf, gameStateObj)
        else:
            mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
            if gameStateObj.combatInstance:
                gameStateObj.combatInstance.draw(mapSurf, gameStateObj)
        return mapSurf

    def drawCombat(self, gameStateObj):
        """Draw the map to a Surface object."""

        # mapSurf will be the single Surface object that the tiles are drawn
        # on, so that is is easy to position the entire map on the GC.DISPLAYSURF
        # Surface object. First, the width and height must be calculated
        mapSurf = gameStateObj.mapSurf
        unit_surf = self.unit_surf.copy()
        # Draw the tile sprites onto this surface
        gameStateObj.map.draw(mapSurf, gameStateObj)
        # Draw the boundary manager so it doesn't flicker on and off during animation
        gameStateObj.boundary_manager.draw(mapSurf, (mapSurf.get_width(), mapSurf.get_height()))

        # Reorder units so they are drawn in correct order, from top to bottom, so that units on bottom are blit over top
        # Only draw units that will be in the camera's field of view
        viewbox = gameStateObj.combatInstance.viewbox if gameStateObj.combatInstance.viewbox else (0, 0, GC.WINWIDTH, GC.WINHEIGHT)
        if gameStateObj.stateMachine.getState() == 'exp_gain' and \
                gameStateObj.stateMachine.state[-1].state.getState() == 'level_up':
            viewbox_bg = self.dark_fuzz_background.copy()
        else:
            viewbox_bg = self.fuzz_background.copy()
        camera_x = int(gameStateObj.cameraOffset.get_x())
        camera_y = int(gameStateObj.cameraOffset.get_y())
        pos_x, pos_y = camera_x * GC.TILEWIDTH, camera_y * GC.TILEHEIGHT
        if viewbox[2] > 0: # Width
            viewbox_bg.fill((0, 0, 0, 0), viewbox) # Excise fuzz section on viewbox
            culled_units = [unit for unit in gameStateObj.allunits if unit.position and
                            camera_x - 1 <= unit.position[0] <= camera_x + GC.TILEX + 1 and
                            camera_y - 1 <= unit.position[1] <= camera_y + GC.TILEY + 1]
            draw_me = sorted(culled_units, key=lambda unit: unit.position[1])
            for unit in draw_me:
                unit.draw(unit_surf, gameStateObj)
            for unit_hp in draw_me:
                unit_hp.draw_hp(unit_surf, gameStateObj)

            unit_surf = Engine.subsurface(unit_surf, (viewbox[0] + pos_x, viewbox[1] + pos_y, viewbox[2], viewbox[3]))
            mapSurf.blit(unit_surf, (viewbox[0] + pos_x, viewbox[1] + pos_y))
        # Draw cursor
        if gameStateObj.cursor:
            gameStateObj.cursor.draw(mapSurf)
        # Draw weather
        for weather in gameStateObj.map.weather:
            weather.draw(mapSurf, pos_x, pos_y)
        mapSurf.blit(viewbox_bg, (pos_x, pos_y))
        return mapSurf

class CameraMoveState(StateMachine.State):
    name = 'move_camera'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if gameStateObj.cameraOffset.check_loc():
            if gameStateObj.message and gameStateObj.stateMachine.getPreviousState() == 'dialogue':
                gameStateObj.message[-1].current_state = "Processing"
            gameStateObj.stateMachine.back()
            return 'repeat'

class MovementState(StateMachine.State):
    name = 'movement'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        # gameStateObj.boundary_manager.draw_flag = 0

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        # Only switch states if no other unit is moving
        if not gameStateObj.moving_units:
            gameStateObj.stateMachine.back()
            # If this was part of a cutscene and I am the last unit moving, head back to dialogue state
            if gameStateObj.stateMachine.getPreviousState() in ('dialogue', 'transparent_dialogue') or gameStateObj.message: # The back should move us out of 'movement' state
                gameStateObj.message[-1].current_state = "Processing" # Make sure that we can go back to processing
            return 'repeat'

class PhaseChangeState(StateMachine.State):
    name = 'phase_change'

    def begin(self, gameStateObj, metaDataObj):
        self.save_state(gameStateObj)
        logger.debug('Phase Start')
        Action.do(Action.LockTurnwheel(gameStateObj.phase.get_current_phase() != 'player'), gameStateObj)

        # Handle cooldown items
        units = [unit for unit in gameStateObj.allunits if 
                 (unit.team == gameStateObj.phase.get_current_phase() and unit.position)]
        for unit in units:
            for item in unit.items:
                if item.cooldown and not item.cooldown.charged:
                    Action.do(Action.CooloffItem(item), gameStateObj)

        # Handle fatigue
        if cf.CONSTANTS['fatigue'] and gameStateObj.turncount == 1 and gameStateObj.phase.get_current_phase() == 'player':
            gameStateObj.refresh_fatigue()

        # Turn by turn fatigue
        if cf.CONSTANTS['fatigue'] == 3:
            for unit in units:
                if unit.team == 'player':
                    Action.do(Action.ChangeFatigue(unit, 1), gameStateObj)

        # All units can now move and attack, etc.
        Action.do(Action.ResetAll([unit for unit in gameStateObj.allunits if not unit.dead]), gameStateObj)
        # Mark phase used to be here
        gameStateObj.cursor.drawState = 0
        gameStateObj.activeMenu = None
        gameStateObj.phase.slide_in(gameStateObj)

    def end(self, gameStateObj, metaDataObj):
        logger.debug('Phase End')
        Engine.music_thread.fade_to_normal(gameStateObj)

    # Save state at beginning of each turn
    def save_state(self, gameStateObj):
        if gameStateObj.phase.get_current_phase() == 'player':
            logger.debug("Saving as we enter player phase!")
            name = 'L' + str(gameStateObj.game_constants['level']) + 'T' + str(gameStateObj.turncount)
            SaveLoad.suspendGame(gameStateObj, 'TurnChange ' + str(gameStateObj.turncount), hard_loc=name)
        elif gameStateObj.phase.get_current_phase() == 'enemy':
            logger.debug("Saving as we enter enemy phase!")
            name = 'L' + str(gameStateObj.game_constants['level']) + 'T' + str(gameStateObj.turncount) + 'b'
            SaveLoad.suspendGame(gameStateObj, 'EnemyTurnChange ' + str(gameStateObj.turncount), hard_loc=name)

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        isDone = gameStateObj.phase.update()
        if isDone:
            gameStateObj.stateMachine.back()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.phase.draw(mapSurf)
        return mapSurf

class StatusState(StateMachine.State):
    name = 'status'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        if not hasattr(self, 'new'):
            if self.name == 'status':
                gameStateObj.status = StatusCatalog.Status_Processor(gameStateObj, True)
            elif self.name == 'end_step':
                gameStateObj.status = StatusCatalog.Status_Processor(gameStateObj, False)
            self.new = True

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        # Update status object
        processing = True
        count = 0 # Only process as much as 10 units in a frame.
        while processing and count < 10:
            output = gameStateObj.status.update(gameStateObj)
            if any(unit.isDying for unit in gameStateObj.allunits):
                processing = False
                gameStateObj.stateMachine.changeState('dying')
                for unit in [u for u in gameStateObj.allunits if u.isDying]:
                    # Death quote
                    scene = Dialogue.Dialogue_Scene(metaDataObj['death_quotes'], unit=unit)
                    gameStateObj.message.append(scene)
                    gameStateObj.stateMachine.changeState('dialogue')
            if output == 'Done':
                self.leave(gameStateObj)
                processing = False
            elif output == 'Waiting' or output == 'Death':
                processing = False
            # print(self.name, count, output, gameStateObj.status.current_unit.position)
            count += 1

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.status.draw(mapSurf, gameStateObj)
        return mapSurf

    def leave(self, gameStateObj):
        gameStateObj.stateMachine.back()
        if self.name == 'status':
            Action.do(Action.MarkPhase(gameStateObj.phase.get_current_phase()), gameStateObj)

class DyingState(StateMachine.State):
    name = 'dying'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0

    def take_input(self, eventList, gameStateObj, metaDataObj):
        if not any(unit.isDying for unit in gameStateObj.allunits):
            gameStateObj.stateMachine.back()

class ItemGainState(StateMachine.State):
    name = 'itemgain'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        # Need to return to the correct background when using a booster from
        # the prep or base menus
        under_state = gameStateObj.stateMachine.get_under_state(self)
        if under_state and under_state.name == 'prep_items_choices':
            under_state.set_background(gameStateObj)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event and gameStateObj.banners and gameStateObj.banners[-1].time_to_start and \
                Engine.get_time() - gameStateObj.banners[-1].time_to_start > gameStateObj.banners[-1].time_to_wait:
            current_banner = gameStateObj.banners.pop()
            gameStateObj.stateMachine.back()

            if isinstance(current_banner, Banner.acquiredItemBanner) and current_banner.allows_choice and \
                    len(current_banner.unit.items) > cf.CONSTANTS['max_items']:
                gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(current_banner.unit, current_banner.unit.items, 'auto', gameStateObj=gameStateObj)
                gameStateObj.cursor.currentSelectedUnit = current_banner.unit
                gameStateObj.stateMachine.changeState('itemdiscard')
                return

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if gameStateObj.banners and gameStateObj.stateMachine.state[-1] is self:
            gameStateObj.banners[-1].update(gameStateObj)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        # To handle promotion
        under_state = gameStateObj.stateMachine.get_under_state(self)
        if under_state and under_state.name == 'exp_gain' or isinstance(under_state, ItemGainState) \
           or isinstance(under_state, CombatState) or under_state.name == 'promotion' \
           or under_state.name == 'prep_items_choices':
            mapSurf = under_state.draw(gameStateObj, metaDataObj)
        # For Dialogue
        elif gameStateObj.message:
            gameStateObj.message[-1].draw(mapSurf)
        # Banner draw -- if top
        if gameStateObj.banners and gameStateObj.stateMachine.state[-1] is self:
            gameStateObj.banners[-1].draw(mapSurf, gameStateObj)
        return mapSurf

class ItemDiscardState(StateMachine.State):
    name = 'itemdiscard'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        gameStateObj.info_surf = None
        if 'Convoy' in gameStateObj.game_constants:
            self.pennant = Banner.Pennant(cf.WORDS['Storage_info'])
        else:
            self.pennant = Banner.Pennant(cf.WORDS['Discard_info'])
        options = gameStateObj.cursor.currentSelectedUnit.items
        if not gameStateObj.activeMenu:
            ignore = [option.locked for option in options]
            color = ['text_grey' if i else 'text_white' for i in ignore]
            gameStateObj.activeMenu = \
                MenuFunctions.ChoiceMenu(gameStateObj.cursor.currentSelectedUnit, options, 'auto',
                                         gameStateObj=gameStateObj, color_control=color, ignore=ignore)
        else:
            gameStateObj.activeMenu.updateOptions(options)
        self.childMenu = None

    def take_input(self, eventList, gameStateObj, metaDataObj):
        gameStateObj.activeMenu.updateOptions(gameStateObj.cursor.currentSelectedUnit.items)
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
            gameStateObj.info_surf = None
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)
            gameStateObj.info_surf = None

        if event == 'BACK':
            if not len(gameStateObj.cursor.currentSelectedUnit.items) > cf.CONSTANTS['max_items']:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.activeMenu = None
                gameStateObj.stateMachine.back()
            else:
                # Play bad sound?
                GC.SOUNDDICT['Select 4'].play()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            # Create child menu with additional options
            if 'Convoy' in gameStateObj.game_constants:
                options = [cf.WORDS['Storage']]
            else:
                options = [cf.WORDS['Discard']]
            self.child_menu = MenuFunctions.ChoiceMenu(selection, options, 'child', gameStateObj=gameStateObj)
            gameStateObj.stateMachine.changeState('itemdiscardchild')

        elif event == 'INFO':
            gameStateObj.activeMenu.toggle_info()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.pennant.draw(mapSurf, gameStateObj)
        if gameStateObj.activeMenu:
            gameStateObj.cursor.currentSelectedUnit.drawItemDescription(mapSurf, gameStateObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.drawInfo(mapSurf)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.info_surf = None

class ItemDiscardChildState(StateMachine.State):
    name = 'itemdiscardchild'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.info_surf = None
        gameStateObj.cursor.drawState = 0
        self.menu = gameStateObj.stateMachine.state[-2].child_menu

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveUp(first_push)

        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            self.menu = None
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            if selection == cf.WORDS['Storage'] or selection == cf.WORDS['Discard']:
                item = self.menu.owner
                if item in gameStateObj.activeMenu.owner.items:
                    Action.do(Action.DiscardItem(gameStateObj.activeMenu.owner, item), gameStateObj)
                self.menu = None
                gameStateObj.activeMenu.currentSelection = 0 # Reset selection?
                if len(gameStateObj.activeMenu.owner.items) > cf.CONSTANTS['max_items']: # If the unit still has >5 items
                    gameStateObj.stateMachine.back() # back to itemdiscard
                else: # If the unit has <=5 items, just head back before item discard
                    gameStateObj.activeMenu = None
                    gameStateObj.stateMachine.back()
                    gameStateObj.stateMachine.back()

    def end(self, gameStateObj, metaDataObj):
        self.menu = None
        gameStateObj.info_surf = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        # Draw ItemDiscard's pennant
        gameStateObj.stateMachine.get_under_state(self).pennant.draw(mapSurf, gameStateObj)
        if gameStateObj.activeMenu:
            gameStateObj.cursor.currentSelectedUnit.drawItemDescription(mapSurf, gameStateObj)
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)
        return mapSurf

class BattleSaveState(StateMachine.State):
    name = 'battle_save'

    def __init__(self, name):
        StateMachine.State.__init__(self, name)
        self.counter = 0

    def begin(self, gameStateObj, metaDataObj):
        self.menu = MenuFunctions.HorizOptionsMenu(cf.WORDS['Battle Save Header'], [cf.WORDS['Yes'], cf.WORDS['No']])
        self.counter += 1

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)

        if event == 'RIGHT':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveRight()
        elif event == 'LEFT':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveLeft()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            selection = self.menu.getSelection()
            self.menu = None
            if selection == cf.WORDS['Yes']:
                GC.SOUNDDICT['Select 1'].play()
                # SaveLoad.suspendGame(gameStateObj, 'Battle')
                gameStateObj.save_kind = 'Battle'
                gameStateObj.stateMachine.changeState('start_save')
                gameStateObj.stateMachine.changeState('transition_out')
                # gameStateObj.banners.append(Banner.gameSavedBanner())
                # gameStateObj.stateMachine.changeState('itemgain')
            else:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.update()
        if self.counter >= 2: # Should never get here twice
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
            return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.draw(mapSurf)
        return mapSurf

class DialogOptionsState(StateMachine.State):
    name = 'dialog_options'

    def begin(self, gameStateObj, metaDataObj):
        name, header, options, arrangement = gameStateObj.game_constants['choice']
        self.name = name

        # Determine if it should be a horizontal or vertical menu.
        if arrangement in ('v', 'vertical'):
            self.menu = MenuFunctions.VertOptionsMenu(header, options)
            self.menu_arrangement = 'v'
        else:
            if arrangement not in ('h', 'horizontal'):
                logger.debug('The option menu arrangement was detected as neither vertical or horizontal')
            self.menu = MenuFunctions.HorizOptionsMenu(header, options)
            self.menu_arrangement = 'h'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)

        if event == 'RIGHT' and self.menu_arrangement == 'h' \
            or event == 'DOWN' and self.menu_arrangement == 'v':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveRight()
        elif event == 'LEFT' and self.menu_arrangement == 'h' \
            or event == 'UP' and self.menu_arrangement == 'v':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveLeft()

        elif event == 'BACK':
            GC.SOUNDDICT['Error'].play()

        elif event == 'SELECT':
            selection = self.menu.getSelection()
            self.menu = None
            gameStateObj.game_constants[self.name] = selection
            gameStateObj.game_constants['last_choice'] = selection
            GC.SOUNDDICT['Select 1'].play()
            gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.message:
            gameStateObj.message[-1].draw(mapSurf)
        if self.menu:
            self.menu.draw(mapSurf)
        return mapSurf

class WaitState(StateMachine.State):
    name = 'wait'

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.stateMachine.back()
        for unit in gameStateObj.allunits:
            if unit.hasAttacked and not unit.isDone():
                unit.wait(gameStateObj)
        return 'repeat'

class ShopState(StateMachine.State):
    name = 'shop'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            if self.name in ('armory', 'market'):
                self.opening_message = self.get_dialog(cf.WORDS['Armory_opener'])
                self.portrait = GC.IMAGESDICT['ArmoryPortrait']
                self.buy_message = cf.WORDS['Armory_buy']
                self.back_message = cf.WORDS['Armory_back']
                self.leave_message = cf.WORDS['Armory_leave']
                Engine.music_thread.fade_in(GC.MUSICDICT[cf.CONSTANTS.get('music_armory')])
            elif self.name == 'vendor':
                self.opening_message = self.get_dialog(cf.WORDS['Vendor_opener'])
                self.portrait = GC.IMAGESDICT['VendorPortrait']
                self.buy_message = cf.WORDS['Vendor_buy']
                self.back_message = cf.WORDS['Vendor_back']
                self.leave_message = cf.WORDS['Vendor_leave']
                Engine.music_thread.fade_in(GC.MUSICDICT[cf.CONSTANTS.get('music_vendor')])
            # Get data
            self.unit = gameStateObj.cursor.currentSelectedUnit

            self.buy_value_mod = 1.0
            for status in self.unit.status_effects:
                if status.buy_value_mod:
                    self.buy_value_mod *= status.buy_value_mod

            if self.name == 'market':
                itemids = gameStateObj.market_items
            else:
                itemids = gameStateObj.map.tile_info_dict[self.unit.position]['Shop']

            # Get items
            items_for_sale = [ItemMethods.itemparser(item) for item in itemids.split(',') if item]

            topleft = (GC.WINWIDTH//2 - 80 + 4, 3*GC.WINHEIGHT//8+8)
            self.shopMenu = MenuFunctions.ShopMenu(self.unit, items_for_sale, topleft, limit=5, mode="Buy", buy_value_mod=self.buy_value_mod)
            self.myMenu = MenuFunctions.ShopMenu(self.unit, self.unit.items, topleft, limit=5, mode="Sell")
            self.buy_sell_menu = MenuFunctions.ChoiceMenu(self.unit, [cf.WORDS['Buy'], cf.WORDS['Sell']], (80, 32), background='ActualTransparent', horizontal=True)
            self.sure_menu = MenuFunctions.ChoiceMenu(self.unit, [cf.WORDS['Yes'], cf.WORDS['No']], (80, 32), background='ActualTransparent', horizontal=True)
            self.stateMachine = CustomObjects.StateMachine('open')
            self.display_message = self.opening_message

            self.init_draw()

            self.info = False

            # For background
            gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def init_draw(self):
        self.draw_surfaces = []
        # Light background
        bg = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH+8, 48), 'ClearMenuBackground')
        self.bg = Engine.subsurface(bg, (4, 0, GC.WINWIDTH, 48))
        # Portrait
        PortraitSurf = self.portrait
        self.draw_surfaces.append((PortraitSurf, (3, 0)))
        # Money
        moneyBGSurf = GC.IMAGESDICT['MoneyBG']
        self.draw_surfaces.append((moneyBGSurf, (172, 48)))

        self.money_counter_disp = MenuFunctions.BriefPopUpDisplay((223, 32))

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if self.stateMachine.getState() == 'open':
            if self.display_message.done:
                self.stateMachine.changeState('choice')
            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.changeState('transition_pop')
            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                if self.display_message.waiting: # Remove waiting check
                    self.display_message.waiting = False

        elif self.stateMachine.getState() == 'choice':
            if event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                self.buy_sell_menu.moveDown()
            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                self.buy_sell_menu.moveUp()
            elif event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                self.display_message = self.get_dialog(self.leave_message)
                self.stateMachine.changeState('close')
            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                if not self.display_message.done:
                    if self.display_message.waiting:
                        self.display_message.waiting = False
                else:
                    selection = self.buy_sell_menu.getSelection()
                    if selection == 'Buy':
                        self.shopMenu.takes_input = True
                        self.stateMachine.changeState('buy')
                        self.display_message = self.get_dialog(self.buy_message)
                    elif selection == 'Sell' and len(self.unit.items) > 0:
                        self.myMenu.takes_input = True
                        self.stateMachine.changeState('sell')

        elif self.stateMachine.getState() == 'buy':
            if 'DOWN' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.shopMenu.moveDown(first_push)
            elif 'UP' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.shopMenu.moveUp(first_push)
            elif event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                if self.info:
                    self.info = False
                else:
                    self.shopMenu.takes_input = False
                    self.stateMachine.changeState('choice')
                    self.display_message = self.get_dialog(cf.WORDS['Shop_again'])
            elif event == 'SELECT' and not self.info:
                selection = self.shopMenu.getSelection()
                value = (selection.value * selection.uses.uses) if selection.uses else selection.value
                value = int(value * self.buy_value_mod)
                if ('Convoy' in gameStateObj.game_constants or len(self.unit.items) < cf.CONSTANTS['max_items']) and\
                        (gameStateObj.get_money() - value) >= 0:
                    GC.SOUNDDICT['Select 1'].play()
                    self.stateMachine.changeState('buy_sure')
                    if len(self.unit.items) >= cf.CONSTANTS['max_items']:
                        self.display_message = self.get_dialog(cf.WORDS['Shop_convoy'])
                    else:
                        self.display_message = self.get_dialog(cf.WORDS['Shop_check'])
                    self.shopMenu.takes_input = False
                elif (gameStateObj.get_money() - value) < 0:
                    GC.SOUNDDICT['Select 4'].play()
                    self.display_message = self.get_dialog(cf.WORDS['Shop_no_money'])
                elif len(self.unit.items) >= cf.CONSTANTS['max_items']:
                    GC.SOUNDDICT['Select 4'].play()
                    self.display_message = self.get_dialog(cf.WORDS['Shop_max'])
                    self.shopMenu.takes_input = False
                    self.stateMachine.changeState('choice')
            elif event == 'INFO':
                self.info = not self.info

        elif self.stateMachine.getState() == 'sell':
            if 'DOWN' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.myMenu.moveDown()
            elif 'UP' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.myMenu.moveUp()
            elif event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                if self.info:
                    self.info = False
                else:
                    self.myMenu.takes_input = False
                    self.stateMachine.changeState('choice')
                    self.display_message = self.get_dialog(cf.WORDS['Shop_again'])
            elif event == 'SELECT' and not self.info:
                selection = self.myMenu.getSelection()
                if not selection.value:
                    GC.SOUNDDICT['Select 4'].play()
                    self.myMenu.takes_input = False
                    self.stateMachine.changeState('choice')
                    self.display_message = self.get_dialog(cf.WORDS['Shop_no_value'])
                else:
                    GC.SOUNDDICT['Select 1'].play()
                    self.stateMachine.changeState('sell_sure')
                    self.display_message = self.get_dialog(cf.WORDS['Shop_check'])
                    self.myMenu.takes_input = False
            elif event == 'INFO':
                self.info = not self.info

        elif self.stateMachine.getState() == 'buy_sure':
            if event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                self.sure_menu.moveDown()
            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                self.sure_menu.moveUp()
            elif event == 'BACK':
                self.stateMachine.changeState('buy')
                self.shopMenu.takes_input = True
                self.display_message = self.get_dialog(self.back_message)
            elif event == 'SELECT':
                choice = self.sure_menu.getSelection()
                if choice == cf.WORDS['Yes']:
                    GC.SOUNDDICT['GoldExchange'].play()
                    selection = self.shopMenu.getSelection()
                    value = (selection.value * selection.uses.uses) if selection.uses else selection.value
                    value = int(value * self.buy_value_mod)
                    new_item = ItemMethods.itemparser(str(selection.id), gameStateObj)
                    if len(self.unit.items) >= cf.CONSTANTS['max_items']:
                        Action.execute(Action.PutItemInConvoy(new_item), gameStateObj)
                    else:
                        Action.execute(Action.GiveItem(self.unit, new_item), gameStateObj)
                    # gameStateObj.game_constants['money'] -= value
                    Action.execute(Action.GiveGold(-value, gameStateObj.current_party), gameStateObj)
                    self.money_counter_disp.start(-value)
                    self.display_message = self.get_dialog(cf.WORDS['Shop_buy_again'])
                    Action.do(Action.HasAttacked(self.unit), gameStateObj)
                    self.myMenu.updateOptions(self.unit.items)
                    self.stateMachine.changeState('buy')
                    self.shopMenu.takes_input = True
                else:
                    GC.SOUNDDICT['Select 4'].play()
                    self.stateMachine.changeState('buy')
                    self.shopMenu.takes_input = True
                    self.display_message = self.get_dialog(self.back_message)

        elif self.stateMachine.getState() == 'sell_sure':
            if event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                self.sure_menu.moveDown()
            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                self.sure_menu.moveUp()
            elif event == 'BACK':
                self.stateMachine.changeState('sell')
                self.myMenu.takes_input = True
                self.display_message = self.get_dialog(self.back_message)
            elif event == 'SELECT':
                choice = self.sure_menu.getSelection()
                if choice == cf.WORDS['Yes']:
                    GC.SOUNDDICT['GoldExchange'].play()
                    selection = self.myMenu.getSelection()
                    Action.do(Action.RemoveItem(self.unit, selection), gameStateObj)
                    # self.unit.remove_item(selection)
                    self.myMenu.currentSelection = 0 # Reset selection
                    value = (selection.value * selection.uses.uses)//2 if selection.uses else selection.value//2 # Divide by 2 because selling
                    # gameStateObj.game_constants['money'] += value
                    Action.execute(Action.GiveGold(value, gameStateObj.current_party), gameStateObj)
                    self.money_counter_disp.start(value)
                    self.display_message = self.get_dialog(self.back_message)
                    Action.do(Action.HasAttacked(self.unit), gameStateObj)
                    self.myMenu.updateOptions(self.unit.items)
                    if len(self.unit.items) <= 0:
                        self.myMenu.takes_input = False
                        self.stateMachine.changeState('choice')
                        self.display_message = self.get_dialog(cf.WORDS['Shop_again'])
                    else:
                        self.stateMachine.changeState('sell')
                        self.myMenu.takes_input = True
                        self.display_message = self.get_dialog(cf.WORDS['Shop_sell_again'])
                else:
                    GC.SOUNDDICT['Select 4'].play()
                    self.stateMachine.changeState('sell')
                    self.myMenu.takes_input = True
                    self.display_message = self.get_dialog(self.back_message)

        elif self.stateMachine.getState() == 'close':
            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()
            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                if self.display_message.done:
                    gameStateObj.stateMachine.back()
                if self.display_message.waiting: # Remove waiting check
                    self.display_message.waiting = False

    def get_dialog(self, text):
        return Dialogue.Dialog(text, 'Narrator', (60, 8), (144, 48), 'text_white', 'ActualTransparent', waiting_cursor_flag=False)

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.shopMenu.update()
        self.myMenu.update()
        self.buy_sell_menu.update()
        self.sure_menu.update()
        self.display_message.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)

        surf.blit(self.bg, (0, 8))

        if self.display_message:
            self.display_message.draw(surf)

        if self.stateMachine.getState() in ('sell', 'sell_sure') or \
                (self.stateMachine.getState() == 'choice' and self.buy_sell_menu.getSelection() == cf.WORDS['Sell']):
            self.myMenu.draw(surf, gameStateObj.get_money())
        else:
            self.shopMenu.draw(surf, gameStateObj.get_money())

        if self.stateMachine.getState() == 'choice' and self.display_message.done:
            self.buy_sell_menu.draw(surf)

        if self.stateMachine.getState() in ['buy_sure', 'sell_sure']:
            self.sure_menu.draw(surf)

        for simple_surf, rect in self.draw_surfaces:
            surf.blit(simple_surf, rect)

        money = str(gameStateObj.get_money())
        GC.FONT['text_blue'].blit(money, surf, (223 - GC.FONT['text_yellow'].size(money)[0], 48))
        self.money_counter_disp.draw(surf)

        # Draw current info
        if self.info:
            if self.stateMachine.getState() == 'sell':
                menu = self.myMenu
            else:
                menu = self.shopMenu
            selection = menu.getSelection()
            if selection:
                help_box = selection.get_help_box()
                help_box.draw(surf, (8, 16*menu.get_relative_index() + 32 - 4))

        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.background = None
        gameStateObj.activeMenu = gameStateObj.hidden_active

class RepairShopState(StateMachine.State):
    name = 'repairshop'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.display_message = self.get_dialog(cf.WORDS['Repair_opener'])
            self.portrait = GC.IMAGESDICT['ArmoryPortrait']
            Engine.music_thread.fade_in(GC.MUSICDICT[cf.CONSTANTS.get('music_armory')])

            self.unit = gameStateObj.cursor.currentSelectedUnit

            self.buy_value_mod = 1.0
            for status in self.unit.status_effects:
                if status.buy_value_mod:
                    self.buy_value_mod *= status.buy_value_mod

            topleft = (GC.WINWIDTH//2 - 80 + 4, 3*GC.WINHEIGHT//8+8)

            self.myMenu = MenuFunctions.ShopMenu(
                self.unit, self.unit.items, topleft,
                limit=5, mode="Repair", buy_value_mod=self.buy_value_mod)
            self.sure_menu = MenuFunctions.ChoiceMenu(
                self.unit, [cf.WORDS['Yes'], cf.WORDS['No']], (80, 32),
                background='ActualTransparent', horizontal=True)
            self.state_machine = CustomObjects.StateMachine('open')

            self.init_draw()

            self.info = False

            # For background
            gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def init_draw(self):
        self.draw_surfaces = []
        # Light background
        bg = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH+8, 48), 'ClearMenuBackground')
        self.bg = Engine.subsurface(bg, (4, 0, GC.WINWIDTH, 48))
        # Portrait
        PortraitSurf = self.portrait
        self.draw_surfaces.append((PortraitSurf, (3, 0)))
        # Money
        moneyBGSurf = GC.IMAGESDICT['MoneyBG']
        self.draw_surfaces.append((moneyBGSurf, (172, 48)))

        self.money_counter_disp = MenuFunctions.BriefPopUpDisplay((223, 32))

    def get_dialog(self, text):
        return Dialogue.Dialog(text, 'Narrator', (60, 8), (144, 48), 'text_white', 'ActualTransparent', waiting_cursor_flag=False)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if self.state_machine.getState() == 'open':
            if self.display_message.done:
                self.myMenu.takes_input = True
                self.state_machine.changeState('repair')
            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.changeState('transition_pop')
            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                if self.display_message.waiting: # Remove waiting check
                    self.display_message.waiting = False

        elif self.state_machine.getState() == 'repair':
            if 'DOWN' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.myMenu.moveDown(first_push)
            elif 'UP' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.myMenu.moveUp(first_push)
            elif event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                if self.info:
                    self.info = False
                else:
                    self.state_machine.changeState('close')
                    self.display_message = self.get_dialog(cf.WORDS['Repair_leave'])
            elif event == 'SELECT' and not self.info:
                selection = self.myMenu.getSelection()
                value = (selection.value * (selection.uses.total_uses - selection.uses.uses)) if selection.uses else 0
                value = int(value * self.buy_value_mod)
                if value > 0:
                    GC.SOUNDDICT['Select 1'].play()
                    self.state_machine.changeState('repair_sure')
                    self.display_message = self.get_dialog(cf.WORDS['Repair_check'])
                    self.myMenu.takes_input = False
                else:
                    GC.SOUNDDICT['Select 4'].play()
                    self.display_message = self.get_dialog(cf.WORDS['Repair_no_value'])
            elif event == 'INFO':
                self.info = not self.info

        elif self.state_machine.getState() == 'repair_sure':
            if event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                self.sure_menu.moveDown()
            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                self.sure_menu.moveUp()
            elif event == 'BACK':
                self.state_machine.changeState('repair')
                self.myMenu.takes_input = True
                self.display_message = self.get_dialog(cf.WORDS['Repair_back'])
            elif event == 'SELECT':
                choice = self.sure_menu.getSelection()
                if choice == cf.WORDS['Yes']:
                    GC.SOUNDDICT['GoldExchange'].play()
                    selection = self.myMenu.getSelection()
                    self.myMenu.currentSelection = 0 # Reset selection

                    value = (selection.value * (selection.uses.total_uses - selection.uses.uses)) if selection.uses else 0
                    value = int(value * self.buy_value_mod)
                    Action.execute(Action.GiveGold(-value, gameStateObj.current_party), gameStateObj)
                    self.money_counter_disp.start(-value)

                    Action.do(Action.RepairItem(selection), gameStateObj)

                    self.display_message = self.get_dialog(cf.WORDS['Repair_again'])
                    Action.do(Action.HasAttacked(self.unit), gameStateObj)
                    self.myMenu.updateOptions(self.unit.items)
                    self.state_machine.changeState('repair')
                    self.myMenu.takes_input = True
                else:
                    GC.SOUNDDICT['Select 4'].play()
                    self.state_machine.changeState('repair')
                    self.myMenu.takes_input = True
                    self.display_message = self.get_dialog(cf.WORDS['Repair_back'])

        elif self.state_machine.getState() == 'close':
            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()
            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                if self.display_message.done:
                    gameStateObj.stateMachine.back()
                if self.display_message.waiting: # Remove waiting check
                    self.display_message.waiting = False

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.myMenu.update()
        self.sure_menu.update()
        self.display_message.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)

        surf.blit(self.bg, (0, 8))

        if self.display_message:
            self.display_message.draw(surf)

        self.myMenu.draw(surf, gameStateObj.get_money())

        if self.state_machine.getState() == 'repair_sure':
            self.sure_menu.draw(surf)

        for simple_surf, rect in self.draw_surfaces:
            surf.blit(simple_surf, rect)

        money = str(gameStateObj.get_money())
        GC.FONT['text_blue'].blit(money, surf, (223 - GC.FONT['text_yellow'].size(money)[0], 48))
        self.money_counter_disp.draw(surf)

        # Draw current info
        if self.info:
            selection = self.myMenu.getSelection()
            if selection:
                help_box = selection.get_help_box()
                help_box.draw(surf, (8, 16*self.myMenu.get_relative_index() + 64 - 4))

        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.background = None
        gameStateObj.activeMenu = gameStateObj.hidden_active

class MinimapState(StateMachine.State):
    name = 'minimap'

    def begin(self, gameStateObj, metaDataObj):
        GC.SOUNDDICT['Map In'].play()
        self.minimap = Minimap.MiniMap(gameStateObj.map, gameStateObj.allunits)
        self.arrive_flag = True
        self.arrive_time = Engine.get_time()
        self.exit_flag = False
        self.exit_time = 0
        self.transition_time = 200

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        gameStateObj.cursor.take_input(eventList, gameStateObj)
        if event and not self.arrive_flag and not self.exit_flag:
            # Back - to free state
            if event in ('BACK', 'SELECT', 'START'):
                GC.SOUNDDICT['Map Out'].play()
                self.exit_flag = True
                self.exit_time = Engine.get_time()
                return

    def draw(self, gameStateObj, metaDataObj):
        current_time = Engine.get_time()
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.cursor.drawPortraits(surf, gameStateObj)
        #
        # Update Times
        if self.arrive_flag:
            if current_time - self.transition_time > self.arrive_time:
                self.arrive_flag = False
        elif self.exit_flag:
            if current_time - self.transition_time > self.exit_time:
                gameStateObj.stateMachine.back()
        # Update Progress
        progress = self.transition_time
        if self.arrive_flag:
            progress = min(self.transition_time, current_time - self.arrive_time)
        elif self.exit_flag:
            progress = max(0, self.transition_time - (current_time - self.exit_time))
        # print(progress, self.arrive_flag, self.exit_flag)
        self.minimap.draw(surf, gameStateObj.cameraOffset, progress/float(self.transition_time))
        return surf
