from . import imagesDict
from . import GlobalConstants as GC
from . import configuration as cf
from . import CustomObjects, BaseMenuSurf, Image_Modification, Engine
from . import StateMachine, Counters, GUIObjects, Background

class OptionsMenu(StateMachine.State, Counters.CursorControl):
    show_map = False
    
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.config = [('Animation', ['Always', 'Your Turn', 'Combat Only', 'Never'], cf.WORDS['Animation_desc'], 0),
                           ('temp_Screen Size', ['1', '2', '3', '4', '5'], cf.WORDS['temp_Screen Size_desc'], 18),
                           ('Unit Speed', list(reversed(range(15, 180, 15))), cf.WORDS['Unit Speed_desc'], 1),
                           ('Text Speed', cf.text_speed_options, cf.WORDS['Text Speed_desc'], 2),
                           ('Cursor Speed', list(reversed(range(32, 160, 16))), cf.WORDS['Cursor Speed_desc'], 8),
                           ('Show Terrain', ['ON', 'OFF'], cf.WORDS['Show Terrain_desc'], 7),
                           ('Show Objective', ['ON', 'OFF'], cf.WORDS['Show Objective_desc'], 6),
                           ('Autocursor', ['ON', 'OFF'], cf.WORDS['Autocursor_desc'], 13),
                           ('HP Map Team', ['All', 'Ally', 'Enemy'], cf.WORDS['HP Map Team_desc'], 10),
                           ('HP Map Cull', ['None', 'Wounded', 'All'], cf.WORDS['HP Map Cull_desc'], 10),
                           ('Music Volume', [x/10.0 for x in range(0, 11, 1)], cf.WORDS['Music Volume_desc'], 15),
                           ('Sound Volume', [x/10.0 for x in range(0, 11, 1)], cf.WORDS['Sound Volume_desc'], 16),
                           ('Autoend Turn', ['ON', 'OFF'], cf.WORDS['Autoend Turn_desc'], 14),
                           ('Confirm End', ['ON', 'OFF'], cf.WORDS['Confirm End_desc'], 14),
                           ('Display Hints', ['ON', 'OFF'], cf.WORDS['Display Hints_desc'], 3)]

            self.controls = {'key_SELECT': Engine.subsurface(GC.IMAGESDICT['Buttons'], (0, 66, 14, 13)),
                             'key_BACK': Engine.subsurface(GC.IMAGESDICT['Buttons'], (0, 82, 14, 13)),
                             'key_INFO': Engine.subsurface(GC.IMAGESDICT['Buttons'], (1, 149, 16, 9)),
                             'key_AUX': Engine.subsurface(GC.IMAGESDICT['Buttons'], (1, 133, 16, 9)),
                             'key_START': Engine.subsurface(GC.IMAGESDICT['Buttons'], (0, 165, 33, 9)),
                             'key_LEFT': Engine.subsurface(GC.IMAGESDICT['Buttons'], (1, 4, 13, 12)),
                             'key_RIGHT': Engine.subsurface(GC.IMAGESDICT['Buttons'], (1, 19, 13, 12)),
                             'key_DOWN': Engine.subsurface(GC.IMAGESDICT['Buttons'], (1, 34, 12, 13)),
                             'key_UP': Engine.subsurface(GC.IMAGESDICT['Buttons'], (1, 50, 12, 13))}

            self.currentSelection = 0
            self.start_offset = 40
            self.top_of_menu = 0

            self.control_order = ['key_SELECT', 'key_BACK', 'key_INFO', 'key_AUX', 'key_LEFT', 'key_RIGHT', 'key_UP', 'key_DOWN', 'key_START']

            self.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

            self.state = CustomObjects.StateMachine('TopMenu')

            Counters.CursorControl.__init__(self)
            self.left_arrow = GUIObjects.ScrollArrow('left', (0, 0), 0)
            self.right_arrow = GUIObjects.ScrollArrow('right', (0, 0), 0.5)

            self.backSurf = gameStateObj.generic_surf

            self.scroll_bar = GUIObjects.ScrollBar((227, 44))

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def back(self, gameStateObj):
        GC.SOUNDDICT['Select 4'].play()
        cf.write_config_file()
        cf.CONSTANTS['Unit Speed'] = cf.OPTIONS['Unit Speed']
        if not cf.OPTIONS['Display Hints']:
            gameStateObj.tutorial_mode_off()
        gameStateObj.stateMachine.changeState('transition_pop')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList, all_keys=True)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if self.state.getState() == "TopMenu":

            if event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                self.currentSelection = 0

            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                self.currentSelection = 1

            elif event == 'DOWN':
                GC.SOUNDDICT['Select 1'].play()
                if self.currentSelection == 0:
                    self.state.changeState('Config')
                else:
                    self.currentSelection = 0
                    self.state.changeState('Controls')

            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
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
                GC.SOUNDDICT['Select 6'].play()
                self.currentSelection += 1
                if self.currentSelection >= len(self.config):
                    self.currentSelection = len(self.config) - 1

            elif 'UP' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.currentSelection -= 1
                if self.currentSelection < 0:
                    self.currentSelection = 0
                    self.state.changeState('TopMenu') # Back to top menu

            elif event == 'BACK':
                self.back(gameStateObj)
                return

            elif event == 'RIGHT':
                GC.SOUNDDICT['Select 6'].play()
                current_section = self.config[self.currentSelection] # Gives me what section we are on
                bounds = current_section[1]
                special = len(''.join(bounds)) > 15 if isinstance(bounds[0], str) else False
                if special:
                    self.right_arrow.pulse()
                current_choice = cf.OPTIONS[current_section[0]] # Gives me what the current option that is selected is
                current_index = self.get_index(bounds, current_choice)
                current_index += 1 # Move that option 1 to the right
                if current_index >= len(bounds): # Make sure we have not gone too far over
                    current_index = 0 if special else len(bounds) - 1
                cf.OPTIONS[current_section[0]] = bounds[current_index] # Set the new option[index] as new option constant
                self.convert_options(current_section[0])
                
            elif event == 'LEFT':
                GC.SOUNDDICT['Select 6'].play()
                current_section = self.config[self.currentSelection]
                bounds = current_section[1]
                special = len(''.join(bounds)) > 15 if isinstance(bounds[0], str) else False
                if special:
                    self.left_arrow.pulse()
                current_choice = cf.OPTIONS[current_section[0]]
                current_index = self.get_index(bounds, current_choice)
                current_index -= 1
                if current_index < 0:
                    current_index = len(bounds) - 1 if special else 0
                cf.OPTIONS[current_section[0]] = bounds[current_index]
                self.convert_options(current_section[0])

        elif self.state.getState() == "Controls":
            if 'DOWN' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.currentSelection += 1
                if self.currentSelection >= len(self.control_order):
                    self.currentSelection = len(self.control_order) - 1

            elif 'UP' in directions:
                GC.SOUNDDICT['Select 6'].play()
                self.currentSelection -= 1
                if self.currentSelection < 0:
                    self.currentSelection = 1
                    self.state.changeState('TopMenu') # Back to top menu

            elif event == 'BACK':
                self.back(gameStateObj)
                return

            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                self.state.changeState("Get_Input")

        elif self.state.getState() == "Get_Input":
            if event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                self.state.changeState("Controls")

            elif event == 'NEW':
                GC.SOUNDDICT['Select 1'].play()
                self.state.back()
                cf.OPTIONS[self.control_order[self.currentSelection]] = gameStateObj.input_manager.unavailable_button
                gameStateObj.input_manager.update_key_map()
                return

            elif event:
                GC.SOUNDDICT['Select 4'].play()
                # Not a legal option
                self.state.back()
                self.state.changeState("Invalid")

        elif self.state.getState() == "Invalid":
            if event:
                GC.SOUNDDICT['Select 6'].play()
                self.state.back()

    def convert_options(self, section):
        if cf.OPTIONS[section] == 'ON':
            cf.OPTIONS[section] = 1
        elif cf.OPTIONS[section] == 'OFF':
            cf.OPTIONS[section] = 0

    def update(self, gameStateObj, metaDataObj):
        # Determine if we need to move the top of the menu
        if self.currentSelection <= self.top_of_menu:
            self.top_of_menu = self.currentSelection - 1
            # self.up_arrow.pulse()
        elif self.currentSelection > self.top_of_menu + 4:
            self.top_of_menu = self.currentSelection - 4
            # self.down_arrow.pulse()
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

        # Update music volume...
        if cf.OPTIONS['Music Volume'] != Engine.music_thread.get_volume():
            Engine.music_thread.set_volume(cf.OPTIONS['Music Volume'])
        if cf.OPTIONS['Sound Volume'] != imagesDict.sound_volume:
            imagesDict.set_sound_volume(cf.OPTIONS['Sound Volume'], GC.SOUNDDICT)

    def draw(self, gameStateObj, metaDataObj):
        surf = self.backSurf
        self.background.draw(surf)
        self.drawSlide(surf)

        self.drawInfo(surf)
        if self.state.getState() == "Config" or (self.state.getState() == "TopMenu" and self.currentSelection == 0):
            self.drawConfig(surf)
            if self.state.getState() == "Config":
                self.drawConfigCursor(surf)
        elif self.state.getState() == "Controls" or self.state.getState() == "Get_Input" or self.state.getState() == "Invalid" or \
                (self.state.getState() == "TopMenu" and self.currentSelection == 1):
            self.drawControls(surf)
            if self.state.getState() == "Controls":
                self.drawControlsCursor(surf)
        if self.state.getState() == "TopMenu":
            self.drawTopMenuCursor(surf)

        if self.state.getState() == "Invalid":
            self.drawInvalid(surf)

        return surf

    def drawInvalid(self, surf):
        size_of_text = GC.FONT['text_white'].size(cf.WORDS["Invalid Choice"])
        width = size_of_text[0]
        height = size_of_text[1]
        pop_up_surf = BaseMenuSurf.CreateBaseMenuSurf((width + 16 - width%8, height + 16 - height%8))
        surf.blit(Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'].copy(), 60), (0, 0))
        topleft = (GC.WINWIDTH//2 - pop_up_surf.get_width()//2, GC.WINHEIGHT//2 - pop_up_surf.get_height()//2)
        surf.blit(pop_up_surf, topleft)
        position = (GC.WINWIDTH//2 - width//2, GC.WINHEIGHT//2 - height//2)
        GC.FONT['text_white'].blit(cf.WORDS["Invalid Choice"], surf, position)

    def drawControls(self, surf):
        for index, control in enumerate(self.control_order[self.top_of_menu:self.top_of_menu + 6]):
            name_font = GC.FONT['text_white']
            key_font = GC.FONT['text_blue']
            if self.state.getState() == "Get_Input" and index == self.currentSelection - self.top_of_menu:
                name_font = GC.FONT['text_yellow']
                key_font = GC.FONT['text_yellow']

            icon_surf = self.controls[control]
            topleft = (24 - icon_surf.get_width()//2, self.start_offset + index*16 + 8 - icon_surf.get_height()//2)
            surf.blit(icon_surf, topleft)

            name_position = (56, self.start_offset + index*16)
            name_font.blit(cf.WORDS[control], surf, name_position)

            key_position = (128, self.start_offset + index*16)
            key_font.blit(Engine.get_key_name(cf.OPTIONS[control]), surf, key_position)

        # self.drawScrollArrows(surf, self.control_order)
        self.scroll_bar.draw(surf, self.top_of_menu, 6, len(self.control_order))

    def drawConfig(self, surf):
        for index, option in enumerate(self.config[self.top_of_menu:self.top_of_menu + 6]):
            name, bounds, info, icon = option
            if name.startswith('temp_'):
                display_name = name[5:]
            else:
                display_name = name
            # Blit Icon
            icon_position = (16, self.start_offset + index*16)
            icon_surf = Engine.subsurface(GC.ICONDICT['Options_Icons'], (0, icon*16, 16, 16))
            surf.blit(icon_surf, icon_position)
            # Blit name
            name_position = (32, self.start_offset + 1 + index*16)
            GC.FONT['text_white'].blit(cf.WORDS[display_name], surf, name_position)
            current_option = cf.OPTIONS[name]
            # Blit Options
            # Is a slider
            if isinstance(bounds[0], int) or isinstance(bounds[0], float):
                slider_bar = GC.IMAGESDICT['HealthBarBG']
                surf.blit(slider_bar, (112, self.start_offset + index*16 + 4))

                slider_hold = GC.IMAGESDICT['WaitingCursor']
                if current_option in bounds:
                    slider_fraction = bounds.index(current_option)/float(len(bounds) - 1)
                else:
                    slider_fraction = (current_option - bounds[0])/float((bounds[-1] - bounds[0]))
                hold_offset = slider_fraction*(slider_bar.get_width() - 6)
                slider_bop = self.cursorAnim[self.cursorCounter]//2 - 1 if index + self.top_of_menu == self.currentSelection else 0
                topleft = (112 + hold_offset, self.start_offset + index*16 + 4 + slider_bop)
                surf.blit(slider_hold, topleft)
            # Is a list of options
            else:
                if len(''.join(bounds)) > 15:
                    font = GC.FONT['text_blue']
                    size = font.size(cf.WORDS[current_option])
                    option_position = (164 - size[0]//2, self.start_offset + index*16)
                    font.blit(cf.WORDS[current_option], surf, option_position)
                    self.drawSideArrows(surf, self.start_offset + index*16)
                else:
                    word_index = 0
                    for choice in bounds:
                        if choice == current_option or (choice == 'ON' and current_option) or (choice == 'OFF' and not current_option) or \
                                (isinstance(choice, str) and str(current_option) == choice):
                            font = GC.FONT['text_blue']
                        else:
                            font = GC.FONT['text_grey']
                        option_position = (112 + word_index, self.start_offset + index*16)
                        font.blit(cf.WORDS[choice], surf, option_position)
                        word_index += font.size(cf.WORDS[choice] + '   ')[0]

        self.scroll_bar.draw(surf, self.top_of_menu, 6, len(self.config))

    def drawSideArrows(self, surf, y_pos):
        self.left_arrow.x = 112
        self.right_arrow.x = GC.WINWIDTH - 32
        self.left_arrow.y = y_pos
        self.right_arrow.y = y_pos
        self.left_arrow.draw(surf)
        self.right_arrow.draw(surf)

    def get_index(self, choices, option):
        if len(choices) == 1:
            return 0
        elif 'ON' in choices and 'OFF' in choices:
            if option:
                return choices.index('ON')
            else:  
                return choices.index('OFF')
        elif isinstance(choices[0], str):
            return choices.index(str(option))
        elif option in choices:
            return choices.index(option)
        else:
            return choices.index(min(choices, key=lambda x: abs(x - option)))

    def drawConfigCursor(self, surf):
        # Blit cursor (s)
        # Blit moving cursor
        bounds = self.config[self.currentSelection][1]
        if not isinstance(bounds[0], int) and not isinstance(bounds[0], float) and len(''.join(bounds)) <= 15:
            bound_index = self.get_index(bounds, cf.OPTIONS[self.config[self.currentSelection][0]])
            left_position = GC.FONT['text_white'].size('   '.join(bounds[:bound_index]) + ('   ' if bound_index > 0 else ''))[0] + 96
            top_position = 43 + (self.currentSelection - self.top_of_menu)*16
            surf.blit(self.cursor, (left_position + self.cursorAnim[self.cursorCounter], top_position))
        # Blit still cursor
        still_cursor_position = (19 - self.cursor.get_width(), 43 + (self.currentSelection - self.top_of_menu)*16)
        surf.blit(self.cursor, still_cursor_position)

    def drawControlsCursor(self, surf):
        # Blit cursor
        cursor_position = (56 - self.cursor.get_width() + self.cursorAnim[self.cursorCounter], 42 + (self.currentSelection - self.top_of_menu)*16)
        surf.blit(self.cursor, cursor_position)

    def drawTopMenuCursor(self, surf):
        # Blit Moving Cursor
        if self.currentSelection == 0: # Config
            left_position = 4 + (GC.WINWIDTH//2 - 8)//2 - GC.FONT['text_white'].size('Config')[0]//2 + self.cursorAnim[self.cursorCounter] - 16
        else: # Controls
            left_position = GC.WINWIDTH//2 + 4 + (GC.WINWIDTH//2 - 8)//2 - GC.FONT['text_white'].size('Controls')[0]//2 + self.cursorAnim[self.cursorCounter] - 16
        moving_cursor_position = (left_position, 12)
        surf.blit(self.cursor, moving_cursor_position)

    def drawInfo(self, surf):
        mainInfoSurf = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH + 16, 16), 'ClearMenuBackground')
        surf.blit(mainInfoSurf, (-8, GC.WINHEIGHT - 16))

        if self.state.getState() == "Config":
            info_text = self.config[self.currentSelection][2]
        elif self.state.getState() == "Controls":
            info_text = cf.WORDS['Controls_desc']
        elif self.state.getState() == "Get_Input":
            info_text = cf.WORDS['Get_Input_desc']
        elif self.state.getState() == "TopMenu":
            if self.currentSelection == 0:
                info_text = cf.WORDS['Config_desc']
            else:
                info_text = cf.WORDS['Controls_desc']
        else:
            return
        GC.FONT['text_white'].blit(info_text, surf, (GC.WINWIDTH//2 - GC.FONT['text_white'].size(info_text)[0]//2, GC.WINHEIGHT - 16))

    def drawSlide(self, surf):
        mainSlideSurf = BaseMenuSurf.CreateBaseMenuSurf((228, 104))
        surf.blit(mainSlideSurf, (6, 36))

        if self.state.getState() == 'Config' or (self.state.getState() == 'TopMenu' and self.currentSelection == 0):
            config_font = GC.FONT['text_yellow']
            controls_font = GC.FONT['text_grey']
        else:
            config_font = GC.FONT['text_grey']
            controls_font = GC.FONT['text_yellow']

        configSlideSurf = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH//2 - 8, 24), 'ClearMenuBackground')
        surf.blit(configSlideSurf, (4, 4))
        config_position = (4 + configSlideSurf.get_width()//2 - config_font.size('Config')[0]//2, 16 - config_font.size('Config')[1]//2)
        config_font.blit(cf.WORDS['Config'], surf, config_position)

        controlsSlideSurf = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH//2 - 8, 24), 'ClearMenuBackground')
        surf.blit(controlsSlideSurf, (GC.WINWIDTH//2 + 4, 4))
        controls_position = (GC.WINWIDTH//2 + 4 + controlsSlideSurf.get_width()//2 - controls_font.size('Controls')[0]//2, 16 - controls_font.size('Controls')[1]//2)
        controls_font.blit(cf.WORDS['Controls'], surf, controls_position)
