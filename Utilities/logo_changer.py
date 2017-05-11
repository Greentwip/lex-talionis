#! usr/bin/env python2.7

from PIL import Image

fp = 'LogoFull.png'
x_cutoff = 126
y_size = 28
y_num = 8

old_pic = Image.open(fp)

new_pic = Image.new("RGBA", (x_cutoff, y_size*y_num*2))

second_width = old_pic.size[0] - x_cutoff
print(second_width)

for num in range(y_num):
	the_lion = old_pic.crop((0, num*y_size, x_cutoff, num*y_size+y_size))
	new_pic.paste(the_lion, (0, num*y_size*2))
	throne = old_pic.crop((x_cutoff, num*y_size, old_pic.size[0], num*y_size+y_size))
	new_pic.paste(throne, (x_cutoff/2 - second_width/2, num*y_size*2 + y_size))

new_pic.save('LogoNew.png')