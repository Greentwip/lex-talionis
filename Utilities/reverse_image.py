from PIL import Image

image = Image.open('Explosion-Image.png')
with open('Explosion-Index.txt') as fp:
    lines = [line.strip().split(';') for line in fp.readlines()]
new_image = Image.new('RGBA', image.size)

for line in lines:
    topleft = line[1].split(',')
    left = int(topleft[0])
    top = int(topleft[1])
    size = line[2].split(',')
    width = int(size[0])
    height = int(size[1])

    flip = image.crop((left, top, left+width, top+height))
    flip = flip.transpose(Image.FLIP_LEFT_RIGHT)
    new_image.paste(flip, (left, top))

new_image.save('FixedExplosion-Image.png')

