import os

from . import Engine, AnimationManager

COLORKEY = (128, 160, 128)
def getImages(home='./'):
    # General Sprites
    IMAGESDICT = {}

    def general_sprites(root, files):
        for name in files:
            if name.endswith('.png'):
                full_name = os.path.join(root, name)
                IMAGESDICT[name[:-4]] = Engine.image_load(full_name, convert_alpha=True)

    def traverse_non_recursive(dir_path):
        for root, dirs, files in os.walk(dir_path):
            general_sprites(root, files) 
            break

    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/Animations/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/CombatBackgrounds/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/CombatBackgrounds/platforms')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/Highlights/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/MenuBackgrounds/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/Minimap/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/Overworld/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/Panoramas/')
    traverse_non_recursive('Assets/Lex-Talionis/Sprites/General/Weather/')



    try:
        traverse_non_recursive('Assets/Lex-Talionis/Data/GeneralSprites/')
        traverse_non_recursive('Assets/Lex-Talionis/Data/GeneralSprites/Panoramas/')
        traverse_non_recursive('Assets/Lex-Talionis/Data/GeneralSprites/TitleBackground')
    except:
        pass

    # Icon Sprites
    loc = 'Assets/Lex-Talionis/Sprites/Icons/'
    ICONDICT = {image[:-4]: Engine.image_load(loc + image, convert_alpha=True) for image in os.listdir(loc) if image.endswith('.png')}
    
    # Item and Skill and Status sprites
    loc = 'Assets/Lex-Talionis/Data/Items/'
    ITEMDICT = {image[:-4]: Engine.image_load(loc + image, convert=True) for image in os.listdir(loc) if image.endswith('.png')}
    for image in ITEMDICT.values():
        Engine.set_colorkey(image, COLORKEY, rleaccel=True)

    # Unit Sprites
    UNITDICT = {}

    def traverse_characters(dir_path):
        for root, dirs, files in os.walk(dir_path):
            for name in files:
                if name.endswith('.png'):
                    full_name = os.path.join(root, name)
                    image = Engine.image_load(full_name, convert=True)
                    Engine.set_colorkey(image, COLORKEY, rleaccel=True)
                    UNITDICT[name[:-4]] = image
            break

    traverse_characters('Assets/Lex-Talionis/Data/Characters/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/NPCs/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/OtherCharacters/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/PlayerCharacters/')

    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/./')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Archer/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Assassin/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Ballista/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Berserker/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Bonewalker/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Brigand/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Cavalier/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Channeler/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Citizen/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Cleric/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Dracoknight/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Dracolord/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Dragoon/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Duke/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Fighter/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/General/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Halberdier/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Knight/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Lord/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Mage/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Mercenary/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Myrmidon/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Oracle/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Paladin/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Phantom/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Raider/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Retainer/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Revenant/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Sage/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Sentinel/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Shaman/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Skirmisher/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Sniper/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Soldier/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Strategist/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Swordmaster/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Tactician/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Thief/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Tiger/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Vanguard/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Wagon/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Warlock/')
    traverse_characters('Assets/Lex-Talionis/Data/Characters/MapSprites/Warrior/')


    # Battle Animations
    ANIMDICT = AnimationManager.BattleAnimationManager(COLORKEY, home)

    return IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT, ANIMDICT

def getSounds(home='./'):
    # SFX Sounds
    class SoundDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key, Engine.BaseSound())

    loc = home + 'Audio/sfx/'
    if os.path.isdir(loc):
        sfxnameList, sfxList = [], []
        for root, dirs, files in os.walk(loc):
            for name in files:
                if name.endswith('.wav') or name.endswith('.ogg'):
                    full_name = os.path.join(root, name)
                    sfxnameList.append(name[:-4])
                    sfxList.append(Engine.create_sound(full_name))
        SOUNDDICT = SoundDict(zip(sfxnameList, sfxList))
    else:
        SOUNDDICT = SoundDict()

    class MusicDict(dict):
        def __getitem__(self, key):
            return dict.get(self, key)

    loc = home + 'Audio/music/'
    if os.path.isdir(loc):
        musicnameList = [music[:-4] for music in os.listdir(loc) if music.endswith('.ogg')]
        musicList = [(loc + music) for music in os.listdir(loc) if music.endswith('.ogg')]
        MUSICDICT = MusicDict(zip(musicnameList, musicList))
        # Add additional names for the loops as well
        for idx, music_name in enumerate(musicnameList):
            if music_name.endswith(' - Start'):
                MUSICDICT[music_name[:-8]] = musicList[idx]
            elif music_name.endswith('- Start'):
                MUSICDICT[music_name[:-7]] = musicList[idx]               
    else:
        MUSICDICT = MusicDict()

    set_sound_volume(1.0, SOUNDDICT)

    return SOUNDDICT, MUSICDICT

sound_volume = 1.0
def set_sound_volume(volume, SOUNDDICT):
    global sound_volume
    sound_volume = volume
    for name, sound in SOUNDDICT.items():
        sound.set_volume(volume)
    # Sets cursor sound volume
    SOUNDDICT['Select 5'].set_volume(.5*volume)

if __name__ == '__main__':
    getImages()
