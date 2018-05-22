# Test image loading
import os
import pstats
import cProfile

import pygame
import pyautogui


import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad
import Code.GameStateObj as GameStateObj
import Code.Transitions as Transitions
import Code.Engine as Engine
import Code.Dialogue as Dialogue

import logging

pyautogui.PAUSE = 0
GC.DISPLAYSURF = pygame.display.set_mode((GC.WINWIDTH, GC.WINHEIGHT))

my_level = logging.DEBUG
logging.basicConfig(filename='Tests/debug.log.test', filemode='w', level=my_level,
                    disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}
    gameStateObj.build_new()
    done = False
    for num in range(0, GC.cf.CONSTANTS['num_levels']):
        if hasattr(gameStateObj, 'saving_thread'):
            gameStateObj.saving_thread.join()
        gameStateObj.save_slots = Transitions.load_saves()
        print('Level: %s'%num)
        gameStateObj.build_new() # Make the gameStateObj ready for a new game
        gameStateObj.save_slot = 0
        levelfolder = 'Data/Level' + str(gameStateObj.counters['level'])
        # Create a save for the first game
        gameStateObj.stateMachine.clear()
        gameStateObj.stateMachine.changeState('turn_change')
        SaveLoad.suspendGame(gameStateObj, "Start", slot=gameStateObj.save_slot)
        # Load the first level
        SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
        # Set Casual Mode
        gameStateObj.mode['death'] = 0
        # Run
        counter = 0
        suspended_yet, dead_yet = False, False
        while not done:
            Engine.update_time()
            current_state = gameStateObj.stateMachine.getState()
            if current_state == 'free':
                units = [unit for unit in gameStateObj.allunits if unit.team == 'player' and
                         not unit.dead and unit.name not in {'Sam', 'Ophie', 'Prim', 'Renae'}]
                if not dead_yet and units:
                    unit = units[0]
                    print(unit.name)
                    unit.isDying = True
                    gameStateObj.stateMachine.changeState('dying')
                    gameStateObj.message.append(Dialogue.Dialogue_Scene(metaDataObj['death_quotes']))
                    gameStateObj.stateMachine.changeState('dialogue')
                    dead_yet = True
                elif suspended_yet:
                    pyautogui.press('w')
                    suspended_yet = False
                else:
                    SaveLoad.suspendGame(gameStateObj, 'Suspend', hard_loc='Suspend')
                    gameStateObj.save_slots = None # Reset save slots
                    gameStateObj.stateMachine.clear()
                    gameStateObj.stateMachine.changeState('start_start')
                    suspended_yet = True
            elif current_state == 'start_save' or current_state == 'start_start' or current_state == 'start_option':
                pyautogui.press('x')
                if current_state == 'start_save':
                    dead_yet = False
            elif current_state == 'move':
                pyautogui.press('z')
            counter += 1
            if not counter%20:
                pyautogui.press('s')
            eventList = Engine.build_event_list()
            mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
            while repeat:
                mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
            GC.DISPLAYSURF.blit(mapSurf, (0, 0))
            pygame.display.update()
            gameStateObj.playtime += GC.FPSCLOCK.tick(GC.FPS)

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(20)
    os.remove("Profile.prof")
