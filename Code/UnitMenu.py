# Imports
from GlobalConstants import *
from configuration import *
import Engine, InputManager, StateMachine, Counters
import Image_Modification, MenuFunctions, CustomObjects, InfoMenu
import GUIObjects

class UnitMenu(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.fluid_helper = InputManager.FluidScroll(64)
            # Get units to display
            self.units = [unit for unit in gameStateObj.allunits if unit.position and unit.team == 'player']

            self.bg_surf = Image_Modification.flickerImageTranslucent(IMAGESDICT['UnitMenuBackground'], 10)
            self.title_bg = Image_Modification.flickerImageTranslucent(IMAGESDICT['TitleBar'], 10)
            self.background = MenuFunctions.MovingBackground(IMAGESDICT['RuneBackground'])

            self.states = ['Character',
                           'Fighting Skill',
                           'Equipment',
                           'Personal Data',
                           'Weapon Level']
            if CONSTANTS['support']:
                self.states.append('Support Chance')
            self.state_index = 0
            self.prev_state_index = 0
            self.unit_index = 1 # 0 means on banner
            self.scroll_index = 1
            self.banner_index = 0
            self.num_per_page = 6

            self.state_scroll = 0
            self.scroll_direction = 0

            self.weapon_icons = [CustomObjects.WeaponIcon(weapon) for weapon in CustomObjects.WEAPON_TRIANGLE.types]
            self.help_boxes = []
            self.info = False

            self.scroll_bar = GUIObjects.ScrollBar((233, 59))
            self.left_arrow = GUIObjects.ScrollArrow('left', (7, 41))
            self.right_arrow = GUIObjects.ScrollArrow('right', (WINWIDTH - 7 - 8, 41), 0.5)

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'
        else:
            chosen_unit = gameStateObj.info_menu_struct['chosen_unit']
            if chosen_unit:
                self.move_to_unit(chosen_unit)
            gameStateObj.info_menu_struct['chosen_unit'] = None

    def back(self, gameStateObj):
        SOUNDDICT['Select 4'].play()
        gameStateObj.stateMachine.changeState('transition_pop')

    def take_input(self, eventList, gameStateObj, metaDataObj):
         ### Get events
        event = gameStateObj.input_manager.process_input(eventList)
        self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
        currentTime = Engine.get_time()

        if event == 'INFO':
            if self.unit_index:
                StateMachine.CustomObjects.handle_info_key(gameStateObj, metaDataObj, self.units[self.unit_index-1])
            else:
                self.info = not self.info
        elif event == 'BACK' or event == 'SELECT':
            self.back(gameStateObj)
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

    def prev_state(self):
        if self.state_index > 0:
            self.prev_state_index = self.state_index
            self.state_index -= 1
            self.scroll_direction = 1
            self.banner_index = 10
            self.help_boxes = []
            self.left_arrow.pulse()

    def next_banner(self):
        self.banner_index += 1
        self.right_arrow.pulse()
        if self.banner_index >= len(self.help_boxes):
            self.next_state()

    def prev_banner(self):
        if self.banner_index > 0:
            self.left_arrow.pulse()
            self.banner_index -= 1
        if self.banner_index < 1:
            self.prev_state()

    def move_up(self):
        if self.unit_index > 0:
            self.unit_index -= 1
        if self.scroll_index >= self.unit_index and self.scroll_index > 1:
            self.scroll_index -= 1

    def move_down(self):
        if self.unit_index < len(self.units):
            self.unit_index += 1
            self.info = False
        if self.scroll_index <= self.unit_index - self.num_per_page + 1 and self.scroll_index <= len(self.units) - self.num_per_page:
            self.scroll_index += 1

    def move_to_unit(self, unit):
        new_unit_index = self.units.index(unit) + 1
        if new_unit_index > self.unit_index:
            for num in xrange(new_unit_index - self.unit_index):
                self.move_down()
        elif new_unit_index < self.unit_index:
            for num in xrange(self.unit_index - new_unit_index):
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
            self.draw_state(surf, gameStateObj, metaDataObj, self.state_scroll, prev=True)
        elif self.scroll_direction < 0:
            self.draw_state(surf, gameStateObj, metaDataObj, self.state_scroll, prev=True)
        self.draw_state(surf, gameStateObj, metaDataObj, self.state_scroll)
        self.draw_banner(surf)
        self.draw_page_numbers(surf)
        self.scroll_bar.draw(surf, self.scroll_index - 1, 6, len(self.units))
        if self.state_index > 0:
            self.left_arrow.draw(surf)
        if self.state_index < len(self.states) - 1:
            self.right_arrow.draw(surf)
        self.draw_cursor(surf)

        return surf

    def draw_highlight(self, surf):
        highlightSurf = IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range(216/width): # Gives me the amount of highlight needed
            topleft = (8 + slot*width, 64 + 2 + (self.unit_index-self.scroll_index)*16)
            surf.blit(highlightSurf, topleft)

    def draw_names(self, surf):
        font = FONT['text_white']
        font.blit('Name', surf, (28, 40))
        for idx, unit in enumerate(self.units[self.scroll_index-1:self.scroll_index-1+self.num_per_page]):
            # Image
            unit_sprite = unit.sprite.create_image('passive')
            left = 8 - max(0, (unit_sprite.get_width() - 16)/2)
            top = 48 + idx*16 - max(0, (unit_sprite.get_height() - 16)/2)
            surf.blit(unit_sprite, (left, top))
            # Name
            font.blit(unit.name, surf, (24, 56 + idx*16))

    def draw_banner(self, surf):
        surf.blit(self.title_bg, (0, 0))
        title = self.states[self.state_index]
        FONT['text_brown'].blit(title, surf, (64 - FONT['text_brown'].size(title)[0]/2, 8))

    def draw_cursor(self, surf):
        self.banner_index = min(self.banner_index, len(self.help_boxes) - 1)
        if self.help_boxes and self.unit_index == 0:
            self.help_boxes[self.banner_index].draw(surf, self.info)

    def draw_page_numbers(self, surf):
        FONT['text_blue'].blit(str(self.state_index+1), surf, (208, 24))
        FONT['text_white'].blit('/', surf, (217, 24))
        FONT['text_blue'].blit(str(len(self.states)), surf, (224, 24))

    def draw_state(self, surf, gameStateObj, metaDataObj, scroll=0, prev=False):
        state_surf = Engine.create_surface((160, 112), transparent=True)
        if prev:
            state = self.states[self.prev_state_index]
        else:
            state = self.states[self.state_index]
        if state == 'Character':
            titles, offsets = self.draw_character_state(state_surf, metaDataObj)
        elif state == 'Fighting Skill':
            titles, offsets = self.draw_fighting_skill_state(state_surf, metaDataObj)
        elif state == 'Equipment':
            titles, offsets = self.draw_equipment_state(state_surf, gameStateObj)
        elif state == 'Personal Data':
            titles, offsets = self.draw_personal_data_state(state_surf, metaDataObj)
        elif state == 'Weapon Level':
            titles, offsets = self.draw_weapon_level_state(state_surf)
        elif state == 'Support Chance':
            titles, offsets = self.draw_support_chance_state(state_surf)

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

    def draw_character_state(self, surf, metaDataObj):
        # draw title
        font = FONT['text_white']
        titles = ['Class', 'Lv', 'Exp', 'HP', 'Max']
        offsets = [4, 66, 89, 113, 133]
        for idx in xrange(len(titles)):
            font.blit(WORDS[titles[idx]], surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            font.blit(unit.klass, surf, (4, top))
            FONT['text_blue'].blit(str(unit.level), surf, (80 - FONT['text_blue'].size(str(unit.level))[0], top))
            FONT['text_blue'].blit(str(unit.exp), surf, (100 - FONT['text_blue'].size(str(unit.exp))[0], top))
            c_hp = str(unit.currenthp)
            FONT['text_blue'].blit(c_hp, surf, (128 - FONT['text_blue'].size(c_hp)[0], top))
            font.blit('/', surf, (130, top))
            unit.stats['HP'].draw(surf, unit, (152, top), metaDataObj)

        return titles, offsets

    def draw_fighting_skill_state(self, surf, metaDataObj):
        font = FONT['text_white']
        titles = ['STR', 'MAG', 'SKL', 'SPD', 'LCK', 'DEF', 'RES']
        offsets = [4, 26, 48, 71, 94, 119, 142]
        for idx in xrange(len(titles)):
            font.blit(WORDS[titles[idx]], surf, (offsets[idx], 0))

        value_offsets = [16, 40, 64, 88, 112, 136, 160]
        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            for idx, stat in enumerate(titles):
                unit.stats[stat].draw(surf, unit, (value_offsets[idx] - 1, top), metaDataObj)

        return titles, offsets

    def draw_equipment_state(self, surf, gameStateObj):
        font = FONT['text_white']
        titles = ['Equip', 'Atk', 'Hit', 'Avoid']
        offsets = [16, 72, 103, 136]
        for idx in xrange(len(titles)):
            font.blit(WORDS[titles[idx]], surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            item = unit.getMainWeapon()
            if item:
                item.draw(surf, (1, top))
                font.blit(item.name, surf, (16, top))
            else:
                font.blit('--', surf, (16, top))
            atk, hit, avoid = str(unit.damage(gameStateObj)), str(unit.accuracy(gameStateObj)), str(unit.avoid(gameStateObj))
            FONT['text_blue'].blit(atk, surf, (88 - FONT['text_blue'].size(atk)[0], top))
            FONT['text_blue'].blit(hit, surf, (120 - FONT['text_blue'].size(hit)[0], top))
            FONT['text_blue'].blit(avoid, surf, (152 - FONT['text_blue'].size(avoid)[0], top))

        return titles, offsets

    def draw_personal_data_state(self, surf, metaDataObj):
        font = FONT['text_white']
        titles = ['MOV', 'CON', 'Aid', 'Rat', 'Trv']
        offsets = [4, 33, 60, 82, 106]
        for idx in xrange(len(titles)):
            font.blit(WORDS[titles[idx]], surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            unit.stats['MOV'].draw(surf, unit, (24, top), metaDataObj)
            unit.stats['CON'].draw(surf, unit, (48, top), metaDataObj)
            aid = str(unit.getAid())
            FONT['text_blue'].blit(aid, surf, (72 - FONT['text_blue'].size(aid)[0], top))
            rat = str(unit.get_rating())
            FONT['text_blue'].blit(rat, surf, (100 - FONT['text_blue'].size(rat)[0], top))
            FONT['text_white'].blit(unit.strTRV, surf, (106, top))

        return titles, offsets

    def draw_weapon_level_state(self, surf):
        titles = CustomObjects.WEAPON_TRIANGLE.types
        offsets = [9 + idx*16 for idx in xrange(len(titles))]

        for idx, weapon_icon in enumerate(self.weapon_icons):
            weapon_icon.draw(surf, (offsets[idx], 0))

        for idx, unit in enumerate(self.avail_units()):
            top = idx*16 + 16
            for index, wexp in enumerate(unit.wexp):
                if wexp > 0:
                    wexpLetter = CustomObjects.WEAPON_EXP.number_to_letter(wexp)
                else:
                    wexpLetter = '-'
                pos = (24 + index*16 - FONT['text_blue'].size(wexpLetter)[0], top)
                FONT['text_blue'].blit(wexpLetter, surf, pos)

        return titles, offsets

    def draw_support_chance_state(self, surf):
        titles = ['Ally']
        offsets = [0]

        return titles, offsets

    def summon_help_boxes(self, titles, offsets):
        if not self.help_boxes:
            self.help_boxes.append(InfoMenu.Help_Box('Name', (28 - 15, 40), InfoMenu.create_help_box(WORDS['Name_desc'])))
            for idx in xrange(len(titles)):
                self.help_boxes.append(InfoMenu.Help_Box(titles[idx], (offsets[idx] + 64 - 15, 40), InfoMenu.create_help_box(WORDS[titles[idx] + '_desc'])))
