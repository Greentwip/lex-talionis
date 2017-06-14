# Transitions
# Game Over, Starting, Intro, Outro screens
import os, time

# Custom imports
from imagesDict import getImages
from GlobalConstants import *
from configuration import *
import CustomObjects, MenuFunctions, SaveLoad, StateMachine, Dialogue, Engine, Image_Modification, Weather

def create_title(text, background='DarkMenu'):
    title_surf = IMAGESDICT[background].copy()
    title_pos = WINWIDTH/2 - title_surf.get_width()/2, 21 - title_surf.get_height()/2
    center_pos = title_surf.get_width()/2 - BASICFONT.size(text)[0]/2, title_surf.get_height()/2 - BASICFONT.size(text)[1]/2
    MenuFunctions.OutlineFont(BASICFONT, text, title_surf, colorDict['off_white'], colorDict['off_black'], center_pos)
    return title_surf, title_pos

class Button(object):
    def __init__(self, height, pos, key):
        self.image = Engine.subsurface(IMAGESDICT['Buttons'], (0, height*16, 16, 16))
        self.pos = pos
        self.key = key

    def draw(self, surf):
        surf.blit(self.image, self.pos)
        FONT['text_blue'].blit(Engine.get_key_name(OPTIONS[self.key]), surf, (self.pos[0] + 18, self.pos[1]))

class TimeDisplay(object):
    def __init__(self):
        self.image = MenuFunctions.CreateBaseMenuSurf((128, 24), 'NoirMessageWindow')
        self.pos = [-128, WINHEIGHT-24]
        self.state = 'right'

    def draw(self, surf, real_time):
        if self.state == 'right':
            self.pos[0] += 12
            if self.pos[0] >= 0:
                self.pos[0] = 0
                self.state = 'normal'
        elif self.state == 'left':
            self.pos[0] -= 12
            if self.pos[0] <= -128:
                self.pos[0] = -128
                self.state = 'dead'
        if not self.state == 'dead':
            surf.blit(self.image, self.pos)
            str_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(real_time))
            FONT['text_white'].blit(str_time, surf, (self.pos[0] + 4, self.pos[1] + 4))

class Logo(object):
    def __init__(self, image, height, center):
        self.texture = image
        self.image = None
        self.height = height
        self.width = self.texture.get_width()
        self.center = center
        self.logo_counter = 0
        self.logo_anim = [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1]
        self.last_update = 0
        self.image = Engine.subsurface(self.texture, (0, self.logo_anim[self.logo_counter]*self.height, self.texture.get_width(), self.height))

    def update(self):
        currentTime = Engine.get_time()
        if currentTime - self.last_update > 60:
            self.logo_counter += 1
            if self.logo_counter >= len(self.logo_anim):
                self.logo_counter = 0
            self.image = Engine.subsurface(self.texture, (0, self.logo_anim[self.logo_counter]*self.height, self.texture.get_width(), self.height))
            self.last_update = currentTime

    def draw(self, surf):
        surf.blit(self.image, (self.center[0] - self.width/2, self.center[1] - self.height/2))

def load_saves():
    save_slots = []
    for num in range(0, int(CONSTANTS['save_slots'])):
        meta_fp = 'Saves/SaveState' + str(num) + '.pmeta'
        ss = CustomObjects.SaveSlot(meta_fp, num)
        save_slots.append(ss)
    return save_slots

def load_restarts():
    save_slots = []
    for num in range(0, int(CONSTANTS['save_slots'])):
        meta_fp = 'Saves/Restart' + str(num) + '.pmeta'
        ss = CustomObjects.SaveSlot(meta_fp, num)
        save_slots.append(ss)
    return save_slots

def remove_suspend():
    if not OPTIONS['debug'] and os.path.exists(SUSPEND_LOC):
        os.remove(SUSPEND_LOC)

class StartStart(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            gameStateObj.button_a = Button(4, (WINWIDTH - 64, WINHEIGHT - 16), 'key_SELECT')
            gameStateObj.button_b = Button(5, (WINWIDTH - 32, WINHEIGHT - 16), 'key_BACK')
            gameStateObj.logo = IMAGESDICT['Logo']
            gameStateObj.press_start = Logo(IMAGESDICT['PressStart'], 16, (WINWIDTH/2, 4*WINHEIGHT/5))
            gameStateObj.fog_bg = MenuFunctions.MovieBackground('fog', 33)
            bounds = (-WINHEIGHT, WINWIDTH, WINHEIGHT, WINHEIGHT+16)
            gameStateObj.fog_particles = Weather.Weather('Smoke', .075, bounds, (TILEX, TILEY))
            # Wait until saving thread has finished
            if hasattr(gameStateObj, 'saving_thread'):
                gameStateObj.saving_thread.join()
            #if not hasattr(gameStateObj, 'save_slots') or not gameStateObj.save_slots:
            gameStateObj.save_slots = load_saves()
            gameStateObj.restart_slots = load_restarts()
            # Start music
            Engine.music_thread.fade_in(MUSICDICT[CONSTANTS['music_main']])

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'AUX' and OPTIONS['debug']:
            SOUNDDICT['Start'].play()
            #selection = gameStateObj.save_slots[0]
            gameStateObj.build_new() # Make the gameStateObj ready for a new game
            gameStateObj.save_slot = 'DEBUG'
            gameStateObj.counters['level'] = 'DEBUG'
            levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
            # Load the first level
            SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
            # Hardset the name of the first level
            #gameStateObj.saveSlot = selection
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('turn_change')
            gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
            return 'repeat'
        # Load most recent save
        elif event == 'INFO' and OPTIONS['debug']:
            SOUNDDICT['Select 1'].play()
            import glob
            fps = glob.glob('Saves/*.pmeta')
            if not fps:
                return
            newest = max(fps, key=os.path.getmtime)
            print(newest)
            selection = CustomObjects.SaveSlot(newest, 3)
            # gameStateObj.activeMenu = None # Remove menu
            logger.debug('Loading game...')
            SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
            if selection.kind == 'Start': # Restart
                levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
                # Load the first level
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
            gameStateObj.transition_from = WORDS['Load Game']
            gameStateObj.stateMachine.changeState('start_wait')
            gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
            remove_suspend()
            return 'repeat'
        elif event:
            SOUNDDICT['Start'].play()
            gameStateObj.stateMachine.changeState('start_option')
            gameStateObj.stateMachine.changeState('transition_out')
            return

    def update(self, gameStateObj, metaDataObj):
        #gameStateObj.logo.update()
        gameStateObj.press_start.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        #gameStateObj.logo.draw(surf)
        surf.blit(gameStateObj.logo, (WINWIDTH/2 - gameStateObj.logo.get_width()/2, WINHEIGHT/2 - gameStateObj.logo.get_height()/2 - 20))
        gameStateObj.press_start.draw(surf)
        #pos = (WINWIDTH/2 - FONT['text_white'].size(CONSTANTS['attribution'])[0]/2, WINHEIGHT - 16)
        #FONT['text_white'].blit(CONSTANTS['attribution'], surf, pos)
        FONT['text_white'].blit(CONSTANTS['attribution'], surf, (4, WINHEIGHT - 16))
        return surf

class StartOption(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.banner = None
            self.position_x = -WINWIDTH/2

            self.background = IMAGESDICT['BlackBackground']
            self.transition = 100

            options = [WORDS['New Game'], WORDS['Extras']]
            # If there are any games to load...
            if any(ss.kind for ss in gameStateObj.save_slots):
                options.insert(0, WORDS['Restart Level'])
                options.insert(0, WORDS['Load Game'])
            if os.path.exists(SUSPEND_LOC):
                options.insert(0, WORDS['Continue'])
            self.menu = MenuFunctions.MainMenu(options, 'DarkMenu')
            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        if self.state == "normal":
            event = gameStateObj.input_manager.process_input(eventList)
                            
            if event == 'DOWN':
                SOUNDDICT['Select 6'].play()
                self.menu.moveDown()
            elif event == 'UP':
                SOUNDDICT['Select 6'].play()
                self.menu.moveUp()

            elif event == 'BACK':
                SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.changeState('start_start')
                gameStateObj.stateMachine.changeState('transition_out')

            elif event == 'SELECT':
                SOUNDDICT['Select 1'].play()
                self.selection = self.menu.getSelection()
                if self.selection == WORDS['Continue']:
                    self.state = 'wait'
                elif os.path.exists(SUSPEND_LOC) and not self.banner and self.selection in [WORDS['Load Game'], WORDS['Restart Level'], WORDS['New Game']]:
                    SOUNDDICT['Select 2'].play()
                    if self.selection == WORDS['New Game']:
                        text = 'Starting a new game will remove suspend!'
                        width = 200
                        position = (6, 6)
                    else:
                        text = 'Loading a game will remove suspend!'
                        width = 180
                        position = (4, 6)
                    self.banner = MenuFunctions.CreateBaseMenuSurf((width, 24), 'DarkMenuBackground')
                    self.banner = Image_Modification.flickerImageTranslucent(self.banner, 10)
                    MenuFunctions.OutlineFont(BASICFONT, text, self.banner, colorDict['off_white'], colorDict['off_black'], position)
                elif self.selection == WORDS['New Game']:
                    self.banner = None
                    gameStateObj.stateMachine.changeState('start_mode')
                    gameStateObj.stateMachine.changeState('transition_out')
                else:
                    self.banner = None
                    self.state = "transition_out"
                #elif self.selection == WORDS['New Game']:
                #    self.state = "wait"

                    #gameStateObj.stateMachine.changeState('start_wait')
                    #gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
                    #return 'repeat'
            
    def update(self, gameStateObj, metaDataObj):
        #gameStateObj.logo.update()
        if self.menu:
            self.menu.update()

        # Transition out
        if self.state == 'transition_in':
            self.position_x += 20
            if self.position_x >= WINWIDTH/2:
                self.position_x = WINWIDTH/2
                self.state = "normal"

        elif self.state == 'transition_out':
            self.position_x -= 20
            if self.position_x <= -WINWIDTH/2:
                self.position_x = -WINWIDTH/2
                if self.selection == WORDS['Load Game']:
                    gameStateObj.stateMachine.changeState('start_load')
                elif self.selection == WORDS['Restart Level']:
                    gameStateObj.stateMachine.changeState('start_restart')
                elif self.selection == WORDS['Extras']:
                    gameStateObj.stateMachine.changeState('start_extras')
                elif self.selection == WORDS['New Game']:
                    #gameStateObj.stateMachine.changeState('start_new')
                    gameStateObj.stateMachine.changeState('start_mode')
                    gameStateObj.stateMachine.changeState('transition_out')
                self.state = 'transition_in'
                return 'repeat'

        elif self.state == 'wait':
            self.transition -= 5
            if self.transition <= 0:
                self.continue_suspend(gameStateObj, metaDataObj)
                return 'repeat'

    def continue_suspend(self, gameStateObj, metaDataObj):
        # gameStateObj.activeMenu = None # Remove menu
        suspend = CustomObjects.SaveSlot(SUSPEND_LOC, 'suspend')
        logger.debug('Loading game...')
        SaveLoad.loadGame(gameStateObj, metaDataObj, suspend)
        #gameStateObj.stateMachine.changeState('start_wait')
        #gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)

    def load_most_recent_game(self, gameStateObj, metaDataObj):
        selection = max(gameStateObj.save_slots, key=lambda x:x.realtime)
        SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
        if selection.kind == 'Start': # Restart
            levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
            # Load the level
            SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
        #gameStateObj.stateMachine.changeState('start_wait')
        #gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
        #gameStateObj.stateMachine.changeState('transition_out')

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        #gameStateObj.logo.draw(surf)
        #FONT['text_white'].blit(CONSTANTS['attribution'], surf, (4, WINHEIGHT - 16))
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        if self.menu:
            self.menu.draw(surf, center=(self.position_x, WINHEIGHT/2), show_cursor= (self.state == "normal"))
        if self.banner and self.state == 'normal':
            surf.blit(self.banner, (WINWIDTH/2 - self.banner.get_width()/2, WINHEIGHT/2 - self.banner.get_height()/2))

        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition)
        surf.blit(bb, (0, 0))

        return surf

class StartLoad(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*WINWIDTH/2
            self.title_surf, self.title_pos = create_title(WORDS['Load Game'])
            self.rel_title_pos_y = -40
            options = [save_slot.get_name() for save_slot in gameStateObj.save_slots] # SaveSlots
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(max(gameStateObj.save_slots, key=lambda x:x.realtime))
            #self.time_display = TimeDisplay()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            #self.time_display.state = 'left'

        elif event == 'SELECT':
            selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                SOUNDDICT['Select 1'].play()

                # gameStateObj.activeMenu = None # Remove menu
                logger.debug('Loading game...')
                SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
                if selection.kind == 'Start': # Restart
                    levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
                    # Load the first level
                    SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                gameStateObj.transition_from = WORDS['Load Game']
                gameStateObj.stateMachine.changeState('start_wait')
                gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
                remove_suspend()
            else:
                SOUNDDICT['Select 4'].play()

    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= WINWIDTH/2:
                self.position_x = WINWIDTH/2
                self.state = "normal"
            if self.rel_title_pos_y < 0:
                self.rel_title_pos_y += 4 

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.rel_title_pos_y > -40:
                self.rel_title_pos_y -= 4
            if self.position_x >= 3*WINWIDTH/2:
                self.position_x = 3*WINWIDTH/2
                gameStateObj.stateMachine.back()
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.draw(surf, center=[self.position_x, WINHEIGHT/2])
        surf.blit(self.title_surf, (self.title_pos[0], self.title_pos[1] + self.rel_title_pos_y))
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        #selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
        #self.time_display.draw(surf, selection.realtime)

        return surf

class StartRestart(StartLoad):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*WINWIDTH/2
            self.title_surf, self.title_pos = create_title(WORDS['Restart Level'])
            self.rel_title_pos_y = -40
            options = [save_slot.get_name() for save_slot in gameStateObj.save_slots]
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(max(gameStateObj.save_slots, key=lambda x:x.realtime))
            #self.time_display = TimeDisplay()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            #self.time_display.state = 'left'

        elif event == 'SELECT':
            selection = gameStateObj.restart_slots[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                SOUNDDICT['Select 1'].play()

                # gameStateObj.activeMenu = None # Remove menu
                logger.debug('Restarting Level...')
                SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
                # Always Restart
                levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                gameStateObj.transition_from = WORDS['Restart Level']
                gameStateObj.stateMachine.changeState('start_wait')
                gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
                remove_suspend()
            else:
                SOUNDDICT['Select 4'].play()

class StartMode(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.state = 0
        else:
            self.state += 1

        if self.state == 0:
            self.title_surf, self.title_pos = create_title(WORDS['Select Difficulty'])
            options = ['Easy', 'Normal', 'Hard']
            toggle = [False, True, False]
            self.menu = MenuFunctions.ModeSelectMenu(options, toggle, default=1)
            self.mode_name = 'difficulty'
            gameStateObj.stateMachine.changeState('transition_in')
            return 'repeat'

        elif self.state == 2:
            self.title_surf, self.title_pos = create_title(WORDS['Select Mode'])
            options = ['Casual', 'Classic']
            toggle = [True, True]
            self.menu = MenuFunctions.ModeSelectMenu(options, toggle, default=1)
            self.mode_name = 'death'
            gameStateObj.stateMachine.changeState('transition_in')
            return 'repeat'

        elif self.state == 4:
            self.title_surf, self.title_pos = create_title(WORDS['Select Growths'])
            options = ['Random', 'Fixed', 'Hybrid']
            toggle = [True, True, True]
            self.menu = MenuFunctions.ModeSelectMenu(options, toggle, default=1)
            self.mode_name = 'growths'
            gameStateObj.stateMachine.changeState('transition_in')
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)    
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            self.menu.moveUp()

        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            self.state -= 4
            if self.state < -1:
                #gameStateObj.stateMachine.changeState('start_option')
                gameStateObj.stateMachine.changeState('transition_pop')
            else:
                gameStateObj.stateMachine.changeState('transition_clean')
            return 'repeat'

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            gameStateObj.mode[self.mode_name] = self.menu.getSelectionIndex()
            if self.state > 4:
                gameStateObj.stateMachine.changeState('start_new')
                gameStateObj.stateMachine.changeState('transition_out')
            else:
                gameStateObj.stateMachine.changeState('transition_clean')
            return 'repeat'

    def update(self, gameStateObj, metaDataObj):
        self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        self.menu.draw(surf)
        surf.blit(self.title_surf, self.title_pos)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)

        return surf

class StartNew(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*WINWIDTH/2
            self.title_surf, self.title_pos = create_title(WORDS['New Game'])
            self.rel_title_pos_y = -40
            options = [save_slot.get_name() for save_slot in gameStateObj.save_slots] # SaveSlots
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options)
            # Default to oldest
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(min(gameStateObj.save_slots, key=lambda x:x.realtime))
            #self.time_display = TimeDisplay()
        #self.time_display.state = 'right'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)    
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            #self.time_display.state = 'left'

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                options = [WORDS['Overwrite'], WORDS['Back']]
                gameStateObj.childMenu = MenuFunctions.ChoiceMenu(selection, options, (TILEWIDTH/2, WINHEIGHT - TILEHEIGHT * 1.5), horizontal=True)
                gameStateObj.stateMachine.changeState('start_newchild')
                #self.time_display.state = 'left'
            else:
                self.build_new_game(gameStateObj, metaDataObj)
    
    def build_new_game(self, gameStateObj, metaDataObj):
        gameStateObj.build_new() # Make the gameStateObj ready for a new game
        gameStateObj.save_slot = gameStateObj.activeMenu.getSelectionIndex()
        levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
        # Create a save for the first game
        gameStateObj.stateMachine.clear()
        gameStateObj.stateMachine.changeState('turn_change')
        SaveLoad.suspendGame(gameStateObj, "Start", slot=gameStateObj.save_slot)
        # Load the first level
        SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
        # Hardset the name of the first level
        gameStateObj.activeMenu.options[gameStateObj.save_slot] = metaDataObj['name']
        gameStateObj.stateMachine.clear()
        gameStateObj.stateMachine.changeState('turn_change')
        #gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
        gameStateObj.transition_from = WORDS['New Game']
        gameStateObj.stateMachine.changeState('start_wait')
        remove_suspend()

    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        if gameStateObj.childMenu:
            gameStateObj.childMenu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= WINWIDTH/2:
                self.position_x = WINWIDTH/2
                self.state = "normal"
            if self.rel_title_pos_y < 0:
                self.rel_title_pos_y += 4 

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.rel_title_pos_y > -40:
                self.rel_title_pos_y -= 4
            if self.position_x >= 3*WINWIDTH/2:
                self.position_x = 3*WINWIDTH/2
                # gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('start_option')
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.draw(surf, center=[self.position_x, WINHEIGHT/2])
        selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
        #self.time_display.draw(surf, selection.realtime)
        if gameStateObj.childMenu:
            gameStateObj.childMenu.draw(surf)
        surf.blit(self.title_surf, (self.title_pos[0], self.title_pos[1] + self.rel_title_pos_y))
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)

        return surf

class StartNewChild(StartNew):
    def begin(self, gameStateObj, metaDataObj):
        self.title_surf, self.title_pos = create_title(WORDS['New Game'])

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'RIGHT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown()
        elif event == 'LEFT':
            SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp()

        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            gameStateObj.childMenu = None # Remove menu
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            selection = gameStateObj.childMenu.getSelection()
            if selection == 'Overwrite':
                SOUNDDICT['Select 1'].play()
                self.build_new_game(gameStateObj, metaDataObj)
            elif selection == 'Back':
                SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.state[-2].update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        return gameStateObj.stateMachine.state[-2].draw(gameStateObj, metaDataObj)

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.childMenu = None

class StartExtras(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        # For transition
        self.selection = None
        self.state = "transition_in"
        self.position_x = 3*WINWIDTH/2

        options = [WORDS['Options'], WORDS['Credits']]
        gameStateObj.activeMenu = MenuFunctions.MainMenu(options, 'DarkMenu')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            SOUNDDICT['Select 4'].play()
            #gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'

        elif event == 'SELECT':
            SOUNDDICT['Select 1'].play()
            selection = gameStateObj.activeMenu.getSelection()
            if selection == WORDS['Credits']:
                gameStateObj.stateMachine.changeState('credits')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == WORDS['Options']:
                gameStateObj.stateMachine.changeState('config_menu')
                gameStateObj.stateMachine.changeState('transition_out')

    def update(self, gameStateObj, metaDataObj):
        #gameStateObj.logo.update()
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= WINWIDTH/2:
                self.position_x = WINWIDTH/2
                self.state = "normal"

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.position_x >= 3*WINWIDTH/2:
                self.position_x = 3*WINWIDTH/2
                gameStateObj.stateMachine.back()
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        #FONT['text_white'].blit(CONSTANTS['attribution'], surf, (4, WINHEIGHT - 16))
        #gameStateObj.logo.draw(surf)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.draw(surf, center=(self.position_x, WINHEIGHT/2))
        return surf

class StartWait(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.wait_flag = False
        self.wait_time = Engine.get_time()
        self.title_surf, self.title_pos = create_title(gameStateObj.transition_from)
        
    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        if not self.wait_flag and hasattr(self, 'wait_time') and Engine.get_time() - self.wait_time > 750:
            #gameStateObj.stateMachine.back()
            self.wait_flag = True
            gameStateObj.stateMachine.changeState('transition_pop')

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        if gameStateObj.activeMenu:
            currentTime = Engine.get_time()
            if hasattr(self, 'wait_time') and currentTime - self.wait_time > 100 and currentTime - self.wait_time < 200:
                gameStateObj.activeMenu.draw(surf, flicker=True)
            else:
                gameStateObj.activeMenu.draw(surf)
        surf.blit(self.title_surf, self.title_pos)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        gameStateObj.fog_bg = None
        gameStateObj.fog_particles = None

class StartSave(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        #self.selection = None
        if self.started:
            self.leave_flag = False
    
        if not self.started:
            gameStateObj.button_a = Button(4, (WINWIDTH - 64, WINHEIGHT - 16), 'key_SELECT')
            gameStateObj.button_b = Button(5, (WINWIDTH - 32, WINHEIGHT - 16), 'key_BACK')
            gameStateObj.fog_bg = MenuFunctions.MovieBackground('fog', 33)
            bounds = (-WINHEIGHT, WINWIDTH, WINHEIGHT, WINHEIGHT+16)
            gameStateObj.fog_particles = Weather.Weather('Smoke', .075, bounds, (TILEX, TILEY))
            #self.time_display = TimeDisplay()
            #if not hasattr(gameStateObj, 'save_slots') or not gameStateObj.save_slots:
            gameStateObj.save_slots = load_saves()
            self.title_surf, self.title_pos = create_title(WORDS['Save Game'])

            options = [save_slot.get_name() for save_slot in gameStateObj.save_slots] # SaveSlots
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(max(gameStateObj.save_slots, key=lambda x:x.realtime))

            gameStateObj.stateMachine.changeState('transition_in')
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if not hasattr(self, 'wait_time'):       
            if event == 'DOWN':
                SOUNDDICT['Select 6'].play()
                gameStateObj.activeMenu.moveDown()
            elif event == 'UP':
                SOUNDDICT['Select 6'].play()
                gameStateObj.activeMenu.moveUp()

            elif event == 'BACK':
                SOUNDDICT['Select 4'].play()
                if gameStateObj.save_kind == 'Start':
                    current_states = gameStateObj.stateMachine.state
                    levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
                    # Load the next level anyway
                    SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                    # Put states back
                    gameStateObj.stateMachine.state = current_states
                gameStateObj.stateMachine.changeState('transition_pop')
            elif event == 'SELECT':
                SOUNDDICT['Select 1'].play()
                #self.selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
                # Rename thing
                name = SaveLoad.read_overview_file('Data/Level' + str(gameStateObj.counters['level']) + '/overview.txt')['name']
                gameStateObj.activeMenu.options[gameStateObj.activeMenu.getSelectionIndex()] = name
                self.wait_time = Engine.get_time()

    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        # Time must be greater than time needed to transition in
        if hasattr(self, 'wait_time') and Engine.get_time() - self.wait_time > 1250 and not self.leave_flag:
            #gameStateObj.stateMachine.back()
            self.leave_flag = True

            current_states = gameStateObj.stateMachine.state
            gameStateObj.stateMachine.state = gameStateObj.stateMachine.state[:-1] # Don't save this state
            SaveLoad.suspendGame(gameStateObj, gameStateObj.save_kind, slot=gameStateObj.activeMenu.getSelectionIndex())
            if gameStateObj.save_kind == 'Start':
                levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
                # Load the next level
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
            # Put states back
            gameStateObj.stateMachine.state = current_states
            gameStateObj.stateMachine.changeState('transition_pop')
            
    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.fog_bg.draw(surf)
        gameStateObj.fog_particles.update(Engine.get_time(), gameStateObj)
        gameStateObj.fog_particles.draw(surf)
        if gameStateObj.activeMenu:
            currentTime = Engine.get_time()
            if hasattr(self, 'wait_time') and currentTime - self.wait_time > 100 and currentTime - self.wait_time < 200:
                gameStateObj.activeMenu.draw(surf, flicker=True)
            else:
                gameStateObj.activeMenu.draw(surf)
        surf.blit(self.title_surf, self.title_pos)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
        #self.time_display.draw(surf, selection.realtime)
        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        gameStateObj.fog_bg = None
        gameStateObj.fog_particles = None

# === DISPLAY CREDITS SCREEN
class CreditsState(StateMachine.State):
    """Displays the credits screen, then returns"""
    def begin(self, gameStateObj, metaDataObj):
        self.show_map = False
        self.message = Dialogue.Dialogue_Scene('Data/credits.txt')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event:
            if self.message.current_state == "Displaying" and self.message.dialog:
                if self.message.dialog.waiting:
                    SOUNDDICT['Select 1'].play()
                    self.message.dialog_unpause()
                else:
                    while not self.message.dialog._next_char():
                        pass # while we haven't reached the end, process all the next chars...

    def update(self, gameStateObj, metaDataObj):
        self.message.update()
        if self.message.done and self.message.current_state == "Processing":
            gameStateObj.stateMachine.back()

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        surf.fill(colorDict['black'])
        self.message.draw(surf)
        return surf

# === DISPLAY GAME OVER SCREEN ================================================
class GameOverState(StateMachine.State):
    """Display the game over screen for a little transition, then cut to start screen"""
    def begin(self, gameStateObj, metaDataObj):
        self.lastUpdate = Engine.get_time()
        self.currentTime = self.lastUpdate
        self.GOStateMachine = CustomObjects.StateMachine('initial_transition')
        # Other states are text_fade_in, bg_fade_in, stasis

        self.transparency = 100
        self.backgroundCounter = 0
        Engine.music_thread.fade_in(MUSICDICT[CONSTANTS['music_game_over']], 1)

        # Make background
        self.MovingSurf = Engine.create_surface((256, 256), transparent=True, convert=True)
        self.MovingSurf.blit(IMAGESDICT['GameOverBackground'], (0,0))
        self.MovingSurf.blit(IMAGESDICT['GameOverBackground'], (0,128))
        self.MovingSurf.blit(IMAGESDICT['GameOverBackground'], (128,0))
        self.MovingSurf.blit(IMAGESDICT['GameOverBackground'], (128,128))
        self.MovingSurf = Engine.subsurface(self.MovingSurf, (0, 0, WINWIDTH, 256))

    def take_input(self, eventList, gameStateObj, metaDataObj):
        if self.GOStateMachine.getState() == 'stasis':
            event = gameStateObj.input_manager.process_input(eventList)
            if event:
                gameStateObj.stateMachine.back() # Any input returns to start screen

    def update(self, gameStateObj, metaDataObj):
        if self.transparency > 0:
            self.transparency -= 2

        if self.GOStateMachine.getState() == 'initial_transition':
            StateMachine.State.update(self, gameStateObj, metaDataObj)
            if self.transparency <= 0:
                self.transparency = 100
                self.GOStateMachine.changeState('text_fade_in')
        elif self.GOStateMachine.getState() == 'text_fade_in':
            if self.transparency <= 0:
                self.transparency = 100
                self.GOStateMachine.changeState('bg_fade_in')
        elif self.GOStateMachine.getState() == 'bg_fade_in':
            if self.transparency <= 0:
                self.transparency = 0
                self.GOStateMachine.changeState('stasis')

        # For bg movement
        self.backgroundCounter += 0.5
        if self.backgroundCounter >= self.MovingSurf.get_height():
            self.backgroundCounter = 0

    def draw(self, gameStateObj, metaDataObj):
        surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)

        # Black Background
        s = IMAGESDICT['BlackBackground'].copy()
        if self.GOStateMachine.getState() == 'initial_transition':
            alpha = 255 - int(2.55*self.transparency)
            s.fill((0,0,0,alpha))
        surf.blit(s, (0,0))

        # Game Over Background
        if self.GOStateMachine.getState() in ['bg_fade_in', 'stasis']:
            GOSurf = self.MovingSurf.copy()
            # Flicker image transparent
            if self.GOStateMachine.getState() == 'bg_fade_in':
                alpha = 255 - int(2.55*self.transparency)
                Engine.fill(GOSurf, (255, 255, 255, alpha), 'RGBA_MULT')

            # blit moving background image
            top = -int(self.backgroundCounter)
            surf.blit(GOSurf, (0, top))
            if 256 + top < WINHEIGHT:
                surf.blit(GOSurf, (0, 256+top))

        if self.GOStateMachine.getState() in ['text_fade_in', 'bg_fade_in', 'stasis']:
            TextSurf = IMAGESDICT['GameOverText'].copy()
            if self.GOStateMachine.getState() == 'text_fade_in':
                alpha = 255 - int(2.55*self.transparency)
                Engine.fill(TextSurf, (255, 255, 255, alpha), 'RGBA_MULT')
            pos = (WINWIDTH/2 - TextSurf.get_width()/2, WINHEIGHT/2 - TextSurf.get_height()/2)
        
            surf.blit(TextSurf, pos)

            surf.blit(IMAGESDICT['GameOverFade'], (0,0))

        return surf

class ChapterTransitionState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.background = TransitionBackground(IMAGESDICT['chapterTransitionBackground'])
        self.name = metaDataObj['name'] # Lol -- this is why some states show up as Chapter I
        self.show_map = False
        Engine.music_thread.fade_in(MUSICDICT['Chapter Sound'], 1)
        self.CTStateMachine = CustomObjects.StateMachine('transition_in')

        self.transition_in = 0
        self.sigil_fade = 100
        self.banner_grow_x = 0
        self.banner_grow_y = 6
        self.banner_fade = 0

        self.ribbon = IMAGESDICT['chapterTransitionRibbon']

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event and self.CTStateMachine.getState() == 'wait':
            Engine.music_thread.fade_out(400)
            self.CTStateMachine.changeState('fade_out')

    def update(self, gameStateObj, metaDataObj):
        currentTime = Engine.get_time()
        #gameStateObj.cameraOffset.update(gameStateObj)

        if self.CTStateMachine.getState() == 'transition_in':
            self.transition_in += 2
            if self.transition_in >= 100:
                self.transition_in = 100
                self.CTStateMachine.changeState('sigil')

        elif self.CTStateMachine.getState() == 'sigil':
            self.sigil_fade -= 1.5
            if self.sigil_fade <= 0:
                self.sigil_fade = 0
                self.CTStateMachine.changeState('banner_grow_x')

        elif self.CTStateMachine.getState() == 'banner_grow_x':
            self.banner_grow_x += 10
            if self.banner_grow_x >= WINWIDTH:
                self.banner_grow_x = WINWIDTH
                self.CTStateMachine.changeState('banner_grow_y')

        elif self.CTStateMachine.getState() == 'banner_grow_y':
            self.banner_grow_y += 2
            if self.banner_grow_y >= self.ribbon.get_height():
                self.banner_grow_y = self.ribbon.get_height()
                self.CTStateMachine.changeState('ribbon_fade_in')

        elif self.CTStateMachine.getState() == 'ribbon_fade_in':
            self.banner_fade += 2
            if self.banner_fade >= 100:
                self.banner_fade = 100
                self.wait_time = currentTime
                self.CTStateMachine.changeState('wait')

        elif self.CTStateMachine.getState() == 'wait':
            if currentTime - self.wait_time > 5000:
                Engine.music_thread.fade_out(400)
                self.CTStateMachine.changeState('fade_out')

        elif self.CTStateMachine.getState() == 'fade_out':
            self.transition_in -= 2
            self.sigil_fade += 2
            if self.sigil_fade >= 100:
                self.CTStateMachine.changeState('ribbon_close')

        elif self.CTStateMachine.getState() == 'ribbon_close':
            self.banner_grow_y -= 2
            if self.banner_grow_y <= 0:
                Engine.music_thread.stop()
                self.banner_grow_y = 0
                self.wait2_time = currentTime
                self.CTStateMachine.changeState('wait2')

        elif self.CTStateMachine.getState() == 'wait2':
            if currentTime - self.wait2_time > 200:
                gameStateObj.stateMachine.back()

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)

        # Draw blackbackground
        BlackTransitionSurf = Image_Modification.flickerImageTranslucent(IMAGESDICT['BlackBackground'], self.transition_in)
        mapSurf.blit(BlackTransitionSurf, (0, 0))

        # Draw sigil
        sigil_outline = Image_Modification.flickerImageTranslucent(IMAGESDICT['chapterTransitionSigil'], self.sigil_fade)
        sigil_middle = Image_Modification.flickerImageTranslucent(IMAGESDICT['chapterTransitionSigil2'], self.sigil_fade)
        center_x = (WINWIDTH/2 - sigil_outline.get_width()/2)
        center_y = (WINHEIGHT/2 - sigil_outline.get_height()/2)
        mapSurf.blit(sigil_outline, (center_x + 1, center_y + 1))
        mapSurf.blit(sigil_middle, (center_x, center_y))

        # Draw Ribbon
        if self.CTStateMachine.getState() in ['ribbon_fade_in', 'wait', 'ribbon_close', 'fade_out']:
            new_ribbon = self.ribbon.copy()
            position = (WINWIDTH/2 - FONT['chapter_yellow'].size(self.name)[0]/2, self.ribbon.get_height()/2 - 6)
            FONT['chapter_yellow'].blit(self.name, new_ribbon, position)
            new_ribbon = Engine.subsurface(new_ribbon, (0, (self.ribbon.get_height() - self.banner_grow_y)/2, self.ribbon.get_width(), self.banner_grow_y))
            mapSurf.blit(new_ribbon, (WINWIDTH/2 - self.ribbon.get_width()/2, WINHEIGHT/2 - new_ribbon.get_height()/2))

        # Draw Banner
        banner = Image_Modification.flickerImageTranslucent(IMAGESDICT['chapterTransitionBanner'], self.banner_fade)
        banner = Engine.subsurface(banner, (0, 0, self.banner_grow_x, self.banner_grow_y))
        mapSurf.blit(banner, (WINWIDTH/2 - banner.get_width()/2, WINHEIGHT/2 - banner.get_height()/2))

        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.background = None

transition_speed = 10
class TransitionInState(StateMachine.State):
    # Assumes there is a state directly under this state. Draw that state also
    def begin(self, gameStateObj, metaDataObj):
        self.background = IMAGESDICT['BlackBackground']
        self.transition = 0

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.state[-2].update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.state[-2].draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition)
        self.transition += transition_speed
        if self.transition >= 100:
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionOutState(StateMachine.State):
    # Assumes there is a state two under this state. Draw that state also
    # Earlier state ^
    # State to be draw
    # New State
    # This state
    def begin(self, gameStateObj, metaDataObj):
        self.background = IMAGESDICT['BlackBackground']
        self.transition = 100

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.state[-3].update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.state[-3].draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition)
        self.transition -= transition_speed
        if self.transition <= 0:
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionPopState(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        self.background = IMAGESDICT['BlackBackground']
        self.transition = 100

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.state[-2].update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.state[-2].draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition)
        self.transition -= transition_speed
        if self.transition <= 0:
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionCleanState(TransitionOutState):
    # Assumes there is a state directly under this state. Draw that state also.
    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.state[-2].update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.state[-2].draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition)
        self.transition -= transition_speed
        if self.transition <= 0:
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionBackground(object):
    def __init__(self, BGSurf):
        self.BGSurf = BGSurf
        self.backgroundSpeed = 25
        self.backgroundCounter = 0
        self.lastBackgroundUpdate = Engine.get_time()
        self.width = self.BGSurf.get_width()
        self.height = self.BGSurf.get_height()

    def draw(self, surf):
        currentTime = Engine.get_time()
        # Update background Counter
        if currentTime - self.lastBackgroundUpdate > self.backgroundSpeed:
            self.backgroundCounter += 1
            if self.backgroundCounter >= self.width:
                self.backgroundCounter = 0
            self.lastBackgroundUpdate = currentTime

        xindex, yindex = -self.backgroundCounter, -self.backgroundCounter
        while xindex < WINWIDTH:
            yindex = -self.backgroundCounter
            while yindex < WINHEIGHT:
                left = self.backgroundCounter if xindex < 0 else 0
                top = self.backgroundCounter if yindex < 0 else 0
                right = self.width - min(0, max(self.height, (xindex + self.width - WINWIDTH))) if xindex > WINWIDTH else self.width
                bottom = self.height - min(0, max(self.height, (yindex + self.height - WINHEIGHT))) if yindex > WINHEIGHT else self.height
                disp_surf = Engine.subsurface(self.BGSurf, (left, top, right - left, bottom - top))
                rect_left = xindex if xindex >= 0 else 0
                rect_top = yindex if yindex >= 0 else 0
                surf.blit(disp_surf, (rect_left, rect_top))
                yindex += self.height
            xindex += self.width