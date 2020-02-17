from . import GlobalConstants as GC
from . import configuration as cf
from . import StateMachine, Interaction, Image_Modification, Engine
from . import Utility, ClassData, Background
from . import Weapons, BattleAnimation, MenuFunctions, TextChunk

class PromotionChoiceState(StateMachine.State):
    name = 'promotion_choice'
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.unit = gameStateObj.cursor.currentSelectedUnit
            self.class_options = ClassData.class_dict[self.unit.klass]['turns_into']
            display_options = [ClassData.class_dict[c]['long_name'] for c in self.class_options]
            self.menu = MenuFunctions.ChoiceMenu(self.unit, display_options, (14, 13), width=80)

            self.on_child_menu = False
            self.child_menu = None

            # Animations
            self.animations = []
            self.weapon_icons = []
            for option in self.class_options:
                anim = GC.ANIMDICT.partake(option, self.unit.gender)
                if anim:
                    # Build animation
                    script = anim['script']
                    name = None
                    if self.unit.id in anim['images']:
                        name = self.unit.id
                    elif self.unit.name in anim['images']:
                        name = self.unit.name
                    else:
                        color = 'Blue' if self.unit.team == 'player' else 'Red'
                        name = 'Generic' + color
                    frame_dir = anim['images'][name]
                    anim = BattleAnimation.BattleAnimation(self.unit, frame_dir, script, name)
                    anim.awake(owner=self, parent=None, partner=None, right=True, at_range=False) # Stand
                self.animations.append(anim)
                # Build weapon icons
                weapons = []
                for idx, wexp in enumerate(ClassData.class_dict[option]['wexp_gain']):
                    if wexp > 0:
                        weapons.append(Weapons.Icon(idx=idx))
                self.weapon_icons.append(weapons)

            # Platforms
            platform_type = gameStateObj.map.tiles[self.unit.position].platform if self.unit.position else 'Floor'
            suffix = '-Melee'
            self.left_platform = GC.IMAGESDICT[platform_type + suffix].copy()
            self.right_platform = Engine.flip_horiz(self.left_platform.copy())

            self.anim_offset = 120
            self.target_anim_offset = False

            gameStateObj.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])

            # Transition in:
            if gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'DOWN':
            GC.SOUNDDICT['Select 6'].play()
            if self.on_child_menu:
                self.child_menu.moveDown()
            else:
                self.menu.moveDown()
                self.target_anim_offset = True
        elif event == 'UP':
            GC.SOUNDDICT['Select 6'].play()
            if self.on_child_menu:
                self.child_menu.moveDown()
            else:
                self.menu.moveUp()
                self.target_anim_offset = True

        elif event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            if self.on_child_menu:
                self.on_child_menu = False
                self.child_menu = None
            else:
                pass # Can't go back...
        
        elif event == 'SELECT':
            if self.on_child_menu:
                selection = self.child_menu.getSelection()
                if selection == cf.WORDS['Change']:
                    self.unit.new_klass = self.class_options[self.menu.getSelectionIndex()]
                    GC.SOUNDDICT['Select 1'].play()
                    gameStateObj.stateMachine.changeState('promotion')
                    gameStateObj.stateMachine.changeState('transition_out')
                else:
                    GC.SOUNDDICT['Select 4'].play()
                    self.on_child_menu = False
                    self.child_menu = None
            else:
                GC.SOUNDDICT['Select 1'].play()
                selection = self.menu.getSelection()
                # Create child menu with additional options
                options = [cf.WORDS['Change'], cf.WORDS['Cancel']]
                self.child_menu = MenuFunctions.ChoiceMenu(selection, options, (72, 32 + self.menu.currentSelection*16))
                self.on_child_menu = True

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        self.menu.update()
        if self.child_menu:
            self.child_menu.update()

        if self.target_anim_offset:
            self.anim_offset += 8
            if self.anim_offset > 120:
                self.target_anim_offset = False
                self.anim_offset = 120
        else:
            self.anim_offset -= 8
            if self.anim_offset < 0:
                self.anim_offset = 0

        anim = self.animations[self.menu.currentSelection]
        if anim:
            anim.update()

    def draw(self, gameStateObj, metaDataObj):
        # surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        surf = gameStateObj.generic_surf
        if gameStateObj.background:
            if gameStateObj.background.draw(surf):
                gameStateObj.background = None
        # Anim
        top = 88
        surf.blit(self.left_platform, (GC.WINWIDTH // 2 - self.left_platform.get_width() + self.anim_offset + 52, top))
        surf.blit(self.right_platform, (GC.WINWIDTH // 2 + self.anim_offset + 52, top))
        anim = self.animations[self.menu.currentSelection]
        if anim:
            anim.draw(surf, (self.anim_offset + 12, 0))

        # Class Reel
        GC.FONT['class_purple'].blit(self.menu.getSelection(), surf, (114, 5))

        # Weapon Icons
        for idx, weapon in enumerate(self.weapon_icons[self.menu.getSelectionIndex()]):
            weapon.draw(surf, (130 + 16*idx, 32))

        # Menus
        self.menu.draw(surf, gameStateObj)
        if self.child_menu:
            self.child_menu.draw(surf, gameStateObj)

        surf.blit(GC.IMAGESDICT['PromotionDescription'], (6, 112))

        # Description
        font = GC.FONT['convo_white']
        desc = ClassData.class_dict[self.class_options[self.menu.getSelectionIndex()]]['desc']
        text = TextChunk.line_wrap(TextChunk.line_chunk(desc), 208, font)
        for idx, line in enumerate(text):
            font.blit(line, surf, (14, font.height * idx + 120))

        return surf

class PromotionState(StateMachine.State):
    name = 'promotion'
    show_map = False

    def begin(self, gameStateObj, metaDataObj):
        self.last_update = Engine.get_time()

        if not self.started:
            # Start music
            self.promotion_music = cf.CONSTANTS.get('music_promotion')
            if self.promotion_music:
                next_song = Engine.music_thread.fade_in(GC.MUSICDICT[self.promotion_music])
                if not next_song:  # Same song as before
                    self.promotion_music = None

            self.unit = gameStateObj.cursor.currentSelectedUnit
            color = Utility.get_color(self.unit.team)

            # Old - Right - Animation
            self.right_anim = GC.ANIMDICT.partake(self.unit.klass, self.unit.gender)
            if self.right_anim:
                # Build animation
                script = self.right_anim['script']
                name = None
                if self.unit.id in self.right_anim['images']:
                    name = self.unit.id
                elif self.unit.name in self.right_anim['images']:
                    name = self.unit.name
                else:
                    name = 'Generic' + color
                frame_dir = self.right_anim['images'].get(name, None)
                if frame_dir:
                    self.right_anim = BattleAnimation.BattleAnimation(self.unit, frame_dir, script, name)
                else:
                    self.right_anim = None
            # New - Left - Animation
            self.left_anim = GC.ANIMDICT.partake(self.unit.new_klass, self.unit.gender)
            if self.left_anim:
                # Build animation
                script = self.left_anim['script']
                name = None
                if self.unit.id in self.left_anim['images']:
                    name = self.unit.id
                elif self.unit.name in self.left_anim['images']:
                    name = self.unit.name
                else:
                    name = 'Generic' + color
                frame_dir = self.left_anim['images'].get(name, None)
                if frame_dir:
                    self.left_anim = BattleAnimation.BattleAnimation(self.unit, frame_dir, script, name)
                else:
                    self.left_anim = None
            if self.right_anim:
                self.right_anim.awake(owner=self, parent=None, partner=self.left_anim if self.left_anim else None, right=True, at_range=False) # Stand
            if self.left_anim:
                self.left_anim.awake(owner=self, parent=None, partner=self.right_anim if self.right_anim else None, right=False, at_range=False) # Stand

            self.current_anim = self.right_anim

            # Platforms
            platform = 'Floor-Melee'
            self.left_platform = GC.IMAGESDICT[platform].copy()
            self.right_platform = Engine.flip_horiz(self.left_platform.copy())

            gameStateObj.background = Background.StaticBackground(GC.IMAGESDICT['Promotion'], fade=False)

            # Name Tag
            self.name_tag = GC.IMAGESDICT[color + 'RightCombatName'].copy()
            size_x = GC.FONT['text_brown'].size(self.unit.name)[0]
            GC.FONT['text_brown'].blit(self.unit.name, self.name_tag, (36 - size_x // 2, 8))

            # For darken backgrounds and drawing
            self.darken_background = 0
            self.target_dark = 0
            self.darken_ui_background = 0
            self.foreground = Background.Foreground()
            self.combat_surf = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT), transparent=True)

            self.current_state = 'Init'

            if not self.right_anim or not self.left_anim:
                self.finalize(Engine.get_time(), gameStateObj)
            elif gameStateObj.stateMachine.from_transition():
                gameStateObj.stateMachine.changeState("transition_in")
                return 'repeat'

    def flash_color(self, num_frames, fade_out=0, color=(248, 248, 248)):
        self.foreground.flash(num_frames, fade_out, color)

    def darken(self):
        self.target_dark += 4

    def lighten(self):
        self.target_dark -= 4

    def darken_ui(self):
        self.darken_ui_background = 1

    def lighten_ui(self):
        self.darken_ui_background = -3

    def start_anim(self, effect):
        anim = self.current_anim
        image, script = GC.ANIMDICT.get_effect(effect, anim.palette_name)
        child_effect = BattleAnimation.BattleAnimation(self.unit, image, script, anim.palette_name)
        child_effect.awake(anim.owner, anim.partner, anim.right, anim.at_range, parent=anim)
        child_effect.start_anim('Attack')
        anim.children.append(child_effect)

    def finalize(self, current_time, gameStateObj):
        self.current_state = 'Level_Up'
        self.last_update = current_time
        gameStateObj.exp_gain_struct = (self.unit, 0, self, 'promote')
        gameStateObj.stateMachine.changeState('exp_gain')

    def update_battle_anim(self, old_anim):
        """
        Done so that when in combat, the in combat animation updates also
        """
        item = self.unit.getMainWeapon()
        magic = item.is_magic() if item else False
        anim = GC.ANIMDICT.partake(self.unit.klass, self.unit.gender, item, magic)
        # anim = GC.ANIMDICT.partake(self.unit.klass, self.unit.gender)
        if anim:
            # Build animation
            script = anim['script']
            if self.unit.id in anim['images']:
                frame_dir = anim['images'][self.unit.id]
            elif self.unit.name in anim['images']:
                frame_dir = anim['images'][self.unit.name]
            else:
                frame_dir = anim['images']['Generic' + Utility.get_color(self.unit.team)]
            self.unit.battle_anim = BattleAnimation.BattleAnimation(self.unit, frame_dir, script)
            self.unit.battle_anim.awake(owner=old_anim.owner, parent=old_anim.parent, partner=old_anim.partner,
                                        right=old_anim.right, at_range=old_anim.at_range, init_speed=old_anim.init_speed,
                                        init_position=old_anim.init_position)
            self.unit.battle_anim.entrance = 0
        else:
            self.unit.battle_anim = old_anim

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        # print(self.current_state)

        current_time = Engine.get_time()
        if self.current_state == 'Init':
            if current_time - self.last_update > 410:  # 25 frames
                self.current_state = 'Right'
                self.last_update = current_time
                self.start_anim('Promotion1')

        elif self.current_state == 'Right':
            if not self.current_anim.children:
                self.current_anim = self.left_anim
                self.current_state = 'Left'
                self.last_update = current_time
                self.start_anim('Promotion2')

        elif self.current_state == 'Left':
            if not self.current_anim.children:
                self.current_state = 'Wait'
                self.last_update = current_time

        elif self.current_state == 'Wait':
            if current_time - self.last_update > 1660:  # 100 frames
                self.finalize(current_time, gameStateObj)

        elif self.current_state == 'Level_Up':
            self.last_update = current_time
            self.current_state = 'Leave'

        elif self.current_state == 'Leave':
            if current_time - self.last_update > 160:  # 10 frames
                if isinstance(gameStateObj.combatInstance, Interaction.AnimationCombat):
                    gameStateObj.stateMachine.back()
                    gameStateObj.stateMachine.back()
                    gameStateObj.background = None
                else:
                    gameStateObj.stateMachine.changeState('transition_double_pop')
                    gameStateObj.background.fade_out()
                self.current_state = 'Done'  # Inert state
                if self.promotion_music:
                    Engine.music_thread.fade_back()
                return 'repeat'

        if self.current_anim:
            self.current_anim.update()

    def draw(self, gameStateObj, metaDataObj):
        # surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        surf = gameStateObj.generic_surf
        if gameStateObj.background:
            if gameStateObj.background.draw(surf):
                gameStateObj.background = None

        if self.darken_background or self.target_dark:
            bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - abs(int(self.darken_background * 12.5)))
            surf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 1
            elif self.target_dark < self.darken_background:
                self.darken_background -= 1

        # Make combat surf
        combat_surf = Engine.copy_surface(self.combat_surf)

        # Platforms
        top = 88
        combat_surf.blit(self.left_platform, (GC.WINWIDTH // 2 - self.left_platform.get_width(), top))
        combat_surf.blit(self.right_platform, (GC.WINWIDTH // 2, top))

        # Name Tag
        combat_surf.blit(self.name_tag, (GC.WINWIDTH + 3 - self.name_tag.get_width(), 0))

        if self.darken_ui_background:
            self.darken_ui_background = min(self.darken_ui_background, 4)
            # bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - abs(int(self.darken_ui_background*11.5)))
            color = 255 - abs(self.darken_ui_background * 24)
            Engine.fill(combat_surf, (color, color, color), None, Engine.BLEND_RGB_MULT)
            # combat_surf.blit(bg, (0, 0))
            self.darken_ui_background += 1

        surf.blit(combat_surf, (0, 0))

        # Anim
        if self.current_anim:
            self.current_anim.draw(surf, (0, 0))
        # Screen flash
        self.foreground.draw(surf)

        return surf
