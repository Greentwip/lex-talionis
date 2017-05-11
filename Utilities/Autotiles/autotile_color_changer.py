from PIL import Image
import os
for fp in os.listdir('.'):
	if fp.endswith('.png'):
		image = Image.open(fp)
		for x in range(image.size[0]):
		    for y in range(image.size[1]):
		        color = image.getpixel((x, y))
		        if color[0] == 8 and color[1] == 8 and color[2] == 8:
		            image.putpixel((x, y), (40, 248, 248))
		image.save(fp)