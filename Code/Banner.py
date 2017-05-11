#! usr/bin/env python2.7

from imagesDict import getImages
from GlobalConstants import *

import MenuFunctions, CustomObjects, Engine, Image_Modification

class Banner(object):
    def __init__(self):
        self.banner = ""
        self.item = None
        self.write_index = 4 # Keeps track of where we should start blitting word
        self.updateflag = False
        self.time_to_wait = 300
        self.time_to_start = None
        self.surf = None

    def figure_out_size(self):
        self.bannerlen = FONT['text_white'].size(''.join(self.banner))[0] + (16 if self.item else 0) # Only need width
        self.font_height = 16
        self.size = (self.bannerlen + 18, 24)

    def draw(self, surf, gameStateObj):
        self.write_index = 6
        if not self.surf:
            bg_surf = MenuFunctions.CreateBaseMenuSurf(self.size, 'BaseMenuBackgroundOpaque')
            self.surf = Engine.create_surface((self.size[0] + 2, self.size[1] + 4), convert=True, transparent=True)
            self.surf.blit(bg_surf, (2, 4))
            self.surf.blit(IMAGESDICT['SmallGem'], (0, 0))
            Image_Modification.flickerImageTranslucent(self.surf, 10)
        BGSurf = self.surf.copy()

        # Center it
        pos = surf.get_width()/2 - self.size[0]/2 - 2, surf.get_height()/2 - self.size[1]/2 - 4
        # Blit words
        for index, word in enumerate(self.banner):
            word_width = FONT[self.banner_font[index]].size(word)[0]
            FONT[self.banner_font[index]].blit(word, BGSurf, (self.write_index, self.size[1]/2 - self.font_height/2 + 4))
            self.write_index += word_width
        # Blit item icon
        if self.item:
            self.item.draw(BGSurf, (self.size[0] - 6 - 16 - 2, 4 + 4), cooldown=False)
        surf.blit(BGSurf, pos)

    def update(self, gameStateObj):
        if not self.updateflag:
            self.updateflag = True
            self.time_to_start = Engine.get_time()
            if self.sound:
                self.sound.play()

class acquiredItemBanner(Banner):
    def __init__(self, unit, item):
        Banner.__init__(self) # Super
        self.unit = unit
        self.item = item
        self.article = 'an' if self.item.name[0] in ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U'] else 'a'
        self.banner = [unit.name, ' got ', self.article, ' ', item.name, '.']
        self.banner_font = ['text_blue', 'text_white', 'text_white', 'text_white', 'text_blue', 'text_blue']
        self.figure_out_size()
        self.sound = SOUNDDICT['Item']

class sent_to_convoyBanner(Banner):
    def __init__(self, item):
        Banner.__init__(self) # Super
        self.item = item 
        self.article = 'An' if self.item.name[0] in ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U'] else 'A'
        self.banner = [self.article, ' ', item.name, ' sent to convoy.']
        self.banner_font = ['text_white', 'text_white', 'text_blue', 'text_white']
        self.figure_out_size()
        self.sound = SOUNDDICT['Item']

class acquiredGoldBanner(Banner):
    def __init__(self, number):
        Banner.__init__(self) # Super
        self.number = number
        self.banner = ['Got ', str(self.number), ' gold.']
        self.banner_font = ['text_white', 'text_blue', 'text_blue']
        self.figure_out_size()
        self.sound = SOUNDDICT['Item']

class brokenItemBanner(Banner):
    def __init__(self, unit, item):
        Banner.__init__(self) # Super
        self.unit = unit
        self.item = item
        self.article = 'an' if self.item.name[0] in ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U'] else 'a'
        if item.booster:
            self.banner = [unit.name, ' used ', self.article, ' ', item.name, '.']
            self.sound = SOUNDDICT['Item']
        else:
            self.banner = [unit.name, ' broke ', self.article, ' ', item.name, '.']
            self.sound = None
        self.banner_font = ['text_blue', 'text_white', 'text_white', 'text_white', 'text_blue', 'text_blue']
        self.figure_out_size()

class gainedWexpBanner(Banner):
    def __init__(self, unit, wexp, weapon_type):
        Banner.__init__(self)
        self.unit = unit
        self.item = CustomObjects.WeaponIcon(weapon_type)
        self.banner = [unit.name, ' reached rank ', CustomObjects.WEAPON_EXP.number_to_letter(wexp)]
        self.sound = SOUNDDICT['Item']
        self.banner_font = ['text_white', 'text_white', 'text_blue']
        self.figure_out_size()

class foundNothingBanner(Banner):
    def __init__(self, unit):
        Banner.__init__(self)
        self.unit = unit
        self.banner = [unit.name, ' found nothing of note.']
        self.sound = None
        self.banner_font = ['text_blue', 'text_white']
        self.figure_out_size()

class switchPulledBanner(Banner):
    def __init__(self):
        Banner.__init__(self)
        self.banner = ['Switch pulled!']
        self.sound = SOUNDDICT['Item']
        self.banner_font = ['text_white']
        self.figure_out_size()

class miracleBanner(Banner):
    def __init__(self, unit, skill):
        Banner.__init__(self)
        self.unit = unit
        self.item = skill
        self.sound = SOUNDDICT['Item']
        self.banner = [skill.name, ' activated!']
        self.banner_font = ['text_blue', 'text_white']
        self.figure_out_size()

class tooFewUnitsBanner(Banner):
    def __init__(self):
        Banner.__init__(self)
        self.banner = ['You have lost too many members of your party.']
        self.sound = None
        self.banner_font = ['text_white']
        self.figure_out_size()

class gameSavedBanner(Banner):
    def __init__(self):
        Banner.__init__(self)
        self.banner = ['Progress Saved.']
        self.sound = SOUNDDICT['Item']
        self.banner_font = ['text_white']
        self.figure_out_size()

class gainedSkillBanner(Banner):
    def __init__(self, unit, skill):
        Banner.__init__(self) # Super
        self.unit = unit
        self.item = skill
        self.banner = [unit.name, ' learned ', skill.name, '.']
        self.banner_font = ['text_blue', 'text_white', 'text_blue', 'text_blue']
        self.figure_out_size()
        self.sound = SOUNDDICT['Item']

class stealBanner(Banner):
    def __init__(self, unit, item):
        Banner.__init__(self) # Super
        self.unit = unit
        self.item = item
        self.article = 'an' if self.item.name[0] in ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U'] else 'a'
        self.banner = [unit.name, ' stole ', self.article, ' ', item.name, '.']
        self.banner_font = ['text_blue', 'text_white', 'text_white', 'text_white', 'text_blue', 'text_blue']
        self.figure_out_size()
        self.sound = SOUNDDICT['Item']

# Lower banner that scrolls across bottom of screen
class Pennant(object):
    def __init__(self, text):
        self.text = text
        self.font = FONT['convo_white']
        self.text_width = self.font.size(self.text)[0]

        self.sprite_offset = 32

        self.width = WINWIDTH
        self.height = TILEHEIGHT
        self.back_surf = IMAGESDICT['PennantBG']

        self.text_counter = 0

    def draw(self, surf, gameStateObj):
        # Minimize sprite offset
        self.sprite_offset -= 4
        self.sprite_offset = max(0, self.sprite_offset)

        counter = self.text_counter

        # If cursor is all the way on the bottom of the map
        if gameStateObj.cursor.position[1] >= gameStateObj.map.height - 1:
            surf.blit(Engine.flip_vert(self.back_surf), (0, 0 - self.sprite_offset))
            while counter < self.width:
                self.font.blit(self.text, surf, (counter, 0 - self.sprite_offset))
                counter += self.text_width + 24
        else:
            surf.blit(self.back_surf, (0, WINHEIGHT - self.height + self.sprite_offset))
            while counter < self.width:
                self.font.blit(self.text, surf, (counter, WINHEIGHT - self.height + self.sprite_offset))
                counter += self.text_width + 24

        self.text_counter -= 1