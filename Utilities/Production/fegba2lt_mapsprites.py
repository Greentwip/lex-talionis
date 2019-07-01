# Converts FERepo Map Sprites to Lex Talionis Format
import glob, difflib
from PIL import Image

gray_dict = {(88, 72, 120): (64, 64, 64),
             (144, 184, 232): (120, 120, 120),
             (216, 232, 240): (184, 184, 184),
             (112, 96, 96): (80, 80, 80),
             (176, 144, 88): (128, 128, 128),
             (248, 248, 208): (200, 200, 200),
             (56, 56, 144): (72, 72, 72),
             (56, 80, 224): (88, 88, 88),
             (40, 160, 248): (152, 152, 152),
             (24, 240, 248): (184, 184, 184),
             (232, 16, 24): (112, 112, 112),
             (248, 248, 64): (200, 200, 200),
             (248, 248, 248): (208, 208, 208)}

enemy_dict = {(56, 56, 144): (96, 40, 32),
              (56, 80, 224): (168, 48, 40),
              (40, 160, 248): (224, 16, 16),
              (24, 240, 248): (248, 80, 72),
              (232, 16, 24): (56, 208, 48),
              (88, 72, 120): (104, 72, 96),
              (216, 232, 240): (224, 224, 224),
              (144, 184, 232): (192, 168, 184)}

other_dict = {(56, 56, 144): (32, 80, 16),
              (56, 80, 224): (8, 144, 0),
              (40, 160, 248): (24, 208, 16),
              (24, 240, 248): (80, 248, 56),
              (232, 16, 24): (0, 120, 200),
              (88, 72, 120): (56, 80, 56),
              (144, 184, 232): (152, 200, 158),
              (216, 232, 240): (216, 248, 184),
              (112, 96, 96): (88, 88, 80),
              (176, 144, 88): (160, 136, 64),
              (248, 248, 208): (248, 248, 192),
              (248, 248, 64): (224, 248, 40)}

enemy2_dict = {(56, 56, 144): (88, 32, 96),
               (56, 80, 224): (128, 48, 144),
               (40, 160, 248): (184, 72, 224),
               (24, 240, 248): (208, 96, 248),
               (232, 16, 24): (56, 208, 48),
               (88, 72, 120): (88, 64, 104),
               (144, 184, 232): (168, 168, 232),
               (64, 56, 56): (72, 40, 64)}

def color_convert(newimg, d):
    width, height = newimg.size
    img = Image.new("RGB", (width, height), (128, 160, 128))
    # Change color
    for x in range(width):
        for y in range(height):
            current_color = newimg.getpixel((x, y))
            try:
                new_color = d[current_color]
            except KeyError:
                new_color = current_color
            img.putpixel((x, y), new_color)

    return img

# Get images
images = glob.glob('*.png')

# Pair images
images_dict = {}
for image in images:
    if 'moving' in image.lower():
        standing_name = image.lower().replace('moving', 'standing')
        match = difflib.get_close_matches(standing_name, images, 1)
        if not match:
            print("Couldn't find a match for %s!" % image)
            continue
        else:
            match = match[0]
        shared_name = image.replace('moving', '').replace('Moving', '').replace('.png', '')
        images_dict[shared_name] = (match, image)

for name, pair in images_dict.items():
    standing, moving = pair
    standing = Image.open(standing)
    mixed_width, mixed_height = standing.size
    moving = Image.open(moving)
    new_s = Image.new("RGB", (192, 144), (128, 160, 128))
    new_m = Image.new("RGB", (192, 160), (128, 160, 128))

    p1 = standing.crop((0, 0, mixed_width, mixed_height//3))
    p2 = standing.crop((0, mixed_height//3, mixed_width, 2*mixed_height//3))
    p3 = standing.crop((0, 2*mixed_height//3, mixed_width, 3*mixed_height//3))

    l1 = moving.crop((0, 0, 32, 32))
    l2 = moving.crop((0, 32, 32, 64))
    l3 = moving.crop((0, 64, 32, 96))
    l4 = moving.crop((0, 96, 32, 128))

    d1 = moving.crop((0, 32*4, 32, 32*5))
    d2 = moving.crop((0, 32*5, 32, 32*6))
    d3 = moving.crop((0, 32*6, 32, 32*7))
    d4 = moving.crop((0, 32*7, 32, 32*8))

    u1 = moving.crop((0, 32*8, 32, 32*9))
    u2 = moving.crop((0, 32*9, 32, 32*10))
    u3 = moving.crop((0, 32*10, 32, 32*11))
    u4 = moving.crop((0, 32*11, 32, 32*12))

    f1 = moving.crop((0, 32*12, 32, 32*13))
    f2 = moving.crop((0, 32*13, 32, 32*14))
    f3 = moving.crop((0, 32*14, 32, 32*15))

    if mixed_height//3 == 16:
        new_height = 24
    else:
        new_height = 8
    if mixed_width == 16:
        new_width = 24
    else:
        new_width = 16

    new_s.paste(p1, (new_width, new_height))
    new_s.paste(p2, (new_width+64, new_height))
    new_s.paste(p3, (new_width+64*2, new_height))

    new_s.paste(f1, (16, 8+96))
    new_s.paste(f2, (16+64, 8+96))
    new_s.paste(f3, (16+64*2, 8+96))

    new_m.paste(d1, (8, 8))
    new_m.paste(d2, (8+48, 8))
    new_m.paste(d3, (8+48*2, 8))
    new_m.paste(d4, (8+48*3, 8))

    new_m.paste(l1, (8, 48))
    new_m.paste(l2, (8+48, 48))
    new_m.paste(l3, (8+48*2, 48))
    new_m.paste(l4, (8+48*3, 48))

    new_m.paste(l1.transpose(Image.FLIP_LEFT_RIGHT), (8, 88))
    new_m.paste(l2.transpose(Image.FLIP_LEFT_RIGHT), (8+48, 88))
    new_m.paste(l3.transpose(Image.FLIP_LEFT_RIGHT), (8+48*2, 88))
    new_m.paste(l4.transpose(Image.FLIP_LEFT_RIGHT), (8+48*3, 88))

    new_m.paste(u1, (8, 128))
    new_m.paste(u2, (8+48, 128))
    new_m.paste(u3, (8+48*2, 128))
    new_m.paste(u4, (8+48*3, 128))

    # Make Passive Sprite
    width, height = new_s.size
    passive_sprites = new_s.crop((0, 0, width, height//3))
    gray_passive_sprites = color_convert(passive_sprites, gray_dict)
    new_s.paste(gray_passive_sprites, (0, height//3))

    new_name = name

    new_s.save("player" + new_name + ".png")
    new_m.save("player" + new_name + "_move.png")

    enemy_s = color_convert(new_s, enemy_dict)
    enemy_m = color_convert(new_m, enemy_dict)
    enemy_s.save("enemy" + new_name + ".png")
    enemy_m.save("enemy" + new_name + "_move.png")

    other_s = color_convert(new_s, other_dict)
    other_m = color_convert(new_m, other_dict)
    other_s.save("other" + new_name + '.png')
    other_m.save("other" + new_name + '_move.png')

    enemy2_s = color_convert(new_s, enemy2_dict)
    enemy2_m = color_convert(new_m, enemy2_dict)
    enemy2_s.save("enemy2" + new_name + '.png')
    enemy2_m.save("enemy2" + new_name + '_move.png')
