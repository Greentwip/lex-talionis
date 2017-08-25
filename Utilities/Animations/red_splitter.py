# Red Splitter
from PIL import Image

image = 'ThunderDust.png'
offset = (147, 63)
CENTER = True

im = Image.open(image)
true_width, true_height = im.size

new_im = Image.new('RGB', (true_width, true_height))

split_indices = [0]
for x in xrange(true_width):
    for y in xrange(true_height):
        color = im.getpixel((x, y))
        if color[0] == 255:
            split_indices.append(x)
            color = (0, color[1], color[2])
        new_im.putpixel((x, y), color)

print(split_indices)
name = image[:-4]
index_script = open('new_index.txt', 'w')
for idx, x in enumerate(split_indices):
    print(idx, x, len(split_indices))
    width = (split_indices[idx + 1] - x) if len(split_indices) - 1 > idx else true_width - x
    to_write = name + ';' + str(x) + ',0;' + str(width) + ',' + str(true_height) + ';'
    if CENTER:
        this_offset = (offset[0] - width/2, offset[1])
    else:
        this_offset = offset
    index_script.write(to_write + str(this_offset[0]) + ',' + str(this_offset[1]) + '\n')

new_im.save('fixed' + image)
