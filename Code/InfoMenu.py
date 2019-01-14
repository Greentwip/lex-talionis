try:
    import GlobalConstants as GC
    import configuration as cf
    import MenuFunctions, Engine, InputManager, StateMachine, Counters
    import GUIObjects, Weapons, Image_Modification, ClassData
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import MenuFunctions, Engine, InputManager, StateMachine, Counters 
    from . import GUIObjects, Weapons, Image_Modification, ClassData

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

            self.helpMenu = HelpGraph(self.states[self.currentState], self.unit, gameStateObj)
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

    def back(self, gameStateObj):
        GC.SOUNDDICT['Select 4'].play()
        gameStateObj.info_menu_struct['current_state'] = self.currentState
        gameStateObj.info_menu_struct['chosen_unit'] = self.unit
        if not gameStateObj.info_menu_struct['one_unit_only'] and self.unit.position:
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
                    self.helpMenu = HelpGraph(self.states[self.currentState], self.next_unit, gameStateObj)
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
                    self.helpMenu = HelpGraph(self.states[self.currentState], self.next_unit, gameStateObj)

    def move_left(self, gameStateObj):
        GC.SOUNDDICT['Status_Page_Change'].play()
        self.last_fluid = Engine.get_time()
        self.nextState = (self.currentState - 1) if self.currentState > 0 else len(self.states) - 1
        self.transition = 'LEFT'
        self.helpMenu = HelpGraph(self.states[self.nextState], self.unit, gameStateObj)
        self.left_arrow.pulse()
        self.switch_logo(self.states[self.nextState])

    def move_right(self, gameStateObj):
        GC.SOUNDDICT['Status_Page_Change'].play()
        self.last_fluid = Engine.get_time()
        self.nextState = (self.currentState + 1) if self.currentState < len(self.states) - 1 else 0
        self.transition = 'RIGHT'
        self.helpMenu = HelpGraph(self.states[self.nextState], self.unit, gameStateObj)
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
            index = cf.CONSTANTS['stat_names'].index(stat)
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
        # menu_surf = MenuFunctions.CreateBaseMenuSurf((GC.WINWIDTH//2 + 8, 24))
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
        index_of_mainweapon = None
        if self.unit.getMainWeapon(): # Ony highlight if unit has weapon
            for index, item in enumerate(self.unit.items): # find first index of mainweapon
                if item.weapon:
                    index_of_mainweapon = index
                    break
            highlightSurf = GC.IMAGESDICT['EquipmentHighlight']
            menu_surf.blit(highlightSurf, (8, 32 + 16 * index_of_mainweapon))

        # Blit items
        for index, item in enumerate(self.unit.items):
            item.draw(menu_surf, (8, index*GC.TILEHEIGHT + 24)) # Draws icon
            if item.droppable:
                namefont = GC.FONT['text_green']
                usefont = GC.FONT['text_green']
            elif self.unit.canWield(item):
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
            rng = self.unit.getMainWeapon().get_range_string()
            dam = str(self.unit.damage(gameStateObj))
            acc = str(self.unit.accuracy(gameStateObj))
        else:
            rng = '--'
            dam = '--'
            acc = '--'
        avo = str(self.unit.avoid(gameStateObj))
        atkspd = str(self.unit.attackspeed())
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
        elif status.active and status.active.required_charge > 0:
            output = str(status.active.current_charge) + '/' + str(status.active.required_charge)
            GC.FONT['text_blue'].blit(output, menu_surf, (pos[0] + 16, pos[1]))
        elif status.automatic and status.automatic.required_charge > 0:
            output = str(status.automatic.current_charge) + '/' + str(status.automatic.required_charge)
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

class HelpGraph(object):
    def __init__(self, state, unit, gameStateObj):
        self.help_boxes = {}
        self.unit = unit
        self.current = None

        if state == 'Personal Data':
            self.populate_personal_data()
            self.initial = "Strength"
        elif state == 'Personal Growths':
            self.populate_personal_data(growths=True)
            self.initial = "Strength"
        elif state == 'Equipment':
            self.populate_equipment()
            if self.unit.items:
                self.initial = "Item0"
            else:
                self.initial = "Unit Desc"
        elif state == 'Support & Status':
            self.populate_status(gameStateObj)
            if [wexp for wexp in self.unit.wexp if wexp > 0]:
                self.initial = "Wexp0"
            else:
                self.initial = "Unit Desc"

    def populate_personal_data(self, growths=False):
        self.help_boxes["Strength"] = Help_Box("Strength", (88, 26), Help_Dialog(cf.WORDS['STR_desc']))
        self.help_boxes["Magic"] = Help_Box("Magic", (88, GC.TILEHEIGHT + 26), Help_Dialog(cf.WORDS['MAG_desc']))
        self.help_boxes["Skill"] = Help_Box("Skill", (88, GC.TILEHEIGHT*2 + 26), Help_Dialog(cf.WORDS['SKL_desc']))
        self.help_boxes["Speed"] = Help_Box("Speed", (88, GC.TILEHEIGHT*3 + 26), Help_Dialog(cf.WORDS['SPD_desc']))
        self.help_boxes["Defense"] = Help_Box("Defense", (88, GC.TILEHEIGHT*4 + 26), Help_Dialog(cf.WORDS['DEF_desc']))
        self.help_boxes["Resistance"] = Help_Box("Resistance", (88, GC.TILEHEIGHT*5 + 26), Help_Dialog(cf.WORDS['RES_desc']))

        self.help_boxes["Luck"] = Help_Box("Luck", (152, 26), Help_Dialog(cf.WORDS['LCK_desc']))
        self.help_boxes["Movement"] = Help_Box("Movement", (152, GC.TILEHEIGHT + 26), Help_Dialog(cf.WORDS['MOV_desc']))
        self.help_boxes["Con"] = Help_Box("Con", (152, GC.TILEHEIGHT*2 + 26), Help_Dialog(cf.WORDS['CON_desc']))
        if growths:
            self.help_boxes["Aid"] = Help_Box("Aid", (152, GC.TILEHEIGHT*3 + 26), Help_Dialog(cf.WORDS['HP_desc']))
        else:
            self.help_boxes["Aid"] = Help_Box("Aid", (152, GC.TILEHEIGHT*3 + 26), Help_Dialog(cf.WORDS['Aid_desc']))
        self.help_boxes["Traveler"] = Help_Box("Traveler", (152, GC.TILEHEIGHT*4 + 26), Help_Dialog(cf.WORDS['Trv_desc']))
        if cf.CONSTANTS['support']:
            self.help_boxes["Affin"] = Help_Box("Affin", (152, GC.TILEHEIGHT*5 + 26), Help_Dialog(cf.WORDS['Affin_desc']))
        else:
            self.help_boxes["Affin"] = Help_Box("Affin", (152, GC.TILEHEIGHT*5 + 26), Help_Dialog(cf.WORDS['Rat_desc']))

        # Connect personal data
        self.help_boxes["Strength"].down = "Magic"
        self.help_boxes["Magic"].down = "Skill"
        self.help_boxes["Skill"].down = "Speed"
        self.help_boxes["Speed"].down = "Defense"
        self.help_boxes["Defense"].down = "Resistance"
        self.help_boxes["Resistance"].up = "Defense"
        self.help_boxes["Magic"].up = "Strength"
        self.help_boxes["Skill"].up = "Magic"
        self.help_boxes["Speed"].up = "Skill"
        self.help_boxes["Defense"].up = "Speed"
        self.help_boxes["Strength"].right = "Luck"
        self.help_boxes["Magic"].right = "Movement"
        self.help_boxes["Skill"].right = "Con"
        self.help_boxes["Speed"].right = "Aid"
        self.help_boxes["Defense"].right = "Traveler"
        self.help_boxes["Resistance"].right = "Affin"

        self.help_boxes["Luck"].down = "Movement"
        self.help_boxes["Movement"].down = "Con"
        self.help_boxes["Con"].down = "Aid"
        self.help_boxes["Aid"].down = "Traveler"
        self.help_boxes["Traveler"].down = "Affin"
        self.help_boxes["Movement"].up = "Luck"
        self.help_boxes["Con"].up = "Movement"
        self.help_boxes["Aid"].up = "Con"
        self.help_boxes["Traveler"].up = "Aid"
        self.help_boxes["Affin"].up = "Traveler"
        self.help_boxes["Luck"].left = "Strength"
        self.help_boxes["Movement"].left = "Magic"
        self.help_boxes["Con"].left = "Skill"
        self.help_boxes["Aid"].left = "Speed"
        self.help_boxes["Traveler"].left = "Defense"
        self.help_boxes["Affin"].left = "Resistance"

        # Populate Class Skills
        skills = [status for status in self.unit.status_effects if status.class_skill]

        for index, skill in enumerate(skills):
            if skill.active:
                description = skill.desc + ' ' + str(skill.active.current_charge) + '/' + str(skill.active.required_charge)
            elif skill.automatic:
                description = skill.desc + ' ' + str(skill.automatic.current_charge) + '/' + str(skill.automatic.required_charge)
            else:
                description = skill.desc
            left_pos = index*((GC.WINWIDTH - 96)//max(cf.CONSTANTS['num_skills'], len(skills))) + 92
            self.help_boxes["Skill"+str(index)] = Help_Box("Skill"+str(index), (left_pos, GC.WINHEIGHT - 32), Help_Dialog(description, name=skill.name))

        for i in range(len(skills)):
            self.help_boxes["Skill"+str(i)].up = "Resistance"
            self.help_boxes["Skill"+str(i)].right = ("Skill"+str(i+1)) if i < (len(skills) - 1) else None
            self.help_boxes["Skill"+str(i)].left = ("Skill"+str(i-1)) if i > 0 else None

        self.populate_info_menu_default()

        if skills:
            self.help_boxes["Skill0"].left = "HP"
            self.help_boxes["HP"].right = "Skill0"
            self.help_boxes["Experience"].right = "Skill0"
            self.help_boxes["Resistance"].down = "Skill0"
            self.help_boxes["Affin"].down = "Skill0"

        # Connect default with personal data
        self.help_boxes["Unit Desc"].right = "Speed"
        self.help_boxes["Class Desc"].right = "Resistance"
        self.help_boxes["Resistance"].left = "Class Desc"
        self.help_boxes["Defense"].left = "Unit Desc"
        self.help_boxes["Speed"].left = "Unit Desc"
        self.help_boxes["Magic"].left = "Unit Desc"
        self.help_boxes["Strength"].left = "Unit Desc"
        self.help_boxes["Skill"].left = "Unit Desc"

    def populate_equipment(self):
        for index, item in enumerate(self.unit.items):
            pos = (88, GC.TILEHEIGHT*index + 24)
            self.help_boxes["Item"+str(index)] = Help_Box("Item"+str(index), pos, item.get_help_box())

        self.help_boxes["Atk"] = Help_Box("Atk", (100, GC.WINHEIGHT - 40), Help_Dialog(cf.WORDS['Atk_desc']))
        self.help_boxes["Hit"] = Help_Box("Hit", (100, GC.WINHEIGHT - 24), Help_Dialog(cf.WORDS['Hit_desc']))
        self.help_boxes["Rng"] = Help_Box("Rng", (158, GC.WINHEIGHT - 56), Help_Dialog(cf.WORDS['Rng_desc']))
        self.help_boxes["AS"] = Help_Box("AS", (158, GC.WINHEIGHT - 40), Help_Dialog(cf.WORDS['AS_desc']))
        self.help_boxes["Avoid"] = Help_Box("Avoid", (158, GC.WINHEIGHT - 24), Help_Dialog(cf.WORDS['Avoid_desc']))

        # Add connections
        for i in range(len(self.unit.items)):
            self.help_boxes["Item"+str(i)].down = ("Item"+str(i+1)) if i < (len(self.unit.items) - 1) else None
            self.help_boxes["Item"+str(i)].up = ("Item"+str(i-1)) if i > 0 else None

        if self.unit.items:
            self.help_boxes["Item" + str(len(self.unit.items) - 1)].down = "Atk"

        self.help_boxes["Atk"].right = "AS"
        self.help_boxes["Atk"].down = "Hit"
        self.help_boxes["Atk"].up = ("Item"+str(len(self.unit.items) - 1)) if self.unit.items else "Unit Desc"
        self.help_boxes["Atk"].left = "Experience"

        self.help_boxes["Hit"].left = "HP"
        self.help_boxes["Hit"].right = "Avoid"
        self.help_boxes["Hit"].up = "Atk"

        self.help_boxes["Avoid"].left = "Hit"
        self.help_boxes["Avoid"].up = "AS"

        self.help_boxes["AS"].left = "Atk"
        self.help_boxes["AS"].up = "Rng"
        self.help_boxes["AS"].down = "Avoid"

        self.help_boxes["Rng"].left = "Atk"
        self.help_boxes["Rng"].up = ("Item"+str(len(self.unit.items) - 1)) if self.unit.items else "Unit Desc"
        self.help_boxes["Rng"].down = "AS"

        self.populate_info_menu_default()

        # Connect default with equipment
        for i in range(len(self.unit.items)):
            self.help_boxes["Item"+str(i)].left = "Unit Desc"

        if self.unit.items:
            self.help_boxes['Unit Desc'].up = "Item0"
            self.help_boxes['Unit Desc'].right = "Item" + str(min(3, len(self.unit.items) - 1))

        self.help_boxes["Class Desc"].right = "Atk"
        self.help_boxes["Experience"].right = "Atk"
        self.help_boxes["HP"].right = "Hit"

    def populate_status(self, gameStateObj):
        # Populate Weapon Exp
        good_weapons = [wexp for wexp in self.unit.wexp if wexp > 0]
        for index, wexp in enumerate(good_weapons):
            self.help_boxes["Wexp"+str(index)] = Help_Box("Wexp"+str(index), (92 + 60*index, 26), Help_Dialog("Weapon Rank: %s"%(wexp)))

        for i in range(len(good_weapons)):
            self.help_boxes["Wexp"+str(i)].right = ("Wexp"+str(i+1)) if i < (len(good_weapons) - 1) else None
            self.help_boxes["Wexp"+str(i)].left = ("Wexp"+str(i-1)) if i > 0 else None

        # Non-class skills
        statuses = [status for status in self.unit.status_effects if not (status.class_skill or status.hidden)]

        for index, status in enumerate(statuses):
            left_pos = index*((GC.WINWIDTH - 96)//max(5, len(statuses))) + 92
            self.help_boxes["Status"+str(index)] = Help_Box("Status"+str(index), (left_pos, GC.WINHEIGHT - 20), Help_Dialog(status.desc, name=status.name))

        # Connect them together
        for i in range(len(statuses)):
            self.help_boxes["Status"+str(i)].right = ("Status"+str(i+1)) if i < (len(statuses) - 1) else None
            self.help_boxes["Status"+str(i)].left = ("Status"+str(i-1)) if i > 0 else None

        # Supports
        if gameStateObj.support:
            supports = gameStateObj.support.get_supports(self.unit.id)
            supports = [support for support in supports if support[2]]
        else:
            supports = []
        for index, support in enumerate(supports):
            affinity = support[1]
            desc = affinity.desc
            pos = (96, 16*index + 48)
            self.help_boxes["Support"+str(index)] = Help_Box("Support"+str(index), pos, Help_Dialog(desc))

        # Connect supports
        for i in range(len(supports)):
            self.help_boxes["Support"+str(i)].down = ("Support"+str(i+1)) if i < (len(supports) - 1) else None
            self.help_boxes["Support"+str(i)].up = ("Support"+str(i-1)) if i > 0 else None

        self.populate_info_menu_default()
        
        for i in range(len(supports)):
            self.help_boxes["Support"+str(i)].left = "Unit Desc"

        if good_weapons:
            self.help_boxes["Wexp0"].left = "Unit Desc"
            self.help_boxes['Unit Desc'].up = "Wexp0"
        if good_weapons and supports:
            for i in range(len(good_weapons)):
                self.help_boxes["Wexp"+str(i)].down = "Support0"
            self.help_boxes["Support0"].up = "Wexp0"
        elif good_weapons and statuses:
            for i in range(len(good_weapons)):
                self.help_boxes["Wexp"+str(i)].down = "Status0"
            for i in range(len(statuses)):
                self.help_boxes["Status"+str(i)].up = "Wexp0"
        if statuses and supports:
            for i in range(len(statuses)):
                self.help_boxes["Status"+str(i)].up = "Support"+str(len(supports)-1)
            self.help_boxes["Support" + str(len(supports)-1)].down = "Status0"
        if supports:
            self.help_boxes['Unit Desc'].right = "Support" + str(min(3, len(statuses) - 1))
            self.help_boxes['Experience'].right = "Support" + str(min(3, len(statuses) - 1))
            self.help_boxes['HP'].right = "Support" + str(min(3, len(statuses) - 1))
        elif good_weapons:
            self.help_boxes['Unit Desc'].right = "Wexp0"
            self.help_boxes['Experience'].right = "Wexp0"
            self.help_boxes['HP'].right = "Wexp0"

    def populate_info_menu_default(self):
        self.help_boxes["Unit Desc"] = Help_Box("Unit Desc", (16, 82), Help_Dialog(self.unit.desc))
        self.help_boxes["Class Desc"] = Help_Box("Class Desc", (-8, 107), Help_Dialog(ClassData.class_dict[self.unit.klass]['desc']))
        self.help_boxes["Unit Level"] = Help_Box("Unit Level", (-8, 123), Help_Dialog(cf.WORDS['Level_desc']))
        self.help_boxes["Experience"] = Help_Box("Experience", (22, 123), Help_Dialog(cf.WORDS['Exp_desc']))
        self.help_boxes["HP"] = Help_Box("HP", (-8, 139), Help_Dialog(cf.WORDS['HP_desc']))

        # Connections
        self.help_boxes["Unit Desc"].down = "Class Desc"
        self.help_boxes["Class Desc"].up = "Unit Desc"
        self.help_boxes["Class Desc"].down = "Unit Level"
        self.help_boxes["Unit Level"].up = "Class Desc"
        self.help_boxes["Unit Level"].right = "Experience"
        self.help_boxes["Unit Level"].down = "HP"
        self.help_boxes["Experience"].left = "Unit Level"
        self.help_boxes["Experience"].up = "Class Desc"
        self.help_boxes["Experience"].down = "HP"
        self.help_boxes["HP"].up = "Unit Level"

class Help_Box(Counters.CursorControl):
    def __init__(self, name, cursor_position, help_surf):
        self.name = name
        self.cursor_position = cursor_position
        self.help_dialog = help_surf
        # Determine help_topleft position
        if self.cursor_position[0] + self.help_dialog.get_width() > GC.WINWIDTH:
            helpleft = GC.WINWIDTH - self.help_dialog.get_width() - 8
        else:
            helpleft = self.cursor_position[0] - min(GC.TILEWIDTH*2, self.cursor_position[0]) # Don't go to far to the left
        if self.cursor_position[1] > GC.WINHEIGHT//2 + 8:
            helptop = self.cursor_position[1] - self.help_dialog.get_height()
        else:
            helptop = self.cursor_position[1] + 16
        self.help_topleft = (helpleft, helptop)

        self.left = None
        self.right = None
        self.up = None
        self.down = None

        Counters.CursorControl.__init__(self)

    def draw(self, surf, info=True):
        surf.blit(self.cursor, (self.cursor_position[0] + self.cursorAnim[self.cursorCounter], self.cursor_position[1]))
        if info:
            self.help_dialog.draw(surf, self.help_topleft)

class Help_Dialog_Base(object):
    def get_width(self):
        return self.help_surf.get_width()

    def get_height(self):
        return self.help_surf.get_height()

    def handle_transition_in(self, time, h_surf):
        # Handle transitioning in
        if self.transition_in:
            perc = (time - self.start_time) / 130.
            if perc >= 1:
                self.transition_in = False
            else:
                h_surf = Engine.transform_scale(h_surf, (int(perc*h_surf.get_width()), int(perc*h_surf.get_height())))
                # h_surf = Image_Modification.flickerImageTranslucent255(h_surf, perc*255)
        return h_surf

    def set_transition_out(self):
        self.transition_out = Engine.get_time()

    def handle_transition_out(self, time, h_surf):
        # Handle transitioning in
        if self.transition_out:
            perc = 1. - ((time - self.transition_out) / 100.)
            if perc <= 0:
                self.transition_out = -1
                perc = 0.1
            h_surf = Engine.transform_scale(h_surf, (int(perc*h_surf.get_width()), int(perc*h_surf.get_height())))
            # h_surf = Image_Modification.flickerImageTranslucent255(h_surf, perc*255)
        return h_surf

    def final_draw(self, surf, pos, time, help_surf):
        # Draw help logo
        h_surf = Engine.copy_surface(self.h_surf)
        h_surf.blit(help_surf, (0, 3))
        h_surf.blit(GC.IMAGESDICT['HelpLogo'], (9, 0))

        if self.transition_in:
            h_surf = self.handle_transition_in(time, h_surf)
        elif self.transition_out:
            h_surf = self.handle_transition_out(time, h_surf)

        surf.blit(h_surf, pos)

class Help_Dialog(Help_Dialog_Base):
    def __init__(self, description, num_lines=2, name=False):
        self.font = GC.FONT['convo_black']
        self.name = name
        self.last_time = self.start_time = 0
        self.transition_in = self.transition_out = False
        # Set up variables needed for algorithm
        description_length = self.font.size(description)[0]
        # Hard set num_lines if description is very short.
        if len(description) < 24:
            num_lines = 1

        lines = []
        for line in range(num_lines):
            lines.append([])
        length_reached = False # Whether we've reached over the length of the description
        which_line = 0 # Which line are we reading
        # Place description into balanced size lines
        for character in description:
            if length_reached and character == ' ':
                which_line += 1
                length_reached = False
                continue
            lines[which_line].append(character)
            length_so_far = self.font.size(''.join(lines[which_line]))[0]
            if length_so_far > description_length//num_lines:
                length_reached = True
            elif length_so_far > GC.WINWIDTH - 8:
                length_reached = True
        # Reform strings
        self.strings = []
        for line in lines:
            self.strings.append(''.join(line)) 
        # Find the greater of the two lengths
        greater_line_len = max([self.font.size(string)[0] for string in self.strings])

        size_x = greater_line_len + 24
        self.width = size_x
        if name:
            num_lines += 1
        size_y = self.font.height * num_lines + 16

        self.help_surf = MenuFunctions.CreateBaseMenuSurf((size_x, size_y), 'MessageWindowBackground')
        self.h_surf = Engine.create_surface((size_x, size_y + 3), transparent=True)

    def draw(self, surf, pos):
        time = Engine.get_time()
        if time > self.last_time + 1000:  # If it's been at least a second since last update
            self.start_time = time - 16
        self.last_time = time

        help_surf = Engine.copy_surface(self.help_surf)
        # Now draw
        if self.name:
            self.font.blit(self.name, help_surf, (8, 8))

        if cf.OPTIONS['Text Speed'] > 0:
            num_characters = int(2*(time - self.start_time)/float(cf.OPTIONS['Text Speed']))
        else:
            num_characters = 1000
        for index, string in enumerate(self.strings):
            if num_characters > 0:
                self.font.blit(string[:num_characters], help_surf, (8, self.font.height*index + 8 + (16 if self.name else 0)))
                num_characters -= len(string)
    
        self.final_draw(surf, pos, time, help_surf)
