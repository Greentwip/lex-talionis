from PIL import Image
import palette_index

# creates a palette based on two exact pictures who only differ in palette
palette1 = palette_index.orson
palette2 = [(0, 0, 0) for _ in xrange(16)]
im1 = Image.open('palette1.png').convert('RGB')
im2 = Image.open('palette2.png').convert('RGB')
assert im1.size == im2.size
width, height = im1.size

for x in xrange(width):
    for y in xrange(height):
        color1 = im1.getpixel((x, y))
        color2 = im2.getpixel((x, y))
        if color1 in palette1:
            index = palette1.index(color1)
            palette2[index] = color2
        else:
            print(x, y, color1)

print('['),
for color in palette2:
    print('\t\t(%s, %s, %s),'%(color[0], color[1], color[2]))
print('\t\t]')
