import os
from PIL import Image

map_sprite = Image.open('MapSprite.png')
mask = Image.open('Autotiles/autotile0.png')

for x in range(map_sprite.size[0]):
    for y in range(map_sprite.size[1]):
        color = mask.getpixel((x, y))
        # If not mask color (128, 160, 128)
        if color[0] != 128 or color[1] != 160 or color[2] != 128:
            map_sprite.putpixel((x, y), (128, 160, 128))
map_sprite.save('FixedMapSprite.png')