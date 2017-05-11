import os
from PIL import Image

images = []
for fp in os.listdir('.'):
	if fp.endswith('.png') and fp.startswith('autotile'):
		images.append((fp, Image.open(fp)))

mask = Image.open('mask_autotile.png')

for fp, image in images:
    #image = Image.new('RGB', (448, 384))
    #image.paste(old_image, (80, 0))
    for x in range(image.size[0]):
        for y in range(image.size[1]):
            color = mask.getpixel((x, y))
            if color[0] == 128 and color[1] == 160 and color[2] == 128:
                image.putpixel((x, y), (128, 160, 128))
    image.save(fp)