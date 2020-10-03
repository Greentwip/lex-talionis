from . import GlobalConstants as GC
from . import configuration as cf
from . import MenuFunctions, Engine, InputManager, StateMachine, Utility
from . import GUIObjects, Weapons, Image_Modification, ClassData
from . import HelpMenu

class InfoMenu(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.show_map = False
            # Set unit to be displayed
            self.unit = gameStateObj.info_menu_struct['chosen_unit']
            if not gameStateObj.info_menu_struct['scroll_units']:
                self.scroll_units = [unit for unit in gameStateObj.allunits if (not self.unit.position or unit.position) and 
                                     not unit.dead and unit.team == self.unit.team]
            else:
                self.scroll_units = gameStateObj.info_menu_struct['scroll_units']
            self.scroll_units = sorted(self.scroll_units, key=lambda unit: unit.team)

            # The current state
            self.states = ["Personal Data", "Equipment", "Support & Status"]
            self.currentState = min(gameStateObj.info_menu_struct['current_state'], len(self.states) - 1)

            self.reset_surfs()
            self.growth_flag = False

            self.fluid_helper = InputManager.FluidScroll(200, slow_speed=0)

            self.helpMenu = HelpMenu.HelpGraph(self.states[self.currentState], self.unit, gameStateObj)
            # Counters
            self.background = GC.IMAGESDICT['InfoMenuBackground']
            self.left_arrow = GUIObjects.ScrollArrow('left', (103, 3))
            self.right_arrow = GUIObjects.ScrollArrow('right', (217, 3), 0.5)

            self.logo = None
            self.switch_logo(self.states[self.currentState])

            self.hold_flag = gameStateObj.info_menu_struct['one_unit_only']

            # Transition helpers
            self.nextState = None
            self.next_unit = None
            self.scroll_offset_y = 0
            self.scroll_offset_x = 0
            self.transparency = 0
            self.transition = None
            self.transition_counter = 0

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def reset_surfs(self):
        # Surfs in memory
        self.portrait_surf = None

        self.personal_data_surf = None
        self.growths_surf = None
        self.wexp_surf = None
        self.equipment_surf = None
        self.support_surf = None
        self.skill_surf = None
        self.class_skill_surf = None
        self.fatigue_surf = None

    def back(self, gameStateObj):
        GC.SOUNDDICT['Select 4'].play()
        gameStateObj.info_menu_struct['current_state'] = self.currentState
        gameStateObj.info_menu_struct['chosen_unit'] = self.unit
        if not gameStateObj.info_menu_struct['one_unit_only'] and self.unit.position and not gameStateObj.info_menu_struct['no_movement']:
            gameStateObj.cursor.setPosition(self.unit.position, gameStateObj)
        gameStateObj.stateMachine.changeState('transition_pop')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        currentTime = Engine.get_time()

        if self.helpMenu.current:
            if event == 'INFO' or event == 'BACK':
                GC.SOUNDDICT['Info Out'].play()
                # self.helpMenu.current = None
                self.helpMenu.help_boxes[self.helpMenu.current].help_dialog.set_transition_out()
                return
            if 'RIGHT' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].right:
                    GC.SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].right
            elif 'LEFT' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].left:
                    GC.SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].left
            if 'UP' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].up:
                    GC.SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].up
            elif 'DOWN' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].down:
                    GC.SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].down
        elif not self.transition:  # Only takes input when not transitioning -- for sanity's sake?
            if event == 'INFO':
                GC.SOUNDDICT['Info In'].play()
                self.helpMenu.current = self.helpMenu.initial
                self.helpMenu.help_boxes[self.helpMenu.current].help_dialog.transition_in = True
            elif event == 'SELECT':
                if self.states[self.currentState] == "Personal Data" and self.unit.team == "player":
                    GC.SOUNDDICT['Select 3'].play()
                    self.growth_flag = not self.growth_flag
            elif event == 'BACK':
                self.back(gameStateObj)
                return
            if 'RIGHT' in directions:
                self.move_right(gameStateObj)
            elif 'LEFT' in directions:
                self.move_left(gameStateObj)
            elif 'DOWN' in directions:
                self.last_fluid = currentTime
                GC.SOUNDDICT['Status_Character'].play()
                if not self.hold_flag and len(self.scroll_units):
                    index = self.scroll_units.index(self.unit)
                    if index < len(self.scroll_units) - 1:
                        self.next_unit = self.scroll_units[index + 1]
                    else:
                        self.next_unit = self.scroll_units[0]
                    self.transition = 'DOWN'
                    # self.reset_surfs()
                    self.helpMenu = HelpMenu.HelpGraph(self.states[self.currentState], self.next_unit, gameStateObj)
            elif 'UP' in directions:
                self.last_fluid = currentTime
                GC.SOUNDDICT['Status_Character'].play()
                if not self.hold_flag and len(self.scroll_units):
                    index = self.scroll_units.index(self.unit)
                    if index > 0:
                        self.next_unit = self.scroll_units[index - 1]
                    else:
                        self.next_unit = self.scroll_units[-1] # last unit
                    self.transition = 'UP'
                    # self.reset_surfs()
                    self.helpMenu = HelpMenu.HelpGraph(self.states[self.currentState], self.next_unit, gameStateObj)

    def move_left(self, gameStateObj):
        GC.SOUNDDICT['Status_Page_Change'].play()
        self.last_fluid = Engine.get_time()
        self.nextState = (self.currentState - 1) if self.currentState > 0 else len(self.states) - 1
        self.transition = 'LEFT'
        self.helpMenu = HelpMenu.HelpGraph(self.states[self.nextState], self.unit, gameStateObj)
        self.left_arrow.pulse()
        self.switch_logo(self.states[self.nextState])

    def move_right(self, gameStateObj):
        GC.SOUNDDICT['Status_Page_Change'].play()
        self.last_fluid = Engine.get_time()
        self.nextState = (self.currentState + 1) if self.currentState < len(self.states) - 1 else 0
        self.transition = 'RIGHT'
        self.helpMenu = HelpMenu.HelpGraph(self.states[self.nextState], self.unit, gameStateObj)
        self.right_arrow.pulse()
        self.switch_logo(self.states[self.nextState])

    def update(self, gameStateObj, metaDataObj):
        if self.helpMenu.current:
            self.helpMenu.help_boxes[self.helpMenu.current].update()
            if self.helpMenu.help_boxes[self.helpMenu.current].help_dialog.transition_out == -1:
                self.helpMenu.help_boxes[self.helpMenu.current].help_dialog.transition_out = False
                self.helpMenu.initial = self.helpMenu.current
                self.helpMenu.current = None

        # Up and Down
        if self.next_unit:
            self.transition_counter += 1
            # Transition in
            if self.next_unit == self.unit:
                if self.transition_counter == 1:
                    self.transparency = 200
                    self.scroll_offset_y = -80 if self.transition == 'DOWN' else 80
                elif self.transition_counter == 2:
                    self.transparency = 160
                    self.scroll_offset_y = -32 if self.transition == 'DOWN' else 32
                elif self.transition_counter == 3:
                    self.transparency = 120
                    self.scroll_offset_y = -16 if self.transition == 'DOWN' else 16
                elif self.transition_counter == 4:
                    self.transparency = 40
                    self.scroll_offset_y = -4 if self.transition == 'DOWN' else 4
                elif self.transition_counter == 5:
                    self.scroll_offset_y = 0
                else:
                    self.transition = None
                    self.transparency = 0
                    self.next_unit = None
                    self.transition_counter = 0
            # Transition out
            else:
                if self.transition_counter == 1:
                    self.transparency = 40
                elif self.transition_counter == 2:
                    self.transparency = 80
                elif self.transition_counter == 3:
                    self.transparency = 120
                    self.scroll_offset_y = 8 if self.transition == 'DOWN' else -8
                elif self.transition_counter == 4:
                    self.transparency = 200
                    self.scroll_offset_y = 16 if self.transition == 'DOWN' else -16
                elif self.transition_counter < 8: # (5, 6, 7, 8):  # Pause for a bit
                    self.transparency = 255
                    self.scroll_offset_y = 160 if self.transition == 'DOWN' else -160
                else:
                    self.unit = self.next_unit  # Now transition in
                    self.reset_surfs()
                    self.transition_counter = 0

        # Left and Right
        elif self.nextState is not None:
            self.transition_counter += 1
            # Transition in
            if self.nextState == self.currentState:
                if self.transition_counter == 1:
                    self.scroll_offset_x = 104 if self.transition == 'RIGHT' else -104
                elif self.transition_counter == 2:
                    self.scroll_offset_x = 72 if self.transition == 'RIGHT' else -72
                elif self.transition_counter == 3:
                    self.scroll_offset_x = 56 if self.transition == 'RIGHT' else -56
                elif self.transition_counter == 4:
                    self.scroll_offset_x = 40 if self.transition == 'RIGHT' else -40
                elif self.transition_counter == 5:
                    self.scroll_offset_x = 24 if self.transition == 'RIGHT' else -24
                elif self.transition_counter == 6:
                    self.scroll_offset_x = 8 if self.transition == 'RIGHT' else -8
                else:
                    self.transition = None
                    self.scroll_offset_x = 0
                    self.nextState = None
                    self.transition_counter = 0
            else:
                if self.transition_counter == 1:
                    self.scroll_offset_x = -32 if self.transition == 'RIGHT' else 32
                elif self.transition_counter == 2:
                    self.scroll_offset_x = -56 if self.transition == 'RIGHT' else 56
                elif self.transition_counter == 3:
                    self.scroll_offset_x = -80 if self.transition == 'RIGHT' else 80
                elif self.transition_counter == 4:
                    self.scroll_offset_x = -96 if self.transition == 'RIGHT' else 96
                elif self.transition_counter == 5:
                    self.scroll_offset_x = -112 if self.transition == 'RIGHT' else 112
                else:
                    self.scroll_offset_x = -140 if self.transition == 'RIGHT' else 140
                    self.currentState = self.nextState
                    self.transition_counter = 0

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        # surf.fill(GC.COLORDICT['black'])
        surf.blit(self.background, (0, 0))

        # Image flashy thing at the top of the InfoMenu
        num_frames = 8
        blend_perc = abs(num_frames - ((Engine.get_time()/134)%(num_frames*2))) / float(num_frames)  # 8 frames long, 8 different frames
        im = Image_Modification.flickerImageTranslucentBlend(GC.IMAGESDICT['InfoMenuFlash'], 128.*blend_perc)
        surf.blit(im, (98, 0), None, Engine.BLEND_RGB_ADD)

        # Portrait and Slide
        self.draw_portrait(surf)
        self.drawSlide(surf, gameStateObj, metaDataObj)

        if self.helpMenu.current:
            self.helpMenu.help_boxes[self.helpMenu.current].draw(surf)

        return surf

    def draw_portrait(self, surf):
        # Only create if we don't have one in memory
        if not self.portrait_surf:
            self.portrait_surf = self.create_portrait()

        # Stick it on the surface
        if self.transparency:
            im = Image_Modification.flickerImageTranslucent255(self.portrait_surf, 255 - self.transparency)
            surf.blit(im, (0, self.scroll_offset_y))
        else:
            surf.blit(self.portrait_surf, (0, self.scroll_offset_y))

        # Blit the unit's active sprite
        if not self.transparency:
            activeSpriteSurf = self.unit.sprite.create_image('active')
            x_pos = 73 - max(0, (activeSpriteSurf.get_width() - 16)//2)
            y_pos = GC.WINHEIGHT - 37 - max(0, (activeSpriteSurf.get_width() - 16)/2)
            # im = Image_Modification.flickerImageTranslucent255(activeSpriteSurf, self.transparency)
            # surf.blit(im, (x_pos, y_pos + self.scroll_offset_y))
            surf.blit(activeSpriteSurf, (x_pos, y_pos + self.scroll_offset_y))

    def create_portrait(self):
        UnitInfoSurface = Engine.create_surface((96, GC.WINHEIGHT), transparent=True)

        UnitInfoSurface.blit(GC.IMAGESDICT['InfoUnit'], (8, 122))

        PortraitSurf = Engine.subsurface(self.unit.bigportrait, ((self.unit.bigportrait.get_width() - 80)//2, 0, 80, 72))
        UnitInfoSurface.blit(PortraitSurf, (8, 8))

        name_size = GC.FONT['text_white'].size(self.unit.name)
        position = (96//2 - name_size[0]//2, 80)
        GC.FONT['text_white'].blit(self.unit.name, UnitInfoSurface, position) 
        # Blit the unit's class on the simple info block
        long_name = ClassData.class_dict[self.unit.klass]['long_name']
        GC.FONT['text_white'].blit(long_name, UnitInfoSurface, (8, 104))
        # Blit the unit's level on the simple info block
        level_size = GC.FONT['text_blue'].size(str(self.unit.level))
        position = (39 - level_size[0], 120)
        GC.FONT['text_blue'].blit(str(self.unit.level), UnitInfoSurface, position)
        # Blit the unit's exp on the simple info block
        exp_size = GC.FONT['text_blue'].size(str(int(self.unit.exp)))
        position = (63 - exp_size[0], 120)
        GC.FONT['text_blue'].blit(str(int(self.unit.exp)), UnitInfoSurface, position)
        # Blit the unit's current hp on the simple info block
        current_hp = str(self.unit.currenthp)
        if len(current_hp) > 2:
            current_hp = '??'
        current_hp_size = GC.FONT['text_blue'].size(current_hp)
        position = (39 - current_hp_size[0], 136)
        GC.FONT['text_blue'].blit(current_hp, UnitInfoSurface, position)
        # Blit the unit's max hp on the simple info block
        max_hp = str(self.unit.stats['HP'])
        if len(max_hp) > 2:
            max_hp = '??'
        max_hp_size = GC.FONT['text_blue'].size(max_hp)
        position = (63 - max_hp_size[0], 136)
        GC.FONT['text_blue'].blit(max_hp, UnitInfoSurface, position)
        # Blit the white status platform
        PlatSurf = GC.IMAGESDICT['StatusPlatform']
        pos = (66, 131)
        UnitInfoSurface.blit(PlatSurf, pos)
        return UnitInfoSurface

    def drawTopArrows(self, surf):
        self.left_arrow.draw(surf)
        self.right_arrow.draw(surf)

    def switch_logo(self, name):
        if name == "Personal Data":
            image = GC.IMAGESDICT['InfoPersonalDataTitle']
        elif name == "Equipment":
            image = GC.IMAGESDICT['InfoItemsTitle']
        elif name == "Support & Status":
            image = GC.IMAGESDICT['InfoWeaponTitle']
        else:
            return
        if self.logo:
            self.logo.switch_image(image)
        else:
            self.logo = MenuFunctions.Logo(image, (164, 10))

    def drawSlide(self, surf, gameStateObj, metaDataObj):
        top_surf = Engine.create_surface((surf.get_width(), surf.get_height()), transparent=True)
        main_surf = Engine.copy_surface(top_surf)
        # blit title of menu
        top_surf.blit(GC.IMAGESDICT['InfoTitleBackground'], (112, 8))
        if self.logo:
            self.logo.update()
            self.logo.draw(top_surf)
        page = str(self.currentState + 1) + '/' + str(len(self.states))
        GC.FONT['small_white'].blit(page, top_surf, (235 - GC.FONT['small_white'].size(page)[0], 12))

        self.drawTopArrows(top_surf)

        if self.states[self.currentState] == "Personal Data":
            if self.growth_flag:
                if not self.growths_surf:
                    self.growths_surf = self.create_growths_surf(gameStateObj)
                self.draw_growths_surf(main_surf)
            else:
                if not self.personal_data_surf:
                    self.personal_data_surf = self.create_personal_data_surf(gameStateObj)
                self.draw_personal_data_surf(main_surf)
            if not self.class_skill_surf:
                self.class_skill_surf = self.create_class_skill_surf()
            self.draw_class_skill_surf(main_surf)
            if cf.CONSTANTS['fatigue'] and self.unit.team == 'player' and \
                    'Fatigue' in gameStateObj.game_constants:
                if not self.fatigue_surf:
                    self.fatigue_surf = self.create_fatigue_surf()
                self.draw_fatigue_surf(main_surf)

        elif self.states[self.currentState] == 'Equipment':
            if not self.equipment_surf:
                self.equipment_surf = self.create_equipment_surf(gameStateObj)
            self.draw_equipment_surf(main_surf)
        elif self.states[self.currentState] == 'Support & Status': 
            main_surf.blit(GC.IMAGESDICT['StatusLogo'], (100, GC.WINHEIGHT - 24 - 10))
            if not self.skill_surf:
                self.skill_surf = self.create_skill_surf()
            self.draw_skill_surf(main_surf)
            if not self.wexp_surf:
                self.wexp_surf = self.create_wexp_surf()
            self.draw_wexp_surf(main_surf)
            # Support surf also goes here
            if not self.support_surf:
                self.support_surf = self.create_support_surf(gameStateObj)
            self.draw_support_surf(main_surf)

        # Now put it in the right place
        offset_x = max(96, 96 - self.scroll_offset_x)
        main_surf = Engine.subsurface(main_surf, (offset_x, 0, main_surf.get_width() - offset_x, GC.WINHEIGHT))
        surf.blit(main_surf, (max(96, 96 + self.scroll_offset_x), self.scroll_offset_y))
        if self.transparency:
            top_surf = Image_Modification.flickerImageTranslucent255(top_surf, 255 - self.transparency)
        surf.blit(top_surf, (0, self.scroll_offset_y))
    
    def create_personal_data_surf(self, gameStateObj):
        # Menu Background
        menu_size = (GC.WINWIDTH - 96, GC.WINHEIGHT)
        menu_surf = Engine.create_surface(menu_size, transparent=True)

        max_stats = ClassData.class_dict[self.unit.klass]['max']
        # offset = GC.FONT['text_yellow'].size('Mag')[0] + 4
        # For each left stat
        stats = ['STR', 'MAG', 'SKL', 'SPD', 'DEF', 'RES']
        for idx, stat in enumerate(stats):
            index = GC.EQUATIONS.stat_list.index(stat)
            self.build_groove(menu_surf, (27, GC.TILEHEIGHT*idx + 32), int(max_stats[index]/float(cf.CONSTANTS['max_stat'])*44), 
                              self.unit.stats[stat].base_stat/float(max_stats[index]))
            self.unit.stats[stat].draw(menu_surf, self.unit, (47, GC.TILEHEIGHT*idx + 24))

        self.blit_stat_titles(menu_surf)

        self.unit.stats['LCK'].draw(menu_surf, self.unit, (111, 24))
        self.unit.stats['MOV'].draw(menu_surf, self.unit, (111, GC.TILEHEIGHT + 24))
        self.unit.stats['CON'].draw(menu_surf, self.unit, (111, GC.TILEHEIGHT*2 + 24))
        GC.FONT['text_blue'].blit(str(self.unit.strTRV), menu_surf, (96, GC.TILEHEIGHT*4 + 24)) # Blit Outlined Traveler
        # Blit Outlined Aid
        GC.FONT['text_blue'].blit(str(self.unit.getAid()), menu_surf, 
                                  (111 - GC.FONT['text_blue'].size(str(self.unit.getAid()))[0], GC.TILEHEIGHT*3 + 24))

        # Handle MountSymbols
        if 'Dragon' in self.unit.tags:
            AidSurf = Engine.subsurface(GC.ICONDICT['Aid'], (0, 48, 16, 16))
        elif 'flying' in self.unit.status_bundle:
            AidSurf = Engine.subsurface(GC.ICONDICT['Aid'], (0, 32, 16, 16))
        elif 'Mounted' in self.unit.tags:
            AidSurf = Engine.subsurface(GC.ICONDICT['Aid'], (0, 16, 16, 16))
        else:
            AidSurf = Engine.subsurface(GC.ICONDICT['Aid'], (0, 0, 16, 16))
        AidRect = AidSurf.get_rect()
        AidRect.topleft = (112, GC.TILEHEIGHT*3 + 24)
        menu_surf.blit(AidSurf, AidRect)

        # Handle Affinity
        if cf.CONSTANTS['support']:
            if self.unit.name in gameStateObj.support.node_dict:
                gameStateObj.support.node_dict[self.unit.name].affinity.draw(menu_surf, (96, GC.TILEHEIGHT*5 + 24))
            else:
                GC.FONT['text_blue'].blit('---', menu_surf, (96, GC.TILEHEIGHT*5 + 24)) # Blit No Affinity
        else:
            rat = str(self.unit.get_rating())
            if len(rat) < 3:
                rat_size = GC.FONT['text_blue'].size(rat)[0]
                GC.FONT['text_blue'].blit(rat, menu_surf, (111 - rat_size, GC.TILEHEIGHT*5 + 24))
            else:
                GC.FONT['text_blue'].blit(rat, menu_surf, (96, GC.TILEHEIGHT*5 + 24))

        return menu_surf

    def blit_stat_titles(self, menu_surf, growths=False):
        GC.FONT['text_yellow'].blit(cf.WORDS['STR'], menu_surf, (8, 24)) # Blit Outlined Strength
        GC.FONT['text_yellow'].blit(cf.WORDS['MAG'], menu_surf, (8, GC.TILEHEIGHT*1 + 24)) # Blit Outlined Magic
        GC.FONT['text_yellow'].blit(cf.WORDS['SKL'], menu_surf, (8, GC.TILEHEIGHT*2 + 24)) # Blit Outlined Skill
        GC.FONT['text_yellow'].blit(cf.WORDS['SPD'], menu_surf, (8, GC.TILEHEIGHT*3 + 24)) # Blit Outlined Speed
        GC.FONT['text_yellow'].blit(cf.WORDS['LCK'], menu_surf, (72, 24)) # Blit Outlined Luck
        GC.FONT['text_yellow'].blit(cf.WORDS['DEF'], menu_surf, (8, GC.TILEHEIGHT*4 + 24)) # Blit Outlined Defense
        GC.FONT['text_yellow'].blit(cf.WORDS['RES'], menu_surf, (8, GC.TILEHEIGHT*5 + 24)) # Blit Outlined Resistance
        GC.FONT['text_yellow'].blit(cf.WORDS['MOV'], menu_surf, (72, GC.TILEHEIGHT*1 + 24)) # Blit Outlined Movement
        GC.FONT['text_yellow'].blit(cf.WORDS['CON'], menu_surf, (72, GC.TILEHEIGHT*2 + 24)) # Blit Outlined Constitution
        GC.FONT['text_yellow'].blit(cf.WORDS['Trv'], menu_surf, (72, GC.TILEHEIGHT*4 + 24)) # Blit Outlined Traveler
        if growths:
            GC.FONT['text_yellow'].blit('HP', menu_surf, (72, GC.TILEHEIGHT*3 + 24)) # Blit Outlined Aid
        else:
            GC.FONT['text_yellow'].blit(cf.WORDS['Aid'], menu_surf, (72, GC.TILEHEIGHT*3 + 24)) # Blit Outlined Aid
        if cf.CONSTANTS['support']:
            GC.FONT['text_yellow'].blit(cf.WORDS['Affin'], menu_surf, (72, GC.TILEHEIGHT*5 + 24)) # Blit Outlined Affinity
        else:
            GC.FONT['text_yellow'].blit(cf.WORDS['Rat'], menu_surf, (72, GC.TILEHEIGHT*5 + 24)) # Blit Outlined Rating

    def draw_personal_data_surf(self, surf):
        menu_position = (96, 0)
        surf.blit(self.personal_data_surf, menu_position)

    def create_growths_surf(self, gameStateObj):
        # Menu Background
        menu_size = (GC.WINWIDTH - 96, GC.WINHEIGHT)
        menu_surf = Engine.create_surface(menu_size, transparent=True)

        stats = [self.unit.growths[1], self.unit.growths[2], self.unit.growths[3], self.unit.growths[4], self.unit.growths[6], self.unit.growths[7]]

        self.blit_stat_titles(menu_surf, growths=True)

        for index, stat in enumerate(stats):
            font = GC.FONT['text_blue']
            font.blit(str(stat), menu_surf, (47 - font.size(str(stat))[0], GC.TILEHEIGHT*1*index + 24))
        GC.FONT['text_blue'].blit(str(self.unit.growths[5]), menu_surf, (111 - GC.FONT['text_blue'].size(str(self.unit.growths[5]))[0], 24)) # Blit Outlined Luck
        GC.FONT['text_blue'].blit(str(self.unit.growths[9]), menu_surf, (111 - GC.FONT['text_blue'].size(str(self.unit.growths[9]))[0], GC.TILEHEIGHT*1 + 24)) # Blit Outlined Movement
        GC.FONT['text_blue'].blit(str(self.unit.growths[8]), menu_surf, (111 - GC.FONT['text_blue'].size(str(self.unit.growths[8]))[0], GC.TILEHEIGHT*2 + 24)) # Blit Outlined Constitution
        GC.FONT['text_blue'].blit(str(self.unit.strTRV), menu_surf, (96, GC.TILEHEIGHT*4 + 24)) # Blit Outlined Traveler
        GC.FONT['text_blue'].blit(str(self.unit.growths[0]), menu_surf, (111 - GC.FONT['text_blue'].size(str(self.unit.growths[0]))[0], GC.TILEHEIGHT*3 + 24))

        # Handle Affinity
        if cf.CONSTANTS['support'] and self.unit.id in gameStateObj.support.node_dict:
            gameStateObj.support.node_dict[self.unit.id].affinity.draw(menu_surf, (96, GC.TILEHEIGHT*5 + 24))
        else:
            GC.FONT['text_blue'].blit('--', menu_surf, (96, GC.TILEHEIGHT*5 + 24)) # Blit No Affinity

        return menu_surf

    def draw_growths_surf(self, surf):
        menu_position = (96, 0)
        surf.blit(self.growths_surf, menu_position)

    def build_groove(self, surf, topleft, width, fill):
        back_groove_surf = GC.IMAGESDICT['StatGrooveBack']
        bgs_start = Engine.subsurface(back_groove_surf, (0, 0, 2, 5))
        bgs_mid = Engine.subsurface(back_groove_surf, (2, 0, 1, 5))
        bgs_end = Engine.subsurface(back_groove_surf, (3, 0, 2, 5))
        fgs_mid = GC.IMAGESDICT['StatGrooveFill']

        # Build back groove
        start_pos = topleft
        surf.blit(bgs_start, start_pos)
        for index in range(width - 2):
            mid_pos = (topleft[0] + bgs_start.get_width() + bgs_mid.get_width()*index, topleft[1])
            surf.blit(bgs_mid, mid_pos)
        end_pos = (topleft[0] + bgs_start.get_width() + bgs_mid.get_width()*(width-2), topleft[1])
        surf.blit(bgs_end, end_pos)

        # Build fill groove
        number_of_fgs_needed = int(fill * (width - 1)) # Width of groove minus section for start and end of back groove
        for groove in range(number_of_fgs_needed):
            surf.blit(fgs_mid, (topleft[0] + bgs_start.get_width() + groove - 1, topleft[1] + 1))

    def create_wexp_surf(self):
        menu_surf = Engine.create_surface((GC.WINWIDTH - 96, 24), transparent=True)
        # menu_surf = BaseMenuSurf.CreateBaseMenuSurf((GC.WINWIDTH//2 + 8, 24))
        # Weapon Icons Pictures
        weaponIcons = GC.ITEMDICT['Wexp_Icons']

        counter = 0
        how_many = sum(1 if wexp > 0 else 0 for wexp in self.unit.wexp)
        x_pos = (menu_surf.get_width()-6)//max(how_many, 2)
        for index, wexp in enumerate(self.unit.wexp):
            wexpLetter = Weapons.EXP.number_to_letter(wexp)
            wexp_percentage = Weapons.EXP.percentage(wexp)
            if wexp > 0:
                offset = 8 + counter*x_pos
                counter += 1
                # Add icon
                menu_surf.blit(Engine.subsurface(weaponIcons, (0, index*16, 16, 16)), (offset, 4))

                # Actually build grooves
                self.build_groove(menu_surf, (offset + 18, 10), x_pos - 24, wexp_percentage)

                # Add text
                GC.FONT['text_blue'].blit(wexpLetter, menu_surf, (offset + 18 + (x_pos - 22)//2 - GC.FONT['text_blue'].size(wexpLetter)[0]//2, 4))

        return menu_surf

    def draw_wexp_surf(self, surf):
        menu_position = (96, 24)
        surf.blit(self.wexp_surf, menu_position)

    def create_equipment_surf(self, gameStateObj):
        # Menu Background
        menu_size = (GC.WINWIDTH - 96, GC.WINHEIGHT)
        menu_surf = Engine.create_surface(menu_size, transparent=True)

        # Blit background highlight
        if self.unit.getMainWeapon(): # Ony highlight if unit has weapon
            index_of_mainweapon = self.unit.items.index(self.unit.getMainWeapon())
            highlightSurf = GC.IMAGESDICT['EquipmentHighlight']
            menu_surf.blit(highlightSurf, (8, 32 + 16 * index_of_mainweapon))

        # Blit items
        for index, item in enumerate(self.unit.items):
            item.draw(menu_surf, (8, index*GC.TILEHEIGHT + 24)) # Draws icon
            if item.droppable:
                namefont = GC.FONT['text_green']
                usefont = GC.FONT['text_green']
            elif self.unit.canWield(item) and self.unit.canUse(item):
                namefont = GC.FONT['text_white']
                usefont = GC.FONT['text_blue']
            else:
                namefont = GC.FONT['text_grey']
                usefont = GC.FONT['text_grey']
            namefont.blit(item.name, menu_surf, (24, index*GC.TILEHEIGHT + 24))
            if item.uses:
                cur_uses = str(item.uses)
                total_uses = str(item.uses.total_uses)
            elif item.c_uses:
                cur_uses = str(item.c_uses)
                total_uses = str(item.c_uses.total_uses)
            elif item.cooldown:
                uses_height = 23
                if not item.cooldown.charged:
                    cur_uses = str(item.cooldown.cd_turns)
                    total_uses = str(item.cooldown.total_cd_turns)
                    namefont = GC.FONT['text_light_red']
                    usefont = GC.FONT['text_light_red']
                    MenuFunctions.build_cd_groove(menu_surf, (89, index*GC.TILEHEIGHT + 37),
                                      40, int(round((int(cur_uses)/int(total_uses))*40)), True)
                else:
                    cur_uses = str(item.cooldown.cd_uses)
                    total_uses = str(item.cooldown.total_cd_uses)
                    namefont = GC.FONT['text_light_green']
                    usefont = GC.FONT['text_light_green']
                    MenuFunctions.build_cd_groove(
                        menu_surf, (89, index*GC.TILEHEIGHT + 37),
                        40, int(round((int(cur_uses)/int(total_uses))*40)), False)
            else:
                cur_uses = total_uses = '--'
            usefont.blit(cur_uses, menu_surf, (104 - usefont.size(cur_uses)[0], index*GC.TILEHEIGHT + 24))
            namefont.blit("/", menu_surf, (106, index*GC.TILEHEIGHT + 24))
            usefont.blit(total_uses, menu_surf, (128 - usefont.size(total_uses)[0], index*GC.TILEHEIGHT + 24))

        # Then, input battle stats
        BattleInfoSurf = GC.IMAGESDICT['BattleInfo']
        # Rect
        top = 104
        left = 12
        menu_surf.blit(BattleInfoSurf, (left, top))
        # Then populate battle info menu_surf
        menu_surf.blit(GC.IMAGESDICT['EquipmentLogo'], (14, top+4)) 
        GC.FONT['text_yellow'].blit(cf.WORDS["Rng"], menu_surf, (78, top))
        GC.FONT['text_yellow'].blit(cf.WORDS["Atk"], menu_surf, (22, top + 16))
        GC.FONT['text_yellow'].blit(cf.WORDS["Hit"], menu_surf, (22, top + 32))
        GC.FONT['text_yellow'].blit(cf.WORDS["AS"], menu_surf, (78, top + 16))
        GC.FONT['text_yellow'].blit(cf.WORDS["Avoid"], menu_surf, (78, top + 32))

        if self.unit.getMainWeapon():
            rng = self.unit.getMainWeapon().get_true_range_string(self.unit)
            dam = str(self.unit.damage(gameStateObj))
            acc = str(self.unit.accuracy(gameStateObj))
        else:
            rng = '--'
            dam = '--'
            acc = '--'
        avo = str(self.unit.avoid(gameStateObj))
        atkspd = str(self.unit.attackspeed(gameStateObj))
        RngWidth = GC.FONT['text_blue'].size(rng)[0]
        AtkWidth = GC.FONT['text_blue'].size(dam)[0]
        HitWidth = GC.FONT['text_blue'].size(acc)[0]
        AvoidWidth = GC.FONT['text_blue'].size(avo)[0]
        ASWidth = GC.FONT['text_blue'].size(atkspd)[0] 
        GC.FONT['text_blue'].blit(rng, menu_surf, (127 - RngWidth, top))
        GC.FONT['text_blue'].blit(dam, menu_surf, (71 - AtkWidth, top + 16))
        GC.FONT['text_blue'].blit(acc, menu_surf, (71 - HitWidth, top + 32))
        GC.FONT['text_blue'].blit(avo, menu_surf, (127 - AvoidWidth, top + 32))
        GC.FONT['text_blue'].blit(atkspd, menu_surf, (127 - ASWidth, top + 16))

        return menu_surf

    def draw_equipment_surf(self, surf):
        menu_position = (96, 0)
        surf.blit(self.equipment_surf, menu_position)

    def draw_status(self, pos, status, menu_surf):
        status.draw(menu_surf, pos)
        if status.time:
            GC.FONT['text_blue'].blit(str(status.time.time_left), menu_surf, (pos[0] + 16, pos[1]))
        elif status.combat_art and status.combat_art.charge_max > 0:
            output = str(status.combat_art.current_charge) + '/' + str(status.combat_art.charge_max)
            GC.FONT['text_blue'].blit(output, menu_surf, (pos[0] + 16, pos[1]))
        elif status.activated_item and status.activated_item.charge_max > 0:
            output = str(status.activated_item.current_charge) + '/' + str(status.activated_item.charge_max)
            GC.FONT['text_blue'].blit(output, menu_surf, (pos[0] + 16, pos[1]))
        elif status.count:
            output = str(status.count.count) + '/' + str(status.count.orig_count)
            GC.FONT['text_blue'].blit(output, menu_surf, (pos[0] + 16, pos[1]))
        # GC.FONT['text_white'].blit(status.name, menu_surf, (32, index*16 + 56))

    def create_skill_surf(self):
        menu_surf = Engine.create_surface((GC.WINWIDTH - 96, 24), transparent=True)
        statuses = [status for status in self.unit.status_effects if not (status.class_skill or status.hidden)][:6]

        for index, status in enumerate(statuses):
            left_pos = index*((GC.WINWIDTH - 96)//max(5, len(statuses)))
            pos = (left_pos + 8, 4)
            self.draw_status(pos, status, menu_surf)

        return menu_surf

    def draw_skill_surf(self, surf):
        menu_position = (96, GC.WINHEIGHT - 24)
        surf.blit(self.skill_surf, menu_position)

    def create_class_skill_surf(self):
        menu_surf = Engine.create_surface((GC.WINWIDTH - 96, 24), transparent=True)
        class_skills = [status for status in self.unit.status_effects if status.class_skill]

        for index, skill in enumerate(class_skills):
            left_pos = index*((GC.WINWIDTH - 96)//max(cf.CONSTANTS['num_skills'], len(class_skills)))
            skill.draw(menu_surf, (left_pos + 8, 4))

        return menu_surf

    def draw_class_skill_surf(self, surf):
        menu_position = (96, GC.WINHEIGHT - 36)
        surf.blit(self.class_skill_surf, menu_position)

    def create_support_surf(self, gameStateObj):
        # Menu background
        menu_surf = Engine.create_surface((GC.WINWIDTH - 96, GC.WINHEIGHT), transparent=True)

        if gameStateObj.support:
            current_supports = gameStateObj.support.get_supports(self.unit.id)
            # support[2] is support level
            current_supports = [support for support in current_supports if support[2]]
        else:
            current_supports = []

        # Display
        top = 48
        for index, (name, affinity, support_level) in enumerate(current_supports):
            affinity.draw(menu_surf, (16, index*16 + top))
            GC.FONT['text_white'].blit(name, menu_surf, (36, index*16 + top))
            if support_level == 1:
                letter_level = '@' # Big C
            elif support_level == 2:
                letter_level = '`' # Big B
            elif support_level == 3:
                letter_level = '~' # Big A
            elif support_level >= 4:
                letter_level = '%' # Big S
            letter_width = GC.FONT['text_yellow'].size(letter_level)[0]
            GC.FONT['text_yellow'].blit(letter_level, menu_surf, (menu_surf.get_width() - 24 - letter_width, index*16 + top))

        return menu_surf

    def draw_support_surf(self, surf):
        surf.blit(self.support_surf, (96, 0))

    def create_fatigue_surf(self):
        menu_size = (GC.WINWIDTH - 96, GC.WINHEIGHT)
        menu_surf = Engine.create_surface(menu_size, transparent=True)
        max_fatigue = max(1, GC.EQUATIONS.get_max_fatigue(self.unit))
        self.build_groove(menu_surf, (27, GC.WINHEIGHT - 9), 88, Utility.clamp(self.unit.fatigue / max_fatigue, 0, 1))
        GC.FONT['text_blue'].blit(str(self.unit.fatigue) + '/' + str(max_fatigue), menu_surf, (56, GC.WINHEIGHT - 17))
        GC.FONT['text_yellow'].blit(cf.WORDS['Ftg'], menu_surf, (8, GC.WINHEIGHT - 17))

        return menu_surf

    def draw_fatigue_surf(self, surf):
        menu_position = (96, 0)
        surf.blit(self.fatigue_surf, (menu_position))
