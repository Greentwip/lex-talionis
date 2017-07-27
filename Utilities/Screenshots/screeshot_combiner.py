from PIL import Image
import glob

new_image = Image.new('RGB', (240*3+2, 160*3+2))
count = 0
fp_list = ['TitleScreen3.png', 'Level5_2.png', 'Skill2.png', 'Combat1.png', 'Conversation1.png', 'Convoy1.png', 'Base2.png', 'Aura2.png', 'TransitionScreen2.png']
for fp in fp_list:
    image = Image.open(fp)
    width, height = image.size
    if width == 240 and height == 160:
        new_image.paste(image, (240*(count%3)+count%3, 160*(count/3)+count/3))
        count += 1

new_image.save('screenshot_compilation.png')