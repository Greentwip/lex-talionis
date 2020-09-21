# Display Unit Info function
from . import GlobalConstants as GC
from . import configuration as cf
from . import StateMachine, CustomObjects, Image_Modification, Engine, Action
from . import StatusCatalog, Banner, Utility, ClassData, HelpMenu

####################################################################
class GainExpState(StateMachine.State):
    name = 'exp_gain'
    
    def begin(self, gameStateObj, metaDataObj):
        gameStateObj.cursor.drawState = 0
        if not self.started:
            if gameStateObj.exp_gain_struct is None:
                # Generally can only happen if a player character attacks a player character
                # Then two exp_gain commands will be put on the stack
                # but of course the second exp gain struct will be overwrite the first
                # So we just ignore the first
                gameStateObj.stateMachine.back()
                return 'repeat'
            self.unit, self.exp_gain, self.combat_object, self.starting_state, = \
                gameStateObj.exp_gain_struct
            gameStateObj.exp_gain_struct = None
            self.old_exp = self.unit.exp
            self.old_level = self.unit.level
            self.unit_klass = ClassData.class_dict[self.unit.klass]
            self.auto_promote = (cf.CONSTANTS['auto_promote'] or 'auto_promote' in self.unit.tags) and \
                self.unit_klass['turns_into'] and 'no_auto_promote' not in self.unit.tags

            self.state = CustomObjects.StateMachine(self.starting_state)
            self.state_time = Engine.get_time()
            self.exp_bar = None
            self.level_up_animation = None
            self.level_up_screen = None

            # If self.exp_gain is a list then this is a stat booster and is not necessary
            if not self.auto_promote and not isinstance(self.exp_gain, list):
                # Make sure we don't go over 0 exp if no autopromote
                max_exp = 100*(self.unit_klass['max_level'] - self.old_level) - self.old_exp
                self.exp_gain = min(self.exp_gain, max_exp)
            
            if self.unit.level >= self.unit_klass['max_level'] and not self.auto_promote and \
                    self.starting_state == 'init':
                # We only leave if we're just gaining exp
                # Gaining stats from boosters, promoting, or choosing promotions
                # Should just work anyways
                gameStateObj.stateMachine.back()  # Done here
                return "repeat"

            self.levelup_list = None
            self.new_wexp = None

            # timing
            self.total_time_for_exp = self.exp_gain * GC.FRAMERATE
            self.level_up_sound_played = False

    def create_level_up_logo(self, gameStateObj):
        if self.combat_object:
            topleft = (0, 6)
            timing = [1]*19 + [10, 1, 1, 1, 1, 1] + [2]*15 + [-1] + [1]*12
            self.level_up_animation = CustomObjects.Animation(
                GC.IMAGESDICT['LevelUpBattle'], topleft, (5, 11), 52, ignore_map=True,
                set_timing=timing)
        else:
            if self.unit.position:
                x, y = self.unit.position
                left = (x - gameStateObj.cameraOffset.x - 2) * GC.TILEWIDTH
                top = (y - gameStateObj.cameraOffset.y - 1) * GC.TILEHEIGHT
                topleft = left, top
            else:
                topleft = GC.WINWIDTH//2, GC.WINHEIGHT//2
            timing = [1]*24 + [44]
            self.level_up_animation = CustomObjects.Animation(
                GC.IMAGESDICT['LevelUpMap'], topleft, (5, 5), ignore_map=True,
                set_timing=timing)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)

        if event == 'SELECT' and self.state.getState() == 'level_screen':
            if self.level_up_screen:
                self.level_up_screen.select()

    def update(self, gameStateObj, metaDataObj):
        StateMachine.State.update(self, gameStateObj, metaDataObj)
        current_time = Engine.get_time()

        # Initiating State
        if self.state.getState() == 'init':
            self.exp_bar = Exp_Bar(self.old_exp, not self.combat_object)
            self.state_time = current_time
            self.state.changeState('exp_wait')

        # Wait before starting to increment exp
        elif self.state.getState() == 'exp_wait':
            self.exp_bar.update(self.old_exp)
            if current_time - self.state_time > 400:
                self.state.changeState('exp0')
                self.state_time = current_time
                GC.SOUNDDICT['Experience Gain'].play(-1)

        # Increment exp until done or 100 exp is reached
        elif self.state.getState() == 'exp0':
            progress = (current_time - self.state_time)/float(self.total_time_for_exp)
            exp_set = self.old_exp + progress * self.exp_gain
            exp_set = int(min(self.old_exp + self.exp_gain, exp_set))
            self.exp_bar.update(exp_set)

            # transition
            if exp_set >= self.old_exp + self.exp_gain:
                GC.SOUNDDICT['Experience Gain'].stop()

            if exp_set >= 100:
                max_level = self.unit_klass['max_level']
                if self.unit.level >= max_level:  # Do I promote?
                    GC.SOUNDDICT['Experience Gain'].stop()
                    if self.auto_promote:
                        self.exp_bar.update(100)
                        GC.SOUNDDICT['Level Up'].play()
                    else:
                        self.exp_bar.update(99)
                    self.state.clear()
                    self.state.changeState('prepare_promote')
                    self.state.changeState('exp_leave')
                    self.exp_bar.fade_out()
                    self.state_time = current_time
                else:
                    old_growth_points = self.unit.growth_points[:]
                    self.levelup_list = self.unit.level_up(gameStateObj, self.unit_klass)
                    Action.do(Action.RecordGrowthPoints(self.unit, old_growth_points), gameStateObj)
                    Action.do(Action.IncLevel(self.unit), gameStateObj)
                    Action.do(Action.ApplyLevelUp(self.unit, self.levelup_list), gameStateObj)
                    self.state.changeState('exp100')
            elif current_time - self.state_time >= self.total_time_for_exp + 500:
                self.state.clear()
                self.state.changeState('exp_leave')
                self.exp_bar.fade_out()
                self.state_time = current_time

        elif self.state.getState() == 'exp_leave':
            done = self.exp_bar.update()
            if done:
                Action.do(Action.GainExp(self.unit, self.exp_gain), gameStateObj)
                self.state.back()
                self.state_time = current_time
                if len(self.state.state) <= 0:
                    gameStateObj.stateMachine.back()

        elif self.state.getState() == 'exp100':
            progress = (current_time - self.state_time)/float(self.total_time_for_exp)
            exp_set = self.old_exp + (self.exp_gain * progress) - 100
            exp_set = int(min(self.old_exp + self.exp_gain - 100, exp_set))
            self.exp_bar.update(exp_set)

            if exp_set >= self.old_exp + self.exp_gain - 100:
                GC.SOUNDDICT['Experience Gain'].stop()

            # Extra time to account for pause at end
            if current_time - self.state_time >= self.total_time_for_exp + 500:
                self.create_level_up_logo(gameStateObj)
                self.state.clear()
                self.state.changeState('level_up')
                self.state.changeState('exp_leave')
                self.exp_bar.fade_out()
                self.state_time = current_time

        elif self.state.getState() == 'level_up':
            if not self.level_up_sound_played:
                GC.SOUNDDICT['Level Up'].play()
                self.level_up_sound_played = True

            if self.level_up_animation.update(gameStateObj):
                if self.combat_object:
                    self.combat_object.darken_ui()
                self.state.changeState('level_screen')
                self.state_time = current_time

        elif self.state.getState() == 'level_screen':
            if not self.level_up_screen:
                use_quote = self.starting_state not in ("booster", "prepare_promote", "item_promote")
                self.level_up_screen = LevelUpScreen(
                    self.unit, self.levelup_list, self.old_level, self.unit.level, use_quote)
            if self.level_up_screen.update(current_time):
                gameStateObj.stateMachine.back()
                if self.combat_object:
                    self.combat_object.lighten_ui()
                # check for weapon experience gain
                if self.new_wexp:
                    Action.do(Action.GainWexp(self.unit, self.new_wexp), gameStateObj)
                # check for skill gain unless you are using a booster
                if self.starting_state != "booster":
                    unit_klass = ClassData.class_dict[self.unit.klass]
                    for level_needed, class_skill in unit_klass['skills']:
                        if self.unit.level == level_needed:
                            if class_skill == 'Feat':
                                gameStateObj.cursor.currentSelectedUnit = self.unit
                                gameStateObj.stateMachine.changeState('feat_choice')
                            else:
                                skill = StatusCatalog.statusparser(class_skill, gameStateObj)
                                # If we don't already have this skill
                                if skill.stack or skill.id not in (s.id for s in self.unit.status_effects):
                                    Action.do(Action.AddStatus(self.unit, skill), gameStateObj)
                                    gameStateObj.banners.append(Banner.gainedSkillBanner(self.unit, skill))
                                    gameStateObj.stateMachine.changeState('itemgain')

        # Wait 100 ms before transferring to the promotion state
        elif self.state.getState() == 'prepare_promote':
            self.exp_bar.update()
            if current_time - self.state_time > 100:
                class_options = self.unit_klass['turns_into']
                if self.auto_promote:
                    self.exp_bar.update(0)
                    if len(class_options) > 1:
                        gameStateObj.cursor.currentSelectedUnit = self.unit
                        gameStateObj.stateMachine.changeState('promotion_choice')
                        gameStateObj.stateMachine.changeState('transition_out')
                        # We are leaving
                        self.state.clear()
                        self.state.changeState('wait')
                        self.state_time = current_time
                    elif len(class_options) == 1:
                        gameStateObj.cursor.currentSelectedUnit = self.unit
                        self.unit.new_klass = class_options[0]
                        gameStateObj.stateMachine.changeState('promotion')
                        gameStateObj.stateMachine.changeState('transition_out')  # We are leaving
                        self.state.clear()
                        self.state.changeState('wait')
                        self.state_time = current_time
                    else:
                        Action.do(Action.SetExp(self.unit, 99), gameStateObj)
                        gameStateObj.stateMachine.back()
                else:
                    Action.do(Action.SetExp(self.unit, 99), gameStateObj)
                    gameStateObj.stateMachine.back()

        elif self.state.getState() == 'promote':
            old_anim = self.unit.battle_anim

            promote_action = Action.Promote(self.unit, self.unit.new_klass)
            self.levelup_list, self.new_wexp = promote_action.get_data()
            Action.do(promote_action, gameStateObj)

            if self.combat_object:
                self.combat_object.darken_ui()
                if old_anim:
                    self.combat_object.update_battle_anim(old_anim)

            self.state.clear()
            self.state.changeState('level_screen')
            self.state_time = current_time

        elif self.state.getState() == 'item_promote':
            class_options = self.unit_klass['turns_into']
            if len(class_options) > 1:
                gameStateObj.cursor.currentSelectedUnit = self.unit
                gameStateObj.stateMachine.changeState('promotion_choice')
                gameStateObj.stateMachine.changeState('transition_out')  # We are leaving
                self.state.changeState('wait')
                self.state_time = current_time
            elif len(class_options) == 1:
                gameStateObj.cursor.currentSelectedUnit = self.unit
                self.unit.new_klass = class_options[0]
                gameStateObj.stateMachine.changeState('promotion')
                gameStateObj.stateMachine.changeState('transition_out')  # We are leaving
                self.state.changeState('wait')
                self.state_time = current_time

        elif self.state.getState() == 'booster':
            # I store the levelup list for this in the exp slot
            self.levelup_list = self.exp_gain
            self.exp_gain = 0
            Action.do(Action.PermanentStatIncrease(self.unit, self.levelup_list), gameStateObj)
            self.old_level = self.unit.level
            self.state.changeState('level_screen')
            self.state_time = current_time

        elif self.state.getState() == 'wait':
            if current_time - self.state_time > 1000:  # Wait a while
                gameStateObj.stateMachine.back()

    def draw(self, gameStateObj, metaDataObj):
        if not self.started:
            return StateMachine.State.draw(self, gameStateObj, metaDataObj)

        if self.combat_object:
            under_state = gameStateObj.stateMachine.get_under_state(self)
            surf = under_state.draw(gameStateObj, metaDataObj)
        else:
            surf = StateMachine.State.draw(self, gameStateObj, metaDataObj)

        if self.state.getState() in ('init', 'exp_wait', 'exp_leave', 'exp0', 'exp100', 'prepare_promote'):
            if self.exp_bar:
                self.exp_bar.draw(surf)

        elif self.state.getState() == 'level_up':
            if self.level_up_animation:
                self.level_up_animation.draw(surf, gameStateObj)

        elif self.state.getState() == 'level_screen':
            if self.level_up_screen:
                self.level_up_screen.draw(surf, gameStateObj)

        return surf

class LevelUpScreen(object):
    bg = GC.IMAGESDICT['LevelScreen']
    width, height = bg.get_width(), bg.get_height()
    spark_time = 320
    level_up_wait = 1960

    spark = GC.IMAGESDICT['StatUpSpark']
    underline = GC.IMAGESDICT['StatUnderline']
    uparrow = GC.IMAGESDICT['LevelUpArrow']
    downarrow = GC.IMAGESDICT['LevelDownArrow']
    positive_numbers = GC.IMAGESDICT['LevelUpNumber']
    negative_numbers = GC.IMAGESDICT['LevelDownNumber']

    def __init__(self, unit, levelup_list, level1, level2, use_quote=False):
        self.unit = unit
        self.levelup_list = levelup_list[:8]
        self.level1 = level1
        self.level2 = level2
        self.current_spark = -1

        self.unit_scroll_offset = 80
        self.screen_scroll_offset = self.width + 32
        self.underline_offset = 36

        self.animations, self.arrow_animations = [], []

        self.state = 'scroll_in'
        self.state_time = 0

        # For level up quotes
        self.levelup_quote = self.get_levelup_quote()
        self.quote_dialog = None
        self.draw_flag = False
        if self.levelup_quote and use_quote:
            self.quote_dialog = HelpMenu.LevelUpQuote_Dialog(self.levelup_quote)
            # 16 characters per second
            # self.level_up_wait += int(62.5 * len(self.levelup_quote))  # Have it wait extra time if there's a level up quote

    def select(self):
        if self.quote_dialog and self.draw_flag and self.state == 'level_up_wait':
            if self.quote_dialog.end_text_position:
                self.begin_scroll_out()
            else:
                self.quote_dialog.start_time = 0  # Make the quote dialog complete

    def make_spark(self, topleft):
        return CustomObjects.Animation(
            self.spark, topleft, (11, 1), animation_speed=32,
            ignore_map=True)

    def get_position(self, i):
        if i >= 4:
            position = (self.width//2 + 8, (i - 4) * 16 + 35)
        else:
            position = (10, i * 16 + 35)
        return position

    def inc_spark(self):
        self.current_spark += 1
        if self.current_spark >= len(self.levelup_list):
            return True
        elif self.levelup_list[self.current_spark] == 0:
            return self.inc_spark()
        return False

    def get_levelup_quote(self):
        num_stats = len([stat for stat in self.levelup_list if stat > 0])
        if self.level2 < self.level1:  # Means you promoted
            return GC.LEVELUPQUOTES.get_promotion(self.unit.id, self.level2)
        if num_stats in (0, 1):
            if self.unit.capped_stats() and GC.LEVELUPQUOTES.get_capped(self.unit.id, self.level2):
                return GC.LEVELUPQUOTES.get_capped(self.unit.id, self.level2)
        return GC.LEVELUPQUOTES.get(self.unit.id, num_stats, self.level2)

    def begin_scroll_out(self):
        self.animations = []
        self.state = 'scroll_out'
        if self.quote_dialog:
            self.quote_dialog.set_transition_out()
        self.state_time = Engine.get_time()

    def update(self, current_time):
        if self.state == 'scroll_in':
            self.unit_scroll_offset = max(0, self.unit_scroll_offset - 10)
            self.screen_scroll_offset = max(0, self.screen_scroll_offset - 20)
            if self.unit_scroll_offset == 0 and self.screen_scroll_offset == 0:
                self.state = 'init_wait'
                self.state_time = current_time

        elif self.state == 'init_wait':
            if current_time - self.state_time > 300:
                if self.level1 == self.level2:  # Don't bother with level up spark
                    self.state = 'get_next_spark'
                else:
                    self.state = 'first_spark'
                    topleft = (87, 27)
                    self.animations.append(self.make_spark(topleft))
                    GC.SOUNDDICT['Level_Up_Level'].play()                
                self.state_time = current_time

        elif self.state == 'scroll_out':
            self.unit_scroll_offset += 10
            self.screen_scroll_offset += 20
            if current_time - self.state_time > 500:
                return True  # Done

        elif self.state == 'first_spark':
            if current_time - self.state_time > self.spark_time:
                self.state = 'get_next_spark'
                self.state_time = current_time

        elif self.state == 'get_next_spark':
            done = self.inc_spark()
            if done:
                self.draw_flag = True
                self.state = 'level_up_wait'
                self.state_time = current_time
            else:
                pos = self.get_position(self.current_spark)
                arrow_animation = CustomObjects.Animation(
                    self.uparrow, (pos[0] + 45, pos[1] - 11), (10, 1), animation_speed=32,
                    ignore_map=True, hold=True)
                self.arrow_animations.append(arrow_animation)
                spark_pos = pos[0] + 14, pos[1] + 26
                self.animations.append(self.make_spark(spark_pos))
                change = self.levelup_list[self.current_spark]
                if change >= 0:
                    increase = Utility.clamp(change, 1, 7)
                    row = Engine.subsurface(self.positive_numbers, (0, (increase - 1)*24, 10*28, 24))
                elif change < 0:
                    decrease = -Utility.clamp(change, -7, -1)
                    row = Engine.subsurface(self.negative_numbers, (0, (decrease - 1)*24, 10*28, 24))
                number_animation = CustomObjects.Animation(
                    row, (pos[0] + 43, pos[1] + 49), (10, 1), animation_speed=32, 
                    ignore_map=True, hold=True)
                number_animation.frameCount = -5  # delay this animation for 5 frames
                self.animations.append(number_animation)
                GC.SOUNDDICT['Stat Up'].play()
                self.underline_offset = 36 # for underline growing
                self.state = 'spark_wait'
                self.state_time = current_time

        elif self.state == 'spark_wait':
            if current_time - self.state_time > self.spark_time:
                self.state = 'get_next_spark'

        elif self.state == 'level_up_wait':
            if self.quote_dialog:  # Don't leave prematurely if there is a level up quote
                pass
            elif current_time - self.state_time > self.level_up_wait:
                self.begin_scroll_out()

    def draw(self, surf, gameStateObj):
        sprite = self.bg.copy()
        new_color = Image_Modification.color_transition2((88, 16, -40), (-80, -32, 40))

        # Render top
        long_name = ClassData.class_dict[self.unit.klass]['long_name']
        GC.FONT['text_white'].blit(long_name, sprite, (12, 3))
        GC.FONT['text_yellow'].blit(cf.WORDS['Lv'], sprite, (self.width//2 + 12, 3))
        if self.state in ('scroll_in', 'init_wait'):
            level = str(self.level1)
        else:
            level = str(self.level2)
        width = GC.FONT['text_blue'].size(level)[0]
        GC.FONT['text_blue'].blit(level, sprite, (self.width//2 + 50 - width, 3))

        # Render underlines
        new_underline_surf = Image_Modification.change_image_color(self.underline, new_color)
        for idx, num in enumerate(self.levelup_list[:self.current_spark + 1]):
            if num != 0:  # we increased this stat
                if idx == self.current_spark:
                    rect = (self.underline_offset, 0, 
                            new_underline_surf.get_width() - self.underline_offset, 3)
                    new_underline_surf = Engine.subsurface(new_underline_surf, rect)
                    self.underline_offset = max(0, self.underline_offset - 6)
                    pos = self.get_position(idx)
                    pos = (pos[0] + self.underline_offset//2 + 1, pos[1] + 10)
                else:
                    pos = self.get_position(idx)
                    pos = (pos[0] + 4, pos[1] + 11)
                sprite.blit(new_underline_surf, pos)

        # Update and draw arrow animations
        self.arrow_animations = [a for a in self.arrow_animations if not a.update(gameStateObj)]
        for animation in self.arrow_animations:
            animation.draw(sprite, gameStateObj, blend=new_color)

        # Draw stats
        for idx, stat in enumerate(GC.EQUATIONS.stat_list[:8]):
            pos = self.get_position(idx)
            GC.FONT['text_yellow'].blit(cf.WORDS[stat], sprite, pos)
            text = self.unit.stats[stat].base_stat - (self.levelup_list[idx] if self.current_spark < idx else 0)
            width = GC.FONT['text_blue'].size(str(text))[0]
            GC.FONT['text_blue'].blit(str(text), sprite, (pos[0] + 40 - width, pos[1]))

        pos = (6 - self.screen_scroll_offset, GC.WINHEIGHT - 8 - self.height)
        surf.blit(sprite, pos)

        # Blit unit's pic
        left = GC.WINWIDTH - self.unit.bigportrait.get_width() - 4
        top = GC.WINHEIGHT + self.unit_scroll_offset - self.unit.bigportrait.get_height()
        surf.blit(self.unit.bigportrait, (left, top))

        if self.quote_dialog and self.draw_flag and self.quote_dialog.transition_out != -1:
            self.quote_dialog.draw(surf, (160, 22))

        # Update and draw animations
        self.animations = [a for a in self.animations if not a.update(gameStateObj)]
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
            self.pos = GC.WINWIDTH//2 - self.width//2, GC.WINHEIGHT//2 - self.height//2
        else:
            self.pos = GC.WINWIDTH//2 - self.width//2, GC.WINHEIGHT - self.height

        self.sprite_offset = self.height//2
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

    def update(self, exp=None):
        if self.done:
            self.sprite_offset += 1
            if self.sprite_offset >= self.height//2:
                return True
        elif self.sprite_offset > 0:
            self.sprite_offset -= 1
        if exp is not None:  # Otherwise just keep it the same
            self.num = exp

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
