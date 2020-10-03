import os, pickle, math

from . import GlobalConstants as GC
from . import configuration as cf
from . import Utility, Image_Modification, Engine
from . import Action

import logging
logger = logging.getLogger(__name__)

# === Simple Finite State Machine Object ===============================
class StateMachine(object):
    def __init__(self, startingstate):
        self.state = []
        self.state.append(startingstate)
        self.state_log = []

    def changeState(self, newstate):
        self.state.append(newstate)

    def back(self):
        self.state.pop()

    def getState(self):
        if self.state:
            return self.state[-1]
        return None

    def clear(self):
        self.state = []

    # Keeps track of the state at every tick
    def update(self):
        self.state_log.append(self.getState())

# === GENERIC ANIMATION OBJECT ===================================
# for miss and no damage animations
class Animation(object):
    def __init__(self, sprite, position, frames, total_num_frames=None, animation_speed=75,
                 loop=False, hold=False, ignore_map=False, start_time=0, on=True, set_timing=None):
        self.sprite = sprite
        self.position = position
        self.frame_x = frames[0]
        self.frame_y = frames[1]
        self.total_num_frames = total_num_frames if total_num_frames else self.frame_x * self.frame_y
        self.frameCount = 0
        self.animation_speed = animation_speed
        self.loop = loop
        self.hold = hold
        self.start_time = start_time
        self.on = on
        self.tint = False
        self.ignore_map = ignore_map # Whether the position of the Animation sould be relative to the map
        self.lastUpdate = Engine.get_time()

        self.set_timing = set_timing
        if self.set_timing:
            assert len([timing for timing in self.set_timing if timing > 0]) == self.total_num_frames, \
                '%s %s'%(len(self.set_timing), len(self.total_num_frames))
        self.timing_count = -1

        self.indiv_width, self.indiv_height = self.sprite.get_width()//self.frame_x, self.sprite.get_height()//self.frame_y

        self.image = Engine.subsurface(self.sprite, (0, 0, self.indiv_width, self.indiv_height))

    def draw(self, surf, gameStateObj=None, blend=None):
        if self.on and self.frameCount >= 0 and Engine.get_time() > self.start_time:
            # The animation is too far to the right. Must move left. (" - 32")
            image = self.image
            x, y = self.position
            if self.ignore_map:
                topleft = x, y
            else:
                topleft = (x-gameStateObj.cameraOffset.x-1)*GC.TILEWIDTH, (y-gameStateObj.cameraOffset.y)*GC.TILEHEIGHT
            if blend:
                image = Image_Modification.change_image_color(image, blend)
            if self.tint:
                Engine.blit(surf, image, topleft, image.get_rect(), Engine.BLEND_RGB_ADD)
            else:
                surf.blit(image, topleft)

    def update(self, gameStateObj=None):
        currentTime = Engine.get_time()
        if self.on and currentTime > self.start_time:
            # If this animation has every frame's count defined
            if self.set_timing:
                num_frames = self.set_timing[self.frameCount]
                # If you get a -1 on set timing, switch to blend tint
                while num_frames < 0:
                    self.tint = not self.tint 
                    self.frameCount += 1
                    num_frames = self.set_timing[self.frameCount]
                self.timing_count += 1
                if self.timing_count >= num_frames:
                    self.timing_count = 0
                    self.frameCount += 1
                    if self.frameCount >= self.total_num_frames:
                        if self.loop:
                            self.frameCount = 0
                        elif self.hold:
                            self.frameCount = self.total_num_frames - 1
                        else:
                            if gameStateObj and self in gameStateObj.allanimations:
                                gameStateObj.allanimations.remove(self)
                            return True
                    if self.frameCount >= 0:
                        rect = (self.frameCount%self.frame_x * self.indiv_width, self.frameCount//self.frame_x * self.indiv_height, 
                                self.indiv_width, self.indiv_height)
                        self.image = Engine.subsurface(self.sprite, rect)
            # Otherwise
            elif currentTime - self.lastUpdate > self.animation_speed:
                self.frameCount += int((currentTime - self.lastUpdate)//self.animation_speed) # 1
                self.lastUpdate = currentTime
                if self.frameCount >= self.total_num_frames:
                    if self.loop: # Reset framecount
                        self.frameCount = 0
                    elif self.hold:
                        self.frameCount = self.total_num_frames - 1 # Hold on last frame
                    else:
                        if gameStateObj and self in gameStateObj.allanimations:
                            gameStateObj.allanimations.remove(self)
                        return True
                if self.frameCount >= 0:
                    rect = (self.frameCount%self.frame_x * self.indiv_width, self.frameCount//self.frame_x * self.indiv_height, 
                            self.indiv_width, self.indiv_height)
                    self.image = Engine.subsurface(self.sprite, rect)

# === PHASE OBJECT ============================================================
class Phase(object):
    def __init__(self, gameStateObj):
        self.phase_in = []
        self.phase_in.append(PhaseIn('player', 'PlayerTurnBanner'))
        self.phase_in.append(PhaseIn('enemy', 'EnemyTurnBanner'))
        self.phase_in.append(PhaseIn('enemy2', 'Enemy2TurnBanner'))
        self.phase_in.append(PhaseIn('other', 'OtherTurnBanner'))
        self.order = ('player', 'enemy', 'enemy2', 'other')

        self.current = 3 if gameStateObj.turncount == 0 else 0
        self.previous = 0

    def get_current_phase(self):
        return self.order[self.current]

    def get_previous_phase(self):
        return self.order[self.previous]

    def _next(self):
        self.current += 1
        if self.current >= len(self.order):
            self.current = 0

    def _prev(self):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.order) - 1

    def next(self, gameStateObj):
        self.previous = self.current
        # Actually change phase
        if gameStateObj.allunits:
            Action.do(Action.ChangePhase(), gameStateObj)
            while not any(self.get_current_phase() == unit.team for unit in gameStateObj.allunits if unit.position) \
                    and self.current != 0: # Also, never skip player phase
                Action.do(Action.ChangePhase(), gameStateObj)
        else:
            self.current = 0 # If no units at all, just default to player phase?

    def slide_in(self, gameStateObj):
        self.phase_in[self.current].begin(gameStateObj)

    def update(self):
        return self.phase_in[self.current].update()

    def draw(self, surf):
        self.phase_in[self.current].draw(surf)

class PhaseIn(object):
    def __init__(self, name, spritename):
        self.name = name
        self.spritename = spritename
        self.loadSprites()
        self.begin_time = 128
        self.main_time = 1000
        self.end_time = 240
        self.display_time = self.begin_time + self.main_time + self.end_time
        self.topleft = ((GC.WINWIDTH - self.image.get_width())//2, (GC.WINHEIGHT - self.image.get_height())//2)
        self.start_time = None # Don't define it here. Define it at first update

    def loadSprites(self):
        self.image = GC.IMAGESDICT[self.spritename]
        self.transition = GC.IMAGESDICT['PhaseTransition'] # The Black Squares that happen during a phase transition
        self.transition_space = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT//2 - 16), transparent=True)

    def removeSprites(self):
        self.image = None
        self.transition = None

    def update(self):
        if Engine.get_time() - self.start_time >= self.display_time:
            return True
        else:
            return False

    def begin(self, gameStateObj):
        currentTime = Engine.get_time()
        GC.SOUNDDICT['Next Turn'].play()
        if self.name == 'player':
            # # Keeps track of where units started their turns (mainly)
            # for unit in gameStateObj.allunits:
            #     unit.previous_position = unit.position

            # Set position over leader lord
            if cf.OPTIONS['Autocursor']:
                gameStateObj.cursor.autocursor(gameStateObj)
            else: # Set position to where it was when we ended turn
                gameStateObj.cursor.setPosition(gameStateObj.statedict['previous_cursor_position'], gameStateObj)
        self.start_time = currentTime

    def draw(self, surf):
        currentTime = Engine.get_time()
        time_passed = min(currentTime - self.start_time, self.display_time)
        if cf.OPTIONS['debug'] and time_passed < 0:
            logger.error('This phase has a negative time_passed! %s %s %s', time_passed, currentTime, self.start_time)
        max_opaque = 118

        # Blit the banner
        # position
        if time_passed < self.begin_time:
            diff = time_passed / float(self.begin_time)
            offset = self.topleft[0] + self.begin_time * (1 - diff)
            trans = 100. * (1 - diff) ** 2
        elif time_passed < self.begin_time + self.main_time:
            offset = self.topleft[0]
            trans = 0
        else:  # 367 milliseconds
            diff = (time_passed - (self.begin_time + self.main_time)) / float(self.end_time)
            offset = self.topleft[0] - self.end_time * diff
            trans = 100. * diff ** 2

        # transparency
        image = Image_Modification.flickerImageTranslucent(self.image.copy(), trans)
        surf.blit(image, (offset, self.topleft[1]))

        transition_space1 = self.transition_space.copy()
        transition_space2 = self.transition_space.copy()

        # === Handle the transition
        half_display_time = self.display_time//2
        if time_passed < half_display_time:
            diff = time_passed/float(half_display_time)
            height = (GC.WINHEIGHT//2 - 16) * diff    
            alpha = int(max_opaque * math.sqrt(time_passed/float(half_display_time)))
        else:
            diff = -(half_display_time - time_passed)/float(half_display_time)
            height = (GC.WINHEIGHT//2 - 16) * (1 - diff)
            alpha = int(max_opaque - max_opaque*((time_passed - half_display_time)/float(half_display_time))**2)
            alpha = Utility.clamp(alpha, 0, 255)

        if time_passed < half_display_time:
            t = int(2 + diff*16)  # Starts a little ways along at the beginning
        else:
            t = int(diff*16)

        for x in range(0, GC.WINWIDTH, 16):
            for y in range(0, 64, 16):
                i, j = x/16, y/16
                k = int(t*1.5 - (i - j%2)/2 + j/2 - 4)
                if time_passed < half_display_time:
                    frame = Utility.clamp(8 - abs(max(k, 8) - 8), 0, 8)
                else:
                    frame = Utility.clamp(k, 0, 8)
                # frame = Utility.clamp(min(k, 8) + min(8 - k, 0), 0, 8)                
                square_surf = Engine.subsurface(self.transition, (frame*16, 0, 16, 16)).copy()
                transition_space1.blit(square_surf, (x, y))

        for x in range(0, GC.WINWIDTH, 16):
            for y in range(0, 64, 16):
                i, j = x/16, y/16
                k = int(t*1.5 - (i - j%2)/2 + j/2 - 1)
                if time_passed < half_display_time:
                    frame = Utility.clamp(8 - abs(max(k, 8) - 8), 0, 8)
                else:
                    frame = Utility.clamp(k, 0, 8)
                # frame = Utility.clamp(min(k, 8) + min(8 - k, 0), 0, 8)
                square_surf = Engine.subsurface(self.transition, (frame*16, 0, 16, 16)).copy()
                transition_space2.blit(square_surf, (x, y))

        # height = 64  # remove later
        transition_space1 = Engine.subsurface(transition_space1, (0, 0, GC.WINWIDTH, height))
        transition_space2 = Engine.subsurface(transition_space2, (0, self.transition_space.get_height() - height, GC.WINWIDTH, height))

        # Fill with correct alpha
        # alpha = 255  # Remove later
        Engine.fill(transition_space1, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)
        Engine.fill(transition_space2, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)
        # Now blit transition space
        surf.blit(transition_space1, (0, 0))
        # Other transition_space
        surf.blit(transition_space2, (0, GC.WINHEIGHT - transition_space2.get_height()))

# === SAVESLOTS ===============================================================
class SaveSlot(object):
    def __init__(self, metadata_fp, number):
        self.no_name = '--NO DATA--'
        self.name = self.no_name
        self.playtime = 0
        self.realtime = 0
        self.kind = None # Prep, Base, Suspend, Battle, Start
        self.mode_id = 1
        self.number = number

        self.metadata_fp = metadata_fp
        self.true_fp = metadata_fp[:-4]

        self.read()

    def read(self):
        try:
            if os.path.exists(self.metadata_fp):
                with open(self.metadata_fp, 'rb') as loadFile:
                    save_metadata = pickle.load(loadFile)
                self.name = save_metadata['name']
                self.playtime = save_metadata['playtime']
                self.realtime = save_metadata['realtime']
                self.kind = save_metadata['kind']
                self.mode_id = int(save_metadata.get('mode_id', 1))
                if self.number is None:
                    self.number = save_metadata['save_slot']

        except ValueError as e:
            print('***Value Error: %s' % (e))
        except ImportError as e:
            print('***Import Error: %s' % (e))
        except TypeError as e:
            print('***Type Error: %s' % (e))
        except KeyError as e:
            print('***Key Error: %s' % (e))
        except IOError as e:
            print('***IO Error: %s' % (e))

    def get_name(self):
        return self.name + (' - ' + self.kind if self.kind else '')

    def loadGame(self):
        with open(self.true_fp, 'rb') as loadFile:
            saveObj = pickle.load(loadFile)
        return saveObj

# === MAPSELECTHELPER =========================================================
class MapSelectHelper(object):
    def __init__(self, pos_list):
        self.pos_list = pos_list

    # For a given position, determine which position in self.pos_list is closest
    def get_closest(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            dist = Utility.calculate_distance(pos, position)
            if dist < min_distance:
                closest = pos
                min_distance = dist
        return closest

    # For a given position, determine which position in self.pos_list is the closest position in the downward direction
    def get_down(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[1] > position[1]: # If further down than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_up(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[1] < position[1]: # If further up than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_right(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[0] > position[0]: # If further right than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_left(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[0] < position[0]: # If further left than the position
                dist = Utility.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

class CameraOffset(object):
    def __init__(self, x, y):
        # Where the camera is supposed to be
        self.x = x
        self.y = y
        # Where the camera actually is
        self.current_x = x
        self.current_y = y

        self.speed = 8.0 # Linear. 

        self.pan_flag = False
        self.pan_to = []

    def set_x(self, x):
        self.x = x

    def set_y(self, y):
        self.y = y

    def force_x(self, x):
        self.current_x = self.x = x

    def force_y(self, y):
        self.current_y = self.y = y

    def set_xy(self, x, y):
        self.x = x
        self.y = y

    def get_xy(self):
        return (self.current_x, self.current_y)

    def get_x(self):
        return self.current_x

    def get_y(self):
        return self.current_y

    def back_pressed(self, val):
        if val:
            self.speed = 4.0
        else:
            self.speed = 8.0

    def center2(self, old, new):
        x1, y1 = old
        x2, y2 = new
        # logger.debug('Camera Center: %s %s %s %s', (x1, y1), (x2, y2), self.x, self.y)
        max_x = max(x1, x2)
        max_y = max(y1, y2)
        min_x = min(x1, x2)
        min_y = min(y1, y2)

        if self.x > min_x - 4 or self.x + GC.TILEX < max_x + 4 or self.y > min_y - 3 or self.y + GC.TILEY < max_y + 3:
            self.x = (max_x + min_x)//2 - GC.TILEX//2
            self.y = (max_y + min_y)//2 - GC.TILEY//2
        
        # logger.debug('New Camera: %s %s', self.x, self.y)

    def check_loc(self):
        # logger.debug('Camera %s %s %s %s', self.current_x, self.current_y, self.x, self.y)
        if not self.pan_to and self.current_x == self.x and self.current_y == self.y:
            self.pan_flag = False
            return True
        return False

    def map_pan(self, tile_map, cursor_pos):
        corners = [(0, 0), (0, tile_map.height - 1), (tile_map.width - 1, tile_map.height - 1), (tile_map.width - 1, 0)]
        distance = [Utility.calculate_distance(cursor_pos, corner) for corner in corners]
        closest_corner, idx = min((val, idx) for (idx, val) in enumerate(distance))
        # print(self.current_x, self.current_y)
        # print(corners, distance, closest_corner, idx)
        self.pan_to = corners[idx:] + corners[:idx]
        # print(self.pan_to)

    def set_travel_limits(self, tilemap):
        if self.x < 0:
            self.set_x(0)
        if self.y < 0:
            self.set_y(0)
        if self.x > (tilemap.width - GC.TILEX): # Need this minus to account for size of screen
            self.set_x(tilemap.width - GC.TILEX)
        if self.y > (tilemap.height - GC.TILEY):
            self.set_y(tilemap.height - GC.TILEY)

    def set_limits(self, tilemap):
        if self.current_x < 0:
            self.current_x = 0
        elif self.current_x > (tilemap.width - GC.TILEX): # Need this minus to account for size of screen
            self.current_x = (tilemap.width - GC.TILEX)
        if self.current_y < 0:
            self.current_y = 0
        elif self.current_y > (tilemap.height - GC.TILEY):
            self.current_y = (tilemap.height - GC.TILEY)
        
    def update(self, gameStateObj):
        if gameStateObj.map:
            self.set_travel_limits(gameStateObj.map)
        if self.current_x != self.x:
            if self.current_x > self.x:
                self.current_x -= 0.125 if self.pan_flag else min(2, (self.current_x - self.x)/self.speed)
            elif self.current_x < self.x:
                self.current_x += 0.125 if self.pan_flag else min(2, (self.x - self.current_x)/self.speed)
        if self.current_y != self.y:
            if self.current_y > self.y:
                self.current_y -= 0.125 if self.pan_flag else min(2, (self.current_y - self.y)/self.speed)
            elif self.current_y < self.y:
                self.current_y += 0.125 if self.pan_flag else min(2, (self.y - self.current_y)/self.speed)
        # If they are close enough, make them so.
        if abs(self.current_x - self.x) <= 0.25:
            self.current_x = self.x
        if abs(self.current_y - self.y) <= 0.25:
            self.current_y = self.y
        # Move to next place on the list
        if self.pan_to and self.current_y == self.y and self.current_x == self.x:
            self.x, self.y = self.pan_to.pop()

        # Make sure current_x and current_y do not go off screen
        if gameStateObj.map:
            self.set_limits(gameStateObj.map)
        # logger.debug('Camera %s %s %s %s', self.current_x, self.current_y, self.x, self.y)

class PhaseMusic(object):
    def __init__(self, player, enemy, other=None, player_battle=None, enemy_battle=None):
        self.player_name = player
        self.enemy_name = enemy
        self.other_name = other
        self.player_battle_name = player_battle
        self.enemy_battle_name = enemy_battle
        self.player_music = GC.MUSICDICT.get(self.player_name)
        self.enemy_music = GC.MUSICDICT.get(self.enemy_name)
        self.other_music = GC.MUSICDICT.get(self.other_name)
        self.player_battle_music = GC.MUSICDICT.get(self.player_battle_name)
        self.enemy_battle_music = GC.MUSICDICT.get(self.enemy_battle_name)

    def get_phase_music(self, phase_name):
        if phase_name == 'player':
            return self.player_music
        elif phase_name.startswith('enemy'):
            return self.enemy_music
        elif phase_name == 'other':
            return self.other_music
        else:
            logging.error('Unsupported phase name: %s', phase_name)
            return None

    def serialize(self):
        return (self.player_name, self.enemy_name, self.other_name, self.player_battle_name, self.enemy_battle_name)

    @classmethod
    def deserialize(cls, info):
        return cls(*info)

    def change_music(self, phase_name, music_name):
        if music_name != 'None' and music_name not in GC.MUSICDICT:
            logging.error('Music %s not in GC.MUSICDICT', music_name)
            return None
        if phase_name == 'player':
            self.player_name = music_name
            self.player_music = GC.MUSICDICT.get(music_name)
        elif phase_name == 'enemy' or phase_name == 'enemy2':
            self.enemy_name = music_name
            self.enemy_music = GC.MUSICDICT.get(music_name)
        elif phase_name == 'other':
            self.other_name = music_name
            self.other_music = GC.MUSICDICT.get(music_name)
        elif phase_name == 'player_battle':
            self.player_battle_name = music_name
            self.player_battle_music = GC.MUSICDICT.get(music_name)
        elif phase_name == 'enemy_battle' or phase_name == 'enemy2_battle':
            self.enemy_battle_name = music_name
            self.enemy_battle_music = GC.MUSICDICT.get(music_name)           
        else:
            logging.error('Unsupported phase name: %s', phase_name)
            return None        

# === HANDLES PRESSING INFO AND APPLYING HELP MENU ===========================
def handle_info_key(gameStateObj, metaDataObj, chosen_unit=None, one_unit_only=False, scroll_units=None, no_movement=False):
    gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.getHoveredUnit(gameStateObj)
    if chosen_unit:
        my_unit = chosen_unit
    elif gameStateObj.cursor.currentHoveredUnit:
        my_unit = gameStateObj.cursor.currentHoveredUnit
    else:
        return
    GC.SOUNDDICT['Select 1'].play()
    gameStateObj.info_menu_struct['one_unit_only'] = one_unit_only
    gameStateObj.info_menu_struct['scroll_units'] = scroll_units
    gameStateObj.info_menu_struct['chosen_unit'] = my_unit
    gameStateObj.info_menu_struct['no_movement'] = no_movement
    gameStateObj.stateMachine.changeState('info_menu')
    gameStateObj.stateMachine.changeState('transition_out')

# === HANDLES PRESSING AUX ===================================================
def handle_aux_key(gameStateObj):
    avail_units = [unit.position for unit in gameStateObj.allunits if unit.team == 'player' and unit.position and not unit.isDone()]
    if avail_units:
        if handle_aux_key.counter > len(avail_units) - 1:
            handle_aux_key.counter = 0
        pos = avail_units[handle_aux_key.counter]
        GC.SOUNDDICT['Select 4'].play()
        gameStateObj.cursor.setPosition(pos, gameStateObj)

        # Increment counter
        handle_aux_key.counter += 1
# Initialize counter
handle_aux_key.counter = 0

class LevelStatistic(object):
    def __init__(self, gameStateObj, metaDataObj):
        self.name = metaDataObj['name']
        self.turncount = gameStateObj.turncount
        self.stats = self.get_records(gameStateObj)

    def get_records(self, gameStateObj):
        records = {}
        for unit in gameStateObj.allunits:
            if unit.team == 'player' and not unit.generic_flag:
                records[unit.name] = unit.records
        return records

    @staticmethod
    def formula(record):
        return record['kills']*cf.CONSTANTS['kill_worth'] + record['damage'] + record['healing']

    def get_mvp(self):
        tp = 0
        current_mvp = 'Ophie'
        for unit, record in self.stats.items():
            test = self.formula(record)
            if test > tp:
                tp = test
                current_mvp = unit 

        return current_mvp
