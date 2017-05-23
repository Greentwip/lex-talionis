#! usr/bine/env python2.7
from imagesDict import getImages
from GlobalConstants import *
from configuration import *
import Image_Modification, Utility, Engine
import copy

import logging
logger = logging.getLogger(__name__)

NETPOSITION_SET = {'weapon', 'attack', 'spellweapon', 'spell', 'select', 'skillselect', 'stealselect', \
                   'tradeselect', 'takeselect', 'dropselect', 'giveselect', 'rescueselect', 'talkselect', \
                   'unlockselect', 'trade', 'steal'}

class UnitSprite(object):
    def __init__(self, unit):
        self.unit = unit
        self.state = 'passive'
        self.transition_state = 'normal' # fade_in, fade_out, warp_in, warp_out, fake_in, fake_out
        self.transition_counter = 0
        self.transition_time = 400
        self.next_position = None
        self.spriteOffset = [0, 0]
        self.old_sprite_offset = (0, 0)

        self.loadSprites()

        self.moveSpriteCounter = 0
        self.lastUpdate = 0
        self.spriteMvm = [1, 2, 3, 2, 1, 0]
        self.spriteMvmindex = 0
        self.lastSpriteUpdate = Engine.get_time()

        self.lastHPUpdate = 0
        self.current_cut_off = int((self.unit.currenthp/float(self.unit.stats['HP']))*12) + 1

    def set_transition(self, new_state):
        self.transition_counter = self.transition_time
        self.transition_state = new_state

    def set_next_position(self, new_pos):
        self.next_position = new_pos

    def draw(self, surf, gameStateObj):
        """Assumes image has already been developed."""
        image = self.create_image(self.state)
        x, y = self.unit.position
        left = x * TILEWIDTH + self.spriteOffset[0]
        top = y * TILEHEIGHT + self.spriteOffset[1]

        # Active Skill Icon
        if not self.unit.isDying and any(status.active and status.active.required_charge and status.active.current_charge >= status.active.required_charge for status in self.unit.status_effects):
            active_icon = ICONDICT["ActiveSkill"]
            active_icon = Engine.subsurface(active_icon, (PASSIVESPRITECOUNTER.count*32, 0, 32, 32))
            topleft = (left - max(0, (active_icon.get_width() - 16)/2), top - max(0, (active_icon.get_height() - 16)/2))
            surf.blit(active_icon, topleft)

        if self.transition_state in ['warp_out', 'fade_out', 'fade_move', 'warp_move']:
            if self.unit.deathCounter:
                image = Image_Modification.flickerImageTranslucentColorKey(image, self.unit.deathCounter/2)
            else:
                image = Image_Modification.flickerImageTranslucentColorKey(image, 100 - self.transition_counter/(self.transition_time/100))
                if self.transition_counter <= 0:
                    if self.transition_state == 'fade_out':
                        self.transition_state = 'normal'
                        self.unit.die(gameStateObj, event=True)
                    if self.transition_state in ['fade_move', 'warp_move']:
                        self.unit.leave(gameStateObj)
                        self.unit.position = self.next_position
                        self.unit.arrive(gameStateObj)
                        self.next_position = None
                        if self.transition_state == 'fade_move':
                            self.set_transition('fade_in')
                        elif self.transition_state == 'warp_move':
                            self.set_transition('warp_in')
        elif self.transition_state in ['warp_in', 'fade_in']:
            image = Image_Modification.flickerImageTranslucentColorKey(image, self.transition_counter/(self.transition_time/100))
            if self.transition_counter <= 0:
                self.transition_state = 'normal'
        elif self.unit.flickerWhite:
            total_time = self.unit.flickerWhite[1]
            starting_time = self.unit.flickerWhite[0]
            time_passed = Engine.get_time() - starting_time
            if time_passed >= total_time:
                self.unit.end_flicker_white()
            else:
                #whiteness = (total_time/2 - abs(time_passed - total_time/2))*255.0/(total_time/2)
                whiteness = (total_time - time_passed)*255.0/total_time
                #image = Image_Modification.flickerImageWhiteColorKey(image, whiteness)
                image = Image_Modification.flickerImageWhite(image.convert_alpha(), whiteness)
        elif any(status.unit_translucent for status in self.unit.status_effects):
            image = Image_Modification.flickerImageTranslucentColorKey(image, 50)
        elif self.unit.flickerRed and gameStateObj.boundary_manager.draw_flag:
            image = Image_Modification.flickerImageRed(image.convert_alpha(), 80)
        # What is this line even doing? - Something majorly important though
        # Each image has (self.image.get_width() - 32)/2 buffers on the left and right of it, to handle any off tile spriting
        # Without self.image.get_width() - 32)/2, we would output the left buffer along with the unit, and the unit would end up +left buffer width to the right of where he should be
        topleft = left - max(0, (image.get_width() - 16)/2), top - 24
        surf.blit(image, topleft)

        # =======
        # Status Aura Icon
        if not self.unit.isDying and any(status.aura for status in self.unit.status_effects):
            aura_icon_name = self.unit.team + 'AuraIcon'
            aura_icon = IMAGESDICT[aura_icon_name] if aura_icon_name in IMAGESDICT else IMAGESDICT['AuraIcon']
            aura_icon = Engine.subsurface(aura_icon, (0, PASSIVESPRITECOUNTER.count*10, 32, 10))
            topleft = (left - max(0, (aura_icon.get_width() - 16)/2), top - max(0, (aura_icon.get_height() - 16)/2) + 8)
            surf.blit(aura_icon, topleft)
        # Status always animationss
        for status in self.unit.status_effects:
            if status.always_animation:
                x,y = self.unit.position
                topleft = (x-1) * TILEWIDTH + self.spriteOffset[0], (y-1) * TILEHEIGHT + self.spriteOffset[1]
                surf.blit(status.always_animation.image, topleft)

        if self.transition_state.startswith('warp'):
            num_frames = 12
            fps = self.transition_time/num_frames
            #if self.transition_state == 'warp_out':
            #    frame = self.transition_counter/fps
            #elif self.transition_state == 'warp_in':
            frame = (self.transition_time - self.transition_counter)/fps
            if frame >= 0 and frame < num_frames:
                warp_anim = Engine.subsurface(IMAGESDICT['Warp'], (frame*32, 0, 32, 48))
                topleft = (left - max(0, (warp_anim.get_width() - 16)/2), top - max(0, (warp_anim.get_height() - 16)/2) - 4)
                surf.blit(warp_anim, topleft)
            elif frame >= num_frames:
                if self.transition_state == 'warp_out':
                    gameStateObj.map.initiate_warp_flowers(self.unit.position)
                    self.unit.die(gameStateObj, event=True)
                    self.transition_state = 'normal'
                elif self.transition_state == 'warp_move':
                    gameStateObj.map.initiate_warp_flowers(self.unit.position)
                    self.unit.leave(gameStateObj)
                    self.unit.position = self.next_position
                    self.unit.arrive(gameStateObj)
                    self.next_position = None
                    self.set_transition('warp_in')
                    gameStateObj.map.initiate_warp_flowers(self.unit.position)
                elif self.transition_state == 'warp_in':
                    self.transition_state = 'normal'

        if gameStateObj and gameStateObj.cursor.currentSelectedUnit and (gameStateObj.cursor.currentSelectedUnit.name, self.unit.name) in gameStateObj.talk_options:
            frame = (Engine.get_time()/100)%8
            topleft = (left + 6, top - 12)
            surf.blit(Engine.subsurface(IMAGESDICT['TalkMarker'], (frame*8, 0, 8, 16)), topleft)

    def draw_hp(self, surf, gameStateObj):
        current_time = Engine.get_time()
        if self.transition_state == 'normal':
            #print('draw_hp')
            x, y = self.unit.position
            left = x * TILEWIDTH + self.spriteOffset[0]
            top = y * TILEHEIGHT + self.spriteOffset[1]
            # Health Bar
            if not self.unit.isDying:
                if (OPTIONS['HP Map Team'] == 'All') or (OPTIONS['HP Map Team'] == 'Ally' and self.unit.team in ['player', 'other']) or (OPTIONS['HP Map Team'] == 'Enemy' and self.unit.team.startswith('enemy')):
                    if (OPTIONS['HP Map Cull'] == 'All') or (OPTIONS['HP Map Cull'] == 'Wounded' and (self.unit.currenthp < self.unit.stats['HP'] or self.current_cut_off != 13)):
                        health_outline = IMAGESDICT['Map_Health_Outline']
                        health_bar = IMAGESDICT['Map_Health_Bar']
                        if(self.unit.currenthp >= int(self.unit.stats['HP'])):
                            cut_off = 13
                        elif self.unit.currenthp <= 0:
                            cut_off = 0
                        else:
                            cut_off = int((self.unit.currenthp/float(self.unit.stats['HP']))*12) + 1
                        if gameStateObj.combatInstance and self.unit in gameStateObj.combatInstance.health_bars:
                            self.current_cut_off = int(float(gameStateObj.combatInstance.health_bars[self.unit].true_hp)/self.unit.stats['HP']*12) + 1
                        else:
                            if current_time - self.lastHPUpdate > 50:
                                self.lastHPUpdate = current_time
                                if self.current_cut_off < cut_off:
                                    self.current_cut_off += 1
                                elif self.current_cut_off > cut_off:
                                    self.current_cut_off -= 1

                        surf.blit(health_outline, (left, top+13))
                        health_bar = Engine.subsurface(health_bar, (0, 0, self.current_cut_off, 1))
                        surf.blit(health_bar, (left+1, top+14))
            # Extra Icons
            if 'Boss' in self.unit.tags and self.state in ['gray', 'passive'] and int((current_time%450)/150) in [1, 2]: # Essentially an every 132 millisecond timer
                bossIcon = ICONDICT['BossIcon']
                surf.blit(bossIcon, (left - 8, top - 8))
            if self.unit.TRV:
                # For now no rescue icon color change, because I would need to add in the gameStateObj...
                """if self.unit.TRV.team == 'player':
                    rescueIcon = ICONDICT['BlueRescueIcon']
                else: # self.TRV.team == 'other':
                    rescueIcon = ICONDICT['GreenRescueIcon']"""
                rescueIcon = ICONDICT['BlueRescueIcon']
                topleft = (left - max(0, (rescueIcon.get_width() - 16)/2), top - max(0, (rescueIcon.get_height() - 16)/2))
                surf.blit(rescueIcon, topleft)

    def get_sprites(self, team):
        unit_stand_sprites = UNITDICT[team + self.unit.klass + self.unit.gender]
        unit_move_sprites = UNITDICT[team + self.unit.klass + self.unit.gender + '_move']
        return unit_stand_sprites, unit_move_sprites

    def loadSprites(self):
        # Load sprites
        try:
            unit_stand_sprites, unit_move_sprites = self.get_sprites(self.unit.team)
        except KeyError as e:
            print('KeyError. Trying Title Case', e)
            unit_stand_sprites, unit_move_sprites = self.get_sprites(self.unit.team.title())
        self.unit_sprites = self.formatSprite(unit_stand_sprites, unit_move_sprites)

    def removeSprites(self):
        self.unit_sprites = None
        self.image = None

    def formatSprite(self, standSprites, moveSprites):
        return {'passive': Engine.subsurface(standSprites, (0, 0, standSprites.get_width(), 48)),
                'gray': Engine.subsurface(standSprites, (0, TILEHEIGHT*3, standSprites.get_width(), 48)),
                'active': Engine.subsurface(standSprites, (0, 2*TILEHEIGHT*3, standSprites.get_width(), 48)),
                'down': Engine.subsurface(moveSprites, (0, 0, moveSprites.get_width(), 40)),
                'left': Engine.subsurface(moveSprites, (0, 40, moveSprites.get_width(), 40)),
                'right': Engine.subsurface(moveSprites, (0, 80, moveSprites.get_width(), 40)),
                'up': Engine.subsurface(moveSprites, (0, 120, moveSprites.get_width(), 40))}

    def create_image(self, state):
        return self.select_frame(self.unit_sprites[state].copy(), state)

    def select_frame(self, image, state):
        if state in ['passive', 'gray']:
            return Engine.subsurface(image, (PASSIVESPRITECOUNTER.count*64, 0, 64, 48))
        elif state == 'active':
            return Engine.subsurface(image, (ACTIVESPRITECOUNTER.count*64, 0, 64, 48))
        else:
            return Engine.subsurface(image, (self.moveSpriteCounter*48, 0, 48, 40))

    def handle_net_position(self, pos):
        if abs(pos[0]) >= abs(pos[1]):
            if pos[0] > 0:
                self.state = 'right'
            elif pos[0] < 0:
                self.state = 'left'
            else:
                self.state = 'down' # default
        else:
            if pos[1] < 0:
                self.state = 'up'
            else:
                self.state = 'down'

    def update_move_sprite_counter(self, currentTime, update_speed=50):
        ### MOVE SPRITE COUNTER LOGIC
        if self.moveSpriteCounter == 0 or self.moveSpriteCounter == 2:
            update_speed *= 2
        if currentTime - self.lastUpdate > update_speed:
            self.moveSpriteCounter += 1
            if self.moveSpriteCounter >= 4:
                self.moveSpriteCounter = 0
            self.lastUpdate = currentTime

    def update(self, gameStateObj):
        currentTime = Engine.get_time()
        self.transition_counter -= (currentTime - Engine.get_last_time())
        self.transition_counter = max(0, self.transition_counter)

        ### SPRITE OFFSET FOR MOVE - Positions unit at intervening positions based on spriteOffset
        if self.transition_state == 'fake_in':
            if self.spriteOffset[0] > 0:
                self.spriteOffset[0] -= 2
            elif self.spriteOffset[0] < 0:
                self.spriteOffset[0] += 2
            if self.spriteOffset[1] > 0:
                self.spriteOffset[1] -= 2
            elif self.spriteOffset[1] < 0:
                self.spriteOffset[1] += 2

            if self.spriteOffset[0] == 0 and self.spriteOffset[1] == 0:
                self.transition_state = 'normal'
        elif self.transition_state in ['fake_out', 'rescue']:
            logger.debug('fake_removal')
            if self.spriteOffset[0] < 0:
                self.spriteOffset[0] -= 2
            elif self.spriteOffset[0] > 0:
                self.spriteOffset[0] += 2
            if self.spriteOffset[1] < 0:
                self.spriteOffset[1] -= 2
            elif self.spriteOffset[1] > 0:
                self.spriteOffset[1] += 2
            if abs(self.spriteOffset[0]) >= TILEWIDTH or abs(self.spriteOffset[1]) >= TILEHEIGHT:
                self.transition_state = 'normal'
                self.spriteOffset = [0, 0]
                if self.transition_state == 'fake_out':
                    self.unit.die(gameStateObj, event=True)
                else: # Rescue
                    self.unit.leave(gameStateObj)
                    self.unit.position = None
        elif self.unit.isMoving and gameStateObj.stateMachine.getState() == 'movement':
            if self.unit.path:
                nextPosition = self.unit.path[-1]
                netPosition = (nextPosition[0] - self.unit.position[0], nextPosition[1] - self.unit.position[1]) 
                self.spriteOffset[0] = int(TILEWIDTH * (currentTime - self.unit.lastMoveTime) / CONSTANTS['Unit Speed'] * netPosition[0])
                self.spriteOffset[1] = int(TILEHEIGHT * (currentTime - self.unit.lastMoveTime) / CONSTANTS['Unit Speed'] * netPosition[1])
            else:
                # reset spriteOffset
                if self.spriteOffset[0] != 0 or self.spriteOffset[1] != 0:
                    self.old_sprite_offset = tuple(self.spriteOffset)
                self.spriteOffset = [0, 0]
                self.transition_state = 'normal'
            
        ### UPDATE IMAGE
        if gameStateObj.stateMachine.getState() == 'combat' and gameStateObj.combatInstance and \
            (self.unit is gameStateObj.combatInstance.p1 or self.unit is gameStateObj.combatInstance.p2 or \
            (self.unit in gameStateObj.combatInstance.splash and self.unit in [result.defender for result in gameStateObj.combatInstance.results])):
            if gameStateObj.combatInstance.results:
                attacker = gameStateObj.combatInstance.results[0].attacker
                defenders = [result.defender for result in gameStateObj.combatInstance.results]
            else:
                attacker = gameStateObj.combatInstance.p1
                defenders = [gameStateObj.combatInstance.p2]
            if self.unit is attacker:
                if not defenders or attacker in defenders:
                    self.state = 'active'
                else:
                    netposition = gameStateObj.cursor.position[0] - attacker.position[0], gameStateObj.cursor.position[1] - attacker.position[1]
                    self.handle_net_position(netposition)
                    if gameStateObj.combatInstance.combat_state == 'Anim':
                        self.spriteOffset[0] = Utility.clamp(netposition[0], -1, 1) * self.spriteMvm[self.spriteMvmindex]
                        self.spriteOffset[1] = Utility.clamp(netposition[1], -1, 1) * self.spriteMvm[self.spriteMvmindex]
                        if currentTime - self.lastSpriteUpdate > 50:
                            self.spriteMvmindex += 1
                            if self.spriteMvmindex > len(self.spriteMvm) - 1:
                                self.spriteMvmindex = len(self.spriteMvm) - 1
                            self.lastSpriteUpdate = currentTime
                        self.update_move_sprite_counter(currentTime, 50)
                    else: # Reset spriteOffset
                        self.spriteMvmindex = 0
                        self.spriteOffset = [0, 0]

            elif self.unit in defenders:
                #print(attacker, defender, attacker.position, defender.position)
                netposition = attacker.position[0] - self.unit.position[0], attacker.position[1] - self.unit.position[1]
                self.handle_net_position(netposition)

        elif gameStateObj.stateMachine.getState() == 'status' and gameStateObj.status and gameStateObj.status.check_active(self.unit):
            self.state = 'active'
        elif gameStateObj.cursor.currentSelectedUnit is self.unit and gameStateObj.stateMachine.getState() == 'menu' and not self.unit.hasAttacked:
            self.handle_net_position(self.old_sprite_offset)
            self.update_move_sprite_counter(currentTime, 80)
        elif gameStateObj.cursor.currentSelectedUnit is self.unit and gameStateObj.stateMachine.getState() in NETPOSITION_SET:
            netposition = (gameStateObj.cursor.position[0] - self.unit.position[0], gameStateObj.cursor.position[1] - self.unit.position[1])
            if netposition == (0, 0):
                netposition = self.old_sprite_offset
            self.handle_net_position(netposition)
            self.update_move_sprite_counter(currentTime, 80)
        elif (self.unit.isMoving and gameStateObj.stateMachine.getState() == 'movement') or self.transition_state in ['fake_in', 'fake_out', 'rescue']:
            if self.unit.isMoving:
                # Where is my path with respect to here
                try:
                    newPosition = self.unit.path[-1]
                except IndexError:
                    return # Just use previous image? Other options include keeping in memory lastPosition. Of course this whole thing will probably haveto be changed in the future... HAHAHA... Yeah right...
            elif self.transition_state in ['fake_in', 'fake_out', 'rescue']:
                newPosition = (self.unit.position[0] + Utility.clamp(self.spriteOffset[0], -1, 1), self.unit.position[1] + Utility.clamp(self.spriteOffset[1], -1, 1))
            netposition = (newPosition[0] - self.unit.position[0], newPosition[1] - self.unit.position[1])
            if self.transition_state == 'fake_in':
                netposition = (-netposition[0], -netposition[1])
            self.handle_net_position(netposition)
            if self.unit.isMoving:
                self.update_move_sprite_counter(currentTime, 80)
        # Unit can't be done in prep, and if you are we should ignore it. Can't ignore dialogue because if I do then units start flickering as death, fight and interact dialogues take place
        elif self.unit.isDone() and not self.unit.isDying and not self.unit.isActive \
        and not gameStateObj.stateMachine.getState().startswith('prep') and \
        not gameStateObj.stateMachine.any_events():
            self.state = 'gray'
        elif gameStateObj.cursor.currentSelectedUnit == self.unit and self.unit.team == 'player' and gameStateObj.cursor.drawState:
            self.state = 'down'
            self.update_move_sprite_counter(currentTime, 80)
        elif gameStateObj.cursor.currentHoveredUnit == self.unit and self.unit.team == 'player' and gameStateObj.cursor.drawState:
            self.state = 'active'
        else:
            self.state = 'passive'

        # Update status effects
        # Status effects
        for status in self.unit.status_effects:
            if status.always_animation:
                staa = status.always_animation
                if currentTime - staa.lastUpdate > staa.animation_speed:
                    staa.frameCount += int((currentTime - staa.lastUpdate)/staa.animation_speed) # 1
                    staa.lastUpdate = currentTime
                    if staa.frameCount >= staa.num_frames:
                        staa.frameCount = 0

                indiv_width, indiv_height = staa.sprite.get_width()/staa.x, staa.sprite.get_height()/staa.y
                staa.image = Engine.subsurface(staa.sprite, (staa.frameCount%staa.x * indiv_width, staa.frameCount/staa.x * indiv_height, indiv_width, indiv_height))