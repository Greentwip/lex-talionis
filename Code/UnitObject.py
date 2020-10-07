import os
from collections import Counter

from . import GlobalConstants as GC
from . import configuration as cf
from . import static_random
from . import Utility, Engine, Image_Modification, TextChunk
from . import Aura, Banner, BaseMenuSurf, ClassData
from . import AStar, Weapons, UnitSprite, UnitSound
from . import Dialogue, StatusCatalog, Action

from Code.StatObject import build_stat_dict_plus  # Needed so old saves can load

import logging
logger = logging.getLogger(__name__)

class Multiset(Counter):
    def __contains__(self, item):
        return self[item] > 0

# === GENERIC UNIT OBJECT =====================================================
class UnitObject(object):
    x_positions = (0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6, 6, 5, 4, 3, 2, 1)
    y_positions = (0, 1, 2, 3, 3, 3, 3, 3, 3, 3, 2, 1, 0, 0, 0, 0, 0, 0)

# === INITIALIZATION ==========================================================    
    def __init__(self, info):
        # --- Basic properties
        self.id = info['u_id']
        self.event_id = info['event_id']
        self.position = self.previous_position = info['position']
        self.name = info['name']
        self.team = info['team']
        self.party = info.get('party', 0)
        self.faction_icon = info.get('faction_icon', 'Neutral')
        self.klass = info['klass']
        self.gender = int(info['gender'])
        self.level = int(info['level'])
        self.exp = int(info.get('exp', 0))
        
        # --- Optional tags and Skills
        self._tags = info['tags']
        self.status_effects = []
        self.status_bundle = Multiset()

        if 'desc' in info and info['desc'] is not None:
            self.desc = info['desc']
        else:
            self.desc = self.name

        # In order, HP, STR, MAG, SKL, SPD, LCK, DEF, RES -- CON -- MOV
        self.growths = info['growths']
        self.growth_points = info['growth_points']

        # --- Stats
        if isinstance(info['stats'], list):
            self.stats = build_stat_dict_plus(info['stats'])
        else:
            self.stats = info['stats']
        self.currenthp = info.get('currenthp') or int(self.stats['HP'])
        self.change_hp(0)  # Just checking bounds

        # --- handle movement
        self.movement_left = self.stats['MOV']
        self.movement_group = info['movement_group']

        # --- Rescue
        self.TRV = info.get('TRV', 0)
        self.strTRV = "---"

        # --- Weapon experience points
        self.wexp = info['wexp']

        # -- Fatigue
        self.fatigue = int(info.get('fatigue', 0))

        # --- Item list
        self.items = []

        # --- The Units AI
        self.get_ai(info['ai'])

        # --- Stats -- this level
        self.records = info.get('records', self.default_records())

        self.portrait_id = info.get('portrait_id', self.id)

        # --- Other Properties (Update related normally)
        self.validPartners = [] # Used by selection algorithms
        self.current_skill = None

        self.dead = info.get('dead', False)
        self.deathCounter = 0

        self.arrowCounter = 0
        self.arrowAnim = [0, 1, 2]
        self.flicker = None
        self.flickerRed = False
        self.loadSprites()
        self.movement_sound = UnitSound.UnitSound(self)

        # For x2 counter
        self.x2_counter = 0

        # --- Temporary Status
        self.reset()
        self.finished = info.get('finished', False)
        self.current_move_action = None
        self.current_arrive_action = None

        self.resetUpdates()
    
# === SPRITING ================================================================
# Mostly handled by Unit Sprite class
    def draw(self, surf, gameStateObj):
        if self.position:
            self.sprite.draw(surf, gameStateObj)

    def draw_hp(self, surf, gameStateObj):
        if self.position:
            self.sprite.draw_hp(surf, gameStateObj)
    
    def removeSprites(self):
        self.sprite.removeSprites()
        self.portrait = None
        self.bigportrait = None 

    def loadSprites(self):
        # Load sprites
        self.sprite = UnitSprite.UnitSprite(self)
        self.sprite.loadSprites()
        self.generic_flag = False
        try:
            # Ex: HectorPortrait
            self.bigportrait = Engine.subsurface(GC.UNITDICT[str(self.portrait_id) + 'Portrait'], (0, 0, 96, 80))
            self.portrait = Engine.subsurface(GC.UNITDICT[str(self.portrait_id) + 'Portrait'], (96, 16, 32, 32))
        except KeyError:
            self.generic_flag = True
            self.bigportrait = GC.UNITDICT['Generic_Portrait_' + self.klass]
            self.portrait = GC.UNITDICT[self.faction_icon + 'Emblem']
        # Generate Animation
        # GC.ANIMDICT.generate(self.klass)
        self.battle_anim = None

    def begin_flicker(self, time, color=(255, 255, 255)):
        self.flicker = (Engine.get_time(), time, color)

    def end_flicker(self):
        self.flicker = None

# === MENUS ===================================================================
    def createPortrait(self):
        PortraitDimensions = (112, 40)
        PortraitWidth, PortraitHeight = PortraitDimensions
        # Create Surface to be blitted
        # Blit background of surface
        PortraitSurface = GC.IMAGESDICT['PortraitInfo'].copy()
        top = 4
        left = 6
        # Blit Portrait
        PortraitSurface.blit(self.portrait, (left + 1 + 16 - self.portrait.get_width()//2, top + 4 + 16 - self.portrait.get_height()//2))
        # Blit Name
        name = self.name
        # If generic, include level in name
        if self.generic_flag:
            short_name = ClassData.class_dict[self.klass]['short_name']
            name = short_name + ' ' + str(self.level)
        position = (left + PortraitWidth//2 + 6 - GC.FONT['info_grey'].size(name)[0]//2, top + 4)
        GC.FONT['info_grey'].blit(name, PortraitSurface, position)
        # Blit Health Text
        PortraitSurface.blit(GC.IMAGESDICT['InfoHP'], (34 + left, PortraitHeight - 20 + top))
        PortraitSurface.blit(GC.IMAGESDICT['InfoSlash'], (68 + left, PortraitHeight - 19 + top))
        current_hp = str(self.currenthp)
        max_hp = str(self.stats['HP'])
        GC.FONT['info_grey'].blit(current_hp, PortraitSurface, (66 + left - GC.FONT['info_grey'].size(current_hp)[0], 16 + top))
        GC.FONT['info_grey'].blit(max_hp, PortraitSurface, (90 + left - GC.FONT['info_grey'].size(max_hp)[0], 16 + top))
        # Blit Health Bar Background
        HealthBGSurf = GC.IMAGESDICT['HealthBar2BG']
        topleft = (36 + left, PortraitHeight - 10 + top)
        PortraitSurface.blit(HealthBGSurf, topleft)
        # Blit Health Bar
        hp_ratio = Utility.clamp(self.currenthp/float(self.stats['HP']), 0, 1)
        if hp_ratio > 0:
            indexpixel = int(hp_ratio*GC.IMAGESDICT['HealthBar2'].get_width())
            HealthSurf = Engine.subsurface(GC.IMAGESDICT['HealthBar2'], (0, 0, indexpixel, 2))
            topleft = (37 + left, PortraitHeight - 9 + top)
            PortraitSurface.blit(HealthSurf, topleft)

        # Blit weapon icon
        current_weapon = self.getMainWeapon()
        if current_weapon:
            current_weapon.draw(PortraitSurface, (PortraitWidth - 20 + left, PortraitHeight//2 - 8 + top))
        return PortraitSurface

    def create_attack_info(self, gameStateObj, enemyunit):
        def blit_num(surf, num, x_pos, y_pos):
            if not isinstance(num, str) and num >= 100:
                surf.blit(GC.IMAGESDICT['blue_100'], (x_pos - 16, y_pos))
            else:
                size = GC.FONT['text_blue'].size(str(num))
                position = x_pos - size[0], y_pos
                GC.FONT['text_blue'].blit(str(num), surf, position)

        if gameStateObj.mode['rng'] == 'hybrid':
            surf = GC.IMAGESDICT['QuickAttackInfoHybrid'].copy()
        elif cf.CONSTANTS['crit']:
            surf = GC.IMAGESDICT['QuickAttackInfoCrit'].copy()
        else:
            surf = GC.IMAGESDICT['QuickAttackInfo'].copy()

        # Blit my name
        size = GC.FONT['text_white'].size(self.name)
        position = 43 - size[0]//2, 3
        GC.FONT['text_white'].blit(self.name, surf, position)
        # Blit enemy name
        size = GC.FONT['text_white'].size(enemyunit.name)
        y_pos = 84
        if not cf.CONSTANTS['crit']: y_pos -= 16
        if gameStateObj.mode['rng'] == 'hybrid': y_pos -= 16
        position = 26 - size[0]//2, y_pos
        GC.FONT['text_white'].blit(enemyunit.name, surf, position)
        # Blit name of enemy weapon
        if isinstance(enemyunit, UnitObject) and enemyunit.getMainWeapon():
            size = GC.FONT['text_white'].size(enemyunit.getMainWeapon().name)
            y_pos = 100
            if not cf.CONSTANTS['crit']: y_pos -= 16
            if gameStateObj.mode['rng'] == 'hybrid': y_pos -= 16
            position = 32 - size[0]//2, y_pos
            GC.FONT['text_white'].blit(enemyunit.getMainWeapon().name, surf, position)
        # Blit self HP
        blit_num(surf, self.currenthp, 64, 19)
        # Blit enemy hp
        blit_num(surf, enemyunit.currenthp, 20, 19)
        # Blit my MT
        mt = self.compute_damage(enemyunit, gameStateObj, self.getMainWeapon(), 'Attack')
        if gameStateObj.mode['rng'] == 'hybrid':
            hit = self.compute_hit(enemyunit, gameStateObj, self.getMainWeapon(), 'Attack')
            blit_num(surf, int(mt * float(hit) / 100), 64, 35)
        # Blit my Hit if not hybrid
        else:
            blit_num(surf, mt, 64, 35)
            hit = self.compute_hit(enemyunit, gameStateObj, self.getMainWeapon(), 'Attack')
            blit_num(surf, hit, 64, 51)
            # Blit crit, if applicable
            if cf.CONSTANTS['crit']:
                crit = self.compute_crit(enemyunit, gameStateObj, self.getMainWeapon(), 'Attack')
                blit_num(surf, crit, 64, 67)
        # Blit enemy hit and mt
        if not self.getMainWeapon().cannot_be_countered and isinstance(enemyunit, UnitObject) and enemyunit.getMainWeapon() and \
                (Utility.calculate_distance(self.position, enemyunit.position) in enemyunit.getMainWeapon().get_range(enemyunit) or 
                 'distant_counter' in enemyunit.status_bundle):
            e_mt = enemyunit.compute_damage(self, gameStateObj, enemyunit.getMainWeapon(), 'Defense')
            e_hit = enemyunit.compute_hit(self, gameStateObj, enemyunit.getMainWeapon(), 'Defense')
            if cf.CONSTANTS['crit']:
                e_crit = enemyunit.compute_crit(self, gameStateObj, enemyunit.getMainWeapon(), 'Defense')
            else:
                e_crit = 0
        else:
            e_mt = '--'
            e_hit = '--'
            e_crit = '--'
        if gameStateObj.mode['rng'] == 'hybrid':
            if e_mt == '--' or e_hit == '--':
                blit_num(surf, e_mt, 20, 35)
            else:
                blit_num(surf, int(e_mt * float(e_hit) / 100), 20, 35)
        else:
            blit_num(surf, e_mt, 20, 35)
            blit_num(surf, e_hit, 20, 51)
            if cf.CONSTANTS['crit']:
                blit_num(surf, e_crit, 20, 67)

        return surf

    def displayAttackInfo(self, surf, gameStateObj, enemyunit):
        if not gameStateObj.info_surf:
            gameStateObj.info_surf = self.create_attack_info(gameStateObj, enemyunit)

        # Find topleft
        if gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1:
            topleft = GC.TILEWIDTH//2, GC.TILEHEIGHT//4
            topleft = (topleft[0] - self.attack_info_offset, topleft[1])
        else:
            topleft = GC.WINWIDTH - 69 - GC.TILEWIDTH//2, GC.TILEHEIGHT//4
            topleft = (topleft[0] + self.attack_info_offset, topleft[1])
        if self.attack_info_offset > 0:
            self.attack_info_offset -= 20

        surf.blit(gameStateObj.info_surf, topleft)

        # Blit my item -- This gets blit every frame
        white = False
        if isinstance(enemyunit, UnitObject):
            if enemyunit.check_effective(self.getMainWeapon()):
                white = True
        else:  # Tile Object
            if self.getMainWeapon().extra_tile_damage:
                white = True
        self.getMainWeapon().draw(surf, (topleft[0] + 2, topleft[1] + 4), white)
        # Blit enemy item
        if isinstance(enemyunit, UnitObject) and enemyunit.getMainWeapon():
            white = False
            if self.check_effective(enemyunit.getMainWeapon()):
                white = True
            y_pos = topleft[1] + 83
            if not cf.CONSTANTS['crit']: y_pos -= 16
            if gameStateObj.mode['rng'] == 'hybrid': y_pos -= 16
            enemyunit.getMainWeapon().draw(surf, (topleft[0] + 50, y_pos), white)

        # Blit advantage -- This must be blit every frame
        if isinstance(enemyunit, UnitObject) and self.checkIfEnemy(enemyunit):
            advantage, e_advantage = Weapons.TRIANGLE.compute_advantage(self.getMainWeapon(), enemyunit.getMainWeapon())
            UpArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (self.arrowAnim[self.arrowCounter]*7, 0, 7, 10))
            DownArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (self.arrowAnim[self.arrowCounter]*7, 10, 7, 10))
            if advantage > 0:
                surf.blit(UpArrow, (topleft[0] + 13, topleft[1] + 8))
            elif advantage < 0:
                surf.blit(DownArrow, (topleft[0] + 13, topleft[1] + 8))
            y_pos = topleft[1] + 89
            if not cf.CONSTANTS['crit']: y_pos -= 16
            if gameStateObj.mode['rng'] == 'hybrid': y_pos -= 16
            if e_advantage > 0:
                surf.blit(UpArrow, (topleft[0] + 61, y_pos))
            elif e_advantage < 0:
                surf.blit(DownArrow, (topleft[0] + 61, y_pos))
                
        # Blit doubling -- This gets blit every frame
        if isinstance(enemyunit, UnitObject):
            x2_position_player = (topleft[0] + 63 + self.x_positions[self.x2_counter] - 4, topleft[1] + 38 + self.y_positions[self.x2_counter])
            x2_position_enemy = (topleft[0] + 20 + self.x_positions[self.x2_counter], topleft[1] + 38 + self.y_positions[self.x2_counter])
            
            my_wep = self.getMainWeapon()

            my_num = 1
            if not my_wep.no_double:
                if my_wep.brave or my_wep.brave_attack:
                    my_num *= 2
                if self.outspeed(enemyunit, my_wep, gameStateObj, "Attack"):
                    my_num *= 2
                if my_wep.uses or my_wep.c_uses or my_wep.cooldown:
                    if my_wep.uses:
                        my_num = min(my_num, my_wep.uses.uses)
                    if my_wep.c_uses:
                        my_num = min(my_num, my_wep.c_uses.uses)
                    if my_wep.cooldown and my_wep.cooldown.charged:
                        my_num = min(my_num, my_wep.cooldown.cd_uses)

            if my_num == 2:
                surf.blit(GC.IMAGESDICT['x2'], x2_position_player)
            elif my_num == 3:
                surf.blit(GC.IMAGESDICT['x3'], x2_position_player)
            elif my_num == 4:
                surf.blit(GC.IMAGESDICT['x4'], x2_position_player)

            # ie if weapon can be countered
            if not my_wep.cannot_be_countered:
                e_wep = enemyunit.getMainWeapon()

                # Check enemy vs player
                e_num = 1
                if e_wep and not e_wep.no_double and isinstance(enemyunit, UnitObject) and \
                        Utility.calculate_distance(self.position, enemyunit.position) in e_wep.get_range(enemyunit):
                    if e_wep.brave or e_wep.brave_defense:
                        e_num *= 2
                    if (cf.CONSTANTS['def_double'] or 'def_double' in enemyunit.status_bundle) and \
                            enemyunit.outspeed(self, e_wep, gameStateObj, "Defense"):
                        e_num *= 2
                if e_num == 2:
                    surf.blit(GC.IMAGESDICT['x2'], x2_position_enemy)
                elif e_num == 4:
                    surf.blit(GC.IMAGESDICT['x4'], x2_position_enemy)

    def create_spell_info(self, gameStateObj, otherunit):
        if self.getMainSpell().spell.targets in ['Ally', 'Enemy', 'Unit']:
            height = 2
            if self.getMainSpell().damage is not None:
                height += 1
            if self.getMainSpell().hit is not None:
                height += 1

            BGSurf = GC.IMAGESDICT['Spell_Window' + str(height)]
            BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, 10)
            width, height = BGSurf.get_width(), BGSurf.get_height()

            running_height = 8

            GC.FONT['text_white'].blit(otherunit.name, BGSurf, (30, running_height))

            running_height += 16
            # Blit HP
            GC.FONT['text_yellow'].blit('HP', BGSurf, (9, running_height))
            # Blit /
            GC.FONT['text_yellow'].blit('/', BGSurf, (width - 25, running_height))
            # Blit stats['HP']
            maxhp_size = GC.FONT['text_blue'].size(str(otherunit.stats['HP']))
            GC.FONT['text_blue'].blit(str(otherunit.stats['HP']), BGSurf, (width - 5 - maxhp_size[0], running_height))
            # Blit currenthp
            currenthp_size = GC.FONT['text_blue'].size(str(otherunit.currenthp))
            GC.FONT['text_blue'].blit(str(otherunit.currenthp), BGSurf, (width - 26 - currenthp_size[0], running_height))

            if self.getMainSpell().damage is not None:
                running_height += 16
                mt = self.compute_damage(otherunit, gameStateObj, self.getMainSpell(), 'Attack')
                GC.FONT['text_yellow'].blit('Mt', BGSurf, (9, running_height))
                mt_size = GC.FONT['text_blue'].size(str(mt))[0]
                GC.FONT['text_blue'].blit(str(mt), BGSurf, (width - 5 - mt_size, running_height))

            if self.getMainSpell().hit is not None:
                running_height += 16
                GC.FONT['text_yellow'].blit('Hit', BGSurf, (9, running_height))
                hit = self.compute_hit(otherunit, gameStateObj, self.getMainSpell(), 'Attack')
                if hit >= 100:
                    BGSurf.blit(GC.IMAGESDICT['blue_100'], (width - 5 - 16, running_height))
                else:
                    hit_size = GC.FONT['text_blue'].size(str(hit))[0]
                    position = width - 5 - hit_size, running_height
                    GC.FONT['text_blue'].blit(str(hit), BGSurf, position)

            if cf.CONSTANTS['crit'] and self.getMainSpell().crit is not None:
                running_height += 16
                GC.FONT['text_yellow'].blit('Crit', BGSurf, (9, running_height))
                crit = self.compute_crit(otherunit, gameStateObj, self.getMainSpell(), 'Attack')
                if crit >= 100:
                    BGSurf.blit(GC.IMAGESDICT['blue_100'], (width - 5 - 16, running_height))
                else:
                    hit_size = GC.FONT['text_blue'].size(str(crit))[0]
                    position = width - 5 - hit_size, running_height
                    GC.FONT['text_blue'].blit(str(crit), BGSurf, position)

            # Blit name
            running_height += 16
            self.getMainSpell().draw(BGSurf, (8, running_height))
            name_width = GC.FONT['text_white'].size(self.getMainSpell().name)[0]
            GC.FONT['text_white'].blit(self.getMainSpell().name, BGSurf, (24 + 24 - name_width//2, running_height))

            return BGSurf

        elif self.getMainSpell().spell.targets.startswith('Tile'):
            """if self.getMainSpell().damage is None and self.getMainSpell().hit is None:
                return None"""
            height = 24
            if self.getMainSpell().damage is not None:
                height += 16
            # if self.getMainSpell().hit is not None:
            #     height += 16
            real_surf = BaseMenuSurf.CreateBaseMenuSurf((80, height), 'BaseMenuBackgroundOpaque')
            BGSurf = Engine.create_surface((real_surf.get_width() + 2, real_surf.get_height() + 4), transparent=True, convert=True)
            BGSurf.blit(real_surf, (2, 4))
            BGSurf.blit(GC.IMAGESDICT['SmallGem'], (0, 0))
            shimmer = GC.IMAGESDICT['Shimmer1']
            BGSurf.blit(shimmer, (BGSurf.get_width() - shimmer.get_width() - 1, BGSurf.get_height() - shimmer.get_height() - 5))
            BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, 10)
            width, height = BGSurf.get_width(), BGSurf.get_height()

            running_height = -10

            if self.getMainSpell().damage is not None:
                running_height += 16
                mt = self.damage(gameStateObj, self.getMainSpell())
                GC.FONT['text_yellow'].blit('Mt', BGSurf, (5, running_height))
                mt_size = GC.FONT['text_blue'].size(str(mt))[0]
                GC.FONT['text_blue'].blit(str(mt), BGSurf, (width - 5 - mt_size, running_height))

            # if self.getMainSpell().hit is not None:
            #     running_height += 16
            #     GC.FONT['text_yellow'].blit('Hit', BGSurf, (5, running_height))
            #     hit = self.accuracy(gameStateObj, self.getMainSpell())
            #     if hit >= 100:
            #         BGSurf.blit(GC.IMAGESDICT['blue_100'], (width - 5 - 16, running_height))
            #     else:
            #         hit_size = GC.FONT['text_blue'].size(str(hit))[0]
            #         position = width - 5 - hit_size, running_height
            #         GC.FONT['text_blue'].blit(str(hit), BGSurf, position)

            # Blit name
            running_height += 16
            self.getMainSpell().draw(BGSurf, (4, running_height))
            name_width = GC.FONT['text_white'].size(self.getMainSpell().name)[0]
            GC.FONT['text_white'].blit(self.getMainSpell().name, BGSurf, (24 + 24 - name_width//2, running_height))

            return BGSurf

    def displaySpellInfo(self, surf, gameStateObj, otherunit=None):
        if not gameStateObj.info_surf:
            gameStateObj.info_surf = self.create_spell_info(gameStateObj, otherunit)
            if not gameStateObj.info_surf:
                return
        
        # Blit otherunit's passive Sprite
        width = gameStateObj.info_surf.get_width()
        if otherunit:
            unit_surf = otherunit.sprite.create_image('passive')

        if gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x() - 1:
            topleft = (4, 4)
            if otherunit:
                u_topleft = (16 - max(0, (unit_surf.get_width() - 16)//2), 12 - max(0, (unit_surf.get_width() - 16)//2))
        else:
            topleft = (GC.WINWIDTH - 4 - width, 4)
            if otherunit:
                u_topleft = (GC.WINWIDTH - width + 8 - max(0, (unit_surf.get_width() - 16)//2), 12 - max(0, (unit_surf.get_width() - 16)//2))

        surf.blit(gameStateObj.info_surf, topleft)
        if otherunit:
            surf.blit(unit_surf, u_topleft)

    def create_item_description(self, gameStateObj):
        """draws a box containing the item description, and then place the units big portrait over it"""
        surf = Engine.create_surface((98, 56 + 80), transparent=True)

        width, height = (96, 56) # ??
        item = gameStateObj.activeMenu.getSelection()
        
        real_surf = BaseMenuSurf.CreateBaseMenuSurf((width, height), 'BaseMenuBackgroundOpaque')
        BGSurf = Engine.create_surface((real_surf.get_width() + 2, real_surf.get_height() + 4), transparent=True, convert=True)
        BGSurf.blit(real_surf, (2, 4))
        BGSurf.blit(GC.IMAGESDICT['SmallGem'], (0, 0))
        # Now make translucent
        BGSurf = Image_Modification.flickerImageTranslucent(BGSurf, 10)

        if item.weapon and self.canWield(item):
            top = 4
            left = 2
            GC.FONT['text_white'].blit('Affin', BGSurf, (width//2 - GC.FONT['text_white'].size('Affin')[0] + left, 4 + top))
            GC.FONT['text_white'].blit('Atk', BGSurf, (5 + left, 20 + top))
            GC.FONT['text_white'].blit('AS', BGSurf, (width//2 + 5 + left, 20 + top))
            GC.FONT['text_white'].blit('Hit', BGSurf, (5 + left, 36 + top))
            GC.FONT['text_white'].blit('Avo', BGSurf, (width//2 + 5 + left, 36 + top))
        
            dam = str(self.damage(gameStateObj, item))
            acc = str(self.accuracy(gameStateObj, item))
            avo = str(self.avoid(gameStateObj, item))
            atkspd = str(self.attackspeed(gameStateObj, item))
            AtkWidth = GC.FONT['text_blue'].size(dam)[0]
            HitWidth = GC.FONT['text_blue'].size(acc)[0]
            AvoidWidth = GC.FONT['text_blue'].size(avo)[0]
            ASWidth = GC.FONT['text_blue'].size(atkspd)[0] 
            GC.FONT['text_blue'].blit(dam, BGSurf, (width//2 - 4 - AtkWidth + left, 20 + top))
            GC.FONT['text_blue'].blit(atkspd, BGSurf, (width - 8 - ASWidth + left, 20 + top))
            GC.FONT['text_blue'].blit(acc, BGSurf, (width//2 - 4 - HitWidth + left, 36 + top))
            GC.FONT['text_blue'].blit(avo, BGSurf, (width - 8 - AvoidWidth + left, 36 + top))

            item.drawType(BGSurf, width//2 + 8 + left, 3 + top)

        else: # assumes every non-weapon has a description
            if item.desc:
                words_in_item_desc = item.desc
            else:
                words_in_item_desc = "Cannot wield."
            lines = TextChunk.line_wrap(TextChunk.line_chunk(words_in_item_desc), width - 8, GC.FONT['text_white'])

            for index, line in enumerate(lines):
                GC.FONT['text_white'].blit(line, BGSurf, (4 + 2, 4+index*16 + 4))

        surf.blit(BGSurf, (0, 76))

        if gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x():
            rightflag = True
        else:
            rightflag = False

        if not self.generic_flag:
            BigPortraitSurf = self.bigportrait
            # If on the left, mirror the character portrait
            if not rightflag:
                BigPortraitSurf = Engine.flip_horiz(BigPortraitSurf)
            surf.blit(BigPortraitSurf, (2, 0))

        return surf

    def drawItemDescription(self, surf, gameStateObj):
        if not gameStateObj.info_surf:
            gameStateObj.info_surf = self.create_item_description(gameStateObj)

        if gameStateObj.cursor.position[0] > GC.TILEX//2 + gameStateObj.cameraOffset.get_x():
            topleft = (GC.WINWIDTH - 8 - gameStateObj.info_surf.get_width(), GC.WINHEIGHT - 8 - gameStateObj.info_surf.get_height())
        else:
            topleft = (8, GC.WINHEIGHT - 8 - gameStateObj.info_surf.get_height())

        surf.blit(gameStateObj.info_surf, topleft)

# === TARGETING AND OTHER UTILITY FUNCTIONS ===================================
    def leave(self, gameStateObj, test=False):
        if self.position:
            logger.debug('Leave %s %s %s', self, self.name, self.position)
            if gameStateObj.cursor.currentHoveredUnit is self:
                gameStateObj.cursor.remove_unit_display()
            if not test:
                gameStateObj.grid_manager.set_unit_node(self.position, None)
                gameStateObj.boundary_manager.leave(self, gameStateObj)
            self.remove_tile_status(gameStateObj)
        Aura.leave(self, gameStateObj)

    def arrive(self, gameStateObj, test=False):
        if self.position:
            logger.debug('Arrive %s %s %s', self, self.name, self.position)
            if not test:
                gameStateObj.grid_manager.set_unit_node(self.position, self)
                gameStateObj.boundary_manager.arrive(self, gameStateObj)
            self.acquire_tile_status(gameStateObj)
            Aura.arrive(self, gameStateObj)

    # Pathfinding algorithm
    def getPath(self, gameStateObj, goalPosition, ally_block=False):
        my_grid = gameStateObj.grid_manager.get_grid(self)
        pathfinder = AStar.AStar(self.position, goalPosition, my_grid, gameStateObj.map.width,
                                 gameStateObj.map.height, self.team, 'pass_through' in self.status_bundle)
        # Run the pathfinder
        pathfinder.process(gameStateObj, ally_block=ally_block)
        # return the path
        return pathfinder.path

    def getMainWeapon(self):
        return next((item for item in self.items if item.weapon and self.canWield(item) and self.canUse(item)), None)

    def getMainSpell(self):
        return next((item for item in self.items if item.spell and self.canWield(item) and self.canUse(item)), None)

    def hasRunAI(self):
        return self.hasRunGeneralAI

    def getAid(self):
        return GC.EQUATIONS.get_aid(self)

    def getWeight(self):
        return GC.EQUATIONS.get_weight(self)

    def canUse(self, item) -> bool:
        if item.uses and item.uses.uses <= 0:
            return False
        if item.c_uses and item.c_uses.uses <= 0:
            return False
        if item.cooldown and not item.cooldown.charged:
            return False
        return True

    def canWield(self, item) -> bool:
        """
        Returns True if it can be wielded/used, and False otherwise
        Now has support for no_weapons status
        """
        klass_wexp = ClassData.class_dict[self.klass]['wexp_gain']
        if (item.weapon or item.spell) and 'no_weapons' in self.status_bundle:
            return False
        if item.is_magic() and 'no_magic_weapons' in self.status_bundle:
            return False

        if item.class_locked:
            if self.klass not in item.class_locked:
                return False
        if item.gender_locked:
            if self.gender not in item.gender_locked:
                return False
        if item.tag_locked:
            if all(tag not in item.tag_locked for tag in self.tags):
                return False
                
        # if the item is a weapon
        if item.weapon:
            itemLvl = item.weapon.LVL
        elif item.spell:
            itemLvl = item.spell.LVL
        else:
            return True # does not have a level so it can be used

        if not itemLvl: # does not have a level so it can be used
            return True

        if item.TYPE:
            idx = Weapons.TRIANGLE.name_to_index[item.TYPE]
            # Filter by klass wexp
            my_wexp = self.wexp[idx] if klass_wexp[idx] else 0
        else:
            my_wexp = 1

        if itemLvl in Weapons.EXP.wexp_dict and my_wexp >= Weapons.EXP.wexp_dict[itemLvl]:
            return True
        elif my_wexp > 0:
            itemLvl = itemLvl.split(',')
            for n in itemLvl:
                if n in (self.id, self.klass, self.name, '--') or n in self.tags:
                    return True
        return False

    # Given an item or a list or an int, increase my wexp based on the types of the weapon
    def increase_wexp(self, item, gameStateObj, banner=True):
        old_wexp = self.wexp[:]
        if item is None:
            return
        if isinstance(item, list):
            for index, num in enumerate(item):
                self.wexp[index] += num
        elif isinstance(item, int):
            for index, num in enumerate(old_wexp):
                if num > 0:
                    self.wexp[index] += item
        else:  # Normal item
            increase = item.wexp if item.wexp is not None else 1
            if item.TYPE in Weapons.TRIANGLE.name_to_index:
                self.wexp[Weapons.TRIANGLE.name_to_index[item.TYPE]] += increase
        if banner:
            self.add_wexp_banner(old_wexp, self.wexp, gameStateObj)

    def add_wexp_banner(self, old_wexp, new_wexp, gameStateObj):
        wexp_partitions = [x[1] for x in Weapons.EXP.sorted_list]
        for index in range(len(old_wexp)):
            for value in reversed(wexp_partitions):
                if new_wexp[index] >= value and old_wexp[index] < value:
                    gameStateObj.banners.append(Banner.gainedWexpBanner(self, value, Weapons.TRIANGLE.index_to_name[index]))
                    gameStateObj.stateMachine.changeState('itemgain')
                    break

    def change_hp(self, dhp):
        self.currenthp += int(dhp)
        self.currenthp = Utility.clamp(self.currenthp, 0, int(self.stats['HP']))

    def set_hp(self, hp):
        self.currenthp = int(hp)
        self.currenthp = Utility.clamp(self.currenthp, 0, int(self.stats['HP']))

    def change_exp(self, dexp):
        self.exp += int(dexp)

    def set_exp(self, exp):
        self.exp = int(exp)

    @property
    def tags(self):
        return self._tags | ClassData.class_dict[self.klass]['tags']

    @tags.setter
    def tags(self, value):
        self._tags = value

    def capped_stats(self) -> bool:
        unit_klass = ClassData.class_dict[self.klass]
        max_stats = unit_klass['max']
        counter = 0
        for idx, stat in enumerate(self.stats.values()):
            if stat >= max_stats[idx]:
                print("Capped %s %s" % (idx, stat))
                counter += 1
        return counter

    def get_internal_level(self):
        unit_klass = ClassData.class_dict[self.klass]
        return Utility.internal_level(unit_klass['tier'], self.level, cf.CONSTANTS['max_level'])

    def can_promote_using(self, item):
        unit_klass = ClassData.class_dict[self.klass]
        allowed_classes = item.promotion
        max_level = unit_klass['max_level']
        return self.level >= max_level//2 and len(unit_klass['turns_into']) >= 1 \
            and (self.klass in allowed_classes or 'All' in allowed_classes)

    def can_use_booster(self, item):
        if item.permanent_stat_increase:
            # Test whether the permanent stat increase would actually do anything
            current_stats = list(self.stats.values())
            klass_max = ClassData.class_dict[self.klass]['max']
            stat_increase = item.permanent_stat_increase
            test = [(klass_max[i] - current_stats[i].base_stat) > 0 for i in range(len(stat_increase)) if stat_increase[i] > 0]
            return any(test)
        elif item.promotion:
            return self.can_promote_using(item)
        elif item.target_fatigue:
            return self.fatigue > 0
        else:
            return True

    def handle_booster(self, item, gameStateObj):
        Action.do(Action.UseItem(item), gameStateObj)
        if item.uses and item.uses.uses <= 0:
            gameStateObj.banners.append(Banner.brokenItemBanner(self, item))
            gameStateObj.stateMachine.changeState('itemgain')
            Action.do(Action.RemoveItem(self, item), gameStateObj)

        # Actually use item
        if item.permanent_stat_increase:
            gameStateObj.exp_gain_struct = (self, item.permanent_stat_increase, None, 'booster')
            gameStateObj.stateMachine.changeState('exp_gain')
        elif item.permanent_growth_increase:
            Action.do(Action.PermanentGrowthIncrease(self, item.permanent_growth_increase), gameStateObj)
        elif item.wexp_increase:
            Action.do(Action.GainWexp(self, item.wexp_increase), gameStateObj)
        elif item.target_fatigue:
            Action.do(Action.ChangeFatigue(self, int(item.target_fatigue)), gameStateObj)
        elif item.promotion:
            # Action.do(Action.Promote(self), gameStateObj)
            gameStateObj.exp_gain_struct = (self, 0, None, 'item_promote')
            gameStateObj.stateMachine.changeState('exp_gain')
        elif item.call_item_script:
            call_item_script = 'Data/callItemScript.txt'
            if os.path.isfile(call_item_script):
                gameStateObj.message.append(Dialogue.Dialogue_Scene(call_item_script, unit=self, unit2=item, tile_pos=self.position))
                gameStateObj.stateMachine.changeState('dialogue')

    def handle_forced_movement(self, other_pos, movement, gameStateObj, def_pos=None):
        move_mag = int(eval(movement.magnitude))
        new_pos = self.position
        
        if movement.mode == 'Push':
            # Get all positions on infinite raytraced vector from other_pos to self.position
            # This section is irrespective of the actual confines of the map
            y_slope = (self.position[1] - other_pos[1])
            x_slope = (self.position[0] - other_pos[0])
            infinite_position = self.position[0] + x_slope*10, self.position[1] + y_slope*10

            possible_positions = Utility.raytrace(self.position, infinite_position)
            path = possible_positions[::-1] # Reverse because travel_algorithm expects reversed path
            new_pos = Utility.travel_algorithm(gameStateObj, path, move_mag, self, gameStateObj.grid_manager.get_grid(self))
        elif movement.mode == 'Shove':
            new_position = self.check_shove(other_pos, move_mag, gameStateObj)
            if new_position:
                self.sprite.set_transition('fake_in')
                self.sprite.spriteOffset = [(self.position[0] - new_position[0])*GC.TILEWIDTH, (self.position[1] - new_position[1])*GC.TILEHEIGHT]
                new_pos = new_position
        elif movement.mode == 'Rescue':
            # print(movement.mode, other_pos)
            for pos in Utility.get_adjacent_positions(other_pos):
                # If in map and walkable and no other unit is there.
                if gameStateObj.map.check_bounds(pos) and gameStateObj.map.tiles[pos].get_mcost(self) < self.stats['MOV'] and \
                        not gameStateObj.grid_manager.get_unit_node(pos):
                    new_pos = pos
                    break
        elif movement.mode == 'Swap': # This simple thing will actually probably work
            new_pos = other_pos
        elif movement.mode == 'Warp':
            Action.do(Action.Warp(self, def_pos), gameStateObj)

        if movement.mode != 'Warp':
            if new_pos != self.position:
                Action.do(Action.ForcedMovement(self, new_pos), gameStateObj)

    def get_nearest_open_space(self, gameStateObj):
        for r in range(1, 15):
            positions = Utility.find_manhattan_spheres([r], self.position)
            positions = [pos for pos in positions if gameStateObj.map.check_bounds(pos)]
            for pos in positions:
                if not any(unit.position == pos for unit in gameStateObj.allunits):
                    return pos

    def check_shove(self, other_pos, move_mag, gameStateObj):
        pos_offset = (self.position[0] - other_pos[0], self.position[1] - other_pos[1])
        new_position = self.position[0] + pos_offset[0]*move_mag, self.position[1] + pos_offset[1]*move_mag

        if gameStateObj.map.check_bounds(new_position) and \
                not any(unit.position == new_position for unit in gameStateObj.allunits) and \
                gameStateObj.map.tiles[new_position].get_mcost(0) < 5: 
            return new_position
        return False

    # Stat-specific levelup function
    def level_up(self, gameStateObj, class_info):
        levelup_list = [0 for x in self.stats]
        growths = self.growths
        if self.team == 'player':
            leveling = int(gameStateObj.mode['growths'])
        else:
            leveling = cf.CONSTANTS['enemy_leveling']
            if leveling == 3: # Match player method
                leveling = int(gameStateObj.mode['growths'])

        r = static_random.get_levelup(self.id, self.level + class_info['tier'] * 100)
        
        if leveling in (0, 1): # Fixed or Random
            for index in range(8):
                growth = growths[index]
                if leveling == 1: # Fixed
                    levelup_list[index] = min((self.growth_points[index] + growth)//100, class_info['max'][index] - list(self.stats.values())[index].base_stat)
                    self.growth_points[index] = (self.growth_points[index] + growth)%100
                elif leveling == 0: # Random
                    while growth > 0:
                        levelup_list[index] += 1 if r.randint(0, 99) < growth else 0
                        growth -= 100
                    levelup_list[index] = min(levelup_list[index], class_info['max'][index] - list(self.stats.values())[index].base_stat)
        else: # Hybrid and Default
            growths = [growth if list(self.stats.values())[index].base_stat < class_info['max'][index] else 0 for index, growth in enumerate(growths)]
            growth_sum = sum(growths)
            num_choices = growth_sum//100
            self.growth_points[0] += growth_sum%100
            if self.growth_points[0] >= 100:
                self.growth_points[0] -= 100
                num_choices += 1

            for _ in range(num_choices):
                if sum(growths) <= 0:
                    break
                index = static_random.weighted_choice(growths, r)
                levelup_list[index] += 1
                growths[index] = max(0, growths[index] - 100)
                if list(self.stats.values())[index].base_stat + levelup_list[index] >= class_info['max'][index]:
                    growths[index] = 0

        return levelup_list

    # For regular levels
    def apply_levelup(self, levelup_list, hp_up=False):
        logger.debug("Applying levelup %s to %s", levelup_list, self.name)
        # Levelup_list should be a len(8) list.
        for idx, name in enumerate(GC.EQUATIONS.stat_list):
            self.stats[name].base_stat += levelup_list[idx]
        # Handle the case where this is done in base
        if hp_up:
            self.change_hp(levelup_list[0])

    # For bonuses
    def apply_stat_change(self, levelup_list):
        logger.debug("Applying stat change %s to %s", levelup_list, self.name)
        for idx, name in enumerate(GC.EQUATIONS.stat_list):
            self.stats[name].bonuses += levelup_list[idx]

        # Handle changed cases
        self.change_hp(0)
        if self.movement_left > int(self.stats['MOV']):
            self.movement_left = max(0, int(self.stats['MOV']))

    def apply_growth_mod(self, growth_mod):
        logger.debug("Applying growth modification %s to %s", growth_mod, self.name)
        self.growths = [a + b for a, b in zip(self.growths, growth_mod)]
        
# === TILE ALGORITHMS ===
    # Kind of a wrapper around the recursive algorithm for finding movement
    def getValidMoves(self, gameStateObj, force=False):
        if not force and self.hasMoved and (not self.has_canto() or self.isDone()): # No Valid moves once moved
            return set()
        if not self.position:  # Not sure how this is possible...
            return set()
        my_grid = gameStateObj.grid_manager.get_grid(self)
        pathfinder = AStar.Djikstra(self.position, my_grid, gameStateObj.map.width, gameStateObj.map.height, self.team, 'pass_through' in self.status_bundle)
        # Run the pathfinder
        movement_left = self.movement_left if not force else int(self.stats['MOV'])
        # Makes ai zero move appear as zero move
        if cf.CONSTANTS['zero_move'] and self.team != 'player' and self.ai and not self.ai.can_move():
            movement_left = 0
        ValidMoves = pathfinder.process(gameStateObj.grid_manager.team_map, movement_left)
        # Own position is always a valid move
        ValidMoves.add(self.position)
        return ValidMoves
        
    def displayMoves(self, gameStateObj, ValidMoves, light=False):
        kind = 'possible_move' if light else 'move'
        for validmove in ValidMoves:
            gameStateObj.highlight_manager.add_highlight(validmove, kind)

    # Uses all weapons the unit has access to find its potential range
    def findPotentialRange(self, spell=False, both=False, boundary=False):
        if both:
            allWeapons = \
                [item for item in self.items if self.canWield(item) and 
                 self.canUse(item) and (item.weapon or (item.spell and item.detrimental))]
        elif spell:
            allWeapons = [item for item in self.items if item.spell and self.canWield(item) and self.canUse(item)]
            if boundary:
                allWeapons = [item for item in self.items if item.detrimental]
        else:
            allWeapons = [item for item in self.items if item.weapon and self.canWield(item) and self.canUse(item)]
        if not allWeapons:
            return []
        potentialRange = []
        for item in allWeapons:
            for rng in item.get_range(self):
                potentialRange.append(rng)
        return list(set(potentialRange)) # Remove duplicates

    def getMaxRange(self):
        allItems = [item for item in self.items if (item.spell or item.weapon) and self.canWield(item)]
        if not allItems:
            return 0
        maxRange = max([max(item.get_range(self)) for item in allItems])
        return maxRange

    # Gets location of every possible attack given all ValidMoves
    def getExcessAttacks(self, gameStateObj, ValidMoves, both=False, boundary=False):
        potentialRange = self.findPotentialRange(both=both)

        ValidAttacks = Utility.get_shell(ValidMoves, potentialRange, gameStateObj.map)
        # Can't attack own team -- maybe not necessary?
        if not boundary:
            ValidAttacks = [pos for pos in ValidAttacks if not gameStateObj.compare_teams(self.team, gameStateObj.grid_manager.get_team_node(pos))]

        if cf.CONSTANTS['line_of_sight'] and potentialRange:
            ValidAttacks = Utility.line_of_sight(ValidMoves, ValidAttacks, max(potentialRange), gameStateObj)
        return ValidAttacks

    def displayExcessAttacks(self, gameStateObj, ValidMoves, both=False, light=False):
        ValidAttacks = self.getExcessAttacks(gameStateObj, ValidMoves, both)

        kind = 'splash' if light else 'attack'
        for validattack in ValidAttacks:
            gameStateObj.highlight_manager.add_highlight(validattack, kind)

    # gets all possible attack positions, assuming unit has not moved yet. If unit has moved, use get all targets
    def getExcessSpellAttacks(self, gameStateObj, ValidMoves, boundary=False):
        potentialRange = self.findPotentialRange(spell=True, boundary=boundary)

        ValidAttacks = Utility.get_shell(ValidMoves, potentialRange, gameStateObj.map)

        # Now filter based on types of spells I've used
        # There are three types of spells, ALLY, ENEMY, TILE
        if not boundary:
            my_spells = [item for item in self.items if item.spell and self.canWield(item) and self.canUse(item)]
            # If can only hit allies, ignore enemies
            if all(["Ally" == spell.spell.targets for spell in my_spells]):
                enemy_unit_positions = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfEnemy(unit)]
                ValidAttacks = [pos for pos in ValidAttacks if pos not in enemy_unit_positions]
            elif all(["Enemy" == spell.spell.targets for spell in my_spells]):
                ally_unit_positions = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfAlly(unit)]
                ValidAttacks = [pos for pos in ValidAttacks if pos not in ally_unit_positions]

        if cf.CONSTANTS['spell_line_of_sight'] and potentialRange:
            ValidAttacks = Utility.line_of_sight(ValidMoves, ValidAttacks, max(potentialRange), gameStateObj)

        return ValidAttacks

    def displayExcessSpellAttacks(self, gameStateObj, ValidMoves, light=False):
        ValidAttacks = self.getExcessSpellAttacks(gameStateObj, ValidMoves)

        kind = 'spell_splash' if light else 'spell'
        for validattack in ValidAttacks:
            gameStateObj.highlight_manager.add_highlight(validattack, kind)

    # Given an item, returns a list of valid positions to target.
    # Used in AI
    def getTargets(self, gameStateObj, item, valid_moves=None, team_ignore=[], name_ignore=[]):
        targets = set()
        if not valid_moves:
            valid_moves = {self.position}

        if item.weapon:
            enemy_units = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfEnemy(unit) and
                           unit.team not in team_ignore and unit.name not in name_ignore]
            # Don't want this line, since AI does not consider tiles in the Primary AI
            # enemy_units += [pos for pos, tile in gameStateObj.map.tiles.items() if tile.stats['HP']]
            while enemy_units:
                current_pos = enemy_units.pop()
                for valid_move in valid_moves:
                    if Utility.calculate_distance(valid_move, current_pos) in item.get_range(self):
                        targets.add(current_pos)
                        break
        elif item.spell:
            if item.spell.targets == 'Tile':
                targets = Utility.get_shell(valid_moves, item.get_range(self), gameStateObj.map)
            elif item.spell.targets == 'TileNoUnit':
                targets = set(Utility.get_shell(valid_moves, item.get_range(self), gameStateObj.map))
                unit_positions = {unit.position for unit in gameStateObj.allunits if unit.position}
                targets -= unit_positions
            elif item.spell.targets == 'Ally':
                ally_units = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfAlly(unit) and
                              unit.team not in team_ignore and unit.name not in name_ignore]
                while ally_units:
                    current_pos = ally_units.pop()
                    for valid_move in valid_moves:
                        if Utility.calculate_distance(valid_move, current_pos) in item.get_range(self):
                            targets.add(current_pos)
                            break
            elif item.spell.targets == 'Enemy':
                enemy_units = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfEnemy(unit) and
                               unit.team not in team_ignore and unit.name not in name_ignore]
                # Don't want this line, since AI does not consider tiles in the Primary AI
                # enemy_units += [pos for pos, tile in gameStateObj.map.tiles.items() if tile.stats['HP']]
                while enemy_units:
                    current_pos = enemy_units.pop()
                    for valid_move in valid_moves:
                        if Utility.calculate_distance(valid_move, current_pos) in item.get_range(self):
                            targets.add(current_pos)
                            break
            else:
                units = [unit.position for unit in gameStateObj.allunits if unit.position and
                         unit.team not in team_ignore and unit.name not in name_ignore]
                # Don't want this line, since AI does not consider tiles in the Primary AI
                # enemy_units += [pos for pos, tile in gameStateObj.map.tiles.items() if tile.stats['HP']]
                while units:
                    current_pos = units.pop()
                    for valid_move in valid_moves:
                        if Utility.calculate_distance(valid_move, current_pos) in item.get_range(self):
                            targets.add(current_pos)
                            break

        # Handle line of sight if necessary
        targets = list(targets)
        if ((item.weapon and cf.CONSTANTS['line_of_sight']) or (item.spell and cf.CONSTANTS['spell_line_of_sight'])):
            targets = Utility.line_of_sight(valid_moves, targets, max(item.get_range(self)), gameStateObj)
        return targets

    def getStealTargets(self, gameStateObj, position=None):
        # Set-up
        if position is None:
            position = self.position
        return [unit for unit in gameStateObj.allunits if unit.position and self.checkIfEnemy(unit) and 
                Utility.calculate_distance(unit.position, position) == 1 and unit.getStealables() and
                GC.EQUATIONS.get_steal_atk(self) > GC.EQUATIONS.get_steal_def(unit)]

    # Given an item and a position, returns a list of valid tiles to attack
    def getWalls(self, gameStateObj, item, position=None):
        # Set-up
        if position is None:
            position = self.position
        targets = []
        for tile_position, tile in gameStateObj.map.tiles.items():
            if 'HP' in gameStateObj.map.tile_info_dict[tile_position] and Utility.calculate_distance(tile_position, position) in item.get_range(self):
                targets.append(tile)
        return targets
        
    # gets all possible positions the unit could attack, given one main weapon or an optionally given main weapon
    # should be called after unit has moved. Does not attempt to determine if an enemy is actually in that specific place
    def getAttacks(self, gameStateObj, weapon=None):
        # Set-up
        if self.isDone() or self.hasAttacked:
            return [], [] # No valid Attacks once you have attacked
        if weapon:
            my_weapon = weapon
        else:
            my_weapon = self.getMainWeapon()
        if not my_weapon:
            return [], [] # no valid weapon

        # calculate legal targets for cursor
        attacks = Utility.find_manhattan_spheres(my_weapon.get_range(self), self.position)
        attacks = [pos for pos in attacks if gameStateObj.map.check_bounds(pos)]
        attacks = [pos for pos in attacks if not gameStateObj.compare_teams(self.team, gameStateObj.grid_manager.get_team_node(pos))]
        if cf.CONSTANTS['line_of_sight']:
            attacks = Utility.line_of_sight([self.position], attacks, max(my_weapon.get_range(self)), gameStateObj)

        # Now actually find true and splash attack positions
        true_attacks = []
        splash_attacks = []
        for position in attacks:
            attack, splash_pos = my_weapon.aoe.get_positions(self.position, position, gameStateObj, my_weapon)
            if attack:
                true_attacks.append(attack)
            splash_attacks += splash_pos
        true_attacks = list(set(true_attacks))
        splash_attacks = list(set(splash_attacks))
        splash_attacks = [splash for splash in splash_attacks if splash not in true_attacks]

        return true_attacks, splash_attacks

    def displayAttacks(self, gameStateObj, weapon=None):
        true_attacks, splash_attacks = self.getAttacks(gameStateObj, weapon)
        # For Graphics
        for attack in true_attacks:
            gameStateObj.highlight_manager.add_highlight(attack, 'attack')
        for attack in splash_attacks:
            gameStateObj.highlight_manager.add_highlight(attack, 'splash')

    # gets all possible positions the unit could use its spell on, given its main weapon or an optionally given main weapon
    # should be called after unit has moved. !!! Does not attempt to determine if an enemy is actually in that specific place. !!!
    def getSpellAttacks(self, gameStateObj, spell=None):
        # Set-up
        if self.isDone() or self.hasAttacked:
            return [] # No valid Attacks once you have attacked
        if spell:
            my_spell = spell
        else:
            my_spell = self.getMainSpell()
        if not my_spell:
            return [] # no valid weapon

        # calculate
        ValidAttacks = Utility.find_manhattan_spheres(my_spell.get_range(self), self.position)
        ValidAttacks = [pos for pos in ValidAttacks if gameStateObj.map.check_bounds(pos)]

        # Now filter based on target
        if my_spell.spell.targets == 'Ally':
            enemy_unit_positions = {unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfEnemy(unit)}
            ValidAttacks = [pos for pos in ValidAttacks if pos not in enemy_unit_positions]
        elif my_spell.spell.targets == "Enemy":
            ally_unit_positions = {unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfAlly(unit)}
            ValidAttacks = [pos for pos in ValidAttacks if pos not in ally_unit_positions]

        if cf.CONSTANTS['spell_line_of_sight']:
            ValidAttacks = Utility.line_of_sight([self.position], ValidAttacks, max(my_spell.get_range(self)), gameStateObj)
        return ValidAttacks

    def displaySpellAttacks(self, gameStateObj, spell=None):
        spellattacks = self.getSpellAttacks(gameStateObj, spell)
        # For graphics
        for attack in spellattacks:
            gameStateObj.highlight_manager.add_highlight(attack, 'spell')

    # FINDS POSITIONS OF VALID TARGETS TO POINT WEAPON AT
    # Finds the positions of all valid targets given the main weapon you are using
    # Only gives positions that enemy units occupy
    def getValidTargetPositions(self, gameStateObj, weapon=None, force_range=None):
        if weapon is None:
            my_weapon = self.getMainWeapon()
        else:
            my_weapon = weapon
        if my_weapon is None:
            return []

        if force_range is not None:
            weapon_range = force_range
        else:
            weapon_range = my_weapon.get_range(self)

        enemy_positions = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfEnemy(unit)] + \
                          [position for position, tile in gameStateObj.map.tiles.items() if 'HP' in gameStateObj.map.tile_info_dict[position]]
        valid_targets = [pos for pos in enemy_positions if Utility.calculate_distance(pos, self.position) in weapon_range]
        if cf.CONSTANTS['line_of_sight']:
            valid_targets = Utility.line_of_sight([self.position], valid_targets, max(weapon_range), gameStateObj)
        return valid_targets

    # Finds all valid target positions given the main spell you are using
    # Gets all valid target positions given 1 main spell
    def getValidSpellTargetPositions(self, gameStateObj, spell=None, targets=None, rng=None):
        from . import Interaction
        # Assumes targetable
        if spell is None:
            my_spell = self.getMainSpell()
        else:
            my_spell = spell
        if my_spell is None:
            return []
        if my_spell.spell.targets == 'Ally':
            if my_spell.heal:
                # This is done more robustly to account for the interaction between healing effects and AOE
                places_i_can_target = Utility.find_manhattan_spheres(my_spell.get_range(self), self.position)
                valid_pos = [unit.position for unit in gameStateObj.allunits if unit.position and 
                             unit.position in places_i_can_target and self.checkIfAlly(unit)]
                targetable_position = []
                for pos in valid_pos:
                    defender, splash = Interaction.convert_positions(gameStateObj, self, self.position, pos, my_spell)
                    if (defender and defender.currenthp < defender.stats['HP']) or any(self.checkIfAlly(s) and s.currenthp < s.stats['HP'] for s in splash):
                        targetable_position.append(pos)

                # targetable_position = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfAlly(unit) and 
                #                        unit.currenthp < unit.stats['HP'] and Utility.calculate_distance(unit.position, self.position) in my_spell.get_range(self)]
            elif my_spell.target_restrict:
                targetable_position = [target.position for target in gameStateObj.allunits if target.position and
                                       self.checkIfAlly(target) and Utility.calculate_distance(target.position, self.position) in my_spell.get_range(self) and 
                                       eval(my_spell.target_restrict)]
            else:
                targetable_position = [unit.position for unit in gameStateObj.allunits if unit.position and self.checkIfAlly(unit) and
                                       Utility.calculate_distance(unit.position, self.position) in my_spell.get_range(self)]
        elif my_spell.spell.targets == 'Enemy':
            targetable_position = [target.position for target in gameStateObj.allunits if target.position and self.checkIfEnemy(target) and
                                   Utility.calculate_distance(target.position, self.position) in my_spell.get_range(self) and
                                   (not my_spell.target_restrict or eval(my_spell.target_restrict))]
        elif my_spell.spell.targets == 'Unit':
            targetable_position = [unit.position for unit in gameStateObj.allunits if unit.position and
                                   Utility.calculate_distance(unit.position, self.position) in my_spell.get_range(self)]
        elif my_spell.spell.targets.startswith('Tile'):
            targetable_position = Utility.find_manhattan_spheres(my_spell.get_range(self), self.position)
            targetable_position = [pos for pos in targetable_position if gameStateObj.map.check_bounds(pos)]
            if my_spell.spell.targets == 'TileNoUnit':
                targetable_position = [pos for pos in targetable_position if not gameStateObj.grid_manager.get_unit_node(pos)]
            if my_spell.unlock:
                targetable_position = [position for position in targetable_position if 'Locked' in gameStateObj.map.tile_info_dict[position]]
            # This might take a while
            elif my_spell.aoe.mode in ('Blast', 'EnemyBlast') and len(my_spell.get_range(self)) < 7:
                valid_positions = []
                for pos in targetable_position:
                    team = gameStateObj.grid_manager.get_team_node(pos)
                    if team and not gameStateObj.compare_teams(self.team, team):
                        valid_positions.append(pos)
                    else:
                        for x_pos in Utility.find_manhattan_spheres(range(1, my_spell.aoe.get_number(my_spell, gameStateObj) + 1), pos):
                            if gameStateObj.map.check_bounds(x_pos):
                                team = gameStateObj.grid_manager.get_team_node(x_pos)
                                if team and not gameStateObj.compare_teams(self.team, team):
                                    valid_positions.append(pos)
                                    break
                targetable_position = valid_positions

        if cf.CONSTANTS['spell_line_of_sight']:
            validSpellTargets = Utility.line_of_sight([self.position], targetable_position, max(my_spell.get_range(self)), gameStateObj)
        else:
            validSpellTargets = targetable_position
        return validSpellTargets

    # Finds all valid target positions given all weapons the unit has access to, as opposed to the just
    # one weapon favored by getValidTargetPosition. Is a wrapper around getValidTargetPosition
    def getAllTargetPositions(self, gameStateObj):
        allWeapons = [item for item in self.items if item.weapon and self.canWield(item) and self.canUse(item)]
        if not allWeapons:
            return []

        allTargets = []
        for weapon in allWeapons:
            validTargets = self.getValidTargetPositions(gameStateObj, weapon=weapon)
            allTargets += validTargets

        return list(set(allTargets))

    # Finds all valid targets given all staves the unit has access to
    # Uses EVERY spell the unit has access to 
    def getAllSpellTargetPositions(self, gameStateObj):
        allSpells = [item for item in self.items if item.spell and self.canWield(item) and self.canUse(item)]
        if not allSpells:
            return []

        allTargets = []
        for spell in allSpells:
            validTargets = self.getValidSpellTargetPositions(gameStateObj, spell=spell)
            allTargets += validTargets

        return list(set(allTargets))

    # Displays range of a single item used on a single position
    def displaySingleAttack(self, gameStateObj, position, item=None):
        if not item:
            item = self.getMainWeapon()
        true_position, splash_positions = item.aoe.get_positions(self.position, position, gameStateObj, item)
        if item.beneficial:
            if true_position:
                gameStateObj.highlight_manager.add_highlight(true_position, 'spell2', allow_overlap=True)
            for position in splash_positions:
                gameStateObj.highlight_manager.add_highlight(position, 'spell2', allow_overlap=True)
        else:
            # For Graphics
            if true_position:
                gameStateObj.highlight_manager.add_highlight(true_position, 'attack', allow_overlap=True)
            for position in splash_positions:
                gameStateObj.highlight_manager.add_highlight(position, 'splash', allow_overlap=True)

    # Finds all adjacent units
    def getAdjacentUnits(self, gameStateObj, rng=1):
        adjpositions = Utility.get_adjacent_positions(self.position, rng)
        return [unit for unit in gameStateObj.allunits if unit.position in adjpositions]

    # Finds all adjacent allied units
    def getValidPartners(self, gameStateObj, rng=1):
        return [unit for unit in self.getAdjacentUnits(gameStateObj, rng) if self.checkIfAlly(unit)]

    # Finds all adjacent units on the exact same team
    def getTeamPartners(self, gameStateObj, rng=1):
        return [unit for unit in self.getAdjacentUnits(gameStateObj, rng) if self.team == unit.team]

    # Finds all adjacent units who have things that can be stolen
    def getStealPartners(self, gameStateObj, rng=1):
        return [unit for unit in self.getAdjacentUnits(gameStateObj, rng) if self.checkIfEnemy(unit) and
                GC.EQUATIONS.get_steal_atk(self) > GC.EQUATIONS.get_steal_def(unit) and unit.getStealables()]

    def getStealables(self):
        if cf.CONSTANTS['steal'] == 0:
            return [item for item in self.items if not item.weapon and not item.spell]
        else:
            return [item for item in self.items if item is not self.getMainWeapon()]

    def getRepairables(self):
        return [item for item in self.items if 
                (item.uses and item.uses.can_repair() and not item.unrepairable) or 
                (item.c_uses and item.c_uses.can_repair() and not item.unrepairable)]

    # locates the closest ally
    def closest_ally(self, gameStateObj):
        ally_list = []
        for unit in gameStateObj.allunits:
            if unit.position and self.checkIfAlly(unit) and unit != self:
                # Taxi Cab distance
                ally_list.append([Utility.calculate_distance(unit.position, self.position), unit])
        if ally_list:
            return min(ally_list)[1]
        else:
            return None

    # Finds distance to closest enemy
    def distance_to_closest_enemy(self, gameStateObj, move=None):
        if move is None:
            move = self.position
        enemy_list = [unit for unit in gameStateObj.allunits if unit.position and unit is not self and self.checkIfEnemy(unit)]
        if not enemy_list:
            return 100 # No enemies?
        dist_list = [Utility.calculate_distance(enemy.position, move) for enemy in enemy_list]
        return min(dist_list)

    def getAdjacentTiles(self, gameStateObj):
        positions = Utility.get_adjacent_positions(self.position)
        adjacentTiles = []
        for position in positions:
            if gameStateObj.map.check_bounds(position):
                adjacentTiles.append(gameStateObj.map.tiles[position])
        return adjacentTiles

    def getAdjacentPositions(self, gameStateObj):
        positions = Utility.get_adjacent_positions(self.position)
        # Positions must be on map
        positions = [position for position in positions if gameStateObj.map.check_bounds(position)]
        return positions

    def checkIfAlly(self, unit): 
        if 'ignore_alliances' in self.status_bundle:
            return True
        if hasattr(unit, 'team'): # check if not a tile
            if self.team == 'player':
                return True if (unit.team == 'player' or unit.team == 'other') else False
            elif self.team == 'other':
                return True if (unit.team == 'player' or unit.team == 'other') else False
            elif self.team == 'enemy':
                return True if (unit.team == 'enemy') else False
            elif self.team == 'enemy2':
                return True if (unit.team == 'enemy2') else False
        return False

    def checkIfEnemy(self, unit):
        if 'ignore_alliances' in self.status_bundle:
            return True
        if hasattr(unit, 'team'): # check if not a tile
            if self.team == 'player':
                return True if (unit.team == 'enemy' or unit.team == 'enemy2') else False
            elif self.team == 'other':
                return True if (unit.team == 'enemy' or unit.team == 'enemy2') else False
            elif self.team == 'enemy':
                return True if (unit.team != 'enemy') else False
            elif self.team == 'enemy2':
                return True if (unit.team != 'enemy2') else False
        return True

    def handle_fight_quote(self, target_unit, gameStateObj):
        fight_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/fightScript.txt'
        if os.path.exists(fight_script_name):
            gameStateObj.message.append(Dialogue.Dialogue_Scene(fight_script_name, unit=target_unit, unit2=self))
            gameStateObj.stateMachine.changeState('dialogue')
            # And again, the other way round
            gameStateObj.message.append(Dialogue.Dialogue_Scene(fight_script_name, unit=self, unit2=target_unit))
            gameStateObj.stateMachine.changeState('dialogue')

    def handle_steal_banner(self, item, gameStateObj):
        gameStateObj.banners.append(Banner.stealBanner(self, item))
        gameStateObj.stateMachine.changeState('itemgain')

    def get_ai(self, ai_line):
        from . import AI_fsm
        self.reset_ai()
        self.ai_descriptor = ai_line
        logger.info('New AI Descriptor: %s', self.ai_descriptor)
        if '_' in ai_line:
            ai_line, self.ai_group = ai_line.split('_')
        else:
            self.ai_group = None

        if ai_line in GC.AIDATA:
            ai_stat = GC.AIDATA[ai_line]
            self.ai = AI_fsm.AI(self, ai_stat[0], ai_stat[1], ai_stat[2], ai_stat[3], ai_stat[4], ai_stat[5], self.ai_group)

        else:
            split_line = ai_line.split('.')
            ai1 = int(split_line[0])
            ai2 = split_line[1]
            try:
                ai2 = int(ai2)
            except ValueError:
                pass
            team_ignore = split_line[2].split(',') if split_line[2] and split_line[2] != '-' else []
            name_ignore = split_line[3].split(',') if split_line[3] and split_line[3] != '-' else []
            view_range = int(split_line[4])
            priority = int(split_line[5])

            self.ai = AI_fsm.AI(self, ai1, ai2, team_ignore, name_ignore, view_range, priority, self.ai_group)

    def notify_others_in_group(self, gameStateObj):
        if self.ai_group:
            for unit in gameStateObj.allunits:
                if unit.team == self.team and unit.ai_group == self.ai_group:
                    Action.do(Action.AIGroupPing(unit), gameStateObj)
                    if not unit.hasMoved and unit.hasRunAI():  # We need to tell this guy to try again
                        gameStateObj.ai_unit_list.append(unit)  # Move him up to next on the list
                        unit.reset_ai()

    def canAttack(self, gameStateObj):
        return self.getAllTargetPositions(gameStateObj) and not self.hasAttacked

    def check_challenge(self, target, gameStateObj):
        my_adj_units = self.getAdjacentUnits(gameStateObj)
        target_adj_units = target.getAdjacentUnits(gameStateObj)
        if not my_adj_units or target in my_adj_units and len(my_adj_units) == 1:
            if not target_adj_units or self in target_adj_units and len(target_adj_units) == 1:
                return True
        return False

    def check_focus(self, gameStateObj):
        if self.position:
            for unit in gameStateObj.allunits:
                if unit.position and self.checkIfAlly(unit) and unit is not self and Utility.calculate_distance(unit.position, self.position) <= 3:
                    return False
        return True

    def check_effective(self, item):
        if item.effective:
            e_against = item.effective.against
            for tag in e_against:
                if tag in self.tags:
                    for status in self.status_effects:
                        if status.uneffective == tag:
                            return False
                    return True
        return False

    def has_canto(self):
        return 'canto' in self.status_bundle or 'canto_plus' in self.status_bundle

    def has_canto_plus(self):
        return 'canto_plus' in self.status_bundle

    def isSummon(self):
        return any(component.startswith('Summon_') for component in self.tags)

# === COMBAT CALCULATIONS ====================================================
    # Gets bonuses from supports
    # Right now this is just recalled every time it is needed!!!
    # If that turns out to be SLOW, then I need to set it up like the aura system
    def get_support_bonuses(self, gameStateObj):
        # attack, defense, accuracy, avoid, crit, dodge, attackspeed
        bonuses = [0] * 7

        if gameStateObj.support and self.position and self.id in gameStateObj.support.node_dict:
            for other_unit in gameStateObj.support.get_adjacent(self.id):
                for unit in gameStateObj.allunits:
                    if unit.id == other_unit and unit.position and self.checkIfAlly(unit):
                        cur_bonus = gameStateObj.support.get_affinity_bonuses(self, unit)
                        bonuses = [a + b for a, b in zip(bonuses, cur_bonus)]
                        break

        return bonuses

    def outspeed(self, target, item, gameStateObj, mode=None):
        """
        Returns bool: whether self doubles target
        """
        if not isinstance(target, UnitObject):
            return False

        advantage = Weapons.TRIANGLE.compute_advantage(item, target.getMainWeapon())
        a, b = 0, 0
        # Weapon Advantage
        if advantage[0] > 0:
            a += advantage[0] * Weapons.ADVANTAGE.get_advantage(item, self.wexp).attackspeed
        else:
            a -= advantage[0] * Weapons.ADVANTAGE.get_disadvantage(item, self.wexp).attackspeed
        if advantage[1] > 0:
            b += advantage[1] * Weapons.ADVANTAGE.get_advantage(target.getMainWeapon(), target.wexp).attackspeed
        else:
            b -= advantage[1] * Weapons.ADVANTAGE.get_disadvantage(target.getMainWeapon(), target.wexp).attackspeed
        # Skills & Status
        for status in self.status_effects:
            if status.conditional_attackspeed and eval(status.conditional_attackspeed.conditional, globals(), locals()):
                bonus = int(eval(status.conditional_attackspeed.value, globals(), locals()))
                a += bonus
        for status in target.status_effects:
            if status.conditional_attackspeed and eval(status.conditional_attackspeed.conditional, globals(), locals()):
                bonus = int(eval(status.conditional_attackspeed.value, globals(), locals()))
                b += bonus
        return self.attackspeed(gameStateObj, item) + a >= target.attackspeed(gameStateObj) + b + cf.CONSTANTS['speed_to_double']

    # computes the damage dealt by me using this item
    def compute_damage(self, target, gameStateObj, item, mode=None, hybrid=None, crit=0):
        if not item:
            return None
        if item.spell and not item.damage:
            return 0
        if not item.weapon and not item.spell:
            return 0
        if item.no_damage:
            return 0

        dist = Utility.calculate_distance(self.position, target.position)
        damage = self.damage(gameStateObj, item, dist)

        if not isinstance(target, UnitObject):  # Therefore must be tile object
            if item.extra_tile_damage:
                damage += item.extra_tile_damage

        else:
            # Determine effective
            if target.check_effective(item):
                damage += item.effective.bonus
            # Weapon Triangle
            advantage = Weapons.TRIANGLE.compute_advantage(item, target.getMainWeapon())
            if advantage[0] > 0:
                damage += advantage[0] * Weapons.ADVANTAGE.get_advantage(item, self.wexp).damage
            else:
                damage -= advantage[0] * Weapons.ADVANTAGE.get_disadvantage(item, self.wexp).damage
            if advantage[1] > 0:
                damage -= advantage[1] * Weapons.ADVANTAGE.get_advantage(target.getMainWeapon(), target.wexp).resist
            else:
                damage += advantage[1] * Weapons.ADVANTAGE.get_disadvantage(target.getMainWeapon(), target.wexp).resist
            if item.is_magic():
                if item.magic_at_range and dist <= 1:
                    equation = 'DEFENSE'
                else:
                    equation = 'MAGIC_DEFENSE'
            elif item.alternate_defense:
                equation = item.alternate_defense
            else:
                equation = 'DEFENSE'
            if item.ignore_def:
                pass
            elif item.ignore_half_def:
                damage -= target.defense(gameStateObj, equation, item, dist)//2
            else:
                damage -= target.defense(gameStateObj, equation, item, dist)

            for status in self.status_effects:
                if status.conditional_mt and eval(status.conditional_mt.conditional, globals(), locals()):
                    new_damage = int(eval(status.conditional_mt.value, globals(), locals()))
                    damage += new_damage
            for status in target.status_effects:
                if status.conditional_resist and eval(status.conditional_resist.conditional, globals(), locals()):
                    new_damage = int(eval(status.conditional_resist.value, globals(), locals()))
                    damage -= new_damage
        
        if item.guaranteed_crit:
            crit = cf.CONSTANTS['crit'] or 1
        if crit == 1:
            damage += self.damage(gameStateObj, item, Utility.calculate_distance(self.position, target.position) <= 1)
        elif crit == 2:
            damage *= 2
        elif crit == 3:
            damage *= 3

        if isinstance(target, UnitObject):
            for status in target.status_effects:
                if status.resist_multiplier:
                    multiplier = float(eval(status.resist_multiplier))
                    damage = int(damage * multiplier)

        # Handle hybrid miss
        if hybrid:
            damage = int(damage * hybrid/100.0) 

        # Can't do negative damage
        return max(cf.CONSTANTS['minimum_damage'], damage)

    def compute_heal(self, target, gameStateObj, item, mode=None):
        if item.heal == 'All':
            return target.stats['HP'] - target.currenthp
        heal = int(eval(item.heal)) + GC.EQUATIONS.get_heal(self, item)
        if self is not target:
            heal += sum(status.caretaker for status in self.status_effects if status.caretaker)

        return heal

    # computes the likelihood of a hit
    # mode is whether self is the attacker or the defender
    def compute_hit(self, target, gameStateObj, item=None, mode=None):
        if item:
            my_item = item
        else:
            my_item = self.getMainWeapon()
        if not my_item:
            return None
        if not isinstance(target, UnitObject):
            return 100

        # Calculations
        if my_item.weapon or my_item.spell:
            # Weapon triangle
            dist = Utility.calculate_distance(self.position, target.position)
            advantage = Weapons.TRIANGLE.compute_advantage(my_item, target.getMainWeapon())
            bonus = 0
            if advantage[0] > 0:
                bonus += advantage[0] * Weapons.ADVANTAGE.get_advantage(item, self.wexp).accuracy
            else:
                bonus -= advantage[0] * Weapons.ADVANTAGE.get_disadvantage(item, self.wexp).accuracy
            if advantage[1] > 0:
                bonus -= advantage[1] * Weapons.ADVANTAGE.get_advantage(target.getMainWeapon(), target.wexp).avoid
            else:
                bonus += advantage[1] * Weapons.ADVANTAGE.get_disadvantage(target.getMainWeapon(), target.wexp).avoid

            hitrate = self.accuracy(gameStateObj, my_item, dist) + bonus - target.avoid(gameStateObj, my_item, dist)
            for status in self.status_effects:
                if status.conditional_hit and eval(status.conditional_hit.conditional, globals(), locals()):
                    new_hit = int(eval(status.conditional_hit.value, globals(), locals()))
                    hitrate += new_hit
            for status in target.status_effects:
                if status.conditional_avoid and eval(status.conditional_avoid.conditional, globals(), locals()):
                    new_avoid = int(eval(status.conditional_avoid.value, globals(), locals()))
                    hitrate -= new_avoid
            return Utility.clamp(hitrate, 0, 100)
        else:
            return 100

    def compute_crit(self, target, gameStateObj, item=None, mode=None):
        if item:
            my_item = item
        else:
            my_item = self.getMainWeapon()
        if not my_item:
            return None
        if not isinstance(target, UnitObject):
            return 0
        if my_item.crit is None:
            return 0
        if 'cannot_be_crit' in target.status_bundle:
            return 0

        # Calculations
        if my_item.weapon or my_item.spell:
            dist = Utility.calculate_distance(self.position, target.position)
            advantage = Weapons.TRIANGLE.compute_advantage(my_item, target.getMainWeapon())
            bonus = 0
            if advantage[0] > 0:
                bonus += advantage[0] * Weapons.ADVANTAGE.get_advantage(item, self.wexp).crit
            else:
                bonus -= advantage[0] * Weapons.ADVANTAGE.get_disadvantage(item, self.wexp).crit
            if advantage[1] > 0:
                bonus -= advantage[1] * Weapons.ADVANTAGE.get_advantage(target.getMainWeapon(), target.wexp).dodge
            else:
                bonus += advantage[1] * Weapons.ADVANTAGE.get_disadvantage(target.getMainWeapon(), target.wexp).dodge
            critrate = self.crit_accuracy(gameStateObj, my_item, dist) + bonus - target.crit_avoid(gameStateObj, my_item, dist)
            for status in self.status_effects:
                if status.conditional_crit_hit and eval(status.conditional_crit_hit.conditional, globals(), locals()):
                    new_hit = int(eval(status.conditional_crit_hit.value, globals(), locals()))
                    critrate += new_hit
            for status in target.status_effects:
                if status.conditional_crit_avoid and eval(status.conditional_crit_avoid.conditional, globals(), locals()):
                    new_avoid = int(eval(status.conditional_crit_avoid.value, globals(), locals()))
                    critrate -= new_avoid
            return Utility.clamp(critrate, 0, 100)
        else:
            return 0

    def attackspeed(self, gameStateObj, item=None):
        if not item:
            item = self.getMainWeapon()
        attackspeed = GC.EQUATIONS.get_attackspeed(self, item)
        for status in self.status_effects:
            if status.attackspeed:
                attackspeed += int(eval(status.attackspeed, globals(), locals()))
        return attackspeed

    def accuracy(self, gameStateObj, item=None, dist=0):
        accuracy = self.get_support_bonuses(gameStateObj)[2]
        # Cannot convert the following into a list comprehension, since the scoping ruins globals and locals
        for status in self.status_effects:
            if status.hit:
                accuracy += int(eval(status.hit, globals(), locals()))
        if not item:
            if self.getMainWeapon():
                item = self.getMainWeapon()
            elif self.getMainSpell():
                item = self.getMainSpell()
            else:
                return None
        if item.weapon:
            if item.alternate_hit:
                accuracy += item.weapon.HIT + GC.EQUATIONS.get_equation(item.alternate_hit, self, item, dist)
            else:
                accuracy += item.weapon.HIT + GC.EQUATIONS.get_hit(self, item, dist)
        elif item.spell and item.hit:
            if item.alternate_hit:
                accuracy += item.hit + GC.EQUATIONS.get_equation(item.alternate_hit, self, item, dist)
            else:
                accuracy += item.hit + GC.EQUATIONS.get_hit(self, item, dist)
        else:
            accuracy = 10000
        # Generic rank bonuses
        if (item.weapon or item.spell) and item.TYPE:
            idx = Weapons.TRIANGLE.name_to_index[item.TYPE]
            accuracy += Weapons.EXP.get_rank_bonus(self.wexp[idx])[0]
        return accuracy

    def avoid(self, gameStateObj, item_to_avoid=None, dist=0):
        if item_to_avoid and item_to_avoid.alternate_avoid:
            base = GC.EQUATIONS.get_equation(item_to_avoid.alternate_avoid, self, self.getMainWeapon(), dist)
        else:
            base = GC.EQUATIONS.get_avoid(self, self.getMainWeapon(), dist)
        
        base += self.get_support_bonuses(gameStateObj)[3]
        for status in self.status_effects:
            if status.avoid:
                base += int(eval(status.avoid, globals(), locals()))
        if self.position:
            base += (0 if 'flying' in self.status_bundle else gameStateObj.map.tiles[self.position].AVO)
        return base
                
    def damage(self, gameStateObj, item=None, dist=0):
        if not item:
            item = self.getMainWeapon()
        if not item:
            return 0
        if item.no_damage:
            return 0

        damage = self.get_support_bonuses(gameStateObj)[0]
        for status in self.status_effects:
            if status.mt:
                damage += int(eval(status.mt, globals(), locals()))
        if item.weapon:
            damage += item.weapon.MT
        elif item.spell and item.damage:
            damage += item.damage

        if item.weapon or (item.spell and item.damage):
            if item.alternate_damage:
                damage += GC.EQUATIONS.get_equation(item.alternate_damage, self, item, dist)
            elif item.is_magic():
                if item.magic_at_range and dist <= 1:
                    damage += GC.EQUATIONS.get_damage(self, item, dist)
                else:  # Normal
                    damage += GC.EQUATIONS.get_magic_damage(self, item, dist)
            else:
                damage += GC.EQUATIONS.get_damage(self, item, dist)
            # Generic rank bonuses
            if item.TYPE:
                idx = Weapons.TRIANGLE.name_to_index[item.TYPE]
                damage += Weapons.EXP.get_rank_bonus(self.wexp[idx])[1]
        else:
            return 0

        return damage

    def crit_accuracy(self, gameStateObj, item=None, dist=0):
        if not item:
            if self.getMainWeapon():
                item = self.getMainWeapon()
            elif self.getMainSpell():
                item = self.getMainSpell()
            else:
                return None
        if item.crit is not None and (item.weapon or item.spell):
            if item.alternate_crit:
                accuracy = item.crit + GC.EQUATIONS.get_equation(item.alternate_crit, self, item, dist)
            else:
                accuracy = item.crit + GC.EQUATIONS.get_crit(self, item, dist)
            for status in self.status_effects:
                if status.crit_hit:
                    accuracy += int(eval(status.crit_hit, globals(), locals()))
            accuracy += self.get_support_bonuses(gameStateObj)[4]
            # Generic rank bonuses
            if item.TYPE:
                idx = Weapons.TRIANGLE.name_to_index[item.TYPE]
                accuracy += Weapons.EXP.get_rank_bonus(self.wexp[idx])[2]
            return accuracy
        else:
            return 0

    def crit_avoid(self, gameStateObj, item_to_avoid=None, dist=0):
        if item_to_avoid.alternate_crit_avoid:
            base = GC.EQUATIONS.get_equation(item_to_avoid.alternate_crit_avoid, self, self.getMainWeapon(), dist)
        else:
            base = GC.EQUATIONS.get_crit_avoid(self, self.getMainWeapon(), dist)
        for status in self.status_effects:
            if status.crit_avoid:
                base += int(eval(status.crit_avoid, globals(), locals()))
        base += self.get_support_bonuses(gameStateObj)[5]
        return base

    def defense(self, gameStateObj, equation='DEFENSE', item_to_avoid=None, dist=0):
        defense = GC.EQUATIONS.get_equation(equation, self, self.getMainWeapon(), dist)
        if 'flying' not in self.status_bundle:
            defense += gameStateObj.map.tiles[self.position].stats['DEF']
        defense += self.get_support_bonuses(gameStateObj)[1]
        for status in self.status_effects:
            if status.resist:
                defense += int(eval(status.resist, globals(), locals()))
        return max(0, defense)

    def get_rating(self):
        return GC.EQUATIONS.get_rating(self)
                                                                                     
# === ACTIONS =========================================================        
    def wait(self, gameStateObj, script=True):
        logger.debug('%s %s waits', self.name, self)

        self.sprite.change_state('normal')

        # changing state
        Action.do(Action.Wait(self), gameStateObj)

        # Called whenever a unit waits
        wait_script_name = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/waitScript.txt'
        if script and os.path.exists(wait_script_name):
            wait_script = Dialogue.Dialogue_Scene(wait_script_name, unit=self)
            gameStateObj.message.append(wait_script)
            gameStateObj.stateMachine.changeState('dialogue')

    def isDone(self):
        return self.finished

    def reset_ai(self):
        self.hasRunMoveAI = False
        self.hasRunAttackAI = False
        self.hasRunGeneralAI = False
        
    def reset(self):
        self.hasMoved = False # Controls whether unit has moved already. Unit can still move back.
        self.hasTraded = False # Controls whether unit has done an action which disallows moving back.
        self.hasAttacked = False # Controls whether unit has done an action which disallows attacking, an action which ends turn
        self.finished = False # Controls whether unit has completed their turn.
        self.reset_ai()
        self.isDying = False # Unit is dying
        self.path = []
        self.movement_left = self.stats['MOV']
        self.current_move_action = None
        self.current_arrive_action = None

    # This is required to reset certain time dependant counters, because pygame counts from the beginning of each session
    # So if you spent 700 seconds in one session, the self.lastUpdate might be 700,000
    # But then when you reload that session, self.lastUpdate is still 700,000; however, currentTime is 0, so bad shit happens
    # Resetting these makes it so that the user does not have to wait 700,000 milliseconds for the game to realize its finally time to update.
    def resetUpdates(self):
        currentTime = Engine.get_time()
        self.lastArrowUpdate = currentTime
        self.lastx2UpdateTime = currentTime
        self.lastMoveTime = currentTime
        self.lastAttackTime = currentTime
        self.sprite.lastUpdate = currentTime

    def sweep(self):
        # Removes sprites
        self.removeSprites()
        # Cleans up other places unit objects could be hiding
        if self.ai:
            self.ai.clean_up()
        self.validPartners = []

    def clean_up(self, gameStateObj, event=False):
        logger.debug("Cleaning up unit %s", self.id)
        # Place any rescued units back in the gameStateObj.allunits list
        if self.TRV and not event:
            self.unrescue(gameStateObj)
        # Units should have full health
        self.set_hp(self.stats['HP'])
        # Units should have their temporary statuses removed
        # Create copy so we can iterate it over without messing around with stuff...
        for status in self.status_effects[:]:
            if (status.time or status.remove_range or 
                    status.lost_on_interact or status.lost_on_endstep or 
                    status.lost_on_attack or status.lost_on_endchapter):
                # Without clean_up parameter, certain statuses can give out other status on removal, statuses we don't want
                # Like if you remove flying, you can get tile statuses, which you obviously don't want at this point
                Action.RemoveStatus(self, status, clean_up=True).do(gameStateObj)
        # Units with status_counts should have theirs reset
        for status in self.status_effects:
            if status.count:
                status.count.count = status.count.orig_count
            if status.combat_art:
                status.combat_art.reset_charge()
            if status.activated_item:
                status.activated_item.reset_charge()
            if status.tether:
                Action.UnTetherStatus(status, self.id).do(gameStateObj)
        # Items with chapter counts should be reset
        for item in self.items:
            if item.c_uses:
                item.c_uses.uses = item.c_uses.total_uses
            elif item.cooldown:
                if not item.cooldown.persist:
                    item.cooldown.reset()
        # Units should have their positions NULLED
        self.position = None
        # Unit sprite should be reset
        self.sprite.change_state('normal', gameStateObj)
        # Units should be reset
        # Units should be reset
        self.reset()

    def default_records(self):
        return {'kills': 0, 'damage': 0, 'healing': 0}

    def serialize(self, gameStateObj):
        """Thoughts on serialization
         # Times when this can be saved. 
         1 - Free State during players turn. 
         2 - Prep Main State
         3 - Base Main State
         4 - Possibly any time?
         # What do we need to know about this unit that we cannot get elsewhere?
        """
        serial_dict = {'u_id': self.id,
                       'event_id': self.event_id,
                       'position': self.position,
                       'name': self.name,
                       'party': self.party,
                       'team': self.team,
                       'faction_icon': self.faction_icon,
                       'klass': self.klass,
                       'gender': self.gender,
                       'level': self.level,
                       'exp': self.exp,
                       'tags': self._tags,
                       'status_effects': [status.uid for status in self.status_effects],
                       'desc': self.desc,
                       'growths': self.growths,
                       'growth_points': self.growth_points,
                       'currenthp': self.currenthp,
                       'wexp': self.wexp,
                       'items': [item.uid for item in self.items],
                       'ai': self.ai_descriptor,
                       'records': self.records,
                       'portrait_id': self.portrait_id,
                       'dead': self.dead,
                       'finished': self.finished,
                       'TRV': self.TRV,
                       'stats': [stat.serialize() for name, stat in self.stats.items()],
                       'movement_group': self.movement_group,
                       'fatigue': self.fatigue}
        return serial_dict

    def acquire_tile_status(self, gameStateObj, force=False):
        if self.position and (force or 'flying' not in self.status_bundle):
            for status_obj in gameStateObj.map.tile_info_dict[self.position].get('Status', []):
                if status_obj not in self.status_effects:
                    Action.do(Action.AddStatus(self, status_obj), gameStateObj)

    def remove_tile_status(self, gameStateObj, force=False):
        if self.position and (force or 'flying' not in self.status_bundle):
            for status_obj in gameStateObj.map.tile_info_dict[self.position].get('Status', []):
                Action.do(Action.RemoveStatus(self, status_obj.id), gameStateObj)

    def unrescue(self, gameStateObj):
        self.TRV = 0
        self.strTRV = "---"
        # Remove rescue penalty
        Action.RemoveStatus(self, "Rescue").do(gameStateObj)

    def escape(self, gameStateObj):
        # Handles any events that happen on escape
        Action.do(Action.HasAttacked(self), gameStateObj)
        if 'Escape' in gameStateObj.map.tile_info_dict[self.position]:
            escape_name = gameStateObj.map.tile_info_dict[self.position]['Escape']
        elif 'Arrive' in gameStateObj.map.tile_info_dict[self.position]:
            escape_name = gameStateObj.map.tile_info_dict[self.position]['Arrive']
        else:
            escape_name = None
        gameStateObj.stateMachine.changeState('wait')
        gameStateObj.message.append(Dialogue.Dialogue_Scene('Data/escapeScript.txt', unit=self, name=escape_name, tile_pos=self.position))
        gameStateObj.stateMachine.changeState('dialogue')

    def seize(self, gameStateObj):
        Action.do(Action.HasAttacked(self), gameStateObj)
        if 'Lord_Seize' in gameStateObj.map.tile_info_dict[self.position]:
            seize_name = gameStateObj.map.tile_info_dict[self.position]['Lord_Seize']
        elif 'Seize' in gameStateObj.map.tile_info_dict[self.position]:
            seize_name = gameStateObj.map.tile_info_dict[self.position]['Seize']
        elif 'Enemy_Seize' in gameStateObj.map.tile_info_dict[self.position]:
            seize_name = gameStateObj.map.tile_info_dict[self.position]['Enemy_Seize']
        else:
            seize_name = None
        gameStateObj.stateMachine.changeState('wait')
        gameStateObj.message.append(Dialogue.Dialogue_Scene('Data/seizeScript.txt', unit=self, name=seize_name, tile_pos=self.position))
        gameStateObj.stateMachine.changeState('dialogue')

    def unlock(self, pos, item, gameStateObj):
        # self.hasAttacked = True
        Action.do(Action.HasAttacked(self), gameStateObj)
        locked_name = gameStateObj.map.tile_info_dict[pos]['Locked']
        unlock_script = 'Data/Level' + str(gameStateObj.game_constants['level']) + '/unlockScript.txt'
        if os.path.exists(unlock_script):
            gameStateObj.message.append(Dialogue.Dialogue_Scene(unlock_script, unit=self, name=locked_name, tile_pos=pos))
            gameStateObj.stateMachine.changeState('dialogue')

        if item:
            Action.do(Action.UseItem(item), gameStateObj)
            if item.uses and item.uses.uses <= 0:
                Action.do(Action.RemoveItem(self, item), gameStateObj)
                gameStateObj.banners.append(Banner.brokenItemBanner(self, item))
                gameStateObj.stateMachine.changeState('itemgain')

    def get_unlock_key(self):
        keys = [item for item in self.items if item.key]
        item = None
        if keys and 'locktouch' not in self.status_bundle:
            item = keys[0]
        return item

    def can_unlock(self):
        return 'locktouch' in self.status_bundle or any(item.unlock for item in self.items) 

    # Wrapper around way of inserting item
    def equip(self, item, gameStateObj):
        # Moves the item to the top and makes it mainweapon
        if item in self.items and self.items.index(item) == 0:
            return  # Don't need to do anything
        self.insert_item(0, item, gameStateObj)

    # Wrappers around way of inserting item
    def add_item(self, item, gameStateObj):
        index = len(self.items)
        self.insert_item(index, item, gameStateObj)

    def unequip_item(self, item, gameStateObj):
        for status_on_equip in item.status_on_equip:
            Action.do(Action.RemoveStatus(self, status_on_equip), gameStateObj)

    def equip_item(self, item, gameStateObj):
        for status_on_equip in item.status_on_equip:
            new_status = StatusCatalog.statusparser(status_on_equip, gameStateObj)
            Action.do(Action.AddStatus(self, new_status), gameStateObj)

    # This does the adding and subtracting of statuses
    def remove_item(self, item, gameStateObj):
        logger.debug("Removing %s from %s items.", item, self.name)
        next_weapon = next((item for item in self.items if item.weapon and self.canWield(item)), None)
        was_mainweapon = next_weapon == item
        self.items.remove(item)
        item.item_owner = 0
        if was_mainweapon:
            self.unequip_item(item, gameStateObj)
        for status_on_hold in item.status_on_hold:
            Action.do(Action.RemoveStatus(self, status_on_hold), gameStateObj)
        # remove item mods skills
        for status in self.status_effects:
            if status.item_mod:
                status.item_mod.reverse_mod(item, gameStateObj)
        # There may be a new item equipped
        if was_mainweapon and self.getMainWeapon():
            self.equip_item(self.getMainWeapon(), gameStateObj)
        # Handle boundary nonsense -- Using a new weapon can make your min or max range change
        if gameStateObj.boundary_manager:
            gameStateObj.boundary_manager.recalculate_unit(self, gameStateObj)

    # This does the adding and subtracting of statuses
    def insert_item(self, index, item, gameStateObj):
        logger.debug("Inserting %s to %s items at index %s.", item, self.name, index)
        # Are we just reordering our items?
        if item in self.items:
            self.items.remove(item)
            self.items.insert(index, item)
            if self.getMainWeapon() == item: # If new mainweapon...
                # You unequipped a different item, so remove its status.
                prev_main_weapon = next((i for i in self.items if i.weapon and self.canWield(i) and i is not item), None)
                if prev_main_weapon:
                    self.unequip_item(prev_main_weapon, gameStateObj)
                # Now add yours
                if self.canWield(item) and self.canUse(item):
                    self.equip_item(item, gameStateObj)
        else:
            self.items.insert(index, item)
            item.item_owner = self.id
            if item is not "EmptySlot":
                # apply item mod skills
                for status in self.status_effects:
                    if status.item_mod:
                        status.item_mod.apply_mod(item, gameStateObj)
                # Item statuses      
                for status_on_hold in item.status_on_hold:
                    new_status = StatusCatalog.statusparser(status_on_hold, gameStateObj)
                    Action.do(Action.AddStatus(self, new_status), gameStateObj)
                if self.getMainWeapon() == item: # If new mainweapon...
                    # You unequipped a different item, so remove its status.
                    prev_main_weapon = next((i for i in self.items if i.weapon and self.canWield(i) and i is not item), None)
                    if prev_main_weapon:
                        self.unequip_item(prev_main_weapon, gameStateObj)
                    # Now add yours
                    if self.canWield(item) and self.canUse(item):
                        self.equip_item(item, gameStateObj)
            # Handle boundary nonsense
            if gameStateObj.boundary_manager:
                gameStateObj.boundary_manager.recalculate_unit(self, gameStateObj)

    def die(self, gameStateObj, event=False):
        if event:
            Action.do(Action.LeaveMap(self), gameStateObj)
        else:
            Action.do(Action.Die(self), gameStateObj)

    def move_back(self, gameStateObj):
        if self.current_arrive_action:
            Action.reverse(self.current_arrive_action, gameStateObj)
            self.current_arrive_action = None
        if self.current_move_action:
            Action.reverse(self.current_move_action, gameStateObj)
            self.current_move_action = None

    def get_unit_speed(self):
        """
        Returns the time the unit should spend getting from one tile to the next
        """
        return cf.CONSTANTS['Unit Speed']

    def play_movement_sound(self, gameStateObj):
        self.movement_sound.play()

    def stop_movement_sound(self, gameStateObj):
        self.movement_sound.stop()

    # This obviously has some important purpose. Should write that purpose when I remember why i did this.
    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)

# === UPDATE ==================================================================       
    def update(self, gameStateObj):
        currentTime = Engine.get_time()

        # === GAMELOGIC ===
        # === MOVE ===
        if self in gameStateObj.moving_units and \
                currentTime - self.lastMoveTime > self.get_unit_speed() and \
                gameStateObj.stateMachine.getState() == 'movement':
            # logger.debug('Moving!')
            if self.path: # and self.movement_left >= gameStateObj.map.tiles[self.path[-1]].mcost: # This causes errors with max movement
                new_position = self.path.pop()
                if self.position != new_position:
                    self.movement_left -= gameStateObj.map.tiles[new_position].get_mcost(self)
                self.position = new_position
                # Camera auto-follow
                if 'dialogue' not in gameStateObj.stateMachine.getPreviousState():
                    if not gameStateObj.cursor.camera_follow:
                        gameStateObj.cursor.camera_follow = self.id
                if gameStateObj.cursor.camera_follow == self.id:
                    gameStateObj.cursor.centerPosition(self.position, gameStateObj)
            else: # Path is empty, which means we are done
                gameStateObj.moving_units.discard(self)
                # self.sprite.change_state('normal', gameStateObj)
                # Add status for new position
                self.current_arrive_action = Action.MoveArrive(self)
                Action.do(self.current_arrive_action, gameStateObj)
                self.stop_movement_sound(gameStateObj)
                if gameStateObj.stateMachine.getPreviousState() != 'dialogue':
                    self.hasMoved = True
                else:
                    self.sprite.change_state('normal', gameStateObj)
                # End Camera Auto-follow
                if gameStateObj.cursor.camera_follow == self.id:
                    gameStateObj.cursor.camera_follow = None
            self.lastMoveTime = currentTime

        if self.position:
            self.sprite.update(gameStateObj)
            self.movement_sound.update()

        # === UP and DOWN Arrow COUNTER logic - For itemAdvantageArrows
        if currentTime - self.lastArrowUpdate > 130:
            self.arrowCounter += 1
            if self.arrowCounter >= len(self.arrowAnim):
                self.arrowCounter = 0
            self.lastArrowUpdate = currentTime

        # === Timer for x2 symbol movement
        if currentTime - self.lastx2UpdateTime > 50:
            self.lastx2UpdateTime = currentTime
            self.x2_counter += 1
            if self.x2_counter >= len(self.x_positions):
                self.x2_counter = 0

        # Death + the right state for processing it
        if self.isDying and gameStateObj.stateMachine.getState() == 'dying':
            if self.deathCounter == 0: # If we just started dying
                GC.SOUNDDICT['Death'].play()
            elif self.deathCounter == 1:
                self.sprite.set_transition('fade_out')
            self.deathCounter += 1
            if self.deathCounter > 27: # DEAD
                self.isDying = False
                self.die(gameStateObj)
                self.deathCounter = 0 # Reset deathCounter. Otherwise characters never leaves death process.
# === END UNIT ================================================================
