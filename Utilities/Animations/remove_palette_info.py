import glob
from PIL import Image

for image in glob.glob('*.png'):
    print(image)
    im = Image.open(image)
    new_im = im.crop((0, 0, 240, 160))
    new_im.save(image)

print('Done!')
