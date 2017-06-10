# Grass Randomizer
from PIL import Image, ImageChops
import random

def equal(im1, im2):
	return ImageChops.difference(im1.convert('RGB'), im2.convert('RGB')).getbbox() is None

grass_locs1 = [(1,2), (1,3), (1,4), (1,5), (2,2), (2,3), (2,4), (2,5), (3,3), (3,4), (3,5), (4,4), (4,5)]
grass_locs3 = [(1,2), (1,3), (1,4), (1,5), (2,2), (2,3), (2,4), (2,5), (3,3), (3,4), (3,5), (4,4), (4,5), (3,2)]
grass_locs2 = [(2,2), (2,3), (2,4), (2,5), (3,2), (3,3), (3,4), (3,5), (4,3), (4,4), (4,5), (5,4), (5,5)]
grass_locs = [(0,4), (0,5), (0,6), (0,7), (0,8), (0,9), (0,10), (1,5), (1,6), (1,7), (1,8), (1,9), (1,10)]
desert_locs = [(14, 25), (14, 26), (14, 27), (15, 25), (15, 26), (15, 27), (13, 25), (13, 26), (13,27), \
			   (14, 28), (14, 29), (14, 30), (15, 28), (15, 29), (15, 30), (13, 28), (13, 29), (13,30)]
snow_locs = [(2,2), (2,3), (2,4), (2,5), (3,2), (3,3), (3,4), (3,5), (4,3), (4,4), (4,5), (5, 4), (5,5), (1,7), (2,7)]
cobble_locs = [(4, 14), (4, 15), (4, 16)]
tile_locs = [(12, 26), (13, 26)]
tile2_locs = [(22, 25), (23, 25)]
v_wall_locs = [(15, 1), (16, 1), (17, 1)]
v_wall2_locs = [(10, 14), (11, 14), (11, 15)]
h_wall_locs = [(15, 0), (16, 0), (17, 0), (18, 0)]
h_wall2_locs = [(10, 13), (11, 13), (14, 14)]
c_locs = [(17, 26), (17, 28)]

locs = c_locs

marked_positions = []
grass = []

my_fp = 'MapSprite.png'
tileset = 'TileSet.png'

my_im = Image.open(my_fp)
my_ts = Image.open(tileset)


for x, y in locs:
	grass.append(my_ts.crop((x*16, y*16, x*16+16, y*16+16)))

# Get positions of grass
for i in range(my_im.size[0]/16):
	for j in range(my_im.size[1]/16):
		test_im = my_im.crop((i*16, j*16, i*16+16, j*16+16))
		if any([equal(grass_pic, test_im) for grass_pic in grass]):
			marked_positions.append((i, j))
			
# Randomize grass
for x,y in marked_positions:
	chosen_grass = random.choice(grass)
	my_im.paste(chosen_grass, (x*16, y*16))

# Save image
my_im.save('fixed' + my_fp)