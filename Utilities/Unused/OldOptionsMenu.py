import Engine
# Complex menu
class OptionsMenu(SimpleMenu):
    def __init__(self, owner, options, background='BaseMenuBackground', child=False, limit=None, center=False, horizontal=False):
        self.owner = owner
        self.options = options
        self.background = background
        self.limit = limit
        self.currentSelection = 0 # Where the cursor is at, at the menu
        self.cursor = IMAGESDICT['menuHand']

        self.menu_width = self.getMenuWidth()
        
        self.cursorCounter = 0 # Helper counter for cursor animation
        self.cursorAnim = [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
        self.lastUpdate = Engine.get_time()

        self.child = child
        self.center = center
        self.horizontal = horizontal # Must use simple draw if using horizontal!

    def draw(self, surf, gameStateObj):
        if self.background:
            if self.limit:
                BGSurf = CreateBaseMenuSurf((self.menu_width, 16*limit+8), self.background)
            else:
                BGSurf = CreateBaseMenuSurf((self.menu_width, 16*len(self.options)+8), self.background)
        else:
            if self.limit:
                BGSurf = pygame.Surface((self.menu_width, 16*limit+8), pygame.SRCALPHA, 32).convert_alpha()
            else:
                BGSurf = pygame.Surface((self.menu_width, 16*len(self.options)+8), pygame.SRCALPHA, 32).convert_alpha()
        BGRect = BGSurf.get_rect()
        ### Placement ########## NEEDS FIXING
        if not self.child:
            if self.center:
                BGRect.center = (WINWIDTH/2, WINHEIGHT/2)
            else:
                if gameStateObj.cursor.position[0] > WINWIDTH/TILEWIDTH/2 + gameStateObj.cameraOffset.get_x():
                    BGRect.topleft = (12, 12)
                else:
                    BGRect.topright = (WINWIDTH - 12, 12)
        else:
            if self.center:
                BGRect.center = (WINWIDTH/2, WINHEIGHT/2)
            else:
                if gameStateObj.cursor.position[0] > WINWIDTH/TILEWIDTH/2 + gameStateObj.cameraOffset.get_x():
                    BGRect.topleft = (12+self.menu_width, 12+16*gameStateObj.activeMenu.currentSelection)
                else:
                    BGRect.topright = (WINWIDTH - 12 - self.menu_width, 12+16*gameStateObj.activeMenu.currentSelection)
              
        # Blit background
        surf.blit(BGSurf, BGRect)

        if self.limit:
            top_of_menu = max(0, min(max(0, self.currentSelection - (self.limit - 1)), len(self.options) - self.limit))
            bottom_of_menu = min(len(self.options), top_of_menu + self.limit)
        else:
            top_of_menu = 0
            bottom_of_menu = len(self.options)

        # Blit background highlight
        highlightSurf = IMAGESDICT['MenuHighlight']
        highlightRect = highlightSurf.get_rect()
        for slot in range((self.menu_width - 16)/highlightRect.width): # Gives me the amount of highlight needed
            highlightRect.topleft = (BGRect.left + 8 + slot*highlightRect.width, BGRect.top + 14 + self.currentSelection*16)
            surf.blit(highlightSurf, highlightRect)
        # Blit options
        for index, option in enumerate(self.options[top_of_menu:bottom_of_menu]):
            if isinstance(option, ItemMethods.ItemObject): # If it is an item
                option.draw(surf, (BGRect.left + 4, BGRect.top + 4 + index*16))
                if self.owner.canWield(option):
                    OptionSurf = BASICFONT.render(str(option), True, colorDict['white'])
                    if option.uses:
                        UsesSurf = BASICFONT.render(str(option.uses), True, colorDict['white'])
                    else:
                        UsesSurf = BASICFONT.render('--', True, colorDict['white'])
                else:
                    OptionSurf = BASICFONT.render(str(option), True, colorDict['light_gray'])
                    if option.uses:
                        UsesSurf = BASICFONT.render(str(option.uses), True, colorDict['light_gray'])
                    else:
                        UsesSurf = BASICFONT.render('--', True, colorDict['light_gray'])
                OptionRect = OptionSurf.get_rect()
                OptionRect.topleft = (BGRect.left + 4 + 16, BGRect.top + 8 + index*16) # 4 is to make display look nicer
                surf.blit(OptionSurf, OptionRect)
                UsesRect = UsesSurf.get_rect()
                UsesRect.topright = (BGRect.right - 4, BGRect.top + 8 + index*16)
                surf.blit(UsesSurf, UsesRect)
            else:
                color = colorDict['white']
                if str(option) == 'Discard':
                    color = Image_Modification.color_transition(colorDict['green'], colorDict['green_white'])
                OptionSurf = BASICFONT.render(str(option), True, color)
                OptionRect = OptionSurf.get_rect()
                OptionRect.topleft = (BGRect.left + 8, BGRect.top + 8 + index*16)
                surf.blit(OptionSurf, OptionRect)
                
        # Blit Menu Cursor
        # If I am not a child and the child menu does not exist
        if not (gameStateObj.childMenu and not self.child):
            cursorRect = self.cursor.get_rect()
            cursorRect.topleft = (BGRect.left - 8 + self.cursorAnim[self.cursorCounter], BGRect.top + 8 + self.currentSelection*16)
            surf.blit(self.cursor, cursorRect)

    def simpleDraw(self, surf, topleft):
        if self.horizontal:
            self.simpleDrawHorizontal(surf, topleft)
        else:
            self.simpleDrawVertical(surf, topleft)

    def simpleDrawVertical(self, surf, topleft):
        # Determine Size of Menu Background
        if self.background:
            if self.limit:
                BGSurf = CreateBaseMenuSurf((self.menu_width, 16*limit+8), self.background)
            else:
                BGSurf = CreateBaseMenuSurf((self.menu_width, 16*len(self.options)+8), self.background)
        else:
            if self.limit:
                BGSurf = pygame.Surface((self.menu_width, 16*limit+8), pygame.SRCALPHA, 32).convert_alpha()
            else:
                BGSurf = pygame.Surface((self.menu_width, 16*len(self.options)+8), pygame.SRCALPHA, 32).convert_alpha()
        # Blit Background
        BGRect = BGSurf.get_rect()
        BGRect.topleft = topleft     
        surf.blit(BGSurf, BGRect)

        if self.limit:
            top_of_menu = min(max(0, self.currentSelection - (self.limit - 1)), len(self.options) - self.limit)
            bottom_of_menu = min(len(self.options), top_of_menu + self.limit)
        else:
            top_of_menu = 0
            bottom_of_menu = len(self.options)

        # Blit background highlight
        highlightSurf = IMAGESDICT['MenuHighlight']
        highlightRect = highlightSurf.get_rect()
        for slot in range((self.menu_width - 16)/highlightRect.width): # Gives me the amount of highlight needed
            highlightRect.topleft = (BGRect.left + 8 + slot*highlightRect.width, BGRect.top + 11 + self.currentSelection*16)
            surf.blit(highlightSurf, highlightRect)

        # Blit options
        for index, option in enumerate(self.options[top_of_menu:bottom_of_menu]):
            if isinstance(option, ItemMethods.ItemObject): # If it is an item
                option.draw(surf, (BGRect.left + 4, BGRect.top + 4 + index*16))
                if self.owner.canWield(option):
                    OptionSurf = BASICFONT.render(str(option), True, colorDict['white'])
                    if option.uses:
                        UsesSurf = BASICFONT.render(str(option.uses), True, colorDict['white'])
                    else:
                        UsesSurf = BASICFONT.render('--', True, colorDict['white'])
                else:
                    OptionSurf = BASICFONT.render(str(option), True, colorDict['light_gray'])
                    if option.uses:
                        UsesSurf = BASICFONT.render(str(option.uses), True, colorDict['light_gray'])
                    else:
                        UsesSurf = BASICFONT.render('--', True, colorDict['light_gray'])
                OptionRect = OptionSurf.get_rect()
                OptionRect.topleft = (BGRect.left + 4 + 16, BGRect.top + 8 + index*16)
                surf.blit(OptionSurf, OptionRect)
                UsesRect = UsesSurf.get_rect()
                UsesRect.topright = (BGRect.right - 4, BGRect.top + 8 + index*16)
                surf.blit(UsesSurf, UsesRect)
                         
            else:
                OptionSurf = BASICFONT.render(str(option), True, colorDict['white'])
                OptionRect = OptionSurf.get_rect()
                OptionRect.topleft = (BGRect.left + 8 - BGRect.left%8, BGRect.top + 8 + index*16)
                surf.blit(OptionSurf, OptionRect)
  
        cursorRect = self.cursor.get_rect()
        cursorRect.topleft = (BGRect.left - 8 + self.cursorAnim[self.cursorCounter], BGRect.top + 8 + self.currentSelection*16)
        surf.blit(self.cursor, cursorRect)

    # DOES NOT SUPPORT ITEMS!
    def simpleDrawHorizontal(self, surf, topleft):
        # Determine Size of Menu Background
        if self.background:
            menu_size = BASICFONT.size('  '.join(self.options))
            BGSurf = CreateBaseMenuSurf((menu_size[0] + 20, menu_size[1] + 16), self.background)
        else:
            menu_size = BASICFONT.size('  '.join(self.options))
            BGSurf = pygame.Surface((menu_size[0] + 20, menu_size[1] + 16), pygame.SRCALPHA, 32).convert_alpha()
        # Blit Background
        BGRect = BGSurf.get_rect()
        BGRect.topleft = topleft     
        surf.blit(BGSurf, BGRect)

        # Blit background highlight
        highlightSurf = IMAGESDICT['MenuHighlight']
        highlightRect = highlightSurf.get_rect()
        for slot in range( (BASICFONT.size( self.options[self.currentSelection] ) )[0] / highlightRect.width ):
            option_left = BASICFONT.size('  '.join(self.options[:self.currentSelection]) + ' ')[0] # determines width of all previous options
            highlightRect.topleft = (BGRect.left + 8 + slot*highlightRect.width + option_left, BGRect.top + 11)
            surf.blit(highlightSurf, highlightRect)

        # Blit options
        OutlineFont(BASICFONT, '  '.join(self.options), surf, colorDict['white'], colorDict['black'], (BGRect.left + 6, BGRect.center[1] - BASICFONT.get_linesize()/2))
  
        cursorRect = self.cursor.get_rect()

        option_left = BASICFONT.size('  '.join(self.options[:self.currentSelection]) + ' ')[0] # determines width of all previous options
        cursorRect.topleft = (BGRect.left - 16 + option_left + self.cursorAnim[self.cursorCounter], BGRect.top + 4)
        surf.blit(self.cursor, cursorRect)