import os
from PIL import Image
import numpy as np

loc = 'shaman_unique'
# Get all sprites
imageList = []
for root, dirs, files in os.walk(loc):
    for name in files:
        if name.endswith('.png'):
            full_name = os.path.join(root, name)
            imageList.append(full_name)

#http://stackoverflow.com/questions/9166400/convert-rgba-png-to-rgb-with-pil
def alpha_to_color(image, color=(128, 160, 128)):
	x = np.array(image)
	try:
		r, g, b, a = np.rollaxis(x, axis=-1)
	except ValueError:
		raise ValueError
	r[a == 0] = color[0]
	g[a == 0] = color[1]
	b[a == 0] = color[2]
	x = np.dstack([r, g, b, a])
	return Image.fromarray(x, 'RGBA')

for image in imageList:
	try:
		alpha_to_color(Image.open(image)).convert('RGB').save(image)
	except ValueError:
		continue