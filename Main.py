#!/usr/bin/env python2.7
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

# --- Missing Sounds ---
# Error sound when you try and move somewhere you should not be able to move
# Chapter Intro Name Sound?
# Sound made when moving the trade menu from one unit to another. Whenever you press left or right while trading
# R Button sound in R Button Menu
# Sound made when pressing Left or Right in R Button Menu
# === CODE ====================================================================

# === IMPORT MODULES ==========================================================
import os
import pygame

# Custom imports
import Code.imagesDict as imagesDict
import Code.GlobalConstants as GC
import Code.configuration as cf
from Code import GameStateObj, Engine


# === MAIN FUNCTION ===========================================================
def main():
    # logger = logging.getLogger(__name__)

    # Set Volume
    Engine.music_thread.set_volume(cf.OPTIONS['Music Volume'])
    imagesDict.set_sound_volume(cf.OPTIONS['Sound Volume'], GC.SOUNDDICT)

    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}

    run(gameStateObj, metaDataObj)

# === Main Game Loop ===
def run(gameStateObj, metaDataObj):
    my_list = gameStateObj.stateMachine.state[-5:]
    while True:
        if cf.OPTIONS['debug']:
            my_new_list = gameStateObj.stateMachine.state[-5:]
            if my_new_list != my_list:
                logger.debug('Current states %s', [state.name for state in gameStateObj.stateMachine.state])
                my_list = my_new_list
                # logger.debug('Active Menu %s', gameStateObj.activeMenu)
        Engine.update_time()

        # Get events
        eventList = Engine.build_event_list()

        # === UPDATE USER STATES ===
        mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
        while repeat:
            mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
        # Update global sprite counters
        GC.PASSIVESPRITECOUNTER.update()
        GC.ACTIVESPRITECOUNTER.update()
        GC.CURSORSPRITECOUNTER.update()
        # Update global music thread
        Engine.music_thread.update(eventList)

        new_size = (GC.WINWIDTH * cf.OPTIONS['Screen Size'], GC.WINHEIGHT * cf.OPTIONS['Screen Size'])
        pygame.transform.scale(mapSurf, new_size, GC.DISPLAYSURF)
        # Keep gameloop (update, renders, etc) ticking
        pygame.display.update()
        gameStateObj.playtime += GC.FPSCLOCK.tick(GC.FPS)
    # === END OF MAIN GAME LOOP ===

def handle_debug_logs():
    counter = 5  # Increments all old debug logs. Destroys ones older than 5 runs.
    while counter > 0:
        fp = ''.join(['./Saves/debug.log.', str(counter)])
        if os.path.exists(fp):
            if counter == 5:
                os.remove(fp)
            else:
                os.rename(fp, ''.join(['./Saves/debug.log.', str(counter + 1)]))
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
    import logging, traceback
    logger = logging.getLogger(__name__)
    try:
        handle_debug_logs()
    except WindowsError:
        print("Error! Debug logs in use -- Another instance of this is already running!")
        Engine.terminate()
    if cf.OPTIONS['debug']:
        my_level = logging.DEBUG
    else:
        my_level = logging.WARNING
    logging.basicConfig(filename='./Saves/debug.log.1', filemode='w',
                        level=my_level, disable_existing_loggers=False,
                        format='%(levelname)8s:%(module)20s: %(message)s')
    try:
        main()
    except Exception as e:
        logger.exception(e)
        inform_error()
        print('Main Crash {0}'.format(str(e)))
        # Now print exception to screen
        import time
        time.sleep(0.5)
        traceback.print_exc()
        time.sleep(0.5)
        inform_error()
        time.sleep(20)
# === END === END === END === END === END === END === END === END === END === #
