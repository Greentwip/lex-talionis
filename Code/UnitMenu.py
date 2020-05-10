# Imports
from . import GlobalConstants as GC
from . import configuration as cf
from . import Engine, StateMachine
from . import Image_Modification, BaseMenuSurf, Weapons, HelpMenu
from . import GUIObjects, Counters, Background, ClassData
from . import CustomObjects

class UnitMenu(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # Get units to display
            self.units = [unit for unit in gameStateObj.allunits if unit.position and unit.team == 'player']

            self.bg_surf = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['UnitMenuBackground'], 10)
            self.title_bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['TitleBar'], 10)
            self.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])
            self.states = [('Character', ['Class', 'Lv', 'Exp', 'HP', 'Max'], [4, 66, 89, 113, 133]),
                           ('Fighting Skill', ['STR', 'MAG', 'SKL', 'SPD', 'LCK', 'DEF', 'RES'], [4, 26, 48, 71, 94, 119, 142]),
                           ('Equipment', ['Equip', 'Atk', 'Hit', 'Avoid'], [16, 72, 103, 136]),
                           ('Personal Data', ['MOV', 'CON', 'Aid', 'Rat', 'Trv'], [4, 33, 60, 82, 106]),
                           ('Weapon Level', Weapons.TRIANGLE.types, [9 + idx*16 for idx in range(len(Weapons.TRIANGLE.types))])]
            if cf.CONSTANTS['support'] and False:  # TODO: Figure out what the hell this is
                self.states.append(('Support Chance', ['Ally'], [11]))
            self.state_index = 0
            self.prev_state_index = 0
            self.unit_index = 1 # 0 means on banner
            self.scroll_index = 1
            self.banner_index = 0
            self.num_per_page = 6

            self.state_scroll = 0
            self.scroll_direction = 0

            self.weapon_icons = [Weapons.Icon(weapon) for weapon in Weapons.TRIANGLE.types]
            self.help_boxes = []
            self.info = False

            self.scroll_bar = GUIObjects.ScrollBar((233, 59))
            self.left_arrow = GUIObjects.ScrollArrow('left', (7, 41))
            self.right_arrow = GUIObjects.ScrollArrow('right', (GC.WINWIDTH - 7 - 8, 41), 0.5)

            # For sort
            self.current_sort = 'Name'
            self.descending = False
            self.sort_surf = BaseMenuSurf.CreateBaseMenuSurf((64, 24))
            self.sort_surf = Image_Modification.flickerImageTranslucent(self.sort_surf, 10)
            self.sort_arrow_counter = Counters.ArrowCounter()
            self.sort_arrow_counter.arrow_anim = [0, 1, 2]
            self.sort()

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'
        else:
            chosen_unit = gameStateObj.info_menu_struct['chosen_unit']
            if chosen_unit and chosen_unit in self.units:
                self.move_to_unit(chosen_unit)
            gameStateObj.info_menu_struct['chosen_unit'] = None

    def back(self, gameStateObj):
        GC.SOUNDDICT['Select 4'].play()
        gameStateObj.stateMachine.changeState('transition_pop')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()

        if event == 'INFO':
            if self.unit_index:
                CustomObjects.handle_info_key(gameStateObj, metaDataObj, self.units[self.unit_index-1])
            else:
                self.info = not self.info
        elif event == 'BACK':
            self.back(gameStateObj)
        elif event == 'SELECT':
            if self.unit_index == 0: # On banner
                if self.banner_index == 0:
                    new_sort = 'Name'
                else:
                    new_sort = self.states[self.state_index][1][self.banner_index - 1]
                if new_sort == self.current_sort:
                    self.descending = not self.descending
                else:
                    self.current_sort = new_sort
                self.sort(gameStateObj)
                GC.SOUNDDICT['Select 3'].play()
        elif 'RIGHT' in directions:
            if self.unit_index:
                self.next_state()
            else:
                self.next_banner()
        elif 'LEFT' in directions:
            if self.unit_index:
                self.prev_state()
            else:
                self.prev_banner()
        elif 'UP' in directions:
            self.move_up()
        elif 'DOWN' in directions:
            self.move_down()

    def next_state(self):
        if self.state_index < len(self.states) - 1:
            self.prev_state_index = self.state_index
            self.state_index += 1
            self.scroll_direction = -1
            self.banner_index = 1
            self.help_boxes = []
            self.right_arrow.pulse()
            GC.SOUNDDICT['Status_Page_Change'].play()
        else:
            GC.SOUNDDICT['Error'].play()

    def prev_state(self):
        if self.state_index > 0:
            self.prev_state_index = self.state_index
            self.state_index -= 1
            self.scroll_direction = 1
            self.banner_index = 10
            self.help_boxes = []
            self.left_arrow.pulse()
            GC.SOUNDDICT['Status_Page_Change'].play()
        else:
            GC.SOUNDDICT['Error'].play()

    def next_banner(self):
        self.banner_index += 1
        self.right_arrow.pulse()
        if self.banner_index >= len(self.help_boxes):
            self.next_state()
        else:
            GC.SOUNDDICT['Select 6'].play()

    def prev_banner(self):
        if self.banner_index > 0:
            self.left_arrow.pulse()
            self.banner_index -= 1
        if self.banner_index < 1:
            self.prev_state()
        else:
            GC.SOUNDDICT['Select 6'].play()

    def move_up(self):
        if self.unit_index > 0:
            GC.SOUNDDICT['Select 6'].play()
            self.unit_index -= 1
        if self.scroll_index >= self.unit_index and self.scroll_index > 1:
            self.scroll_index -= 1

    def move_down(self):
        if self.unit_index < len(self.units):
            GC.SOUNDDICT['Select 6'].play()
            self.unit_index += 1
            self.info = False
        if self.scroll_index <= self.unit_index - self.num_per_page + 1 and self.scroll_index <= len(self.units) - self.num_per_page:
            self.scroll_index += 1

    def move_to_unit(self, unit):
        new_unit_index = self.units.index(unit) + 1
        if new_unit_index > self.unit_index:
            for num in range(new_unit_index - self.unit_index):
                self.move_down()
        elif new_unit_index < self.unit_index:
            for num in range(self.unit_index - new_unit_index):
                self.move_up()

    def update(self, gameStateObj, metaDataObj):
        if self.scroll_direction > 0:
            self.state_scroll += 16
        elif self.scroll_direction < 0:
            self.state_scroll -= 16
        if self.state_scroll < -160 or self.state_scroll > 160:
            self.state_scroll = 0
            self.scroll_direction = 0

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf.copy()
        self.background.draw(surf)
        surf.blit(self.bg_surf, (6, 36))
        if self.unit_index:
            self.draw_highlight(surf)
        self.draw_names(surf)
        if self.scroll_direction > 0:
            self.draw_state(surf, gameStateObj, self.state_scroll, prev=True)
        elif self.scroll_direction < 0:
            self.draw_state(surf, gameStateObj, self.state_scroll, prev=True)
        self.draw_state(surf, gameStateObj, self.state_scroll)
        self.draw_banner(surf)
        self.draw_sort(surf)
        self.draw_page_numbers(surf)
        if self.units:
            self.scroll_bar.draw(surf, self.scroll_index - 1, 6, len(self.units))
        if self.state_index > 0:
            self.left_arrow.draw(surf)
        if self.state_index < len(self.states) - 1:
            self.right_arrow.draw(surf)
        self.draw_cursor(surf)

        return surf

    def draw_highlight(self, surf):
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range(216//width): # Gives me the amount of highlight needed
            topleft = (8 + slot*width, 64 + 2 + (self.unit_index-self.scroll_index)*16)
            surf.blit(highlightSurf, topleft)

    def draw_names(self, surf):
        font = GC.FONT['text_white']
        font.blit('Name', surf, (28, 40))
        for idx, unit in enumerate(self.units[self.scroll_index-1:self.scroll_index-1+self.num_per_page]):
            # Image
            unit_sprite = unit.sprite.create_image('passive')
            left = 8 - max(0, (unit_sprite.get_width() - 16)//2)
            top = 48 + idx*16 - max(0, (unit_sprite.get_height() - 16)//2)
            surf.blit(unit_sprite, (left, top))
            # Name
            font.blit(unit.name, surf, (24, 56 + idx*16))

    def draw_banner(self, surf):
        surf.blit(self.title_bg, (0, 0))
        title = self.states[self.state_index][0]
        GC.FONT['text_brown'].blit(title, surf, (64 - GC.FONT['text_brown'].size(title)[0]//2, 8))

    def draw_cursor(self, surf):
        self.banner_index = min(self.banner_index, len(self.help_boxes) - 1)
        if self.help_boxes and self.unit_index == 0:
            self.help_boxes[self.banner_index].update()
            self.help_boxes[self.banner_index].draw(surf, self.info)

    def draw_page_numbers(self, surf):
        GC.FONT['text_blue'].blit(str(self.state_index+1), surf, (208, 24))
        GC.FONT['text_white'].blit('/', surf, (217, 24))
        GC.FONT['text_blue'].blit(str(len(self.states)), surf, (224, 24))

    def draw_sort(self, surf):
        self.sort_arrow_counter.update()
        surf.blit(self.sort_surf, (170, 4))
        if self.descending:
            surf.blit(Engine.flip_vert(GC.IMAGESDICT['GreenArrow']), (225, 9 + self.sort_arrow_counter.get()))
        else:
            surf.blit(GC.IMAGESDICT['GreenArrow'], (225, 9 + self.sort_arrow_counter.get()))
        GC.FONT['text_white'].blit('Sort: ' + self.current_sort, surf, (173, 8))

    def draw_state(self, surf, gameStateObj, scroll=0, prev=False):
        state_surf = Engine.create_surface((160, 112), transparent=True)
        if prev:
            idx = self.prev_state_index
        else:
            idx = self.state_index
        state = self.states[idx][0]
        if state == 'Character':
            titles, offsets = self.draw_character_state(state_surf, idx)
        elif state == 'Fighting Skill':
            titles, offsets = self.draw_fighting_skill_state(state_surf, idx)
        elif state == 'Equipment':
            titles, offsets = self.draw_equipment_state(state_surf, idx, gameStateObj)
        elif state == 'Personal Data':
            titles, offsets = self.draw_personal_data_state(state_surf, idx)
        elif state == 'Weapon Level':
            titles, offsets = self.draw_weapon_level_state(state_surf, idx)
        elif state == 'Support Chance':
            titles, offsets = self.draw_support_chance_state(state_surf, idx, gameStateObj)

        if not prev:
            self.summon_help_boxes(titles, offsets)

        if prev:
            if scroll > 0:
                left = scroll + 64
                state_surf = Engine.subsurface(state_surf, (0, 0, 160 - scroll, 112))
            elif scroll < 0:
                left = 64
                state_surf = Engine.subsurface(state_surf, (-scroll, 0, 160 + scroll, 112))
            else:
                left = 64
                state_surf = Engine.subsurface(state_surf, (0, 0, 160, 112))
        else:
            if scroll > 0:
                left = 64
                state_surf = Engine.subsurface(state_surf, (160 - scroll, 0, scroll, 112))
            elif scroll < 0:
                left = 160 + 64 + scroll
                state_surf = Engine.subsurface(state_surf, (0, 0, -scroll, 112))
            else:
                left = 64
                state_surf = Engine.subsurface(state_surf, (0, 0, 160, 112))
        surf.blit(state_surf, (left, 40))

    def avail_units(self):
        return self.units[self.scroll_index-1:self.scroll_index-1+self.num_per_page]

    def draw_character_state(self, surf, idx):
        # draw title
        titles = self.states[idx][1]
        offsets = self.states[idx][2]
        font = GC.FONT['text_white']
        for idx in range(len(titles)):
            font.blit(cf.WORDS[titles[idx]], surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            long_name = ClassData.class_dict[unit.klass]['long_name']
            font.blit(long_name, surf, (4, top))
            GC.FONT['text_blue'].blit(str(unit.level), surf, (80 - GC.FONT['text_blue'].size(str(unit.level))[0], top))
            exp = str(int(unit.exp))
            GC.FONT['text_blue'].blit(exp, surf, (100 - GC.FONT['text_blue'].size(exp)[0], top))
            c_hp = str(unit.currenthp)
            GC.FONT['text_blue'].blit(c_hp, surf, (128 - GC.FONT['text_blue'].size(c_hp)[0], top))
            font.blit('/', surf, (130, top))
            unit.stats['HP'].draw(surf, unit, (152, top), compact=True)

        return titles, offsets

    def draw_fighting_skill_state(self, surf, idx):
        titles = self.states[idx][1]
        offsets = self.states[idx][2]
        font = GC.FONT['text_white']
        for idx in range(len(titles)):
            font.blit(cf.WORDS[titles[idx]], surf, (offsets[idx], 0))

        value_offsets = [16, 40, 64, 88, 112, 136, 160]
        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            for idx, stat in enumerate(titles):
                unit.stats[stat].draw(surf, unit, (value_offsets[idx] - 1, top), compact=True)

        return titles, offsets

    def draw_equipment_state(self, surf, idx, gameStateObj):
        titles = self.states[idx][1]
        offsets = self.states[idx][2]
        font = GC.FONT['text_white']
        for idx in range(len(titles)):
            font.blit(cf.WORDS[titles[idx]], surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            item = unit.getMainWeapon()
            if item:
                item.draw(surf, (1, top))
                font.blit(item.name, surf, (16, top))
            else:
                font.blit('--', surf, (16, top))
            atk, hit, avoid = str(unit.damage(gameStateObj)), str(unit.accuracy(gameStateObj)), str(unit.avoid(gameStateObj))
            GC.FONT['text_blue'].blit(atk, surf, (88 - GC.FONT['text_blue'].size(atk)[0], top))
            GC.FONT['text_blue'].blit(hit, surf, (120 - GC.FONT['text_blue'].size(hit)[0], top))
            GC.FONT['text_blue'].blit(avoid, surf, (152 - GC.FONT['text_blue'].size(avoid)[0], top))

        return titles, offsets

    def draw_personal_data_state(self, surf, idx):
        titles = self.states[idx][1]
        offsets = self.states[idx][2]
        font = GC.FONT['text_white']
        for idx in range(len(titles)):
            font.blit(cf.WORDS[titles[idx]], surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            unit.stats['MOV'].draw(surf, unit, (24, top), compact=True)
            unit.stats['CON'].draw(surf, unit, (48, top), compact=True)
            aid = str(unit.getAid())
            GC.FONT['text_blue'].blit(aid, surf, (72 - GC.FONT['text_blue'].size(aid)[0], top))
            rat = str(unit.get_rating())
            GC.FONT['text_blue'].blit(rat, surf, (100 - GC.FONT['text_blue'].size(rat)[0], top))
            GC.FONT['text_white'].blit(unit.strTRV, surf, (106, top))

        return titles, offsets

    def draw_weapon_level_state(self, surf, idx):
        titles = self.states[idx][1]
        offsets = self.states[idx][2]

        for idx, weapon_icon in enumerate(self.weapon_icons):
            weapon_icon.draw(surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            for index, wexp in enumerate(unit.wexp):
                if wexp > 0:
                    wexpLetter = Weapons.EXP.number_to_letter(wexp)
                else:
                    wexpLetter = '-'
                pos = (24 + index*16 - GC.FONT['text_blue'].size(wexpLetter)[0], top)
                GC.FONT['text_blue'].blit(wexpLetter, surf, pos)

        return titles, offsets

    def draw_support_chance_state(self, surf, idx, gameStateObj):
        titles = self.states[idx][1]
        offsets = self.states[idx][2]
        font = GC.FONT['text_white']
        for idx in range(len(titles)):
            font.blit(cf.WORDS[titles[idx]], surf, (offsets[idx], 0))

        party_members = gameStateObj.get_units_in_party(gameStateObj.current_party)
        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            counter = 0
            for index, (name, affinity, support_level) in enumerate(gameStateObj.support.get_supports(unit.id)):
                pos = (9 + index*49, top)
                if support_level > 0 and name in [unit.name for unit in party_members]:
                    GC.FONT['text_blue'].blit(name, surf, pos)
                    counter += 1
            for index in range(counter, 3):
                pos = (9 + index*49, top)
                GC.FONT['text_blue'].blit('---', surf, pos)

        return titles, offsets

    def summon_help_boxes(self, titles, offsets):
        if not self.help_boxes:
            self.help_boxes.append(HelpMenu.Help_Box('Name', (28 - 15, 40), HelpMenu.Help_Dialog(cf.WORDS['Name_desc'])))
            for idx in range(len(titles)):
                pos = (offsets[idx] + 64 - 15 - 2, 40)
                self.help_boxes.append(HelpMenu.Help_Box(titles[idx], pos, HelpMenu.Help_Dialog(cf.WORDS[titles[idx] + '_desc'])))

    fighting_stats = set(GC.EQUATIONS.stat_list[1:])

    def sort(self, gameStateObj=None):
        if self.current_sort == 'Name':
            comp = lambda unit: unit.name
        elif self.current_sort == 'Class':
            comp = lambda unit: unit.klass
        elif self.current_sort == 'Lv':
            comp = lambda unit: unit.level
        elif self.current_sort == 'Exp':
            comp = lambda unit: int(unit.exp)
        elif self.current_sort == 'HP':
            comp = lambda unit: unit.currenthp
        elif self.current_sort == 'Max':
            comp = lambda unit: unit.stats['HP']
        elif self.current_sort in self.fighting_stats:
            comp = lambda unit: unit.stats[self.current_sort]
        elif self.current_sort == 'Aid':
            comp = lambda unit: unit.getAid()
        elif self.current_sort == 'Rat':
            comp = lambda unit: unit.get_rating()
        elif self.current_sort == 'Trv':
            comp = lambda unit: unit.strTRV
        elif self.current_sort == 'Atk':
            comp = lambda unit: unit.damage(gameStateObj)
        elif self.current_sort == 'Hit':
            comp = lambda unit: unit.accuracy(gameStateObj)
        elif self.current_sort == 'Avoid':
            comp = lambda unit: unit.avoid(gameStateObj)
        elif self.current_sort in Weapons.TRIANGLE.types:
            comp = lambda unit: unit.wexp[Weapons.TRIANGLE.types.index(self.current_sort)]
        elif self.current_sort == 'Equip':
            comp = lambda unit: GC.ITEMDATA[unit.getMainWeapon().id]['num'] if unit.getMainWeapon() else 1000

        self.units = sorted(self.units, key=comp, reverse=self.descending)
