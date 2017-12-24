import datetime, collections
import GlobalConstants as GC
import configuration as cf
import ItemMethods, Image_Modification, Utility, Engine, Counters
import StateMachine, InfoMenu, GUIObjects
import CustomObjects

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

class MovingBackground(object):
    def __init__(self, BGSurf):
        self.lastBackgroundUpdate = Engine.get_time()
        self.change_counter = 0
        self.backgroundCounter = 0
        self.BGSurf = BGSurf

    def draw(self, surf):
        self.change_counter += 1
        if self.change_counter > 2:
            self.change_counter = 0
        if self.change_counter == 0:
            self.backgroundCounter += 1
            if self.backgroundCounter >= self.BGSurf.get_width():
                self.backgroundCounter = 0
        
        # Clip the Background surface based on how much it needs to be moved
        BG1Sub = (self.backgroundCounter, 0, min(self.BGSurf.get_width() - self.backgroundCounter, GC.WINWIDTH), GC.WINHEIGHT)
        BG1Surf = Engine.subsurface(self.BGSurf, BG1Sub)

        # Determine if we need a second section of the background surface to fill up the rest of the background
        if BG1Surf.get_width() < GC.WINWIDTH:
            BG2Sub = (0, 0, min(self.BGSurf.get_width() - BG1Surf.get_width(), GC.WINWIDTH), GC.WINHEIGHT)
            BG2Surf = Engine.subsurface(self.BGSurf, BG2Sub)
            surf.blit(BG2Surf, (BG1Surf.get_width(), 0))
        surf.blit(BG1Surf, (0, 0))

class StaticBackground(object):
    def __init__(self, BGSurf, fade=True):
        self.BGSurf = BGSurf
        if fade:
            self.fade = 100
            self.state = "In"
        else:
            self.fade = 0
            self.state = "Neutral"

    def draw(self, surf):
        if self.state == "In":
            self.fade -= 4
            BGSurf = Image_Modification.flickerImageTranslucent(self.BGSurf, self.fade)
            if self.fade <= 0:
                self.fade = 0
                self.state = "Neutral"
        elif self.state == "Out":
            self.fade += 4
            BGSurf = Image_Modification.flickerImageTranslucent(self.BGSurf, self.fade)
            if self.fade >= 100:
                return True
        else:
            BGSurf = self.BGSurf
        surf.blit(BGSurf, (0, 0))
        return False

    def fade_out(self):
        self.state = "Out"

class MovieBackground(object):
    def __init__(self, movie_prefix):
        self.counter = 0
        self.movie_prefix = movie_prefix
        self.num_frames = len([image_name for image_name in GC.IMAGESDICT if image_name.startswith(movie_prefix)])

        self.last_update = 0
        self.speed = 125

    def draw(self, surf):
        if Engine.get_time() - self.last_update > self.speed:
            self.counter += 1
            self.last_update = Engine.get_time()
            if self.counter >= self.num_frames:
                self.counter = 0
        image = GC.IMAGESDICT[self.movie_prefix + str(self.counter)]
        surf.blit(image, (0, 0))

class Foreground(object):
    def __init__(self):
        self.foreground = None
        self.foreground_frames = 0
        self.fade_out = False
        self.fade_out_frames = 0

    def flash(self, num_frames, fade_out, color=(248, 248, 248)):
        self.foreground_frames = num_frames
        self.foreground = GC.IMAGESDICT['BlackBackground'].copy()
        Engine.fill(self.foreground, color)
        self.fade_out_frames = fade_out

    def draw(self, surf, blend=False):
        # Screen flash
        if self.foreground or self.fade_out_frames:
            if self.fade_out:
                alpha = 100 - self.foreground_frames/float(self.fade_out_frames)*100
                foreground = Image_Modification.flickerImageTranslucent(self.foreground, alpha)
            else:
                foreground = self.foreground\
            # Always additive blend
            Engine.blit(surf, foreground, (0, 0), blend=Engine.BLEND_RGB_ADD)
            self.foreground_frames -= 1
            # If done
            if self.foreground_frames <= 0:
                if self.fade_out_frames and not self.fade_out:
                    self.foreground_frames = self.fade_out_frames
                    self.fade_out = True
                else:
                    self.fade_out_frames = 0
                    self.foreground_frames = 0
                    self.foreground = None
                    self.fade_out = False

class MoneyCounterDisplay(object):
    def __init__(self, topright):
        self.topright = topright
        self.update_num = -200

    def start(self, money):
        self.update_num = 100
        if money >= 0:
            font = GC.FONT['text_green']
        else:
            font = GC.FONT['text_red']
        money_str = str(money)
        if money >= 0:
            money_str = '+' + money_str
        money_size = font.size(money_str)[0]
        self.surf = Engine.create_surface((money_size + 8, 16), transparent=True)
        self.width = self.surf.get_width()
        font.blit(money_str, self.surf, (0, 0))

    def draw(self, surf):
        if self.update_num > -200:
            self.update_num -= 5
            # Fade in and move up
            if self.update_num > 0:
                my_surf = Image_Modification.flickerImageTranslucent(self.surf, self.update_num)
                surf.blit(my_surf, (self.topright[0] - self.width, self.topright[1] + self.update_num/5))
            # Fade out
            else: 
                if self.update_num < -100:
                    my_surf = Image_Modification.flickerImageTranslucent(self.surf, -self.update_num - 100)
                else:
                    my_surf = self.surf
                surf.blit(my_surf, (self.topright[0] - self.width, self.topright[1]))

class StatusMenu(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.background = MovingBackground(GC.IMAGESDICT['StatusBackground'])
            self.surfaces = self.get_surfaces(gameStateObj, metaDataObj)
            # backSurf
            self.backSurf = gameStateObj.generic_surf

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'
        
    def get_surfaces(self, gameStateObj, metaDataObj):
        surfaces = []
        # Background
        name_back_surf = GC.IMAGESDICT['ChapterSelect']
        surfaces.append((name_back_surf, (24, 2)))
        # Text
        big_font = GC.FONT['chapter_green']
        name_size = (big_font.size(metaDataObj['name'])[0] + 1, big_font.height)
        name_surf = Engine.create_surface(name_size, transparent=True, convert=True)
        big_font.blit(metaDataObj['name'], name_surf, (0, 0))
        pos = (24 + name_back_surf.get_width()/2 - name_surf.get_width()/2, 2 + name_back_surf.get_height()/2 - name_surf.get_height()/2)
        surfaces.append((name_surf, pos))                    
        # Background
        back_surf = CreateBaseMenuSurf((GC.WINWIDTH - 8, 24), 'WhiteMenuBackgroundOpaque')
        surfaces.append((back_surf, (4, 34)))
        # Get Words
        golden_words_surf = GC.IMAGESDICT['GoldenWords']
        # Get Turn
        turn_surf = Engine.subsurface(golden_words_surf, (0, 17, 26, 10))
        surfaces.append((turn_surf, (10, 42)))
        # Get Funds
        funds_surf = Engine.subsurface(golden_words_surf, (0, 33, 32, 10))
        surfaces.append((funds_surf, (GC.WINWIDTH/3 - 8, 42)))
        # Get PlayTime
        playtime_surf = Engine.subsurface(golden_words_surf, (32, 15, 17, 13))
        surfaces.append((playtime_surf, (2*GC.WINWIDTH/3 + 6, 39)))
        # Get G
        g_surf = Engine.subsurface(golden_words_surf, (40, 50, 9, 9))
        surfaces.append((g_surf, (2*GC.WINWIDTH/3 - 8 - 1, 43)))
        # TurnCountSurf
        turn_count_size = (GC.FONT['text_blue'].size(str(gameStateObj.turncount))[0] + 1, GC.FONT['text_blue'].height)
        turn_count_surf = Engine.create_surface(turn_count_size, transparent=True, convert=True)
        GC.FONT['text_blue'].blit(str(gameStateObj.turncount), turn_count_surf, (0, 0))
        surfaces.append((turn_count_surf, (GC.WINWIDTH/3 - 16 - turn_count_surf.get_width(), 38)))                    
        # MoneySurf
        money_size = (GC.FONT['text_blue'].size(str(gameStateObj.counters['money']))[0] + 1, GC.FONT['text_blue'].height)
        money_surf = Engine.create_surface(money_size, transparent=True, convert=True)
        GC.FONT['text_blue'].blit(str(gameStateObj.counters['money']), money_surf, (0, 0))
        surfaces.append((money_surf, (2*GC.WINWIDTH/3 - 8 - 4 - money_surf.get_width(), 38)))

        # Get win and loss conditions
        win_cons, win_connectives = gameStateObj.objective.get_win_conditions(gameStateObj)
        loss_cons, loss_connectives = gameStateObj.objective.get_loss_conditions(gameStateObj)

        hold_surf = CreateBaseMenuSurf((GC.WINWIDTH - 16, 8 + 16 + 16 + 16*len(win_cons) + 16 * len(loss_cons)))

        GC.FONT['text_yellow'].blit(cf.WORDS['Win Conditions'], hold_surf, (4, 4))

        for index, win_con in enumerate(win_cons):
            GC.FONT['text_white'].blit(win_con, hold_surf, (8, 20 + 16*index))

        GC.FONT['text_yellow'].blit(cf.WORDS['Loss Conditions'], hold_surf, (4, 20 + 16*len(win_cons)))

        for index, loss_con in enumerate(loss_cons):
            GC.FONT['text_white'].blit(loss_con, hold_surf, (8, 36 + 16*len(win_cons) + index*16))

        surfaces.append((hold_surf, (8, 34 + back_surf.get_height() + 2)))
            
        return surfaces

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'BACK':
            gameStateObj.stateMachine.changeState('transition_pop')

    def update(self, gameStateObj, metaDataObj):
        pass

    def draw(self, gameStateObj, metaDataObj):
        self.background.draw(self.backSurf)

        # Non moving surfaces
        for (surface, rect) in self.surfaces:
            self.backSurf.blit(surface, rect)

        # Playtime
        time = datetime.timedelta(milliseconds=gameStateObj.playtime)
        seconds = int(time.total_seconds())
        hours = min(seconds/3600, 99)
        minutes = str((seconds%3600)/60)
        if len(minutes) < 2:
            minutes = '0' + minutes
        seconds = str(seconds%60)
        if len(seconds) < 2:
            seconds = '0' + seconds

        formatted_time = ':'.join([str(hours), str(minutes), str(seconds)])
        formatted_time_size = (GC.FONT['text_blue'].size(formatted_time)[0], GC.FONT['text_blue'].height)
        # Truncate seconds section. I don't care, and could add those later if I wished
        GC.FONT['text_blue'].blit(formatted_time, self.backSurf, (GC.WINWIDTH - 8 - formatted_time_size[0], 38))

        return self.backSurf
        
def CreateBaseMenuSurf((width, height), baseimage='BaseMenuBackground', top_left_sigil=None):
    menuBaseSprite = GC.IMAGESDICT[baseimage]
    # Get total width and height.
    # Each piece of the menu (9) should be 1/3 of these dimensions
    mBSWidth = menuBaseSprite.get_width()
    mBSHeight = menuBaseSprite.get_height()

    # Force the width and height to be correct!
    full_width = width - width%(mBSWidth/3)
    full_height = height - height%(mBSHeight/3)
    width = mBSWidth/3
    height = mBSHeight/3

    assert full_width%(width) == 0, "The dimensions of the menu are wrong - the sprites will not line up correctly. They must be multiples of 8. %s" %(width)
    assert full_height%(height) == 0, "The dimensions of the manu are wrong - the sprites will not line up correctly. They must be multiples of 8. %s" %(height)

    # Create simple surfs to be blitted from the menuBaseSprite
    TopLeftSurf = Engine.subsurface(menuBaseSprite, (0, 0, width, height))
    TopSurf = Engine.subsurface(menuBaseSprite, (width, 0, width, height))
    TopRightSurf = Engine.subsurface(menuBaseSprite, (2*width, 0, width, height))
    LeftSurf = Engine.subsurface(menuBaseSprite, (0, height, width, height))
    CenterSurf = Engine.subsurface(menuBaseSprite, (width, height, width, height))
    RightSurf = Engine.subsurface(menuBaseSprite, (2*width, height, width, height))
    BottomLeftSurf = Engine.subsurface(menuBaseSprite, (0, 2*height, width, height))
    BottomSurf = Engine.subsurface(menuBaseSprite, (width, 2*height, width, height))
    BottomRightSurf = Engine.subsurface(menuBaseSprite, (2*width, 2*height, width, height))

    # Create transparent background
    MainMenuSurface = Engine.create_surface((full_width, full_height), transparent=True, convert=True)

    # Blit Center sprite
    for positionx in range(full_width/width - 2):
        for positiony in range(full_height/height - 2):
            topleft = ((positionx+1)*width, (positiony+1)*height)
            MainMenuSurface.blit(CenterSurf, topleft)

    # Blit Edges
    for position in range(full_width/width - 2): # For each position in which this would fit
        topleft = ((position+1)*width, 0)
        MainMenuSurface.blit(TopSurf, topleft)
    # --
    for position in range(full_width/width - 2):
        topleft = ((position+1)*width, full_height - height)
        MainMenuSurface.blit(BottomSurf, topleft)
    # --
    for position in range(full_height/height - 2):
        topleft = (0, (position+1)*height)
        MainMenuSurface.blit(LeftSurf, topleft)
    # --
    for position in range(full_height/height - 2):
        topleft = (full_width - width, (position+1)*height)
        MainMenuSurface.blit(RightSurf, topleft)

    # Perhaps switch order in which these are blitted
    # Blit corners
    MainMenuSurface.blit(TopLeftSurf, (0, 0))
    # --
    MainMenuSurface.blit(TopRightSurf, (full_width - width, 0))
    # --
    MainMenuSurface.blit(BottomLeftSurf, (0, full_height - height))
    # --
    MainMenuSurface.blit(BottomRightSurf, (full_width - width, full_height - height))

    return MainMenuSurface

class Lore_Display(object):
    def __init__(self, starting_entry):
        self.topleft = (72, 4)
        self.menu_width = GC.WINWIDTH - 72 - 4
        self.back_surf = CreateBaseMenuSurf((self.menu_width, GC.WINHEIGHT - 8))

        self.update_entry(starting_entry)

    def update_entry(self, entry):
        self.image = self.back_surf.copy()
        if entry['type'] == cf.WORDS['Character']:
            current_image = GC.UNITDICT[entry['short_name'] + 'Portrait']
            current_image = Engine.subsurface(current_image, (0, 0, 96, 80))
            current_image = Image_Modification.flickerImageTranslucentColorKey(current_image, 50)
            self.image.blit(current_image, (self.menu_width - 96, GC.WINHEIGHT - 8 - 80 - 4))

        GC.FONT['text_yellow'].blit(entry['long_name'], self.image, (self.menu_width/2 - GC.FONT['text_yellow'].size(entry['long_name'])[0]/2, 4))

        output_lines = line_wrap(line_chunk(entry['desc']), self.menu_width - 12, GC.FONT['text_white'])
        if entry['type'] == cf.WORDS['Character']:
            first_section = output_lines[:4]
            second_section = output_lines[4:]
            if second_section:
                second_section = line_wrap(line_chunk(' '.join(second_section)), self.menu_width - 80, GC.FONT['text_white'])
            output_lines = first_section + second_section

        # Now draw
        for index, line in enumerate(output_lines):
            GC.FONT['text_white'].blit(''.join(line), self.image, (4, GC.FONT['text_white'].height*index + 4 + 16))

    def draw(self, surf):
        surf.blit(self.image, self.topleft)

def line_chunk(text):
    chunks = text.strip().split(' ')
    chunks = filter(None, chunks) # Remove empty chunks
    return chunks

def line_wrap(chunks, width, font, test=False):
    lines = []
    chunks.reverse()
    space_length = font.size(' ')[0]

    while chunks:
        cur_line = []
        cur_len = 0

        while chunks:
            length = font.size(chunks[-1])[0]
            # print(cur_line, chunks[-1], cur_len, length, width)
            if length > width:
                if test:
                    return 'Too big!'
                # else
                if cur_line:
                    lines.append(' '.join(cur_line))
                cur_line = []
                cur_len = 0
                cur_line.append(chunks.pop())
                cur_len += length
                cur_len += space_length
            # Can at least squeeze this chunk onto the current line
            elif cur_len + length <= width:
                cur_line.append(chunks.pop())
                cur_len += length
                cur_len += space_length
            # Nope, this line is full
            else:
                break

        # Convert current line back to a string and store it in list
        # of all lines (return value).
        if cur_line:
            lines.append(' '.join(cur_line))
    return lines
    
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
        for slot in range((self.menu_width - 10)/width): # Gives me the amount of highlight needed
            topleft = (self.topleft[0] + 5 + slot*width, self.topleft[1] + 12 + index*16 + 1)
            surf.blit(highlightSurf, topleft)

class ChoiceMenu(SimpleMenu):
    def __init__(self, owner, options, topleft, gameStateObj=None, horizontal=False,
                 background='BaseMenuBackgroundOpaque', limit=None, hard_limit=False,
                 info_desc=[], color_control=None, ignore=None, width=None, shimmer=0,
                 gem=True):
        self.set_width = width

        SimpleMenu.__init__(self, owner, options, topleft, background)

        self.horizontal = horizontal

        if self.horizontal: # Does not support items
            self.bg_surf = CreateBaseMenuSurf((GC.FONT['text_white'].size('  '.join(self.options))[0] + 16, 24), background)
        else:
            if limit and (len(self.options) > limit or hard_limit):
                height = (8 + 16*limit)
            else:
                height = (8 + 16*len(self.options)) 
            # Add small gem
            bg_surf = CreateBaseMenuSurf((self.menu_width, height), background)
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
        self.info_desc = info_desc

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
                return 104 # This is the recommended menu width for items
            else:
                option_width = GC.FONT['text_white'].size(option)[0]
                if option_width > longest_width_needed:
                    longest_width_needed = option_width
        return (longest_width_needed - longest_width_needed%8 + 24)

    def get_topleft(self, gameStateObj):
        if self.topleft == 'auto':
            if gameStateObj.cursor.position[0] > GC.WINWIDTH/GC.TILEWIDTH/2 + gameStateObj.cameraOffset.get_x():
                self.topleft = (8, 8)
            else:
                self.topleft = (GC.WINWIDTH - self.menu_width - 8, 8)
        elif self.topleft == 'child':
            if gameStateObj.cursor.position[0] > GC.WINWIDTH/GC.TILEWIDTH/2 + gameStateObj.cameraOffset.get_x():
                self.topleft = (8 + gameStateObj.activeMenu.menu_width - 32, gameStateObj.activeMenu.currentSelection*16 + 8)
            else:
                self.topleft = (GC.WINWIDTH - 32 - 8 - gameStateObj.activeMenu.menu_width, gameStateObj.activeMenu.currentSelection*16 + 8)
        elif self.topleft == 'center':
            self.topleft = (GC.WINWIDTH/2 - self.menu_width/2, GC.WINHEIGHT/2 - (len(self.options)*16)/2)

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

        if self.ignore and self.ignore[self.currentSelection]:
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

        if self.ignore and self.ignore[self.currentSelection]:
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
        self.scroll = Utility.clamp(self.scroll, 0, max(0, len(self.options) - self.limit))

    def draw(self, surf, gameStateObj=None):
        if self.horizontal:
            self.horiz_draw(surf)
        else:
            self.vert_draw(surf)

    def drawInfo(self, surf):
        if self.info_flag:
            option = self.getSelection()
            if isinstance(option, ItemMethods.ItemObject):
                help_box = option.get_help_box()
            elif self.info_desc:
                help_box = InfoMenu.create_help_box(self.info_desc[self.currentSelection])
            else:
                return

            if self.topleft[0] < GC.WINWIDTH/2:
                surf.blit(help_box, (self.topleft[0], self.topleft[1] + 20 + 16*self.currentSelection))
            else:
                surf.blit(help_box, (self.topleft[0] + self.menu_width - help_box.get_width(), self.topleft[1] + 20 + 16*self.currentSelection))

    def drawFace(self, surf):
        face_image = self.owner.bigportrait.copy()
        face_image = Engine.flip_horiz(face_image)
        face_image = Image_Modification.flickerImageTranslucentColorKey(face_image, 50)
        left = self.topleft[0] + self.bg_surf.get_width()/2 - face_image.get_width()/2
        top = self.topleft[1] + self.bg_surf.get_height()/2 - face_image.get_height()/2 - 3
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
                    elif self.owner.canWield(option):
                        main_font = GC.FONT['text_white']
                        uses_font = GC.FONT['text_blue']
                    main_font.blit(str(option), surf, (left + 20, top))
                    uses_string = "--"
                    if option.uses:
                        uses_string = str(option.uses)
                    elif option.c_uses:
                        uses_string = str(option.c_uses)
                    pos = (left + self.menu_width - 4 - uses_font.size(uses_string)[0] - (5 if self.limit and len(self.options) > self.limit else 0), top)
                    uses_font.blit(uses_string, surf, pos)
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

class ItemUseMenu(SimpleMenu):
    def __init__(self, owner, option, topleft, background='BaseMenuBackground'):
        SimpleMenu.__init__(self, owner, option, topleft, background)
        self.legal_indices = [index for index, opt in self.options if opt.usable and opt.booster]
        self.true_selection = 0
        self.currentSelection = self.legal_indices[self.true_selection]

    def moveUp(self, first_push=True):
        if first_push:
            self.true_selection += 1
            if self.true_selection > len(self.legal_indices) - 1:
                self.true_selection = 0
        else:
            self.true_selection = min(self.true_selection + 1, len(self.legal_indices) - 1)
        self.currentSelection = self.legal_indices[self.true_selection]

    def moveDown(self, first_push=True):
        if first_push:
            self.true_selection -= 1
            if self.true_selection < 0:
                self.true_selection = len(self.legal_indices) - 1
        else:
            self.true_selection = max(self.true_selection - 1, 0)
        self.currentSelection = self.legal_indices[self.true_selection]

    def draw(self, surf):
        BGSurf = CreateBaseMenuSurf((self.menu_width, 16*5+8), self.background)
        # Blit face
        face_image = self.owner.bigportrait.copy()
        face_image = Engine.flip_horiz(face_image)
        BGSurf.blit(face_image, (0, 0))

        self.draw_highlight(BGSurf, self.currentSelection)
        for index, option in enumerate(self.options):
            option.draw(BGSurf, (4, 4 + index*16))
            name_font = GC.FONT['text_grey']
            uses_font = GC.FONT['text_grey']
            if option.usable and option.booster:
                name_font = GC.FONT['text_white']
                uses_font = GC.FONT['text_blue']
            name_font.blit(str(option), BGSurf, (20, 8+index*16))
            uses_string = "--"
            if option.uses:
                uses_string = str(option.uses)
            elif option.c_uses:
                uses_string = str(option.c_uses)
            uses_font.blit(uses_string, BGSurf, (self.menu_width - 4 - uses_font.size(uses_string), 8+index*16))
        surf.blit(BGSurf, self.topleft)
        self.draw_cursor(surf, self.currentSelection)

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
        split_num = len(self.options)/2
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
        split_num = len(self.options)/2
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
        split_num = len(self.options)/2
        if self.currentSelection < split_num:
            next_selection = self.currentSelection + split_num
            valid_indices = [index for index in range(split_num, len(self.options)) if self.isIndexValid(index)]
            if valid_indices:
                self.currentSelection = min(valid_indices, key=lambda x: abs(x-next_selection))

    def moveLeft(self, first_push=True):
        split_num = len(self.options)/2
        if self.currentSelection > split_num - 1:
            next_selection = self.currentSelection - split_num
            valid_indices = [index for index in range(0, split_num) if self.isIndexValid(index)]
            if valid_indices:
                self.currentSelection = min(valid_indices, key=lambda x: abs(x-next_selection))

    def draw_cursor(self, surf, index):
        split_num = len(self.options)/2
        x_position = self.topleft[0] - 12 + (index/split_num)*self.menu_width + self.cursorAnim[self.cursorCounter]
        y_position = self.topleft[1] + 8 + (index%split_num)*16
        surf.blit(self.cursor, (x_position, y_position))

    def draw_highlight(self, surf, index):
        split_num = len(self.options)/2
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range((self.menu_width - 16)/width): # Gives me the amount of highlight needed
            x_position = 8 + (index/split_num)*self.menu_width + slot*width
            y_position = 12 + (index%split_num)*16
            surf.blit(highlightSurf, (x_position, y_position))

    def draw(self, surf):
        split_num = len(self.options)/2
        BGSurf = CreateBaseMenuSurf((self.menu_width*2, 16*split_num+8), self.background)
        self.draw_highlight(BGSurf, self.currentSelection)

        for index, option in enumerate(self.options):
            position = 4+(index/split_num)*self.menu_width, 4 + index%split_num*16
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
        ComplexMenu.__init__(self, owner, options, (GC.WINWIDTH/2 - menu_width, GC.WINHEIGHT - len(options)/2*16 - 8), 'BaseMenuBackground')

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
        face_position_x = self.topleft[0] + self.menu_width - self.owner.bigportrait.get_width()/2
        face_position_y = self.topleft[1] - self.owner.bigportrait.get_height() + 8
        face_image = Engine.subsurface(self.owner.bigportrait, (0, 0, self.owner.bigportrait.get_width(), self.owner.bigportrait.get_height() - 8))
        surf.blit(face_image, (face_position_x, face_position_y))

    def draw_label(self, surf):
        label = cf.WORDS['Feat Choice']
        width = GC.FONT['text_white'].size(label)[0]
        menu_width = width - width%8 + 16
        bg_surf = CreateBaseMenuSurf((menu_width, 24))
        GC.FONT['text_white'].blit(label, bg_surf, (menu_width/2 - width/2, 4))
        surf.blit(bg_surf, (0, 0))

class ModeSelectMenu(SimpleMenu):
    def __init__(self, options, toggle, default=0):
        self.options = options
        self.toggle = toggle
        self.currentSelection = default

        self.label = CreateBaseMenuSurf((96, 88), 'BaseMenuBackgroundOpaque')
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
            font.blit(option, surf, (left + width/2 - font.size(option)[0]/2, top+4+index*32))

        # Draw cursor
        height = top - 16 + self.currentSelection*32 + self.cursorAnim[self.cursorCounter] + self.cursor_y_offset*16
        surf.blit(self.cursor, (0, height))
        self.cursor_y_offset = 0 # Reset

        # Draw gem
        surf.blit(self.label, (142, 52))
        # surf.blit(GC.IMAGESDICT['SmallGem'], (139, 48))
        # Draw text
        text = cf.WORDS['mode_' + self.options[self.currentSelection]]
        text_lines = line_wrap(line_chunk(text), 88, GC.FONT['text_white'])
        for index, line in enumerate(text_lines):
            GC.FONT['text_white'].blit(line, surf, (142 + 4, 52 + 4 + index*16))

# Support Conversation Menu
class SupportMenu(object):
    def __init__(self, owner, gameStateObj, topleft, background='BaseMenuBackground'):
        self.owner = owner
        self.updateOptions(gameStateObj)
        self.topleft = topleft
        self.back_surf = CreateBaseMenuSurf((136, 136), background)

        self.currentSelection = 0
        self.currentLevel = 0

        self.cursor = GC.IMAGESDICT['menuHand']

        self.cursor_flag = False

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

    def moveRight(self, first_push=True):
        self.currentLevel += 1
        limit = self.options[self.currentSelection][4]
        self.currentLevel = min(self.currentLevel, limit)

    def moveLeft(self, first_push=True):
        self.currentLevel -= 1
        if self.currentLevel < 0:
            self.currentLevel = 0
            return False
        return True

    def getSelection(self):
        return self.options[self.currentSelection], self.currentLevel

    def updateOptions(self, gameStateObj):
        names = gameStateObj.support.node_dict[self.owner.name].adjacent.keys()
        # convert names to units
        self.options = []
        for name in names:
            unit_sprite = None
            for unit in gameStateObj:
                if unit.team == 'player' and name == unit.name:
                    unit_sprite = unit.sprite
                    break
            if gameStateObj.support.node_dict[name].dead:
                pass
            else:
                continue
            # We haven't found unit yet, so just skip
            affinity = gameStateObj.support.node_dict[name].affinity
            edge = gameStateObj.support.node_dict[self.owner.name].adjacent[name]
            limit = edge.limit
            support_level = edge.current_value/cf.CONSTANTS['support_points'] # 0, 1, 2, 3
            self.options.append((name, unit_sprite, affinity, support_level, limit))

        self.currentSelection = 0

    def update(self):
        pass

    def draw(self, surf, gameStateObj):
        back_surf = self.back_surf.copy()
        units = []
        for index, (name, unit_sprite, affinity, support_level, limit) in enumerate(self.options):
            # Blit passive sprite
            unit_image = topleft = None
            if unit_sprite:
                unit_image = unit_sprite.create_image('passive')
                if index == self.currentSelection:
                    unit_image = unit_sprite.create_image('active')
                if gameStateObj.support.node_dict[name].dead:
                    unit_image = unit_sprite.create_image('gray')
                topleft = (4 - 24, 2 + (index+1)*16 - unit_image.get_height())
            units.append((unit_image, topleft))

            # Blit name
            position = (24 + 1, 2 + index*16)
            GC.FONT['text_white'].blit(name, back_surf, position)

            # Blit Affinity
            affinity.draw(back_surf, (72, 2 + index*16))

            # Blit LVS
            font = GC.FONT['text_white']
            letters = ['@', '`', '~'] # C, B, A
            if limit == 4:
                letters.append('%') # Big S
            for letter_index, letter in enumerate(letters):
                if letter_index + 1 > support_level:
                    font = GC.FONT['text_grey']
                font.blit(letter, back_surf, (90+letter_index*10, 2 + index*16))

        surf.blit(back_surf, self.topleft)
        for unit in units:
            if unit[0]:
                surf.blit(unit[0], (self.topleft[0] + unit[1][0], self.topleft[1] + unit[1][1]))

        # Blit cursor
        if self.cursor_flag:
            left = self.currentLevel*10 + self.topleft[0] + 100 - 12 - 10
            top = self.currentSelection*16 + self.topleft[1] + 2
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
        if background == 'ChapterSelect':
            self.menu_width = 192
            self.menu_height = 30
        
        self.cursorCounter = 0 # Helper counter for cursor animation
        self.cursorAnim = [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()

    def draw(self, surf, center=(GC.WINWIDTH/2, GC.WINHEIGHT/2), flicker=False, show_cursor=True):
        for index, option in enumerate(self.options):
            if flicker and self.currentSelection == index: # If the selection should flash white
                BGSurf = GC.IMAGESDICT[self.background + 'Flicker']
            elif self.currentSelection == index: # Highlight the chosen option
                BGSurf = GC.IMAGESDICT[self.background + 'Highlight']
            else:
                BGSurf = GC.IMAGESDICT[self.background]
            top = center[1] - (len(self.options)/2.0 - index)*(self.menu_height+1) + (20 if self.background == 'ChapterSelect' else 0) # What is this formula?
            left = center[0] - BGSurf.get_width()/2
            surf.blit(BGSurf, (left, top))
         
            position = (center[0] - GC.BASICFONT.size(str(option))[0]/2, top + BGSurf.get_height()/2 - GC.BASICFONT.size(str(option))[1]/2)
            color_transition = Image_Modification.color_transition(GC.COLORDICT['light_blue'], GC.COLORDICT['off_black'])
            OutlineFont(GC.BASICFONT, str(option), surf, GC.COLORDICT['off_white'], color_transition, position)
  
        if show_cursor:
            height = center[1] - 12 - (len(self.options)/2.0 - self.currentSelection)*(self.menu_height+1) + self.cursorAnim[self.cursorCounter]
            if self.background == 'ChapterSelect':
                height += 22 
            
            surf.blit(self.cursor1, (center[0] - self.menu_width/2 - self.cursor1.get_width()/2 - 8, height))
            surf.blit(self.cursor2, (center[0] + self.menu_width/2 - self.cursor2.get_width()/2 + 8, height))

    def getSelection(self):
        return self.options[self.currentSelection]

    def getSelectionIndex(self):
        return self.currentSelection

    def moveDown(self):
        self.currentSelection += 1
        if self.currentSelection > len(self.options) - 1:
            self.currentSelection = 0

    def moveUp(self):
        self.currentSelection -= 1
        if self.currentSelection < 0:
            self.currentSelection = len(self.options) - 1

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
    def __init__(self, options):
        MainMenu.__init__(self, options, 'ChapterSelect')
        self.use_rel_y = (len(options) > 3)
        self.use_transparency = True
        self.rel_pos_y = 0

    def moveUp(self):
        MainMenu.moveUp(self)
        if self.use_rel_y:
            self.rel_pos_y -= self.menu_height

    def moveDown(self):
        MainMenu.moveDown(self)
        if self.use_rel_y:
            self.rel_pos_y += self.menu_height

    def update(self):
        MainMenu.update(self)
        if self.use_rel_y:
            if self.rel_pos_y > 0:
                self.rel_pos_y -= 2
            elif self.rel_pos_y < 0:
                self.rel_pos_y += 2

    def draw(self, surf, center=(GC.WINWIDTH/2, GC.WINHEIGHT/2), flicker=False, show_cursor=True):
        try:
            check = center[1]
        except TypeError:
            logger.warning("this is a gameStateObj.activeMenu... It shouldn't be. Aborting draw...")
            return
        for index, option in enumerate(self.options):
            if flicker and self.currentSelection == index: # If the selection should flash white
                BGSurf = GC.IMAGESDICT[self.background + 'Flicker'].copy()
            elif self.currentSelection == index: # Highlight the chosen option
                BGSurf = GC.IMAGESDICT[self.background + 'Highlight'].copy()
            else:
                BGSurf = GC.IMAGESDICT[self.background].copy()
            # Position
            diff = index - self.currentSelection
            if self.use_rel_y:
                top = center[1] + diff*(self.menu_height+1) + self.rel_pos_y
            else:
                top = center[1] + index*(self.menu_height+1) - (len(self.options)-1)*self.menu_height/2 - 4
            # Text
            position = (BGSurf.get_width()/2 - GC.BASICFONT.size(str(option))[0]/2, BGSurf.get_height()/2 - GC.BASICFONT.size(str(option))[1]/2)
            color_transition = Image_Modification.color_transition(GC.COLORDICT['light_blue'], GC.COLORDICT['off_black'])
            OutlineFont(GC.BASICFONT, str(option), BGSurf, GC.COLORDICT['off_white'], color_transition, position)
            # Transparency
            if self.use_transparency:
                BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, abs(diff)*30)
            surf.blit(BGSurf, (center[0] - BGSurf.get_width()/2, top))
         
        if show_cursor:
            center_y = center[1] - 12 + self.cursorAnim[self.cursorCounter]
            if self.use_rel_y:
                height = center_y + self.rel_pos_y
            else:
                height = center_y + self.currentSelection*(self.menu_height+1) - (len(self.options)-1)*self.menu_height/2 - 4
            
            surf.blit(self.cursor1, (center[0] - self.menu_width/2 - self.cursor1.get_width()/2 - 8, height))
            surf.blit(self.cursor2, (center[0] + self.menu_width/2 - self.cursor2.get_width()/2 + 8, height))

class BattleSaveMenu(Counters.CursorControl):
    def __init__(self):
        self.options = [cf.WORDS['Yes'], cf.WORDS['No']]
        self.text = cf.WORDS['Battle Save Header']
        self.font = GC.FONT['text_white']

        self.BGSurf = CreateBaseMenuSurf(self.get_menu_size())
        self.topleft = GC.WINWIDTH/2 - self.BGSurf.get_width()/2, GC.WINHEIGHT/2 - self.BGSurf.get_height()/2

        self.currentSelection = 0

        Counters.CursorControl.__init__(self)

    def get_menu_size(self):
        h_size = self.font.size(self.text)[0]
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
        self.font.blit(self.text, bg_surf, (bg_surf.get_width()/2 - self.font.size(self.text)[0]/2, 4))

        # blit background highlight
        options = '    '.join(self.options)
        option_width = self.font.size(options)[0]
        center = bg_surf.get_width()/2 - option_width/2

        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range(((GC.FONT['text_white'].size(self.options[self.currentSelection]))[0] + 8)/width):
            if self.currentSelection:
                option_left = GC.FONT['text_white'].size('Yes' + '    ')[0] + center
            else:
                option_left = center
            topleft = (slot*width + option_left - 2, 20 + 9)
            bg_surf.blit(highlightSurf, topleft)

        # Blit options
        GC.FONT['text_white'].blit(options, bg_surf, (center, 20))

        # blit menu
        surf.blit(bg_surf, self.topleft)
  
        # blit cursor
        if self.currentSelection:
            option_left = GC.FONT['text_white'].size('Yes' + '    ')[0] + center
        else:
            option_left = center
        surf.blit(self.cursor, (self.topleft[0] - 16 + option_left + self.cursorAnim[self.cursorCounter], self.topleft[1] + 20))
        
# For Pick Unit and Prep Item
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

        self.scroll_bar = GUIObjects.ScrollBar((self.topleft[0] + self.menu_width, self.topleft[1]))
        Counters.CursorControl.__init__(self)
        self.cursor_y_offset = 0

        # Build background
        self.backsurf = CreateBaseMenuSurf(self.menu_size, 'BaseMenuBackgroundOpaque')
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
            self.scroll = Utility.clamp(self.scroll, 0, max(0, len(self.options)/self.units_per_row - self.num_rows + 1))

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

        # Blit background highlight
        if self.highlight:
            highlightSurf = GC.IMAGESDICT['MenuHighlight']
            width = highlightSurf.get_width()
            for slot in range((self.option_length-20)/width): # Gives me the amount of highlight needed
                left = self.topleft[0] + 20 + self.currentSelection%self.units_per_row*self.option_length + slot*width 
                top = self.topleft[1] + (self.currentSelection-self.scroll*self.units_per_row)/self.units_per_row*self.option_height + 12
                surf.blit(highlightSurf, (left, top))
        if self.draw_extra_marker:
            self.draw_extra_highlight(surf)

        s_size = self.units_per_row*self.num_rows
        for index, unit in enumerate(self.options[self.scroll*self.units_per_row:s_size+self.scroll*self.units_per_row]):
            top = index/self.units_per_row
            left = index%self.units_per_row

            # Blit passive sprite
            unit_image = unit.sprite.create_image('passive')
            if self.mode == 'position' and not unit.position:
                unit_image = unit.sprite.create_image('gray')
            elif unit == self.options[self.currentSelection]:
                unit_image = unit.sprite.create_image('active')
            topleft = (self.topleft[0] - 16 - 4 + 16 + left*self.option_length, self.topleft[1] + 2 + (top+1)*self.option_height - unit_image.get_height() + 8)
            surf.blit(unit_image, topleft)

            # Blit name
            font = GC.FONT['text_white']
            if self.mode == 'position' and not unit.position:
                font = GC.FONT['text_grey']
            position = (self.topleft[0] + 20 + 1 + 16 + left*self.option_length, self.topleft[1] + 2 + top*self.option_height)
            font.blit(unit.name, surf, position)

        # Blit cursor
        left = self.topleft[0] + 8 + self.currentSelection%self.units_per_row*self.option_length + self.cursorAnim[self.cursorCounter]
        top = self.topleft[1] + 4 + (self.currentSelection-self.scroll*self.units_per_row)/self.units_per_row*self.option_height + self.cursor_y_offset*8
        self.cursor_y_offset = 0 # Reset
        surf.blit(self.cursor, (left, top))
        if self.draw_extra_marker:
            self.draw_extra_cursor(surf)

        if len(self.options) > self.units_per_row*self.num_rows:
            self.scroll_bar.draw(surf, self.scroll, self.num_rows, len(self.options)/self.units_per_row + 1)

    def set_extra_marker(self, selection):
        self.draw_extra_marker = selection

    def draw_extra_highlight(self, surf):
        # Blit background highlight
        if self.highlight:
            selection = self.draw_extra_marker
            highlightSurf = GC.IMAGESDICT['MenuHighlight']
            width = highlightSurf.get_width()
            for slot in range((self.option_length-20)/width): # Gives me the amount of highlight needed
                left = self.topleft[0] + 20 + selection%self.units_per_row*self.option_length + slot*width 
                top = self.topleft[1] + (selection-self.scroll)/self.units_per_row*self.option_height + 12
                surf.blit(highlightSurf, (left, top))

    def draw_extra_cursor(self, surf):
        # Blit cursor
        selection = self.draw_extra_marker
        left = self.topleft[0] - 8 + selection%self.units_per_row*self.option_length + self.cursorAnim[self.cursorCounter]
        top = self.topleft[1] + 4 + (selection-self.scroll)/self.units_per_row*self.option_height
        surf.blit(self.cursor, (left, top))

def drawUnitItems(surf, topleft, unit, include_top=False, include_bottom=True, include_face=False, right=True, shimmer=0):
    if include_top:
        white_backSurf = GC.IMAGESDICT['PrepTop']
        surf.blit(white_backSurf, (topleft[0] - 6, topleft[1] - white_backSurf.get_height()))
        surf.blit(unit.portrait, (topleft[0] + 3, topleft[1] - 35))
        GC.FONT['text_white'].blit(unit.name, surf, (topleft[0] + 68 - GC.FONT['text_white'].size(unit.name)[0]/2, topleft[1] - 40 + 5))
        # GC.FONT['text_yellow'].blit('<>', surf, (topleft[0] + 37, topleft[1] - 20))
        # GC.FONT['text_yellow'].blit('$', surf, (topleft[0] + 69, topleft[1] - 20))
        GC.FONT['text_blue'].blit(str(unit.level), surf, (topleft[0] + 72 - GC.FONT['text_blue'].size(str(unit.level))[0], topleft[1] - 19))
        GC.FONT['text_blue'].blit(str(unit.exp), surf, (topleft[0] + 97 - GC.FONT['text_blue'].size(str(unit.exp))[0], topleft[1] - 19))

    if include_bottom:
        blue_backSurf = CreateBaseMenuSurf((104, 16*cf.CONSTANTS['max_items']+8), 'BaseMenuBackgroundOpaque')
        if shimmer:
            img = GC.IMAGESDICT['Shimmer' + str(shimmer)]
            blue_backSurf.blit(img, (blue_backSurf.get_width() - img.get_width() - 1, blue_backSurf.get_height() - img.get_height() - 5))
        blue_backSurf = Image_Modification.flickerImageTranslucent(blue_backSurf, 10)
        surf.blit(blue_backSurf, topleft)

        if include_face:
            face_image = unit.bigportrait.copy()
            if right:
                face_image = Engine.flip_horiz(face_image)
            face_image = Image_Modification.flickerImageTranslucentColorKey(face_image, 50)
            left = topleft[0] + blue_backSurf.get_width()/2 - face_image.get_width()/2 + 1
            top = topleft[1] + blue_backSurf.get_height()/2 - face_image.get_height()/2 - 1
            pos = left, top
            surf.blit(face_image, pos)

        for index, item in enumerate(unit.items):
            item.draw(surf, (topleft[0] + 2, topleft[1] + index*16 + 4))
            name_font = GC.FONT['text_grey']
            use_font = GC.FONT['text_grey']
            if unit.canWield(item):
                name_font = GC.FONT['text_white']
                use_font = GC.FONT['text_blue']
            name_font.blit(item.name, surf, (topleft[0] + 4 + 16, topleft[1] + index*16 + 4))
            uses_string = "--"
            if item.uses:
                uses_string = str(item.uses)
            elif item.c_uses:
                uses_string = str(item.c_uses)
            use_font.blit(uses_string, surf, (topleft[0] + 104 - 4 - use_font.size(uses_string)[0], topleft[1] + index*16 + 4))

def drawUnitSupport(surf, unit1, unit2, gameStateObj):
    # Draw face one
    face_image1 = unit1.bigportrait.copy()
    face_image1 = Engine.flip(face_image1)
    pos = 0, 80
    surf.blit(face_image1, pos)

    # Determine status
    status = cf.WORDS['Currently Unpaired']
    if not unit2:
        unit2_name = gameStateObj.support.node_dict[unit1.name].paired_with
        if unit2_name:
            try:
                unit2 = [unit for unit in gameStateObj.allunits if unit.name == unit2_name][0]
                status = cf.WORDS['Currently Paired With'] + ' ' + unit2.name
            except IndexError:
                print("Unit does not seem to exist?")
    else:
        status = cf.WORDS['Pair With'] + ' ' + unit2.name + '?'

    # Draw face two
    if unit2:
        face_image2 = unit2.bigportrait.copy()
        pos = GC.WINWIDTH - 96, 80
        surf.blit(face_image2, pos)

    # Get support nodes
    node1 = gameStateObj.support.node_dict[unit1.name]
    if unit2:
        node2 = gameStateObj.support.node_dict[unit2.name]
    else:
        node2 = None

    # Status surf
    width = 192
    status_menu = CreateBaseMenuSurf((width, 24))
    GC.FONT['text_white'].blit(status, status_menu, (width/2 - GC.FONT['text_white'].size(status)[0]/2, 4))
    node1.affinity.draw(status_menu, (4, 3))
    if node2:
        node2.affinity.draw(status_menu, (width - 20, 3))
    surf.blit(status_menu, (GC.WINWIDTH/2 - width/2, GC.WINHEIGHT/2 - 20))

    # Draw middle menu
    middle_surf = CreateBaseMenuSurf((72, 72))
    GC.FONT['text_yellow'].blit(cf.WORDS['Atk'], middle_surf, (72/2 - GC.FONT['text_yellow'].size('Atk')[0]/2, 4))
    GC.FONT['text_yellow'].blit(cf.WORDS['DEF'], middle_surf, (72/2 - GC.FONT['text_yellow'].size('Def')[0]/2, 20))
    GC.FONT['text_yellow'].blit(cf.WORDS['Hit'], middle_surf, (72/2 - GC.FONT['text_yellow'].size('Hit')[0]/2, 36))
    GC.FONT['text_yellow'].blit(cf.WORDS['Avo'], middle_surf, (72/2 - GC.FONT['text_yellow'].size('Avo')[0]/2, 52))

    # Draw stars for strengths
    unit2_attack = node1.affinity.attack
    unit2_defense = node1.affinity.defense
    unit2_accuracy = node1.affinity.accuracy
    unit2_avoid = node1.affinity.avoid
    if unit2:
        unit1_attack = node2.affinity.attack
        unit1_defense = node2.affinity.defense
        unit1_accuracy = node2.affinity.accuracy
        unit1_avoid = node2.affinity.avoid
    else:
        unit1_attack = 0
        unit1_defense = 0
        unit1_accuracy = 0
        unit1_avoid = 0

    stats = [unit1_attack, unit1_defense, unit1_accuracy, unit1_avoid, unit2_attack, unit2_defense, unit2_accuracy, unit2_avoid]
    positions = [(12, 4), (12, 20), (12, 36), (12, 52), (54, 4), (54, 20), (54, 36), (54, 52)]

    for index, stat in enumerate(stats):
        if stat == 0:
            GC.FONT['text_white'].blit('-', middle_surf, positions[index])
        elif stat == 1:
            middle_surf.blit(GC.ICONDICT['StarIcon'], (positions[index][0] - 4, positions[index][1]))
        elif stat == 2:
            middle_surf.blit(GC.ICONDICT['StarIcon'], positions[index])
            if positions[index][0] == 4:
                middle_surf.blit(GC.ICONDICT['StarIcon'], (positions[index][0] + 8, positions[index][1]))
            else:
                middle_surf.blit(GC.ICONDICT['StarIcon'], (positions[index][0] - 8, positions[index][1]))

    surf.blit(middle_surf, (GC.WINWIDTH/2 - 72/2, 88))

# Serves as controller class for host of menus
class ConvoyMenu(object):
    def __init__(self, owner, options, topleft, disp_value=None):
        self.owner = owner
        self.topleft = topleft
        self.disp_value = disp_value

        self.order = CustomObjects.WEAPON_TRIANGLE.types + ["Consumable"]
        self.wexp_icons = [CustomObjects.WeaponIcon(name, grey=True) for name in self.order]
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
            sorted_dict[w_type] = [option for option in options if w_type in option.TYPE]
        sorted_dict['Consumable'] = [option for option in options if not option.weapon and not option.spell]
        for key, value in sorted_dict.iteritems():
            value.sort(key=lambda item: item.c_uses.uses if item.c_uses else 100)
            value.sort(key=lambda item: item.uses.uses if item.uses else 100)
            value.sort(key=lambda item: item.name)
            value.sort(key=lambda item: item.value*item.uses.total_uses if item.uses else item.value)

        return sorted_dict

    def updateOptions(self, options):
        sorted_dict = self.get_sorted_dict(options)
        for menu_name, menu in self.menus.iteritems():
            menu.updateOptions(sorted_dict[menu_name])

    def buildMenus(self, options):
        sorted_dict = self.get_sorted_dict(options)
        self.menus = {}
        if self.disp_value:
            buy = True if self.disp_value == "Buy" else False
            for w_type in self.order:
                self.menus[w_type] = ShopMenu(self.owner, sorted_dict[w_type], self.topleft, limit=7, hard_limit=True, buy=buy, shimmer=2)
            self.menus["Consumable"] = ShopMenu(self.owner, sorted_dict['Consumable'], self.topleft, limit=7, hard_limit=True, buy=buy, shimmer=2)
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
            self.selection_index = self.order.index(item.TYPE[0])
        else:
            self.selection_index = len(self.order) - 1
        item_index = self.menus[self.order[self.selection_index]].options.index(item)
        self.menus[self.order[self.selection_index]].moveTo(item_index)

    def update(self):
        self.menus[self.order[self.selection_index]].update()

    def draw(self, surf, gameStateObj=None):
        dist = int(120/len(self.order)) - 1
        if self.disp_value:
            dist = int(160/len(self.order)) - 1
            self.menus[self.order[self.selection_index]].draw(surf, gameStateObj.counters['money'])
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
                icon = CustomObjects.WeaponIcon(icon)
                icon.draw(surf, (self.topleft[0] + index*dist + 4, self.topleft[1] - 14))
                surf.blit(GC.IMAGESDICT['Shine_Wexp'], (self.topleft[0] + index*dist + 4, self.topleft[1] - 14))
        self.drawTopArrows(surf)

    def drawTopArrows(self, surf):
        self.left_arrow.draw(surf)
        self.right_arrow.draw(surf)

# Simple shop menu
class ShopMenu(ChoiceMenu):
    def __init__(self, owner, options, topleft, limit=5, hard_limit=True, background='BaseMenuBackground', buy=True, shimmer=0):
        ChoiceMenu.__init__(self, owner, options, topleft, limit=limit, hard_limit=hard_limit, background=background, width=120, shimmer=shimmer, gem=False)
        # Whether we are buying or selling
        if buy:
            self.denominator = 1
        else:
            self.denominator = 2

        self.takes_input = False

        self.lastUpdate = Engine.get_time()

        self.old_scroll = self.scroll
        self.up_arrow = GUIObjects.ScrollArrow('up', (self.topleft[0] + self.menu_width/2 - 7, self.topleft[1] - 4))
        self.down_arrow = GUIObjects.ScrollArrow('down', (self.topleft[0] + self.menu_width/2 - 7, self.topleft[1] + 16*5 + 4), 0.5)

        self.shimmer = shimmer

    def draw(self, surf, money):
        if self.limit:
            BGSurf = CreateBaseMenuSurf((self.menu_width, 16*self.limit+8), 'BaseMenuBackgroundOpaque')
        else:
            BGSurf = CreateBaseMenuSurf((self.menu_width, 16*len(self.options)+8), 'BaseMenuBackgroundOpaque')
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
            if option.uses:
                uses_string = str(option.uses.uses)
                true_value = option.uses.uses * option.value / self.denominator
                value_string = str(true_value)
            elif option.c_uses:
                uses_string = str(option.c_uses)
                true_value = option.value / self.denominator
                value_string = str(option.value / self.denominator)
            elif option.value:
                true_value = option.value / self.denominator
                value_string = str(option.value / self.denominator)

            if option.locked or not option.value or (self.owner and not self.owner.canWield(option)):
                name_font = GC.FONT['text_grey']
                uses_font = GC.FONT['text_grey']
            else:
                name_font = GC.FONT['text_white']
                uses_font = GC.FONT['text_blue']
            if not option.value:
                value_font = GC.FONT['text_grey']
            elif self.denominator == 1:
                if money < true_value:
                    value_font = GC.FONT['text_grey']
                else:
                    value_font = GC.FONT['text_blue']
            elif self.denominator == 2:
                value_font = GC.FONT['text_blue']

            name_font.blit(str(option), surf, (self.topleft[0] + 20, self.topleft[1] + 4 + index*16))

            uses_font.blit(uses_string, surf, (self.topleft[0] + 96, self.topleft[1] + 4 + index*16))
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
    def __init__(self, owner, partner, options1, options2):
        self.owner = owner
        self.partner = partner
        self.options1 = options1
        self.options2 = options2

        self.topleft = (12, 68)
        # Where the cursor hands are at
        self.selection1 = 0 # Main hand
        self.selection2 = None # Secondary Hand

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
        GC.FONT['text_white'].blit(self.owner.name, surf, (24 - GC.FONT['text_white'].size(self.owner.name)[0]/2, 0))
        GC.FONT['text_white'].blit(self.partner.name, surf, (GC.WINWIDTH - 24 - GC.FONT['text_white'].size(self.partner.name)[0]/2, 0))

        # Blit menu background
        BGSurf1 = CreateBaseMenuSurf((self.menuWidth, self.optionHeight*cf.CONSTANTS['max_items']+8))

        BGSurf2 = Engine.copy_surface(BGSurf1)
        second_topleft = (self.topleft[0] + BGSurf1.get_width() + 8, self.topleft[1])

        # Blit portraits
        clipped_surf1 = Engine.subsurface(self.owner.bigportrait, (0, 3, self.owner.bigportrait.get_width(), 68))
        portraitSurf1 = Engine.flip_horiz(clipped_surf1)
        pos = (self.topleft[0] + BGSurf1.get_width()/2 - portraitSurf1.get_width()/2, self.topleft[1] - portraitSurf1.get_height())
        surf.blit(portraitSurf1, pos)
        surf.blit(BGSurf1, self.topleft)

        if hasattr(self.partner, 'bigportrait'):
            clipped_surf2 = Engine.subsurface(self.partner.bigportrait, (0, 3, self.partner.bigportrait.get_width(), 68))
            portraitSurf2 = clipped_surf2
            pos = (second_topleft[0] + BGSurf2.get_width()/2 - portraitSurf2.get_width()/2, second_topleft[1] - portraitSurf2.get_height())
            surf.blit(portraitSurf2, pos)
        surf.blit(BGSurf2, second_topleft)

        # Blit background highlight
        highlightSurf = GC.IMAGESDICT['MenuHighlight']
        width = highlightSurf.get_width()
        for slot in range((self.menuWidth - 16)/width): # Gives me the amount of highlight needed
            topleft = (self.topleft[0] + 8 + slot*width + (self.menuWidth+8)*(self.selection1/cf.CONSTANTS['max_items']), 
                       self.topleft[1] + 11 + (self.selection1%cf.CONSTANTS['max_items'])*16)
            surf.blit(highlightSurf, topleft)

        self.draw_items(surf, self.options1, self.topleft, BGSurf1.get_width(), self.owner)
        self.draw_items(surf, self.options2, second_topleft, BGSurf2.get_width(), self.partner)

        if self.selection2 is not None:
            left = self.topleft[0] - 10 + self.cursorAnim[self.cursorCounter] + (self.menuWidth+8)*(self.selection2/cf.CONSTANTS['max_items'])
            top = self.topleft[1] + 4 + (self.selection2%cf.CONSTANTS['max_items'])*self.optionHeight
            surf.blit(self.cursor, (left, top))

        # Cursor location        
        left = self.topleft[0] - 10 + self.cursorAnim[self.cursorCounter] + (self.menuWidth+8)*(self.selection1/cf.CONSTANTS['max_items'])
        top = self.topleft[1] + 4 + (self.selection1%cf.CONSTANTS['max_items'])*16 + self.cursor_y_offset*8
        self.cursor_y_offset = 0 # reset
        surf.blit(self.cursor, (left, top))

    def draw_items(self, surf, options, topleft, width, owner):
        # Blit second unit's items
        for index, option in enumerate(options):
            option.draw(surf, (topleft[0] + 4, topleft[1] + 4 + index*self.optionHeight))
            if option.locked:
                font = GC.FONT['text_yellow']
                uses_font = GC.FONT['text_blue']
            elif owner.canWield(option):
                font = GC.FONT['text_white']
                uses_font = GC.FONT['text_blue']
            else:
                font = GC.FONT['text_grey']
                uses_font = GC.FONT['text_grey']
            height = self.topleft[1] + 5 + index*self.optionHeight
            right = topleft[0] + width - 4
            font.blit(str(option), surf, (topleft[0] + 20, height))
            if option.uses:
                uses_font.blit(str(option.uses), surf, (right - uses_font.size(str(option.uses))[0], height))
            elif option.c_uses:
                uses_font.blit(str(option.c_uses), surf, (right - uses_font.size(str(option.c_uses))[0], height))
            else:
                uses_font.blit('--', surf, (right - uses_font.size('--')[0], height))

    def setSelection(self):
        self.selection2 = self.selection1

        if self.selection1 < 5:
            self.selection1 = 5
        else:
            self.selection1 = 0

    def drawInfo(self, surf):
        if self.info_flag:
            side_flag = False
            if self.selection1 < cf.CONSTANTS['max_items'] and self.selection1 < len(self.options1):
                option = self.options1[self.selection1]
                idx = self.selection1
            elif self.selection1 > cf.CONSTANTS['max_items']-1 and self.selection1 - cf.CONSTANTS['max_items'] < len(self.options2):
                option = self.options2[self.selection1-cf.CONSTANTS['max_items']]
                idx = self.selection1-cf.CONSTANTS['max_items']
                side_flag = True
            else:
                self.info_flag = False
                return
            if isinstance(option, ItemMethods.ItemObject):
                help_box = option.get_help_box()
                top = self.topleft[1] + 4 + 16*idx - help_box.get_height()
                if side_flag:
                    surf.blit(help_box, (GC.WINWIDTH - 8 - help_box.get_width(), top))
                else:
                    surf.blit(help_box, (self.topleft[0] + 8, top))

    def tradeItems(self):
        # swaps selected item and current item
        # Get items
        item1 = "EmptySlot"
        item2 = "EmptySlot"
        if self.selection1 < cf.CONSTANTS['max_items'] and self.selection1 < len(self.options1):
            item1 = self.options1[self.selection1]
        elif self.selection1 > cf.CONSTANTS['max_items']-1 and self.selection1 - cf.CONSTANTS['max_items'] < len(self.options2):
            item1 = self.options2[self.selection1-cf.CONSTANTS['max_items']]
        if self.selection2 < cf.CONSTANTS['max_items'] and self.selection2 < len(self.options1):
            item2 = self.options1[self.selection2]
        elif self.selection2 > cf.CONSTANTS['max_items']-1 and self.selection2 - cf.CONSTANTS['max_items'] < len(self.options2):
            item2 = self.options2[self.selection2-cf.CONSTANTS['max_items']]

        """
        if cf.OPTIONS['debug']:
            print(self.options1, self.options2)
            print(item1, item2)
        """

        if (item1 is item2) or (item1 is not "EmptySlot" and item1.locked) or (item2 is not "EmptySlot" and item2.locked):
            self.selection2 = None
            return 

        # Now swap items
        if self.selection1 < cf.CONSTANTS['max_items']:
            if self.selection2 < cf.CONSTANTS['max_items']:
                self.swap(self.owner, self.owner, item1, item2)
            else:
                self.swap(self.owner, self.partner, item1, item2)
        else:
            if self.selection2 < cf.CONSTANTS['max_items']:
                self.swap(self.partner, self.owner, item1, item2)
            else:
                self.swap(self.partner, self.partner, item1, item2)

        self.selection2 = None
        self.owner.hasTraded = True
                
    def swap(self, unit1, unit2, item1, item2):
        selection1 = self.selection1%5
        selection2 = self.selection2%5
        if item1 is not "EmptySlot":
            unit1.remove_item(item1)
            unit2.insert_item(selection2, item1)
        if item2 is not "EmptySlot":
            unit2.remove_item(item2)
            unit1.insert_item(selection1, item2)

    def toggle_info(self):
        self.info_flag = not self.info_flag

    def moveDown(self, first_push=True):
        if self.selection1 < cf.CONSTANTS['max_items']-1 or (self.selection1 > cf.CONSTANTS['max_items']-1 and self.selection1 < cf.CONSTANTS['max_items']*2-1):
            self.selection1 += 1
            self.cursor_y_offset = -1
            return True
        return False

    def moveUp(self, first_push=True):
        if (self.selection1 > 0 and self.selection1 < cf.CONSTANTS['max_items']) or self.selection1 > cf.CONSTANTS['max_items']:
            self.selection1 -= 1
            self.cursor_y_offset = 1
            return True
        return False

    def moveLeft(self, first_push=True):
        if self.selection1 > cf.CONSTANTS['max_items']-1:
            self.selection1 -= 5
            return True
        return False

    def moveRight(self, first_push=True):
        if self.selection1 < cf.CONSTANTS['max_items']:
            self.selection1 += 5
            return True
        return False

    def updateOptions(self, options1, options2):
        self.options1 = options1
        self.options2 = options2

def drawTradePreview(surf, gameStateObj, steal=False):
    unit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
    position = unit.position
    items = unit.items
    window = GC.IMAGESDICT['Trade_Window']
    width, height = window.get_width(), window.get_height()
    top_of_window = Engine.subsurface(window, (0, 0, width, 27))
    bottom_of_window = Engine.subsurface(window, (0, height - 5, width, 5))
    middle_of_window = Engine.subsurface(window, (0, height/2 + 3, width, 16))
    size = (width, top_of_window.get_height() + bottom_of_window.get_height() + middle_of_window.get_height() * max(1, len(items)) - 2)
    BGSurf = Engine.create_surface(size, transparent=True)
    BGSurf.blit(top_of_window, (0, 0))

    for index, item in enumerate(items):
        BGSurf.blit(middle_of_window, (0, top_of_window.get_height() + index * middle_of_window.get_height()))
    if not items:
        BGSurf.blit(middle_of_window, (0, top_of_window.get_height()))
    BGSurf.blit(bottom_of_window, (0, BGSurf.get_height() - bottom_of_window.get_height()))
    BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, 10)

    if items:
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
            else:
                uses_width = uses_font.size('--')[0]
                uses_font.blit('--', BGSurf, (right - uses_width, height))
    else:
        GC.FONT['text_grey'].blit(cf.WORDS['Nothing'], BGSurf, (25, top_of_window.get_height() - 2))

    # Blit Character's name and passive Sprite
    unit_surf = unit.sprite.create_image('passive')

    GC.FONT['text_white'].blit(unit.name, BGSurf, (32, 8))

    if position[0] > GC.TILEX/2 + gameStateObj.cameraOffset.get_x() - 1:
        b_topleft = (0, 0)
        u_topleft = (12 - max(0, (unit_surf.get_width() - 16)/2), 8 - max(0, (unit_surf.get_width() - 16)/2))
    else:
        b_topleft = (GC.WINWIDTH - 4 - BGSurf.get_width(), 0)
        u_topleft = (GC.WINWIDTH - BGSurf.get_width() + 4 - max(0, (unit_surf.get_width() - 16)/2), 8 - max(0, (unit_surf.get_width() - 16)/2))

    surf.blit(BGSurf, b_topleft)
    surf.blit(unit_surf, u_topleft)

def drawRescuePreview(surf, gameStateObj):
    rescuer = gameStateObj.cursor.currentSelectedUnit
    rescuee = gameStateObj.cursor.getHoveredUnit(gameStateObj)
    window = GC.IMAGESDICT['RescueWindow'].copy()
    width = window.get_width()
    con = str(rescuee.stats['CON'])
    aid = str(rescuer.getAid())
    num_font = GC.FONT['text_blue']
    num_font.blit(con, window, (width - num_font.size(con)[0] - 3, 72))
    num_font.blit(aid, window, (width - num_font.size(aid)[0] - 3, 24))
    rescuer_surf = rescuer.sprite.create_image('passive')
    rescuee_surf = rescuee.sprite.create_image('passive')
    left = 12 - max(0, (rescuer_surf.get_width() - 16)/2) 
    top = 8 - max(0, (rescuer_surf.get_width() - 16)/2)
    window.blit(rescuer_surf, (left, top))
    window.blit(rescuee_surf, (left, top + 48))
    GC.FONT['text_white'].blit(rescuer.name, window, (32, 8))
    GC.FONT['text_white'].blit(rescuee.name, window, (32, 56))

    if rescuer.position[0] > GC.TILEX/2 + gameStateObj.cameraOffset.get_x() - 1:
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

        self.back_surf = CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
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
            for unit, record in level.stats.iteritems():
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
        for slot in range((self.menu_width - 16)/width): # Gives me the amount of highlight needed
            topleft = (self.topleft[0] + 8 + slot*width, self.topleft[1] + 12 + 1 + index*16)
            surf.blit(highlightSurf, topleft)

    def create_top_banner(self):
        banner_surf = CreateBaseMenuSurf((self.menu_width, 24), 'WhiteMenuBackground75')
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
        surf.blit(self.top_banner, (GC.WINWIDTH/2 - self.top_banner.get_width()/2, 4))

        back_surf = self.back_surf.copy()
        self.draw_highlight(back_surf, self.currentSelection - self.scroll)
        # Draw scroll bar
        if len(self.options) > self.limit:
            self.scroll_bar.draw(back_surf, self.scroll, self.limit, len(self.options))

        # Blit titles
        GC.FONT['text_yellow'].blit(cf.WORDS['Records Header'], back_surf, (4, 4))
        for index, (name, turncount, mvp) in enumerate(self.options[self.scroll:self.scroll+self.limit]):
            GC.FONT['text_white'].blit(name, back_surf, (4, index*16 + 20))
            GC.FONT['text_blue'].blit(str(turncount), back_surf, (self.menu_width/2 - GC.FONT['text_blue'].size(str(turncount))[0] + 8, index*16 + 20))
            GC.FONT['text_white'].blit(mvp, back_surf, (self.menu_width - 28 - GC.FONT['text_white'].size(mvp)[0]/2, index*16 + 20))

        surf.blit(back_surf, (8 + offset_x, 32 + offset_y))

        if not offset_x and not offset_y:
            self.draw_cursor(surf, self.currentSelection-self.scroll)
            self.drawTopArrows(surf)

class UnitStats(RecordsDisplay):
    def __init__(self, name, stats):
        self.name = name
        self.options = [(level_name, record) for (level_name, record) in stats]

        self.set_up()

        self.back_surf = CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def create_top_banner(self):
        banner_surf = GC.IMAGESDICT['PurpleBackground'].copy()
        GC.FONT['chapter_grey'].blit(self.name, banner_surf, (banner_surf.get_width()/2 - GC.FONT['chapter_grey'].size(self.name)[0]/2, 4))
        return banner_surf

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH/2 - self.top_banner.get_width()/2 + offset_x, 4 + offset_y))

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
            for unit, record in level.stats.iteritems():
                if unit in self.mvp_dict:
                    for stat in record:
                        self.mvp_dict[unit][stat] += record[stat]
                else:
                    self.mvp_dict[unit] = {k: v for (k, v) in record.iteritems()}

        # Now convert to list and sort
        self.options = self.mvp_dict.iteritems()
        self.options = sorted(self.options, key=lambda record: CustomObjects.LevelStatistic.formula(record[1]), reverse=True)

        self.set_up()

        self.total_turns = sum([level.turncount for level in stats])
        self.mvp_dict = self.get_game_mvp_dict(stats)

        self.back_surf = CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH/2 - self.top_banner.get_width()/2, 4))
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
        self.options = self.mvp_dict.iteritems()
        self.options = sorted(self.options, key=lambda record: CustomObjects.LevelStatistic.formula(record[1]), reverse=True)

        self.set_up()

        self.back_surf = CreateBaseMenuSurf((self.menu_width, (self.limit+1)*16+8), 'BaseMenuBackgroundOpaque')
        img = GC.IMAGESDICT['Shimmer2']
        self.back_surf.blit(img, (self.back_surf.get_width() - 1 - img.get_width(), self.back_surf.get_height() - 5 - img.get_height()))
        self.back_surf = Image_Modification.flickerImageTranslucent(self.back_surf, 10)

        self.top_banner = self.create_top_banner()

    def create_top_banner(self):
        banner_surf = GC.IMAGESDICT['PurpleBackground'].copy()
        GC.FONT['chapter_grey'].blit(self.name, banner_surf, (banner_surf.get_width()/2 - GC.FONT['chapter_grey'].size(self.name)[0]/2, 4))
        return banner_surf

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.top_banner, (GC.WINWIDTH/2 - self.top_banner.get_width()/2 + offset_x, 4 + offset_y))
        self.draw_rest(surf, offset_x, offset_y)
