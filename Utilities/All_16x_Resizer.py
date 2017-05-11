#! usr/bin/env python

from PIL import Image
import os

for fp in os.listdir('.'):
    if fp.endswith('.png'):
        picture = Image.open(fp)

        picture = picture.resize((16*picture.size[0], 16*picture.size[1]))
        picture.save('MapSprite' + fp[8:])
