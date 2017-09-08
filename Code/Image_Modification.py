#! usr/bin/env python

import math

# Custom imports
import GlobalConstants as GC
import Engine, Utility

def flicker_image(image, color):
    color = tuple(Utility.clamp(c, 0, 255) for c in color)
    image = Engine.copy_surface(image)
    Engine.fill(image, color, None, Engine.BLEND_RGB_ADD)
    return image

def flickerImageWhite(image, white):
    """whiteness measured from 0 to 255"""
    white = Utility.clamp(white, 0, 255)
    image = Engine.copy_surface(image)
    Engine.fill(image, (white, white, white), None, Engine.BLEND_RGB_ADD)

    return image

def flickerImageRed(image, red):
    """whiteness measured from 0 to 255"""
    red = Utility.clamp(red, 0, 255)
    image = Engine.copy_surface(image)
    Engine.fill(image, (red, 0, 0), None, Engine.BLEND_RGB_ADD)

    return image
#
# Don't use this for ANYTHING BIG. It's slow. For instance, flicker white the minimap (which was 80 x 40, took ~5 milliseconds!)
def flickerImageWhiteColorKey(image, white, colorkey=(128, 160, 128)):
    white = Utility.clamp(white, 0, 255)
    image = Engine.copy_surface(image)
    
    for row in range(image.get_width()):
        for col in range(image.get_height()):
            color = image.get_at((row, col))
            if color != colorkey: # ie, my transparent color
                color = (min(255, color[0] + white), min(255, color[1] + white), min(255, color[2] + white))
            image.set_at((row, col), color)
    
    # Basically none of the below actually work. None respect the color key when blending...
    # image.fill((white, white, white), None, pygame.BLEND_RGB_ADD)

    return image

def flickerImageTranslucent(image, transparency):
    """transparency measured from 0% transparent to 100% transparent"""
    alpha = 255 - int(2.55*transparency)
    alpha = Utility.clamp(alpha, 0, 255)
    image = Engine.copy_surface(image)
    Engine.fill(image, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)

    return image

def flickerImageTranslucent255(image, alpha):
    alpha = Utility.clamp(alpha, 0, 255)
    image = Engine.copy_surface(image)
    Engine.fill(image, (255, 255, 255, alpha), None, Engine.BLEND_RGBA_MULT)
    
    return image

def flickerImageTranslucentBlend(image, alpha):
    alpha = Utility.clamp(alpha, 0, 255)
    image = Engine.copy_surface(image)
    Engine.fill(image, (alpha, alpha, alpha), None, Engine.BLEND_RGB_MULT)
    
    return image

def flickerImageTranslucentColorKey(image, transparency):
    # 100 is most transparent. 0 is opaque.
    alpha = 255 - int(2.55*transparency)
    alpha = Utility.clamp(alpha, 0, 255)
    image = Engine.copy_surface(image)
    Engine.set_alpha(image, alpha, rleaccel=True)

    return image

def flickerImageBlackColorKey(image, black):
    # 100 is most black. 0 is no black.
    black = 255 - int(2.55*black)
    black = Utility.clamp(black, 0, 255)
    temp = Engine.create_surface((image.get_width(), image.get_height()), transparent=True)
    temp.blit(image, (0, 0))
    Engine.fill(temp, (black, black, black), None, Engine.BLEND_RGB_MULT)

    return temp

def change_image_color(image, color):
    # color = (Utility.clamp(color[0], 0, 255), Utility.clamp(color[1], 0, 255), Utility.clamp(color[2], 0, 255))
    image = Engine.copy_surface(image)
    for idx, band in enumerate(color):
        blend_mode = Engine.BLEND_RGB_ADD
        if band < 0:
            blend_mode = Engine.BLEND_RGB_SUB
            band = -band
        if idx == 0:
            new_color = (band, 0, 0)
        elif idx == 1:
            new_color = (0, band, 0)
        else:
            new_color = (0, 0, band)
        Engine.fill(image, new_color, None, blend_mode)

    return image

# Gets a color that is between the two colors in a linear way
def color_transition(color1, color2):
    # A number between 1 and 20 that changes at a set pace in a linear fashion
    linear_transform_num = math.sin(math.radians((Engine.get_time()/10)%180))
    diff_colors = (color2[0] - color1[0], color2[1] - color1[1], color2[2] - color1[2])
    new_color = []
    for index, chroma in enumerate(diff_colors):
        new_color.append(min(255, max(0, int(chroma * linear_transform_num) + color1[index])))
    # print linear_transform_num, color1, color2, diff_colors, new_color

    return new_color

# Gets a color that is between the two colors in a linear way
def color_transition2(color1, color2):
    # A number between 1 and 20 that changes at a set pace in a linear fashion
    linear_transform_num = math.sin(math.radians((Engine.get_time()/10)%180))
    diff_colors = (color2[0] - color1[0], color2[1] - color1[1], color2[2] - color1[2])
    new_color = []
    for index, chroma in enumerate(diff_colors):
        new_color.append(int(chroma * linear_transform_num) + color1[index])
    # print linear_transform_num, color1, color2, diff_colors, new_color

    return new_color

def transition_image_white(image):
    # Might be too slow :(
    for row in range(image.get_width()):
        for col in range(image.get_height()):
            color = image.get_at((row, col))
            if color[3] == 255: # ie, an opaque color
                color = color_transition(color, GC.COLORDICT['white'])
            image.set_at((row, col), color)

    return image

def resize(image, scale):
    x_scale, y_scale = scale
    """scale is a float from 0 to 1"""
    return Engine.transform_scale(image, (int(image.get_width()*x_scale), int(image.get_height()*y_scale)))
