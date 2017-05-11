#! usr/bin/env python

from PIL import Image
import os

for fp in os.listdir('.'):
    if fp.endswith('.png'):
        picture = Image.open(fp)

        picture = picture.resize((picture.size[0]/2, picture.size[1]/2))
        picture.save(fp)
