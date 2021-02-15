from . import GlobalConstants as GC
from . import Engine

def CreateBaseMenuSurf(size, baseimage='BaseMenuBackground', top_left_sigil=None):
    width, height = size
    menuBaseSprite = GC.IMAGESDICT[baseimage]
    # Get total width and height.
    # Each piece of the menu (9) should be 1/3 of these dimensions
    mBSWidth = menuBaseSprite.get_width()
    mBSHeight = menuBaseSprite.get_height()

    # Force the width and height to be correct!
    full_width = width - width%(mBSWidth//3)
    full_height = height - height%(mBSHeight//3)
    width = mBSWidth//3
    height = mBSHeight//3

    assert full_width%(width) == 0, "The dimensions of the menu are wrong - the sprites will not line up correctly. They must be multiples of 8. %s" %(width)
    assert full_height%(height) == 0, "The dimensions of the manu are wrong - the sprites will not line up correctly. They must be multiples of 8. %s" %(height)

    # Create simple surfs to be blitted from the menuBaseSprite
    TopLeftSurf = Engine.subsurface(menuBaseSprite, (0, 0, width, height))
    TopSurf = Engine.subsurface(menuBaseSprite, (width, 0, width, height))
    TopRightSurf = Engine.subsurface(menuBaseSprite, (2*width, 0, width, height))
    LeftSurf = Engine.subsurface(menuBaseSprite, (0, height, width, height))
    CenterSurf = Engine.subsurface(menuBaseSprite, (width, height, width, height))
    RightSurf = Engine.subsurface(menuBaseSprite, (2*width, height, width, height))
    BottomLeftSurf = Engine.subsurface(menuBaseSprite, (0, 2*height, width, height))
    BottomSurf = Engine.subsurface(menuBaseSprite, (width, 2*height, width, height))
    BottomRightSurf = Engine.subsurface(menuBaseSprite, (2*width, 2*height, width, height))

    # Create transparent background
    MainMenuSurface = Engine.create_surface((full_width, full_height), transparent=True, convert=True)

    # Blit Center sprite
    for positionx in range(full_width//width - 2):
        for positiony in range(full_height//height - 2):
            topleft = ((positionx+1)*width, (positiony+1)*height)
            MainMenuSurface.blit(CenterSurf, topleft)

    # Blit Edges
    for position in range(full_width//width - 2): # For each position in which this would fit
        topleft = ((position+1)*width, 0)
        MainMenuSurface.blit(TopSurf, topleft)
    # --
    for position in range(full_width//width - 2):
        topleft = ((position+1)*width, full_height - height)
        MainMenuSurface.blit(BottomSurf, topleft)
    # --
    for position in range(full_height//height - 2):
        topleft = (0, (position+1)*height)
        MainMenuSurface.blit(LeftSurf, topleft)
    # --
    for position in range(full_height//height - 2):
        topleft = (full_width - width, (position+1)*height)
        MainMenuSurface.blit(RightSurf, topleft)

    # Perhaps switch order in which these are blitted
    # Blit corners
    MainMenuSurface.blit(TopLeftSurf, (0, 0))
    # --
    MainMenuSurface.blit(TopRightSurf, (full_width - width, 0))
    # --
    MainMenuSurface.blit(BottomLeftSurf, (0, full_height - height))
    # --
    MainMenuSurface.blit(BottomRightSurf, (full_width - width, full_height - height))

    return MainMenuSurface
