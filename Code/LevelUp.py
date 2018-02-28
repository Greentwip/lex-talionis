# Display Unit Info function
import GlobalConstants as GC
import configuration as cf
import CustomObjects, Image_Modification, Engine
import StatusObject, Banner, Utility

####################################################################
# Displays the level up screen
class levelUpScreen(object):
    def __init__(self, gameStateObj, unit, exp, force_level=None, force_promotion=False, in_combat=False):
        self.unit = unit
        # if cf.OPTIONS['debug']:
        #     print('LevelUpScreen: ', exp)
            
        self.expNew = min(100, exp)
        self.expOld = self.unit.exp
        self.expSet = self.expOld

        self.force_level = force_level
        self.in_combat = in_combat
        self.new_wexp = None  # For promotion

        # spriting
        self.levelUpScreen = GC.IMAGESDICT['LevelScreen']
        if self.in_combat:
            topleft=(0, 6)
            timing = [1 for _ in xrange(19)] + [10, 1, 1, 1, 1, 1] + [2 for _ in xrange(15)] + [-1] + [1 for _ in xrange(12)] 
            self.levelUpAnimation = CustomObjects.Animation(GC.IMAGESDICT['LevelUpBattle'], topleft, (5, 11), 52, ignore_map=True, set_timing=timing)
        else:
            if unit.position:
                x, y = unit.position
                topleft = (x-gameStateObj.cameraOffset.x-2)*GC.TILEWIDTH, (y-gameStateObj.cameraOffset.y-1)*GC.TILEHEIGHT
            else:
                topleft = GC.WINWIDTH/2, GC.WINHEIGHT/2
            timing = [1 for _ in xrange(24)] + [44]
            self.levelUpAnimation = CustomObjects.Animation(GC.IMAGESDICT['LevelUpMap'], topleft, (5, 5), ignore_map=True, set_timing=timing)
        self.statupanimation = GC.IMAGESDICT['StatUpSpark']
        self.statunderline = GC.IMAGESDICT['StatUnderline']
        self.uparrow = GC.IMAGESDICT['LevelUpArrow']
        self.numbers = GC.IMAGESDICT['LevelUpNumber']

        self.exp_bar = None

        self.levelup_list = force_level
        self.sparkCounter = -1 # Where we are in the levelScreen spark display section
        self.lastSparkUpdate = Engine.get_time()
        self.first_spark_flag = False
        self.unit_scroll_offset = 80
        self.screen_scroll_offset = self.levelUpScreen.get_width() + 32
        self.underline_offset = 0
        self.state = CustomObjects.StateMachine('init')
        self.animations, self.arrow_animations, self.number_animations = [], [], []
        if force_level:
            self.unit.apply_levelup(force_level, exp == 0)
            self.state.changeState('levelScreen')
            self.state_time = Engine.get_time()
        if force_promotion:
            self.state.changeState('item_promote')
            self.state_time = Engine.get_time()

        # TIMING
        self.total_time_for_exp = self.expNew * GC.FRAMERATE # exp rate is 16
        self.level_up_sound_played = False
        self.SPARKTIME = 320
        self.LEVELUPWAIT = 1660

    def get_num_sparks(self):
        if self.levelup_list:
            return sum(min(num, 1) for num in self.levelup_list)
        return 0

    def update(self, gameStateObj, metaDataObj):
        # print(self.state.getState())
        # Don't do this if there is no exp change
        if not self.force_level and self.expNew == 0 or \
                (self.unit.level%cf.CONSTANTS['max_level'] == 0 and metaDataObj['class_dict'][self.unit.klass]['turns_into'] is None):
            return True # We're done here

        currentTime = Engine.get_time()

        # Initiating State
        if self.state.getState() == 'init':
            self.exp_bar = Exp_Bar(self.expSet, not self.in_combat) # Create exp_bar
            self.state_time = currentTime
            self.state.changeState('exp_wait')

        # Wait before starting to increment exp
        elif self.state.getState() == 'exp_wait':
            self.exp_bar.update(self.expSet)
            if currentTime - self.state_time > 400:
                self.state.changeState('exp0')
                self.state_time = currentTime
                GC.SOUNDDICT['Experience Gain'].play(-1)

        # Increment exp until done or 100 exp is reached
        elif self.state.getState() == 'exp0':
            progress = (currentTime - self.state_time)/float(self.total_time_for_exp)
            self.expSet = self.expOld + progress*self.expNew
            self.expSet = int(min(self.expNew + self.expOld, self.expSet))
            self.exp_bar.update(self.expSet)
            # transitions
            if self.expNew + self.expOld <= self.expSet:
                GC.SOUNDDICT['Experience Gain'].stop() 

            if self.expSet >= 100:
                if self.unit.level%cf.CONSTANTS['max_level'] == 0: # If I would promote because I am level 20
                    GC.SOUNDDICT['Experience Gain'].stop()
                    GC.SOUNDDICT['Level Up'].play()
                    self.state.clear()
                    self.state.changeState('prepare_promote')
                    self.state.changeState('exp_leave')
                    self.exp_bar.fade_out()
                    self.state_time = currentTime
                else:
                    self.expSet = 0
                    self.unit.level += 1
                    self.levelup_list = self.unit.level_up(gameStateObj, metaDataObj['class_dict'][self.unit.klass])
                    self.state.changeState('exp100')
                    # Do not reset state time
            # Extra time to account for end pause
            elif currentTime - self.state_time >= self.total_time_for_exp + 500:
                self.state.clear()
                self.state.changeState('exp_leave')
                self.state_time = currentTime
                self.exp_bar.fade_out()

        elif self.state.getState() == 'exp_leave':
            done = self.exp_bar.update(self.expSet)
            if done:
                self.unit.exp += self.expNew
                self.state.back()
                self.state_time = currentTime
                if len(self.state.state) <= 0:
                    return True

        # Continue incrementing past 100
        elif self.state.getState() == 'exp100':
            progress = (currentTime - self.state_time)/float(self.total_time_for_exp)
            self.expSet = self.expOld + self.expNew*progress - 100
            self.expSet = int(min(self.expNew + self.expOld - 100, self.expSet))
            self.exp_bar.update(self.expSet)
            if self.expNew + self.expOld - 100 <= self.expSet:
                GC.SOUNDDICT['Experience Gain'].stop() 
            # Extra time to account for pause at end
            if currentTime - self.state_time >= self.total_time_for_exp + 500:
                self.state.clear()
                self.state.changeState('levelUp')
                self.state.changeState('exp_leave')
                self.exp_bar.fade_out()
                self.state_time = currentTime

        # Display the level up animation initial
        elif self.state.getState() == 'levelUp':
            if not self.level_up_sound_played:
                GC.SOUNDDICT['Level Up'].play()
                self.level_up_sound_played = True
            # Update it
            if self.levelUpAnimation.update(gameStateObj):
                if self.in_combat:
                    self.in_combat.darken_ui()
                self.state.changeState('levelScreen')
                self.state_time = currentTime

        # Display the level up stat screen
        elif self.state.getState() == 'levelScreen':
            time_to_wait = self.LEVELUPWAIT + (self.get_num_sparks()+1)*self.SPARKTIME + 500
            # Am i Done displaying?
            if currentTime - self.state_time >= time_to_wait:
                if self.in_combat:
                    self.in_combat.lighten_ui()
                # Handle EXP when the user levels up, if this is not a forced level
                if not self.force_level:
                    self.unit.exp += self.expNew
                    if self.unit.exp >= 100:
                        self.unit.exp = self.expNew - (100 - self.expOld)
                # Remove animations
                self.animations = []
                # check for weapon gain
                if self.new_wexp:
                    self.unit.increase_wexp(self.new_wexp, gameStateObj)
                # check for skill gain if not a forced level
                if not self.force_level:
                    for level_needed, class_skill in metaDataObj['class_dict'][self.unit.klass]['skills']:
                        if self.unit.level%cf.CONSTANTS['max_level'] == level_needed:
                            if class_skill == 'Feat':
                                gameStateObj.cursor.currentSelectedUnit = self.unit
                                gameStateObj.stateMachine.changeState('feat_choice')
                            else:
                                skill = StatusObject.statusparser(class_skill)
                                # If we don't already have this skill
                                if skill.stack or skill.id not in (s.id for s in self.unit.status_effects):
                                    StatusObject.HandleStatusAddition(skill, self.unit, gameStateObj)
                                    gameStateObj.banners.append(Banner.gainedSkillBanner(self.unit, skill))
                                    gameStateObj.stateMachine.changeState('itemgain')
                
                return True

        # Wait 100 milliseconds before transferring us to the promotion state
        elif self.state.getState() == 'prepare_promote':
            self.expSet = 99
            self.exp_bar.update(self.expSet)
            if currentTime - self.state_time > 100:
                if cf.CONSTANTS['auto_promote'] and metaDataObj['class_dict'][self.unit.klass]['turns_into']: # If has at least one class to turn into
                    self.expSet = 0
                    class_options = metaDataObj['class_dict'][self.unit.klass]['turns_into']
                    if len(class_options) > 1:
                        gameStateObj.cursor.currentSelectedUnit = self.unit
                        gameStateObj.stateMachine.changeState('promotion_choice')
                        gameStateObj.stateMachine.changeState('transition_out')
                        self.state.changeState('wait')
                        self.state_time = currentTime
                    elif len(class_options) == 1:
                        gameStateObj.cursor.currentSelectedUnit = self.unit
                        self.unit.new_klass = class_options[0]
                        gameStateObj.stateMachine.changeState('promotion')
                        gameStateObj.stateMachine.changeState('transition_out')
                        # self.state.changeState('promote')
                        self.state.changeState('wait')
                        self.state_time = currentTime
                    else:
                        self.unit.exp = 99
                        return True # Done
                else: # Unit is at the highest point it can be. No more.
                    self.unit.exp = 99
                    return True # Done

        elif self.state.getState() == 'item_promote':
            if metaDataObj['class_dict'][self.unit.klass]['turns_into']: # If has at least one class to turn into
                class_options = metaDataObj['class_dict'][self.unit.klass]['turns_into']
                if len(class_options) > 1:
                    gameStateObj.cursor.currentSelectedUnit = self.unit
                    gameStateObj.stateMachine.changeState('promotion_choice')
                    gameStateObj.stateMachine.changeState('transition_out')
                    self.state.changeState('wait')
                    self.state_time = currentTime
                elif len(class_options) == 1:
                    gameStateObj.cursor.currentSelectedUnit = self.unit
                    self.unit.new_klass = class_options[0]
                    gameStateObj.stateMachine.changeState('promotion')
                    gameStateObj.stateMachine.changeState('transition_out')
                    # self.state.changeState('promote')
                    self.state.changeState('wait')
                    self.state_time = currentTime
                else:
                    self.unit.exp = 99
                    return True # Done
            else: # Unit is at the highest point it can be. No more.
                self.unit.exp = 99
                return True # Done

        elif self.state.getState() == 'wait':
            if currentTime - self.state_time > 1000:  # Wait a while
                return True

        elif self.state.getState() == 'promote':
            # Class should already have been changed by now in the levelpromote state
            # Here's where I change all the important information
            new_class = metaDataObj['class_dict'][self.unit.klass]
            old_anim = self.unit.battle_anim
            self.unit.removeSprites()
            self.unit.loadSprites()
            # Reseed the combat animation
            if self.in_combat and old_anim:
                item = self.unit.getMainWeapon()
                magic = CustomObjects.WEAPON_TRIANGLE.isMagic(item) if item else False
                anim = GC.ANIMDICT.partake(self.unit.klass, self.unit.gender, item, magic)
                if anim:
                    # Build animation
                    script = anim['script']
                    if self.unit.name in anim['images']:
                        frame_dir = anim['images'][self.unit.name]
                    else:
                        frame_dir = anim['images']['Generic' + Utility.get_color(self.unit.team)]
                    import BattleAnimation
                    self.unit.battle_anim = BattleAnimation.BattleAnimation(self.unit, frame_dir, script)
                    self.unit.battle_anim.awake(owner=old_anim.owner, parent=old_anim.parent, partner=old_anim.partner,
                                                right=old_anim.right, at_range=old_anim.at_range, init_speed=old_anim.entrance,
                                                init_position=old_anim.init_position)
                else:
                    self.unit.battle_anim = old_anim
            # Reset Level - Don't!
            self.unit.level += 1
            # Actually change class
            # Reset movement group
            self.unit.movement_group = new_class['movement_group']
            # Add weapon exp gains from that class.
            # This right here!
            self.new_wexp = new_class['wexp_gain']
            # Add any extra tags
            if new_class['tags']: # Add any necessary tags. Does not currently take away tags, although it may have to later
                self.unit.tags |= new_class['tags']
            # Give promotion
            # self.levelup_list = self.unit.level_up(new_class, apply_level=False) # Level up once, then promote.
            # self.levelup_list = [x + y for x, y in zip(self.levelup_list, new_class['promotion'])] # Add lists together
            self.levelup_list = new_class['promotion'] # No two level ups, too much gain in one level...
            current_stats = self.unit.stats.values()
            assert len(self.levelup_list) == len(new_class['max']) == len(current_stats), "%s %s %s"%(self.levelup_list, new_class['max'], current_stats)
            for index, stat in enumerate(self.levelup_list):
                self.levelup_list[index] = min(stat, new_class['max'][index] - current_stats[index].base_stat)
            self.unit.apply_levelup(self.levelup_list)

            if self.in_combat:
                self.in_combat.darken_ui()

            self.state.changeState('levelScreen')
            self.state_time = currentTime # Reset time so that it doesn't skip right over LevelScreen
        
        return False

    def draw(self, surf, gameStateObj):
        currentTime = Engine.get_time()
        # if should be displaying exp bar OR should be displaying level Up screen
        if self.state.getState() in ['exp_wait', 'exp_leave', 'exp0', 'exp100', 'init', 'prepare_promote']:
            if self.exp_bar:
                self.exp_bar.draw(surf)

        elif self.state.getState() == 'levelUp':
            self.levelUpAnimation.draw(surf, gameStateObj)
            """
            marker1 = self.animationMarker[0]
            marker2 = self.animationMarker[1]
            LvlSurf = Engine.subsurface(self.levelUpAnimation, (marker2*78, marker1*16, 78, 16))
            x, y = self.unit.position
            topleft = (x-gameStateObj.cameraOffset.x-2)*GC.TILEWIDTH, (y-gameStateObj.cameraOffset.y-1)*GC.TILEHEIGHT
            surf.blit(LvlSurf, topleft)
            """

        elif self.state.getState() == 'levelScreen':
            # Highlight underline -- yellow, blue
            new_color = Image_Modification.color_transition2((88, 16, -40), (-80, -32, 40))
            # Scroll out
            if currentTime - self.state_time > self.LEVELUPWAIT + (self.get_num_sparks()+1)*self.SPARKTIME + 300:
                self.unit_scroll_offset += 10
                self.screen_scroll_offset += 20
                self.animations = []
            else: # scroll in
                if self.unit_scroll_offset:
                    self.lastSparkUpdate = currentTime - 300 # add 300 extra milliseconds of waiting at beginning
                self.unit_scroll_offset -= 10
                self.unit_scroll_offset = max(0, self.unit_scroll_offset)
                self.screen_scroll_offset -= 20
                self.screen_scroll_offset = max(0, self.screen_scroll_offset)

            DisplayWidth = self.levelUpScreen.get_width()
            DisplayHeight = self.levelUpScreen.get_height()
            # Level up screen
            LevelUpSurface = Engine.create_surface((DisplayWidth, DisplayHeight), transparent=True, convert=True)
            # Create background
            LevelSurf = self.levelUpScreen
            LevelUpSurface.blit(LevelSurf, (0, 0))

            # Render top banner text
            long_name = gameStateObj.metaDataObj['class_dict'][self.unit.klass]['long_name']
            GC.FONT['text_white'].blit(long_name, LevelUpSurface, (12, 3))
            GC.FONT['text_yellow'].blit(cf.WORDS['Lv'], LevelUpSurface, (LevelUpSurface.get_width()/2+12, 3))
            if self.first_spark_flag or self.force_level:
                level = str(self.unit.level)
            else:
                level = str(self.unit.level - 1)
            GC.FONT['text_blue'].blit(level, LevelUpSurface, (LevelUpSurface.get_width()/2+50-GC.FONT['text_blue'].size(level)[0], 3))

            # Blit first spark
            if self.force_level and not self.first_spark_flag:
                self.first_spark_flag = True
                self.lastSparkUpdate = currentTime
            elif self.screen_scroll_offset == 0 and not self.first_spark_flag and currentTime - self.lastSparkUpdate > self.SPARKTIME + 500:
                position = (87, 27)
                spark_animation = CustomObjects.Animation(self.statupanimation, position, (11, 1), animation_speed=32, ignore_map=True)
                self.animations.append(spark_animation)
                self.first_spark_flag = True
                self.lastSparkUpdate = currentTime
                # Sound
                GC.SOUNDDICT['Level_Up_Level'].play()
            
            # Add sparks to animation list one at a time
            if self.first_spark_flag and currentTime - self.lastSparkUpdate > self.SPARKTIME:
                self.sparkCounter += 1
                self.sparkUp = True # Whether the sparkCounter was actually incremented or not
                if self.sparkCounter > 7:
                    self.sparkCounter = 7
                    self.sparkUp = False
                else:
                    while self.levelup_list[self.sparkCounter] == 0:
                        self.sparkCounter += 1
                        self.sparkUp = True
                        if self.sparkCounter > 7:
                            self.sparkCounter = 7
                            self.sparkUp = False
                            break

                if self.sparkUp:
                    self.underline_offset = 36 # for underline growing
                    # Add animations and Sound
                    # Animations
                    if self.sparkCounter >= 4:
                        position = (88, (self.sparkCounter - 4)*GC.TILEHEIGHT + 61)
                    else:
                        position = (24, self.sparkCounter*GC.TILEHEIGHT + 61)
                    arrow_animation = CustomObjects.Animation(self.uparrow, (position[0]+31, position[1]-37), (10, 1), animation_speed=32, ignore_map=True, hold=True)
                    self.arrow_animations.append(arrow_animation) 
                    spark_animation = CustomObjects.Animation(self.statupanimation, position, (11, 1), animation_speed=32, ignore_map=True)
                    self.animations.append(spark_animation)
                    # Only 1-7 are supported increases for a levelup right now
                    # assert 8 > self.levelup_list[self.sparkCounter] > 0, "%s %s"%(self.levelup_list, self.levelup_list[self.sparkCounter])
                    if 1 <= self.levelup_list[self.sparkCounter] <= 4:
                        row = Engine.subsurface(self.numbers, (0, (self.levelup_list[self.sparkCounter] - 1)*24, 10*28, 24))
                        number_animation = CustomObjects.Animation(row, (position[0]+29, position[1]+23), (10, 1), animation_speed=32, ignore_map=True, hold=True)
                    else:
                        row = Engine.subsurface(self.numbers, (0, (Utility.clamp(self.levelup_list[self.sparkCounter], 1, 7) - 1)*24, 2*28, 24))
                        number_animation = CustomObjects.Animation(row, (position[0]+29, position[1]+23), (2, 1), animation_speed=32, ignore_map=True, hold=True)
                    number_animation.frameCount = -5 # delay this animation for 5 frames
                    self.animations.append(number_animation)
                    # Sound
                    GC.SOUNDDICT['Stat Up'].play()

                self.lastSparkUpdate = currentTime # Reset the last update time.

            # HP, Str, Mag, Skl, Spd, Luck, Def, Res
            new_underline_surf = Image_Modification.change_image_color(self.statunderline, new_color)
            for num in range(len(self.levelup_list[0:self.sparkCounter+1])):
                if self.levelup_list[num] > 0: # IE it should be updated, since it leveled up
                    if num == self.sparkCounter: 
                        rect = (self.underline_offset, 0, new_underline_surf.get_width() - self.underline_offset, 3)
                        new_underline_surf = Engine.subsurface(new_underline_surf, rect)
                        self.underline_offset -= 6
                        self.underline_offset = max(0, self.underline_offset)
                        if num >= 4:
                            topleft = (76 + self.underline_offset/2, 45 + GC.TILEHEIGHT * (num - 4))
                        else:
                            topleft = (12 + self.underline_offset/2, 45 + GC.TILEHEIGHT * (num))
                    else:
                        if num >= 4:
                            topleft = (76, 45 + GC.TILEHEIGHT * (num - 4))
                        else:
                            topleft = (12, 45 + GC.TILEHEIGHT * (num))
                    LevelUpSurface.blit(new_underline_surf, topleft)

            # Update and draw arrow animations
            self.arrow_animations = [animation for animation in self.arrow_animations if not animation.update(gameStateObj)]
            for animation in self.arrow_animations:
                animation.draw(LevelUpSurface, gameStateObj, blend=new_color)
            # Update and draw number animations
            self.number_animations = [animation for animation in self.number_animations if not animation.update(gameStateObj)]
            for animation in self.number_animations:
                animation.draw(LevelUpSurface, gameStateObj, blend=new_color)

            GC.FONT['text_yellow'].blit('HP', LevelUpSurface, (10, 35))
            GC.FONT['text_yellow'].blit(cf.WORDS['STR'], LevelUpSurface, (10, GC.TILEHEIGHT + 35))
            GC.FONT['text_yellow'].blit(cf.WORDS['MAG'], LevelUpSurface, (10, GC.TILEHEIGHT*2+35))
            GC.FONT['text_yellow'].blit(cf.WORDS['SKL'], LevelUpSurface, (10, GC.TILEHEIGHT*3+35))
            GC.FONT['text_yellow'].blit(cf.WORDS['SPD'], LevelUpSurface, (LevelUpSurface.get_width()/2+8, 35))
            GC.FONT['text_yellow'].blit(cf.WORDS['LCK'], LevelUpSurface, (LevelUpSurface.get_width()/2+8, GC.TILEHEIGHT+35))
            GC.FONT['text_yellow'].blit(cf.WORDS['DEF'], LevelUpSurface, (LevelUpSurface.get_width()/2+8, GC.TILEHEIGHT*2+35))
            GC.FONT['text_yellow'].blit(cf.WORDS['RES'], LevelUpSurface, (LevelUpSurface.get_width()/2+8, GC.TILEHEIGHT*3+35))

            hp_text = self.unit.stats['HP'].base_stat - (self.levelup_list[0] if self.sparkCounter < 0 else 0)
            str_text = self.unit.stats['STR'].base_stat - (self.levelup_list[1] if self.sparkCounter < 1 else 0)
            mag_text = self.unit.stats['MAG'].base_stat - (self.levelup_list[2] if self.sparkCounter < 2 else 0)
            skl_text = self.unit.stats['SKL'].base_stat - (self.levelup_list[3] if self.sparkCounter < 3 else 0)
            spd_text = self.unit.stats['SPD'].base_stat - (self.levelup_list[4] if self.sparkCounter < 4 else 0)
            lck_text = self.unit.stats['LCK'].base_stat - (self.levelup_list[5] if self.sparkCounter < 5 else 0)
            def_text = self.unit.stats['DEF'].base_stat - (self.levelup_list[6] if self.sparkCounter < 6 else 0)
            res_text = self.unit.stats['RES'].base_stat - (self.levelup_list[7] if self.sparkCounter < 7 else 0)

            GC.FONT['text_blue'].blit(str(hp_text), LevelUpSurface, (50 - GC.FONT['text_blue'].size(str(hp_text))[0], 35))
            GC.FONT['text_blue'].blit(str(str_text), LevelUpSurface, (50 - GC.FONT['text_blue'].size(str(str_text))[0], GC.TILEHEIGHT+35))
            GC.FONT['text_blue'].blit(str(mag_text), LevelUpSurface, (50 - GC.FONT['text_blue'].size(str(mag_text))[0], GC.TILEHEIGHT*2+35))
            GC.FONT['text_blue'].blit(str(skl_text), LevelUpSurface, (50 - GC.FONT['text_blue'].size(str(skl_text))[0], GC.TILEHEIGHT*3+35))
            GC.FONT['text_blue'].blit(str(spd_text), LevelUpSurface, (LevelUpSurface.get_width()/2+48-GC.FONT['text_blue'].size(str(spd_text))[0], 35))
            GC.FONT['text_blue'].blit(str(lck_text), LevelUpSurface, (LevelUpSurface.get_width()/2+48-GC.FONT['text_blue'].size(str(lck_text))[0], GC.TILEHEIGHT+35))
            GC.FONT['text_blue'].blit(str(def_text), LevelUpSurface, (LevelUpSurface.get_width()/2+48-GC.FONT['text_blue'].size(str(def_text))[0], GC.TILEHEIGHT*2+35))
            GC.FONT['text_blue'].blit(str(res_text), LevelUpSurface, (LevelUpSurface.get_width()/2+48-GC.FONT['text_blue'].size(str(res_text))[0], GC.TILEHEIGHT*3+35))

            """
            # HP, Str, Mag, Skl, Spd, Luck, Def, Res
            for num in range(len(self.levelup_list[0:self.sparkCounter])):
                if self.levelup_list[num] != 0: # IE it should be updated, since it leveled up
                    # Blit number
                    if num >= 4:
                        topleft = (LevelUpSurface.get_width()/2+50, GC.TILEHEIGHT * (num - 4) + 33)
                    else:
                        topleft = (52, GC.TILEHEIGHT * num + 33)
                    change = str(self.levelup_list[num])
                    if self.levelup_list[num] > 0:
                        change = '+' + change
                    GC.FONT['stat_white'].blit(change, LevelUpSurface, topleft)
            """
            pos = (6 - self.screen_scroll_offset, GC.WINHEIGHT - 8 - LevelUpSurface.get_height())
            surf.blit(LevelUpSurface, pos)

            # Blit unit's pic
            BigPortraitSurf = self.unit.bigportrait
            pos = (GC.WINWIDTH - BigPortraitSurf.get_width() - 4, GC.WINHEIGHT + self.unit_scroll_offset - BigPortraitSurf.get_height())
            surf.blit(BigPortraitSurf, pos)

        # Update and draw animations
        self.animations = [animation for animation in self.animations if not animation.update(gameStateObj)]
        for animation in self.animations:
            animation.draw(surf, gameStateObj)

class Exp_Bar(object):
    def __init__(self, expSet, center=True):
        self.background = Engine.subsurface(GC.IMAGESDICT['ExpBar'], (0, 0, 136, 24))
        self.begin = Engine.subsurface(GC.IMAGESDICT['ExpBar'], (0, 24, 3, 7))
        self.middle = Engine.subsurface(GC.IMAGESDICT['ExpBar'], (3, 24, 1, 7))
        self.end = Engine.subsurface(GC.IMAGESDICT['ExpBar'], (4, 24, 2, 7))

        self.width = self.background.get_width()
        self.height = self.background.get_height()
        self.bg_surf = self.create_bg_surf()

        if center:
            self.pos = GC.WINWIDTH/2 - self.width/2, GC.WINHEIGHT/2 - self.height/2
        else:
            self.pos = GC.WINWIDTH/2 - self.width/2, GC.WINHEIGHT - self.height

        self.sprite_offset = self.height/2
        self.done = False

        self.num = expSet

    def create_bg_surf(self):
        # Create surf
        surf = Engine.create_surface((self.width, self.height), transparent=True, convert=True)
        # Blit background
        surf.blit(self.background, (0, 0))
        # Blit beginning sprite
        surf.blit(self.begin, (7, 9))
        return surf

    def fade_out(self):
        self.done = True

    def update(self, expSet):
        if self.done:
            self.sprite_offset += 1
            if self.sprite_offset >= self.height/2:
                return True
        elif self.sprite_offset > 0:
            self.sprite_offset -= 1
        self.num = expSet

    def draw(self, surf):
        new_surf = Engine.create_surface((self.width, self.height))
        new_surf.blit(self.bg_surf, (0, 0))

        # Blit the correct number of sprites for the middle of the EXP bar
        indexpixel = int((max(0, self.num)))
        for x in range(indexpixel):
            new_surf.blit(self.middle, (10 + x, 9))

        # Blit sprite for end of EXP bar
        new_surf.blit(self.end, (10 + indexpixel, 9))

        # Blit current amount of exp
        position = (self.width - GC.FONT['number_small3'].size(str(self.num))[0] - 4, 4)
        GC.FONT['number_small3'].blit(str(self.num), new_surf, position)

        new_surf = Engine.subsurface(new_surf, (0, self.sprite_offset, self.width, self.height - self.sprite_offset*2))

        surf.blit(new_surf, (self.pos[0], self.pos[1] + self.sprite_offset))
