import time, os

# Test image loading
import pstats
import cProfile

import pygame
import Code.GlobalConstants as GC
DISPLAYSURF = pygame.display.set_mode((GC.WINWIDTH, GC.WINHEIGHT))
import Code.imagesDict as images
import Code.Engine as Engine

import logging
my_level = logging.DEBUG
logging.basicConfig(filename='Tests/debug.log.test', filemode='w', level=my_level, disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    SOUNDDICT, MUSICDICT = images.getSounds()
    print('Num Music: %s'%len(MUSICDICT))
    print('Num Sounds: %s'%len(SOUNDDICT))
    for num in range(0, GC.CONSTANTS['num_levels']):
        print('Level: %s'%num)
        levelfolder = 'Data/Level' + str(num)
        for fp in os.listdir(levelfolder):
            if fp.endswith('Script.txt'):
                with open(levelfolder + '/' + fp) as script:
                    for line in script.readlines():
                        if line.startswith('#'):
                            continue
                        line = line.strip().split(';')
                        if line[0] == 'm':
                            if line[1] in MUSICDICT:
                                Engine.music_thread.fade_in(MUSICDICT[line[1]])
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
                            if line[1] in MUSICDICT:
                                Engine.music_thread.fade_in(MUSICDICT[line[1]])
                            else:
                                print("***Couldn't find music matching %s"%line[1])

    print('Sound check!')
    for name, sfx in SOUNDDICT.iteritems():
        sfx.play()
        time.sleep(.1)
        sfx.stop()

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(10)