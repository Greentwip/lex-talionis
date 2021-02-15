# Transitions
# Game Over, Starting, Intro, Outro screens
import os, time

# Custom imports
from . import GlobalConstants as GC
from . import configuration as cf
from . import static_random
from . import Engine, Image_Modification
from . import CustomObjects, MenuFunctions, SaveLoad, StateMachine, Dialogue
from . import ClassData, BaseMenuSurf, Weather, Background

import logging
logger = logging.getLogger(__name__)

def create_title(text, background='DarkMenu'):
    title_surf = GC.IMAGESDICT[background].copy()
    title_pos = GC.WINWIDTH//2 - title_surf.get_width()//2, 21 - title_surf.get_height()//2
    center_pos = title_surf.get_width()//2 - GC.BASICFONT.size(text)[0]//2, title_surf.get_height()//2 - GC.BASICFONT.size(text)[1]//2
    MenuFunctions.OutlineFont(GC.BASICFONT, text, title_surf, GC.COLORDICT['off_white'], GC.COLORDICT['off_black'], center_pos)
    return title_surf, title_pos

class Button(object):
    def __init__(self, height, pos, key):
        self.image = Engine.subsurface(GC.IMAGESDICT['Buttons'], (0, height*16, 16, 16))
        self.pos = pos
        self.key = key

    def draw(self, surf):
        surf.blit(self.image, self.pos)
        GC.FONT['text_blue'].blit(Engine.get_key_name(cf.OPTIONS[self.key]), surf, (self.pos[0] + 18, self.pos[1]))

class TimeDisplay(object):
    def __init__(self):
        self.image = BaseMenuSurf.CreateBaseMenuSurf((128, 24), 'NoirMessageWindow')
        self.pos = [-128, GC.WINHEIGHT-24]
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
            GC.FONT['text_white'].blit(str_time, surf, (self.pos[0] + 4, self.pos[1] + 4))

def load_saves():
    save_slots = []
    for num in range(0, int(cf.CONSTANTS['save_slots'])):
        meta_fp = 'Saves/SaveState' + str(num) + '.pmeta'
        ss = CustomObjects.SaveSlot(meta_fp, num)
        save_slots.append(ss)
    return save_slots

def load_restarts():
    save_slots = []
    for num in range(0, int(cf.CONSTANTS['save_slots'])):
        meta_fp = 'Saves/Restart' + str(num) + '.pmeta'
        ss = CustomObjects.SaveSlot(meta_fp, num)
        save_slots.append(ss)
    return save_slots

def remove_suspend():
    if not cf.OPTIONS['cheat'] and os.path.exists(GC.SUSPEND_LOC):
        os.remove(GC.SUSPEND_LOC)

def get_save_title(save_slots):
    options = [save_slot.get_name() for save_slot in save_slots]

    def get_color(mode_id):
        for mode in GC.DIFFICULTYDATA.values():
            if int(mode['id']) == mode_id:
                return mode.get('color', 'Green')
        return 'Green'

    colors = [get_color(save_slot.mode_id) for save_slot in save_slots]
    return options, colors

TITLE_SCRIPT = False

class TitleDialogue(StateMachine.State):
    name = 'title_dialogue'

    def __init__(self, name='title_dialogue'):
        StateMachine.State.__init__(self, name)
        self.message = None
        self.text_speed_change = MenuFunctions.BriefPopUpDisplay((GC.WINWIDTH, GC.WINHEIGHT - 16))
        self.hurry_up_time = 0

    def begin(self, gameStateObj, metaDataObj):
        logger.info('Begin Title Dialogue State')
        if gameStateObj.message:
            self.message = gameStateObj.message[-1]
        if self.message:
            self.message.current_state = "Processing"

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)

        if (event == 'START' or event == 'BACK') and self.message and not self.message.do_skip: # SKIP
            GC.SOUNDDICT['Select 4'].play()
            self.message.skip()

        elif event == 'SELECT' or event == 'RIGHT' or event == 'DOWN': # Get it to move along...
            if self.message.current_state == "Displaying" and self.message.dialog:
                last_hit = Engine.get_time() - self.hurry_up_time
                if last_hit > 200:  # How long it will pause before moving on to next section
                    if self.message.dialog[-1].waiting:
                        GC.SOUNDDICT['Select 1'].play()
                        self.message.dialog_unpause()
                        self.hurry_up_time = 0
                    else:
                        self.message.dialog[-1].hurry_up()
                        self.hurry_up_time = Engine.get_time()

        elif event == 'AUX':  # Increment the text speed to be faster
            if cf.OPTIONS['Text Speed'] in cf.text_speed_options:
                GC.SOUNDDICT['Select 4'].play()
                current_index = cf.text_speed_options.index(cf.OPTIONS['Text Speed'])
                current_index += 1
                if current_index >= len(cf.text_speed_options):
                    current_index = 0
                cf.OPTIONS['Text Speed'] = cf.text_speed_options[current_index]
                self.text_speed_change.start('Changed Text Speed!')

    def end_dialogue_state(self, gameStateObj, metaDataObj):
        logger.debug('Ending dialogue state')
        last_message = None
        if self.message and gameStateObj.message:
            gameStateObj.message.pop()
        logger.info('Repeat Dialogue State!')
        return 'repeat'

    def update(self, gameStateObj, metaDataObj):
        if self.message:
            self.message.update(gameStateObj, metaDataObj)
        else:
            logger.info('Done with Dialogue State!')
            gameStateObj.stateMachine.back()
            return 'repeat'

        if self.message.done and self.message.current_state == "Processing":
            gameStateObj.stateMachine.back()
            return self.end_dialogue_state(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = gameStateObj.generic_surf
        if self.message:
            self.message.draw(mapSurf)
        self.text_speed_change.draw(mapSurf)
        return mapSurf

class StartStart(StateMachine.State):
    name = 'start_start'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            gameStateObj.button_a = Button(4, (GC.WINWIDTH - 64, GC.WINHEIGHT - 16), 'key_SELECT')
            gameStateObj.button_b = Button(5, (GC.WINWIDTH - 32, GC.WINHEIGHT - 16), 'key_BACK')
            gameStateObj.logo = GC.IMAGESDICT['Logo']
            gameStateObj.press_start = MenuFunctions.Logo(GC.IMAGESDICT['PressStart'], (GC.WINWIDTH//2, 4*GC.WINHEIGHT//5))
            gameStateObj.title_bg = Background.MovieBackground('title_background')
            bounds = (-GC.WINHEIGHT, GC.WINWIDTH, GC.WINHEIGHT, GC.WINHEIGHT+16)
            if cf.CONSTANTS['title_particles'] in Weather.WEATHER_CATALOG:
                gameStateObj.title_particles = Weather.Weather(cf.CONSTANTS['title_particles'], .075, bounds, (GC.TILEX, GC.TILEY))
            else:
                gameStateObj.title_particles = None
            # Wait until saving thread has finished
            if hasattr(gameStateObj, 'saving_thread'):
                gameStateObj.saving_thread.join()
            # if not hasattr(gameStateObj, 'save_slots') or not gameStateObj.save_slots:
            gameStateObj.save_slots = load_saves()
            gameStateObj.restart_slots = load_restarts()
            # Start music
            Engine.music_thread.fade_in(GC.MUSICDICT[cf.CONSTANTS.get('music_main')])

            # Play title script if it exists
            title_script_name = 'Data/titleScript.txt'
            global TITLE_SCRIPT
            if os.path.exists(title_script_name) and \
                    not TITLE_SCRIPT:
                gameStateObj.build_new()
                TITLE_SCRIPT = True
                title_script = Dialogue.Dialogue_Scene(title_script_name)
                gameStateObj.message.append(title_script)
                gameStateObj.stateMachine.changeState('title_dialogue')

            # Transition in:
            else:
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'AUX' and cf.OPTIONS['cheat']:
            GC.SOUNDDICT['Start'].play()
            # selection = gameStateObj.save_slots[0]    
            gameStateObj.build_new() # Make the gameStateObj ready for a new game
            gameStateObj.set_generic_mode()
            gameStateObj.save_slot = 'DEBUG'
            gameStateObj.game_constants['level'] = 'DEBUG'
            # static_random.set_seed(0)
            levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
            if not os.path.exists(levelfolder):
                return
            # Load the first level
            SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
            # Hardset the name of the first level
            # gameStateObj.saveSlot = selection
            gameStateObj.stateMachine.clear()
            gameStateObj.stateMachine.changeState('turn_change')
            gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
            return 'repeat'
        # Load most recent save
        elif event == 'INFO' and cf.OPTIONS['cheat']:
            GC.SOUNDDICT['Select 1'].play()
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
                levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
                # Load the first level
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
            gameStateObj.transition_from = cf.WORDS['Load Game']
            gameStateObj.stateMachine.changeState('start_wait')
            gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
            remove_suspend()
            return 'repeat'
        elif event:
            GC.SOUNDDICT['Start'].play()
            gameStateObj.stateMachine.changeState('start_option')
            gameStateObj.stateMachine.changeState('transition_out')
            return

    def update(self, gameStateObj, metaDataObj):
        # gameStateObj.logo.update()
        gameStateObj.press_start.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        # gameStateObj.logo.draw(surf)
        surf.blit(gameStateObj.logo, (GC.WINWIDTH//2 - gameStateObj.logo.get_width()//2, GC.WINHEIGHT//2 - gameStateObj.logo.get_height()//2 - 20))
        gameStateObj.press_start.draw(surf)
        GC.FONT['text_white'].blit(cf.CONSTANTS['attribution'], surf, (4, GC.WINHEIGHT - 16))
        return surf

class StartOption(StateMachine.State):
    name = 'start_option'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.banner = None
            self.position_x = -GC.WINWIDTH//2

            self.background = GC.IMAGESDICT['BlackBackground']
            self.transition = 100

            options = [cf.WORDS['New Game'], cf.WORDS['Extras']]
            # If there are any games to load...
            if any(ss.kind for ss in gameStateObj.save_slots):
                options.insert(0, cf.WORDS['Restart Level'])
                options.insert(0, cf.WORDS['Load Game'])
            if os.path.exists(GC.SUSPEND_LOC):
                options.insert(0, cf.WORDS['Continue'])
            self.menu = MenuFunctions.MainMenu(options, 'DarkMenu')
            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)

        if self.state == "normal":
            if event == 'DOWN':
                GC.SOUNDDICT['Select 6'].play()
                self.menu.moveDown()
            elif event == 'UP':
                GC.SOUNDDICT['Select 6'].play()
                self.menu.moveUp()

            elif event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.changeState('start_start')
                gameStateObj.stateMachine.changeState('transition_out')

            elif event == 'SELECT':
                GC.SOUNDDICT['Select 1'].play()
                self.selection = self.menu.getSelection()
                if self.selection == cf.WORDS['Continue']:
                    self.state = 'wait'
                elif os.path.exists(GC.SUSPEND_LOC) and not self.banner and \
                        self.selection in (cf.WORDS['Load Game'], cf.WORDS['Restart Level'], cf.WORDS['New Game']):
                    GC.SOUNDDICT['Select 2'].play()
                    if self.selection == cf.WORDS['New Game']:
                        text = 'Starting a new game will remove suspend!'
                        width = 200
                        position = (6, 6)
                    else:
                        text = 'Loading a game will remove suspend!'
                        width = 180
                        position = (4, 6)
                    self.banner = BaseMenuSurf.CreateBaseMenuSurf((width, 24), 'DarkMenuBackground')
                    self.banner = Image_Modification.flickerImageTranslucent(self.banner, 10)
                    MenuFunctions.OutlineFont(GC.BASICFONT, text, self.banner, GC.COLORDICT['off_white'], GC.COLORDICT['off_black'], position)
                    self.state = "click_once"
                elif self.selection == cf.WORDS['New Game']:
                    self.banner = None
                    gameStateObj.stateMachine.changeState('start_mode')
                    gameStateObj.stateMachine.changeState('transition_out')
                else:
                    self.banner = None
                    self.state = "transition_out"

        elif self.state == "click_once":
            if event == 'SELECT':
                if self.menu.getSelection() == cf.WORDS['New Game']:
                    gameStateObj.stateMachine.changeState('start_mode')
                    gameStateObj.stateMachine.changeState('transition_out')
                else:
                    self.state = "transition_out"
                self.banner = None
            elif event:
                self.banner = None
                self.state = "normal"
                
    def update(self, gameStateObj, metaDataObj):
        # gameStateObj.logo.update()
        if self.menu:
            self.menu.update()

        # Transition out
        if self.state == 'transition_in':
            self.position_x += 20
            if self.position_x >= GC.WINWIDTH//2:
                self.position_x = GC.WINWIDTH//2
                self.state = "normal"

        elif self.state == 'transition_out':
            self.position_x -= 20
            if self.position_x <= -GC.WINWIDTH//2:
                self.position_x = -GC.WINWIDTH//2
                if self.selection == cf.WORDS['Load Game']:
                    gameStateObj.stateMachine.changeState('start_load')
                elif self.selection == cf.WORDS['Restart Level']:
                    gameStateObj.stateMachine.changeState('start_restart')
                elif self.selection == cf.WORDS['Extras']:
                    gameStateObj.stateMachine.changeState('start_extras')
                elif self.selection == cf.WORDS['New Game']:
                    # gameStateObj.stateMachine.changeState('start_new')
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
        gameStateObj.activeMenu = None # Remove menu
        suspend = CustomObjects.SaveSlot(GC.SUSPEND_LOC, None)
        logger.debug('Loading game...')
        SaveLoad.loadGame(gameStateObj, metaDataObj, suspend)

    def load_most_recent_game(self, gameStateObj, metaDataObj):
        selection = max(gameStateObj.save_slots, key=lambda x: x.realtime)
        SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
        if selection.kind == 'Start': # Restart
            levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
            # Load the level
            SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        if self.menu:
            self.menu.draw(surf, center=(self.position_x, GC.WINHEIGHT//2), show_cursor=(self.state == "normal"))
        if self.banner and self.state == 'click_once':
            surf.blit(self.banner, (GC.WINWIDTH//2 - self.banner.get_width()//2, GC.WINHEIGHT//2 - self.banner.get_height()//2))

        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition)
        surf.blit(bb, (0, 0))

        return surf

class StartLoad(StateMachine.State):
    name = 'start_load'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*GC.WINWIDTH//2
            self.title_surf, self.title_pos = create_title(cf.WORDS['Load Game'])
            self.rel_title_pos_y = -40
            options, colors = get_save_title(gameStateObj.save_slots)
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options, colors)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(max(gameStateObj.save_slots, key=lambda x: x.realtime))
            # self.time_display = TimeDisplay()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            # self.time_display.state = 'left'

        elif event == 'SELECT':
            selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                GC.SOUNDDICT['Save'].play()

                # gameStateObj.activeMenu = None # Remove menu
                logger.debug('Loading game...')
                SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
                if selection.kind == 'Start': # Restart
                    levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
                    # Load the first level
                    SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                gameStateObj.transition_from = cf.WORDS['Load Game']
                gameStateObj.stateMachine.changeState('start_wait')
                gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
                remove_suspend()
            else:
                GC.SOUNDDICT['Error'].play()

    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= GC.WINWIDTH//2:
                self.position_x = GC.WINWIDTH//2
                self.state = "normal"
            if self.rel_title_pos_y < 0:
                self.rel_title_pos_y += 4 

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.rel_title_pos_y > -40:
                self.rel_title_pos_y -= 4
            if self.position_x >= 3*GC.WINWIDTH//2:
                self.position_x = 3*GC.WINWIDTH//2
                gameStateObj.stateMachine.back()
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.draw(surf, center=[self.position_x, GC.WINHEIGHT/2])
        surf.blit(self.title_surf, (self.title_pos[0], self.title_pos[1] + self.rel_title_pos_y))
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        # selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
        # self.time_display.draw(surf, selection.realtime)

        return surf

class StartAllSaves(StartLoad):
    name = 'start_all_saves'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.fluid_helper.update_speed(128)
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*GC.WINWIDTH//2
            self.title_surf, self.title_pos = create_title(cf.WORDS['Load Game'])
            self.rel_title_pos_y = -40
            self.all_saves = sorted(self.get_all_saves(), key=lambda x: x.realtime, reverse=True)
            options, colors = get_save_title(self.all_saves)
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options, colors)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = 0

    def get_all_saves(self):
        import glob
        save_slots = []
        for meta_fn in glob.glob('Saves/L*T*.pmeta'):
            ss = CustomObjects.SaveSlot(meta_fn, 0)
            save_slots.append(ss)
        return save_slots

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        first_push = self.fluid_helper.update(gameStateObj)
        directions = self.fluid_helper.get_directions()
                        
        if 'DOWN' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown(first_push)
        elif 'UP' in directions:
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp(first_push)

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            # self.time_display.state = 'left'

        elif event == 'SELECT':
            selection = self.all_saves[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                GC.SOUNDDICT['Save'].play()

                # gameStateObj.activeMenu = None # Remove menu
                logger.debug('Loading game...')
                SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
                if selection.kind == 'Start': # Restart
                    levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
                    # Load the first level
                    SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                gameStateObj.transition_from = cf.WORDS['Load Game']
                gameStateObj.stateMachine.changeState('start_wait')
                gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
            else:
                GC.SOUNDDICT['Error'].play()

class StartPreloadedLevels(StartLoad):
    name = 'start_preloaded_levels'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*GC.WINWIDTH//2
            self.title_surf, self.title_pos = create_title(cf.WORDS['Load Game'])
            self.rel_title_pos_y = -40
            options, colors = self.get_colors()
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options, colors)
            gameStateObj.activeMenu.currentSelection = 0

    def get_colors(self):
        name, color = [], []
        for level in GC.PRELOADDATA.getroot().findall('level'):
            name.append(level.get('name'))
            color.append(GC.DIFFICULTYDATA[level.find('mode').text].get('color', 'Green'))
        return name, color

    def preload_level(self, name):
        def parse_item_uses_list(text):
            my_items = []
            if text:
                items = text.split(',')
                for item in items:
                    uses = item.split()[-1]
                    item_id = ' '.join(item.split()[:-1])
                    my_items.append((item_id, uses))
            return my_items

        def parse_game_constants(text):
            gc = {}
            if text:
                pairs = text.split(';')
                for pair in pairs:
                    key, value = pair.split(',')
                    try:
                        gc[key] = int(value)
                    except:
                        gc[key] = value
            return gc

        level_dict = {}
        for level in GC.PRELOADDATA.getroot().findall('level'):
            if level.get('name') == name:
                level_dict['name'] = level.get('name')
                level_dict['mode'] = level.find('mode').text
                try:
                    level_dict['game_constants'] = parse_game_constants(level.find('game_constants').text)
                except AttributeError as e:
                    print('Could not load game constants: %s' % e)
                    level_dict['game_constants'] = {}
                level_dict['convoy'] = parse_item_uses_list(level.find('convoy').text)
                units = level.find('units')
                unit_list = []
                for unit in units.findall('unit'):
                    unit_dict = {}
                    unit_dict['name'] = unit.get('name')
                    unit_dict['party'] = unit.find('party').text if unit.find('party') is not None else None
                    unit_dict['class'] = unit.find('class').text if unit.find('class') is not None else None
                    unit_dict['level'] = int(unit.find('level').text)
                    unit_dict['exp'] = int(unit.find('exp').text)
                    unit_dict['items'] = parse_item_uses_list(unit.find('items').text)
                    unit_dict['wexp'] = [int(x) for x in unit.find('wexp').text.split(',')]
                    skill_text = unit.find('skills').text
                    unit_dict['skills'] = [x for x in skill_text.split(',')] if skill_text else []
                    unit_dict['dead'] = int(unit.find('dead').text) if unit.find('dead') is not None else 0
                    unit_list.append(unit_dict)
                level_dict['units'] = unit_list
                return level_dict

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            # self.time_display.state = 'left'

        elif event == 'SELECT':
            preloaded_level = self.preload_level(gameStateObj.activeMenu.getSelection())
            GC.SOUNDDICT['Save'].play()
            logger.debug('Starting Preloaded Level...')
            self.build_new_game(preloaded_level, gameStateObj, metaDataObj)

    def build_new_game(self, level, gameStateObj, metaDataObj):
        from . import ItemMethods, StatusCatalog, Action
        gameStateObj.build_new() # Make the gameStateObj ready for a new game

        levelfolder = 'Data/Level' + str(level['name'])
        SaveLoad.get_metaDataObj(levelfolder, metaDataObj)

        # === Populate ===
        # Mode, Money, Level...
        gameStateObj.game_constants['level'] = level['name']
        try:
            gameStateObj.game_constants['level'] = int(gameStateObj.game_constants['level'])
        except ValueError:  # That's fine just keep going
            pass
        for key, value in level['game_constants'].items():
            gameStateObj.game_constants[key] = value
        static_random.set_seed(gameStateObj.game_constants.get('_random_seed', 0))

        modes = [mode for mode in GC.DIFFICULTYDATA.values() if level['mode'] == mode['name'] or level['mode'] == mode['id']]
        if modes:
            gameStateObj.mode = modes[0]
        else:
            gameStateObj.mode = gameStateObj.default_mode()
        gameStateObj.default_mode_choice()

        gameStateObj.save_slot = 'Preload ' + level['name']
        # Convoy
        for item_id, uses in level['convoy']:
            item = ItemMethods.itemparser(item_id, gameStateObj)
            if not item:
                continue
            if item.uses:
                item.uses.uses = int(uses)
            gameStateObj.convoy.append(item)
        if level['convoy']:
            gameStateObj.game_constants['Convoy'] = True
        # Units
        for unit_dict in level['units']:
            legend = {}
            legend['team'] = 'player'
            legend['event_id'] = '0'
            legend['position'] = 'None'
            legend['unit_id'] = unit_dict['name']
            legend['ai'] = 'None'
            # Reinforcement units can be empty, since they won't spawn in as reinforcements
            unit = SaveLoad.add_unit_from_legend(legend, gameStateObj.allunits, {}, gameStateObj)

            # Put unit in the correct party
            if unit_dict['party'] is not None:
                unit.party = unit_dict['party']

            # Remove starting items
            for item in reversed(unit.items):
                Action.RemoveItem(unit, item).execute(gameStateObj)

            # Get items
            for item_id, uses in unit_dict['items']:
                item = ItemMethods.itemparser(item_id, gameStateObj)
                if not item:
                    continue
                if item.uses:
                    item.uses.uses = int(uses)
                unit.add_item(item, gameStateObj)
            # Level up the unit
            max_level = ClassData.class_dict[unit.klass]['max_level']
            old_class_tier = ClassData.class_dict[unit.klass]['tier']
            if unit_dict['class']:
                new_class_tier = ClassData.class_dict[unit_dict['class']]['tier']
            else:
                new_class_tier = -10  # Really low
            tier_diff = max(0, new_class_tier - old_class_tier) * max_level
            for level_num in range(unit_dict['level'] + tier_diff - unit.level):
                unit_klass = ClassData.class_dict[unit.klass]
                max_level = unit_klass['max_level']
                if unit.level >= max_level:
                    class_options = unit_klass['turns_into']
                    if class_options:
                        if unit_dict['class'] in class_options:
                            new_klass = unit_dict['class']
                        else:
                            new_klass = class_options[0]
                        Action.Promote(unit, new_klass).execute(gameStateObj)
                else:
                    unit.level += 1
                    leveluplist = unit.level_up(gameStateObj, unit_klass)
                    unit.apply_levelup(leveluplist, True)
            unit.set_exp(unit_dict['exp'])
            unit.wexp = unit_dict['wexp']
            # Get skills
            for skill_id in unit_dict['skills']:
                if skill_id not in (s.id for s in unit.status_effects):
                    skill = StatusCatalog.statusparser(skill_id, gameStateObj)
                    if skill:
                        Action.AddStatus(unit, skill).do(gameStateObj)
            unit.change_hp(1000)  # reset currenthp

            # Handle units that are already dead
            if unit_dict['dead']:
                unit.dead = True

        # Actually load the level
        SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
        # Hardset the name of the first level
        gameStateObj.stateMachine.clear()
        gameStateObj.stateMachine.changeState('turn_change')
        # gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
        # gameStateObj.transition_from = cf.WORDS['Load Game']
        # gameStateObj.stateMachine.changeState('start_wait')
        # gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)

class StartRestart(StartLoad):
    name = 'start_restart'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*GC.WINWIDTH//2
            self.title_surf, self.title_pos = create_title(cf.WORDS['Restart Level'])
            self.rel_title_pos_y = -40
            options, colors = get_save_title(gameStateObj.save_slots)
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options, colors)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(max(gameStateObj.save_slots, key=lambda x: x.realtime))
            # self.time_display = TimeDisplay()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            # self.time_display.state = 'left'

        elif event == 'SELECT':
            selection = gameStateObj.restart_slots[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                GC.SOUNDDICT['Save'].play()

                # gameStateObj.activeMenu = None # Remove menu
                logger.debug('Restarting Level...')
                SaveLoad.loadGame(gameStateObj, metaDataObj, selection)
                # Always Restart
                levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                gameStateObj.transition_from = cf.WORDS['Restart Level']
                gameStateObj.stateMachine.changeState('start_wait')
                gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
                remove_suspend()
            else:
                GC.SOUNDDICT['Error'].play()

class StartMode(StateMachine.State):
    name = 'start_mode'

    def no_difficulty_choice(self):
        return len(GC.DIFFICULTYDATA) == 1

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.menu = None
            self.state = 'difficulty_setup'
            self.started = True
            self.death_choice = True
            self.growth_choice = True

        if self.state == 'difficulty_setup':
            if self.no_difficulty_choice():
                gameStateObj.mode = list(GC.DIFFICULTYDATA.values())[0].copy()
                self.death_choice = gameStateObj.mode['death'] == '?'
                self.growth_choice = gameStateObj.mode['growths'] == '?'
                self.state = 'death_setup'
                return self.begin(gameStateObj, metaDataObj)
            else:
                self.title_surf, self.title_pos = create_title(cf.WORDS['Select Difficulty'])
                options = list(GC.DIFFICULTYDATA)
                toggle = [True for o in options]
                self.menu = MenuFunctions.ModeSelectMenu(options, toggle, default=0)
                gameStateObj.stateMachine.changeState('transition_in')
                self.state = 'difficulty_wait'
                return 'repeat'

        elif self.state == 'death_setup':
            if self.death_choice:
                self.title_surf, self.title_pos = create_title(cf.WORDS['Select Mode'])
                options = ['Casual', 'Classic']
                toggle = [True, True]
                self.menu = MenuFunctions.ModeSelectMenu(options, toggle, default=1)
                gameStateObj.stateMachine.changeState('transition_in')
                self.state = 'death_wait'
                return 'repeat'
            else:
                self.state = 'growth_setup'
                return self.begin(gameStateObj, metaDataObj)

        elif self.state == 'growth_setup':
            if self.growth_choice:
                self.title_surf, self.title_pos = create_title(cf.WORDS['Select Growths'])
                options = ['Random', 'Fixed', 'Hybrid']
                toggle = [True, True, True]
                self.menu = MenuFunctions.ModeSelectMenu(options, toggle, default=1)
                gameStateObj.stateMachine.changeState('transition_in')
                self.state = 'growth_wait'
            else:
                gameStateObj.stateMachine.changeState('start_new')
                gameStateObj.stateMachine.changeState('transition_out')
                
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)    
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if self.state == 'difficulty_wait':
                gameStateObj.stateMachine.changeState('transition_pop')
            elif self.state == 'death_wait':
                if self.no_difficulty_choice():
                    gameStateObj.stateMachine.changeState('transition_pop')
                else:
                    self.state = 'difficulty_setup'
                    gameStateObj.stateMachine.changeState('transition_clean')
            elif self.state == 'growth_wait':
                if self.death_choice:
                    self.state = 'death_setup'
                    gameStateObj.stateMachine.changeState('transition_clean')
                else:
                    if self.no_difficulty_choice():
                        gameStateObj.stateMachine.changeState('transition_pop')
                    else:
                        self.state = 'difficulty_setup'
                        gameStateObj.stateMachine.changeState('transition_clean')
                    
            return 'repeat'

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            if self.state == 'growth_wait':
                gameStateObj.mode['growths'] = self.menu.getSelectionIndex()
                gameStateObj.stateMachine.changeState('start_new')
                gameStateObj.stateMachine.changeState('transition_out')
            elif self.state == 'death_wait':
                gameStateObj.mode['death'] = self.menu.getSelectionIndex()
                if self.growth_choice:
                    self.state = 'growth_setup'
                    gameStateObj.stateMachine.changeState('transition_clean')
                else:
                    gameStateObj.stateMachine.changeState('start_new')
                    gameStateObj.stateMachine.changeState('transition_out')
            elif self.state == 'difficulty_wait':
                gameStateObj.mode = list(GC.DIFFICULTYDATA.values())[self.menu.getSelectionIndex()].copy()
                self.death_choice = gameStateObj.mode['death'] == '?'
                self.growth_choice = gameStateObj.mode['growths'] == '?'
                if self.death_choice:
                    self.state = 'death_setup'
                    gameStateObj.stateMachine.changeState('transition_clean')
                elif self.growth_choice:
                    self.state = 'growth_setup'
                    gameStateObj.stateMachine.changeState('transition_clean')
                else:
                    gameStateObj.stateMachine.changeState('start_new')
                    gameStateObj.stateMachine.changeState('transition_out')
            return 'repeat'

    def update(self, gameStateObj, metaDataObj):
        if self.menu:
            self.menu.update()

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        if self.menu:
            self.menu.draw(surf)
            surf.blit(self.title_surf, self.title_pos)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        return surf

class StartNew(StateMachine.State):
    name = 'start_new'

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            # For transition
            self.selection = None
            self.state = "transition_in"
            self.position_x = 3*GC.WINWIDTH//2
            self.title_surf, self.title_pos = create_title(cf.WORDS['New Game'])
            self.rel_title_pos_y = -40
            options, colors = get_save_title(gameStateObj.save_slots)
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options, colors)
            # Default to oldest
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(min(gameStateObj.save_slots, key=lambda x: x.realtime))
            # self.time_display = TimeDisplay()
        # self.time_display.state = 'right'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)    
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.activeMenu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'
            # self.time_display.state = 'left'

        elif event == 'SELECT':
            selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
            if selection.kind:
                GC.SOUNDDICT['Select 1'].play()
                options = [cf.WORDS['Overwrite'], cf.WORDS['Back']]
                gameStateObj.childMenu = MenuFunctions.ChoiceMenu(selection, options, (GC.TILEWIDTH//2, GC.WINHEIGHT - GC.TILEHEIGHT * 1.5), horizontal=True)
                gameStateObj.stateMachine.changeState('start_newchild')
                # self.time_display.state = 'left'
            else:
                GC.SOUNDDICT['Save'].play()
                self.build_new_game(gameStateObj, metaDataObj)
    
    def build_new_game(self, gameStateObj, metaDataObj):
        gameStateObj.build_new() # Make the gameStateObj ready for a new game
        gameStateObj.save_slot = gameStateObj.activeMenu.getSelectionIndex()
        levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
        # Create a save for the first game
        gameStateObj.stateMachine.clear()
        gameStateObj.stateMachine.changeState('turn_change')
        SaveLoad.suspendGame(gameStateObj, "Start", slot=gameStateObj.save_slot)
        # Load the first level
        SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
        # Hardset the name of the first level
        gameStateObj.activeMenu.options[gameStateObj.save_slot] = metaDataObj['name']
        gameStateObj.activeMenu.set_color(gameStateObj.save_slot, gameStateObj.mode.get('color', 'Green'))
        gameStateObj.stateMachine.clear()
        gameStateObj.stateMachine.changeState('turn_change')
        # gameStateObj.stateMachine.process_temp_state(gameStateObj, metaDataObj)
        gameStateObj.transition_from = cf.WORDS['New Game']
        gameStateObj.stateMachine.changeState('start_wait')
        remove_suspend()

    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        if gameStateObj.childMenu:
            gameStateObj.childMenu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= GC.WINWIDTH//2:
                self.position_x = GC.WINWIDTH//2
                self.state = "normal"
            if self.rel_title_pos_y < 0:
                self.rel_title_pos_y += 4 

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.rel_title_pos_y > -40:
                self.rel_title_pos_y -= 4
            if self.position_x >= 3*GC.WINWIDTH//2:
                self.position_x = 3*GC.WINWIDTH//2
                # gameStateObj.stateMachine.back()
                gameStateObj.stateMachine.clear()
                gameStateObj.stateMachine.changeState('start_option')
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.draw(surf, center=[self.position_x, GC.WINHEIGHT//2])
        # selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
        # self.time_display.draw(surf, selection.realtime)
        if gameStateObj.childMenu:
            gameStateObj.childMenu.draw(surf)
        surf.blit(self.title_surf, (self.title_pos[0], self.title_pos[1] + self.rel_title_pos_y))
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)

        return surf

class StartNewChild(StartNew):
    name = 'start_newchild'

    def begin(self, gameStateObj, metaDataObj):
        self.title_surf, self.title_pos = create_title(cf.WORDS['New Game'])

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'RIGHT':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveDown()
        elif event == 'LEFT':
            GC.SOUNDDICT['Select 6'].play()
            gameStateObj.childMenu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.childMenu = None # Remove menu
            gameStateObj.stateMachine.back()

        elif event == 'SELECT':
            selection = gameStateObj.childMenu.getSelection()
            if selection == 'Overwrite':
                GC.SOUNDDICT['Save'].play()
                self.build_new_game(gameStateObj, metaDataObj)
            elif selection == 'Back':
                GC.SOUNDDICT['Select 4'].play()
                gameStateObj.stateMachine.back()

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.state[-2].update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        return gameStateObj.stateMachine.state[-2].draw(gameStateObj, metaDataObj)

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.childMenu = None

class StartExtras(StateMachine.State):
    name = 'start_extras'

    def begin(self, gameStateObj, metaDataObj):
        # For transition
        self.selection = None
        self.state = "transition_in"
        self.position_x = 3*GC.WINWIDTH//2

        options = [cf.WORDS['Options'], cf.WORDS['Credits']]
        if cf.OPTIONS['cheat']:
            options.append(cf.WORDS['All Saves'])
            options.append(cf.WORDS['Preloaded Levels'])
        self.menu = MenuFunctions.MainMenu(options, 'DarkMenu')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
                        
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveDown()
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            self.menu.moveUp()

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            # gameStateObj.activeMenu = None # Remove menu
            self.state = 'transition_out'

        elif event == 'SELECT':
            GC.SOUNDDICT['Select 1'].play()
            selection = self.menu.getSelection()
            if selection == cf.WORDS['Credits']:
                gameStateObj.stateMachine.changeState('credits')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Options']:
                gameStateObj.stateMachine.changeState('config_menu')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['All Saves']:
                gameStateObj.stateMachine.changeState('start_all_saves')
                gameStateObj.stateMachine.changeState('transition_out')
            elif selection == cf.WORDS['Preloaded Levels']:
                gameStateObj.stateMachine.changeState('start_preloaded_levels')
                gameStateObj.stateMachine.changeState('transition_out')

    def update(self, gameStateObj, metaDataObj):
        # gameStateObj.logo.update()
        if self.menu:
            self.menu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= GC.WINWIDTH//2:
                self.position_x = GC.WINWIDTH//2
                self.state = "normal"

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.position_x >= 3*GC.WINWIDTH//2:
                self.position_x = 3*GC.WINWIDTH//2
                gameStateObj.stateMachine.back()
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        # GC.FONT['text_white'].blit(cf.CONSTANTS['attribution'], surf, (4, GC.WINHEIGHT - 16))
        # gameStateObj.logo.draw(surf)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        if self.menu:
            self.menu.draw(surf, center=(self.position_x, GC.WINHEIGHT//2))
        return surf

class StartWait(StateMachine.State):
    name = 'start_wait'

    def begin(self, gameStateObj, metaDataObj):
        self.wait_flag = False
        self.wait_time = Engine.get_time()
        self.title_surf, self.title_pos = create_title(gameStateObj.transition_from)
        
    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        if not self.wait_flag and hasattr(self, 'wait_time') and Engine.get_time() - self.wait_time > 750:
            # gameStateObj.stateMachine.back()
            self.wait_flag = True
            gameStateObj.stateMachine.changeState('transition_pop')

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
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
        gameStateObj.title_bg = None
        gameStateObj.title_particles = None

class StartSave(StateMachine.State):
    name = 'start_save'

    def begin(self, gameStateObj, metaDataObj):
        # self.selection = None
        if self.started:
            self.leave_flag = False
    
        if not self.started:
            gameStateObj.button_a = Button(4, (GC.WINWIDTH - 64, GC.WINHEIGHT - 16), 'key_SELECT')
            gameStateObj.button_b = Button(5, (GC.WINWIDTH - 32, GC.WINHEIGHT - 16), 'key_BACK')
            gameStateObj.title_bg = Background.MovieBackground('title_background')
            bounds = (-GC.WINHEIGHT, GC.WINWIDTH, GC.WINHEIGHT, GC.WINHEIGHT+16)
            if cf.CONSTANTS['title_particles'] in Weather.WEATHER_CATALOG:
                gameStateObj.title_particles = Weather.Weather(cf.CONSTANTS['title_particles'], .075, bounds, (GC.TILEX, GC.TILEY))
            else:
                gameStateObj.title_particles = None
            # self.time_display = TimeDisplay()
            # if not hasattr(gameStateObj, 'save_slots') or not gameStateObj.save_slots:
            gameStateObj.save_slots = load_saves()
            self.title_surf, self.title_pos = create_title(cf.WORDS['Save Game'])

            options, colors = get_save_title(gameStateObj.save_slots)
            gameStateObj.activeMenu = MenuFunctions.ChapterSelectMenu(options, colors)
            # Default to most recent
            gameStateObj.activeMenu.currentSelection = gameStateObj.save_slots.index(max(gameStateObj.save_slots, key=lambda x: x.realtime))

            gameStateObj.stateMachine.changeState('transition_in')
            return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if not hasattr(self, 'wait_time'):       
            if event == 'DOWN':
                GC.SOUNDDICT['Select 6'].play()
                gameStateObj.activeMenu.moveDown()
            elif event == 'UP':
                GC.SOUNDDICT['Select 6'].play()
                gameStateObj.activeMenu.moveUp()

            elif event == 'BACK':
                GC.SOUNDDICT['Select 4'].play()
                if gameStateObj.save_kind == 'Start':
                    current_states = gameStateObj.stateMachine.state
                    levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
                    # Load the next level anyway
                    SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
                    # Put states back
                    gameStateObj.stateMachine.state = current_states
                gameStateObj.stateMachine.changeState('transition_pop')
            elif event == 'SELECT':
                GC.SOUNDDICT['Save'].play()
                # self.selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
                # Rename thing
                name = SaveLoad.read_overview_file('Data/Level' + str(gameStateObj.game_constants['level']) + '/overview.txt')['name']
                gameStateObj.activeMenu.options[gameStateObj.activeMenu.getSelectionIndex()] = name
                gameStateObj.activeMenu.set_color(gameStateObj.activeMenu.getSelectionIndex(), gameStateObj.mode.get('color', 'Green'))
                self.wait_time = Engine.get_time()

    def update(self, gameStateObj, metaDataObj):
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        # Time must be greater than time needed to transition in
        if hasattr(self, 'wait_time') and Engine.get_time() - self.wait_time > 1250 and not self.leave_flag:
            # gameStateObj.stateMachine.back()
            self.leave_flag = True

            current_states = gameStateObj.stateMachine.state
            gameStateObj.stateMachine.state = gameStateObj.stateMachine.state[:-1] # Don't save this state
            SaveLoad.suspendGame(gameStateObj, gameStateObj.save_kind, slot=gameStateObj.activeMenu.getSelectionIndex())
            if gameStateObj.save_kind == 'Start':
                levelfolder = 'Data/Level' + str(gameStateObj.game_constants['level'])
                # Load the next level
                SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
            # Put states back
            gameStateObj.stateMachine.state = current_states
            gameStateObj.stateMachine.changeState('transition_pop')
            
    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.generic_surf
        gameStateObj.title_bg.draw(surf)
        if gameStateObj.title_particles:
            gameStateObj.title_particles.update(Engine.get_time(), gameStateObj)
            gameStateObj.title_particles.draw(surf)
        if gameStateObj.activeMenu:
            currentTime = Engine.get_time()
            if hasattr(self, 'wait_time') and currentTime - self.wait_time > 100 and currentTime - self.wait_time < 200:
                gameStateObj.activeMenu.draw(surf, flicker=True)
            else:
                gameStateObj.activeMenu.draw(surf)
        surf.blit(self.title_surf, self.title_pos)
        gameStateObj.button_a.draw(surf)
        gameStateObj.button_b.draw(surf)
        # selection = gameStateObj.save_slots[gameStateObj.activeMenu.getSelectionIndex()]
        # self.time_display.draw(surf, selection.realtime)
        return surf

    def finish(self, gameStateObj, metaDataObj):
        gameStateObj.activeMenu = None
        gameStateObj.title_bg = None
        gameStateObj.title_particles = None

# === DISPLAY CREDITS SCREEN
class CreditsState(StateMachine.State):
    name = 'credits'

    """Displays the credits screen, then returns"""
    def begin(self, gameStateObj, metaDataObj):
        self.show_map = False
        self.message = Dialogue.Dialogue_Scene('Data/credits.txt')

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event:
            if self.message.current_state == "Displaying" and self.message.dialog:
                if self.message.dialog.waiting:
                    GC.SOUNDDICT['Select 1'].play()
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
        surf.fill(GC.COLORDICT['black'])
        self.message.draw(surf)
        return surf

# === DISPLAY GAME OVER SCREEN ================================================
class GameOverState(StateMachine.State):
    name = 'game_over'

    """Display the game over screen for a little transition, then cut to start screen"""
    def begin(self, gameStateObj, metaDataObj):
        self.lastUpdate = Engine.get_time()
        self.currentTime = self.lastUpdate
        if 'no_fade_to_game_over' in gameStateObj.level_constants:
            init_state = 'text_fade_in'
        else:
            init_state = 'initial_transition'
        self.GOStateMachine = CustomObjects.StateMachine(init_state)
        # Other states are text_fade_in, bg_fade_in, stasis

        self.transparency = 100
        self.backgroundCounter = 0
        Engine.music_thread.fade_in(GC.MUSICDICT[cf.CONSTANTS.get('music_game_over')])

        # Make background
        self.MovingSurf = Engine.create_surface((256, 256), transparent=True, convert=True)
        self.MovingSurf.blit(GC.IMAGESDICT['GameOverBackground'], (0, 0))
        self.MovingSurf.blit(GC.IMAGESDICT['GameOverBackground'], (0, 128))
        self.MovingSurf.blit(GC.IMAGESDICT['GameOverBackground'], (128, 0))
        self.MovingSurf.blit(GC.IMAGESDICT['GameOverBackground'], (128, 128))
        self.MovingSurf = Engine.subsurface(self.MovingSurf, (0, 0, GC.WINWIDTH, 256))

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
        s = GC.IMAGESDICT['BlackBackground'].copy()
        if self.GOStateMachine.getState() == 'initial_transition':
            alpha = 255 - int(2.55*self.transparency)
            s.fill((0, 0, 0, alpha))
        surf.blit(s, (0, 0))

        # Game Over Background
        if self.GOStateMachine.getState() in ('bg_fade_in', 'stasis'):
            GOSurf = self.MovingSurf.copy()
            # Flicker image transparent
            if self.GOStateMachine.getState() == 'bg_fade_in':
                alpha = 255 - int(2.55*self.transparency)
                Engine.fill(GOSurf, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)

            # blit moving background image
            top = -int(self.backgroundCounter)
            surf.blit(GOSurf, (0, top))
            if 256 + top < GC.WINHEIGHT:
                surf.blit(GOSurf, (0, 256+top))

        if self.GOStateMachine.getState() in ('text_fade_in', 'bg_fade_in', 'stasis'):
            TextSurf = GC.IMAGESDICT['GameOverText'].copy()
            if self.GOStateMachine.getState() == 'text_fade_in':
                alpha = 255 - int(2.55*self.transparency)
                Engine.fill(TextSurf, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)
            pos = (GC.WINWIDTH//2 - TextSurf.get_width()//2, GC.WINHEIGHT//2 - TextSurf.get_height()//2)
        
            surf.blit(TextSurf, pos)

            surf.blit(GC.IMAGESDICT['GameOverFade'], (0, 0))

        return surf

class ChapterTransitionState(StateMachine.State):
    name = 'chapter_transition'

    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.background = TransitionBackground(GC.IMAGESDICT['chapterTransitionBackground'])
        self.name = metaDataObj['name'] # Lol -- this is why some states show up as Chapter I
        self.show_map = False
        Engine.music_thread.clear()
        Engine.music_thread.fade_in(GC.MUSICDICT['Chapter Sound'], 1)
        self.CTStateMachine = CustomObjects.StateMachine('transition_in')

        self.transition_in = 0
        self.sigil_fade = 100
        self.banner_grow_x = 0
        self.banner_grow_y = 6
        self.banner_fade = 0

        self.ribbon = GC.IMAGESDICT['chapterTransitionRibbon']

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'START': # self.CTStateMachine.getState() == 'wait':
            # Alternatively
            Engine.music_thread.fade_out()
            # gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.changeState('transition_pop')

    def update(self, gameStateObj, metaDataObj):
        currentTime = Engine.get_time()
        # gameStateObj.cameraOffset.update(gameStateObj)

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
            if self.banner_grow_x >= GC.WINWIDTH:
                self.banner_grow_x = GC.WINWIDTH
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
                Engine.music_thread.fade_back()
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
        BlackTransitionSurf = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], self.transition_in)
        mapSurf.blit(BlackTransitionSurf, (0, 0))

        # Draw sigil
        sigil_outline = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['chapterTransitionSigil'], self.sigil_fade)
        sigil_middle = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['chapterTransitionSigil2'], self.sigil_fade)
        center_x = (GC.WINWIDTH//2 - sigil_outline.get_width()//2)
        center_y = (GC.WINHEIGHT//2 - sigil_outline.get_height()//2)
        mapSurf.blit(sigil_outline, (center_x + 1, center_y + 1))
        mapSurf.blit(sigil_middle, (center_x, center_y))

        # Draw Ribbon
        if self.CTStateMachine.getState() in ('ribbon_fade_in', 'wait', 'ribbon_close', 'fade_out'):
            new_ribbon = self.ribbon.copy()
            position = (GC.WINWIDTH//2 - GC.FONT['chapter_yellow'].size(self.name)[0]//2, self.ribbon.get_height()//2 - 6)
            GC.FONT['chapter_yellow'].blit(self.name, new_ribbon, position)
            new_ribbon = Engine.subsurface(new_ribbon, (0, (self.ribbon.get_height() - self.banner_grow_y)//2, self.ribbon.get_width(), self.banner_grow_y))
            mapSurf.blit(new_ribbon, (GC.WINWIDTH//2 - self.ribbon.get_width()//2, GC.WINHEIGHT//2 - new_ribbon.get_height()//2))

        # Draw Banner
        banner = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['chapterTransitionBanner'], self.banner_fade)
        banner = Engine.subsurface(banner, (0, 0, self.banner_grow_x, self.banner_grow_y))
        mapSurf.blit(banner, (GC.WINWIDTH//2 - banner.get_width()//2, GC.WINHEIGHT//2 - banner.get_height()//2))

        return mapSurf

    def end(self, gameStateObj, metaDataObj):
        gameStateObj.background = None

transition_speed = 1
transition_max = 10
class TransitionInState(StateMachine.State):
    name = 'transition_in'
    # Assumes there is a state directly under this state. Draw that state also
    def begin(self, gameStateObj, metaDataObj):
        self.background = GC.IMAGESDICT['BlackBackground']
        self.transition = 0

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.get_under_state(self).update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.get_under_state(self).draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition*12.5)
        self.transition += transition_speed
        if self.transition >= transition_max:
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionOutState(StateMachine.State):
    name = 'transition_out'
    # Assumes there is a state two under this state. Draw that state also
    # Earlier state ^
    # State to be draw
    # New State
    # This state
    
    def begin(self, gameStateObj, metaDataObj):
        self.background = GC.IMAGESDICT['BlackBackground']
        self.transition = transition_max

    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.get_under_state(self, 2).update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.get_under_state(self, 2).draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition*12.5)
        self.transition -= transition_speed
        if self.transition <= 0:
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionPopState(StateMachine.State):
    name = 'transition_pop'

    def begin(self, gameStateObj, metaDataObj):
        self.background = GC.IMAGESDICT['BlackBackground']
        self.transition = transition_max

    def update(self, gameStateObj, metaDataObj):
        # logger.debug('%s %s', self, self.transition)
        gameStateObj.stateMachine.get_under_state(self).update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.get_under_state(self).draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition*12.5)
        self.transition -= transition_speed
        if self.transition <= 0:
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionDoublePopState(TransitionPopState):
    name = 'transition_double_pop'

    # Used when you you want to transition from current state, immediately skip the state under it, and go to the state under that one
    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.get_under_state(self).draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition*12.5)
        self.transition -= transition_speed
        if self.transition <= 0:
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.back()
            gameStateObj.stateMachine.back()
        surf.blit(bb, (0, 0))
        return surf

class TransitionCleanState(TransitionOutState):
    name = 'transition_clean'
    
    # Assumes there is a state directly under this state. Draw that state also.
    def update(self, gameStateObj, metaDataObj):
        gameStateObj.stateMachine.get_under_state(self).update(gameStateObj, metaDataObj)

    def draw(self, gameStateObj, metaDataObj):
        surf = gameStateObj.stateMachine.get_under_state(self).draw(gameStateObj, metaDataObj)
        # Now draw black background
        bb = Image_Modification.flickerImageTranslucent(self.background, self.transition*12.5)
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
        while xindex < GC.WINWIDTH:
            yindex = -self.backgroundCounter
            while yindex < GC.WINHEIGHT:
                left = self.backgroundCounter if xindex < 0 else 0
                top = self.backgroundCounter if yindex < 0 else 0
                right = self.width - min(0, max(self.height, (xindex + self.width - GC.WINWIDTH))) if xindex > GC.WINWIDTH else self.width
                bottom = self.height - min(0, max(self.height, (yindex + self.height - GC.WINHEIGHT))) if yindex > GC.WINHEIGHT else self.height
                disp_surf = Engine.subsurface(self.BGSurf, (left, top, right - left, bottom - top))
                rect_left = xindex if xindex >= 0 else 0
                rect_top = yindex if yindex >= 0 else 0
                surf.blit(disp_surf, (rect_left, rect_top))
                yindex += self.height
            xindex += self.width
