# Test image loading
import os, time
import pstats
import cProfile

#pygame.display.set_mode((600, 400))
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad
import Code.GameStateObj as GameStateObj

import logging
my_level = logging.DEBUG
logging.basicConfig(filename='Tests/debug.log.test', filemode='w', level=my_level, disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}
    gameStateObj.build_new()
    for num in range(0, GC.CONSTANTS['num_levels']):
        time1 = time.clock()
        print('Level: %s'%num)
        SaveLoad.load_level('Data/Level' + str(num), gameStateObj, metaDataObj)
        print('Time to Load: %s'%(time.clock() - time1))
        print('Num Units: %s  Map Size: %s'%(len(gameStateObj.allunits), gameStateObj.map.width*gameStateObj.map.height))
        gameStateObj.clean_up()
        print('Num Units Remaining: %s'%(len(gameStateObj.allunits)))

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(20)
    os.remove("Profile.prof")