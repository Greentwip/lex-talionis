import os, Engine

COLORKEY = (128,160,128)
def getImages():
    # General Sprites
    spriteList, imageList = [], []
    for root, dirs, files in os.walk('./Sprites/General/'):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                spriteList.append(name[:-4])
                imageList.append(Engine.image_load(full_name, convert_alpha=True))
    IMAGESDICT = dict(zip(spriteList, imageList))

    # Icon Sprites
    iconList = [image[:-4] for image in os.listdir('./Sprites/Icons/') if image.endswith('.png')]
    imageList = [Engine.image_load('./Sprites/Icons/' + image, convert_alpha=True) for image in os.listdir('./Sprites/Icons/') if image.endswith('.png')]
    ICONDICT = dict(zip(iconList, imageList))
    
    # Item and Skill and Status sprites
    itemList = [image[:-4] for image in os.listdir('./Data/Items/') if image.endswith('.png')]
    imageList = [Engine.image_load('./Data/Items/' + image, convert=True) for image in os.listdir('./Data/Items/') if image.endswith('.png')]
    for image in imageList:
        Engine.set_colorkey(image, COLORKEY, rleaccel=True)
    ITEMDICT = dict(zip(itemList, imageList))

    # Unit Sprites
    unitnameList, imageList = [], []
    for root, dirs, files in os.walk('./Data/Characters/'):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                unitnameList.append(name[:-4])
                image = Engine.image_load(full_name, convert=True)
                Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                imageList.append(image)
    UNITDICT = dict(zip(unitnameList, imageList))
    
    return IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT

def getSounds():
    # SFX Sounds
    sfxnameList = [sfx[:-4] for sfx in os.listdir('./Audio/sfx/') if sfx.endswith('.wav') or sfx.endswith('.ogg')]
    sfxList = [Engine.create_sound('./Audio/sfx/' + sfx) for sfx in os.listdir('./Audio/sfx/') if sfx.endswith('.wav') or sfx.endswith('.ogg')]
    SOUNDDICT = dict(zip(sfxnameList, sfxList))

    musicnameList = [music[:-4] for music in os.listdir('./Audio/music/') if music.endswith('.ogg')]
    musicList = [('./Audio/music/' + music) for music in os.listdir('./Audio/music/') if music.endswith('.ogg')]
    MUSICDICT = dict(zip(musicnameList, musicList))

    set_sound_volume(1.0, SOUNDDICT)

    return SOUNDDICT, MUSICDICT

def set_sound_volume(volume, SOUNDDICT):
    for name, sound in SOUNDDICT.iteritems():
        sound.set_volume(volume)
    # Sets cursor sound volume
    SOUNDDICT['Select 5'].set_volume(.5*volume)

if __name__ == '__main__':
    getImages()
