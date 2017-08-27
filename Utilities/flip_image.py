from PIL import Image
import glob

for fp in glob.glob('*.png'):
	im = Image.open(fp)
	im = im.transpose(Image.FLIP_LEFT_RIGHT)
	im.save(fp)
