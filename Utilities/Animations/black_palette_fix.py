#! usr/bin/env python2.7
import time
from PIL import Image

# Joshua
palette_list = [(128, 160, 128), # Background
                (248, 248, 248), # White
                (248, 248, 208), # Light skin
                (248, 192, 144), # Med skin
                (112, 72, 48), # Dark skin
                (224, 48, 16), # Light Hair
                (160, 8, 8), # Med Hair
                (104, 8, 16), # Dark Hair
                (176, 208, 240), # Light Weapon/Leather
                (112, 144, 176), # Med Weapon/Leather
                (64, 96, 128), # Dark Weapon/String
                (128, 168, 168), # Light Clothes
                (88, 128, 128), # LM Clothes
                (48, 88, 88), # MD Clothes
                (24, 48, 48), # Dark Clothes
                (40, 40, 40)] # Outline

# Generic Red
enemy_palette = [(128, 160, 128), # Background
                (248, 248, 248), # White
                (248, 248, 208), # Light skin
                (248, 192, 144), # Med skin
                (112, 72, 48), # Dark skin
                (216, 216, 224), # Light Hair
                (176, 176, 192), # Med Hair
                (112, 112, 144), # Dark Hair
                (176, 208, 240), # Light Weapon/Leather
                (120, 152, 184), # Med Weapon/Leather
                (80, 112, 144), # Dark Weapon/String
                (248, 192, 128), # Light Clothes
                (248, 136, 48), # LM Clothes
                (200, 0, 0), # MD Clothes
                (128, 0, 8), # Dark Clothes
                (40, 40, 40)] # Outline

# Generic blue
player_palette = [(128, 160, 128), # Background
                (248, 248, 248), # White
                (248, 248, 208), # Light skin
                (248, 192, 144), # Med skin
                (112, 72, 48), # Dark skin
                (216, 216, 224), # Light Hair
                (176, 176, 192), # Med Hair
                (112, 112, 144), # Dark Hair
                (176, 208, 240), # Light Weapon/Leather
                (120, 152, 184), # Med Weapon/Leather
                (80, 112, 144), # Dark Weapon/String
                (128, 192, 248), # Light Clothes
                (48, 136, 248), # LM Clothes
                (40, 40, 200), # MD Clothes
                (48, 40, 128), # Dark Clothes
                (40, 40, 40)] # Outline

palette = player_palette

index_swap = {1: 13,
              2: 12,
              3: 11,
              4: 7,
              5: 6,
              6: 5,
              7: 15,
              8: 4,
              9: 3,
              10: 2,
              11: 1,
              12: 8,
              13: 9,
              14: 10,
              15: 14
              }
assert len(palette_list) == 16

fp = 'Myrmidon0.png'
picture = Image.open(fp)

# Get the size of the image
width, height = picture.size

# Change color
time1 = time.clock()
for x in range(width):
    for y in range(height):
    	current_color = picture.getpixel((x,y))
        index = current_color[0]
        if index == 0 and current_color[3] != 0:
            index = 15
        if index in index_swap:
            index = index_swap[index]
    	new_color = palette[index]
    	picture.putpixel((x, y), new_color)
print((time.clock() - time1)*1000)

picture.save('Generic'+fp)