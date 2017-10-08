# Gets palette from image

from PIL import Image
palette = set()

fp = 'palette.png'
im = Image.open(fp)
width, height = im.size

for x in range(width):
	for y in range(height):
		color = im.getpixel((x, y))
		palette.add(color)

for color in palette:
    print('\t\t(%s, %s, %s),'%(color[0], color[1], color[2]))
