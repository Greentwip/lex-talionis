import glob
from PIL import Image

for fp in glob.glob('*.png'):
	print(fp)
	image = Image.open(fp).convert('RGBA')
	width, height = image.size
	for x in xrange(width):
		for y in xrange(height):
			color = image.getpixel((x, y))
			# If totally transparent
			if color[3] == 0:
				image.putpixel((x, y), (0, 0, 0, 0))
	image.save(fp)
