import os, Engine

COLORKEY = (128,160,128)
def getImages():
    # General Sprites
    IMAGESDICT = {}
    for root, dirs, files in os.walk('./Sprites/General/'):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                IMAGESDICT[name[:-4]] = Engine.image_load(full_name, convert_alpha=True)

    # Icon Sprites
    ICONDICT = {image[:-4]: Engine.image_load('./Sprites/Icons/' + image, convert_alpha=True) for image in os.listdir('./Sprites/Icons/') if image.endswith('.png')}
    
    # Item and Skill and Status sprites
    ITEMDICT = {image[:-4]: Engine.image_load('./Data/Items/' + image, convert=True) for image in os.listdir('./Data/Items/') if image.endswith('.png')}
    for image in ITEMDICT.values():
        Engine.set_colorkey(image, COLORKEY, rleaccel=True)

    # Unit Sprites
    UNITDICT = {}
    for root, dirs, files in os.walk('./Data/Characters/'):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                image = Engine.image_load(full_name, convert=True)
                Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                UNITDICT[name[:-4]] = image
    
    return IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT

def getSounds():
    # SFX Sounds
    class SoundDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key, Engine.BaseSound())

    sfxnameList = [sfx[:-4] for sfx in os.listdir('./Audio/sfx/') if sfx.endswith('.wav') or sfx.endswith('.ogg')]
    sfxList = [Engine.create_sound('./Audio/sfx/' + sfx) for sfx in os.listdir('./Audio/sfx/') if sfx.endswith('.wav') or sfx.endswith('.ogg')]
    SOUNDDICT = SoundDict(zip(sfxnameList, sfxList))

    class MusicDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key)

    musicnameList = [music[:-4] for music in os.listdir('./Audio/music/') if music.endswith('.ogg')]
    musicList = [('./Audio/music/' + music) for music in os.listdir('./Audio/music/') if music.endswith('.ogg')]
    MUSICDICT = MusicDict(zip(musicnameList, musicList))

    set_sound_volume(1.0, SOUNDDICT)

    return SOUNDDICT, MUSICDICT

def set_sound_volume(volume, SOUNDDICT):
    for name, sound in SOUNDDICT.iteritems():
        sound.set_volume(volume)
    # Sets cursor sound volume
    SOUNDDICT['Select 5'].set_volume(.5*volume)

if __name__ == '__main__':
    getImages()
