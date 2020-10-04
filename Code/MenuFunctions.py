import collections

from . import GlobalConstants as GC
from . import configuration as cf
from . import Image_Modification, Utility, Engine, Counters, TextChunk
from . import HelpMenu, GUIObjects
from . import CustomObjects, Action, Weapons
from . import ItemMethods
from . import BaseMenuSurf

import logging
logger = logging.getLogger(__name__)

def OutlineFont(FONTNAME, text, surf, innercolor, outercolor, position):
    """ renders and blits outlined text based on the position.
        Assumes position is topleft"""
    if outercolor:
        outer_text = FONTNAME.render(text, True, outercolor)
        surf.blit(outer_text, (position[0] - 1, position[1] + 1))
        surf.blit(outer_text, (position[0] + 1, position[1] + 1))
        surf.blit(outer_text, (position[0] + 1, position[1] - 1))
        surf.blit(outer_text, (position[0] - 1, position[1] - 1))
    # inner_text
    inner_text = FONTNAME.render(text, True, innercolor)
    surf.blit(inner_text, position)
    return position

def build_cd_groove(surf, topleft, width, fill, reverse):
    if reverse:
        fgs_mid = GC.IMAGESDICT['StatGrooveFillRed']
    else:
        fgs_mid = GC.IMAGESDICT['StatGrooveFillGreen']
    fgs_mid = Engine.subsurface(fgs_mid, (0, 0, 1, 1))
    back_groove_surf = GC.IMAGESDICT['StatGrooveBackSmall']
    bgs_start = Engine.subsurface(back_groove_surf, (0, 0, 1, 3))
    bgs_mid = Engine.subsurface(back_groove_surf, (1, 0, 1, 3))
    bgs_end = Engine.subsurface(back_groove_surf, (2, 0, 1, 3))

    # Build back groove
    start_pos = topleft
    surf.blit(bgs_start, start_pos)
    for index in range(width - 2):
        mid_pos = (topleft[0] + bgs_start.get_width() + bgs_mid.get_width()*index, topleft[1])
        surf.blit(bgs_mid, mid_pos)
    end_pos = (topleft[0] + bgs_start.get_width() + bgs_mid.get_width()*(width-2), topleft[1])
    surf.blit(bgs_end, end_pos)

    # Build fill groove
    if fill == width:
        number_of_fgs_needed = int(fill - 2)
    else:
        number_of_fgs_needed = int(fill - 1) # Width of groove minus section for start and end of back groove
    for groove in range(number_of_fgs_needed):
        surf.blit(fgs_mid, (topleft[0] + bgs_start.get_width() + groove, topleft[1] + 1))

class Logo(object):
    def __init__(self, texture, center):
        self.texture = texture
        self.center = center

        self.image = None
        self.height = self.texture.get_height()//8
        self.width = self.texture.get_width()

        self.logo_counter = 0
        self.logo_anim = [0, 0, 1, 2, 3, 4, 5, 6, 7, 7, 6, 5, 4, 3, 2, 1]
        self.last_update = 0

        self.image = Engine.subsurface(self.texture, (0, self.logo_anim[self.logo_counter]*self.height, self.texture.get_width(), self.height))

        self.state = "Idle"

    def update(self):
        currentTime = Engine.get_time()

        if currentTime - self.last_update > 64:
            self.logo_counter += 1
            if self.logo_counter >= len(self.logo_anim):
                self.logo_counter = 0
            self.image = Engine.subsurface(self.texture, (0, self.logo_anim[self.logo_counter]*self.height, self.width, self.height))
            self.last_update = currentTime

        if self.state == "Idle":
            self.draw_image = self.image

        elif self.state == "Out":
            self.transition_counter -= 1

            self.draw_image = Engine.subsurface(self.image, (0, self.height//2 - self.transition_counter, self.width, self.transition_counter*2))

            if self.transition_counter <= 0:
                self.state = "In"
                self.texture = self.new_texture
                self.height = self.new_height
                self.width = self.new_width
                self.image = Engine.subsurface(self.texture, (0, self.logo_anim[self.logo_counter]*self.height, self.width, self.height))

        elif self.state == "In":
            self.transition_counter += 1
            if self.transition_counter >= self.height//2:
                self.transition_counter = self.height//2
                self.state = "Idle"

            self.draw_image = Engine.subsurface(self.image, (0, self.height//2 - self.transition_counter, self.width, self.transition_counter*2))

    def draw(self, surf, offset_y=0):
        surf.blit(self.draw_image, (self.center[0] - self.draw_image.get_width()//2, self.center[1] - self.draw_image.get_height()//2 + offset_y))

    def switch_image(self, new_image):
        self.new_texture = new_image
        self.new_height = self.new_texture.get_height()//8
        self.new_width = self.new_texture.get_width()
        self.transition_counter = self.height//2
        self.state = "Out"

class BriefPopUpDisplay(object):
    def __init__(self, topright):
        self.topright = topright
        self.update_num = -200

    def start(self, text):
        self.update_num = 100
        if isinstance(text, int):
            money = text
            if money >= 0:
                font = GC.FONT['text_green']
            else:
                font = GC.FONT['text_red']
            my_str = str(money)
            if money >= 0:
                my_str = '+' + my_str
        else:
            font = GC.FONT['text_blue']
            my_str = str(text)
        str_size = font.size(my_str)[0]
        self.surf = Engine.create_surface((str_size + 8, 16), transparent=True)
        self.width = self.surf.get_width()
        font.blit(my_str, self.surf, (0, 0))

    def draw(self, surf):
        if self.update_num > -200:
            self.update_num -= 5
            # Fade in and move up
            if self.update_num > 0:
                my_surf = Image_Modification.flickerImageTranslucent(self.surf, self.update_num)
                surf.blit(my_surf, (self.topright[0] - self.width + 8, self.topright[1] + self.update_num//5))
            # Fade out
            else:
                if self.update_num < -100:
                    my_surf = Image_Modification.flickerImageTranslucent(self.surf, -self.update_num - 100)
                else:
                    my_surf = self.surf
                surf.blit(my_surf, (self.topright[0] - self.width + 8, self.topright[1]))

class Lore_Display(object):
    def __init__(self, starting_entry):
        self.topleft = (72, 4)
        self.menu_width = GC.WINWIDTH - 72 - 4
        self.back_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, GC.WINHEIGHT - 8))

        self.update_entry(starting_entry)

    def update_entry(self, entry):
        self.image = self.back_surf.copy()
        if entry['type'] == cf.WORDS['Character']:
            current_image = GC.UNITDICT[entry['short_name'] + 'Portrait']
            current_image = Engine.subsurface(current_image, (0, 0, 96, 80))
            current_image = Image_Modification.flickerImageTranslucentColorKey(current_image, 50)
            self.image.blit(current_image, (self.menu_width - 96, GC.WINHEIGHT - 8 - 80 - 4))

        GC.FONT['text_yellow'].blit(entry['long_name'], self.image, (self.menu_width//2 - GC.FONT['text_yellow'].size(entry['long_name'])[0]//2, 4))

        output_lines = TextChunk.line_wrap(TextChunk.line_chunk(entry['desc']), self.menu_width - 12, GC.FONT['text_white'])
        if entry['type'] == cf.WORDS['Character']:
            first_section = output_lines[:4]
            second_section = output_lines[4:]
            if second_section:
                second_section = TextChunk.line_wrap(TextChunk.line_chunk(' '.join(second_section)), self.menu_width - 80, GC.FONT['text_white'])
            output_lines = first_section + second_section

        # Now draw
        for index, line in enumerate(output_lines):
            GC.FONT['text_white'].blit(''.join(line), self.image, (4, GC.FONT['text_white'].height*index + 4 + 16))

    def draw(self, surf):
        surf.blit(self.image, self.topleft)

# === MENUS ============================================================ ###
# Abstract menu class. Must implement personal draw function
class SimpleMenu(Counters.CursorControl):
    def __init__(self, owner, options, topleft, background='BaseMenuBackground'):
        self.options = options
        self.owner = owner
        self.topleft = topleft
        self.currentSelection = 0
        self.background = background

        Counters.CursorControl.__init__(self)
        self.cursor_y_offset = 0

        self.menu_width = self.getMenuWidth()

    def getMenuWidth(self):
        longest_width_needed = 16
        for option in self.options:
            if isinstance(option, ItemMethods.ItemObject): # If it is an item
                return 104 # This is the recommended menu width for items
            else:
                option_width = GC.FONT['text_white'].size(option)[0]
                if option_width > longest_width_needed:
                    longest_width_needed = option_width

        return (longest_width_needed - longest_width_needed%8 + 24)

    def getSelection(self):
        if self.currentSelection > len(self.options) - 1:
            self.currentSelection = len(self.options) - 1
        if self.currentSelection < 0:
            self.currentSelection = 0
        if self.options:
            return self.options[self.currentSelection]
        else:
            return None

    def getSelectionIndex(self):
        return self.currentSelection

    def setSelection(self, option):
        if option in self.options:
            idx = self.options.index(option)
            self.currentSelection = idx

    def moveDown(self, first_push=True):
        if first_push:
            self.currentSelection += 1
            if self.currentSelection > len(self.options) - 1:
                self.currentSelection = 0
            else:
                self.cursor_y_offset = -1
        else:
            self.currentSelection = min(self.currentSelection + 1, len(self.options) - 1)

    def moveUp(self, first_push=True):
        if first_push:
            self.currentSelection -= 1
            if self.currentSelection < 0:
                self.currentSelection = len(self.options) - 1
            else:
                self.cursor_y_offset = 1
        else:
            self.currentSelection = max(self.currentSelection - 1, 0)

    def updateOptions(self, options):
        self.options = options
        self.menu_width = self.getMenuWidth()
        self.currentSelection = Utility.clamp(self.currentSelection, 0, len(self.options) - 1)

    def draw_cursor(self, surf, index):
        surf.blit(self.cursor, (self.topleft[0] - 12 + self.cursorAnim[self.cursorCounter], self.topleft[1] + 7 + index*16 + self.cursor_y_offset*8))
        self.cursor_y_offset = 0 # Reset

    def draw_highlight(self, surf, index):
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range((self.menu_width - 10)//width): # Gives me the amount of highlight needed
            topleft = (self.topleft[0] + 5 + slot*width, self.topleft[1] + 12 + index*16 + 1)
            surf.blit(highlightSurf, topleft)

class ChoiceMenu(SimpleMenu):
    def __init__(self, owner, options, topleft, gameStateObj=None, horizontal=False,
                 background='BaseMenuBackgroundOpaque', limit=None, hard_limit=False,
                 info_desc=None, color_control=None, ignore=None, width=None, shimmer=0,
                 gem=True, disp_total_uses=False):
        self.set_width = width
        self.disp_total_uses = disp_total_uses
        info_desc = info_desc or []

        SimpleMenu.__init__(self, owner, options, topleft, background)

        self.horizontal = horizontal

        if self.horizontal: # Does not support items
            self.bg_surf = BaseMenuSurf.CreateBaseMenuSurf((GC.FONT['text_white'].size('  '.join(self.options))[0] + 16, 24), background)
        else:
            if limit and (len(self.options) > limit or hard_limit):
                height = (8 + 16*limit)
            else:
                height = (8 + 16*len(self.options))
            # Add small gem
            bg_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, height), background)
            self.bg_surf = Engine.create_surface((bg_surf.get_width() + 2, bg_surf.get_height() + 4), transparent=True, convert=True)
            self.bg_surf.blit(bg_surf, (2, 4))
            if gem:
                self.bg_surf.blit(GC.IMAGESDICT['SmallGem'], (0, 0))
            if shimmer:
                img = GC.IMAGESDICT['Shimmer' + str(shimmer)]
                self.bg_surf.blit(img, (self.bg_surf.get_width() - 1 - img.get_width(), self.bg_surf.get_height() - 5 - img.get_height()))
            # Now make translucent
            self.bg_surf = Image_Modification.flickerImageTranslucent(self.bg_surf, 10)

        self.color_control = color_control
        self.ignore = ignore

        self.info_flag = False
        self.help_boxes = []
        for index, desc in enumerate(self.options):
            if isinstance(self.options[index], ItemMethods.ItemObject):
                self.help_boxes.append(self.options[index].get_help_box())
            elif len(info_desc) > index:
                self.help_boxes.append(HelpMenu.Help_Dialog(info_desc[index]))

        self.takes_input = True
        self.draw_face = False

        # For Scroll Bar
        self.limit = limit
        self.scroll = 0

        self.get_topleft(gameStateObj)

        self.scroll_bar = GUIObjects.ScrollBar((self.menu_width + self.topleft[0], self.topleft[1] + 6))

    def getMenuWidth(self):
        longest_width_needed = 16
        if self.set_width:
            return self.set_width
        for option in self.options:
            if isinstance(option, ItemMethods.ItemObject): # If it is an item
                if self.disp_total_uses:
                    return 120
                else:
                    return 104 # This is the recommended menu width for items
            else:
                option_width = GC.FONT['text_white'].size(option)[0]
                if option_width > longest_width_needed:
                    longest_width_needed = option_width
        return (longest_width_needed - longest_width_needed%8 + 24)

    def get_topleft(self, gameStateObj):
        if self.topleft == 'auto':
            if gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.x:
                self.topleft = (8, 8)
            else:
                self.topleft = (GC.WINWIDTH - self.menu_width - 8, 8)
        elif self.topleft == 'child':
            if gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.x:
                self.topleft = (8 + gameStateObj.activeMenu.menu_width - 32, gameStateObj.activeMenu.currentSelection*16 + 8)
            else:
                self.topleft = (GC.WINWIDTH - 32 - 8 - gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.currentSelection*16 + 8)
        elif self.topleft == 'center':
            self.topleft = (GC.WINWIDTH//2 - self.menu_width//2, GC.WINHEIGHT//2 - (len(self.options)*16)//2)

    def toggle_info(self):
        self.info_flag = not self.info_flag
        if self.info_flag:
            GC.SOUNDDICT['Info In'].play()
        else:
            GC.SOUNDDICT['Info Out'].play()

    def moveDown(self, first_push=True):
        SimpleMenu.moveDown(self, first_push)
        if self.limit:
            if self.currentSelection >= self.scroll + self.limit - 1:
                self.scroll += 1
            elif self.currentSelection == 0:
                self.scroll = 0
            self.scroll = Utility.clamp(self.scroll, 0, max(0, len(self.options) - self.limit))

        if self.ignore and self.ignore[self.currentSelection] and not all(self.ignore):
            self.moveDown()

        if not self.options:
            self.scroll = 0
            self.currentSelection = 0

    def moveUp(self, first_push=True):
        SimpleMenu.moveUp(self, first_push)
        if self.limit:
            if self.currentSelection < self.scroll + 1:
                self.scroll -= 1
            # To account for moving from top to bottom
            elif self.currentSelection >= len(self.options) - 1:
                self.scroll = self.currentSelection - self.limit + 1
            self.scroll = max(self.scroll, 0) # Scroll cannot go negative

        if self.ignore and self.ignore[self.currentSelection] and not all(self.ignore):
            self.moveUp()

        if not self.options:
            self.scroll = 0
            self.currentSelection = 0

    def updateOptions(self, options):
        self.options = options
        self.menu_width = self.getMenuWidth()
        self.currentSelection = Utility.clamp(self.currentSelection, 0, len(self.options) - 1)

        if not self.options:
            self.scroll = 0
            self.currentSelection = 0

    def moveTo(self, index):
        self.currentSelection = index
        self.scroll = index
        if self.limit:
            self.scroll = Utility.clamp(self.scroll, 0, max(0, len(self.options) - self.limit))

    def draw(self, surf, gameStateObj=None):
        if self.horizontal:
            self.horiz_draw(surf)
        else:
            self.vert_draw(surf)

    def drawInfo(self, surf):
        if self.info_flag:
            help_box = self.help_boxes[self.currentSelection]

            if self.topleft[0] < GC.WINWIDTH//2:
                help_box.draw(surf, (self.topleft[0], self.topleft[1] + 20 + 16*self.currentSelection))
            else:
                help_box.draw(surf, (self.topleft[0] + self.menu_width - help_box.get_width(), self.topleft[1] + 20 + 16*self.currentSelection))

    def drawFace(self, surf):
        face_image = self.owner.bigportrait.copy()
        face_image = Engine.flip_horiz(face_image)
        face_image = Image_Modification.flickerImageTranslucentColorKey(face_image, 50)
        left = self.topleft[0] + self.bg_surf.get_width()//2 - face_image.get_width()//2
        top = self.topleft[1] + self.bg_surf.get_height()//2 - face_image.get_height()//2 - 3
        surf.blit(face_image, (left, top))

    def vert_draw(self, surf):
        surf.blit(self.bg_surf, (self.topleft[0] - 2, self.topleft[1] - 4)) # To account for small gem
        if self.draw_face:
            self.drawFace(surf)
        if self.takes_input:
            self.draw_highlight(surf, self.currentSelection-self.scroll)
        if self.limit and len(self.options) > self.limit:
            self.scroll_bar.draw(surf, self.scroll, self.limit, len(self.options))
        if self.options:
            choices = self.options[self.scroll:self.scroll+self.limit] if self.limit else self.options
            for index, option in enumerate(choices):
                top = self.topleft[1] + 4 + 16*index
                left = self.topleft[0]
                # Text
                if isinstance(option, ItemMethods.ItemObject):
                    option.draw(surf, (left + 2, top))
                    main_font = GC.FONT['text_grey']
                    uses_font = GC.FONT['text_grey']
                    if self.color_control:
                        main_font = GC.FONT[self.color_control[index+self.scroll]]
                        uses_font = GC.FONT[self.color_control[index+self.scroll]]
                        if uses_font == GC.FONT['text_white']:
                            uses_font = GC.FONT['text_blue']
                    elif self.owner.canWield(option) and self.owner.canUse(option):
                        main_font = GC.FONT['text_white']
                        uses_font = GC.FONT['text_blue']
                    main_font.blit(str(option), surf, (left + 20, top))
                    if self.disp_total_uses:
                        uses_string = "--/--"
                        if option.uses:
                            uses_string = str(option.uses) + '/' + str(option.uses.total_uses)
                        elif option.c_uses:
                            uses_string = str(option.c_uses) + '/' + str(option.c_uses.total_uses)
                        elif option.cooldown:
                            top -= 2
                            if option.cooldown.charged:
                                uses_font = GC.FONT['text_light_green']
                                uses_string = str(option.cooldown.cd_uses) + '/' + str(option.cooldown.total_cd_uses)
                            else:
                                uses_font = GC.FONT['text_light_red']
                                uses_string = str(option.cooldown.cd_turns) + '/' + str(option.cooldown.total_cd_turns)
                    else:
                        uses_string = "--"
                        if option.uses:
                            uses_string = str(option.uses)
                        elif option.c_uses:
                            uses_string = str(option.c_uses)
                        elif option.cooldown:
                            top -= 2
                            if option.cooldown.charged:
                                uses_font = GC.FONT['text_light_green']
                                uses_string = str(option.cooldown.cd_uses)
                            else:
                                uses_font = GC.FONT['text_light_red']
                                uses_string = str(option.cooldown.cd_turns)
                    pos = (left + self.menu_width - 4 - uses_font.size(uses_string)[0] - (5 if self.limit and len(self.options) > self.limit else 0), top)
                    uses_font.blit(uses_string, surf, pos)
                    # Draw cooldown groove
                    if option.cooldown:
                        if option.cooldown.charged:
                            build_cd_groove(surf, (left + self.menu_width - 19 - (5 if self.limit and len(self.options) > self.limit else 0), pos[1] + 14), 16,
                                            int(round((int(option.cooldown.cd_uses) / int(option.cooldown.total_cd_uses)) * 16)), False)
                        else:
                            build_cd_groove(surf, (left + self.menu_width - 19 - (5 if self.limit and len(self.options) > self.limit else 0), pos[1] + 14), 16,
                                            int(round((int(option.cooldown.cd_turns) / int(option.cooldown.total_cd_turns)) * 16)), True)
                else:
                    if self.color_control:
                        main_font = GC.FONT[self.color_control[index+self.scroll]]
                    elif option == cf.WORDS['Nothing']:
                        main_font = GC.FONT['text_grey']
                    else:
                        main_font = GC.FONT['text_white']
                    main_font.blit(str(option), surf, (left + 6, top))
        else:
            GC.FONT['text_grey'].blit(cf.WORDS['Nothing'], surf, (self.topleft[0] + 16, self.topleft[1] + 4))
        if self.takes_input:
            self.draw_cursor(surf, self.currentSelection-self.scroll)

    def horiz_draw(self, surf):
        surf.blit(self.bg_surf, self.topleft)

        """# blit background highlight
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        highlightRect = highlightSurf.get_rect()
        for slot in range((GC.FONT['text_white'].size(self.options[self.currentSelection]))[0]/highlightRect.width):
            option_left = GC.FONT['text_white'].size('  '.join(self.options[:self.currentSelection]) + ' ')[0] # determines width of all previous options
            highlightRect.topleft = (self.topleft[0] + 8 + slot*highlightRect.width + option_left, self.topleft[1] + 11)
            surf.blit(highlightSurf, highlightRect)"""

        # Blit options
        GC.FONT['text_white'].blit('  '.join(self.options), surf, (self.topleft[0] + 4, self.topleft[1] + 4))

        # blit cursor
        left_options = self.options[:self.currentSelection]
        option_left = sum(GC.FONT['text_white'].size(option)[0] for option in left_options) + \
            sum(GC.FONT['text_white'].size('  ')[0] for option in left_options)
        topleft = (self.topleft[0] - 16 + option_left + self.cursorAnim[self.cursorCounter], self.topleft[1] + 5)
        surf.blit(self.cursor, topleft)

class ComplexMenu(SimpleMenu):
    def __init__(self, owner, options, topleft, background='BaseMenuBackground'):
        SimpleMenu.__init__(self, owner, options, topleft, background)

    def isIndexValid(self, index):
        return True

    def getMenuWidth(self):
        longest_width_needed = 16
        for option in self.options:
            if hasattr(option, 'name'):
                option_width = GC.FONT['text_white'].size(option.name)[0]
            else:
                option_width = GC.FONT['text_white'].size(option)[0]
            if hasattr(option, 'draw'):
                option_width += 16
            if option_width > longest_width_needed:
                longest_width_needed = option_width

        return (longest_width_needed - longest_width_needed%8 + 16)

    def moveUp(self, first_push=True):
        split_num = len(self.options)//2
        if self.currentSelection < split_num and self.currentSelection > 0:
            next_selection = self.currentSelection - 1
            while not self.isIndexValid(next_selection):
                next_selection -= 1
                if next_selection < 0:
                    return
            self.currentSelection = next_selection
        elif self.currentSelection > split_num:
            next_selection = self.currentSelection - 1
            while not self.isIndexValid(next_selection):
                next_selection -= 1
                if next_selection < split_num:
                    return
            self.currentSelection = next_selection

    def moveDown(self, first_push=True):
        split_num = len(self.options)//2
        if self.currentSelection < split_num - 1:
            next_selection = self.currentSelection + 1
            while not self.isIndexValid(next_selection):
                next_selection += 1
                if next_selection > split_num - 1:
                    return
            self.currentSelection = next_selection
        elif self.currentSelection < len(self.options) - 1 and self.currentSelection > split_num - 1:
            next_selection = self.currentSelection + 1
            while not self.isIndexValid(next_selection):
                next_selection += 1
                if next_selection > len(self.options) - 1:
                    return
            self.currentSelection = next_selection

    def moveRight(self, first_push=True):
        split_num = len(self.options)//2
        if self.currentSelection < split_num:
            next_selection = self.currentSelection + split_num
            valid_indices = [index for index in range(split_num, len(self.options)) if self.isIndexValid(index)]
            if valid_indices:
                self.currentSelection = min(valid_indices, key=lambda x: abs(x-next_selection))

    def moveLeft(self, first_push=True):
        split_num = len(self.options)//2
        if self.currentSelection > split_num - 1:
            next_selection = self.currentSelection - split_num
            valid_indices = [index for index in range(0, split_num) if self.isIndexValid(index)]
            if valid_indices:
                self.currentSelection = min(valid_indices, key=lambda x: abs(x-next_selection))

    def draw_cursor(self, surf, index):
        split_num = len(self.options)//2
        x_position = self.topleft[0] - 12 + (index//split_num)*self.menu_width + self.cursorAnim[self.cursorCounter]
        y_position = self.topleft[1] + 8 + (index%split_num)*16
        surf.blit(self.cursor, (x_position, y_position))

    def draw_highlight(self, surf, index):
        split_num = len(self.options)//2
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range((self.menu_width - 16)//width): # Gives me the amount of highlight needed
            x_position = 8 + (index//split_num)*self.menu_width + slot*width
            y_position = 12 + (index%split_num)*16
            surf.blit(highlightSurf, (x_position, y_position))

    def draw(self, surf):
        split_num = len(self.options)//2
        BGSurf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width*2, 16*split_num+8), self.background)
        self.draw_highlight(BGSurf, self.currentSelection)

        for index, option in enumerate(self.options):
            position = 4+(index//split_num)*self.menu_width, 4 + index%split_num*16
            # Draw icon if possible
            if hasattr(option, 'draw'):
                option.draw(BGSurf, position)
            # Draw text
            font = GC.FONT['text_white']
            if not self.isIndexValid(index):
                font = GC.FONT['text_grey']
            left = position[0] + (16 if hasattr(option, 'draw') else 0)
            if hasattr(option, 'name'):
                font.blit(option.name, BGSurf, (left, position[1]))
            else:
                font.blit(option, BGSurf, (left, position[1]))
        surf.blit(BGSurf, self.topleft)
        self.draw_cursor(surf, self.currentSelection)

class GreyMenu(ComplexMenu):
    def __init__(self, owner, option, topleft, grayed_out, background='BaseMenuBackground'):
        ComplexMenu.__init__(self, owner, option, topleft, background)
        self.grayed_out = grayed_out

    def isIndexValid(self, index):
        return self.grayed_out[index]

    def update_grey(self, index, value):
        self.grayed_out[index] = value
        # Handle if the current Selection ends up on a grayed out index
        orig_index = self.currentSelection
        while not self.grayed_out[self.currentSelection]:
            self.currentSelection -= 1
            if self.currentSelection == orig_index:
                break # Just give up
            if self.currentSelection < 0:
                self.currentSelection = len(self.options) - 1

class FeatChoiceMenu(ComplexMenu):
    def __init__(self, owner, options):
        self.options = options
        menu_width = self.getMenuWidth()
        ComplexMenu.__init__(self, owner, options, (GC.WINWIDTH//2 - menu_width, GC.WINHEIGHT - len(options)//2*16 - 8), 'BaseMenuBackground')
        # Place index at valid position
        for idx, option in enumerate(self.options):
            if self.isIndexValid(idx):
                self.currentSelection = idx
                break

    def isIndexValid(self, index):
        return not self.options[index].id in [status.id for status in self.owner.status_effects]

    def getMenuWidth(self):
        longest_width_needed = 16
        for option in self.options:
            option_width = GC.FONT['text_white'].size(option.name)[0] + 16 + 4
            if option_width > longest_width_needed:
                longest_width_needed = option_width

        return (longest_width_needed - longest_width_needed%8 + 8)

    def draw(self, surf, gameStateObj):
        ComplexMenu.draw(self, surf)
        self.draw_face(surf)
        self.draw_label(surf)

    # Draw face
    def draw_face(self, surf):
        face_position_x = self.topleft[0] + self.menu_width - self.owner.bigportrait.get_width()//2
        face_position_y = self.topleft[1] - self.owner.bigportrait.get_height() + 8
        face_image = Engine.subsurface(self.owner.bigportrait, (0, 0, self.owner.bigportrait.get_width(), self.owner.bigportrait.get_height() - 8))
        surf.blit(face_image, (face_position_x, face_position_y))

    def draw_label(self, surf):
        label = cf.WORDS['Feat Choice']
        width = GC.FONT['text_white'].size(label)[0]
        menu_width = width - width%8 + 16
        bg_surf = BaseMenuSurf.CreateBaseMenuSurf((menu_width, 24))
        GC.FONT['text_white'].blit(label, bg_surf, (menu_width//2 - width//2, 4))
        surf.blit(bg_surf, (0, 0))

class ModeSelectMenu(SimpleMenu):
    def __init__(self, options, toggle, default=0):
        self.options = options
        self.toggle = toggle
        self.currentSelection = default

        self.label = BaseMenuSurf.CreateBaseMenuSurf((96, 88), 'BaseMenuBackgroundOpaque')
        shimmer = GC.IMAGESDICT['Shimmer2']
        self.label.blit(shimmer, (96 - shimmer.get_width() - 1, 88 - shimmer.get_height() - 5))
        self.label = Image_Modification.flickerImageTranslucent(self.label, 10)

        self.cursor = GC.IMAGESDICT['dragonCursor']
        self.cursorCounter = 0 # Helper counter for cursor animation
        self.cursorAnim = [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()
        self.cursor_y_offset = 0

    def isIndexValid(self, index):
        return self.toggle[index]

    def update(self):
        currentTime = Engine.get_time()
        if currentTime - self.lastUpdate > 100:
            self.lastUpdate = currentTime
            self.cursorCounter += 1
            if self.cursorCounter > len(self.cursorAnim) - 1:
                self.cursorCounter = 0

    def moveDown(self):
        self.currentSelection += 1
        if self.currentSelection > len(self.options) - 1:
            self.currentSelection = 0
            if not self.isIndexValid(self.currentSelection):
                self.currentSelection = len(self.options) - 1
        else:
            if not self.isIndexValid(self.currentSelection):
                self.currentSelection -= 1
                return
            self.cursor_y_offset = -1

    def moveUp(self):
        self.currentSelection -= 1
        if self.currentSelection < 0:
            self.currentSelection = len(self.options) - 1
            if not self.isIndexValid(self.currentSelection):
                self.currentSelection = 0
        else:
            if not self.isIndexValid(self.currentSelection):
                self.currentSelection += 1
                return
            self.cursor_y_offset = 1

    def draw(self, surf):
        top = 52 + (3-len(self.options))*16
        for index, option in enumerate(self.options):
            left = 8
            if index == self.currentSelection:
                background = GC.IMAGESDICT['DarkMenuHighlightShort']
            else:
                background = GC.IMAGESDICT['DarkMenuShort']
            if self.isIndexValid(index):
                font = GC.FONT['chapter_grey']
            else:
                font = GC.FONT['chapter_black']
            width = background.get_width()
            surf.blit(background, (left, top+index*32))
            font.blit(option, surf, (left + width//2 - font.size(option)[0]//2, top+4+index*32))

        # Draw cursor
        height = top - 16 + self.currentSelection*32 + self.cursorAnim[self.cursorCounter] + self.cursor_y_offset*16
        surf.blit(self.cursor, (0, height))
        self.cursor_y_offset = 0 # Reset

        # Draw gem
        surf.blit(self.label, (142, 52))
        # surf.blit(GC.IMAGESDICT['SmallGem'], (139, 48))
        # Draw text
        text = cf.WORDS['mode_' + self.options[self.currentSelection]]
        text_lines = TextChunk.line_wrap(TextChunk.line_chunk(text), 88, GC.FONT['text_white'])
        for index, line in enumerate(text_lines):
            GC.FONT['text_white'].blit(line, surf, (142 + 4, 52 + 4 + index*16))

# Support Conversation Menu
class SupportMenu(object):
    def __init__(self, owner, gameStateObj, topleft, background='BaseMenuBackgroundOpaque'):
        self.owner = owner
        self.updateOptions(gameStateObj)
        self.topleft = topleft
        self.back_surf = BaseMenuSurf.CreateBaseMenuSurf((136, 136), background)
        shimmer = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(shimmer, (136 - shimmer.get_width() - 1, 136 - shimmer.get_height() - 5))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.cursor = GC.IMAGESDICT['menuHand']
        self.cursor_flag = False

    def moveDown(self, first_push=True):
        self.currentSelection += 1
        if self.currentSelection > len(self.options) - 1:
            if first_push:
                self.currentSelection = 0
            else:
                self.currentSelection -= 1
        # Check limit for new row
        limit = max(0, self.options[self.currentSelection][2].available_support_level() - 1)
        self.currentLevel = Utility.clamp(self.currentLevel, 0, limit)

    def moveUp(self, first_push=True):
        self.currentSelection -= 1
        if self.currentSelection < 0:
            if first_push:
                self.currentSelection = len(self.options) - 1
            else:
                self.currentSelection += 1
        # Check limit for new row
        limit = max(0, self.options[self.currentSelection][2].available_support_level() - 1)
        self.currentLevel = Utility.clamp(self.currentLevel, 0, limit)

    def moveRight(self, first_push=True):
        self.currentLevel += 1
        limit = max(0, self.options[self.currentSelection][2].available_support_level() - 1)
        self.currentLevel = Utility.clamp(self.currentLevel, 0, limit)

    def moveLeft(self, first_push=True):
        self.currentLevel -= 1
        if self.currentLevel < 0:
            self.currentLevel = 0
            return False
        return True

    def getSelection(self):
        return self.options[self.currentSelection][0], self.currentLevel

    def updateOptions(self, gameStateObj):
        self.currentSelection = 0
        self.currentLevel = 0

        ids = sorted(gameStateObj.support.node_dict[self.owner.id].adjacent)
        # convert names to units
        self.options = []
        for other_id in ids:
            other_unit = None
            for unit in gameStateObj.allunits:
                if unit.team == 'player' and other_id == unit.id:
                    other_unit = unit
                    break
            # if gameStateObj.support.node_dict[name].dead:
            #     pass
            # else:
            #     continue
            # We haven't found unit yet, so just skip
            affinity = gameStateObj.support.node_dict[other_id].affinity
            edge = gameStateObj.support.node_dict[self.owner.id].adjacent[other_id]
            self.options.append((other_unit, affinity, edge))

    def update(self):
        pass

    def draw(self, surf, gameStateObj):
        back_surf = self.back_surf.copy()
        units = []
        for index, (unit, affinity, edge) in enumerate(self.options):
            # Blit passive sprite
            unit_image = topleft = None
            if unit:
                unit_sprite = unit.sprite
                unit_image = unit_sprite.create_image('passive')
                if index == self.currentSelection and self.cursor_flag:
                    unit_image = unit_sprite.create_image('active')
                if gameStateObj.support.node_dict[unit.id].dead:
                    unit_image = unit_sprite.create_image('gray')
                topleft = (4 - 24, 16 + 2 + (index+1)*16 - unit_image.get_height())
            units.append((unit_image, topleft))

            # Blit name
            position = (24 + 1, 4 + index*16 + 8)
            if unit:
                GC.FONT['text_white'].blit(unit.name, back_surf, position)
            else:
                GC.FONT['text_white'].blit('---', back_surf, position)

            # Blit Affinity
            affinity.draw(back_surf, (72, 3 + index*16 + 8))

            # Blit LVS
            letters = ['@', '`', '~', '%'] # C, B, A, S
            limit = len(edge.support_limits)
            letters = letters[:limit]
            for level, letter in enumerate(letters):
                if unit and gameStateObj.support.can_support(unit.id, self.owner.id) and edge.support_level == level:
                    font = GC.FONT['text_green']
                elif edge.support_level > level:
                    font = GC.FONT['text_white']
                else:
                    font = GC.FONT['text_grey']
                font.blit(letter, back_surf, (90 + level*10, 4 + index*16 + 8))

        surf.blit(back_surf, self.topleft)
        for unit in units:
            if unit[0]:
                surf.blit(unit[0], (self.topleft[0] + unit[1][0], self.topleft[1] + unit[1][1]))

        # Blit Name -- Affin -- LV
        if GC.IMAGESDICT.get('SupportWords'):
            surf.blit(GC.IMAGESDICT['SupportWords'], (104, 12))

        # Blit cursor
        if self.cursor_flag:
            left = self.currentLevel*10 + self.topleft[0] + 100 - 12 - 10
            top = self.currentSelection*16 + self.topleft[1] + 4 + 8
            surf.blit(self.cursor, (left, top))

# Simple start menu
class MainMenu(object):
    def __init__(self, options, background):
        self.options = options
        self.currentSelection = 0 # Where the cursor is at, at the menu
        self.cursor1 = GC.IMAGESDICT['dragonCursor']
        self.cursor2 = Engine.flip_horiz(GC.IMAGESDICT['dragonCursor'])
        self.background = background

        self.menu_width = 136
        self.menu_height = 24
        if background.startswith('ChapterSelect'):
            self.menu_width = 192
            self.menu_height = 30

        self.cursorCounter = 0 # Helper counter for cursor animation
        self.cursorAnim = [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()

    def draw(self, surf, center=(GC.WINWIDTH//2, GC.WINHEIGHT//2), flicker=False, show_cursor=True):
        for index, option in enumerate(self.options):
            if flicker and self.currentSelection == index: # If the selection should flash white
                BGSurf = GC.IMAGESDICT[self.background + 'Flicker']
            elif self.currentSelection == index: # Highlight the chosen option
                BGSurf = GC.IMAGESDICT[self.background + 'Highlight']
            else:
                BGSurf = GC.IMAGESDICT[self.background]
            top = center[1] - (len(self.options)/2.0 - index)*(self.menu_height+1) + (20 if self.background.startswith('ChapterSelect') else 0) # What is this formula?
            left = center[0] - BGSurf.get_width()//2
            surf.blit(BGSurf, (left, top))

            position = (center[0] - GC.BASICFONT.size(str(option))[0]//2, top + BGSurf.get_height()//2 - GC.BASICFONT.size(str(option))[1]//2)
            color_transition = Image_Modification.color_transition(GC.COLORDICT['light_blue'], GC.COLORDICT['off_black'])
            OutlineFont(GC.BASICFONT, str(option), surf, GC.COLORDICT['off_white'], color_transition, position)

        if show_cursor:
            height = center[1] - 12 - (len(self.options)/2.0 - self.currentSelection)*(self.menu_height+1) + self.cursorAnim[self.cursorCounter]
            if self.background.startswith('ChapterSelect'):
                height += 22

            surf.blit(self.cursor1, (center[0] - self.menu_width//2 - self.cursor1.get_width()//2 - 8, height))
            surf.blit(self.cursor2, (center[0] + self.menu_width//2 - self.cursor2.get_width()//2 + 8, height))

    def getSelection(self):
        return self.options[self.currentSelection]

    def getSelectionIndex(self):
        return self.currentSelection

    def moveDown(self, first_push=True):
        self.currentSelection += 1
        if self.currentSelection > len(self.options) - 1:
            if first_push:
                self.currentSelection = 0
            else:
                self.currentSelection -= 1

    def moveUp(self, first_push=True):
        self.currentSelection -= 1
        if self.currentSelection < 0:
            if first_push:
                self.currentSelection = len(self.options) - 1
            else:
                self.currentSelection += 1

    def updateOptions(self, options):
        self.options = options

    def update(self):
        currentTime = Engine.get_time()
        if currentTime - self.lastUpdate > 100:
            self.lastUpdate = currentTime
            self.cursorCounter += 1
            if self.cursorCounter > len(self.cursorAnim) - 1:
                self.cursorCounter = 0

class ChapterSelectMenu(MainMenu):
    def __init__(self, options, colors=None):
        MainMenu.__init__(self, options, 'ChapterSelect')
        if colors:
            self.colors = colors
        else:
            self.colors = ['Green' for option in self.options]
        self.use_rel_y = len(options) > 3
        self.use_transparency = True
        self.rel_pos_y = 0

    def set_color(self, idx, color):
        self.colors[idx] = color

    def moveUp(self, first_push=True):
        MainMenu.moveUp(self, first_push)
        if self.use_rel_y:
            self.rel_pos_y -= self.menu_height

    def moveDown(self, first_push=True):
        MainMenu.moveDown(self, first_push)
        if self.use_rel_y:
            self.rel_pos_y += self.menu_height

    def update(self):
        MainMenu.update(self)
        if self.use_rel_y:
            if self.rel_pos_y > 0:
                self.rel_pos_y -= 4
                if self.rel_pos_y < 0:
                    self.rel_pos_y = 0
            elif self.rel_pos_y < 0:
                self.rel_pos_y += 4
                if self.rel_pos_y > 0:
                    self.rel_pos_y = 0

    def draw(self, surf, center=(GC.WINWIDTH//2, GC.WINHEIGHT//2), flicker=False, show_cursor=True):
        try:
            check = center[1]
        except TypeError:
            logger.warning("this is a gameStateObj.activeMenu... It shouldn't be. Aborting draw...")
            return
        # Only bother to show closest 7
        start_index = max(0, self.currentSelection - 3)
        for index, option in enumerate(self.options[start_index:self.currentSelection + 3], start_index):
            if flicker and self.currentSelection == index: # If the selection should flash white
                BGSurf = GC.IMAGESDICT[self.background + 'Flicker' + self.colors[index]].copy()
            elif self.currentSelection == index: # Highlight the chosen option
                BGSurf = GC.IMAGESDICT[self.background + 'Highlight' + self.colors[index]].copy()
            else:
                BGSurf = GC.IMAGESDICT[self.background + self.colors[index]].copy()
            # Position
            diff = index - self.currentSelection
            if self.use_rel_y:
                top = center[1] + diff*(self.menu_height+1) + self.rel_pos_y
            else:
                top = center[1] + index*(self.menu_height+1) - (len(self.options)-1)*self.menu_height//2 - 4
            # Text
            position = (BGSurf.get_width()//2 - GC.BASICFONT.size(str(option))[0]//2, BGSurf.get_height()//2 - GC.BASICFONT.size(str(option))[1]//2)
            color_transition = Image_Modification.color_transition(GC.COLORDICT['light_blue'], GC.COLORDICT['off_black'])
            OutlineFont(GC.BASICFONT, str(option), BGSurf, GC.COLORDICT['off_white'], color_transition, position)
            # Transparency
            if self.use_transparency:
                BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, abs(diff)*30)
            surf.blit(BGSurf, (center[0] - BGSurf.get_width()//2, top))

        if show_cursor:
            center_y = center[1] - 12 + self.cursorAnim[self.cursorCounter]
            if self.use_rel_y:
                height = center_y + self.rel_pos_y
            else:
                height = center_y + self.currentSelection*(self.menu_height+1) - (len(self.options)-1)*self.menu_height//2 - 4

            surf.blit(self.cursor1, (center[0] - self.menu_width//2 - self.cursor1.get_width()//2 - 8, height))
            surf.blit(self.cursor2, (center[0] + self.menu_width//2 - self.cursor2.get_width()//2 + 8, height))

class HorizOptionsMenu(Counters.CursorControl):
    def __init__(self, header, options):
        self.options = options
        self.text = header
        self.font = GC.FONT['text_white']
        self.spacing = '    '

        self.BGSurf = BaseMenuSurf.CreateBaseMenuSurf(self.get_menu_size())
        self.half_width = self.BGSurf.get_width()//2
        self.topleft = GC.WINWIDTH//2 - self.half_width, GC.WINHEIGHT//2 - self.BGSurf.get_height()//2

        self.currentSelection = 0

        Counters.CursorControl.__init__(self)

    def get_menu_size(self):
        h_text = self.font.size(self.text)[0]
        h_options = self.font.size(self.spacing.join(self.options))[0]
        h_size = max(h_text, h_options)
        width = h_size + 16 - h_size%8
        height = 40
        return (width, height)

    def getSelection(self):
        return self.options[self.currentSelection]

    def moveLeft(self):
        self.currentSelection -= 1
        if self.currentSelection < 0:
            self.currentSelection = len(self.options) - 1

    def moveRight(self):
        self.currentSelection += 1
        if self.currentSelection > len(self.options) - 1:
            self.currentSelection = 0

    def draw(self, surf):
        bg_surf = self.BGSurf.copy()
        # blit first line
        self.font.blit(self.text, bg_surf, (self.half_width - self.font.size(self.text)[0]//2, 4))

        # blit background highlight
        options = self.spacing.join(self.options)
        option_width = self.font.size(options)[0]
        option_start = self.half_width - option_width//2

        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        highlight_width = highlightSurf.get_width()
        current_selection_width = self.font.size(self.getSelection())[0] + 6
        num_highlights = current_selection_width//highlight_width
        prev_words = self.spacing.join(self.options[:self.currentSelection])
        if prev_words:
            prev_words += self.spacing
        start_left = self.font.size(prev_words)[0] + option_start
        for slot in range(num_highlights):
            topleft = (slot*highlight_width + start_left - 2, 20 + 9)
            bg_surf.blit(highlightSurf, topleft)

        # Blit options
        self.font.blit(options, bg_surf, (option_start, 20))

        # blit menu
        surf.blit(bg_surf, self.topleft)

        # blit cursor
        surf.blit(self.cursor, (self.topleft[0] - 16 + start_left + self.cursorAnim[self.cursorCounter], self.topleft[1] + 20))

class VertOptionsMenu(HorizOptionsMenu):
    def get_menu_size(self):
        h_text = self.font.size(self.text)[0]
        h_options = max([self.font.size(option)[0] for option in self.options])
        h_size = max(h_text, h_options)
        width = h_size + 16 - h_size%8
        height = (24 + 16*len(self.options))
        return (width, height)

    def draw(self, surf):
        bg_surf = self.BGSurf.copy()
        top = self.topleft[1] + 4 + 16
        left = self.topleft[0]

        # blit first line
        self.font.blit(self.text, bg_surf, (self.half_width - self.font.size(self.text)[0]//2, 4))

        cursor_y = top + 16 * self.options.index(self.getSelection())

        # blit menu
        surf.blit(bg_surf, self.topleft)

        # blit highlight
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        highlight_width = highlightSurf.get_width()
        num_highlights = self.half_width - 16
        for slot in range(num_highlights):
            topleft = (slot*highlight_width + left + 16, cursor_y + 9)
            surf.blit(highlightSurf, topleft)

        # blit options
        for idx, option in enumerate(self.options):
            self.font.blit(str(option), surf, (left + 16, top + (16 * idx)))

        # blit cursor
        surf.blit(self.cursor, (left + self.cursorAnim[self.cursorCounter], cursor_y))
                
# For Pick Unit and Prep Item and Arena Choice
class UnitSelectMenu(Counters.CursorControl):
    def __init__(self, units, units_per_row, num_rows, topleft):
        self.options = units
        self.units_per_row = units_per_row
        self.num_rows = num_rows
        self.currentSelection = 0
        self.mode = 'position'

        self.topleft = topleft
        self.option_length = 60
        self.option_height = 16
        self.scroll = 0

        if topleft == 'center':
            self.option_length = 64
            self.topleft = (6, 0)
            self.menu_size = GC.WINWIDTH - 16, self.option_height*self.num_rows + 8
        else:
            self.menu_size = self.getMenuSize()

        self.menu_width = self.menu_size[0]
        self.highlight = True
        self.draw_extra_marker = None

        self.scroll_bar = GUIObjects.ScrollBar((self.topleft[0] + self.menu_width, self.topleft[1] + 4))
        Counters.CursorControl.__init__(self)
        self.cursor_y_offset = 0

        # Build background
        self.backsurf = BaseMenuSurf.CreateBaseMenuSurf(self.menu_size, 'BaseMenuBackgroundOpaque')
        shimmer = GC.IMAGESDICT['Shimmer2']
        self.backsurf.blit(shimmer, (self.backsurf.get_width() - shimmer.get_width() - 1, self.backsurf.get_height() - shimmer.get_height() - 5))
        self.backsurf = Image_Modification.flickerImageTranslucent(self.backsurf, 10)

    def updateOptions(self, options):
        self.options = options

    def getMenuSize(self):
        return (self.option_length * self.units_per_row + 8, self.option_height*self.num_rows + 8)

    def getSelection(self):
        if self.currentSelection > len(self.options) - 1:
            self.currentSelection = len(self.options) - 1
        if self.currentSelection < 0:
            self.currentSelection = 0
        if self.options:
            return self.options[self.currentSelection]
        else:
            return None

    def moveDown(self, first_push=True):
        self.currentSelection += self.units_per_row
        if self.currentSelection > len(self.options) - 1:
            self.currentSelection -= self.units_per_row
        else:
            self.cursor_y_offset = -1
        if len(self.options) > self.units_per_row*self.num_rows and self.scroll <= self.currentSelection - self.units_per_row*(self.num_rows-1):
            self.scroll += 1
            self.scroll = Utility.clamp(self.scroll, 0, max(0, len(self.options)//self.units_per_row - self.num_rows + 1))

    def moveUp(self, first_push=True):
        self.currentSelection -= self.units_per_row
        if self.currentSelection < 0:
            self.currentSelection += self.units_per_row
        else:
            self.cursor_y_offset = 1
        if self.scroll > 0 and self.currentSelection < self.scroll*self.units_per_row:
            self.scroll -= 1
            self.scroll = max(self.scroll, 0) # Scroll cannot go negative

    def moveLeft(self, first_push=True):
        if self.currentSelection%self.units_per_row != 0:
            self.currentSelection -= 1

    def moveRight(self, first_push=True):
        if (self.currentSelection+1)%self.units_per_row != 0:
            self.currentSelection += 1
            if self.currentSelection > len(self.options) - 1:
                self.currentSelection -= 1

    def update(self):
        Counters.CursorControl.update(self)

    def draw(self, surf, gameStateObj):
        surf.blit(self.backsurf, self.topleft)
        x_center = -16 if self.units_per_row <= 2 else 0

        # Blit background highlight
        if self.highlight:
            highlightSurf = GC.IMAGESDICT['MenuHighlight']
            width = highlightSurf.get_width()
            for slot in range((self.option_length-4)//width): # Gives me the amount of highlight needed
                left = self.topleft[0] + 20 + x_center + self.currentSelection%self.units_per_row*self.option_length + slot*width
                top = self.topleft[1] + (self.currentSelection-self.scroll*self.units_per_row)//self.units_per_row*self.option_height + 12
                surf.blit(highlightSurf, (left, top))
        if self.draw_extra_marker:
            self.draw_extra_highlight(surf)

        self.draw_units(surf, x_center, gameStateObj)

        # Blit cursor
        self.draw_cursor(surf, x_center)
        if self.draw_extra_marker:
            self.draw_extra_cursor(surf)

        if len(self.options) > self.units_per_row*self.num_rows:
            self.scroll_bar.draw(surf, self.scroll, self.num_rows, len(self.options)//self.units_per_row + 1)

    def draw_units(self, surf, x_center, gameStateObj):
        s_size = self.units_per_row*self.num_rows
        for index, unit in enumerate(self.options[self.scroll*self.units_per_row:s_size+self.scroll*self.units_per_row]):
            top = index//self.units_per_row
            left = index%self.units_per_row

            # Blit passive sprite
            unit_image = unit.sprite.create_image('passive')
            if self.mode == 'position' and not unit.position:
                unit_image = unit.sprite.create_image('gray')
            elif self.mode == 'arena' and unit.currenthp <= 1:
                unit_image = unit.sprite.create_image('gray')
            elif unit == self.options[self.currentSelection]:
                unit_image = unit.sprite.create_image('active')
            topleft = (self.topleft[0] - 4 + x_center + left*self.option_length, self.topleft[1] + 2 + (top+1)*self.option_height - unit_image.get_height() + 8)
            surf.blit(unit_image, topleft)

            # Blit name
            font = GC.FONT['text_white']
            if self.mode == 'position':
                if not unit.position:
                    font = GC.FONT['text_grey']
                elif unit.position and 'Formation' not in gameStateObj.map.tile_info_dict[unit.position]:
                    font = GC.FONT['text_green']  # Locked/Lord character
            elif self.mode == 'arena' and unit.currenthp <= 1:
                font = GC.FONT['text_grey']
            position = (self.topleft[0] + 20 + 1 + 16 + x_center + left*self.option_length, self.topleft[1] + 2 + top*self.option_height)
            font.blit(unit.name, surf, position)

    def draw_cursor(self, surf, x_center):
        left = self.topleft[0] + 8 + x_center + self.currentSelection%self.units_per_row*self.option_length + self.cursorAnim[self.cursorCounter]
        top = self.topleft[1] + 4 + (self.currentSelection-self.scroll*self.units_per_row)//self.units_per_row*self.option_height + self.cursor_y_offset*8
        self.cursor_y_offset = 0 # Reset
        surf.blit(self.cursor, (left, top))

    def set_extra_marker(self, selection):
        self.draw_extra_marker = selection

    def draw_extra_highlight(self, surf):
        # Blit background highlight
        if self.highlight:
            selection = self.draw_extra_marker
            highlightSurf = GC.IMAGESDICT['MenuHighlight']
            width = highlightSurf.get_width()
            for slot in range((self.option_length-20)//width): # Gives me the amount of highlight needed
                left = self.topleft[0] + 20 + selection%self.units_per_row*self.option_length + slot*width
                top = self.topleft[1] + (selection-self.scroll)//self.units_per_row*self.option_height + 12
                surf.blit(highlightSurf, (left, top))

    def draw_extra_cursor(self, surf):
        # Blit cursor
        selection = self.draw_extra_marker
        left = self.topleft[0] - 8 + selection%self.units_per_row*self.option_length + self.cursorAnim[self.cursorCounter]
        top = self.topleft[1] + 4 + (selection-self.scroll)//self.units_per_row*self.option_height
        surf.blit(self.cursor, (left, top))

def drawUnitItems(surf, topleft, unit, include_top=False, include_bottom=True, include_face=False, right=True, shimmer=0):
    if include_top:
        white_backSurf = GC.IMAGESDICT['PrepTop']
        surf.blit(white_backSurf, (topleft[0] - 6, topleft[1] - white_backSurf.get_height()))
        surf.blit(unit.portrait, (topleft[0] + 3, topleft[1] - 35))
        GC.FONT['text_white'].blit(unit.name, surf, (topleft[0] + 68 - GC.FONT['text_white'].size(unit.name)[0]//2, topleft[1] - 40 + 5))
        # GC.FONT['text_yellow'].blit('<>', surf, (topleft[0] + 37, topleft[1] - 20))
        # GC.FONT['text_yellow'].blit('$', surf, (topleft[0] + 69, topleft[1] - 20))
        GC.FONT['text_blue'].blit(str(unit.level), surf, (topleft[0] + 72 - GC.FONT['text_blue'].size(str(unit.level))[0], topleft[1] - 19))
        GC.FONT['text_blue'].blit(str(unit.exp), surf, (topleft[0] + 97 - GC.FONT['text_blue'].size(str(unit.exp))[0], topleft[1] - 19))

    if include_bottom:
        blue_backSurf = BaseMenuSurf.CreateBaseMenuSurf((104, 16*cf.CONSTANTS['max_items']+8), 'BaseMenuBackgroundOpaque')
        if shimmer:
            img = GC.IMAGESDICT['Shimmer' + str(shimmer)]
            blue_backSurf.blit(img, (blue_backSurf.get_width() - img.get_width() - 1, blue_backSurf.get_height() - img.get_height() - 5))
        blue_backSurf = Image_Modification.flickerImageTranslucent(blue_backSurf, 10)
        if include_top:
            topleft = topleft[0], topleft[1] - 4
        surf.blit(blue_backSurf, topleft)

        if include_face:
            face_image = unit.bigportrait.copy()
            if right:
                face_image = Engine.flip_horiz(face_image)
            face_image = Image_Modification.flickerImageTranslucentColorKey(face_image, 50)
            left = topleft[0] + blue_backSurf.get_width()//2 - face_image.get_width()//2 + 1
            top = topleft[1] + blue_backSurf.get_height()//2 - face_image.get_height()//2 - 1
            pos = left, top
            surf.blit(face_image, pos)

        for index, item in enumerate(unit.items):
            item.draw(surf, (topleft[0] + 2, topleft[1] + index*16 + 4))
            name_font = GC.FONT['text_grey']
            use_font = GC.FONT['text_grey']
            if unit.canWield(item) and unit.canUse(item):
                name_font = GC.FONT['text_white']
                use_font = GC.FONT['text_blue']
            name_font.blit(item.name, surf, (topleft[0] + 4 + 16, topleft[1] + index*16 + 4))
            uses_string = "--"
            vert_adj = 0
            if item.uses:
                uses_string = str(item.uses)
            elif item.c_uses:
                uses_string = str(item.c_uses)
            elif item.cooldown:
                vert_adj = 2
                if item.cooldown.charged:
                    uses_string = str(item.cooldown.cd_uses)
                    use_font = GC.FONT['text_light_green']
                    build_cd_groove(surf, (topleft[0] + 104 - 19, topleft[1] + (index+1)*16), 16,
                                    int(round((int(item.cooldown.cd_uses) / int(item.cooldown.total_cd_uses)) * 16)), False)
                else:
                    uses_string = (str(item.cooldown.cd_turns))
                    use_font = GC.FONT['text_light_red']
                    build_cd_groove(surf, (topleft[0] + 104 - 19, topleft[1] + (index+1)*16), 16,
                                    int(round((int(item.cooldown.cd_turns) / int(item.cooldown.total_cd_turns)) * 16)), True)
            use_font.blit(uses_string, surf, (topleft[0] + 104 - 4 - use_font.size(uses_string)[0], topleft[1] + index*16 + 4 - vert_adj))

# Serves as controller class for host of menus
class ConvoyMenu(object):
    def __init__(self, owner, options, topleft, disp_value=None, buy_value_mod=1.0):
        self.owner = owner
        self.topleft = topleft
        self.disp_value = disp_value
        self.buy_value_mod = buy_value_mod

        self.order = Weapons.TRIANGLE.types + ["Consumable"]
        self.wexp_icons = [Weapons.Icon(name, grey=True) for name in self.order]
        self.buildMenus(options)

        self.selection_index = 0

        # Handle arrows
        self.left_arrow = GUIObjects.ScrollArrow('left', (self.topleft[0] - 4, self.topleft[1] - 14))
        menu_width = 120
        if self.disp_value:
            menu_width = 160
        self.right_arrow = GUIObjects.ScrollArrow('right', (self.topleft[0] + menu_width - 4, self.topleft[1] - 14), 0.5)

    def get_sorted_dict(self, options):
        sorted_dict = {}
        for w_type in self.order:
            sorted_dict[w_type] = [option for option in options if w_type == option.TYPE]
        sorted_dict['Consumable'] = [option for option in options if not option.TYPE]
        for key, value in sorted_dict.items():
            value.sort(key=lambda item: item.cooldown.cd_turns if item.cooldown and not item.cooldown.charged else 100)
            value.sort(key=lambda item: item.cooldown.cd_uses if item.cooldown and item.cooldown.charged else 100)
            value.sort(key=lambda item: item.c_uses.uses if item.c_uses else 100)
            value.sort(key=lambda item: item.uses.uses if item.uses else 100)
            value.sort(key=lambda item: item.name)
            value.sort(key=lambda item: item.value*item.uses.total_uses if item.uses else item.value)

        return sorted_dict

    def updateOptions(self, options):
        sorted_dict = self.get_sorted_dict(options)
        for menu_name, menu in self.menus.items():
            menu.updateOptions(sorted_dict[menu_name])

    def buildMenus(self, options):
        sorted_dict = self.get_sorted_dict(options)
        self.menus = {}
        if self.disp_value:
            buy = True if self.disp_value == "Buy" else False
            mode = "Buy" if buy else "Sell"
            buy_value_mod = self.buy_value_mod if buy else 1.0
            for w_type in self.order:
                self.menus[w_type] = ShopMenu(self.owner, sorted_dict[w_type], self.topleft, limit=7, hard_limit=True, mode=mode, shimmer=2, buy_value_mod=buy_value_mod)
            self.menus["Consumable"] = ShopMenu(self.owner, sorted_dict['Consumable'], self.topleft, limit=7, hard_limit=True, mode=mode, shimmer=2, buy_value_mod=buy_value_mod)
        else:
            for w_type in self.order:
                self.menus[w_type] = ChoiceMenu(self.owner, sorted_dict[w_type], self.topleft, limit=7, hard_limit=True, width=120, shimmer=2, gem=False)
            self.menus["Consumable"] = ChoiceMenu(self.owner, sorted_dict['Consumable'], self.topleft, limit=7, hard_limit=True, width=120, shimmer=2, gem=False)

    def getSelection(self):
        return self.menus[self.order[self.selection_index]].getSelection()

    def get_relative_index(self):
        current_menu = self.menus[self.order[self.selection_index]]
        return current_menu.currentSelection - current_menu.scroll

    def set_take_input(self, takes_input):
        for menu in self.menus.values():
            menu.takes_input = takes_input

    def moveDown(self, first_push=True):
        self.menus[self.order[self.selection_index]].moveDown(first_push)

    def moveUp(self, first_push=True):
        self.menus[self.order[self.selection_index]].moveUp(first_push)

    def moveLeft(self, first_push=True):
        self.selection_index -= 1
        if self.selection_index < 0:
            if first_push:
                self.selection_index = len(self.order) - 1
            else:
                self.selection_index += 1
        else:
            self.left_arrow.pulse()

    def moveRight(self, first_push=True):
        self.selection_index += 1
        if self.selection_index > len(self.order) - 1:
            if first_push:
                self.selection_index = 0
            else:
                self.selection_index -= 1
        else:
            self.right_arrow.pulse()

    def goto(self, item):
        if item.TYPE:
            self.selection_index = self.order.index(item.TYPE)
        else:
            self.selection_index = len(self.order) - 1
        item_index = self.menus[self.order[self.selection_index]].options.index(item)
        self.menus[self.order[self.selection_index]].moveTo(item_index)

    def goto_same_item_id(self, item):
        if item.TYPE:
            self.selection_index = self.order.index(item.TYPE)
        else:
            self.selection_index = len(self.order) - 1
        item_menu = self.menus[self.order[self.selection_index]]
        for idx, match in enumerate(item_menu.options):
            if match.id == item.id:
                item_menu.moveTo(idx)
                return

    def update(self):
        self.menus[self.order[self.selection_index]].update()

    def draw(self, surf, gameStateObj=None):
        dist = int(120//len(self.order)) - 1
        if self.disp_value:
            dist = int(160//len(self.order)) - 1
            self.menus[self.order[self.selection_index]].draw(surf, gameStateObj.get_money())
        else:
            self.menus[self.order[self.selection_index]].draw(surf)
        # Draw item icons
        for index, gray_icon in enumerate(reversed(self.wexp_icons)):
            if index == len(self.order) - 1 - self.selection_index:
                pass
                # Saving this for later. To be blit on top
            else:
                gray_icon.draw(surf, (self.topleft[0] + (len(self.order) - 1 - index)*dist + 4, self.topleft[1] - 14))
        for index, icon in enumerate(self.order):
            if index == self.selection_index:
                # offset = 4
                # if index == 0:
                #     offset = 0 # noqa
                icon = Weapons.Icon(icon)
                icon.draw(surf, (self.topleft[0] + index*dist + 4, self.topleft[1] - 14))
                surf.blit(GC.IMAGESDICT['Shine_Wexp'], (self.topleft[0] + index*dist + 4, self.topleft[1] - 14))
        self.drawTopArrows(surf)

    def drawTopArrows(self, surf):
        self.left_arrow.draw(surf)
        self.right_arrow.draw(surf)

# Simple shop menu
class ShopMenu(ChoiceMenu):
    def __init__(self, owner, options, topleft, limit=5, hard_limit=True,
                 background='BaseMenuBackground', mode='Buy', shimmer=0, buy_value_mod=1.0):
        ChoiceMenu.__init__(self, owner, options, topleft, limit=limit, hard_limit=hard_limit, background=background, width=120, shimmer=shimmer, gem=False)
        # Whether we are buying or selling
        self.mode = mode
        self.buy_value_mod = buy_value_mod
        self.takes_input = False

        self.lastUpdate = Engine.get_time()

        self.old_scroll = self.scroll
        self.up_arrow = GUIObjects.ScrollArrow('up', (self.topleft[0] + self.menu_width//2 - 7, self.topleft[1] - 4))
        self.down_arrow = GUIObjects.ScrollArrow('down', (self.topleft[0] + self.menu_width//2 - 7, self.topleft[1] + 16*5 + 4), 0.5)

        self.shimmer = shimmer

    def draw(self, surf, money):
        if self.limit:
            BGSurf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, 16*self.limit+8), 'BaseMenuBackgroundOpaque')
        else:
            BGSurf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, 16*len(self.options)+8), 'BaseMenuBackgroundOpaque')
        if self.shimmer:
            img = GC.IMAGESDICT['Shimmer' + str(self.shimmer)]
            BGSurf.blit(img, (BGSurf.get_width() - img.get_width() - 1, BGSurf.get_height() - img.get_height() - 5))
        BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, 10)
        # Blit background
        surf.blit(BGSurf, self.topleft)

        # if self.limit:
        #     top_of_menu = max(0, min(max(0, self.currentSelection - (self.limit - 1)), len(self.options) - self.limit))
        #     bottom_of_menu = min(len(self.options), top_of_menu + self.limit)
        # else:
        #     top_of_menu = 0
        #     bottom_of_menu = len(self.options)

        # Blit background highlight
        if self.takes_input:
            self.draw_highlight(surf, self.currentSelection-self.scroll)

        # Blit options
        for index, option in enumerate(self.options[self.scroll:self.scroll+self.limit]):
            option.draw(surf, (self.topleft[0] + 4, self.topleft[1] + 4 + index*16))

            uses_string = '--'
            value_string = '--'
            true_value = None
            vert_adj = 0
            if option.uses:
                uses_string = str(option.uses.uses)
                if self.mode == 'Repair':
                    true_value = (option.uses.total_uses - option.uses.uses) * option.value
                else:
                    true_value = option.uses.uses * option.value
                if self.mode in ('Buy', 'Repair'):
                    true_value *= self.buy_value_mod
                else:
                    true_value //= 2
                true_value = int(true_value)
            elif option.c_uses or option.cooldown:
                if option.c_uses:
                    uses_string = str(option.c_uses)
                else:
                    uses_string = str(option.cooldown.cd_uses)
                if self.mode in ('Buy', 'Sell'):
                    true_value = option.value
                else:
                    true_value = 0
                if self.mode in ('Buy', 'Repair'):
                    true_value *= self.buy_value_mod
                else:
                    true_value //= 2
                true_value = int(true_value)
            else:
                if self.mode in ('Buy', 'Sell'):
                    true_value = option.value
                else:
                    true_value = 0
                if self.mode in ('Buy', 'Repair'):
                    true_value *= self.buy_value_mod
                else:
                    true_value //= 2
                true_value = int(true_value)
            value_string = str(true_value)

            if option.locked or not option.value or (self.owner and not self.owner.canWield(option)):
                name_font = GC.FONT['text_grey']
                uses_font = GC.FONT['text_grey']
            else:
                name_font = GC.FONT['text_white']
                uses_font = GC.FONT['text_blue']
            if not true_value:
                value_font = GC.FONT['text_grey']
            elif self.mode in ('Buy', 'Repair'):
                if money < true_value:
                    value_font = GC.FONT['text_grey']
                else:
                    value_font = GC.FONT['text_blue']
            else:
                value_font = GC.FONT['text_blue']

            name_font.blit(str(option), surf, (self.topleft[0] + 20, self.topleft[1] + 4 + index*16))
            if option.cooldown:
                vert_adj = 1
                uses_font = GC.FONT['text_light_green']
                build_cd_groove(surf, (self.topleft[0] + 95, self.topleft[1] + (1 + index) * 16 + 1), 16,
                                int(round((int(option.cooldown.cd_uses) / int(option.cooldown.total_cd_uses)) * 16)),
                                False)
            uses_font.blit(uses_string, surf, (self.topleft[0] + 96, self.topleft[1] + 4 + index*16 - vert_adj))
            left = self.topleft[0] + BGSurf.get_width() - 4 - value_font.size(value_string)[0]
            if self.limit == 7:
                left -= 4 # to get out of the way of scroll bar
            value_font.blit(value_string, surf, (left, self.topleft[1] + 4 + index*16))
        if not self.options:
            GC.FONT['text_grey'].blit(cf.WORDS['Nothing'], surf, (self.topleft[0] + 20, self.topleft[1] + 4))

        if self.takes_input:
            self.draw_cursor(surf, self.currentSelection-self.scroll)

        if self.limit == 7: # Base Market Convoy menu
            if len(self.options) > self.limit:
                self.scroll_bar.draw(surf, self.scroll, self.limit, len(self.options))
        else:
            self.draw_arrows(surf)

    def draw_arrows(self, surf):
        if self.old_scroll < self.scroll:
            self.down_arrow.pulse()
        elif self.old_scroll > self.scroll:
            self.up_arrow.pulse()
        self.old_scroll = self.scroll
        if len(self.options) > self.limit:
            if self.scroll > 0:
                self.up_arrow.draw(surf)
            if self.scroll + self.limit < len(self.options):
                self.down_arrow.draw(surf)

    def getMenuWidth(self):
        return 160 # Recommended width of shopmenu

    def get_relative_index(self):
        return self.currentSelection - self.scroll

# Menu used for trading between units
class TradeMenu(Counters.CursorControl):
    def __init__(self, owner, partner, owner_items, partner_items):
        self.owner = owner
        self.partner = partner
        self.owner_items = owner_items
        self.partner_items = partner_items

        self.topleft = (12, 68)
        # Where the cursor hands are at
        # First number is which side of the menu (left (0) or right (1))
        # Second number is which item index
        self.main_hand = [0, 0] # Main hand
        self.extra_hand = None # Secondary Hand

        Counters.CursorControl.__init__(self)
        self.cursor_y_offset = 0

        self.menuWidth = 104
        self.optionHeight = 16
        self.info_flag = False

    def draw(self, surf, gameStateObj):
        # Blit names
        nameBG1Surf = GC.IMAGESDICT['TradeName']

        nameBG2Surf = GC.IMAGESDICT['TradeName']

        surf.blit(nameBG1Surf, (-4, -1))
        surf.blit(nameBG2Surf, (GC.WINWIDTH - nameBG2Surf.get_width() + 4, -1))
        GC.FONT['text_white'].blit(self.owner.name, surf, (24 - GC.FONT['text_white'].size(self.owner.name)[0]//2, 0))
        GC.FONT['text_white'].blit(self.partner.name, surf, (GC.WINWIDTH - 24 - GC.FONT['text_white'].size(self.partner.name)[0]//2, 0))

        # Blit menu background
        BGSurf1 = BaseMenuSurf.CreateBaseMenuSurf((self.menuWidth, self.optionHeight*cf.CONSTANTS['max_items']+8))

        BGSurf2 = Engine.copy_surface(BGSurf1)
        second_topleft = (self.topleft[0] + BGSurf1.get_width() + 8, self.topleft[1])

        # Blit portraits
        clipped_surf1 = Engine.subsurface(self.owner.bigportrait, (0, 3, self.owner.bigportrait.get_width(), 68))
        portraitSurf1 = Engine.flip_horiz(clipped_surf1)
        pos = (self.topleft[0] + BGSurf1.get_width()//2 - portraitSurf1.get_width()//2, self.topleft[1] - portraitSurf1.get_height())
        surf.blit(portraitSurf1, pos)
        surf.blit(BGSurf1, self.topleft)

        if hasattr(self.partner, 'bigportrait'):
            clipped_surf2 = Engine.subsurface(self.partner.bigportrait, (0, 3, self.partner.bigportrait.get_width(), 68))
            portraitSurf2 = clipped_surf2
            pos = (second_topleft[0] + BGSurf2.get_width()//2 - portraitSurf2.get_width()//2, second_topleft[1] - portraitSurf2.get_height())
            surf.blit(portraitSurf2, pos)
        surf.blit(BGSurf2, second_topleft)

        # Blit background highlight
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range((self.menuWidth - 16)//width): # Gives me the amount of highlight needed
            topleft = (self.topleft[0] + 8 + slot*width + (self.menuWidth+8)*self.main_hand[0],
                       self.topleft[1] + 11 + (self.main_hand[1]*16))
            surf.blit(highlightSurf, topleft)

        self.draw_items(surf, self.owner_items, self.topleft, BGSurf1.get_width(), self.owner)
        self.draw_items(surf, self.partner_items, second_topleft, BGSurf2.get_width(), self.partner)

        if self.extra_hand is not None:
            left = self.topleft[0] - 10 + self.cursorAnim[self.cursorCounter] + (self.menuWidth+8)*self.extra_hand[0]
            top = self.topleft[1] + 4 + self.extra_hand[1]*self.optionHeight
            surf.blit(self.cursor, (left, top))

        # Cursor location
        left = self.topleft[0] - 10 + self.cursorAnim[self.cursorCounter] + (self.menuWidth+8)*self.main_hand[0]
        top = self.topleft[1] + 4 + self.main_hand[1]*16 + self.cursor_y_offset*8
        self.cursor_y_offset = 0 # reset
        surf.blit(self.cursor, (left, top))

    def draw_items(self, surf, items, topleft, width, owner):
        for index, item in enumerate(items):
            item.draw(surf, (topleft[0] + 4, topleft[1] + 4 + index*self.optionHeight))
            if item.locked:
                font = GC.FONT['text_yellow']
                uses_font = GC.FONT['text_blue']
            elif owner.canWield(item):
                font = GC.FONT['text_white']
                uses_font = GC.FONT['text_blue']
            else:
                font = GC.FONT['text_grey']
                uses_font = GC.FONT['text_grey']
            height = self.topleft[1] + 5 + index*self.optionHeight
            right = topleft[0] + width - 4
            font.blit(str(item), surf, (topleft[0] + 20, height))
            if item.uses:
                uses_font.blit(str(item.uses), surf, (right - uses_font.size(str(item.uses))[0], height))
            elif item.c_uses:
                uses_font.blit(str(item.c_uses), surf, (right - uses_font.size(str(item.c_uses))[0], height))
            elif item.cooldown:
                if item.cooldown.charged:
                    uses_font = GC.FONT['text_light_green']
                    uses_font.blit(str(item.cooldown.cd_uses), surf, (right - uses_font.size(str(item.cooldown.cd_uses))[0], height - 3))
                    build_cd_groove(surf, (right - 15, height + self.optionHeight - 5), 16,
                                    int(round((int(item.cooldown.cd_uses) / int(item.cooldown.total_cd_uses)) * 16)), False)
                else:
                    uses_font = GC.FONT['text_light_red']
                    uses_font.blit((str(item.cooldown.cd_turns)), surf, (right - uses_font.size((str(item.cooldown.cd_turns)))[0], height - 3))
                    build_cd_groove(surf, (right - 15, height + self.optionHeight - 5), 16,
                                    int(round((int(item.cooldown.cd_turns) / int(item.cooldown.total_cd_turns)) * 16)), True)
            else:
                uses_font.blit('--', surf, (right - uses_font.size('--')[0], height))

    def drawInfo(self, surf):
        if self.info_flag:
            # If on an owner item
            if self.main_hand[0] == 0 and self.main_hand[1] < len(self.owner_items):
                option = self.owner_items[self.main_hand[1]]
                idx = self.main_hand[1]
            elif self.main_hand[0] == 1 and self.main_hand[1] < len(self.partner_items):
                option = self.partner_items[self.main_hand[1]]
                idx = self.main_hand[1]
            else:
                self.info_flag = False
                return
            if isinstance(option, ItemMethods.ItemObject):
                help_box = option.get_help_box()
                top = self.topleft[1] + 4 + 16*idx - help_box.get_height()
                if self.main_hand[0] == 1:
                    help_box.draw(surf, (GC.WINWIDTH - 8 - help_box.get_width(), top))
                else:
                    help_box.draw(surf, (self.topleft[0] + 8, top))

    def is_selection_set(self):
        return self.extra_hand is not None

    def unsetSelection(self):
        self.extra_hand = None

    def setSelection(self):
        # This puts the secondary hand in the spot the original hand came from
        self.extra_hand = [self.main_hand[0], self.main_hand[1]]

        # Trading item FROM the unit on the left
        if self.main_hand[0] == 0:  # Main hand was on left
            self.main_hand[0] = 1  # Move hand to right
            # Move hand to highest empty spot available
            if len(self.partner_items) < cf.CONSTANTS['max_items']:
                self.main_hand[1] = self._get_max_selectable2() - 1
            else:
                self.main_hand[1] = self.main_hand[1]  # Index doesn't change
            # if len(self.partner_items) < cf.CONSTANTS['max_items']:
            #     self.main_hand[1] = len(self.partner_items)
            # else:  # if not available, top of items
            #     self.main_hand[1] = 0
        # Trading item FROM the unit on the right
        else:
            self.main_hand[0] = 0
            if len(self.owner_items) < cf.CONSTANTS['max_items']:
                self.main_hand[1] = self._get_max_selectable1() - 1
            else:
                self.main_hand[1] = self.main_hand[1]
            # if len(self.owner_items) < cf.CONSTANTS['max_items']:
            #     self.main_hand[1] = len(self.owner_items)
            # else:
            #     self.main_hand[1] = 0

    def tradeItems(self, gameStateObj):
        # swaps selected item and current item
        # Get items
        item1 = "EmptySlot"
        item2 = "EmptySlot"
        # Item 2 is where the item came from
        # Item 1 is where the item is going
        if self.main_hand[0] == 0 and self.main_hand[1] < len(self.owner_items):
            item1 = self.owner_items[self.main_hand[1]]
        elif self.main_hand[0] == 1 and self.main_hand[1] < len(self.partner_items):
            item1 = self.partner_items[self.main_hand[1]]
        if self.extra_hand[0] == 0 and self.extra_hand[1] < len(self.owner_items):
            item2 = self.owner_items[self.extra_hand[1]]
        elif self.extra_hand[0] == 1 and self.extra_hand[1] < len(self.partner_items):
            item2 = self.partner_items[self.extra_hand[1]]

        if (item1 is item2) or (item1 is not "EmptySlot" and item1.locked) or (item2 is not "EmptySlot" and item2.locked):
            self.extra_hand = None
            GC.SOUNDDICT['Error'].play()
            return

        # Now swap items
        # Main hand is where the item is going
        # Extra hand is where the item came from
        if self.extra_hand[0] == 0:
            if self.main_hand[0] == 0:
                Action.do(Action.TradeItem(self.owner, self.owner, item2, item1), gameStateObj)
            else:
                Action.do(Action.TradeItem(self.owner, self.partner, item2, item1), gameStateObj)
        else:
            if self.main_hand[0] == 0:
                Action.do(Action.TradeItem(self.partner, self.owner, item2, item1), gameStateObj)
            else:
                Action.do(Action.TradeItem(self.partner, self.partner, item2, item1), gameStateObj)
        Action.do(Action.OwnerHasTraded(self.owner), gameStateObj)

        # This part puts the main hand at the location you traded to
        # Otherwise the main hand would stay in its original spot
        if self.extra_hand[0] == 0:
            self.main_hand = [self.extra_hand[0], min(self.extra_hand[1], self._get_max_selectable1() - 1)]
        else:
            self.main_hand = [self.extra_hand[0], min(self.extra_hand[1], self._get_max_selectable2() - 1)]
        self.extra_hand = None

    def toggle_info(self):
        self.info_flag = not self.info_flag

    def _get_max_selectable1(self):
        '''Get the maximum number of selectable menu items
           on the left side of the trading screen. Depends
           upon number of items in inventory and whether a
           trade is active.
        '''
        # Allows an empty slot to be selectable if user is choosing trade destination
        empty_slot = int(
            self.extra_hand is not None and
            self.extra_hand[0] == 1 and
            len(self.owner_items) < cf.CONSTANTS['max_items'] and
            len(self.partner_items) > 0)
        return max(len(self.owner_items) + empty_slot, 1)

    def _get_max_selectable2(self):
        '''Get the maximum number of selectable menu items
           on the right side of the trading screen. Depends
           upon number of items in inventory and whether a
           trade is active.
        '''
        # Allows an empty slot to be selectable if user is choosing trade destination
        empty_slot = int(
            self.extra_hand is not None and
            self.extra_hand[0] == 0 and
            len(self.partner_items) < cf.CONSTANTS['max_items'] and
            len(self.owner_items) > 0)
        return max(len(self.partner_items) + empty_slot, 1)

    def moveDown(self, first_push=True):
        if self.main_hand[0] == 0:
            num_allowed = self._get_max_selectable1()
        else:
            num_allowed = self._get_max_selectable2()
        if first_push:
            tmp = (self.main_hand[1] + 1) % num_allowed  # wrap past
        else:
            tmp = min(self.main_hand[1] + 1, num_allowed - 1)
        if tmp != self.main_hand[1]:  # If it moved
            self.cursor_y_offset = 1 if tmp < self.main_hand[1] else -1
            self.main_hand[1] = tmp
            return True
        else:
            return False

    def moveUp(self, first_push=True):
        if self.main_hand[0] == 0:
            num_allowed = self._get_max_selectable1()
        else:
            num_allowed = self._get_max_selectable2()
        if first_push:
            tmp = (self.main_hand[1] - 1) % num_allowed  # wrap past
        else:
            tmp = max(self.main_hand[1] - 1, 0)
        if tmp != self.main_hand[1]:  # If it moved
            self.cursor_y_offset = 1 if tmp < self.main_hand[1] else -1
            self.main_hand[1] = tmp
            return True
        else:
            return False

    def moveLeft(self, first_push=True):
        if self.main_hand[0] == 1:
            self.main_hand[0] = 0
            self.main_hand[1] = min(self.main_hand[1], self._get_max_selectable1() - 1)
            return True
        return False

    def moveRight(self, first_push=True):
        if self.main_hand[0] == 0:
            self.main_hand[0] = 1
            self.main_hand[1] = min(self.main_hand[1], self._get_max_selectable2() - 1)
            return True
        return False

    def updateOptions(self, owner_items, partner_items):
        self.owner_items = owner_items
        self.partner_items = partner_items

def drawTradePreview(surf, gameStateObj, steal=False, display_traveler=False):
    unit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
    position = unit.position
    if display_traveler and unit.TRV:
        unit = gameStateObj.get_unit_from_id(unit.TRV)
    items = unit.items
    window = GC.IMAGESDICT['Trade_Window']
    width, height = window.get_width(), window.get_height()
    top_of_window = Engine.subsurface(window, (0, 0, width, 27))
    bottom_of_window = Engine.subsurface(window, (0, height - 5, width, 5))
    middle_of_window = Engine.subsurface(window, (0, height//2 + 3, width, 16))
    size = (width, top_of_window.get_height() + bottom_of_window.get_height() + middle_of_window.get_height() * max(1, len(items)) - 2)
    BGSurf = Engine.create_surface(size, transparent=True)
    BGSurf.blit(top_of_window, (0, 0))

    for index, item in enumerate(items):
        BGSurf.blit(middle_of_window, (0, top_of_window.get_height() + index * middle_of_window.get_height()))
    if not items:
        BGSurf.blit(middle_of_window, (0, top_of_window.get_height()))
    BGSurf.blit(bottom_of_window, (0, BGSurf.get_height() - bottom_of_window.get_height()))
    BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, 10)

    for index, item in enumerate(items):
        # Item image
        item.draw(BGSurf, (8, top_of_window.get_height() + index * middle_of_window.get_height() - 2))
        if item.locked or (steal and item is unit.getMainWeapon()):
            name_font = GC.FONT['text_grey']
            uses_font = GC.FONT['text_grey']
        else:
            name_font = GC.FONT['text_white']
            uses_font = GC.FONT['text_blue']
        # Name of item
        height = top_of_window.get_height() + index * name_font.height - 2
        right = BGSurf.get_width() - 4
        name_font.blit(item.name, BGSurf, (25, height))
        # Uses for item
        if item.uses:
            uses_width = uses_font.size(str(item.uses))[0]
            uses_font.blit(str(item.uses), BGSurf, (right - uses_width, height))
        elif item.c_uses:
            uses_width = uses_font.size(str(item.c_uses))[0]
            uses_font.blit(str(item.c_uses), BGSurf, (right - uses_width, height))
        elif item.cooldown:
            if item.cooldown.charged:
                uses_font = GC.FONT['text_light_green']
                uses_width = uses_font.size(str(item.cooldown.cd_uses))[0]
                uses_font.blit(str(item.cooldown.cd_uses), BGSurf, (right - uses_width, height - 1))
                build_cd_groove(BGSurf, (right - 15, height + name_font.height - 3), 16,
                                int(round((int(item.cooldown.cd_uses) / int(item.cooldown.total_cd_uses)) * 16)), False)
            else:
                uses_font = GC.FONT['text_light_red']
                uses_width = uses_font.size((str(item.cooldown.cd_turns)))[0]
                uses_font.blit((str(item.cooldown.cd_turns)), BGSurf, (right - uses_width, height - 1))
                build_cd_groove(BGSurf, (right - 15, height + name_font.height - 3), 16,
                                int(round((int(item.cooldown.cd_turns) / int(item.cooldown.total_cd_turns)) * 16)), True)
        else:
            uses_width = uses_font.size('--')[0]
            uses_font.blit('--', BGSurf, (right - uses_width, height))
    if not items:
        GC.FONT['text_grey'].blit(cf.WORDS['Nothing'], BGSurf, (25, top_of_window.get_height() - 2))

    # Blit Character's name and passive Sprite
    unit_surf = unit.sprite.create_image('passive')

    GC.FONT['text_white'].blit(unit.name, BGSurf, (32, 8))

    if position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1:
        b_topleft = (0, 0)
        u_topleft = (12 - max(0, (unit_surf.get_width() - 16)//2), 8 - max(0, (unit_surf.get_width() - 16)//2))
    else:
        b_topleft = (GC.WINWIDTH - 4 - BGSurf.get_width(), 0)
        u_topleft = (GC.WINWIDTH - BGSurf.get_width() + 4 - max(0, (unit_surf.get_width() - 16)//2), 8 - max(0, (unit_surf.get_width() - 16)//2))

    surf.blit(BGSurf, b_topleft)
    surf.blit(unit_surf, u_topleft)

def drawRescuePreview(surf, gameStateObj):
    rescuer = gameStateObj.cursor.currentSelectedUnit
    rescuee = gameStateObj.cursor.getHoveredUnit(gameStateObj)
    window = GC.IMAGESDICT['RescueWindow'].copy()
    width = window.get_width()
    con = str(rescuee.getWeight())
    aid = str(rescuer.getAid())
    num_font = GC.FONT['text_blue']
    num_font.blit(con, window, (width - num_font.size(con)[0] - 3, 72))
    num_font.blit(aid, window, (width - num_font.size(aid)[0] - 3, 24))
    rescuer_surf = rescuer.sprite.create_image('passive')
    rescuee_surf = rescuee.sprite.create_image('passive')
    left = 12 - max(0, (rescuer_surf.get_width() - 16)//2)
    top = 8 - max(0, (rescuer_surf.get_width() - 16)//2)
    window.blit(rescuer_surf, (left, top))
    window.blit(rescuee_surf, (left, top + 48))
    GC.FONT['text_white'].blit(rescuer.name, window, (32, 8))
    GC.FONT['text_white'].blit(rescuee.name, window, (32, 56))

    if rescuer.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1:
        topleft = (0, 0)
    else:
        topleft = (GC.WINWIDTH - 4 - width, 0)

    surf.blit(window, topleft)

class RecordsDisplay(ChoiceMenu):
    def __init__(self, stats):
        self.options = []
        for level in stats:
            name = level.name
            turncount = level.turncount
            mvp = level.get_mvp()
            self.options.append((name, turncount, mvp))

        self.set_up()

        self.total_turns = sum([option[1] for option in self.options])
        self.mvp_dict = self.get_game_mvp_dict(stats)

        self.back_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def set_up(self):
        self.currentSelection = 0
        self.scroll = 0
        self.limit = 6
        self.ignore = None
        self.menu_width = 224

        Counters.CursorControl.__init__(self)
        self.cursor_y_offset = 0

        # Not really -- only used for scroll bar
        self.topleft = (0, 16)
        self.scroll_bar = GUIObjects.ScrollBar((self.topleft[0] + self.menu_width, self.topleft[1]))

        self.left_arrow = GUIObjects.ScrollArrow('left', (self.topleft[0] + 2, self.topleft[1] - 7))
        self.right_arrow = GUIObjects.ScrollArrow('right', (self.topleft[0] + 8 + self.menu_width - 1, self.topleft[1] - 7))

    def get_game_mvp_dict(self, stats):
        mvp_dict = collections.Counter()
        for level in stats:
            # print('')
            for unit, record in level.stats.items():
                # print(unit, record),
                mvp_dict[unit] += CustomObjects.LevelStatistic.formula(record)
        return mvp_dict

    def drawTopArrows(self, surf):
        self.left_arrow.draw(surf)
        self.right_arrow.draw(surf)

    def draw_cursor(self, surf, index):
        x_position = self.topleft[0] - 8 + self.cursorAnim[self.cursorCounter]
        y_position = self.topleft[1] + 40 - 1 + index*16
        surf.blit(self.cursor, (x_position, y_position))

    def draw_highlight(self, surf, index):
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range((self.menu_width - 16)//width): # Gives me the amount of highlight needed
            topleft = (self.topleft[0] + 8 + slot*width, self.topleft[1] + 12 + 1 + index*16)
            surf.blit(highlightSurf, topleft)

    def create_top_banner(self):
        banner_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, 24), 'WhiteMenuBackground75')
        GC.FONT['text_yellow'].blit(cf.WORDS['Total Turns'], banner_surf, (4, 4))
        total_turns = str(self.total_turns)
        GC.FONT['text_blue'].blit(total_turns, banner_surf, (92 - GC.FONT['text_blue'].size(total_turns)[0], 4))
        GC.FONT['text_yellow'].blit(cf.WORDS['Overall MVP'], banner_surf, (100, 4))
        if self.mvp_dict:
            game_mvp = Utility.key_with_max_val(self.mvp_dict)
        else:
            game_mvp = '--'
        GC.FONT['text_white'].blit(game_mvp, banner_surf, (224 - 8 - GC.FONT['text_white'].size(game_mvp)[0], 4))
        return banner_surf

    def draw_record(self, surf, record, y, x_offset=0):
        GC.FONT['text_blue'].blit(str(record['kills']), surf, (x_offset + 110 - GC.FONT['text_blue'].size(str(record['kills']))[0] + 4, y))
        damage = str(record['damage'])
        # if record['damage'] >= 1000:
        #    damage = damage[:-2] + 'h'
        healing = str(record['healing'])
        # if record['healing'] >= 1000:
        #    healing = healing[:-2] + 'h'
        GC.FONT['text_blue'].blit(damage, surf, (x_offset + 160 - GC.FONT['text_blue'].size(str(record['damage']))[0] + 4, y))
        GC.FONT['text_blue'].blit(healing, surf, (x_offset + 206 - GC.FONT['text_blue'].size(str(record['healing']))[0] + 4, y))

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH//2 - self.top_banner.get_width()//2, 4))

        back_surf = self.back_surf.copy()
        self.draw_highlight(back_surf, self.currentSelection - self.scroll)
        # Draw scroll bar
        if len(self.options) > self.limit:
            self.scroll_bar.draw(back_surf, self.scroll, self.limit, len(self.options))

        # Blit titles
        GC.FONT['text_yellow'].blit(cf.WORDS['Records Header'], back_surf, (4, 4))
        for index, (name, turncount, mvp) in enumerate(self.options[self.scroll:self.scroll+self.limit]):
            GC.FONT['text_white'].blit(name, back_surf, (4, index*16 + 20))
            GC.FONT['text_blue'].blit(str(turncount), back_surf, (self.menu_width//2 - GC.FONT['text_blue'].size(str(turncount))[0] + 8, index*16 + 20))
            GC.FONT['text_white'].blit(mvp, back_surf, (self.menu_width - 28 - GC.FONT['text_white'].size(mvp)[0]//2, index*16 + 20))

        surf.blit(back_surf, (8 + offset_x, 32 + offset_y))

        if not offset_x and not offset_y:
            self.draw_cursor(surf, self.currentSelection-self.scroll)
            self.drawTopArrows(surf)

class UnitStats(RecordsDisplay):
    def __init__(self, name, stats):
        self.name = name
        self.options = [(level_name, record) for (level_name, record) in stats]

        self.set_up()

        self.back_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def create_top_banner(self):
        banner_surf = GC.IMAGESDICT['PurpleBackground'].copy()
        GC.FONT['chapter_grey'].blit(self.name, banner_surf, (banner_surf.get_width()//2 - GC.FONT['chapter_grey'].size(self.name)[0]//2, 4))
        return banner_surf

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH//2 - self.top_banner.get_width()//2 + offset_x, 4 + offset_y))

        back_surf = self.back_surf.copy()

        # Draw scroll bar
        if len(self.options) > self.limit:
            self.scroll_bar.draw(back_surf, self.scroll, self.limit, len(self.options))

        # Blit titles
        GC.FONT['text_yellow'].blit(cf.WORDS['UnitStat Header'], back_surf, (4, 4))
        for index, (level_name, record) in enumerate(self.options[self.scroll:self.scroll+self.limit]):
            y = index*16 + 20
            GC.FONT['text_white'].blit(level_name, back_surf, (4, y))
            self.draw_record(back_surf, record, y)

        surf.blit(back_surf, (8 + offset_x, 32 + offset_y))

        if not offset_x and not offset_y:
            self.draw_cursor(surf, self.currentSelection-self.scroll)
            self.drawTopArrows(surf)

class MVPDisplay(RecordsDisplay):
    def __init__(self, stats):
        self.mvp_dict = {}
        for level in stats:
            for unit, record in level.stats.items():
                if unit in self.mvp_dict:
                    for stat in record:
                        self.mvp_dict[unit][stat] += record[stat]
                else:
                    self.mvp_dict[unit] = {k: v for (k, v) in record.items()}

        # Now convert to list and sort
        self.options = list(self.mvp_dict.items())
        self.options = sorted(self.options, key=lambda record: CustomObjects.LevelStatistic.formula(record[1]), reverse=True)

        self.set_up()

        self.total_turns = sum([level.turncount for level in stats])
        self.mvp_dict = self.get_game_mvp_dict(stats)

        self.back_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH//2 - self.top_banner.get_width()//2, 4))
        self.draw_rest(surf, offset_x, offset_y)

    def draw_rest(self, surf, offset_x=0, offset_y=0):
        back_surf = self.back_surf.copy()
        self.draw_highlight(back_surf, self.currentSelection - self.scroll)

        # Draw scroll bar
        if len(self.options) > self.limit:
            self.scroll_bar.draw(back_surf, self.scroll, self.limit, len(self.options))

        # Blit titles
        GC.FONT['text_yellow'].blit(cf.WORDS['MVP Header'], back_surf, (4, 4))
        for index, (unit, record) in enumerate(self.options[self.scroll:self.scroll+self.limit]):
            y = index*16 + 20
            GC.FONT['text_yellow'].blit(str(index+self.scroll+1), back_surf, (10, y))
            GC.FONT['text_white'].blit(unit, back_surf, (41, y))
            self.draw_record(back_surf, record, y)

        surf.blit(back_surf, (8 + offset_x, 32 + offset_y))

        if not offset_x and not offset_y:
            self.draw_cursor(surf, self.currentSelection-self.scroll)
            self.drawTopArrows(surf)

class ChapterStats(MVPDisplay):
    def __init__(self, level):
        self.name = level.name
        self.mvp_dict = level.stats

        # Now convert to list and sort
        self.options = list(self.mvp_dict.items())
        self.options = sorted(self.options, key=lambda record: CustomObjects.LevelStatistic.formula(record[1]), reverse=True)

        self.set_up()

        self.back_surf = BaseMenuSurf.CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def create_top_banner(self):
        banner_surf = GC.IMAGESDICT['PurpleBackground'].copy()
        GC.FONT['chapter_grey'].blit(self.name, banner_surf, (banner_surf.get_width()//2 - GC.FONT['chapter_grey'].size(self.name)[0]//2, 4))
        return banner_surf

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH//2 - self.top_banner.get_width()//2 + offset_x, 4 + offset_y))
        self.draw_rest(surf, offset_x, offset_y)
