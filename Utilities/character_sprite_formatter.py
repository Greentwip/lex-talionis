from PIL import Image

def replace_color(img):
    # Change color
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            current_color = img.getpixel((x,y))
            if current_color == (161, 199, 150):
                img.putpixel((x,y), (128, 160, 128))

im = Image.open("BaseSprites.png")
width, height = im.size

counter = 0
for x in range(1794, width, 128):
    for y in range(111, 1567, 112):
        new_im = im.crop((x, y, x + 128, y + 112))
        replace_color(new_im)
        new_im.save(str(counter) + "Portrait.png")
        counter += 1
    new_im = im.crop((x, 0, x + 128, 111))
    n = Image.new('RGB', (128, 112), (128, 160, 128))
    replace_color(new_im)
    n.paste(new_im, (0, 1))
    n.save(str(counter) + "Portrait.png")
    counter += 1
