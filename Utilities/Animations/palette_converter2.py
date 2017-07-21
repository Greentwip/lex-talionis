from PIL import Image

# Joshua
joshua = [(128, 160, 128), # Background
                (248, 248, 248), # White
                (248, 248, 208), # Light skin
                (248, 192, 144), # Med skin
                (112, 72, 48), # Dark skin
                (224, 48, 16), # Light Hair
                (160, 8, 8), # Med Hair
                (104, 8, 16), # Dark Hair
                (176, 208, 240), # Light Weapon/Leather
                (114, 146, 178), # Med Weapon/Leather
                (64, 96, 128), # Dark Weapon/String
                (128, 168, 168), # Light Clothes
                (88, 128, 128), # LM Clothes
                (48, 88, 88), # MD Clothes
                (24, 48, 48), # Dark Clothes
                (40, 40, 40)] # Outline

# Generic Red
enemy = [(128, 160, 128), # Background
                (248, 248, 248), # White
                (248, 248, 208), # Light skin
                (248, 192, 144), # Med skin
                (112, 72, 48), # Dark skin
                (216, 216, 224), # Light Hair
                (176, 176, 192), # Med Hair
                (112, 112, 144), # Dark Hair
                (176, 208, 240), # Light Weapon/Leather
                (120, 152, 184), # Med Weapon/Leather
                (80, 112, 144), # Dark Weapon/String
                (248, 192, 128), # Light Clothes
                (248, 136, 48), # LM Clothes
                (200, 0, 0), # MD Clothes
                (128, 0, 8), # Dark Clothes
                (40, 40, 40)] # Outline

# Generic blue
player = [(128, 160, 128), # Background
                (248, 248, 248), # White
                (248, 248, 208), # Light skin
                (248, 192, 144), # Med skin
                (112, 72, 48), # Dark skin
                (216, 216, 224), # Light Hair
                (176, 176, 192), # Med Hair
                (112, 112, 144), # Dark Hair
                (176, 208, 240), # Light Weapon/Leather
                (120, 152, 184), # Med Weapon/Leather
                (80, 112, 144), # Dark Weapon/String
                (128, 192, 248), # Light Clothes
                (48, 136, 248), # LM Clothes
                (40, 40, 200), # MD Clothes
                (48, 40, 128), # Dark Clothes
                (40, 40, 40)] # Outline

p1 = joshua
p2 = enemy

conversion = {p1[i]: p2[i] for i in xrange(len(p1))}
image_to_convert = 'new_spritesheet.png'

image = Image.open(image_to_convert)
width, height = image.size

for x in xrange(width):
        for y in xrange(height):
                color = image.getpixel((x, y))
                image.putpixel((x, y), conversion[color])

image.save('fixed' + image_to_convert)
