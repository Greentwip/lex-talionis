# Preparations Menu and Base Menu States
import os

# Custom imports
from . import GlobalConstants as GC
from . import configuration as cf
from . import Image_Modification, Engine, TextChunk
from . import StateMachine, MenuFunctions, ItemMethods, GeneralStates
from . import CustomObjects, Dialogue, WorldMap, Action
from . import Background, BaseMenuSurf, Banner

class PrepMainState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        Engine.music_thread.fade_in(GC.MUSICDICT[metaDataObj['prep_music']])
        gameStateObj.cursor.drawState = 0
        gameStateObj.cursor.autocursor(gameStateObj)
        gameStateObj.boundary_manager.draw_flag = 0
        if gameStateObj.stateMachine.get_last_state() == 'prep_formation':
            fade = True
        else:
            fade = False
        gameStateObj.background = Background.StaticBackground(GC.IMAGESDICT['FocusFade'], fade=fade)
        if not self.started:
            options = [cf.WORDS['Manage'], cf.WORDS['Formation'], cf.WORDS['Options'], cf.WORDS['Save'], cf.WORDS['Fight']]
            if metaDataObj['pickFlag']:
                options.insert(0, cf.WORDS['Pick Units'])
            self.menu = MenuFunctions.ChoiceMenu(self, options, 'center', gameStateObj=gameStateObj)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            self.started = False
            return 'repeat'

        # Play prep script if it exists
        if not self.started:
            self.started = True
            prep_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/prepScript.txt'
            if os.path.exists(prep_script_name):
                prep_script = Dialogue.Dialogue_Scene(prep_script_name)
                gameStateObj.message.append(prep_script)
                gameStateObj.stateMachine.changeState('transparent_dialogue')

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
        
        if event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            if selection == cf.WORDS['Pick Units']:
                gameStateObj.stateMachine.changeState('prep_pick_units')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Manage']:
                # self.menu = None
                gameStateObj.stateMachine.changeState('prep_items')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Formation']:
                # self.menu = None
                gameStateObj.background = None
                gameStateObj.stateMachine.changeState('prep_formation')
            elif selection == cf.WORDS['Options']:
                gameStateObj.stateMachine.changeState('config_menu')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Save']:
                # SaveLoad.suspendGame(gameStateObj, 'Prep')
                gameStateObj.save_kind = 'Prep'
                gameStateObj.stateMachine.changeState('start_save')
                gameStateObj.stateMachine.changeState('transition_out')
                # gameStateObj.banners.append(Banner.gameSavedBanner())
                # gameStateObj.stateMachine.changeState('itemgain')
            elif selection == cf.WORDS['Fight']:
                if any(unit.position for unit in gameStateObj.allunits if unit.team == 'player'):
                    # self.menu = None
                    gameStateObj.background = None
                    gameStateObj.stateMachine.back()
                else:
                    GC.SOUNDDICT['Select 4'].play()
                    gameStateObj.banners.append(Banner.customBanner("Must select at least one unit!"))
                    gameStateObj.stateMachine.changeState('itemgain')

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.update()

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.background = None
        # self.menu = None

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.menu:
            self.menu.draw(mapSurf, gameStateObj)
        return mapSurf

class PrepPickUnitsState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started and gameStateObj.stateMachine.getPreviousState() == 'prep_main':
            gameStateObj.background = None

        if not self.started:
            player_units = gameStateObj.get_units_in_party(gameStateObj.current_party) 
            lord_units = [unit for unit in player_units if unit.position and 'Formation' not in gameStateObj.map.tile_info_dict[unit.position]]
            non_lord_units = [unit for unit in player_units if unit not in lord_units]
            self.units = lord_units + sorted(non_lord_units, key=lambda unit: bool(unit.position), reverse=True)
            gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(self.units, 2, 6, (110, 24))
    
        if not gameStateObj.background:
            gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveUp(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveLeft(first_push)
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveRight(first_push)

        if event == 'SELECT':
            selection = gameStateObj.activeMenu.getSelection()
            if selection.position and 'Formation' not in gameStateObj.map.tile_info_dict[selection.position]:
                GC.SOUNDDICT['Select 4'].play()  # Locked/Lord Character
            elif selection.position:
                GC.SOUNDDICT['Select 1'].play()
                selection.leave(gameStateObj)
                Action.RemoveFromMap(selection).do(gameStateObj)
            else:
                possible_position = gameStateObj.check_formation_spots()
                # Check for fatigue
                is_fatigued = False
                if cf.CONSTANTS['fatigue'] and gameStateObj.game_constants['Fatigue'] == 1:
                    if selection.fatigue >= GC.EQUATIONS.get_max_fatigue(selection):
                        is_fatigued = True
                if possible_position and not is_fatigued:
                    GC.SOUNDDICT['Select 1'].play()
                    Action.PlaceOnMap(selection, possible_position).do(gameStateObj)
                    selection.arrive(gameStateObj)
                    selection.reset() # Make sure unit is not 'wait'...
                elif is_fatigued:
                    GC.SOUNDDICT['Select 4'].play()  # Unit is fatigued and cannot be deployed
                    
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu and gameStateObj.activeMenu.getSelection():
            MenuFunctions.drawUnitItems(surf, (4, 4 + 40), gameStateObj.activeMenu.getSelection(), include_top=True)

        # Draw Pick Units screen
        backSurf = BaseMenuSurf.CreateBaseMenuSurf((132, 24), 'WhiteMenuBackgroundOpaque')
        topleft = (110, 4)
        player_units = [unit for unit in gameStateObj.allunits if unit.position and unit.team == 'player']
        num_lords = len([unit for unit in player_units if 'Formation' not in gameStateObj.map.tile_info_dict[unit.position]])
        num_units_map = len(player_units)
        num_slots = num_lords + len([value for position, value in gameStateObj.map.tile_info_dict.items() if 'Formation' in value])
        pick_string = ['Pick ', str(num_slots - num_units_map), ' units  ', str(num_units_map), '/', str(num_slots)]
        pick_font = ['text_white', 'text_blue', 'text_white', 'text_blue', 'text_white', 'text_blue']
        word_index = 8
        for index, word in enumerate(pick_string):
            GC.FONT[pick_font[index]].blit(word, backSurf, (word_index, 4))
            word_index += GC.FONT[pick_font[index]].size(word)[0]
        surf.blit(backSurf, topleft)

        # Useful for telling at a glance which units are fatigued
        if cf.CONSTANTS['fatigue'] and gameStateObj.activeMenu and gameStateObj.activeMenu.getSelection():
            base_surf = BaseMenuSurf.CreateBaseMenuSurf((132, 24))
            topleft = (110, 128 + 4)
            unit = gameStateObj.activeMenu.getSelection()
            if unit.fatigue >= GC.EQUATIONS.get_max_fatigue(unit):
                text = cf.WORDS["Fatigued"]
            else:
                text = cf.WORDS["Ready!"]
            length = GC.FONT['text_white'].size(text)[0]
            GC.FONT['text_white'].blit(text, base_surf, (132//2 - length//2, 4))
            surf.blit(base_surf, topleft)

        gameStateObj.activeMenu.draw_units(surf, -16, gameStateObj)
        gameStateObj.activeMenu.draw_cursor(surf, -16)

        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        # gameStateObj.background = None

class PrepFormationState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 1
        gameStateObj.boundary_manager.draw_flag = 1
        gameStateObj.cursor.currentSelectedUnit = None

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if cf.OPTIONS['cheat'] and 'AUX' in gameStateObj.input_manager.key_down_events and 'INFO' in gameStateObj.input_manager.key_down_events:
            gameStateObj.stateMachine.changeState('debug')
            
        # Show R unit status screen
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj)
        elif event == 'AUX':
            CustomObjects.handle_aux_key(gameStateObj)

        # Swap unit positions       
        elif event == 'SELECT':
            gameStateObj.cursor.currentSelectedUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
            if gameStateObj.cursor.currentSelectedUnit:
                if cf.WORDS['Formation'] in gameStateObj.map.tile_info_dict[gameStateObj.cursor.position]:
                    GC.SOUNDDICT['Select 3'].play()
                    gameStateObj.stateMachine.changeState('prep_formation_select')
                else:
                    GC.SOUNDDICT['Select 2'].play()
                    if gameStateObj.cursor.currentSelectedUnit.team.startswith('enemy'):
                        gameStateObj.boundary_manager.toggle_unit(gameStateObj.cursor.currentSelectedUnit)

        elif event == 'BACK':
            GC.SOUNDDICT['Select 1'].play()
            gameStateObj.stateMachine.back()

        elif event == 'START':
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.stateMachine.changeState('minimap')

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
        self.marker = GC.IMAGESDICT['menuHandRotated']
        self.dynamic_marker_offset = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()
        self.counter = 0

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        # Swap unit positions       
        if event == 'SELECT':
            if cf.WORDS['Formation'] in gameStateObj.map.tile_info_dict[gameStateObj.cursor.position]: 
                GC.SOUNDDICT['FormationSelect'].play()
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
                GC.SOUNDDICT['Error'].play()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

        elif event == 'AUX':
            gameStateObj.cursor.setPosition(gameStateObj.cursor.currentSelectedUnit.position, gameStateObj)

        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj)

        gameStateObj.cursor.take_input(eventList, gameStateObj)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        gameStateObj.cursor.drawPortraits(mapSurf, gameStateObj)
        # blit static hand
        if gameStateObj.cursor.currentSelectedUnit:
            current_pos = gameStateObj.cursor.currentSelectedUnit.position
            s_x_pos = (current_pos[0] - gameStateObj.cameraOffset.get_x()) * GC.TILEWIDTH + 2
            s_y_pos = (current_pos[1] - gameStateObj.cameraOffset.get_y() - 1) * GC.TILEHEIGHT
            mapSurf.blit(self.marker, (s_x_pos, s_y_pos))

        # blit dynamic hand
        if cf.WORDS['Formation'] in gameStateObj.map.tile_info_dict[gameStateObj.cursor.position]:
            dynamic_marker_position = gameStateObj.cursor.position
            if Engine.get_time() - 50 > self.lastUpdate:
                self.lastUpdate = Engine.get_time()
                self.counter += 1
                if self.counter > len(self.dynamic_marker_offset) - 1:
                    self.counter = 0
            x_pos = (dynamic_marker_position[0] - gameStateObj.cameraOffset.get_x()) * GC.TILEWIDTH + 2
            y_pos = (dynamic_marker_position[1] - gameStateObj.cameraOffset.get_y() - 1) * GC.TILEHEIGHT + self.dynamic_marker_offset[self.counter]
            mapSurf.blit(self.marker, (x_pos, y_pos))
        return mapSurf

def draw_funds(surf, gameStateObj):
    # Draw R: Info display
    helper = Engine.get_key_name(cf.OPTIONS['key_INFO']).upper()
    GC.FONT['text_yellow'].blit(helper, surf, (123, 143))
    GC.FONT['text_white'].blit(': Info', surf, (123 + GC.FONT['text_blue'].size(helper)[0], 143))
    # Draw Funds display
    surf.blit(GC.IMAGESDICT['FundsDisplay'], (168, 137))
    money = str(gameStateObj.get_money())
    size = GC.FONT['text_blue'].size(money)[0]
    GC.FONT['text_blue'].blit(money, surf, (219 - size, 141))

class PrepItemsState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started and gameStateObj.stateMachine.getPreviousState() == 'prep_main':
            gameStateObj.background = None

        if not self.started:
            # print([(unit.name, unit.dead) for unit in gameStateObj.allunits])
            player_units = gameStateObj.get_units_in_party(gameStateObj.current_party)
            self.units = sorted(player_units, key=lambda unit: bool(unit.position), reverse=True)
            gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(self.units, 3, 4, 'center')
            if self.name == 'base_items' or self.name == 'base_armory_pick':
                gameStateObj.activeMenu.mode = 'items'
            # for display
            self.buttons = [GC.IMAGESDICT['Buttons'].subsurface(0, 165, 33, 9), GC.IMAGESDICT['Buttons'].subsurface(0, 66, 14, 13)]
            self.font = GC.FONT['text_white']
            self.commands = [cf.WORDS['Optimize'], cf.WORDS['Manage']]
            pos = (33 + self.font.size(self.commands[0])[0] + 16, self.font.size(self.commands[0])[1]*len(self.commands) + 8)
            self.quick_sort_disp = BaseMenuSurf.CreateBaseMenuSurf(pos, 'BrownBackgroundOpaque')
            self.quick_sort_disp = Image_Modification.flickerImageTranslucent(self.quick_sort_disp, 10)
            for idx, button in enumerate(self.buttons):
                self.quick_sort_disp.blit(button, (4 + 33//2 - button.get_width()//2, idx*self.font.height + 8 - button.get_height()//2 + 4))
            for idx, command in enumerate(self.commands):
                self.font.blit(command, self.quick_sort_disp, (38, idx*self.font.height + 4))

        if not gameStateObj.background:
            gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveUp(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveLeft(first_push)
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveRight(first_push)

        if event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            gameStateObj.cursor.currentSelectedUnit = selection
            if self.name == 'base_armory_pick':
                gameStateObj.hidden_active = gameStateObj.activeMenu
                # gameStateObj.activeMenu = None
                gameStateObj.stateMachine.changeState('market')
                gameStateObj.stateMachine.changeState('transition_out')
            else:
                gameStateObj.stateMachine.changeState('prep_items_choices')
                # gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)
        elif event == 'START':
            gameStateObj.quick_sort_inventories(gameStateObj.allunits)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu and gameStateObj.activeMenu.getSelection():
            MenuFunctions.drawUnitItems(surf, (6, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True, shimmer=2)
        # Draw quick sort display
        surf.blit(self.quick_sort_disp, (GC.WINWIDTH//2 + 10, GC.WINHEIGHT//2 + 9))
        draw_funds(surf, gameStateObj)

        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None

class PrepItemsChoicesState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            grayed_out = [True, False, True, False, False, False]
            if 'Convoy' in gameStateObj.game_constants:
                grayed_out = [True, False, True, True, True, False]
            if metaDataObj['marketFlag']:
                grayed_out[5] = True
            options = [cf.WORDS['Trade'], cf.WORDS['Use'], cf.WORDS['List'], cf.WORDS['Transfer'], cf.WORDS['Give All'], cf.WORDS['Market']]
            self.menu = MenuFunctions.GreyMenu(gameStateObj.cursor.currentSelectedUnit, options, (128, 80), grayed_out=grayed_out)
            self.background = None

        if hasattr(gameStateObj, 'hidden_item_child_option'):
            self.menu.setSelection(gameStateObj.hidden_item_child_option)

        self.set_background(gameStateObj)

        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.set_extra_marker(False)
        if any(self.can_use(item, gameStateObj) for item in gameStateObj.cursor.currentSelectedUnit.items):
            self.menu.update_grey(1, True)
        else:
            self.menu.update_grey(1, False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def set_background(self, gameStateObj):
        if self.background:
            gameStateObj.background = self.background
        elif not gameStateObj.background:
            gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])
        self.background = gameStateObj.background

    def can_use(self, item, gameStateObj):
        current_unit = gameStateObj.cursor.currentSelectedUnit
        if item.usable and item.booster:
            return current_unit.can_use_booster(item)
        return False

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
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveRight(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveLeft(first_push)

        if event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            if selection == cf.WORDS['Trade']:
                gameStateObj.stateMachine.changeState('prep_trade_select')
            elif selection == cf.WORDS['Use']:
                gameStateObj.stateMachine.changeState('prep_use_item')
            elif selection == cf.WORDS['Transfer']:
                gameStateObj.stateMachine.changeState('prep_transfer')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Give All']:
                for item in reversed(gameStateObj.cursor.currentSelectedUnit.items):
                    if not item.locked:
                        gameStateObj.cursor.currentSelectedUnit.remove_item(item, gameStateObj)
                        gameStateObj.convoy.append(item)
                # Can no longer use items
                self.menu.update_grey(1, False)
            elif selection == cf.WORDS['List']:
                gameStateObj.stateMachine.changeState('prep_list')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Market']:
                gameStateObj.stateMachine.changeState('base_market')
                gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(surf)
        if gameStateObj.activeMenu:
            MenuFunctions.drawUnitItems(surf, (6, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True, include_top=True, shimmer=2)
        draw_funds(surf, gameStateObj)
        return surf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.hidden_item_child_option = self.menu.getSelection()
        # self.menu = None

class PrepTradeSelectState(StateMachine.State):
    show_map = False

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
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveUp(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveLeft(first_push)
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveRight(first_push)

        if event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            gameStateObj.cursor.secondSelectedUnit = selection
            gameStateObj.stateMachine.changeState('prep_trade')
            gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.activeMenu.currentSelection = self.currentSelection
            gameStateObj.stateMachine.back()
        elif event == 'INFO':
            player_units = gameStateObj.get_units_in_party(gameStateObj.current_party)
            units = sorted(player_units, key=lambda unit: bool(unit.position), reverse=True)
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=units)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        MenuFunctions.drawUnitItems(mapSurf, (6, 8+16*4), self.selection, include_face=True, shimmer=2)
        MenuFunctions.drawUnitItems(mapSurf, (126, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True, right=False, shimmer=2)
        return mapSurf

class ConvoyTrader(object):
    def __init__(self, items, convoy):
        self.name = 'Convoy'
        self.items = items
        self.convoy = convoy

    def canWield(self, item):
        return True

    def canUse(self, item):
        return True

    def insert_item(self, index, item, gameStateObj=None):
        self.items.insert(index, item)
        item.item_owner = 0
        self.convoy.append(item)

    def remove_item(self, item, gameStateObj=None):
        self.items.remove(item)
        item.item_owner = 0
        if item != "EmptySlot":
            self.convoy.remove(item)

class PrepTradeState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.partner = gameStateObj.cursor.secondSelectedUnit
            self.initiator = gameStateObj.cursor.currentSelectedUnit
            if isinstance(self.partner, ItemMethods.ItemObject):
                self.partner = ConvoyTrader([self.partner], gameStateObj.convoy)
            self.menu = MenuFunctions.TradeMenu(self.initiator, self.partner, self.initiator.items, self.partner.items)
            # Hide active menu -- if it exists
            self.hidden_active = gameStateObj.activeMenu
            # self.hidden_child = gameStateObj.childMenu
            gameStateObj.activeMenu = None
            # gameStateObj.childMenu = None

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        self.menu.updateOptions(self.initiator.items, self.partner.items)
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            if self.menu.moveDown(first_push):
                GC.SOUNDDICT['Select 6'].play()
        elif 'UP' in directions:
            if self.menu.moveUp(first_push):
                GC.SOUNDDICT['Select 6'].play()
        elif event == 'RIGHT':
            if self.menu.moveRight():
                GC.SOUNDDICT['TradeRight'].play()
        elif event == 'LEFT':
            if self.menu.moveLeft():
                GC.SOUNDDICT['TradeRight'].play()

        elif event == 'BACK':
            if self.menu.is_selection_set():
                GC.SOUNDDICT['Select 4'].play()
                self.menu.unsetSelection()
            else:
                GC.SOUNDDICT['Select 4'].play()
                # gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')
                                              
        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            if self.menu.is_selection_set():
                self.menu.tradeItems(gameStateObj)
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
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        cur_unit = gameStateObj.cursor.currentSelectedUnit
        self.menu = MenuFunctions.ChoiceMenu(cur_unit, cur_unit.items, (6, 72), limit=5, hard_limit=True, gem=False, shimmer=2,
                                             color_control=['text_white' if item.booster else 'text_grey' for item in cur_unit.items],
                                             ignore=[False if item.booster else True for item in cur_unit.items])
        self.menu.draw_face = True
        self.info = False
        # Move cursor to starting point
        for index, item in enumerate(cur_unit.items):
            if item.booster:
                self.menu.moveTo(index)
                break

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

        if event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            gameStateObj.stateMachine.back()
            gameStateObj.cursor.currentSelectedUnit.handle_booster(selection, gameStateObj)
        elif event == 'BACK':
            if self.info:
                self.info = False
                GC.SOUNDDICT['Info Out'].play()
            else:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()
        elif event == 'INFO':
            self.info = not self.info
            if self.info:
                GC.SOUNDDICT['Info In'].play()
            else:
                GC.SOUNDDICT['Info Out'].play()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(mapSurf, gameStateObj)
        # Just to draw the top
        MenuFunctions.drawUnitItems(mapSurf, (6, 8+16*4), self.menu.owner, include_top=True, include_bottom=False)
        selection = self.menu.getSelection()
        if selection:
            self.draw_use_desc(mapSurf, selection.desc)
        if self.info:
            selection = None
            position = None
            selection = self.menu.getSelection()
            if selection:
                help_box = selection.get_help_box()
                height = 16*self.menu.currentSelection - help_box.get_height() + 64
                position = (16, height)
                help_box = selection.get_help_box()
                help_box.draw(mapSurf, position)
        return mapSurf

    def draw_use_desc(self, surf, desc):
        topleft = (110, 80)
        back_surf = BaseMenuSurf.CreateBaseMenuSurf((136, 64), 'SharpClearMenuBG')
        surf.blit(back_surf, topleft)

        font = GC.FONT['text_white']
        if desc:
            text = TextChunk.line_wrap(TextChunk.line_chunk(desc), GC.WINWIDTH - topleft[0] - 8, font)
            for idx, line in enumerate(text):
                font.blit(line, surf, (topleft[0] + 4, font.height * idx + 4 + topleft[1]))

    def end(self, gameStateObj, metaDataObj):
        self.menu = None

class PrepListState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # self.name_surf = BaseMenuSurf.CreateBaseMenuSurf((56, 24), 'TransMenuBackground60')
            self.name_surf = GC.IMAGESDICT['TradeName']
            self.owner_surf = BaseMenuSurf.CreateBaseMenuSurf((96, 24), 'TransMenuBackground60')
            self.info = False

            # Hide active Menu
            gameStateObj.childMenu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None

        all_items = self.calc_all_items(gameStateObj)
        if hasattr(self, 'menu'):
            self.menu.updateOptions(all_items)
        else:
            self.menu = MenuFunctions.ConvoyMenu(gameStateObj.cursor.currentSelectedUnit, all_items, (GC.WINWIDTH - 120 - 4, 40))

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def calc_all_items(self, gameStateObj):
        player_units = gameStateObj.get_units_in_party(gameStateObj.current_party) 
        all_items = [item for item in gameStateObj.convoy]
        for unit in player_units:
            for item in unit.items:
                all_items.append(item)
        return all_items

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
        elif 'RIGHT' in directions:
            # GC.SOUNDDICT['Select 6'].play()
            GC.SOUNDDICT['TradeRight'].play()
            self.menu.moveRight(first_push)
        elif 'LEFT' in directions:
            # GC.SOUNDDICT['Select 6'].play()
            GC.SOUNDDICT['TradeRight'].play()
            self.menu.moveLeft(first_push)

        if event == 'SELECT':
            selection = self.menu.getSelection()
            if selection and not self.info:
                if selection.item_owner:
                    GC.SOUNDDICT['Select 1'].play()
                    gameStateObj.stateMachine.changeState('prep_trade')
                    gameStateObj.stateMachine.changeState('transition_out')
                    gameStateObj.cursor.secondSelectedUnit = gameStateObj.get_unit_from_id(selection.item_owner)
                elif len(gameStateObj.cursor.currentSelectedUnit.items) < cf.CONSTANTS['max_items']:
                    GC.SOUNDDICT['Select 1'].play()
                    gameStateObj.cursor.currentSelectedUnit.add_item(selection, gameStateObj)
                    gameStateObj.convoy.remove(selection)
                else: # Unit has too many items -- Trade with convoy instead
                    GC.SOUNDDICT['Select 1'].play()
                    gameStateObj.stateMachine.changeState('prep_trade')
                    gameStateObj.stateMachine.changeState('transition_out')
                    gameStateObj.cursor.secondSelectedUnit = selection
            else: # Nothing selected
                pass
            # Re-update options
            self.menu.updateOptions(self.calc_all_items(gameStateObj))
        elif event == 'BACK':
            if self.info:
                self.info = False
                GC.SOUNDDICT['Info Out'].play()
            else:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            self.info = not self.info
            if self.info:
                GC.SOUNDDICT['Info In'].play()
            else:
                GC.SOUNDDICT['Info Out'].play()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(surf)
        # Draw name
        surf.blit(self.name_surf, (-2, -1))
        name_position = (24 - GC.FONT['text_white'].size(gameStateObj.cursor.currentSelectedUnit.name)[0]//2, 0)
        GC.FONT['text_white'].blit(gameStateObj.cursor.currentSelectedUnit.name, surf, name_position)
        # Draw face image
        face_image = gameStateObj.cursor.currentSelectedUnit.bigportrait.copy()
        face_image = Engine.flip_horiz(face_image)
        height = min(face_image.get_height(), 72)
        surf.blit(Engine.subsurface(face_image, (0, 0, face_image.get_width(), height)), (12, 0))
        # Draw owner
        surf.blit(self.owner_surf, (156, 0))
        item_owner = None
        if self.menu.getSelection():
            item_owner = gameStateObj.get_unit_from_id(self.menu.getSelection().item_owner)
        if item_owner:
            item_owner = item_owner.name
        else:
            item_owner = "---"
        owner_string = cf.WORDS["Owner"] + ": " + item_owner
        GC.FONT['text_white'].blit(owner_string, surf, (156+4, 4))
        # Draw units items
        MenuFunctions.drawUnitItems(surf, (4, 72), gameStateObj.cursor.currentSelectedUnit, include_top=False, shimmer=2)
        # Draw current info
        if self.info:
            selection = self.menu.getSelection()
            if selection:
                help_box = selection.get_help_box()
                height = 16*(self.menu.get_relative_index()+2) + 12 - help_box.get_height()
                if height < 0:
                    height = 16*(self.menu.get_relative_index()+4) - 4
                left = 64
                if help_box.get_width() > GC.WINWIDTH - 64 - 4:
                    left = GC.WINWIDTH - help_box.get_width() - 4
                help_box.draw(surf, (left, height))

        return surf

    def finish(self, gameStateObj, metaDataObj):
        # Unhide active menu
        gameStateObj.activeMenu = gameStateObj.childMenu
        gameStateObj.childMenu = None

class PrepTransferState(StateMachine.State):
    show_map = False
    options = [cf.WORDS["Give"], cf.WORDS["Take"], cf.WORDS["Merge"]]
    background = None

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            all_items = gameStateObj.convoy
            self.menu = MenuFunctions.ConvoyMenu(gameStateObj.cursor.currentSelectedUnit, all_items, (GC.WINWIDTH - 120 - 4, 40))
            self.menu.set_take_input(False)
            self.cur_unit = gameStateObj.cursor.currentSelectedUnit
            self.choice_menu = MenuFunctions.ChoiceMenu(self.cur_unit, self.options, (60, 8), gem=False, background='BrownBackgroundOpaque')
            self.choice_menu.ignore = [False, False, not any(self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items)]
            self.choice_menu.color_control = ['text_grey' if i else 'text_white' for i in self.choice_menu.ignore]
            self.owner_menu = MenuFunctions.ChoiceMenu(self.cur_unit, self.cur_unit.items, (6, 72), limit=5, hard_limit=True, width=104, gem=False, shimmer=2)
            self.owner_menu.takes_input = False
            self.owner_menu.draw_face = True
            self.state = "Free" # Can also be Give, Take, Merge1, Merge2
            self.info = False

            # Hide active menu
            gameStateObj.childMenu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def can_merge(self, item, convoy):
        if item.uses and item.uses.can_repair():
            for i in convoy:
                if i.id == item.id:
                    return True

    def merge_items(self, host, guest):
        diff_needed = host.uses.total_uses - host.uses.uses
        if diff_needed > 0:
            if guest.uses.uses >= diff_needed:
                guest.uses.uses -= diff_needed
                host.uses.uses += diff_needed
            else:
                host.uses.uses += guest.uses.uses
                guest.uses.uses = 0

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == 'Give':
                self.owner_menu.moveDown(first_push)
            elif self.state == 'Take':
                self.menu.moveDown(first_push)
            elif self.state == 'Merge1':
                self.owner_menu.moveDown(first_push)
                self.menu.goto_same_item_id(self.owner_menu.getSelection())
            elif self.state == 'Merge2':
                self.menu.moveDown(first_push)
            else:
                self.choice_menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == 'Give':
                self.owner_menu.moveUp(first_push)
            elif self.state == 'Take':
                self.menu.moveUp(first_push)
            elif self.state == 'Merge1':
                self.owner_menu.moveUp(first_push)
                self.menu.goto_same_item_id(self.owner_menu.getSelection())
            elif self.state == 'Merge2':
                self.menu.moveUp(first_push)
            else:
                self.choice_menu.moveUp(first_push)
        elif 'RIGHT' in directions:
            if self.state in ('Give', 'Take', 'Free'):
                GC.SOUNDDICT['TradeRight'].play()
                self.menu.moveRight(first_push)
            else:
                GC.SOUNDDICT['Error'].play()
        elif 'LEFT' in directions:
            if self.state in ('Give', 'Take', 'Free'):
                GC.SOUNDDICT['TradeRight'].play()
                self.menu.moveLeft(first_push)
            else:
                GC.SOUNDDICT['Error'].play()

        if event == 'SELECT':
            if self.state == 'Give':
                selection = self.owner_menu.getSelection()
                if selection and not selection.locked:
                    GC.SOUNDDICT['Select 1'].play()
                    self.cur_unit.remove_item(selection, gameStateObj)
                    gameStateObj.convoy.append(selection)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.menu.goto(selection)
                    # Goto the item in self.menu
                    self.owner_menu.updateOptions(self.cur_unit.items)
                    self.choice_menu.ignore = [False, False, not any(self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items)]
                    self.choice_menu.color_control = ['text_grey' if i else 'text_white' for i in self.choice_menu.ignore]
            elif self.state == 'Take':
                if len(self.cur_unit.items) < cf.CONSTANTS['max_items']:
                    GC.SOUNDDICT['Select 1'].play()
                    selection = self.menu.getSelection()
                    if selection:
                        gameStateObj.convoy.remove(selection)
                        self.cur_unit.add_item(selection, gameStateObj)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.owner_menu.updateOptions(self.cur_unit.items)
                    self.choice_menu.ignore = [False, False, not any(self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items)]
                    self.choice_menu.color_control = ['text_grey' if i else 'text_white' for i in self.choice_menu.ignore]
            elif self.state == 'Merge1':
                selection = self.owner_menu.getSelection()
                if selection:
                    GC.SOUNDDICT['Select 2'].play()
                    self.state = "Merge2"
                    self.menu.set_take_input(True)
            elif self.state == 'Merge2':
                my_item = self.owner_menu.getSelection()
                convoy_item = self.menu.getSelection()
                if my_item and convoy_item and my_item.id == convoy_item.id:
                    GC.SOUNDDICT['Select 1'].play()
                    self.merge_items(my_item, convoy_item)
                    if convoy_item.uses.uses <= 0:
                        gameStateObj.convoy.remove(convoy_item)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.owner_menu.ignore = [not self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items]
                    can_still_merge = not all(self.owner_menu.ignore)
                    self.owner_menu.color_control = ['text_grey' if i else 'text_white' for i in self.owner_menu.ignore]
                    self.owner_menu.updateOptions(self.cur_unit.items)
                    self.choice_menu.ignore = [False, False, not can_still_merge]
                    self.choice_menu.color_control = ['text_grey' if i else 'text_white' for i in self.choice_menu.ignore]
                    if can_still_merge:
                        self.state = "Merge1"
                        self.owner_menu.moveDown(True)
                        self.menu.goto_same_item_id(self.owner_menu.getSelection())
                    else:
                        self.state = "Free"
                        self.choice_menu.moveTo(0)
                        self.owner_menu.takes_input = False
                        self.owner_menu.ignore = None    
                        self.owner_menu.color_control = None
                    self.menu.set_take_input(False)
                else:
                    GC.SOUNDDICT['Error'].play()
            else:  # Free State
                GC.SOUNDDICT['Select 1'].play()
                selection_index = self.choice_menu.getSelectionIndex()
                if selection_index == 0:
                    self.state = "Give"
                elif selection_index == 1: 
                    self.state = "Take"
                elif selection_index == 2:
                    self.state = "Merge1"
                if self.state == "Give" or self.state == "Merge1":
                    self.owner_menu.takes_input = True
                    if self.state == "Merge1":
                        self.owner_menu.ignore = [not self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items]
                        self.owner_menu.color_control = ['text_grey' if i else 'text_white' for i in self.owner_menu.ignore]
                        self.owner_menu.updateOptions(self.cur_unit.items)
                        self.owner_menu.moveTo(self.owner_menu.color_control.index('text_white'))
                        self.menu.goto_same_item_id(self.owner_menu.getSelection())
                else:
                    self.menu.set_take_input(True)
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if self.state in ('Give', 'Take', 'Merge1'):
                if self.info:
                    self.info = False
                else:
                    self.state = "Free"
                    self.owner_menu.takes_input = False
                    self.menu.set_take_input(False)
                    self.owner_menu.ignore = None
                    self.owner_menu.color_control = None
            elif self.state == 'Merge2':
                self.state = "Merge1"
                self.menu.set_take_input(False)
            else:
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            if self.state != "Free":
                self.info = not self.info
                if self.info:
                    GC.SOUNDDICT['Info In'].play()
                else:
                    GC.SOUNDDICT['Info Out'].play()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        if self.state in ("Give", "Merge1"):
            self.owner_menu.update()
        elif self.state in ("Take", "Merge2"):
            self.menu.update()
        else:
            self.choice_menu.update()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if self.background:
            self.background.draw(mapSurf)
        self.choice_menu.draw(mapSurf)
        self.owner_menu.draw(mapSurf)
        self.menu.draw(mapSurf)
        # Draw supply portrait
        mapSurf.blit(GC.IMAGESDICT['SupplyPortrait'], (0, 0))
        # Draw current info
        if self.info:
            selection = None
            position = None
            if self.state in ("Give", "Merge1"):
                selection = self.owner_menu.getSelection()
                if selection:
                    help_box = selection.get_help_box()
                    height = 16*self.owner_menu.currentSelection - help_box.get_height() + 64
                    position = (16, height)
            elif self.state in ("Take", "Merge2"):
                selection = self.menu.getSelection()
                if selection:
                    help_box = selection.get_help_box()
                    height = 16*(self.menu.get_relative_index()+2) + 12 - help_box.get_height()
                    if height < 0:
                        height = 16*(self.menu.get_relative_index()+4) - 4
                    left = 64
                    if help_box.get_width() > GC.WINWIDTH - 64 - 4:
                        left = GC.WINWIDTH - help_box.get_width() - 4
                    position = (left, height)
            if selection:
                help_box = selection.get_help_box()
                help_box.draw(mapSurf, position)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        # Unhide active menu
        gameStateObj.activeMenu = gameStateObj.childMenu
        gameStateObj.childMenu = None

class ConvoyTransferState(PrepTransferState):
    options = [cf.WORDS["Give"], cf.WORDS["Take"]]
    background = None

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])
        super().begin(gameStateObj, metaDataObj)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == 'Give':
                self.owner_menu.moveDown(first_push)
            elif self.state == 'Take':
                self.menu.moveDown(first_push)
            else:
                self.choice_menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == 'Give':
                self.owner_menu.moveUp(first_push)
            elif self.state == 'Take':
                self.menu.moveUp(first_push)
            else:
                self.choice_menu.moveUp(first_push)
        elif 'RIGHT' in directions:
            if self.state in ('Give', 'Take', 'Free'):
                GC.SOUNDDICT['TradeRight'].play()
                self.menu.moveRight(first_push)
            else:
                GC.SOUNDDICT['Error'].play()
        elif 'LEFT' in directions:
            if self.state in ('Give', 'Take', 'Free'):
                GC.SOUNDDICT['TradeRight'].play()
                self.menu.moveLeft(first_push)
            else:
                GC.SOUNDDICT['Error'].play()

        if event == 'SELECT':
            if self.state == 'Give':
                selection = self.owner_menu.getSelection()
                if selection and not selection.locked:
                    GC.SOUNDDICT['Select 1'].play()
                    Action.do(Action.DiscardItem(self.cur_unit, selection), gameStateObj)
                    Action.do(Action.OwnerHasTraded(self.cur_unit), gameStateObj)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.menu.goto(selection)
                    # Goto the item in self.menu
                    self.owner_menu.updateOptions(self.cur_unit.items)
                    self.choice_menu.ignore = [False, False, not any(self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items)]
                    self.choice_menu.color_control = ['text_grey' if i else 'text_white' for i in self.choice_menu.ignore]
            elif self.state == 'Take':
                if len(self.cur_unit.items) < cf.CONSTANTS['max_items']:
                    GC.SOUNDDICT['Select 1'].play()
                    selection = self.menu.getSelection()
                    if selection:
                        Action.do(Action.TakeItem(self.cur_unit, selection), gameStateObj)
                        Action.do(Action.OwnerHasTraded(self.cur_unit), gameStateObj)
                    self.menu.updateOptions(gameStateObj.convoy)
                    self.owner_menu.updateOptions(self.cur_unit.items)
                    self.choice_menu.ignore = [False, False, not any(self.can_merge(item, gameStateObj.convoy) for item in self.cur_unit.items)]
                    self.choice_menu.color_control = ['text_grey' if i else 'text_white' for i in self.choice_menu.ignore]
            else:  # Free State
                GC.SOUNDDICT['Select 1'].play()
                selection_index = self.choice_menu.getSelectionIndex()
                if selection_index == 0:
                    self.state = "Give"
                elif selection_index == 1: 
                    self.state = "Take"
                if self.state == "Give":
                    self.owner_menu.takes_input = True
                else:
                    self.menu.set_take_input(True)
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if self.state in ('Give', 'Take'):
                if self.info:
                    self.info = False
                else:
                    self.state = "Free"
                    self.owner_menu.takes_input = False
                    self.menu.set_take_input(False)
                    self.owner_menu.ignore = None
                    self.owner_menu.color_control = None
            else:
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            if self.state != "Free":
                self.info = not self.info
                if self.info:
                    GC.SOUNDDICT['Info In'].play()
                else:
                    GC.SOUNDDICT['Info Out'].play()

class BaseMarketState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.cur_unit = gameStateObj.cursor.currentSelectedUnit
            self.buy_value_mod = 1.0
            if self.cur_unit:
                for status in self.cur_unit.status_effects:
                    if status.buy_value_mod:
                        self.buy_value_mod *= status.buy_value_mod
            self.update_options(gameStateObj)
            items_for_sale = [ItemMethods.itemparser(item) for item in gameStateObj.market_items]
            self.shop_menu = MenuFunctions.ConvoyMenu(None, items_for_sale, (GC.WINWIDTH - 160 - 4, 40), disp_value="Buy", buy_value_mod=self.buy_value_mod)
            self.choice_menu = MenuFunctions.ChoiceMenu(None, [cf.WORDS["Buy"], cf.WORDS["Sell"]], (16, 16), gem=False, background='BrownBackgroundOpaque')
            self.buy_sure_menu = MenuFunctions.ChoiceMenu(None, [cf.WORDS['Buy'], cf.WORDS['Cancel']], 'center', gameStateObj, horizontal=True, gem=False, background='BrownBackgroundOpaque')
            self.sell_sure_menu = MenuFunctions.ChoiceMenu(None, [cf.WORDS['Sell'], cf.WORDS['Cancel']], 'center', gameStateObj, horizontal=True, gem=False, background='BrownBackgroundOpaque')
            self.state = "Free" # Can also be Buy, Sell, Buy_Sure, Sell_Sure
            self.info = False
            self.current_menu = self.shop_menu

            # Create money surf
            self.money_surf = BaseMenuSurf.CreateBaseMenuSurf((56, 24))
            g_surf = Engine.subsurface(GC.IMAGESDICT['GoldenWords'], (40, 47, 11, 11))
            self.money_surf.blit(g_surf, (45, 8))
            self.money_counter_disp = MenuFunctions.BriefPopUpDisplay((66, GC.WINHEIGHT - 40))

            # Create owner surf
            self.owner_surf = BaseMenuSurf.CreateBaseMenuSurf((96, 24), 'TransMenuBackground60')

            if not gameStateObj.background:
                gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

            # Hide active menu
            gameStateObj.childMenu = gameStateObj.activeMenu
            gameStateObj.activeMenu = None

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def update_options(self, gameStateObj):
        my_units = gameStateObj.get_units_in_party(gameStateObj.current_party) 
        all_items = [item for item in gameStateObj.convoy]
        for unit in my_units:
            for item in unit.items:
                all_items.append(item)              
        if hasattr(self, 'my_menu'):
            self.my_menu.updateOptions(all_items)
        else:
            self.my_menu = MenuFunctions.ConvoyMenu(self.cur_unit, all_items, (GC.WINWIDTH - 160 - 4, 40), disp_value="Sell")

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == "Free":
                self.choice_menu.moveDown()
                selection = self.choice_menu.getSelection()
                if selection == cf.WORDS['Buy']:
                    self.current_menu = self.shop_menu
                else:
                    self.current_menu = self.my_menu
            elif self.state == 'Buy_Sure':
                self.buy_sure_menu.moveDown(first_push)
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveDown(first_push)
            else:
                self.current_menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == "Free":
                self.choice_menu.moveUp()
                selection = self.choice_menu.getSelection()
                if selection == cf.WORDS['Buy']:
                    self.current_menu = self.shop_menu
                else:
                    self.current_menu = self.my_menu
            elif self.state == 'Buy_Sure':
                self.buy_sure_menu.moveUp(first_push)
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveUp(first_push)
            else:
                self.current_menu.moveUp(first_push)
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == 'Buy_Sure':
                self.buy_sure_menu.moveDown(first_push)
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveDown(first_push)
            else:
                self.my_menu.moveRight(first_push)
                self.shop_menu.moveRight(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state == 'Buy_Sure':
                self.buy_sure_menu.moveUp(first_push)
            elif self.state == 'Sell_Sure':
                self.sell_sure_menu.moveUp(first_push)
            else:
                self.my_menu.moveLeft(first_push)
                self.shop_menu.moveLeft(first_push)

        if event == 'SELECT':
            if self.state == cf.WORDS['Buy']:
                selection = self.current_menu.getSelection()
                if selection:
                    value = (selection.value * selection.uses.uses) if selection.uses else selection.value
                    value = int(value * self.buy_value_mod)
                    if gameStateObj.get_money() - value >= 0:
                        self.state = 'Buy_Sure'
                        GC.SOUNDDICT['Select 1'].play()
                    else:
                        # You don't have enough money
                        GC.SOUNDDICT['Select 4'].play()
                else:
                    # You didn't choose anything to buy
                    GC.SOUNDDICT['Select 4'].play()
            elif self.state == 'Buy_Sure':
                selection = self.buy_sure_menu.getSelection()
                if selection == cf.WORDS['Buy']:
                    GC.SOUNDDICT['GoldExchange'].play()
                    item = ItemMethods.itemparser(str(self.current_menu.getSelection().id), gameStateObj) # Create a copy

                    if self.cur_unit and len(self.cur_unit.items) < cf.CONSTANTS['max_items']:
                        self.cur_unit.add_item(item, gameStateObj)
                    else:
                        gameStateObj.convoy.append(item)
                    value = (item.value * item.uses.uses) if item.uses else item.value
                    value = int(value * self.buy_value_mod)
                    gameStateObj.inc_money(-value)
                    self.money_counter_disp.start(-value)
                    self.update_options(gameStateObj)
                else:
                    GC.SOUNDDICT['Select 4'].play()
                self.state = cf.WORDS['Buy']
            elif self.state == cf.WORDS['Sell']:
                selection = self.current_menu.getSelection()
                if selection:
                    if selection.value:
                        GC.SOUNDDICT['Select 1'].play()
                        self.state = 'Sell_Sure'
                    else:
                        # No value, can't be sold
                        GC.SOUNDDICT['Select 4'].play()
                else:
                    # You didn't choose anything to sell
                    GC.SOUNDDICT['Select 4'].play()
            elif self.state == 'Sell_Sure':
                selection = self.sell_sure_menu.getSelection()
                if selection == cf.WORDS['Sell']:
                    GC.SOUNDDICT['GoldExchange'].play()
                    item = self.current_menu.getSelection()
                    value = (item.value * item.uses.uses)//2 if item.uses else item.value//2
                    gameStateObj.inc_money(value)
                    self.money_counter_disp.start(value)
                    if item.item_owner:
                        owner = gameStateObj.get_unit_from_id(item.item_owner)
                        owner.remove_item(item, gameStateObj)
                    else:
                        gameStateObj.convoy.remove(item)
                    self.update_options(gameStateObj)
                else:
                    GC.SOUNDDICT['Select 4'].play()
                self.state = cf.WORDS['Sell']
            else:
                GC.SOUNDDICT['Select 1'].play()
                selection = self.choice_menu.getSelection()
                self.state = selection
                if self.state == cf.WORDS['Buy']:
                    self.current_menu = self.shop_menu
                else:
                    self.current_menu = self.my_menu
                self.current_menu.set_take_input(True)
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if self.state == cf.WORDS['Buy'] or self.state == cf.WORDS['Sell']:
                if self.info:
                    self.info = False
                else:
                    self.state = "Free"
                    self.current_menu.set_take_input(False)
            elif self.state == 'Buy_Sure':
                self.state = cf.WORDS['Buy']
            elif self.state == 'Sell_Sure':
                self.state = cf.WORDS['Sell']
            else:
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            if self.state == cf.WORDS['Buy'] or self.state == cf.WORDS['Sell']:
                self.info = not self.info
                if self.info:
                    GC.SOUNDDICT['Info In'].play()
                else:
                    GC.SOUNDDICT['Info Out'].play()

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
        mapSurf.blit(self.money_surf, (10, GC.WINHEIGHT - 24))
        GC.FONT['text_blue'].blit(str(gameStateObj.get_money()), mapSurf, (16, GC.WINHEIGHT - 20))
        # Draw money counter display
        self.money_counter_disp.draw(mapSurf)

        # Draw owner
        mapSurf.blit(self.owner_surf, (156, 0))
        item_owner = None
        if self.current_menu.getSelection():
            item_owner = gameStateObj.get_unit_from_id(self.current_menu.getSelection().item_owner)
        if item_owner:
            item_owner = item_owner.name
        elif self.state == cf.WORDS["Sell"] or (self.state == "Free" and self.choice_menu.getSelection() == cf.WORDS['Sell']):
            item_owner = "Convoy"
        else:
            item_owner = "Market"
        owner_string = cf.WORDS["Owner"] + ": " + item_owner
        GC.FONT['text_white'].blit(owner_string, mapSurf, (156+4, 4))

        # Draw current info
        if self.info:
            selection = self.current_menu.getSelection()
            if selection:
                help_box = selection.get_help_box()
                height = 16*(self.current_menu.get_relative_index()+2) + 12 - help_box.get_height()
                if height < 0:
                    height = 16*(self.current_menu.get_relative_index()+4) - 4
                left = 64
                if help_box.get_width() > GC.WINWIDTH - 64 - 4:
                    left = GC.WINWIDTH - help_box.get_width() - 4
                help_box.draw(mapSurf, (left, height))

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
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        Engine.music_thread.fade_in(GC.MUSICDICT[metaDataObj['base_music']])
        self.done = False
        gameStateObj.cursor.drawState = 0
        background_image = GC.IMAGESDICT.get(metaDataObj['baseFlag'], GC.IMAGESDICT['MainBase'])
        gameStateObj.background = Background.StaticBackground(background_image, fade=False)

        if gameStateObj.main_menu:
            gameStateObj.activeMenu = gameStateObj.main_menu
            gameStateObj.main_menu = None
        elif not gameStateObj.activeMenu:
            options = [cf.WORDS['Items'], cf.WORDS['Market'], cf.WORDS['Convos'], cf.WORDS['Codex'], cf.WORDS['Save'], cf.WORDS['Continue']]
            color_control = ['text_white', 'text_grey', 'text_grey', 'text_white', 'text_white', 'text_white']
            # In base supports
            if cf.CONSTANTS['support'] == 2:
                options.insert(3, cf.WORDS['Supports'])
                color_control.insert(3, 'text_grey')
            # In base Arena
            if cf.CONSTANTS['arena_in_base']:
                options.insert(3, cf.WORDS['Arena'])
                color_control.insert(3, 'text_grey')
            if metaDataObj['marketFlag']:
                color_control[1] = 'text_white'
            if gameStateObj.base_conversations:
                color_control[2] = 'text_white'
            if cf.CONSTANTS['support'] == 2 and gameStateObj.support and \
                    'Supports' in gameStateObj.game_constants and gameStateObj.support.node_dict:
                idx = options.index(cf.WORDS['Supports'])
                color_control[idx] = 'text_white'
            if cf.CONSTANTS['arena_in_base'] and 'Arena' in gameStateObj.game_constants:
                idx = options.index(cf.WORDS['Arena'])
                color_control[idx] = 'text_white'
            topleft = 4, GC.WINHEIGHT//2 - (len(options)*16 + 8)//2
            gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(self, options, topleft, color_control=color_control, shimmer=2, gem=False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition() or not self.started:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

        # Play base script if it exists
        base_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/in_base_script.txt'
        if os.path.exists(base_script_name):
            base_script = Dialogue.Dialogue_Scene(base_script_name)
            gameStateObj.message.append(base_script)
            gameStateObj.stateMachine.changeState('transparent_dialogue')
            return 'repeat'

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
        
        if event == 'SELECT':
            selection = gameStateObj.activeMenu.getSelection()
            if gameStateObj.activeMenu.color_control[gameStateObj.activeMenu.currentSelection] == 'text_grey':
                pass
            elif selection == cf.WORDS['Items']:
                GC.SOUNDDICT['Select 1'].play()
                gameStateObj.main_menu = gameStateObj.activeMenu
                # gameStateObj.activeMenu = None
                gameStateObj.stateMachine.changeState('base_items')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Market']:
                GC.SOUNDDICT['Select 1'].play()
                gameStateObj.cursor.currentSelectedUnit = None
                gameStateObj.stateMachine.changeState('base_market')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Convos']:
                GC.SOUNDDICT['Select 1'].play()
                gameStateObj.stateMachine.changeState('base_info')
            elif selection == cf.WORDS['Arena']:
                GC.SOUNDDICT['Select 1'].play()
                gameStateObj.stateMachine.changeState('base_arena_choice')
            elif selection == cf.WORDS['Supports']:
                GC.SOUNDDICT['Select 1'].play()
                # gameStateObj.stateMachine.changeState('base_support_child')
                gameStateObj.stateMachine.changeState('base_support_convos')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Codex']:
                GC.SOUNDDICT['Select 1'].play()
                gameStateObj.stateMachine.changeState('base_codex_child')
            elif selection == cf.WORDS['Save']:
                GC.SOUNDDICT['Select 1'].play()
                # SaveLoad.suspendGame(gameStateObj, 'Base')
                gameStateObj.save_kind = 'Base'
                gameStateObj.stateMachine.changeState('start_save')
                gameStateObj.stateMachine.changeState('transition_out')
                # gameStateObj.banners.append(Banner.gameSavedBanner())
                # gameStateObj.stateMachine.changeState('itemgain')
            elif selection == cf.WORDS['Continue']:
                GC.SOUNDDICT['Select 1'].play()
                self.done = True
                # gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.changeState('transition_pop')

    def finish(self, gameStateObj, metaDataObj):
        # if self.done:
        gameStateObj.background = None
        gameStateObj.activeMenu = None

class BaseInfoState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        options = [key for key in gameStateObj.base_conversations]
        color_control = [('text_white' if white else 'text_grey') for key, white in gameStateObj.base_conversations.items()]
        topleft = 4 + gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.topleft[1] + 2*16
        gameStateObj.childMenu = MenuFunctions.ChoiceMenu(self, options, topleft, color_control=color_control, gem=False, limit=5)

        # Transition in:
        if gameStateObj.stateMachine.from_transition() or gameStateObj.stateMachine.get_last_state() == 'dialogue':
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp()
        elif event == 'SELECT':
            selection = gameStateObj.childMenu.getSelection()
            if gameStateObj.childMenu.color_control[gameStateObj.childMenu.currentSelection] == 'text_white':
                GC.SOUNDDICT['Select 1'].play()
                dialogue_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/baseScript.txt'
                gameStateObj.message.append(Dialogue.Dialogue_Scene(dialogue_script, name=selection))
                gameStateObj.stateMachine.changeState('dialogue')
                gameStateObj.stateMachine.changeState('transition_out')
            return
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.back()

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.childMenu = None

class BaseArenaState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        self.units = gameStateObj.get_units_in_party(gameStateObj.current_party)
        gameStateObj.activeMenu = MenuFunctions.UnitSelectMenu(self.units, 2, 9, (110, 4))
        gameStateObj.activeMenu.mode = 'arena'
        self.portrait = GC.IMAGESDICT.get('ArenaPortrait')

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveUp(first_push)
        elif 'LEFT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveLeft(first_push)
        elif 'RIGHT' in directions:
            GC.SOUNDDICT['Select 5'].play()
            gameStateObj.activeMenu.moveRight(first_push)

        if event == 'SELECT':
            selection = gameStateObj.activeMenu.getSelection()
            if selection.currenthp > 1:
                GC.SOUNDDICT['Select 1'].play()
                gameStateObj.cursor.currentSelectedUnit = selection
                gameStateObj.stateMachine.changeState('arena_base')
                gameStateObj.stateMachine.changeState('transition_out')
            else:
                GC.SOUNDDICT['Error'].play()
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.stateMachine.clear()
            # gameStateObj.stateMachine.changeState('base_main')
            gameStateObj.stateMachine.back()
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        if gameStateObj.activeMenu and gameStateObj.activeMenu.getSelection():
            MenuFunctions.drawUnitItems(surf, (6, 8+16*4), gameStateObj.activeMenu.getSelection(), include_face=True, shimmer=2)
        if self.portrait:
            surf.blit(self.portrait, (3, 0))
        if gameStateObj.activeMenu and gameStateObj.activeMenu.getSelection():
            unit = gameStateObj.activeMenu.getSelection()
            hp_surf = BaseMenuSurf.CreateBaseMenuSurf((56, 24), 'BaseMenuBackgroundOpaque')
            hp_surf = Image_Modification.flickerImageTranslucent(hp_surf, 10)
            current_hp = str(unit.currenthp)
            max_hp = str(unit.stats['HP'])
            text = "HP: %s/%s" % (current_hp, max_hp)
            GC.FONT['text_white'].blit(text, hp_surf, (56//2 - GC.FONT['text_white'].size(text)[0]//2, 4))
            surf.blit(hp_surf, (54, 48))

        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None

class BaseSupportConvoState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        self.units = [unit for unit in gameStateObj.get_units_in_party(gameStateObj.current_party)
                      if not unit.generic_flag and unit.id in gameStateObj.support.node_dict]

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
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state:
                gameStateObj.childMenu.moveDown(first_push)
            else:
                gameStateObj.activeMenu.moveDown(first_push)
                gameStateObj.childMenu.owner = gameStateObj.activeMenu.getSelection()
                gameStateObj.childMenu.updateOptions(gameStateObj)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            if self.state:
                gameStateObj.childMenu.moveUp(first_push)
            else:
                gameStateObj.activeMenu.moveUp(first_push)
                gameStateObj.childMenu.owner = gameStateObj.activeMenu.getSelection()
                gameStateObj.childMenu.updateOptions(gameStateObj)
        elif 'LEFT' in directions:
            if self.state:
                GC.SOUNDDICT['TradeRight'].play()
                self.state = gameStateObj.childMenu.moveLeft(first_push)
                gameStateObj.childMenu.cursor_flag = self.state
        elif 'RIGHT' in directions:
            if self.state:
                GC.SOUNDDICT['TradeRight'].play()
                gameStateObj.childMenu.moveRight(first_push)
            # Has supports
            elif gameStateObj.support.node_dict[gameStateObj.childMenu.owner.id].adjacent:
                GC.SOUNDDICT['TradeRight'].play()
                self.state = True
                gameStateObj.childMenu.cursor_flag = True
            else:
                GC.SOUNDDICT['Error'].play()

        if event == 'SELECT':
            # Play conversation
            if self.state:
                GC.SOUNDDICT['Select 1'].play()
                unit, level = gameStateObj.childMenu.getSelection()
                if unit:
                    owner = gameStateObj.childMenu.owner
                    edge = gameStateObj.support.node_dict[owner.id].adjacent[unit.id]
                    # print(level, edge.available_level())
                    # if level < edge.available_level():
                    if gameStateObj.support.can_support(unit.id, owner.id):
                        if os.path.exists(edge.script):
                            support_script = edge.script
                        else:
                            support_script = 'Data/SupportConvos/GenericScript.txt'
                        gameStateObj.message.append(Dialogue.Dialogue_Scene(support_script, unit=unit, unit2=owner, name=level))
                        gameStateObj.stateMachine.changeState('dialogue')
                        gameStateObj.stateMachine.changeState('transition_out')
                    else:
                        GC.SOUNDDICT['Error'].play()
                else:
                    GC.SOUNDDICT['Error'].play()
            elif gameStateObj.support.node_dict[gameStateObj.childMenu.owner.id].adjacent:
                GC.SOUNDDICT['Select 1'].play()
                self.state = True
                gameStateObj.childMenu.cursor_flag = True
            else:
                GC.SOUNDDICT['Error'].play()

        elif event == 'BACK':
            if self.state:
                GC.SOUNDDICT['TradeRight'].play()
                self.state = False
                gameStateObj.childMenu.cursor_flag = self.state
            else:
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.activeMenu = None
                gameStateObj.childMenu = None
                gameStateObj.stateMachine.changeState('transition_pop')
        elif event == 'INFO':
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, gameStateObj.activeMenu.getSelection(), scroll_units=self.units)

class BaseCodexChildState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not gameStateObj.childMenu:
            options = [cf.WORDS['Library']]
            if 'WorldMap' in gameStateObj.game_constants:
                options.append(cf.WORDS['Map'])
            if gameStateObj.statistics:
                options.append(cf.WORDS['Records'])
            topleft = 4 + gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.topleft[1] + (4*16 if gameStateObj.support else 3*16)
            gameStateObj.childMenu = MenuFunctions.ChoiceMenu(self, options, topleft, gem=False)

        # Transition in:
        if gameStateObj.stateMachine.from_transition():
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp(first_push)

        if event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = gameStateObj.childMenu.getSelection()
            if selection == cf.WORDS['Library'] and gameStateObj.unlocked_lore:
                gameStateObj.stateMachine.changeState('base_library')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Map']:
                gameStateObj.stateMachine.changeState('base_map')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Records']:
                gameStateObj.stateMachine.changeState('base_records')
                gameStateObj.stateMachine.changeState('transition_out')
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.childMenu = None
            gameStateObj.stateMachine.back()

class BaseMapState(StateMachine.State):
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        self.hidden_active = gameStateObj.activeMenu
        gameStateObj.activeMenu = None

        gameStateObj.old_background = gameStateObj.background
        gameStateObj.background = WorldMap.WorldMapBackground(GC.IMAGESDICT['WorldMap'])

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
            GC.SOUNDDICT['Select 4'].play()
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
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.hidden_active = gameStateObj.activeMenu
            self.hidden_child = gameStateObj.childMenu
            gameStateObj.activeMenu = None
            gameStateObj.childMenu = None

            options, ignore, color_control = [], [], []
            unlocked_entries = [(entry, data) for entry, data in GC.LOREDICT.items() if entry in gameStateObj.unlocked_lore]
            categories = sorted(list(set([data['type'] for entry, data in unlocked_entries])))
            for category in categories:
                options.append(category)
                ignore.append(True)
                color_control.append('text_yellow')
                for name in sorted([name for name, data in unlocked_entries if data['type'] == category]):
                    options.append(name)
                    ignore.append(False)
                    color_control.append('text_white')

            gameStateObj.activeMenu = MenuFunctions.ChoiceMenu(self, options, (4, 4), limit=9, hard_limit=True, ignore=ignore, color_control=color_control)
            gameStateObj.activeMenu.moveDown()
            self.menu = MenuFunctions.Lore_Display(GC.LOREDICT[gameStateObj.activeMenu.getSelection()])

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
            self.menu.update_entry(GC.LOREDICT[gameStateObj.activeMenu.getSelection()])
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)
            self.menu.update_entry(GC.LOREDICT[gameStateObj.activeMenu.getSelection()])

        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.changeState('transition_pop')

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        self.menu.draw(mapSurf)
        return mapSurf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = self.hidden_active
        gameStateObj.childMenu = self.hidden_child

class BaseRecordsState(StateMachine.State):
    show_map = False
    
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
                for unit, record in level.stats.items():
                    if unit not in self.name_dict:
                        self.name_dict[unit] = []
                    self.name_dict[unit].append((level.name, record))
            self.name_list = [(k, v) for (k, v) in self.name_dict.items()]
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
                self.current_offset_y = GC.WINHEIGHT

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.current_menu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            self.current_menu.moveUp(first_push)

        if event == 'LEFT':
            self.prev_menu = self.current_menu
            self.current_offset_x = -GC.WINWIDTH
            self.prev_offset_x = 1
            GC.SOUNDDICT['Status_Page_Change'].play()
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
            self.current_offset_x = GC.WINWIDTH
            self.prev_offset_x = -1
            GC.SOUNDDICT['Status_Page_Change'].play()
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
            GC.SOUNDDICT['Select 1'].play()
            if self.state in {'records', 'mvp'}:
                self.prev_menu = self.current_menu
                self.current_offset_y = GC.WINHEIGHT
                self.prev_offset_y = -1
            if self.state == 'records':
                self.state = "chapter"
                self.current_menu = self.chapter_stats[self.current_menu.currentSelection]
            elif self.state == 'mvp':
                self.state = "unit"
                self.current_menu = self.unit_stats[self.current_menu.currentSelection]
        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if self.state == 'records' or self.state == 'mvp':
                gameStateObj.stateMachine.changeState('transition_pop')
            else:
                self.prev_menu = self.current_menu
                self.current_offset_y = -GC.WINHEIGHT
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
            if self.prev_offset_x > GC.WINWIDTH or self.prev_offset_x < -GC.WINWIDTH:
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
            if self.prev_offset_y > GC.WINHEIGHT or self.prev_offset_y < -GC.WINHEIGHT:
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
