#! usr/bin/env python

# Imports
from imagesDict import getImages
from GlobalConstants import *
from configuration import *
import CustomObjects, ItemMethods, MenuFunctions, Image_Modification, Engine, InputManager, StateMachine, Counters

class InfoMenu(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # Set unit to be displayed
            self.unit = gameStateObj.info_menu_struct['chosen_unit']
            if not gameStateObj.info_menu_struct['scroll_units']:
                self.scroll_units = [unit for unit in gameStateObj.allunits if (not self.unit.position or unit.position) and not unit.dead and unit.team == self.unit.team]
            else:
                self.scroll_units = gameStateObj.info_menu_struct['scroll_units']
            self.scroll_units = sorted(self.scroll_units, key=lambda unit:unit.team)

            # The current state
            self.states = [WORDS["Equipment"], WORDS["Personal Data"], WORDS["Skills & Status"]]
            if CONSTANTS['support'] and self.unit.team == 'player':
                self.states.append(WORDS["Supports"])
            self.currentState = min(gameStateObj.info_menu_struct['current_state'], len(self.states) - 1)

            self.reset_surfs()
            self.growth_flag = False

            self.fluid_helper = InputManager.FluidScroll(200, slow_speed=0)

            self.helpMenu = HelpGraph(self.states[self.currentState], self.unit, metaDataObj, gameStateObj)
            # Counters
            self.background = MenuFunctions.MovingBackground(IMAGESDICT['StatusBackground'])
            #self.background = MenuFunctions.MovieBackground('fog', 33) # This looks odd in comparison...
            self.arrowCounter = 0
            self.lastArrowUpdate = Engine.get_time()
            self.arrowSpeed = 125
            self.scroll_offset = 0

            self.hold_flag = gameStateObj.info_menu_struct['one_unit_only']

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
        SOUNDDICT['Select 4'].play()
        gameStateObj.info_menu_struct['current_state'] = self.currentState
        if not gameStateObj.info_menu_struct['one_unit_only'] and self.unit.position:
            gameStateObj.cursor.setPosition(self.unit.position, gameStateObj)
        gameStateObj.stateMachine.changeState('transition_pop')

    def take_input(self, eventList, gameStateObj, metaDataObj):
         ### Get events
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        currentTime = Engine.get_time()

        if self.helpMenu.current:
            if event == 'INFO' or event == 'BACK':
                SOUNDDICT['Select 4'].play() # TODO. Needs different sound
                self.helpMenu.current = None
            if 'RIGHT' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].right:
                    SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].right
            elif 'LEFT' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].left:
                    SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].left
            if 'UP' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].up:
                    SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].up
            elif 'DOWN' in directions:
                if self.helpMenu.help_boxes[self.helpMenu.current].down:
                    SOUNDDICT['Select 6'].play()
                    self.helpMenu.current = self.helpMenu.help_boxes[self.helpMenu.current].down
        else:
            if event == 'INFO':
                SOUNDDICT['Select 1'].play() # TODO. Needs different sound
                self.helpMenu.current = self.helpMenu.initial
            elif event == 'SELECT':
                if self.states[self.currentState] == WORDS["Personal Data"] and self.unit.team == "player":
                    SOUNDDICT['Select 3'].play()
                    self.growth_flag = not self.growth_flag
            elif event == 'BACK':
                self.back(gameStateObj)
                return
            if 'RIGHT' in directions:
                self.move_right(gameStateObj, metaDataObj)
            elif 'LEFT' in directions:
                self.move_left(gameStateObj, metaDataObj)
            elif 'DOWN' in directions:
                self.last_fluid = currentTime
                if self.hold_flag:
                    SOUNDDICT['Select 2'].play()
                else:
                    SOUNDDICT['Attack Miss 2'].play()
                    index = self.scroll_units.index(self.unit)
                    if index < len(self.scroll_units) - 1:
                        self.unit = self.scroll_units[index+1]
                    else:
                        self.unit = self.scroll_units[0]
                    self.scroll_offset = 9
                    self.reset_surfs()
                    self.helpMenu = HelpGraph(self.states[self.currentState], self.unit, metaDataObj, gameStateObj)
            elif 'UP' in directions:
                self.last_fluid = currentTime
                if self.hold_flag:
                    SOUNDDICT['Select 2'].play()
                else:
                    SOUNDDICT['Attack Miss 2'].play()
                    index = self.scroll_units.index(self.unit)
                    if index > 0:
                        self.unit = self.scroll_units[index - 1]
                    else:
                        self.unit = self.scroll_units[-1] # last unit
                    self.scroll_offset = -9
                    self.reset_surfs()
                    self.helpMenu = HelpGraph(self.states[self.currentState], self.unit, metaDataObj, gameStateObj)

    def move_left(self, gameStateObj, metaDataObj):
        SOUNDDICT['Select 3'].play()
        self.last_fluid = Engine.get_time()
        self.currentState = (self.currentState - 1) if self.currentState > 0 else len(self.states) - 1
        self.helpMenu = HelpGraph(self.states[self.currentState], self.unit, metaDataObj, gameStateObj)

    def move_right(self, gameStateObj, metaDataObj):
        SOUNDDICT['Select 3'].play()
        self.last_fluid = Engine.get_time()
        self.currentState = (self.currentState + 1) if self.currentState < len(self.states) - 1 else 0
        self.helpMenu = HelpGraph(self.states[self.currentState], self.unit, metaDataObj, gameStateObj)

    def update(self, gameStateObj, metaDataObj):
        if self.helpMenu.current:
            self.helpMenu.help_boxes[self.helpMenu.current].update()

        if self.scroll_offset > 0:
            self.scroll_offset -= 1
        if self.scroll_offset < 0:
            self.scroll_offset += 1

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        surf.fill(colorDict['black'])
        self.background.draw(surf)
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
        surf.blit(self.portrait_surf, (0,16*self.scroll_offset))

        # Blit the unit's active sprite
        activeSpriteSurf = self.unit.sprite.create_image('active')
        pos = (74 - max(0, (activeSpriteSurf.get_width() - 16)/2), \
               WINHEIGHT - TILEHEIGHT*3.5 + 18 - max(0, (activeSpriteSurf.get_width() - 16)/2))
        surf.blit(activeSpriteSurf, (pos[0], pos[1] + 16*self.scroll_offset))

    def create_portrait(self):
        UnitInfoSurface = Engine.create_surface((7*WINWIDTH/16, WINHEIGHT), transparent=True)
        UnitInfoSurface = UnitInfoSurface.convert_alpha()
        # Blit Background of Character Portrait
        PortraitBGSurf = IMAGESDICT['PortraitBackground']
        UnitInfoSurface.blit(PortraitBGSurf, (4, TILEHEIGHT/2))
        # Blit Character Portrait for the chosen unit
        # 80 x 72 is what fits in the portrait slot
        # 96 x 80 is the actual size of a big_portrait
        PortraitSurf = Engine.subsurface(self.unit.bigportrait, ((self.unit.bigportrait.get_width() - 80)/2, 0, 80, 72))
        UnitInfoSurface.blit(PortraitSurf, (12, TILEHEIGHT/2+4))
        # Blit Background for the simple info block beneath the Character Portrait
        InfoBlockSurf = IMAGESDICT['TransparentBackground']
        UnitInfoSurface.blit(InfoBlockSurf, (0, WINHEIGHT - TILEHEIGHT*3.5))
        # Blit background for the unit Name banner beneath the Character Portrait
        PortraitNameSurf = IMAGESDICT['PortraitName']
        p_left = PortraitBGSurf.get_width()/2 + 4 - PortraitNameSurf.get_width()/2
        p_top = TILEHEIGHT/2 + PortraitBGSurf.get_height() - 7
        UnitInfoSurface.blit(PortraitNameSurf, (p_left, p_top))
        # Blit the name on top of the unit name banner
        NameSize = FONT['text_white'].size(self.unit.name)
        position = (p_left + PortraitNameSurf.get_width()/2 - NameSize[0]/2, p_top + PortraitNameSurf.get_height()/2 - NameSize[1]/2)
        FONT['text_white'].blit(self.unit.name, UnitInfoSurface, position) 
        # Blit the unit's class on the simple info block
        FONT['text_white'].blit(self.unit.klass.replace('_', ' '), UnitInfoSurface, (TILEWIDTH/2, WINHEIGHT - TILEHEIGHT * 3.25 - 1))
        # Blit the unit's level on the simple info block
        LevelSize = FONT['text_blue'].size(str(self.unit.level))
        position = (TILEWIDTH*2.5 - LevelSize[0] - 1, WINHEIGHT - TILEHEIGHT*2.5)
        FONT['text_blue'].blit(str(self.unit.level), UnitInfoSurface, position)
        # Blit the unit's exp on the simple info block
        ExpSize = FONT['text_blue'].size(str(self.unit.exp))
        position = (TILEWIDTH*4 - 2 - ExpSize[0], WINHEIGHT - TILEHEIGHT*2.5)
        FONT['text_blue'].blit(str(self.unit.exp), UnitInfoSurface, position)
        # Blit the unit's current hp on the simple info block
        current_hp = str(self.unit.currenthp)
        if len(current_hp) > 2:
            current_hp = '??'
        CurrentHPSize = FONT['text_blue'].size(current_hp)
        position = (TILEWIDTH*2.5 - CurrentHPSize[0], WINHEIGHT - TILEHEIGHT*1.5)
        FONT['text_blue'].blit(current_hp, UnitInfoSurface, position)
        # Blit the unit's max hp on the simple info block
        max_hp = str(self.unit.stats['HP'])
        if len(max_hp) > 2:
            max_hp = '??'
        MaxHPSize = FONT['text_blue'].size(max_hp)
        position = (TILEWIDTH*4 - 2 - MaxHPSize[0], WINHEIGHT - TILEHEIGHT*1.5)
        FONT['text_blue'].blit(max_hp, UnitInfoSurface, position)
        # Blit the white status platform
        PlatSurf = IMAGESDICT['StatusPlatform']
        pos = (InfoBlockSurf.get_width() - 2 - PlatSurf.get_width(), WINHEIGHT - TILEHEIGHT*3.5 + InfoBlockSurf.get_height() + 2 - PlatSurf.get_width())
        UnitInfoSurface.blit(PlatSurf, pos)
        return UnitInfoSurface

    def drawTopArrows(self, surf):
        currentTime = Engine.get_time()
        #--Increment arrow counter
        if currentTime - self.lastArrowUpdate > self.arrowSpeed:
            self.arrowCounter += 1
            if self.arrowCounter >= 6: # Num arrows - 1
                self.arrowCounter = 0
            self.lastArrowUpdate = currentTime
        ScrollArrowSurf = IMAGESDICT['PageArrows']
        LeftScrollArrow = Engine.subsurface(ScrollArrowSurf, (8*self.arrowCounter,0,8,16))
        #-- Flip horizontally
        RightScrollArrow = Engine.flip_horiz(LeftScrollArrow)
        surf.blit(LeftScrollArrow, (108, 16*self.scroll_offset + 1))
        surf.blit(RightScrollArrow, (WINWIDTH - 13, 16*self.scroll_offset + 1))

    def drawSlide(self, surf, gameStateObj, metaDataObj):
        # blit title of menu
        name = self.states[self.currentState]
        if self.growth_flag and name == WORDS["Personal Data"]:
            name = WORDS["Personal Growths"]
        StateSize = FONT['text_yellow'].size(name)
        position = (172 - StateSize[0]/2, TILEHEIGHT/2 - StateSize[1]/2 + 16*self.scroll_offset)
        FONT['text_yellow'].blit(name, surf, position)

        self.drawTopArrows(surf)

        if self.states[self.currentState] == WORDS["Personal Data"]:
            if self.growth_flag:
                if not self.growths_surf:
                    self.growths_surf = self.create_growths_surf(gameStateObj)
                self.draw_growths_surf(surf)
            else:
                if not self.personal_data_surf:
                    self.personal_data_surf = self.create_personal_data_surf(gameStateObj, metaDataObj)
                self.draw_personal_data_surf(surf)
            if not self.wexp_surf:
                self.wexp_surf = self.create_wexp_surf()
            self.draw_wexp_surf(surf)
        elif self.states[self.currentState] == WORDS['Equipment']:
            if not self.equipment_surf:
                self.equipment_surf = self.create_equipment_surf(gameStateObj)
            self.draw_equipment_surf(surf)
        elif self.states[self.currentState] == WORDS["Supports"]:
            if not self.support_surf:
                self.support_surf = self.create_support_surf(gameStateObj)
            self.draw_support_surf(surf)
        elif self.states[self.currentState] == WORDS['Skills & Status']: 
            if not self.skill_surf:
                self.skill_surf = self.create_skill_surf()
            self.draw_skill_surf(surf)
            if not self.class_skill_surf:
                self.class_skill_surf = self.create_class_skill_surf()
            self.draw_class_skill_surf(surf)
    
    def create_personal_data_surf(self, gameStateObj, metaDataObj):
        # Menu Background
        menu_size = (WINWIDTH/2+8, WINHEIGHT - TILEHEIGHT * 3)
        menu_surf = MenuFunctions.CreateBaseMenuSurf(menu_size)

        fgs_mid = IMAGESDICT['StatGrooveFill']

        stats = [self.unit.stats['STR'].base_stat, self.unit.stats['MAG'].base_stat, self.unit.stats['SKL'].base_stat, self.unit.stats['SPD'].base_stat, self.unit.stats['DEF'].base_stat, self.unit.stats['RES'].base_stat]
        max_stats = metaDataObj['class_dict'][self.unit.klass]['max']
        maximum = [max_stats[1], max_stats[2], max_stats[3], max_stats[4], max_stats[6], max_stats[7]]
        offset = FONT['text_yellow'].size('Mag')[0] + 4
        # For each left stat
        for index, stat in enumerate(stats):
            #print(index, stat/float(maximum[index]))
            self.build_groove(menu_surf, (offset - 1, TILEHEIGHT*1.1*index + 10), int(maximum[index]/float(CONSTANTS['max_stat'])*44), stat/float(maximum[index]))

        self.blit_stat_titles(menu_surf)

        for index, stat in enumerate(stats):
            if stat >= maximum[index]:
                font = FONT['text_green']
            else:
                font = FONT['text_blue']
            font.blit(str(stat), menu_surf, (43 - font.size(str(stat))[0],TILEHEIGHT*1.1*index + 4))
        FONT['text_blue'].blit(str(self.unit.stats['LCK'].base_stat), menu_surf, (108 - FONT['text_blue'].size(str(self.unit.stats['LCK'].base_stat))[0], 4)) # Blit Outlined Luck
        FONT['text_blue'].blit(str(self.unit.stats['MOV'].base_stat), menu_surf, (108 - FONT['text_blue'].size(str(self.unit.stats['MOV'].base_stat))[0], TILEHEIGHT*1.1+4)) # Blit Outlined Movement
        FONT['text_blue'].blit(str(self.unit.stats['CON'].base_stat), menu_surf, (108 - FONT['text_blue'].size(str(self.unit.stats['CON'].base_stat))[0], TILEHEIGHT*2.2+4)) # Blit Outlined Constitution
        FONT['text_blue'].blit(str(self.unit.strTRV), menu_surf, (92, TILEHEIGHT*4.4+4)) # Blit Outlined Traveler
        FONT['text_blue'].blit(str(self.unit.getAid()), menu_surf, (108 - FONT['text_blue'].size(str(self.unit.getAid()))[0], TILEHEIGHT*3.3+4)) # Blit Outlined Aid

        for index, stat in enumerate([self.unit.stats['STR'], self.unit.stats['MAG'], self.unit.stats['SKL'], self.unit.stats['SPD'], self.unit.stats['DEF'], self.unit.stats['RES']]):
            output = ""
            if stat.bonuses > 0:
                output = "+" + str(stat.bonuses)
                FONT['small_green'].blit(output, menu_surf, (44, 16*1.1*index+4))
            elif stat.bonuses < 0:
                output = str(stat.bonuses)
                FONT['small_red'].blit(output, menu_surf, (44, 16*1.1*index+4))
        for index, stat in enumerate([self.unit.stats['LCK'], self.unit.stats['MOV'], self.unit.stats['CON']]):
            output = ""
            if stat.bonuses > 0:
                output = "+" + str(stat.bonuses)
                FONT['small_green'].blit(output, menu_surf, (menu_surf.get_width()/2 + 44, 16*1.1*index+4))
            elif stat.bonuses < 0:
                output = str(stat.bonuses)
                FONT['small_red'].blit(output, menu_surf, (menu_surf.get_width()/2 + 44, 16*1.1*index+4))

            
        # Handle MountSymbols
        """if 'Dragon' in self.unit.tags:
            AidSurf = Engine.subsurface(ICONDICT['Aid'], (0,48,16,16))
        elif self.unit.has_flying():
            AidSurf = Engine.subsurface(ICONDICT['Aid'], (0,32,16,16))
        elif 'Mounted' in self.unit.tags:
            AidSurf = Engine.subsurface(ICONDICT['Aid'], (0,16,16,16))
        else:
            AidSurf = Engine.subsurface(ICONDICT['Aid'], (0,0,16,16))
        AidRect = AidSurf.get_rect()
        AidRect.topleft = (menu_surf.get_width()/2 + 38, TILEHEIGHT*3.3 + 4)
        menu_surf.blit(AidSurf, AidRect)"""

        # Handle Affinity
        if CONSTANTS['support'] and self.unit.name in gameStateObj.support.node_dict:
            gameStateObj.support.node_dict[self.unit.name].affinity.draw(menu_surf, (menu_surf.get_width()/2 + 32, TILEHEIGHT*5.5 + 4))
        else:
            FONT['text_blue'].blit('--', menu_surf, (94, TILEHEIGHT*5.5 + 4)) # Blit No Affinity

        return menu_surf

    def blit_stat_titles(self, menu_surf, growths=False):
        FONT['text_yellow'].blit(WORDS['STR'], menu_surf, (4,4)) # Blit Outlined Strength
        FONT['text_yellow'].blit(WORDS['MAG'], menu_surf, (4, TILEHEIGHT*1.1+4)) # Blit Outlined Magic
        FONT['text_yellow'].blit(WORDS['SKL'], menu_surf, (4, TILEHEIGHT*2.2+4)) # Blit Outlined Skill
        FONT['text_yellow'].blit(WORDS['SPD'], menu_surf, (4, TILEHEIGHT*3.3+4)) # Blit Outlined Speed
        FONT['text_yellow'].blit(WORDS['LCK'], menu_surf, (68, 4)) # Blit Outlined Luck
        FONT['text_yellow'].blit(WORDS['DEF'], menu_surf, (4, TILEHEIGHT*4.4+4)) # Blit Outlined Defense
        FONT['text_yellow'].blit(WORDS['RES'], menu_surf, (4, TILEHEIGHT*5.5+4)) # Blit Outlined Resistance
        FONT['text_yellow'].blit(WORDS['MOV'], menu_surf, (68, TILEHEIGHT*1.1+4)) # Blit Outlined Movement
        FONT['text_yellow'].blit(WORDS['CON'], menu_surf, (68, TILEHEIGHT*2.2+4)) # Blit Outlined Constitution
        FONT['text_yellow'].blit(WORDS['Trv'], menu_surf, (68, TILEHEIGHT*4.4+4)) # Blit Outlined Traveler
        if growths:
            FONT['text_yellow'].blit('HP', menu_surf, (68, TILEHEIGHT*3.3+4)) # Blit Outlined Aid
        else:
            FONT['text_yellow'].blit(WORDS['Aid'], menu_surf, (68, TILEHEIGHT*3.3+4)) # Blit Outlined Aid
        FONT['text_yellow'].blit(WORDS['Affin'], menu_surf, (68, TILEHEIGHT*5.5+4)) # Blit Outlined Affinity

    def draw_personal_data_surf(self, surf):
        menu_position = (108, TILEHEIGHT + 16*self.scroll_offset)
        surf.blit(self.personal_data_surf, menu_position)

    def create_growths_surf(self, gameStateObj):
        # Menu Background
        menu_size = (WINWIDTH/2+8, WINHEIGHT - TILEHEIGHT * 3)
        menu_surf = MenuFunctions.CreateBaseMenuSurf(menu_size)

        fgs_mid = IMAGESDICT['StatGrooveFill']

        stats = [self.unit.growths[1], self.unit.growths[2], self.unit.growths[3], self.unit.growths[4], self.unit.growths[6], self.unit.growths[7]]

        self.blit_stat_titles(menu_surf, growths=True)

        for index, stat in enumerate(stats):
            font = FONT['text_blue']
            font.blit(str(stat), menu_surf, (49 - font.size(str(stat))[0],TILEHEIGHT*1.1*index + 4))
        FONT['text_blue'].blit(str(self.unit.growths[5]), menu_surf, (115 - FONT['text_blue'].size(str(self.unit.growths[5]))[0], 4)) # Blit Outlined Luck
        FONT['text_blue'].blit(str(0), menu_surf, (108 - FONT['text_blue'].size(str(0))[0], TILEHEIGHT*1.1+4)) # Blit Outlined Movement
        FONT['text_blue'].blit(str(0), menu_surf, (108 - FONT['text_blue'].size(str(0))[0], TILEHEIGHT*2.2+4)) # Blit Outlined Constitution
        FONT['text_blue'].blit(str(self.unit.strTRV), menu_surf, (92, TILEHEIGHT*4.4+4)) # Blit Outlined Traveler
        FONT['text_blue'].blit(str(self.unit.growths[0]), menu_surf, (115 - FONT['text_blue'].size(str(self.unit.growths[0]))[0], TILEHEIGHT*3.3+4)) # Blit Outlined Aid

        # Handle Affinity
        if CONSTANTS['support'] and self.unit.name in gameStateObj.support.node_dict:
            gameStateObj.support.node_dict[self.unit.name].affinity.draw(menu_surf, (menu_surf.get_width()/2 + 32, TILEHEIGHT*5.5 + 4))
        else:
            FONT['text_blue'].blit('--', menu_surf, (94, TILEHEIGHT*5.5 + 4)) # Blit No Affinity

        return menu_surf

    def draw_growths_surf(self, surf):
        menu_position = (108, TILEHEIGHT + 16*self.scroll_offset)
        surf.blit(self.growths_surf, menu_position)

    def build_groove(self, surf, topleft, width, fill):
        back_groove_surf = IMAGESDICT['StatGrooveBack']
        bgs_start = Engine.subsurface(back_groove_surf, (0, 0, 2, 5))
        bgs_mid = Engine.subsurface(back_groove_surf, (2, 0, 1, 5))
        bgs_end = Engine.subsurface(back_groove_surf, (3, 0, 2, 5))
        fgs_mid = IMAGESDICT['StatGrooveFill']

        # Build back groove
        start_pos = topleft
        surf.blit(bgs_start, start_pos)
        for index in range(width - 2):
            mid_pos = (topleft[0] + bgs_start.get_width() + bgs_mid.get_width()*index, topleft[1])
            surf.blit(bgs_mid, mid_pos)
        end_pos = (topleft[0] + bgs_start.get_width() + bgs_mid.get_width()*(width-2), topleft[1])
        surf.blit(bgs_end, end_pos)

        # Build fill groove
        number_of_fgs_needed = int(fill * (width - 2)) # Width of groove minus section for start and end of back groove
        for groove in range(number_of_fgs_needed):
            surf.blit(fgs_mid, (topleft[0] + bgs_start.get_width() + groove, topleft[1] + 1))

    def create_wexp_surf(self):
        menu_surf = MenuFunctions.CreateBaseMenuSurf((WINWIDTH/2 + 8, 24))
        # Weapon Icons Pictures
        weaponIcons = ITEMDICT['Wexp_Icons']

        counter = 0
        how_many = sum(1 if wexp > 0 else 0 for wexp in self.unit.wexp)
        x_pos = (menu_surf.get_width()-6)/max(how_many, 2)
        for index, wexp in enumerate(self.unit.wexp):
            wexpLetter = CustomObjects.WEAPON_EXP.number_to_letter(wexp)
            wexp_percentage = CustomObjects.WEAPON_EXP.percentage(wexp)
            if wexp > 0:
                offset = 3 + counter*x_pos
                counter += 1
                # Add icon
                menu_surf.blit(Engine.subsurface(weaponIcons, (0, index*16, 16, 16)), (offset, 4))

                # Actually build grooves
                self.build_groove(menu_surf, (offset + 18, 10), x_pos - 22, wexp_percentage)

                # Add text
                FONT['text_blue'].blit(wexpLetter, menu_surf, (offset + 18 + (x_pos - 22)/2 - FONT['text_blue'].size(wexpLetter)[0]/2, 4))

        return menu_surf

    def draw_wexp_surf(self, surf):
        menu_position = (108, WINHEIGHT - 16 - 12 + 16*self.scroll_offset)
        surf.blit(self.wexp_surf, menu_position)

    def create_equipment_surf(self, gameStateObj):
         # Menu Background
        menu_size = (WINWIDTH/2+8, WINHEIGHT - TILEHEIGHT)
        menu_surf = MenuFunctions.CreateBaseMenuSurf(menu_size)

        # Blit background highlight
        index_of_mainweapon = None
        if self.unit.getMainWeapon(): # Ony highlight if unit has weapon
            for index,item in enumerate(self.unit.items): # find first index of mainweapon
                if item.weapon:
                    index_of_mainweapon = index
                    break
            highlightSurf = IMAGESDICT['MenuHighlight']
            for slot in range((menu_surf.get_width() - 16)/highlightSurf.get_width()): # Gives me the amount of highlight needed
                left = 8 + slot*highlightSurf.get_width()
                top = 14 + index_of_mainweapon*16
                menu_surf.blit(highlightSurf, (left, top))

        # Blit items
        for index, item in enumerate(self.unit.items):
            item.draw(menu_surf, (4, index*TILEHEIGHT+4)) # Draws icon
            if item.droppable:
                namefont = FONT['text_green']
                usefont = FONT['text_green']
            elif self.unit.canWield(item):
                namefont = FONT['text_white']
                usefont = FONT['text_blue']
            else:
                namefont = FONT['text_grey']
                usefont = FONT['text_grey']
            namefont.blit(item.name, menu_surf, (20, index*TILEHEIGHT+5))
            if item.uses:
                uses = str(item.uses) + '/' + str(item.uses.total_uses)
            elif item.c_uses:
                uses = str(item.c_uses) + '/' + str(item.c_uses.total_uses)
            else:
                uses = "--/--"
            usefont.blit(uses, menu_surf, (menu_surf.get_width() - 4 - usefont.size(uses)[0], index*TILEHEIGHT+5))

        # Then, input battle stats
        BattleInfoSurf = IMAGESDICT['BattleInfo']
        # Rect
        top = menu_surf.get_height() - BattleInfoSurf.get_height() - 5
        left = 4
        width = BattleInfoSurf.get_width()
        height = BattleInfoSurf.get_height()
        right = left + width
        menu_surf.blit(BattleInfoSurf, (left, top))
        # Then populate battle info menu_surf
        menu_surf.blit(IMAGESDICT['EquipmentLogo'], (8, top+4)) 
        FONT['text_yellow'].blit(WORDS["Rng"], menu_surf, (width/2+8, top))
        FONT['text_yellow'].blit(WORDS["Atk"], menu_surf, (12, top + height/3))
        FONT['text_yellow'].blit(WORDS["Hit"], menu_surf, (12, top + 2*height/3))
        FONT['text_yellow'].blit(WORDS["AS"], menu_surf, (width/2+8, top + height/3))
        FONT['text_yellow'].blit(WORDS["Avoid"], menu_surf, (width/2+8, top + 2*height/3))

        if self.unit.getMainWeapon():
            rng = self.unit.getMainWeapon().get_str_RNG()
            dam = str(self.unit.damage(gameStateObj))
            acc = str(self.unit.accuracy(gameStateObj))
        else:
            rng = '--'
            dam = '--'
            acc = '--'
        avo = str(self.unit.avoid(gameStateObj))
        atkspd = str(self.unit.attackspeed())
        RngWidth = FONT['text_blue'].size(rng)[0]
        AtkWidth = FONT['text_blue'].size(dam)[0]
        HitWidth = FONT['text_blue'].size(acc)[0]
        AvoidWidth = FONT['text_blue'].size(avo)[0]
        ASWidth = FONT['text_blue'].size(atkspd)[0] 
        FONT['text_blue'].blit(rng, menu_surf, (right - 6 - RngWidth, top))
        FONT['text_blue'].blit(dam, menu_surf, (width/2 - 2 - AtkWidth, top + height/3))
        FONT['text_blue'].blit(acc, menu_surf, (width/2 - 2 - HitWidth, top + 2*height/3))
        FONT['text_blue'].blit(avo, menu_surf, (right - 6 - AvoidWidth, top + 2*height/3))
        FONT['text_blue'].blit(atkspd, menu_surf, (right - 6 - ASWidth, top + height/3))

        return menu_surf

    def draw_equipment_surf(self, surf):
        menu_position = (108, TILEHEIGHT + 16*self.scroll_offset)
        surf.blit(self.equipment_surf, menu_position)

    def draw_status(self, index, status, menu_surf):
        if status.time:
            FONT['text_blue'].blit(str(status.time.time_left), menu_surf, (menu_surf.get_width() - FONT['text_blue'].size(str(status.time.time_left))[0] - 4, index*16 + 5))
        elif status.active and status.active.required_charge > 0:
            output = str(status.active.current_charge) + '/' + str(status.active.required_charge)
            FONT['text_blue'].blit(output, menu_surf, (menu_surf.get_width() - FONT['text_blue'].size(output)[0] - 6, index*16 + 5))
        elif status.count:
            output = str(status.count.count) + '/' + str(status.count.orig_count)
            FONT['text_blue'].blit(output, menu_surf, (menu_surf.get_width() - FONT['text_blue'].size(output)[0] - 6, index*16 + 5))
        FONT['text_white'].blit(status.name, menu_surf, (24, index*16 + 5))
        status.draw(menu_surf, (4, index*16 + 4))

    def create_skill_surf(self):
        # Menu background
        menu_size = (WINWIDTH/2+8, WINHEIGHT - 3*TILEHEIGHT)
        menu_surf = MenuFunctions.CreateBaseMenuSurf(menu_size)

        for index, status in enumerate([status for status in self.unit.status_effects if not (status.class_skill or status.hidden)][:6]):
            self.draw_status(index, status, menu_surf)

        return menu_surf

    def draw_skill_surf(self, surf):
        menu_position = (108, TILEHEIGHT + 16*self.scroll_offset)
        surf.blit(self.skill_surf, menu_position)

    def create_class_skill_surf(self):
        menu_surf = MenuFunctions.CreateBaseMenuSurf((WINWIDTH/2 + 8, 24), 'ClearMenuBackground')
        class_skills = [status for status in self.unit.status_effects if status.class_skill]

        for index, skill in enumerate(class_skills):
            left_pos = index*((WINWIDTH/2 + 8)/max(CONSTANTS['num_skills'], len(class_skills)))
            skill.draw(menu_surf, (left_pos + 4, 4))

        return menu_surf

    def draw_class_skill_surf(self, surf):
        menu_position = (108, WINHEIGHT - 16 - 12 + 16*self.scroll_offset)
        surf.blit(self.class_skill_surf, menu_position)

    def create_support_surf(self, gameStateObj):
        # Menu background
        menu_size = (WINWIDTH/2+8, WINHEIGHT - TILEHEIGHT)
        menu_surf = MenuFunctions.CreateBaseMenuSurf(menu_size)

        current_supports = gameStateObj.support.get_supports(self.unit.name)
        current_supports = [support for support in current_supports if support[2]]

        # Display
        for index, (name, affinity, support_level) in enumerate(current_supports):
            affinity.draw(menu_surf, (4, index*16 + 4))
            FONT['text_white'].blit(name, menu_surf, (24, index*16 + 4))
            if support_level == 1:
                letter_level = '@' # Big C
            elif support_level == 2:
                letter_level = '`' # Big B
            elif support_level == 3:
                letter_level = '~' # Big A
            elif support_level >= 4:
                letter_level = '%' # Big S
            FONT['text_yellow'].blit(letter_level, menu_surf, (menu_surf.get_width() - 8 - FONT['text_yellow'].size(letter_level)[0], index*16 + 4))

        # Then, display current support bonuses
        SupportInfoSurf = IMAGESDICT['CurrentSupportInfo']
        left = 4
        height = SupportInfoSurf.get_height()
        width = SupportInfoSurf.get_width()
        top = menu_surf.get_height() - height - 5        
        menu_surf.blit(SupportInfoSurf, (left, top))

        # Then populate current support info menu_surf
        FONT['text_white'].blit(WORDS["Current Bonuses"], menu_surf, (8, top)) 
        FONT['text_yellow'].blit(WORDS["Atk"], menu_surf, (12, top + height/3))
        FONT['text_yellow'].blit(WORDS["Hit"], menu_surf, (12, top + 2*height/3))
        FONT['text_yellow'].blit(WORDS["DEF"], menu_surf, (width/2+8, top + height/3))
        FONT['text_yellow'].blit(WORDS["Avoid"], menu_surf, (width/2+8, top + 2*height/3))

        attack, defense, accuracy, avoid = self.unit.get_support_bonuses(gameStateObj)
        AtkWidth = FONT['text_blue'].size(str(attack))[0]
        HitWidth = FONT['text_blue'].size(str(accuracy))[0]
        AvoidWidth = FONT['text_blue'].size(str(avoid))[0]
        DefWidth = FONT['text_blue'].size(str(defense))[0] 
        FONT['text_blue'].blit(str(attack), menu_surf, (width/2 - 2 - AtkWidth, top + height/3))
        FONT['text_blue'].blit(str(accuracy), menu_surf, (width/2 - 2 - HitWidth, top + 2*height/3))
        FONT['text_blue'].blit(str(avoid), menu_surf, (right - 6 - AvoidWidth, top + 2*height/3))
        FONT['text_blue'].blit(str(defense), menu_surf, (right - 6 - DefWidth, top + height/3))

        return menu_surf

    def draw_support_surf(self, surf):
        menu_position = (108, TILEHEIGHT + 16*self.scroll_offset)
        surf.blit(self.support_surf, menu_position)

class HelpGraph(object):
    def __init__(self, state, unit, metaDataObj, gameStateObj):
        self.help_boxes = {}
        self.unit = unit
        self.current = None

        if state == WORDS['Personal Data']:
            self.populate_personal_data(metaDataObj)
            self.initial = "Strength"
        elif state == WORDS['Personal Growths']:
            self.populate_personal_data(metaDataObj, growths=True)
            self.initial = "Strength"
        elif state == WORDS['Equipment']:
            self.populate_equipment(metaDataObj)
            if self.unit.items:
                self.initial = "Item0"
            else:
                self.initial = "Unit Desc"
        elif state == WORDS["Supports"]:
            self.populate_supports(gameStateObj, metaDataObj)
            if any(support[2] for support in gameStateObj.support.get_supports(self.unit.name)):
                self.initial = "Support0"
            else:
                self.initial = "Unit Desc"
        elif state == WORDS["Skills & Status"]:
            self.populate_status(metaDataObj)
            if [status for status in self.unit.status_effects if not status.class_skill]:
                self.initial = "Status0"
            elif self.unit.status_effects:
                self.initial = "Skill0"
            else:
                self.initial = "Unit Desc"

    def populate_personal_data(self, metaDataObj, growths=False):
        self.help_boxes["Strength"] = Help_Box("Strength", (2 + (6*WINWIDTH/16), TILEHEIGHT+5), create_help_box(WORDS['STR_desc']))
        self.help_boxes["Magic"] = Help_Box("Magic", (2 + (6*WINWIDTH/16), TILEHEIGHT*2.1+5), create_help_box(WORDS['MAG_desc']))
        self.help_boxes["Skill"] = Help_Box("Skill", (2 + (6*WINWIDTH/16), TILEHEIGHT*3.2+5), create_help_box(WORDS['SKL_desc']))
        self.help_boxes["Speed"] = Help_Box("Speed", (2 + (6*WINWIDTH/16), TILEHEIGHT*4.3+5), create_help_box(WORDS['SPD_desc']))
        self.help_boxes["Defense"] = Help_Box("Defense", (2 + (6*WINWIDTH/16), TILEHEIGHT*5.4+5), create_help_box(WORDS['DEF_desc']))
        self.help_boxes["Resistance"] = Help_Box("Resistance", (2 + (6*WINWIDTH/16), TILEHEIGHT*6.5+5), create_help_box(WORDS['RES_desc']))

        self.help_boxes["Luck"] = Help_Box("Luck", (10*WINWIDTH/16 + 6, TILEHEIGHT+5), create_help_box(WORDS['LCK_desc']))
        self.help_boxes["Movement"] = Help_Box("Movement", (10*WINWIDTH/16 + 6, TILEHEIGHT*2.1 + 5), create_help_box(WORDS['MOV_desc']))
        self.help_boxes["Con"] = Help_Box("Con", (10*WINWIDTH/16 + 6, TILEHEIGHT*3.2 + 5), create_help_box(WORDS['CON_desc']))
        if growths:
            self.help_boxes["Aid"] = Help_Box("Aid", (10*WINWIDTH/16 + 6, TILEHEIGHT*4.3 + 5), create_help_box(WORDS['HP_desc']))
        else:
            self.help_boxes["Aid"] = Help_Box("Aid", (10*WINWIDTH/16 + 6, TILEHEIGHT*4.3 + 5), create_help_box(WORDS['Aid_desc']))
        self.help_boxes["Traveler"] = Help_Box("Traveler", (10*WINWIDTH/16 + 6, TILEHEIGHT*5.4 + 5), create_help_box(WORDS['Trv_desc']))
        self.help_boxes["Affin"] = Help_Box("Affin", (10*WINWIDTH/16 + 6, TILEHEIGHT*6.5 + 5), create_help_box(WORDS['Affin_desc']))

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

        # Populate Weapon Exp
        good_weapons = [wexp for wexp in self.unit.wexp if wexp > 0]
        for index, wexp in enumerate(good_weapons):
            self.help_boxes["Wexp"+str(index)] = Help_Box("Wexp"+str(index), (100+60*index, 136), create_help_box("Weapon Rank: %s"%(wexp)))

        for i in range(len(good_weapons)):
            self.help_boxes["Wexp"+str(i)].right = ("Wexp"+str(i+1)) if i < (len(good_weapons) - 1) else None
            self.help_boxes["Wexp"+str(i)].left = ("Wexp"+str(i-1)) if i > 0 else None
            if i:
                self.help_boxes["Wexp"+str(i)].up = "Affin"
            else:
                self.help_boxes["Wexp"+str(i)].up = "Resistance"
                self.help_boxes["Wexp"+str(i)].left = "HP"

        if good_weapons:
            self.help_boxes["Resistance"].down = "Wexp0"
        if len(good_weapons) > 1:
            self.help_boxes["Affin"].down = "Wexp1"

        self.populate_info_menu_default(metaDataObj)

        # Connect default with personal data
        self.help_boxes["Unit Desc"].right = "Speed"
        self.help_boxes["Class Desc"].right = "Resistance"
        self.help_boxes["Experience"].right = "Resistance"
        self.help_boxes["HP"].right = "Wexp0" if good_weapons else "Resistance"
        self.help_boxes["Resistance"].left = "Class Desc"
        self.help_boxes["Defense"].left = "Unit Desc"
        self.help_boxes["Speed"].left = "Unit Desc"
        self.help_boxes["Magic"].left = "Unit Desc"
        self.help_boxes["Strength"].left = "Unit Desc"
        self.help_boxes["Skill"].left = "Unit Desc"

    def populate_equipment(self, metaDataObj):
        for index, item in enumerate(self.unit.items):
            self.help_boxes["Item"+str(index)] = Help_Box("Item"+str(index), ((7*WINWIDTH/16) - 8, TILEHEIGHT*index + TILEHEIGHT + 4), item.get_help_box())

        self.help_boxes["Atk"] = Help_Box("Atk", (100, WINHEIGHT - TILEHEIGHT*2 - 2), create_help_box(WORDS['Atk_desc']))
        self.help_boxes["Hit"] = Help_Box("Hit", (100, WINHEIGHT - TILEHEIGHT - 2), create_help_box(WORDS['Hit_desc']))
        self.help_boxes["Rng"] = Help_Box("Rng", (160, WINHEIGHT - TILEHEIGHT*3 - 2), create_help_box(WORDS['Rng_desc']))
        self.help_boxes["AS"] = Help_Box("AS", (160, WINHEIGHT - TILEHEIGHT*2 - 2), create_help_box(WORDS['AS_desc']))
        self.help_boxes["Avoid"] = Help_Box("Avoid", (160, WINHEIGHT - TILEHEIGHT - 2), create_help_box(WORDS['Avoid_desc']))

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

        self.populate_info_menu_default(metaDataObj)

        # Connect default with equipment
        for i in range(len(self.unit.items)):
            self.help_boxes["Item"+str(i)].left = "Unit Desc"

        if self.unit.items:
            self.help_boxes['Unit Desc'].up = "Item0"
            self.help_boxes['Unit Desc'].right = "Item" + str(min(3, len(self.unit.items) - 1))

        self.help_boxes["Class Desc"].right = "Atk"
        self.help_boxes["Experience"].right = "Atk"
        self.help_boxes["HP"].right = "Hit"

    def populate_supports(self, gameStateObj, metaDataObj):
        supports = gameStateObj.support.get_supports(self.unit.name)
        supports = [support for support in supports if support[2]]
        for index, support in enumerate(supports):
            affinity = support[1]
            desc = affinity.desc
            self.help_boxes["Support"+str(index)] = Help_Box("Support"+str(index), ((7*WINWIDTH/16) - 8, TILEHEIGHT*index + TILEHEIGHT + 4), create_help_box(desc))

        self.help_boxes["Atk"] = Help_Box("Atk", (100, WINHEIGHT - TILEHEIGHT*2 - 2), create_help_box(WORDS['Support_Atk_desc']))
        self.help_boxes["Hit"] = Help_Box("Hit", (100, WINHEIGHT - TILEHEIGHT - 2), create_help_box(WORDS['Support_Hit_desc']))
        self.help_boxes["Def"] = Help_Box("Def", (160, WINHEIGHT - TILEHEIGHT*2 - 2), create_help_box(WORDS['Support_Def_desc']))
        self.help_boxes["Avoid"] = Help_Box("Avoid", (160, WINHEIGHT - TILEHEIGHT - 2), create_help_box(WORDS['Support_Avoid_desc']))

        # Add connections
        for i in range(len(supports)):
            self.help_boxes["Support"+str(i)].down = ("Support"+str(i+1)) if i < (len(supports) - 1) else None
            self.help_boxes["Support"+str(i)].up = ("Support"+str(i-1)) if i > 0 else None

        if supports:
            self.help_boxes["Support" + str(len(supports) - 1)].down = "Atk"

        self.help_boxes["Atk"].right = "Def"
        self.help_boxes["Atk"].down = "Hit"
        self.help_boxes["Atk"].up = ("Support"+str(len(supports) - 1)) if supports else "Unit Desc"
        self.help_boxes["Atk"].left = "Experience"

        self.help_boxes["Hit"].left = "HP"
        self.help_boxes["Hit"].right = "Avoid"
        self.help_boxes["Hit"].up = "Atk"

        self.help_boxes["Avoid"].left = "Hit"
        self.help_boxes["Avoid"].up = "Def"

        self.help_boxes["Def"].left = "Atk"
        self.help_boxes["Def"].up = ("Support"+str(len(supports) - 1)) if supports else "Unit Desc"
        self.help_boxes["Def"].down = "Avoid"

        self.populate_info_menu_default(metaDataObj)

        # Connect default with equipment
        for i in range(len(supports)):
            self.help_boxes["Support"+str(i)].left = "Unit Desc"

        if supports:
            self.help_boxes['Unit Desc'].up = "Support0"
            self.help_boxes['Unit Desc'].right = "Support" + str(min(3, len(supports) - 1))

        self.help_boxes["Class Desc"].right = "Atk"
        self.help_boxes["Experience"].right = "Atk"
        self.help_boxes["HP"].right = "Hit"

    def populate_status(self, metaDataObj):
        statuses = [status for status in self.unit.status_effects if not status.class_skill]
        skills = [status for status in self.unit.status_effects if status.class_skill]

        for index, status in enumerate(statuses):
            self.help_boxes["Status"+str(index)] = Help_Box("Status"+str(index), ((7*WINWIDTH/16) - 8, TILEHEIGHT*1.1*index + TILEHEIGHT + 4), create_help_box(status.desc))

        for index, skill in enumerate(skills):
            if skill.active:
                description = skill.desc + ' ' + str(skill.active.current_charge) + '/' + str(skill.active.required_charge)
            else:
                description = skill.desc
            left = 108 + index*((WINWIDTH/2 + 8)/max(CONSTANTS['num_skills'], len(skills))) - 10
            self.help_boxes["Skill"+str(index)] = Help_Box("Skill"+str(index), (left, 82 + 7*TILEHEIGHT/2), create_help_box(description, name=skill.name))

        self.populate_info_menu_default(metaDataObj)

        # Connect them together
        for i in range(len(statuses)):
            self.help_boxes["Status"+str(i)].down = ("Status"+str(i+1)) if i < (len(statuses) - 1) else None
            self.help_boxes["Status"+str(i)].up = ("Status"+str(i-1)) if i > 0 else None
        
        # Connect default with equipment
        for i in range(len(statuses)):
            self.help_boxes["Status"+str(i)].left = "Unit Desc"

        if statuses:
            self.help_boxes['Unit Desc'].up = "Status0"
            self.help_boxes['Unit Desc'].right = "Status" + str(min(3, len(statuses) - 1))

        if statuses and skills:
            self.help_boxes["Status"+str(len(statuses)-1)].down = "Skill0"

        for i in range(len(skills)):
            if statuses:
                self.help_boxes["Skill"+str(i)].up = "Status" + str(len(statuses)-1)
            self.help_boxes["Skill"+str(i)].right = ("Skill"+str(i+1)) if i < (len(skills) - 1) else None
            self.help_boxes["Skill"+str(i)].left = ("Skill"+str(i-1)) if i > 0 else None

        if skills:
            self.help_boxes["Skill0"].left = "HP"
            self.help_boxes["HP"].right = "Skill0"
            self.help_boxes["Experience"].right = "Skill0"

    def populate_info_menu_default(self, metaDataObj):
        self.help_boxes["Unit Desc"] = Help_Box("Unit Desc", (24, 84 + TILEHEIGHT/2), create_help_box(self.unit.desc))
        self.help_boxes["Class Desc"] = Help_Box("Class Desc", (-8, 84 + 3*TILEHEIGHT/2), create_help_box(metaDataObj['class_dict'][self.unit.klass]['desc']))
        self.help_boxes["Unit Level"] = Help_Box("Unit Level", (-8, 82 + 5*TILEHEIGHT/2), create_help_box(WORDS['Level_desc']))
        self.help_boxes["Experience"] = Help_Box("Experience", (22, 84 + 5*TILEHEIGHT/2), create_help_box(WORDS['Exp_desc']))
        self.help_boxes["HP"] = Help_Box("HP", (-8, 82 + 7*TILEHEIGHT/2), create_help_box(WORDS['HP_desc']))

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
        self.cursor_position = cursor_position
        self.help_surf = help_surf
        # Determine help_topleft position
        if self.cursor_position[0] + self.help_surf.get_width() > WINWIDTH:
            helpleft = WINWIDTH - self.help_surf.get_width()
        else:
            helpleft = self.cursor_position[0] - min(TILEWIDTH*2, self.cursor_position[0]) # Don't go to far to the left
        if self.cursor_position[1] > WINHEIGHT/2 + 8:
            helptop = self.cursor_position[1] - self.help_surf.get_height()
        else:
            helptop = self.cursor_position[1] + 16
        self.help_topleft = (helpleft, helptop)
        
        self.left = None
        self.right = None
        self.up = None
        self.down = None

        Counters.CursorControl.__init__(self)

    def draw(self, surf):
        surf.blit(self.cursor, (self.cursor_position[0] + 2*self.cursorAnim[self.cursorCounter], self.cursor_position[1]))
        surf.blit(self.help_surf, self.help_topleft)

def create_help_box(description, num_lines=2, name=False):
    font = FONT['convo_black']
    # Set up variables needed for algorithm
    description_length = font.size(description)[0]
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
        length_so_far = font.size(''.join(lines[which_line]))[0]
        if length_so_far > description_length/num_lines:
            length_reached = True
        elif length_so_far > WINWIDTH - 8:
            length_reached = True
    # Reform strings
    strings = []
    for line in lines:
        strings.append(''.join(line)) 
    # Find the greater of the two lengths
    greater_line_len = max([font.size(string)[0] for string in strings])

    size_x = greater_line_len + 16
    if name:
        num_lines += 1
    size_y = font.height * num_lines + 8
    help_surf = MenuFunctions.CreateBaseMenuSurf((size_x, size_y), 'MessageWindowBackground')
    # Now draw
    if name:
        font.blit(name, help_surf, (4, 4))
    for index, string in enumerate(strings):
        font.blit(string, help_surf, (4, font.height*index + 4 + (16 if name else 0)))

    return help_surf