# Test image loading
import pstats
import cProfile

import pygame
import Code.imagesDict as images
pygame.display.set_mode((600, 400))

def main():
    IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT = images.getImages()
    assert len(IMAGESDICT) > 0
    assert len(UNITDICT) > 0
    assert len(ICONDICT) > 0
    assert len(ITEMDICT) > 0

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(10)
