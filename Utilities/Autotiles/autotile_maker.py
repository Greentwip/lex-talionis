# Autotiles maker
from PIL import Image, ImageChops
fp = 'MapSprite_Autotile.png'
vertical = True
horizontal = False

image = Image.open(fp)

# Get column bands of the image
column_bands = []
if horizontal:
    for x in range(image.size[0]/16):
        column_bands.append(image.crop((x*16, 0, x*16+16, image.size[1])))
else:
    for y in range(image.size[1]/16):
        column_bands.append(image.crop((0, y*16, image.size[0], y*16+16)))

for num in range(16):
    new_image = Image.new('RGB', image.size)
    for idx, band in enumerate(column_bands):
        print(idx)
        offset = ImageChops.offset(band, num*horizontal, num*vertical)
        if horizontal:
            new_image.paste(offset, (idx*16, 0))
        else:
            new_image.paste(offset, (0, idx*16))
    new_image.save('autotile' + str(num) + '.png')