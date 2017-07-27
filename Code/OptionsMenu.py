import imagesDict
from GlobalConstants import *
from configuration import *
import CustomObjects, MenuFunctions, Image_Modification, InputManager, Engine, StateMachine, Counters

class OptionsMenu(StateMachine.State, Counters.CursorControl):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.config = [('Animation', ['OFF'], WORDS['Animation_desc'], 0),
                           ('Unit Speed', range(15, 180, 15), WORDS['Unit Speed_desc'], 1),
                           ('Text Speed', range(0, 110, 10), WORDS['Text Speed_desc'], 2),
                           ('Cursor Speed', range(0, 220, 20), WORDS['Cursor Speed_desc'], 8),
                           ('Show Terrain', ['ON', 'OFF'], WORDS['Show Terrain_desc'], 7),
                           ('Show Objective', ['ON', 'OFF'], WORDS['Show Objective_desc'], 6),
                           ('Autocursor', ['ON', 'OFF'], WORDS['Autocursor_desc'], 13),
                           ('HP Map Team', ['All', 'Ally', 'Enemy'], WORDS['HP Map Team_desc'], 10),
                           ('HP Map Cull', ['None', 'Wounded', 'All'], WORDS['HP Map Cull_desc'], 10),
                           ('Music Volume', [x/10.0 for x in range(0, 11, 1)], WORDS['Music Volume_desc'], 15),
                           ('Sound Volume', [x/10.0 for x in range(0, 11, 1)], WORDS['Sound Volume_desc'], 16),
                           ('Autoend Turn', ['ON', 'OFF'], WORDS['Autoend Turn_desc'], 14),
                           ('Confirm End', ['ON', 'OFF'], WORDS['Confirm End_desc'], 14),
                           ('Display Hints', ['ON', 'OFF'], WORDS['Display Hints_desc'], 3)]

            self.controls = {'key_SELECT': Engine.subsurface(IMAGESDICT['Buttons'], (0, 66, 14, 13)),
                             'key_BACK': Engine.subsurface(IMAGESDICT['Buttons'], (0, 82, 14, 13)),
                             'key_INFO': Engine.subsurface(IMAGESDICT['Buttons'], (1, 149, 16, 9)),
                             'key_AUX': Engine.subsurface(IMAGESDICT['Buttons'], (1, 133, 16, 9)),
                             'key_START': Engine.subsurface(IMAGESDICT['Buttons'], (0, 165, 33, 9)),
                             'key_LEFT': Engine.subsurface(IMAGESDICT['Buttons'], (1, 4, 13, 12)),
                             'key_RIGHT': Engine.subsurface(IMAGESDICT['Buttons'], (1, 19, 13, 12)),
                             'key_DOWN': Engine.subsurface(IMAGESDICT['Buttons'], (1, 34, 12, 13)),
                             'key_UP': Engine.subsurface(IMAGESDICT['Buttons'], (1, 50, 12, 13))}

            self.currentSelection = 0
            self.start_offset = 32
            self.top_of_menu = 0

            self.control_order = ['key_SELECT', 'key_BACK', 'key_INFO', 'key_AUX', 'key_LEFT', 'key_RIGHT', 'key_UP', 'key_DOWN', 'key_START']

            self.background = MenuFunctions.MovingBackground(IMAGESDICT['StatusBackground'])

            self.state = CustomObjects.StateMachine('TopMenu')

            self.fluid_helper = InputManager.FluidScroll(100)

            Counters.CursorControl.__init__(self)
            self.up_arrows = IMAGESDICT['ScrollArrows']
            self.down_arrows = Engine.flip_vert(IMAGESDICT['ScrollArrows'])
            self.arrowCounter = 0
            self.arrowMax = 5
            self.lastArrowUpdate = 0

            self.backSurf = gameStateObj.generic_surf

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def back(self, gameStateObj):
        SOUNDDICT['Select 4'].play()
        write_config_file()
        CONSTANTS['Unit Speed'] = OPTIONS['Unit Speed']
        if not OPTIONS['Display Hints']:
            gameStateObj.tutorial_mode_off()
        gameStateObj.stateMachine.changeState('transition_pop')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList, all_keys=True)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if self.state.getState() == "TopMenu":

            if event == 'LEFT':
                SOUNDDICT['Select 6'].play()
                self.currentSelection = 0

            elif event == 'RIGHT':
                SOUNDDICT['Select 6'].play()
                self.currentSelection = 1

            elif event == 'DOWN':
                SOUNDDICT['Select 1'].play()
                if self.currentSelection == 0:
                    self.state.changeState('Config')
                else:
                    self.currentSelection = 0
                    self.state.changeState('Controls')

            elif event == 'SELECT':
                SOUNDDICT['Select 1'].play()
                if self.currentSelection == 0:
                    self.state.changeState('Config')
                else:
                    self.currentSelection = 0
                    self.state.changeState('Controls')

            elif event == 'BACK':
                self.back(gameStateObj)
                return

        elif self.state.getState() == "Config":

            if 'DOWN' in directions:
                SOUNDDICT['Select 6'].play()
                self.currentSelection += 1
                if self.currentSelection >= len(self.config):
                    self.currentSelection = len(self.config) - 1

            elif 'UP' in directions:
                SOUNDDICT['Select 6'].play()
                self.currentSelection -= 1
                if self.currentSelection < 0:
                    self.currentSelection = 0
                    self.state.changeState('TopMenu') # Back to top menu

            elif event == 'BACK':
                self.back(gameStateObj)
                return

            elif event == 'RIGHT':
                SOUNDDICT['Select 6'].play()
                current_section = self.config[self.currentSelection] # Gives me what section we are on
                current_choice = OPTIONS[current_section[0]] # Gives me what the current option that is selected is
                current_index = self.get_index(current_section[1], current_choice)
                current_index += 1 # Move that option 1 to the right
                if current_index >= len(current_section[1]): # Make sure we have not gone too far over
                    current_index = len(current_section[1]) - 1
                OPTIONS[current_section[0]] = current_section[1][current_index] # Set the new option[index] as new option constant
                self.convert_options(current_section[0])

            elif event == 'LEFT':
                SOUNDDICT['Select 6'].play()
                current_section = self.config[self.currentSelection]
                current_choice = OPTIONS[current_section[0]]
                current_index = self.get_index(current_section[1], current_choice)
                current_index -= 1
                if current_index < 0:
                    current_index = 0
                OPTIONS[current_section[0]] = current_section[1][current_index]
                self.convert_options(current_section[0])

        elif self.state.getState() == "Controls":
            if 'DOWN' in directions:
                SOUNDDICT['Select 6'].play()
                self.currentSelection += 1
                if self.currentSelection >= len(self.control_order):
                    self.currentSelection = len(self.control_order) - 1

            elif 'UP' in directions:
                SOUNDDICT['Select 6'].play()
                self.currentSelection -= 1
                if self.currentSelection < 0:
                    self.currentSelection = 1
                    self.state.changeState('TopMenu') # Back to top menu

            elif event == 'BACK':
                self.back(gameStateObj)
                return

            elif event == 'SELECT':
                SOUNDDICT['Select 1'].play()
                self.state.changeState("Get_Input")

        elif self.state.getState() == "Get_Input":
            if event == 'BACK':
                SOUNDDICT['Select 4'].play()
                self.state.changeState("Controls")

            elif event == 'NEW':
                SOUNDDICT['Select 1'].play()
                self.state.back()
                OPTIONS[self.control_order[self.currentSelection]] = gameStateObj.input_manager.unavailable_button
                gameStateObj.input_manager.update_key_map()
                return

            elif event:
                SOUNDDICT['Select 4'].play()
                # Not a legal option
                self.state.back()
                self.state.changeState("Invalid")

        elif self.state.getState() == "Invalid":
            if event:
                SOUNDDICT['Select 6'].play()
                self.state.back()

    def convert_options(self, section):
        if OPTIONS[section] == 'ON':
            OPTIONS[section] = 1
        elif OPTIONS[section] == 'OFF':
            OPTIONS[section] = 0 

    def update(self, gameStateObj, metaDataObj):
        # Determine if we need to move the top of the menu
        if self.currentSelection <= self.top_of_menu:
            self.top_of_menu = self.currentSelection - 1
        elif self.currentSelection > self.top_of_menu + 4:
            self.top_of_menu = self.currentSelection - 4
        if self.top_of_menu < 0:
            self.top_of_menu = 0
        if self.state.getState() == "Config":
            if self.top_of_menu > len(self.config) - 6:
                self.top_of_menu = len(self.config) - 6
        elif self.state.getState() == "Controls":
            if self.top_of_menu > len(self.control_order) - 6:
                self.top_of_menu = len(self.control_order) - 6

        # Handle Cursor
        Counters.CursorControl.update(self)
        currentTime = Engine.get_time()
        if currentTime - self.lastArrowUpdate > 50:
            self.lastArrowUpdate = currentTime
            self.arrowCounter += 1
            if self.arrowCounter > self.arrowMax:
                self.arrowCounter = 0

        # Update music volume...
        Engine.music_thread.set_volume(OPTIONS['Music Volume'])
        imagesDict.set_sound_volume(OPTIONS['Sound Volume'], SOUNDDICT)

    def draw(self, gameStateObj, metaDataObj):
        surf = self.backSurf
        self.background.draw(surf)
        self.drawSlide(surf)

        if self.state.getState() == "Config" or (self.state.getState() == "TopMenu" and self.currentSelection == 0):
            self.drawConfig(surf)
            if self.state.getState() == "Config":
                self.drawConfigCursor(surf)
        elif self.state.getState() == "Controls" or self.state.getState() == "Get_Input" or self.state.getState() == "Invalid" or (self.state.getState() == "TopMenu" and self.currentSelection == 1):
            self.drawControls(surf)
            if self.state.getState() == "Controls":
                self.drawControlsCursor(surf)
        if self.state.getState() == "TopMenu":
            self.drawTopMenuCursor(surf)
        self.drawInfo(surf)

        if self.state.getState() == "Invalid":
            self.drawInvalid(surf)

        return surf

    def drawInvalid(self, surf):
        size_of_text = FONT['text_white'].size("Invalid Choice!")
        width = size_of_text[0]
        height = size_of_text[1]
        pop_up_surf = MenuFunctions.CreateBaseMenuSurf((width + 16 - width%8, height + 16 - height%8))
        surf.blit(Image_Modification.flickerImageTranslucent(IMAGESDICT['BlackBackground'].copy(), 60), (0, 0))
        topleft = (WINWIDTH/2 - pop_up_surf.get_width()/2, WINHEIGHT/2 - pop_up_surf.get_height()/2)
        surf.blit(pop_up_surf, topleft)
        position = (WINWIDTH/2 - width/2, WINHEIGHT/2 - height/2)
        FONT['text_white'].blit(WORDS["Invalid Choice"], surf, position)

    def drawControls(self, surf):
        for index, control in enumerate(self.control_order[self.top_of_menu:self.top_of_menu + 6]):
            name_font = FONT['text_white']
            key_font = FONT['text_blue']
            if self.state.getState() == "Get_Input" and index == self.currentSelection - self.top_of_menu:
                name_font = FONT['text_yellow']
                key_font = FONT['text_yellow']

            icon_surf = self.controls[control]
            topleft = (18 - icon_surf.get_width()/2, 2 + self.start_offset + index*16 + 8 - icon_surf.get_height()/2)
            surf.blit(icon_surf, topleft)

            name_position = (44, self.start_offset + index*16 + 2)
            name_font.blit(WORDS[control], surf, name_position)

            key_position = (WINWIDTH/2 + 8, self.start_offset + index*16 + 2)
            key_font.blit(Engine.get_key_name(OPTIONS[control]), surf, key_position)

        self.drawScrollArrows(surf, self.control_order)            

    def drawConfig(self, surf):
        # Blit arrow... eventually
        # Blit text
        slider_offset = [0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 2, 2, 2, 1, 1]
        for index, option in enumerate(self.config[self.top_of_menu:self.top_of_menu + 6]):
            name, bounds, info, icon = option
            # Blit Icon
            icon_position = (15, self.start_offset + index*16)
            icon_surf = Engine.subsurface(ICONDICT['Options_Icons'], (0, icon*16, 16, 16))
            surf.blit(icon_surf, icon_position)
            # Blit name
            name_position = (32, self.start_offset + 1 + index*16)
            FONT['text_white'].blit(WORDS[name], surf, name_position)
            current_option = OPTIONS[name]
            # Blit Options
            # Is a slider
            if isinstance(bounds[0], int) or isinstance(bounds[0], float):
                slider_bar = IMAGESDICT['HealthBarBG']
                surf.blit(slider_bar, (WINWIDTH/2 + 12, self.start_offset + index*16 + 4))

                slider_hold = IMAGESDICT['WaitingCursor']
                slider_fraction = (current_option - bounds[0])/float((bounds[-1] - bounds[0]))
                hold_offset = slider_fraction*(slider_bar.get_width() - 6)
                slider_bop = slider_offset[self.cursorCounter] - 1 if index + self.top_of_menu == self.currentSelection else 0
                topleft = (WINWIDTH/2 + 12 + hold_offset, self.start_offset + index*16 + 4 + slider_bop)
                surf.blit(slider_hold, topleft)
            # Is a list of options
            else:
                word_index = 0
                for choice in bounds:
                    if choice == current_option or (choice == 'ON' and current_option) or (choice == 'OFF' and not current_option):
                        font = FONT['text_blue']
                    else:
                        font = FONT['text_grey']
                    option_position = (WINWIDTH/2 + 8 + word_index, self.start_offset + index*16)
                    font.blit(WORDS[choice], surf, option_position)
                    word_index += font.size(WORDS[choice] + '    ')[0]

        self.drawScrollArrows(surf, self.config)

    def drawScrollArrows(self, surf, menu):
        if self.top_of_menu > 0:
            position = WINWIDTH/2 - 8, self.start_offset - 4
            surf.blit(Engine.subsurface(self.up_arrows, (0,self.arrowCounter*8,16,8)), position)
        if self.top_of_menu + 6 < len(menu):
            position = WINWIDTH/2 - 8, self.start_offset + 6*16 - 1
            surf.blit(Engine.subsurface(self.down_arrows, (0,self.arrowCounter*8,16,8)), position)

    def get_index(self, choices, option):
        if len(choices) == 1:
            return 0
        elif 'ON' in choices and 'OFF' in choices:
            if option:
                return choices.index('ON')
            else:  
                return choices.index('OFF')
        else:
            return choices.index(option)

    def drawConfigCursor(self, surf):
         # Blit cursor (s)
        # Blit moving cursor
        bounds = self.config[self.currentSelection][1]
        if not isinstance(bounds[0], int) and not isinstance(bounds[0], float):
            bound_index = self.get_index(bounds, OPTIONS[self.config[self.currentSelection][0]])
            left_position = FONT['text_white'].size('    '.join(bounds[:bound_index]) + ('    ' if bound_index > 0 else ''))[0] + WINWIDTH/2 - 8
            top_position = 32 + (self.currentSelection - self.top_of_menu)*16
            surf.blit(self.cursor, (left_position + self.cursorAnim[self.cursorCounter], top_position))
        # Blit still cursor
        still_cursor_position = (15 - self.cursor.get_width(), 32 + (self.currentSelection - self.top_of_menu)*16)
        surf.blit(self.cursor, still_cursor_position)

    def drawControlsCursor(self, surf):
        # Blit cursor
        cursor_position = (32 - self.cursor.get_width() + self.cursorAnim[self.cursorCounter] - 4, 32 + (self.currentSelection - self.top_of_menu)*16)
        surf.blit(self.cursor, cursor_position)

    def drawTopMenuCursor(self, surf):
        # Blit Moving Cursor
        if self.currentSelection == 0: # Config
            left_position = 4 + (WINWIDTH/2 - 8)/2 - FONT['text_white'].size('Config')[0]/2 + self.cursorAnim[self.cursorCounter] - 16
            top_position = 16 - FONT['text_white'].size('Config')[1]/2
        else: # Controls
            left_position = WINWIDTH/2 + 4 + (WINWIDTH/2 - 8)/2 - FONT['text_white'].size('Controls')[0]/2 + self.cursorAnim[self.cursorCounter] - 16
            top_position = 16 - FONT['text_white'].size('Controls')[1]/2
        moving_cursor_position = (left_position, top_position)
        surf.blit(self.cursor, moving_cursor_position)

    def drawInfo(self, surf):
        mainInfoSurf = MenuFunctions.CreateBaseMenuSurf((WINWIDTH - 32, 24), 'BaseMenuBackground')
        surf.blit(mainInfoSurf, (16, WINHEIGHT - 24))

        if self.state.getState() == "Config":
            info_text = self.config[self.currentSelection][2]
        elif self.state.getState() == "Controls":
            info_text = WORDS['Controls_desc']
        elif self.state.getState() == "Get_Input":
            info_text = WORDS['Get_Input_desc']
        elif self.state.getState() == "TopMenu":
            if self.currentSelection == 0:
                info_text = WORDS['Config_desc']
            else:
                info_text = WORDS['Controls_desc']
        else:
            return
        FONT['text_white'].blit(info_text, surf, (32, WINHEIGHT - 20))

    def drawSlide(self, surf):
        mainSlideSurf = MenuFunctions.CreateBaseMenuSurf((WINWIDTH + 8, 6*WINHEIGHT/10 + 8), 'ClearMenuBackground')
        surf.blit(mainSlideSurf, (0 - 4, WINHEIGHT/5))

        if self.state.getState() == 'Config' or (self.state.getState() == 'TopMenu' and self.currentSelection == 0):
            config_font = FONT['text_blue']
            controls_font = FONT['text_grey']
        else:
            config_font = FONT['text_grey']
            controls_font = FONT['text_blue']

        configSlideSurf = MenuFunctions.CreateBaseMenuSurf((WINWIDTH/2 - 8, 24), 'ClearMenuBackground')
        surf.blit(configSlideSurf, (4, 4))
        config_position = (4 + configSlideSurf.get_width()/2 - config_font.size('Config')[0]/2, 16 - config_font.size('Config')[1]/2)
        config_font.blit(WORDS['Config'], surf, config_position)

        controlsSlideSurf = MenuFunctions.CreateBaseMenuSurf((WINWIDTH/2 - 8, 24), 'ClearMenuBackground')
        surf.blit(controlsSlideSurf, (WINWIDTH/2 + 4, 4))
        controls_position = (WINWIDTH/2 + 4 + controlsSlideSurf.get_width()/2 - controls_font.size('Controls')[0]/2, 16 - controls_font.size('Controls')[1]/2)
        controls_font.blit(WORDS['Controls'], surf, controls_position)