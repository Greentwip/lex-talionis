# Tests death Dialogue
import os, time
import pstats
import cProfile

import pygame
import pyautogui
pyautogui.PAUSE = 0

import Code.GlobalConstants as GC
DISPLAYSURF = pygame.display.set_mode((GC.WINWIDTH, GC.WINHEIGHT))
import Code.SaveLoad as SaveLoad
import Code.GameStateObj as GameStateObj
import Code.StateMachine as StateMachine
import Code.Dialogue as Dialogue
import Code.Engine as Engine

import logging
my_level = logging.DEBUG
logging.basicConfig(filename='Tests/debug.log.test', filemode='w', level=my_level, disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}
    gameStateObj.build_new()
    levelfolder = 'Data/Level0'
    SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
    run(gameStateObj, metaDataObj)
    gameStateObj.clean_up()
    print('Num Units Remaining: %s'%(len(gameStateObj.allunits)))

def run(gameStateObj, metaDataObj):
    gameStateObj.message.append(Dialogue.Dialogue_Scene('Data/fight_quote_info.txt', event_flag = False))
    gameStateObj.stateMachine.changeState('dialogue')
    counter = 0
    while gameStateObj.message:
        Engine.update_time()
        counter += 1
        if not counter%50:
            pyautogui.press('x')
        eventList = Engine.build_event_list()
        mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
        while repeat:
            mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
        DISPLAYSURF.blit(mapSurf, (0, 0))
        pygame.display.update()

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(20)
    os.remove("Profile.prof")