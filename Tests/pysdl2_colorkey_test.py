"""
# Testing PYGAME_SDL2's colorkey + subsurface interaction
"""
PYGAME_SDL2 = False
if PYGAME_SDL2:
    import pygame_sdl2
    pygame_sdl2.import_as_pygame()
import pygame
import sys

pygame.init()
size = 240, 160
DISPLAYSURF = pygame.display.set_mode(size)

im = pygame.image.load('colorkey_test.png').convert()
im.set_colorkey((128, 160, 128), pygame.RLEACCEL)  # Whether RLEACCEL is active makes no difference
im = im.subsurface(16, 16, 32, 32)

def process_events():
    # Only gets escape events!
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

while True:
    process_events()
    DISPLAYSURF.fill((0, 0, 0))
    DISPLAYSURF.blit(im, (120 - 16, 80 - 16))
    pygame.display.update()
