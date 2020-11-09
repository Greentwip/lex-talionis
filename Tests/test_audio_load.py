import time, os, sys

# Test image loading
import pstats
import cProfile

import pygame
sys.path.append('../')
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import logging
GC.DISPLAYSURF = pygame.display.set_mode((GC.WINWIDTH, GC.WINHEIGHT))

my_level = logging.DEBUG
logging.basicConfig(filename='debug.log.test', filemode='w', level=my_level, 
                    disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    print('Num Music: %s' % len(GC.MUSICDICT))
    print('Num Sounds: %s' % len(GC.SOUNDDICT))

    num = 0
    while True:
        levelfolder = 'Assets/Lex-Talionis/Data/Level' + str(num)
        if not os.path.exists(levelfolder):
            break
        print('Level: %s' % num)
        for fp in os.listdir(levelfolder):
            if fp.endswith('Script.txt'):
                with open(levelfolder + '/' + fp) as script:
                    for line in script.readlines():
                        if line.startswith('#'):
                            continue
                        line = line.strip().split(';')
                        if line[0] == 'm':
                            if line[1] in GC.MUSICDICT:
                                Engine.music_thread.fade_in(GC.MUSICDICT[line[1]])
                            else:
                                print("***Couldn't find music matching %s"%line[1])
                        elif line[0] == 'mf':
                            print('Fade out music')
                            Engine.music_thread.fade_back()
            elif fp == 'overview.txt':
                with open(levelfolder + '/' + fp) as overview:
                    for line in overview.readlines():
                        line = line.strip().split(';')
                        if line[0].endswith('music'):
                            if line[1] in GC.MUSICDICT:
                                Engine.music_thread.fade_in(GC.MUSICDICT[line[1]])
                            else:
                                print("***Couldn't find music matching %s"%line[1])
        num += 1

    print('Sound check!')
    for name, sfx in GC.SOUNDDICT.iteritems():
        sfx.play()
        time.sleep(.1)
        sfx.stop()

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(10)
