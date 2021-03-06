#                           __       __________   ___    
#                          |  |     |   ____\  \ /  /    
#                          |  |     |  |__   \  V  /     
#                          |  |     |   __|   >   <       
#                          |  `----.|  |____ /  .  \        
#                          |_______||_______/__/ \__\          
# .___________.    ___       __       __    ______   .__   __.  __       _______.                                                                                                             
# |           |   /   \     |  |     |  |  /  __  \  |  \ |  | |  |     /       |
# `---|  |----`  /  ^  \    |  |     |  | |  |  |  | |   \|  | |  |    |   (----`
#     |  |      /  /_\  \   |  |     |  | |  |  |  | |  . `  | |  |     \   \  
#     |  |     /  _____  \  |  `----.|  | |  `--'  | |  |\   | |  | .----)   |  
#     |__|    /__/     \__\ |_______||__|  \______/  |__| \__| |__| |_______/

# MAIN STRUCTURES USED
# Game Loop (get events, logic, update, draw)
# FrameRate independant animations (mostly :))
# State Machine Stack -> to help keep the game logic sane
# Arbitrary Components for Statuses, Skills, and Items
# Massive Unit Object
# Super-serializable save states

# === CODE ====================================================================

# === IMPORT MODULES ==========================================================
import os
import sys
import time

sys.path.append('Assets/Lex-Talionis')

from datetime import datetime

# Custom imports
import Code.imagesDict as imagesDict
import Code.GlobalConstants as GC
import Code.configuration as cf
from Code import GameStateObj, Engine

import metrosetup

temp_canvas = None
# === MAIN FUNCTION ===========================================================
def main():
    # Set Volume
    Engine.music_thread.set_volume(cf.OPTIONS['Music Volume'])
    imagesDict.set_sound_volume(cf.OPTIONS['Sound Volume'], GC.SOUNDDICT)

    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}
    gameStateObj.metaDataObj = metaDataObj

    run(gameStateObj, metaDataObj)

# === Main Game Loop ===
def run(gameStateObj, metaDataObj):
    while True:
        Engine.update_time()

        # Get events
        eventList = Engine.build_event_list()

        # Update global music thread
        Engine.music_thread.update(eventList)

        # === UPDATE USER STATES ===
        mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
        

        while repeat:
            # We don't need to process the eventList more than once I think
            mapSurf, repeat = gameStateObj.stateMachine.update([], gameStateObj, metaDataObj)

        # Update global sprite counters
        GC.PASSIVESPRITECOUNTER.update()
        GC.ACTIVESPRITECOUNTER.update()
        GC.CURSORSPRITECOUNTER.update()

        #new_size = (cf.OPTIONS['Screen Width'], cf.OPTIONS['Screen Height'])

        draw_rect = GC.TEMPCANVASRECT

        Engine.push_display(mapSurf, (draw_rect[2], draw_rect[3]), GC.TEMPCANVAS)

        GC.DISPLAYSURF.blit(GC.TEMPCANVAS, draw_rect)
        #Engine.push_display(mapSurf, new_size, GC.DISPLAYSURF)
        
        # Check for taking screenshot
        for event in eventList:
            if event.type == Engine.KEYDOWN and event.key == Engine.key_map['`']:
                current_time = str(datetime.now()).replace(' ', '_').replace(':', '.')
                Engine.save_surface(mapSurf, "Lex_Talionis_%s.png" % current_time)
        # Keep gameloop (update, renders, etc) ticking
        
        Engine.update_display()

        gameStateObj.playtime += GC.FPSCLOCK.tick(GC.FPS)

    # === END OF MAIN GAME LOOP ===

def handle_debug_logs():
    counter = 5  # Increments all old debug logs. Destroys ones older than 5 runs.
    while counter > 0:
        fp = ''.join([ metrosetup.get_prefs_dir() + '/' + 'Saves/debug.log.', str(counter)])
        if os.path.exists(fp):
            if counter == 5:
                os.remove(fp)
            else:
                os.rename(fp, ''.join([metrosetup.get_prefs_dir() + '/' + 'Saves/debug.log.', str(counter + 1)]))
        counter -= 1

def inform_error():
    print("=== === === === === ===")
    print('Damn. Another bug :(')
    print("Quick! Copy this error log and send it to rainlash!")
    print('Or send the file "Saves/debug.log.1" to rainlash!')
    print('Thank you!')
    print("=== === === === === === \n")

# ____________________________________________________________________________#
# === START === START === START  === START ===  START === START === START === #
if __name__ == '__main__':
    #import logging, traceback
    #import trackeback
    #logging.logThreads = 0
    #logging.logProcesses = 0
    #logger = logging.getLogger(__name__)
    try:
        handle_debug_logs()
    except WindowsError:
        print("Error! Debug logs in use -- Another instance of this is already running!")
        Engine.terminate()
    #if cf.OPTIONS['debug']:
    #    my_level = logging.DEBUG
    #else:
    #    my_level = logging.WARNING
    #logging.basicConfig(handlers=[logging.FileHandler('./Saves/debug.log.1', 'w', 'utf-8')],
    #                    level=my_level, format='%(relativeCreated)d %(levelname)7s:%(module)16s: %(message)s')
    print('*** Lex Talionis Engine Version %s ***' % GC.version)
    main()
    
# === END === END === END === END === END === END === END === END === END === #
