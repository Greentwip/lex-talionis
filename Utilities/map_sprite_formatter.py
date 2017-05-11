#! usr/bin/env python

from PIL import Image

# === INPUTS ===
name = "AssassinF"
my_image = Image.open('AllFireEmblem.png', 'r')
x = 367
y = 4661
# === === ===

new_list = [];

# Get component images
for j in range(5):
	for i in range(5):
		left = x+33*i
		top = y+33*j
		new_list.append(my_image.crop((left, top, left+32, top+32)))

print new_list

# Create new image
static = Image.new('RGB', (192, 144))
move = Image.new('RGB', (192, 160))

static.paste(new_list[5], (16, 8))
static.paste(new_list[10], (64 + 16, 8))
static.paste(new_list[15], (64*2 + 16, 8))

static.paste(new_list[9], (16, 48*2+8))
static.paste(new_list[14], (64 + 16, 48*2+8))
static.paste(new_list[19], (64*2 + 16, 48*2+8))

move.paste(new_list[2], (8, 4))
move.paste(new_list[7], (8 + 48, 4))
move.paste(new_list[12], (8 + 48*2, 4))
move.paste(new_list[17], (8 + 48*3, 4))

move.paste(new_list[1], (8, 44))
move.paste(new_list[6], (8 + 48, 44))
move.paste(new_list[11], (8 + 48*2, 44))
move.paste(new_list[16], (8 + 48*3, 44))

move.paste(new_list[1].transpose(Image.FLIP_LEFT_RIGHT), (8, 84))
move.paste(new_list[6].transpose(Image.FLIP_LEFT_RIGHT), (8 + 48, 84))
move.paste(new_list[11].transpose(Image.FLIP_LEFT_RIGHT), (8 + 48*2, 84))
move.paste(new_list[16].transpose(Image.FLIP_LEFT_RIGHT), (8 + 48*3, 84))

move.paste(new_list[3], (8, 124))
move.paste(new_list[8], (8 + 48, 124))
move.paste(new_list[13], (8 + 48*2, 124))
move.paste(new_list[18], (8 + 48*3, 124))

static.save('player' + name + '.png')
move.save('player' + name + '_move.png')
