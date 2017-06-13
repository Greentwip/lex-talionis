# Preparations Menu and Base Menu States

# Custom imports
from GlobalConstants import *
from configuration import *
import StateMachine, MenuFunctions, OptionsMenu, SaveLoad, ItemMethods, Banner
import Image_Modification, CustomObjects, Dialogue, WorldMap, InputManager, Engine

class PrepMainState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        Engine.music_thread.fade_in(MUSICDICT[metaDataObj['prep_music']])
        gameStateObj.cursor.drawState = 0
        gameStateObj.boundary_manager.draw_flag = 0
        if gameStateObj.stateMachine.get_last_state() == 'prep_formation':
            fade = True
        else:
            fade = False
        gameStateObj.background = MenuFunctions.StaticBackground(IMAGESDICT['FocusFade'], fade=fade)
        if not self.started:
            options = [WORDS['Manage'], WORDS['Formation'], WORDS['Options'], WORDS['Save'], WORDS['Fight']]
            if metaDataObj['pickFlag']:
                options.insert(0, WORDS['Pick Units'])
            self.menu = MenuFunctions.ChoiceMenu(self, options, 'center', gameStateObj=gameStateObj)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            self.started = False
            return 'repeat'

        # Play prep script if it exists
        if not self.started:
            gameStateObj.cursor.autocursor(gameStateObj)
            self.started = True
            prep_script_name = 'Data/Level' + str(gameStateObj.counters['level']) + '/prepScript.txt'
            if os.path.exists(prep_script_name):
                prep_script = Dialogue.Dialogue_Scene(prep_script_name, None, event_flag=False)
                gameStateObj.message.append(prep_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            self.menu.moveUp()
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            if selection == WORDS['Pick Units']:
                gameStateObj.stateMachine.changeState('prep_pick_units')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Manage']:
                #self.menu = None
                gameStateObj.stateMachine.changeState('prep_items')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Formation']:
                #self.menu = None
                gameStateObj.background = None
                gameStateObj.stateMachine.changeState('prep_formation')
            elif selection == WORDS['Options']:
                gameStateObj.stateMachine.changeState('config_menu')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Save']:
                #SaveLoad.suspendGame(gameStateObj, 'Prep')
                gameStateObj.save_kind = 'Prep'
                gameStateObj.stateMachine.changeState('start_save')
                gameStateObj.stateMachine.changeState('transition_out')
                #gameStateObj.banners.append(Banner.gameSavedBanner())
                #gameStateObj.stateMachine.changeState('itemgain')
            elif selection == WORDS['Fight']:
                #self.menu = None
                gameStateObj.background = None
                gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.update()

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.background = None
        #self.menu = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)
        return mapSurf

class PrepPickUnitsState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and not unit.dead]
            units = sorted(units, key=lambda unit: unit.position, reverse=True)
            gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(units, 2, 6, (110, 24))
            gameStateObj.background = MenuFunctions.MovingBackground(IMAGESDICT['StatusBackground'])

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveLeft()
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveRight()

        elif event == 'SELECT':
            selection = gameStateObj.activeMenu.getSelection()
            if selection.position:
                SOUNDDICT['Select 1'].play()
                selection.position = None
            else:
                possible_position = gameStateObj.check_formation_spots()
                if possible_position:
                    SOUNDDICT['Select 1'].play()
                    selection.position = possible_position
                    selection.reset() # Make sure unit is not 'wait'...
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()
        elif event == 'INFO':
            StateMachine.CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection())

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        MenuFunctions.drawUnitItems(surf, (4, 4 + 40), gameStateObj.activeMenu.getSelection(), include_top=True)

        # Draw Pick Units screen
        backSurf = MenuFunctions.CreateBaseMenuSurf((132, 24), 'BrownPickBackground')
        topleft = (110, 0)
        num_units_map = len([unit for unit in gameStateObj.allunits if unit.position and unit.team == 'player'])
        num_slots = len([value for position, value in gameStateObj.map.tile_info_dict.iteritems() if 'Formation' in value])
        pick_string = ['Pick ', str(num_slots - num_units_map), ' units  ', str(num_units_map), '/', str(num_slots)]
        pick_font = ['text_white', 'text_blue', 'text_white', 'text_blue', 'text_white', 'text_blue']
        word_index = 8
        for index, word in enumerate(pick_string):
            FONT[pick_font[index]].blit(word, backSurf, (word_index, 4))
            word_index += FONT[pick_font[index]].size(word)[0]
        surf.blit(backSurf, topleft)

        return surf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        gameStateObj.background = None

class PrepFormationState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 1
        gameStateObj.boundary_manager.draw_flag = 1
        gameStateObj.cursor.currentSelectedUnit = None

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        # Show R unit status screen
        if event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj)
        elif event == 'AUX':
            CustomObjects.handle_aux_key(gameStateObj)

        # Swap unit positions       
        elif event == 'SELECT':
            gameStateObj.cursor.currentSelectedUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
            if gameStateObj.cursor.currentSelectedUnit:
                if WORDS['Formation'] in gameStateObj.map.tile_info_dict[gameStateObj.cursor.position]:
                    SOUNDDICT['Select 1'].play()
                    gameStateObj.stateMachine.changeState('prep_formation_select')
                else:
                    SOUNDDICT['Select 2'].play()
                    if gameStateObj.cursor.currentSelectedUnit.team.startswith('enemy'):
                        gameStateObj.boundary_manager.toggle_unit(gameStateObj.cursor.currentSelectedUnit, gameStateObj)

        elif event == 'BACK':
            SOUNDDICT['Select 3'].play()
            gameStateObj.stateMachine.back()

        elif event == 'START':
            SOUNDDICT['Select 5'].play()
            gameStateObj.stateMachine.changeState('minimap')

        elif OPTIONS['debug']:
            StateMachine.handle_debug(eventList, gameStateObj, metaDataObj)

        gameStateObj.cursor.take_input(eventList, gameStateObj)
            
    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        gameStateObj.highlight_manager.handle_hover(gameStateObj)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.cursor.drawPortraits(mapSurf, gameStateObj)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.highlight_manager.remove_highlights()

class PrepFormationSelectState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.marker = IMAGESDICT['menuHandRotated']
        self.dynamic_marker_offset = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()
        self.counter = 0

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        # Swap unit positions       
        if event == 'SELECT':
            if WORDS['Formation'] in gameStateObj.map.tile_info_dict[gameStateObj.cursor.position]: 
                SOUNDDICT['Select 1'].play()
                gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
                cur_unit = gameStateObj.cursor.currentSelectedUnit
                if gameStateObj.cursor.currentHoveredUnit:
                    hov_unit = gameStateObj.cursor.currentHoveredUnit
                    hov_unit.leave(gameStateObj)
                    cur_unit.leave(gameStateObj)
                    hov_unit.position, cur_unit.position = cur_unit.position, hov_unit.position
                    cur_unit.arrive(gameStateObj)
                    hov_unit.arrive(gameStateObj)
                else:
                    cur_unit.leave(gameStateObj)
                    cur_unit.position = gameStateObj.cursor.position
                    cur_unit.arrive(gameStateObj)
                gameStateObj.stateMachine.back()
                gameStateObj.cursor.currentSelectedUnit = None
                # Remove unit display
                gameStateObj.cursor.remove_unit_display()
            else:
                SOUNDDICT['Select 3'].play()

        elif event == 'BACK':
            SOUNDDICT['Select 3'].play()
            gameStateObj.stateMachine.back()

        gameStateObj.cursor.take_input(eventList, gameStateObj)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.cursor.drawPortraits(mapSurf, gameStateObj)
        # blit static hand
        if gameStateObj.cursor.currentSelectedUnit:
            current_pos = gameStateObj.cursor.currentSelectedUnit.position
            s_x_pos = (current_pos[0] - gameStateObj.cameraOffset.get_x()) * TILEWIDTH + 2
            s_y_pos = (current_pos[1] - gameStateObj.cameraOffset.get_y() - 1) * TILEHEIGHT
            mapSurf.blit(self.marker, (s_x_pos, s_y_pos))

        # blit dynamic hand
        if WORDS['Formation'] in gameStateObj.map.tile_info_dict[gameStateObj.cursor.position]:
            dynamic_marker_position = gameStateObj.cursor.position
            if Engine.get_time() - 50 > self.lastUpdate:
                self.lastUpdate = Engine.get_time()
                self.counter += 1
                if self.counter > len(self.dynamic_marker_offset) - 1:
                    self.counter = 0
            x_pos = (dynamic_marker_position[0] - gameStateObj.cameraOffset.get_x()) * TILEWIDTH + 2
            y_pos = (dynamic_marker_position[1] - gameStateObj.cameraOffset.get_y() - 1) * TILEHEIGHT + self.dynamic_marker_offset[self.counter]
            mapSurf.blit(self.marker, (x_pos, y_pos))
        return mapSurf

class PrepItemsState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.show_map = False
        if not self.started and gameStateObj.stateMachine.getPreviousState() == 'prep_main':
            gameStateObj.background = None

        if not self.started:
            units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and not unit.dead]
            units = sorted(units, key=lambda unit: bool(unit.position), reverse=True)
            gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(units, 3, 4, 'center')
            if self.name == 'base_items' or self.name == 'base_armory_pick':
                gameStateObj.activeMenu.mode = 'items'
            # for display
            self.buttons = [IMAGESDICT['Buttons'].subsurface(0, 165, 33, 9), IMAGESDICT['Buttons'].subsurface(0, 66, 14, 13)]
            self.font = FONT['text_white']
            self.commands = [WORDS['Optimize'], WORDS['Manage']]
            pos = (33 + self.font.size(self.commands[0])[0] + 16, self.font.size(self.commands[0])[1]*len(self.commands) + 8)
            self.quick_sort_disp = MenuFunctions.CreateBaseMenuSurf(pos, 'BrownBackgroundOpaque')
            self.quick_sort_disp = Image_Modification.flickerImageTranslucent(self.quick_sort_disp, 10)
            for idx, button in enumerate(self.buttons):
                self.quick_sort_disp.blit(button, (4 + 33/2 - button.get_width()/2, idx*self.font.height + 8 - button.get_height()/2 + 4))
            for idx, command in enumerate(self.commands):
                self.font.blit(command, self.quick_sort_disp, (38, idx*self.font.height + 4))

        if not gameStateObj.background:
            gameStateObj.background = MenuFunctions.MovingBackground(IMAGESDICT['StatusBackground'])

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveLeft()
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveRight()

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            gameStateObj.cursor.currentSelectedUnit = selection
            if self.name == 'base_armory_pick':
                gameStateObj.hidden_active = gameStateObj.activeMenu
                #gameStateObj.activeMenu = None
                gameStateObj.stateMachine.changeState('market')
                gameStateObj.stateMachine.changeState('transition_out')
            else:
                gameStateObj.stateMachine.changeState('prep_items_choices')
                #gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection())
        elif event == 'START':
            gameStateObj.quick_sort_inventories(gameStateObj.allunits)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            MenuFunctions.drawUnitItems(surf, (16, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True, shimmer=2)
        # Draw quick sort display
        surf.blit(self.quick_sort_disp, (WINWIDTH/2 + 12, WINHEIGHT/2))
        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None

class PrepItemsChoicesState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.show_map = False
        if not self.started:
            grayed_out = [True, False, True, False, False, False]
            if 'Convoy' in gameStateObj.game_constants:
                grayed_out = [True, False, True, True, True, False]
            if metaDataObj['marketFlag']:
                grayed_out[5] = True
            options = [WORDS['Trade'], WORDS['Use'], WORDS['List'], WORDS['Transfer'], WORDS['Give All'], WORDS['Market']]
            self.menu = MenuFunctions.GreyMenu(gameStateObj.cursor.currentSelectedUnit, options, (128, 80), grayed_out=grayed_out)

        if hasattr(gameStateObj, 'hidden_item_child_option'):
            self.menu.setSelection(gameStateObj.hidden_item_child_option)
        if not gameStateObj.background:
            gameStateObj.background = MenuFunctions.MovingBackground(IMAGESDICT['StatusBackground'])
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.set_extra_marker(False)
        if any(item.usable and item.booster for item in gameStateObj.cursor.currentSelectedUnit.items):
            self.menu.update_grey(1, True)
        else:
            self.menu.update_grey(1, False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            self.menu.moveUp()
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            self.menu.moveRight()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            self.menu.moveLeft()

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            if selection == WORDS['Trade']:
                gameStateObj.stateMachine.changeState('prep_trade_select')
            elif selection == WORDS['Use']:
                gameStateObj.stateMachine.changeState('prep_use_item')
            elif selection == WORDS['Transfer']:
                gameStateObj.stateMachine.changeState('prep_transfer')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Give All']:
                for item in reversed(gameStateObj.cursor.currentSelectedUnit.items):
                    gameStateObj.cursor.currentSelectedUnit.remove_item(item)
                    gameStateObj.convoy.append(item)
            elif selection == WORDS['List']:
                gameStateObj.stateMachine.changeState('prep_list')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Market']:
                gameStateObj.stateMachine.changeState('base_market')
                gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(surf)
        if gameStateObj.activeMenu:
            MenuFunctions.drawUnitItems(surf, (16, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True)
        return surf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.hidden_item_child_option = self.menu.getSelection()
        #self.menu = None

class PrepTradeSelectState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        # Put a marker where gameStateObj.activeMenu is pointing
        if not hasattr(self, 'selection'):
            self.selection = gameStateObj.activeMenu.getSelection()
            self.currentSelection = gameStateObj.activeMenu.currentSelection
            gameStateObj.activeMenu.set_extra_marker(self.currentSelection)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveLeft()
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveRight()

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            gameStateObj.cursor.secondSelectedUnit = selection
            gameStateObj.stateMachine.changeState('prep_trade')
            gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.activeMenu.currentSelection = self.currentSelection
            gameStateObj.stateMachine.back()
        elif event == 'INFO':
            StateMachine.CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection())

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        MenuFunctions.drawUnitItems(mapSurf, (16, 8+16*4), self.selection, include_face=True)
        MenuFunctions.drawUnitItems(mapSurf, (128, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True, right=False)
        return mapSurf

class ConvoyTrader(object):
    def __init__(self, items, convoy):
        self.name = 'Convoy'
        self.items = items
        self.convoy = convoy

    def canWield(self, item):
        return True

    def insert_item(self, index, item):
        self.items.insert(index, item)
        item.owner = 0
        self.convoy.append(item)

    def remove_item(self, item):
        item_index = self.items.index(item)
        self.items.remove(item)
        item.owner = 0
        if item != "Empty Slot":
            self.convoy.remove(item)

class PrepTradeState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.partner = gameStateObj.cursor.secondSelectedUnit
            self.initiator = gameStateObj.cursor.currentSelectedUnit
            if isinstance(self.partner, ItemMethods.ItemObject):
                self.partner = ConvoyTrader([self.partner], gameStateObj.convoy)
            self.menu = MenuFunctions.TradeMenu(self.initiator, self.partner, self.initiator.items, self.partner.items)
            # Hide active menu -- if it exists
            self.hidden_active = gameStateObj.activeMenu
            #self.hidden_child = gameStateObj.childMenu
            gameStateObj.activeMenu = None
            #gameStateObj.childMenu = None

            self.fluid_helper = InputManager.FluidScroll()

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        self.menu.updateOptions(self.initiator.items, self.partner.items)
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif 'UP' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveUp()
        elif event == 'RIGHT':
            if self.menu.moveRight():
                SOUNDDICT['Select 6'].play() # TODO NOT the exact SOuND
        elif event == 'LEFT':
            if self.menu.moveLeft():
                SOUNDDICT['Select 6'].play()

        elif event == 'BACK':
            if self.menu.selection2 is not None:
                SOUNDDICT['Select 4'].play()
                self.menu.selection2 = None
            else:
                SOUNDDICT['Select 2'].play()
                #gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')
                                              
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            if self.menu.selection2 is not None:
                self.menu.tradeItems()
            else:
                self.menu.setSelection()

        elif event == 'INFO':
            self.menu.toggle_info()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)
            self.menu.drawInfo(mapSurf)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        # Unhide active menu
        gameStateObj.activeMenu = self.hidden_active

class PrepUseItemState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.menu = MenuFunctions.ChoiceMenu(gameStateObj.cursor.currentSelectedUnit, gameStateObj.cursor.currentSelectedUnit.items, (16, 72), limit=5, hard_limit=True, gem=False)
        self.menu.draw_face = True
        self.info = False

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            self.menu.moveUp()

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            gameStateObj.stateMachine.back()
            gameStateObj.cursor.currentSelectedUnit.handle_booster(selection, gameStateObj)
        elif event == 'BACK':
            gameStateObj.stateMachine.back()
        elif event == 'INFO':
            self.info = not self.info

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(mapSurf, gameStateObj)
        if self.info:
            selection = None
            position = None
            selection = self.menu.getSelection()
            if selection:
                help_surf = selection.get_help_box()
                height = 16*self.menu.currentSelection - help_surf.get_height() + 64
                position = (16, height)
                help_surf = selection.get_help_box()
                mapSurf.blit(help_surf, position)
        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        self.menu = None

class PrepListState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.name_surf = MenuFunctions.CreateBaseMenuSurf((56, 24), 'TransMenuBackground60')
            self.owner_surf = MenuFunctions.CreateBaseMenuSurf((96, 24), 'TransMenuBackground60')
            self.info = False

            # Hide active Menu
            gameStateObj.childMenu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None

        all_items = self.calc_all_items(gameStateObj)
        if hasattr(self, 'menu'):
            self.menu.updateOptions(all_items)
        else:
            self.menu = MenuFunctions.ConvoyMenu(gameStateObj.cursor.currentSelectedUnit, all_items, (WINWIDTH - 120 - 4, 40))
        self.fluid_helper = InputManager.FluidScroll()

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def calc_all_items(self, gameStateObj):
        my_units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and not unit.dead]
        all_items = [item for item in gameStateObj.convoy]
        for unit in my_units:
            for item in unit.items:
                all_items.append(item)
        return all_items

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif 'UP' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveUp()
        elif 'RIGHT' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveRight()
        elif 'LEFT' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveLeft()

        elif event == 'SELECT':
            selection = self.menu.getSelection()
            if selection and not self.info:
                if selection.owner:
                    SOUNDDICT['Select 1'].play()
                    gameStateObj.stateMachine.changeState('prep_trade')
                    gameStateObj.stateMachine.changeState('transition_out')
                    gameStateObj.cursor.secondSelectedUnit = gameStateObj.get_unit_from_id(selection.owner)
                elif len(gameStateObj.cursor.currentSelectedUnit.items) < CONSTANTS['max_items']:
                    SOUNDDICT['Select 1'].play()
                    gameStateObj.cursor.currentSelectedUnit.add_item(selection)
                    gameStateObj.convoy.remove(selection)
                else: # Unit has too many items -- Trade with convoy instead
                    SOUNDDICT['Select 1'].play()
                    gameStateObj.stateMachine.changeState('prep_trade')
                    gameStateObj.stateMachine.changeState('transition_out')
                    gameStateObj.cursor.secondSelectedUnit = selection
            else: # Nothing selected
                pass
            # Re-update options
            self.menu.updateOptions(self.calc_all_items(gameStateObj))
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            if self.info:
                self.info = False
            else:
                #gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            self.info = not self.info

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(surf)
        # Draw face image
        face_image = gameStateObj.cursor.currentSelectedUnit.bigportrait.copy()
        face_image = Engine.flip_horiz(face_image)
        height = min(face_image.get_height(), 72)
        surf.blit(Engine.subsurface(face_image, (0, 0, face_image.get_width(), height)), (12, 0))
        # Draw name
        surf.blit(self.name_surf, (-2,0))
        name_position = (24 - FONT['text_white'].size(gameStateObj.cursor.currentSelectedUnit.name)[0]/2, 4)
        FONT['text_white'].blit(gameStateObj.cursor.currentSelectedUnit.name, surf, name_position)
        # Draw owner
        surf.blit(self.owner_surf, (156, 0))
        item_owner = None
        if self.menu.getSelection():
            item_owner = gameStateObj.get_unit_from_id(self.menu.getSelection().owner)
        if item_owner:
            item_owner = item_owner.name
        else:
            item_owner = "---"
        owner_string = WORDS["Owner"] + ": " + item_owner
        FONT['text_white'].blit(owner_string, surf, (156+4, 4))
        # Draw units items
        MenuFunctions.drawUnitItems(surf, (4, 72), gameStateObj.cursor.currentSelectedUnit, include_top=False, shimmer=2)
        # Draw current info
        if self.info:
            selection = self.menu.getSelection()
            if selection:
                help_surf = selection.get_help_box()
                height = 16*(self.menu.get_relative_index()+2) + 12 - help_surf.get_height()
                if height < 0:
                    height = 16*(self.menu.get_relative_index()+4) - 4
                left = 64
                if help_surf.get_width() > WINWIDTH - 64 - 4:
                    left = WINWIDTH - help_surf.get_width() - 4
                surf.blit(help_surf, (left, height))

        return surf

    def finish(self, gameStateObj, metaDataObj):
        # Unhide active menu
        gameStateObj.activeMenu = gameStateObj.childMenu
        gameStateObj.childMenu = None

class PrepTransferState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.fluid_helper = InputManager.FluidScroll()
        if not self.started:
            all_items = gameStateObj.convoy
            self.menu = MenuFunctions.ConvoyMenu(gameStateObj.cursor.currentSelectedUnit, all_items, (WINWIDTH - 120 - 4, 40))
            self.menu.set_take_input(False)
            self.choice_menu = MenuFunctions.ChoiceMenu(gameStateObj.cursor.currentSelectedUnit, [WORDS["Give"], WORDS["Take"]], (60, 16), gem=False, background='BrownBackgroundOpaque')
            self.owner_menu = MenuFunctions.ChoiceMenu(gameStateObj.cursor.currentSelectedUnit, gameStateObj.cursor.currentSelectedUnit.items, (8, 72), limit=5, hard_limit=True, width=104, gem=False)
            self.owner_menu.takes_input = False
            self.owner_menu.draw_face = True
            self.state = "Free" # Can also be Give, Take
            self.info = False

            # Hide active menu
            gameStateObj.childMenu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            SOUNDDICT['Select 6'].play()
            if self.state == WORDS['Give']:
                self.owner_menu.moveDown()
            elif self.state == WORDS['Take']:
                self.menu.moveDown()
            else:
                self.choice_menu.moveDown()
        elif 'UP' in directions:
            SOUNDDICT['Select 6'].play()
            if self.state == WORDS['Give']:
                self.owner_menu.moveUp()
            elif self.state == WORDS['Take']:
                self.menu.moveUp()
            else:
                self.choice_menu.moveUp()
        elif 'RIGHT' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveRight()
        elif 'LEFT' in directions:
            SOUNDDICT['Select 6'].play()
            self.menu.moveLeft()

        elif event == 'SELECT':
            if self.state == WORDS['Give']:
                selection = self.owner_menu.getSelection()
                if selection:
                    SOUNDDICT['Select 1'].play()
                    gameStateObj.cursor.currentSelectedUnit.remove_item(selection)
                    gameStateObj.convoy.append(selection)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.menu.goto(selection)
                    # Goto the item in self.menu
                    self.owner_menu.updateOptions(gameStateObj.cursor.currentSelectedUnit.items)
            elif self.state == WORDS['Take']:
                if len(gameStateObj.cursor.currentSelectedUnit.items) < CONSTANTS['max_items']:
                    SOUNDDICT['Select 1'].play()
                    selection = self.menu.getSelection()
                    if selection:
                        gameStateObj.convoy.remove(selection)
                        gameStateObj.cursor.currentSelectedUnit.add_item(selection)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.owner_menu.updateOptions(gameStateObj.cursor.currentSelectedUnit.items)
            else:
                SOUNDDICT['Select 1'].play()
                selection = self.choice_menu.getSelection()
                self.state = selection
                if self.state == WORDS['Give']:
                    self.owner_menu.takes_input = True
                else:
                    self.menu.set_take_input(True)
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            if self.state == WORDS['Give'] or self.state == WORDS['Take']:
                if self.info:
                    self.info = False
                else:
                    self.state = "Free"
                    self.owner_menu.takes_input = False
                    self.menu.set_take_input(False)
            else:
                #gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            if self.state == WORDS['Give'] or self.state == WORDS['Take']:
                self.info = not self.info

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.state == WORDS["Give"]:
            self.owner_menu.update()
        elif self.state == WORDS["Take"]:
            self.menu.update()
        else:
            self.choice_menu.update()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.choice_menu.draw(mapSurf)
        self.owner_menu.draw(mapSurf)
        self.menu.draw(mapSurf)
        # Draw supply portrait
        mapSurf.blit(IMAGESDICT['SupplyPortrait'], (0, 0))
        # Draw current info
        if self.info:
            selection = None
            position = None
            if self.state == WORDS["Give"]:
                selection = self.owner_menu.getSelection()
                if selection:
                    help_surf = selection.get_help_box()
                    height = 16*self.owner_menu.currentSelection - help_surf.get_height() + 64
                    position = (16, height)
            elif self.state == WORDS["Take"]:
                selection = self.menu.getSelection()
                if selection:
                    help_surf = selection.get_help_box()
                    height = 16*(self.menu.get_relative_index()+2) + 12 - help_surf.get_height()
                    if height < 0:
                        height = 16*(self.menu.get_relative_index()+4) - 4
                    left = 64
                    if help_surf.get_width() > WINWIDTH - 64 - 4:
                        left = WINWIDTH - help_surf.get_width() - 4
                    position = (left, height)
            if selection:
                help_surf = selection.get_help_box()
                mapSurf.blit(help_surf, position)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        # Unhide active menu
        gameStateObj.activeMenu = gameStateObj.childMenu
        gameStateObj.childMenu = None

class BaseMarketState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.cur_unit = gameStateObj.cursor.currentSelectedUnit
            cur_time = Engine.get_true_time()
            self.update_options(gameStateObj)
            items_for_sale = ItemMethods.itemparser(','.join(list(gameStateObj.market_items)))
            self.shop_menu = MenuFunctions.ConvoyMenu(None, items_for_sale, (WINWIDTH - 160 - 4, 40), disp_value="Buy")
            self.choice_menu = MenuFunctions.ChoiceMenu(None, [WORDS["Buy"], WORDS["Sell"]], (16, 16), gem=False, background='BrownBackgroundOpaque')
            self.buy_sure_menu = MenuFunctions.ChoiceMenu(None, [WORDS['Buy'], WORDS['Cancel']], 'center', gameStateObj, horizontal=True, gem=False, background='BrownBackgroundOpaque')
            self.sell_sure_menu = MenuFunctions.ChoiceMenu(None, [WORDS['Sell'], WORDS['Cancel']], 'center', gameStateObj, horizontal=True, gem=False, background='BrownBackgroundOpaque')
            self.state = "Free" # Can also be Buy, Sell, Buy_Sure, Sell_Sure
            self.info = False
            self.current_menu = self.shop_menu
            self.fluid_helper = InputManager.FluidScroll(100)

            # Create money surf
            self.money_surf = MenuFunctions.CreateBaseMenuSurf((56, 24))
            g_surf = Engine.subsurface(IMAGESDICT['GoldenWords'], (40, 50, 9, 9))
            self.money_surf.blit(g_surf, (45, 8))

            # Create owner surf
            self.owner_surf = MenuFunctions.CreateBaseMenuSurf((96, 24), 'TransMenuBackground60')

            if not gameStateObj.background:
                gameStateObj.background = MenuFunctions.MovingBackground(IMAGESDICT['StatusBackground'])

            # Hide active menu
            gameStateObj.childMenu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def update_options(self, gameStateObj):
        my_units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and not unit.dead]
        all_items = [item for item in gameStateObj.convoy]
        for unit in my_units:
            for item in unit.items:
                all_items.append(item)              
        if hasattr(self, 'my_menu'):
            self.my_menu.updateOptions(all_items)
        else:
            self.my_menu = MenuFunctions.ConvoyMenu(self.cur_unit, all_items, (WINWIDTH - 160 - 4, 40), disp_value="Sell")

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            SOUNDDICT['Select 6'].play()
            if self.state == "Free":
                self.choice_menu.moveDown()
                selection = self.choice_menu.getSelection()
                if selection == WORDS['Buy']:
                    self.current_menu = self.shop_menu
                else:
                    self.current_menu = self.my_menu
            elif self.state == 'Buy_Sure':
                self.buy_sure_menu.moveDown()
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveDown()
            else:
                self.current_menu.moveDown()
        elif 'UP' in directions:
            SOUNDDICT['Select 6'].play()
            if self.state == "Free":
                self.choice_menu.moveUp()
                selection = self.choice_menu.getSelection()
                if selection == WORDS['Buy']:
                    self.current_menu = self.shop_menu
                else:
                    self.current_menu = self.my_menu
            elif self.state == 'Buy_Sure':
                self.buy_sure_menu.moveUp()
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveUp()
            else:
                self.current_menu.moveUp()
        elif 'RIGHT' in directions:
            SOUNDDICT['Select 6'].play()
            if self.state == 'Buy_Sure':
                self.buy_sure_menu.moveDown()
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveDown()
            else:
                self.my_menu.moveRight()
                self.shop_menu.moveRight()
        elif 'LEFT' in directions:
            SOUNDDICT['Select 6'].play()
            if self.state == 'Buy_Sure':
                self.buy_sure_menu.moveUp()
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveUp()
            else:
                self.my_menu.moveLeft()
                self.shop_menu.moveLeft()

        elif event == 'SELECT':
            if self.state == WORDS['Buy']:
                selection = self.current_menu.getSelection()
                if selection:
                    value = (selection.value * selection.uses.uses) if selection.uses else selection.value
                    if gameStateObj.counters['money'] - value >= 0:
                        self.state = 'Buy_Sure'
                        SOUNDDICT['Select 1'].play()
                    else:
                        # You don't have enough money
                        SOUNDDICT['Select 4'].play()
                else:
                    # You didn't choose anything to buy
                    SOUNDDICT['Select 4'].play()
            elif self.state == 'Buy_Sure':
                selection = self.buy_sure_menu.getSelection()
                if selection == WORDS['Buy']:
                    SOUNDDICT['Select 1'].play()
                    item = ItemMethods.itemparser(str(self.current_menu.getSelection().id))[0] # Create a copy
                    if self.cur_unit and len(self.cur_unit.items) < CONSTANTS['max_items']:
                        self.cur_unit.add_item(item)
                    else:
                        gameStateObj.convoy.append(item)
                    value = (item.value * item.uses.uses) if item.uses else item.value
                    gameStateObj.counters['money'] -= value
                    self.update_options(gameStateObj)
                else:
                    SOUNDDICT['Select 4'].play()
                self.state = WORDS['Buy']
            elif self.state == WORDS['Sell']:
                selection = self.current_menu.getSelection()
                if selection:
                    if selection.value:
                        SOUNDDICT['Select 1'].play()
                        self.state = 'Sell_Sure'
                    else:
                        # No value, can't be sold
                        SOUNDDICT['Select 4'].play()
                else:
                    # You didn't choose anything to sell
                    SOUNDDICT['Select 4'].play()
            elif self.state == 'Sell_Sure':
                selection = self.sell_sure_menu.getSelection()
                if selection == WORDS['Sell']:
                    SOUNDDICT['Select 1'].play()
                    item = self.current_menu.getSelection()
                    value = (item.value * item.uses.uses)/2 if item.uses else item.value/2
                    gameStateObj.counters['money'] += value
                    if item.owner:
                        owner = gameStateObj.get_unit_from_id(item.owner)
                        owner.remove_item(item)
                    else:
                        gameStateObj.convoy.remove(item)
                    self.update_options(gameStateObj)
                else:
                    SOUNDDICT['Select 4'].play()
                self.state = WORDS['Sell']
            else:
                SOUNDDICT['Select 1'].play()
                selection = self.choice_menu.getSelection()
                self.state = selection
                if self.state == WORDS['Buy']:
                    self.current_menu = self.shop_menu
                else:
                    self.current_menu = self.my_menu
                self.current_menu.set_take_input(True)
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            if self.state == WORDS['Buy'] or self.state == WORDS['Sell']:
                if self.info:
                    self.info = False
                else:
                    self.state = "Free"
                    self.current_menu.set_take_input(False)
            elif self.state == 'Buy_Sure':
                self.state = WORDS['Buy']
            elif self.state == 'Sell_Sure':
                self.state = WORDS['Sell']
            else:
                #gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            if self.state == WORDS['Buy'] or self.state == WORDS['Sell']:
                self.info = not self.info

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.state == "Free":
            self.choice_menu.update()
        elif self.state == 'Buy_Sure':
            self.buy_sure_menu.update()
        elif self.state == 'Sell_Sure':
            self.sell_sure_menu.update()
        else:
            self.current_menu.update()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.current_menu.draw(mapSurf, gameStateObj)
        self.choice_menu.draw(mapSurf, gameStateObj)
        
        # Draw Money
        mapSurf.blit(self.money_surf, (10, WINHEIGHT - 24))
        FONT['text_blue'].blit(str(gameStateObj.counters['money']), mapSurf, (16, WINHEIGHT - 20))

        # Draw owner
        mapSurf.blit(self.owner_surf, (156, 0))
        item_owner = None
        if self.current_menu.getSelection():
            item_owner = gameStateObj.get_unit_from_id(self.current_menu.getSelection().owner)
        if item_owner:
            item_owner = item_owner.name
        elif self.state == WORDS["Sell"] or (self.state == "Free" and self.choice_menu.getSelection() == WORDS['Sell']):
            item_owner = "Convoy"
        else:
            item_owner = "Market"
        owner_string = WORDS["Owner"] + ": " + item_owner
        FONT['text_white'].blit(owner_string, mapSurf, (156+4, 4))

        # Draw current info
        if self.info:
            selection = self.current_menu.getSelection()
            if selection:
                help_surf = selection.get_help_box()
                height = 16*(self.current_menu.get_relative_index()+2) + 12 - help_surf.get_height()
                if height < 0:
                    height = 16*(self.current_menu.get_relative_index()+4) - 4
                left = 64
                if help_surf.get_width() > WINWIDTH - 64 - 4:
                    left = WINWIDTH - help_surf.get_width() - 4
                mapSurf.blit(help_surf, (left, height))

        if self.state == 'Buy_Sure':
            self.buy_sure_menu.draw(mapSurf, gameStateObj)
        elif self.state == 'Sell_Sure':
            self.sell_sure_menu.draw(mapSurf, gameStateObj)

        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        # Unhide active menu
        gameStateObj.activeMenu = gameStateObj.childMenu
        gameStateObj.childMenu = None

class BaseMainState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        Engine.music_thread.fade_in(MUSICDICT[metaDataObj['base_music']])
        self.done = False
        self.show_map = False
        gameStateObj.cursor.drawState = 0
        background_image = IMAGESDICT[metaDataObj['baseFlag']]
        gameStateObj.background = MenuFunctions.StaticBackground(background_image, fade=False)
        if gameStateObj.main_menu:
            gameStateObj.activeMenu = gameStateObj.main_menu
            gameStateObj.main_menu = None
        elif not gameStateObj.activeMenu:
            options = [WORDS['Items'], WORDS['Market'], WORDS['Info'], WORDS['Codex'], WORDS['Save'], WORDS['Continue']]
            color_control = ['text_white', 'text_grey', 'text_grey', 'text_white', 'text_white', 'text_white']
            if gameStateObj.support:
                options.insert(3, WORDS['Supports'])
                color_control.insert(3, 'text_grey')
            if metaDataObj['marketFlag']:
                color_control[1] = 'text_white'
            if gameStateObj.base_conversations:
                color_control[2] = 'text_white'
            if gameStateObj.support and 'AllowSupports' in gameStateObj.game_constants:
                color_control[3] = 'text_white'
            topleft = 4, WINHEIGHT/2 - (len(options)*16 + 8)/2
            gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(self, options, topleft, color_control=color_control, shimmer=2, gem=False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition() or not self.started:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

        # Play base script if it exists
        base_script_name = 'Data/Level' + str(gameStateObj.counters['level']) + '/in_base_script.txt'
        if os.path.exists(base_script_name):
            base_script = Dialogue.Dialogue_Scene(base_script_name, None, event_flag=False)
            gameStateObj.message.append(base_script)
            gameStateObj.stateMachine.changeState('transparent_dialogue')
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
        elif event == 'SELECT':
            selection = gameStateObj.activeMenu.getSelection()
            if gameStateObj.activeMenu.color_control[gameStateObj.activeMenu.currentSelection] == 'text_grey':
                pass
            elif selection == WORDS['Items']:
                SOUNDDICT['Select 1'].play()
                gameStateObj.main_menu = gameStateObj.activeMenu
                #gameStateObj.activeMenu = None
                gameStateObj.stateMachine.changeState('base_items')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Market']:
                SOUNDDICT['Select 1'].play()
                gameStateObj.cursor.currentSelectedUnit = None
                gameStateObj.stateMachine.changeState('base_market')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Info']:
                SOUNDDICT['Select 1'].play()
                gameStateObj.stateMachine.changeState('base_info')
            elif selection == WORDS['Supports']:
                SOUNDDICT['Select 1'].play()
                gameStateObj.stateMachine.changeState('base_support_child')
            elif selection == WORDS['Codex']:
                SOUNDDICT['Select 1'].play()
                gameStateObj.stateMachine.changeState('base_codex_child')
            elif selection == WORDS['Save']:
                SOUNDDICT['Select 1'].play()
                #SaveLoad.suspendGame(gameStateObj, 'Base')
                gameStateObj.save_kind = 'Base'
                gameStateObj.stateMachine.changeState('start_save')
                gameStateObj.stateMachine.changeState('transition_out')
                #gameStateObj.banners.append(Banner.gameSavedBanner())
                #gameStateObj.stateMachine.changeState('itemgain')
            elif selection == WORDS['Continue']:
                SOUNDDICT['Select 1'].play()
                self.done = True
                #gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')

    def finish(self, gameStateObj, metaDataObj):
        #if self.done:
        gameStateObj.background = None
        gameStateObj.activeMenu = None

class BaseInfoState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        options = [key for key in gameStateObj.base_conversations]
        color_control = [('text_white' if white else 'text_grey') for key, white in gameStateObj.base_conversations.iteritems()]
        topleft = 4 + gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.topleft[1] + 2*16
        gameStateObj.childMenu = MenuFunctions.ChoiceMenu(self, options, topleft, color_control=color_control, gem=False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition() or gameStateObj.stateMachine.get_last_state() == 'dialogue':
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp()
        elif event == 'SELECT':
            selection = gameStateObj.childMenu.getSelection()
            if gameStateObj.childMenu.color_control[gameStateObj.childMenu.currentSelection] == 'text_white':
                SOUNDDICT['Select 1'].play()
                dialogue_script = 'Data/Level' + str(gameStateObj.counters['level']) + '/baseScript.txt'
                gameStateObj.message.append(Dialogue.Dialogue_Scene(dialogue_script, selection))
                gameStateObj.stateMachine.changeState('dialogue')
                gameStateObj.stateMachine.changeState('transition_out')
            return
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.childMenu = None

class BaseSupportChildState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if gameStateObj.hidden_active and gameStateObj.hidden_child:
            gameStateObj.activeMenu = gameStateObj.hidden_active
            gameStateObj.childMenu = gameStateObj.hidden_child
            gameStateObj.hidden_active = None
            gameStateObj.hidden_child = None

        if not gameStateObj.childMenu:
            options = [WORDS['Pairings'], WORDS['Conversations']]
            topleft = 4 + gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.topleft[1] + 3*16
            gameStateObj.childMenu = MenuFunctions.ChoiceMenu(self, options, topleft)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp()
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.childMenu.getSelection()
            if selection == WORDS['Pairings']:
                gameStateObj.stateMachine.changeState('base_pairing')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Conversations']:
                gameStateObj.stateMachine.changeState('base_support_convos')
                gameStateObj.stateMachine.changeState('transition_out')
            gameStateObj.hidden_active = gameStateObj.activeMenu
            gameStateObj.hidden_child = gameStateObj.childMenu
            gameStateObj.activeMenu = None
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.childMenu = None

class BasePairingState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and unit.name in gameStateObj.support.node_dict \
                 and any(o_unit.name in gameStateObj.support.node_dict[unit.name].adjacent for o_unit in gameStateObj.allunits)]
        if not gameStateObj.activeMenu:
            gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(self.units, 3, 3, 'center')
            gameStateObj.activeMenu.mode = 'support'

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveLeft()
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveRight()
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            gameStateObj.cursor.currentSelectedUnit = selection
            gameStateObj.stateMachine.changeState('base_pairing_select')
            # Hide this menu
            gameStateObj.pair_menu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            StateMachine.CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu:
            MenuFunctions.drawUnitSupport(surf, gameStateObj.activeMenu.getSelection(), None, gameStateObj)
        return surf

class BasePairingSelectState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.selection = gameStateObj.cursor.currentSelectedUnit
        self.units = [unit for unit in gameStateObj.allunits if unit.name in gameStateObj.support.node_dict[self.selection.name].adjacent]
        gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(self.units, 3, 3, 'center')
        gameStateObj.activeMenu.mode = 'support'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveLeft()
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveRight()
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            # Re-pair
            gameStateObj.support.pair(selection.name, self.selection.name)
            gameStateObj.stateMachine.back()
            # Unhide
            gameStateObj.activeMenu = gameStateObj.pair_menu
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()
            # Unhide
            gameStateObj.activeMenu = gameStateObj.pair_menu
        elif event == 'INFO':
            StateMachine.CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        MenuFunctions.drawUnitSupport(surf, self.selection, gameStateObj.activeMenu.getSelection(), gameStateObj)
        return surf

class BaseSupportConvoState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and not unit.generic_flag]
        if not hasattr(self, 'state'):
            gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(self.units, 1, 9, (4, 4))
            gameStateObj.activeMenu.mode = 'support'
            gameStateObj.childMenu = MenuFunctions.SupportMenu(gameStateObj.activeMenu.getSelection(), gameStateObj, (80, 16))
            self.state = False

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            if self.state:
                gameStateObj.childMenu.moveDown()
            else:
                gameStateObj.activeMenu.moveDown()
                gameStateObj.childMenu.owner = gameStateObj.activeMenu.getSelection()
                gameStateObj.childMenu.updateOptions(gameStateObj)
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            if self.state:
                gameStateObj.childMenu.moveUp()
            else:
                gameStateObj.activeMenu.moveUp()
                gameStateObj.childMenu.owner = gameStateObj.activeMenu.getSelection()
                gameStateObj.childMenu.updateOptions(gameStateObj)
        elif event == 'LEFT':
            if self.state:
                SOUNDDICT['Select 6'].play()
                self.state = gameStateObj.childMenu.moveLeft()
                gameStateObj.childMenu.cursor_flag = self.state
        elif event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            if self.state:
                gameStateObj.childMenu.moveRight()
            else:
                self.state = True
                gameStateObj.childMenu.cursor_flag = True
        elif event == 'SELECT':
            # Play conversation
            if self.state:
                SOUNDDICT['Select 1'].play()
                unit, level = gameStateObj.childMenu.getSelection()
                owner = gameStateObj.childMenu.owner
                edge = gameStateObj.support.node_dict[owner.name].adjacent[unit.name]
                support_level = edge.current_value/CONSTANTS['support_points']
                # if OPTIONS['debug']:
                #     print(level, support_level)
                if level < support_level:
                    if level == 0:
                        level = 'C'
                    elif level == 1:
                        level = 'B'
                    elif level == 2:
                        level = 'A'
                    elif level == 3:
                        level = 'S'
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(edge.script, level))
                    gameStateObj.stateMachine.changeState('dialogue')
                    gameStateObj.stateMachine.changeState('transition_out')
                    edge.unread = False
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.activeMenu = None
            gameStateObj.childMenu = None
            #gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            StateMachine.CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)

class BaseCodexChildState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not gameStateObj.childMenu:
            options = [WORDS['Library'], WORDS['Records']]
            if 'WorldMap' in gameStateObj.game_constants:
                options.insert(1, WORDS['Map'])
            topleft = 4 + gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.topleft[1] + (4*16 if gameStateObj.support else 3*16)
            gameStateObj.childMenu = MenuFunctions.ChoiceMenu(self, options, topleft, gem=False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp()
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.childMenu.getSelection()
            if selection == WORDS['Library'] and gameStateObj.unlocked_lore:
                gameStateObj.stateMachine.changeState('base_library')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Map']:
                gameStateObj.stateMachine.changeState('base_map')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Records']:
                gameStateObj.stateMachine.changeState('base_records')
                gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.childMenu = None
            gameStateObj.stateMachine.back()

class BaseMapState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.hidden_active = gameStateObj.activeMenu
        gameStateObj.activeMenu = None

        gameStateObj.old_background = gameStateObj.background
        gameStateObj.background = WorldMap.WorldMapBackground(IMAGESDICT['WorldMap'])

        # Set up cursor
        self.moveUp = False
        self.moveDown = False
        self.moveRight = False
        self.moveLeft = False
        self.lastMove = Engine.get_time()

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')
            return

        if gameStateObj.input_manager.is_pressed('LEFT'):
            self.moveRight = False
            self.moveLeft = True
        else:
            self.moveLeft = False

        if gameStateObj.input_manager.is_pressed('RIGHT'):
            self.moveLeft = False
            self.moveRight = True
        else:
            self.moveRight = False

        if gameStateObj.input_manager.is_pressed('UP'):
            self.moveDown = False
            self.moveUp = True
        else:
            self.moveUp = False

        if gameStateObj.input_manager.is_pressed('DOWN'):
            self.moveUp = False
            self.moveDown = True
        else:
            self.moveDown = False

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        current_time = Engine.get_time()
        if current_time - self.lastMove > 30:
            self.lastMove = current_time
            if self.moveUp:
                gameStateObj.background.move((0, -8))
            if self.moveDown:
                gameStateObj.background.move((0, 8))
            if self.moveRight:
                gameStateObj.background.move((8, 0))
            if self.moveLeft:
                gameStateObj.background.move((-8, 0))

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = self.hidden_active
        gameStateObj.background = gameStateObj.old_background

class BaseLibraryState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.hidden_active = gameStateObj.activeMenu
            self.hidden_child = gameStateObj.childMenu
            gameStateObj.activeMenu = None
            gameStateObj.childMenu = None

            options, ignore, color_control = [], [], []
            unlocked_entries = [(entry, data) for entry, data in metaDataObj['lore'].iteritems() if entry in gameStateObj.unlocked_lore]
            categories = sorted(list(set([data['type'] for entry, data in unlocked_entries])))
            for category in categories:
                options.append(category)
                ignore.append(True)
                color_control.append('text_yellow')
                for name in sorted([name for name, data in unlocked_entries if data['type'] == category]):
                    options.append(name)
                    ignore.append(False)
                    color_control.append('text_white')

            gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(self, options, (4,4), limit=9, hard_limit=True, ignore=ignore, color_control=color_control)
            gameStateObj.activeMenu.moveDown()
            self.menu = MenuFunctions.Lore_Display(metaDataObj['lore'][gameStateObj.activeMenu.getSelection()])

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
            self.menu.update_entry(metaDataObj['lore'][gameStateObj.activeMenu.getSelection()])
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()
            self.menu.update_entry(metaDataObj['lore'][gameStateObj.activeMenu.getSelection()])
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(mapSurf)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = self.hidden_active
        gameStateObj.childMenu = self.hidden_child

class BaseRecordsState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.hidden_active = gameStateObj.activeMenu
            self.hidden_child = gameStateObj.childMenu
            gameStateObj.activeMenu = None
            gameStateObj.childMenu = None

            self.records = MenuFunctions.RecordsDisplay(gameStateObj.statistics)
            self.chapter_stats = [MenuFunctions.ChapterStats(level) for level in gameStateObj.statistics]
            self.mvp = MenuFunctions.MVPDisplay(gameStateObj.statistics)
            # Create name dict
            self.name_dict = {}
            for level in gameStateObj.statistics:
                for unit, record in level.stats.iteritems():
                    if not unit in self.name_dict:
                        self.name_dict[unit] = []
                    self.name_dict[unit].append((level.name, record))
            self.name_list = [(k, v) for (k, v) in self.name_dict.iteritems()]
            self.name_list = sorted(self.name_list, key=lambda x: self.mvp.mvp_dict[x[0]], reverse=True)
            self.unit_stats = [MenuFunctions.UnitStats(unit, record) for (unit, record) in self.name_list]
            self.state = "records"
            self.current_menu = self.records
            self.current_offset_x = 0
            self.current_offset_y = 0
            self.prev_menu = None
            self.prev_offset_x = 0
            self.prev_offset_y = 0

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'
            elif gameStateObj.stateMachine.get_last_state() == 'dialogue':
                self.current_offset_y = WINHEIGHT

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            self.current_menu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            self.current_menu.moveUp()
        elif event == 'LEFT':
            self.prev_menu = self.current_menu
            self.current_offset_x = -WINWIDTH
            self.prev_offset_x = 1
            SOUNDDICT['Select 6'].play()
            if self.state == 'records':
                self.state = "mvp"
                self.current_menu = self.mvp
            elif self.state == 'mvp':
                self.state = "records"
                self.current_menu = self.records
            elif self.state == 'chapter':
                self.records.moveUp()
                self.current_menu = self.chapter_stats[self.records.currentSelection]
            elif self.state == 'unit':
                self.mvp.moveUp()
                self.current_menu = self.unit_stats[self.mvp.currentSelection]
        elif event == 'RIGHT':
            self.prev_menu = self.current_menu
            self.current_offset_x = WINWIDTH
            self.prev_offset_x = -1
            SOUNDDICT['Select 6'].play()
            if self.state == 'records':
                self.state = "mvp"
                self.current_menu = self.mvp
            elif self.state == 'mvp':
                self.state = 'records'
                self.current_menu = self.records
            elif self.state == 'chapter':
                self.records.moveDown()
                self.current_menu = self.chapter_stats[self.records.currentSelection]
            elif self.state == 'unit':
                self.mvp.moveDown()
                self.current_menu = self.unit_stats[self.mvp.currentSelection]
        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            if self.state in {'records', 'mvp'}:
                self.prev_menu = self.current_menu
                self.current_offset_y = WINHEIGHT
                self.prev_offset_y = -1
            if self.state == 'records':
                self.state = "chapter"
                self.current_menu = self.chapter_stats[self.current_menu.currentSelection]
            elif self.state == 'mvp':
                self.state = "unit"
                self.current_menu = self.unit_stats[self.current_menu.currentSelection]
        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            if self.state == 'records' or self.state == 'mvp':
                gameStateObj.stateMachine.changeState('transition_pop')
            else:
                self.prev_menu = self.current_menu
                self.current_offset_y = -WINHEIGHT
                self.prev_offset_y = 1

            if self.state == 'unit':
                self.state = 'mvp'
                self.current_menu = self.mvp
            elif self.state == 'chapter':
                self.state = 'records'
                self.current_menu = self.records

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.current_menu.update()
        # Handle transitions
        # X axis
        if self.current_offset_x > 0:
            self.current_offset_x -= 16
        elif self.current_offset_x < 0:
            self.current_offset_x += 16
        if self.prev_menu:
            if self.prev_offset_x > 0:
                self.prev_offset_x += 16
            elif self.prev_offset_x < 0:
                self.prev_offset_x -= 16
            if self.prev_offset_x > WINWIDTH or self.prev_offset_x < -WINWIDTH:
                self.prev_offset_x = 0
                self.prev_menu = None
        # Y axis
        if self.current_offset_y > 0:
            self.current_offset_y -= 16
        elif self.current_offset_y < 0:
            self.current_offset_y += 16
        if self.prev_menu:
            if self.prev_offset_y > 0:
                self.prev_offset_y += 16
            elif self.prev_offset_y < 0:
                self.prev_offset_y -= 16
            if self.prev_offset_y > WINHEIGHT or self.prev_offset_y < -WINHEIGHT:
                self.prev_offset_y = 0
                self.prev_menu = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.message:
            gameStateObj.message[-1].draw(mapSurf)
        self.current_menu.draw(mapSurf, self.current_offset_x, self.current_offset_y)
        if self.prev_menu:
            self.prev_menu.draw(mapSurf, self.prev_offset_x, self.prev_offset_y)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = self.hidden_active
        gameStateObj.childMenu = self.hidden_child