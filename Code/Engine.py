#! usr/bin/env python2.7
import pygame, sys

import configuration

import logging
logger = logging.getLogger(__name__)

engine_constants = {'current_time': 0,
                    'last_time': 0,
                    'last_fps': 0}

BLEND_RGB_ADD = pygame.BLEND_RGB_ADD
BLEND_RGB_SUB = pygame.BLEND_RGB_SUB
BLEND_RGB_MULT = pygame.BLEND_RGB_MULT
BLEND_RGBA_ADD = pygame.BLEND_RGBA_ADD
BLEND_RGBA_MULT = pygame.BLEND_RGBA_MULT

# === INITIALIZING FUNCTIONS =================================================
def init():
    # pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.pre_init(44100, -16, 2, 4096)
    pygame.init()
    pygame.mixer.init()

def set_icon(icon):
    pygame.display.set_icon(icon)

def set_caption(text):
    pygame.display.set_caption(text)

def clock():
    return pygame.time.Clock()

def build_display(size):
    return pygame.display.set_mode(size)

def build_font(ttf, size):
    return pygame.font.Font(ttf, size)

def terminate():
    configuration.OPTIONS['Screen Size'] = configuration.OPTIONS['temp_Screen Size']
    configuration.write_config_file() # Write last saved options to config file
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    pygame.quit()
    sys.exit()

# === TIMING STUFF ===========================================================
def update_time():
    engine_constants['last_time'] = engine_constants['current_time']
    engine_constants['current_time'] = pygame.time.get_ticks()
    engine_constants['last_fps'] = engine_constants['current_time'] - engine_constants['last_time']
    if engine_constants['last_fps'] > 32:
        # print('Frame took too long! %s ms'%(engine_constants['last_fps']))
        logger.debug('Frame took too long! %s ms', engine_constants['last_fps'])
    
def get_time():
    return engine_constants['current_time']

def get_last_time():
    return engine_constants['last_time']

def get_true_time():
    return pygame.time.get_ticks()

def get_delta():
    return engine_constants['last_fps']

# === DRAW STUFF =============================================================
def blit(dest, source, pos=(0, 0), mask=None, blend=0):
    dest.blit(source, pos, mask, blend)
        
def create_surface(size, transparent=False, convert=False):
    if transparent:
        surf = pygame.Surface(size, pygame.SRCALPHA, 32)
        if convert:
            surf = surf.convert_alpha()
        return surf
    else:
        surf = pygame.Surface(size)
        if convert:
            surf = surf.convert()
        return surf

def copy_surface(surf):
    return surf.copy()

# assumes pygame surface
def subsurface(surf, rect):
    x, y, width, height = rect
    return surf.subsurface(x, y, width, height)

def image_load(fp, convert=False, convert_alpha=False):
    image = pygame.image.load(fp)
    if convert:
        image = image.convert()
    elif convert_alpha:
        image = image.convert_alpha()
    return image

def fill(surf, color, mask=None, blend=0):
    surf.fill(color, mask, blend)

def set_alpha(surf, alpha, rleaccel=False):
    if rleaccel:
        surf.set_alpha(alpha, pygame.RLEACCEL)
    else:
        surf.set_alpha(alpha)

def set_colorkey(surf, color, rleaccel=True):
    if rleaccel:
        surf.set_colorkey(color, pygame.RLEACCEL)
    else:
        surf.set_colorkey(color)

# === TRANSFORMTATION STUFF ==================================================
def flip_horiz(surf):
    return pygame.transform.flip(surf, 1, 0)

def flip_vert(surf):
    return pygame.transform.flip(surf, 0, 1)

def transform_scale(surf, scale):
    return pygame.transform.scale(surf, scale)

def transform_rotate(surf, degrees):
    return pygame.transform.rotate(surf, degrees)

# === EVENT STUFF ============================================================
def get_key_name(key_code):
    return pygame.key.name(key_code)

def build_event_list():
    # Get events
    eventList = [] # Clear event list
    # Only gets escape events!
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            terminate()
        if event.type == pygame.KEYUP and configuration.OPTIONS['cheat']:
            if event.key == pygame.K_ESCAPE:
                terminate()
        eventList.append(event)
    return eventList

KEYUP = pygame.KEYUP
key_map = {'w': pygame.K_w,
           'j': pygame.K_j,
           '5': pygame.K_5, 
           'u': pygame.K_u,
           'p': pygame.K_p,
           'l': pygame.K_l,
           'e': pygame.K_e,
           't': pygame.K_t,
           'd': pygame.K_d}

# === SOUND STUFF =====================================================
class BaseSound():
    def play(self, loops=0, maxtime=0, fade_ms=0):
        pass

    def stop():
        pass

    def fadeout(time):
        pass

    def set_volume(value):
        pass

    def get_volume():
        pass

def create_sound(fp):
    return pygame.mixer.Sound(fp)

# === MUSIC STUFF =====================================================
class Song(object):
    def __init__(self, song, num_plays=-1, time=0):
        self.song = song
        self.num_plays = num_plays
        self.current_time = time

        if self.song.endswith('- Start.ogg'):
            self.loop = self.song[:-11] + '- Loop.ogg'
        else:
            self.loop = None

    def swap(self):
        self.song = self.loop[:]
        self.loop = None

class MusicThread(object):
    def __init__(self):
        self.song_stack = []
        self.volume = 1.0

        self.fade_out_time = 200
        self.fade_out_update = 0

        self.state = 'normal'

        self.end_song = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.end_song)

        self.current = None
        self.next = None

        self.debug = 0

    def clear(self):
        self.song_stack = []
        self.state = "normal"

    def pause(self):
        pygame.mixer.music.pause()

    def resume(self):
        pygame.mixer.music.unpause()

    def set_volume(self, volume):
        self.volume = volume
        pygame.mixer.music.set_volume(self.volume)
    
    def fade_to_normal(self, gameStateObj, metaDataObj):
        logger.info('Music: Fade to Normal')
        phase_name = gameStateObj.statedict['phases'][gameStateObj.statedict['current_phase']].name
        if phase_name == 'player':
            self.fade_in(metaDataObj['playerPhaseMusic'])
        elif phase_name.startswith('enemy'):
            self.fade_in(metaDataObj['enemyPhaseMusic'])
        elif phase_name == 'other':
            self.fade_in(metaDataObj['otherPhaseMusic'])
        else:
            logging.error('Unsupported phase name: %s', phase_name)
        # self.music_stack = [] # Clear the stack

    def fade_in(self, next, num_plays=-1, time=0):
        logger.info('Music: Fade in')
        # Confirm thats its not already at the top of the stack
        if self.song_stack and self.song_stack[-1].song == next:
            logger.info('Music: Already Present')
            return
        # Determine if song is in stack
        for song in self.song_stack:
            # If so, move to top of stack
            if song.song == next:
                logger.info('Music: Pull Up')
                self.song_stack.remove(song)
                self.song_stack.append(song)
                break
        else:
            logger.info('Music: New')
            new_song = Song(next, num_plays, time)
            self.song_stack.append(new_song)

        # Update the current one -- so we know where to head back to
        if self.current:
            self.current.current_time += pygame.mixer.music.get_pos()/1000

        # This is where we are going to
        self.next = self.song_stack[-1]

        # Start fade out process
        self.state = 'fade' # Now we know to fade to next index
        pygame.mixer.music.fadeout(self.fade_out_time)
        self.fade_out_update = get_time()

    def fade_back(self):
        logger.info('Music: Fade back')
        # Confirm that there is something to pop
        if not self.song_stack:
            return
        self.song_stack.pop()

        self.next = self.song_stack[-1]

        # Start fade out process
        self.state = 'fade' # Now we know to fade to next index
        pygame.mixer.music.fadeout(self.fade_out_time)
        self.fade_out_update = get_time()

    def fade_out(self, time=400):
        pygame.mixer.music.fadeout(time)

    def stop(self):
        pygame.mixer.music.stop()

    def update(self, eventList):
        current_time = get_time()
        """
        if not pygame.mixer.music.get_busy():
            if self.debug:
                print(current_time - self.debug)
            print('Music not playing!')
            self.debug = 0
        elif not self.debug:
            print('--')
            self.debug = current_time
        """
        # logger.debug(current_time)

        # === Take Input
        for event in eventList:
            if event.type == self.end_song:
                if self.state == 'normal':
                    logger.debug('Music: Normal Event')
                    if self.current.loop:
                        self.current.swap()
                        pygame.mixer.music.load(self.current.song)
                        pygame.mixer.music.play(0)
                    elif self.current.num_plays == -1:
                        pygame.mixer.music.play(0)
                    self.current.current_time = 0
                elif self.state == 'fade':
                    logger.debug('Music: Fade Event')
                    self.state = 'normal' # catches the stop from fade

        # === Update
        if self.state == 'normal':
            pass

        elif self.state == 'fade':
            if current_time - self.fade_out_update > self.fade_out_time:
                logger.debug('Music: Actual Fade in!')
                self.current = self.next
                if pygame.mixer.music.get_busy():
                    self.fade_out_update = current_time
                # self.next = None
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.current.song)
                pygame.mixer.music.play(0, self.current.current_time)
                # self.fade_out_update = current_time
                # self.state = 'normal'

music_thread = MusicThread()
