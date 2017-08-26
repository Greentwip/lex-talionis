import os
import Engine, AnimationManager

COLORKEY = (128, 160, 128)
def getImages(home='./'):
    # General Sprites
    IMAGESDICT = {}
    for root, dirs, files in os.walk(home + 'Sprites/General/'):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                IMAGESDICT[name[:-4]] = Engine.image_load(full_name, convert_alpha=True)

    # Icon Sprites
    loc = home + 'Sprites/Icons/'
    ICONDICT = {image[:-4]: Engine.image_load(loc + image, convert_alpha=True) for image in os.listdir(loc) if image.endswith('.png')}
    
    # Item and Skill and Status sprites
    loc = home + 'Data/Items/'
    ITEMDICT = {image[:-4]: Engine.image_load(loc + image, convert=True) for image in os.listdir(loc) if image.endswith('.png')}
    for image in ITEMDICT.values():
        Engine.set_colorkey(image, COLORKEY, rleaccel=True)

    # Unit Sprites
    UNITDICT = {}
    for root, dirs, files in os.walk(home + 'Data/Characters/'):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                image = Engine.image_load(full_name, convert=True)
                Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                UNITDICT[name[:-4]] = image

    # Battle Animations
    ANIMDICT = AnimationManager.BattleAnimationManager(COLORKEY, home)

    return IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT, ANIMDICT

def getSounds(home='./'):
    # SFX Sounds
    class SoundDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key, Engine.BaseSound())

    loc = home + 'Audio/sfx/'
    sfxnameList = [sfx[:-4] for sfx in os.listdir(loc) if sfx.endswith('.wav') or sfx.endswith('.ogg')]
    sfxList = [Engine.create_sound(loc + sfx) for sfx in os.listdir(loc) if sfx.endswith('.wav') or sfx.endswith('.ogg')]
    SOUNDDICT = SoundDict(zip(sfxnameList, sfxList))

    class MusicDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key)

    loc = home + 'Audio/music/'
    musicnameList = [music[:-4] for music in os.listdir(loc) if music.endswith('.ogg')]
    musicList = [(loc + music) for music in os.listdir(loc) if music.endswith('.ogg')]
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
