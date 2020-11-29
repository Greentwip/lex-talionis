# Test image loading
import os, time
import pstats
import cProfile

import pygame

import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad
import Code.GameStateObj as GameStateObj
import Code.InfoMenu as InfoMenu
import Code.CustomObjects as CustomObjects

#import logging

GC.DISPLAYSURF = pygame.display.set_mode((GC.WINWIDTH, GC.WINHEIGHT))

my_level = logging.DEBUG
logging.basicConfig(filename='Tests/debug.log.test', filemode='w', level=my_level,
                    disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}
    gameStateObj.build_new()
    gameStateObj.set_generic_mode()
    wait_for = 1
    num = 0
    while True:
        levelfolder = 'Assets/Lex-Talionis/Data/Level' + str(num)
        if not os.path.exists(levelfolder):
            break
        print('Level: %s' % num)
        time1 = time.clock()
        SaveLoad.load_level('Assets/Lex-Talionis/Data/Level' + str(num), gameStateObj, metaDataObj)
        print('Time to Load: %s' % (time.clock() - time1))
        print('Num Units: %s  Map Size: %s' % (len(gameStateObj.allunits), gameStateObj.map.width*gameStateObj.map.height))
        for unit in gameStateObj.allunits:
            CustomObjects.handle_info_key(gameStateObj, metaDataObj, unit)
            info_menu = InfoMenu.InfoMenu()
            info_menu.begin(gameStateObj, metaDataObj)
            for _ in range(wait_for):
                run(gameStateObj, metaDataObj, info_menu)
            # Move right
            info_menu.move_right(gameStateObj, metaDataObj)
            for _ in range(wait_for):
                run(gameStateObj, metaDataObj, info_menu)
            info_menu.move_right(gameStateObj, metaDataObj)
            for _ in range(wait_for):
                run(gameStateObj, metaDataObj, info_menu)
            info_menu.move_right(gameStateObj, metaDataObj)
            for _ in range(wait_for):
                run(gameStateObj, metaDataObj, info_menu)

        gameStateObj.clean_up()
        print('Num Units Remaining: %s'%(len(gameStateObj.allunits)))

        num += 1

def run(gameStateObj, metaDataObj, info_menu):
    info_menu.update(gameStateObj, metaDataObj)
    surf = info_menu.draw(gameStateObj, metaDataObj)
    GC.DISPLAYSURF.blit(surf, (0, 0))
    pygame.display.update()

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(20)
    os.remove("Profile.prof")
