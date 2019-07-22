#! usr/bin/env python2.7
PYGAME_SDL2 = False
if PYGAME_SDL2:
    import pygame_sdl2
    pygame_sdl2.import_as_pygame()
import pygame
import sys

from . import configuration

import logging
logger = logging.getLogger(__name__)

engine_constants = {'current_time': 0,
                    'last_time': 0,
                    'last_fps': 0,
                    'home': './'}

BLEND_RGB_ADD = pygame.BLEND_RGB_ADD
BLEND_RGB_SUB = pygame.BLEND_RGB_SUB
BLEND_RGB_MULT = pygame.BLEND_RGB_MULT
BLEND_RGBA_ADD = pygame.BLEND_RGBA_ADD
BLEND_RGBA_SUB = pygame.BLEND_RGBA_SUB
BLEND_RGBA_MULT = pygame.BLEND_RGBA_MULT

# === INITIALIZING FUNCTIONS =================================================
def init():
    # pygame.mixer.pre_init(44100, -16, 1, 512)
    if not PYGAME_SDL2:
        pygame.mixer.pre_init(44100, -16, 2, 256 * 2**configuration.OPTIONS['Sound Buffer Size'])
    pygame.init()
    if not PYGAME_SDL2:
        pygame.mixer.init()

def simple_init():
    pygame.init()

def set_icon(icon):
    pygame.display.set_icon(icon)

def set_caption(text):
    pygame.display.set_caption(text)

def clock():
    return pygame.time.Clock()

def build_display(size):
    return pygame.display.set_mode(size)

def push_display(surf, size, new_surf):
    pygame.transform.scale(surf, size, new_surf)

def update_display():
    pygame.display.update()

def remove_display():
    pygame.display.quit()

def build_font(ttf, size):
    if PYGAME_SDL2:
        size += 2
    return pygame.font.Font(ttf, size)

def terminate(crash=False):
    final(crash)
    if not PYGAME_SDL2:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    pygame.quit()
    sys.exit()

def final(crash=False):
    if 'temp_Screen Size' in configuration.OPTIONS:
        configuration.OPTIONS['Screen Size'] = configuration.OPTIONS['temp_Screen Size']
    configuration.write_config_file() # Write last saved options to config file
    if crash:
        create_crash_save()

def create_crash_save():
    import os, glob
    from shutil import copyfile
    # Get newest *.pmeta file in Saves/
    save_metas = glob.glob(engine_constants['home'] + 'Saves/*.pmeta')
    if not save_metas:
        return
    latest_file = max(save_metas, key=os.path.getmtime)
    pmeta_name = os.path.split(latest_file)[1]
    # If newest *.pmeta file is not called SaveState* or Suspend* or Restart*
    if not (pmeta_name.startswith('SaveState') or pmeta_name.startswith('Suspend') or pmeta_name.startswith('Restart')):
        # Copy newest *.p and *.pmeta file and call them Suspend.p and Suspend.pmeta
        p_file = latest_file[:-6] + '.p'
        copyfile(p_file, engine_constants['home'] + 'Saves/Suspend.p')
        copyfile(latest_file, engine_constants['home'] + 'Saves/Suspend.pmeta')
        print('\nCreated save point at last turn change! Select Continue in Main Menu to load!\n')
        logger.debug('Created save point from %s', p_file)

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

def save_surface(surf, fn):
    pygame.image.save(surf, fn)

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

# === CONTROLS STUFF =========================================================
QUIT = pygame.QUIT
KEYUP = pygame.KEYUP
KEYDOWN = pygame.KEYDOWN
key_map = {'d': pygame.K_d,
           'enter': pygame.K_RETURN,
           'backspace': pygame.K_BACKSPACE,
           'up': pygame.K_UP,
           'ctrl': pygame.K_LCTRL}

def get_pressed():
    return pygame.key.get_pressed()

def joystick_avail():
    return pygame.joystick.get_count()

def get_joystick():
    return pygame.joystick.Joystick(0)
    
# === SOUND STUFF ============================================================
class BaseSound():
    def play(self, loops=0, maxtime=0, fade_ms=0):
        pass

    def stop(self):
        pass

    def fadeout(self, time):
        pass

    def set_volume(self, value):
        pass

    def get_volume(self):
        pass

def create_sound(fp):
    return pygame.mixer.Sound(fp)

# === MUSIC STUFF =====================================================
class Song(object):
    def __init__(self, name, num_plays=-1, time=0):
        self.name = name
        self.num_plays = num_plays
        self.current_time = time

        if self.name.endswith('- Start.ogg'):
            self.loop = self.name[:-11] + '- Loop.ogg'
        else:
            self.loop = None

    def swap(self):
        logger.info('Music: Swap to Loop')
        self.name = self.loop[:]
        self.loop = None

    def is_same_song(self, name):
        name = name.replace('- Start.ogg', '').replace('- Loop.ogg', '')
        my_name = self.name.replace('- Start.ogg', '').replace('- Loop.ogg', '')
        return name == my_name

class NoMusicThread(object):
    def __init__(self):
        pass
    def clear(self):
        pass
    def pause(self):
        pass
    def resume(self):
        pass
    def mute(self):
        pass
    def lower(self):
        pass
    def unmute(self):
        pass
    def get_volume(self):
        return 0
    def set_volume(self, volume):
        pass
    def fade_to_normal(self, gameStateObj):
        pass
    def fade_in(self, next, num_plays=-1, time=0):
        pass
    def fade_back(self):
        pass
    def fade_out(self):
        pass
    def stop(self):
        pass
    def update(self, eventList):
        pass

class MusicThread(object):
    def __init__(self):
        self.song_stack = []
        self.volume = 1.0

        self.fade_out_time = 400
        self.fade_out_update = 0

        self.state = 'normal'

        self.end_song_event = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.end_song_event)

        self.current_song = None
        self.next_song = None

        self.debug = 0

    # Does not actually stop the current music from playing, just clears the stack
    def clear(self):
        self.song_stack = []
        self.state = "normal"

    def pause(self):
        pygame.mixer.music.pause()

    def resume(self):
        pygame.mixer.music.unpause()

    def mute(self):
        pygame.mixer.music.set_volume(0)

    def lower(self):
        pygame.mixer.music.set_volume(0.25*self.volume)

    def unmute(self):
        pygame.mixer.music.set_volume(self.volume)

    def get_volume(self):
        return self.volume

    def set_volume(self, volume):
        self.volume = volume
        pygame.mixer.music.set_volume(self.volume)
    
    def fade_to_normal(self, gameStateObj):
        logger.info('Music: Fade to Normal')
        phase_name = gameStateObj.phase.get_current_phase()
        self.fade_in(gameStateObj.phase_music.get_phase_music(phase_name))

    def fade_in(self, next_song, num_plays=-1, time=0):
        if not next_song:
            logger.info('Music: Song does not exist')
            return
        logger.info('Music: Fade in')
        # Confirm thats its not already at the top of the stack
        if self.song_stack and self.song_stack[-1].is_same_song(next_song):
            logger.info('Music: Already Present')
            return
        # Determine if song is in stack
        for song in self.song_stack:
            # If so, move to top of stack
            if song.is_same_song(next_song):
                logger.info('Music: Pull Up')
                self.song_stack.remove(song)
                self.song_stack.append(song)
                break
        else:
            logger.info('Music: Next Song %s', next_song)
            if next_song:
                new_song = Song(next_song, num_plays, time)
                self.song_stack.append(new_song)

        # Update the current one -- so we know where to head back to
        if self.current_song:
            self.current_song.current_time += pygame.mixer.music.get_pos()

        # This is where we are going to
        if self.song_stack:
            self.next_song = self.song_stack[-1]
        else:
            self.next_song = None
        logger.info('Music: Next Song %s', self.next_song)

        # Start fade out process
        if self.state == 'fade_out':
            pass  # Just piggyback off other fade_out
        else:
            self.fade_out()

    def fade_back(self):
        logger.info('Music: Fade back')
        # Confirm that there is something to pop
        if not self.song_stack:
            return
        self.song_stack.pop()

        if self.song_stack:
            self.next_song = self.song_stack[-1]
        else:
            self.next_song = None

        # Start fade out process
        if self.state == 'fade_out':
            pass  # Just piggyback off other fade_out
        else:
            self.fade_out()

    def fade_out(self):
        self.state = 'fade_out'
        pygame.mixer.music.fadeout(self.fade_out_time)
        self.fade_out_update = get_time()

    def stop(self):
        if self.current_song:
            self.current_song.current_time += pygame.mixer.music.get_pos()
            self.current_song = None
        pygame.mixer.music.stop()

    def update(self, eventList):
        current_time = get_time()

        # === Catching events
        for event in eventList:
            # If the current song has ended...
            if event.type == self.end_song_event:
                if self.state == 'normal':
                    logger.debug('Music: Song End Event')
                    if self.current_song:
                        if self.current_song.loop:
                            self.current_song.swap()
                            pygame.mixer.music.load(self.current_song.name)
                            pygame.mixer.music.play(0)
                        elif self.current_song.num_plays == -1:
                            pygame.mixer.music.play(0)
                        elif self.current_song.num_plays >= 0:
                            self.current_song.num_plays -= 1
                        self.current_song.current_time = 0
                        if self.current_song.num_plays == 0:
                            self.stop()
                            self.fade_back()
                elif self.state == 'fade_catch':
                    logger.debug('Music: Fade Catch Event')
                    self.state = 'normal' # catches the stop from fade and returns to normal

        # === Update
        if self.state == 'fade_out':
            if current_time - self.fade_out_update > self.fade_out_time:
                logger.debug('Music: Actual Fade in!')
                self.current_song = self.next_song
                if self.current_song:
                    if pygame.mixer.music.get_busy():  # Catching double fade outs?
                        self.fade_out_update = current_time

                    pygame.mixer.music.set_volume(self.volume)
                    pygame.mixer.music.stop()
                    # This takes 50 ms or so each time :(
                    pygame.mixer.music.load(self.current_song.name)
                    pygame.mixer.music.play(0, self.current_song.current_time/1000)

                    self.state = 'fade_catch'  # The above action will cause an event. Catch it...
                else:
                    self.state = 'normal'

        # If there's no music currently playing, make it so that music does play
        if self.current_song and not pygame.mixer.music.get_busy():
            logger.debug('Music: Music not playing!')
            if self.current_song.loop:
                self.current_song.swap()
            pygame.mixer.music.load(self.current_song.name)
            pygame.mixer.music.play(0)

if PYGAME_SDL2:
    music_thread = NoMusicThread()
else:
    music_thread = MusicThread()
