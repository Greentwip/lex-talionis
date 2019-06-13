import re, datetime

try:
    import GlobalConstants as GC
    import configuration as cf
    import MenuFunctions, Background, StateMachine, Image_Modification, Engine
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import MenuFunctions, Background, StateMachine, Image_Modification, Engine

class Objective(object):
    def __init__(self, display_name, win_condition, loss_condition):
        self.display_name_string = display_name
        self.win_condition_string = win_condition
        self.loss_condition_string = loss_condition
        self.connectives = ['OR', 'AND']

        self.removeSprites()

    def removeSprites(self):
        # For drawing
        self.BGSurf = None
        self.surf_width = 0
        self.num_lines = 0

    def serialize(self):
        return (self.display_name_string, self.win_condition_string, self.loss_condition_string)

    @classmethod
    def deserialize(cls, info):
        return cls(*info)

    def eval_string(self, text, gameStateObj):
        # Parse evals
        to_evaluate = re.findall(r'\{[^}]*\}', text)
        evaluated = []
        for evaluate in to_evaluate:
            evaluated.append(str(eval(evaluate[1:-1])))
        for index in range(len(to_evaluate)):
            text = text.replace(to_evaluate[index], evaluated[index])
        return text

    def split_string(self, text):
        return text.split(',')

    def get_size(self, text_lines):
        longest_surf_width = 0
        for line in text_lines:
            guess = GC.FONT['text_white'].size(line)[0]
            if guess > longest_surf_width:
                longest_surf_width = guess
        return longest_surf_width

    # Mini-Objective that shows up in free state
    def draw(self, gameStateObj):
        text_lines = self.split_string(self.eval_string(self.display_name_string, gameStateObj))

        longest_surf_width = self.get_size(text_lines)

        if longest_surf_width != self.surf_width or len(text_lines) != self.num_lines:
            self.num_lines = len(text_lines)
            self.surf_width = longest_surf_width
            surf_height = 16 * self.num_lines + 8

            # Blit background
            BGSurf = MenuFunctions.CreateBaseMenuSurf((self.surf_width + 16, surf_height), 'BaseMenuBackgroundOpaque')
            if self.num_lines == 1:
                BGSurf.blit(GC.IMAGESDICT['Shimmer1'], (BGSurf.get_width() - 1 - GC.IMAGESDICT['Shimmer1'].get_width(), 4))
            elif self.num_lines == 2:
                BGSurf.blit(GC.IMAGESDICT['Shimmer2'], (BGSurf.get_width() - 1 - GC.IMAGESDICT['Shimmer2'].get_width(), 4))
            self.BGSurf = Engine.create_surface((BGSurf.get_width(), BGSurf.get_height() + 3), transparent=True, convert=True)
            self.BGSurf.blit(BGSurf, (0, 3))
            gem = GC.IMAGESDICT['BlueCombatGem']
            self.BGSurf.blit(gem, (BGSurf.get_width()//2 - gem.get_width()//2, 0))
            # Now make translucent
            self.BGSurf = Image_Modification.flickerImageTranslucent(self.BGSurf, 20)

        temp_surf = self.BGSurf.copy()
        for index, line in enumerate(text_lines):
            position = temp_surf.get_width()//2 - GC.FONT['text_white'].size(line)[0]//2, 16 * index + 6
            GC.FONT['text_white'].blit(line, temp_surf, position)

        return temp_surf

    def get_win_conditions(self, gameStateObj):
        text_list = self.split_string(self.eval_string(self.win_condition_string, gameStateObj))
        win_cons = [text for text in text_list if text not in self.connectives]
        connectives = [text for text in text_list if text in self.connectives]
        return win_cons, connectives

    def get_loss_conditions(self, gameStateObj):
        text_list = self.split_string(self.eval_string(self.loss_condition_string, gameStateObj))
        loss_cons = [text for text in text_list if text not in self.connectives]
        connectives = [text for text in text_list if text in self.connectives]
        return loss_cons, connectives

class StatusMenu(StateMachine.State):
    def begin(self, gameStateObj, metaDataObj):
        if not self.started:
            self.background = Background.MovingBackground(GC.IMAGESDICT['RuneBackground'])
            self.surfaces = self.get_surfaces(gameStateObj, metaDataObj)
            # backSurf
            self.backSurf = gameStateObj.generic_surf

            # Transition in:
            gameStateObj.stateMachine.changeState("transition_in")
            return 'repeat'
        
    def get_surfaces(self, gameStateObj, metaDataObj):
        surfaces = []
        # Background
        # name_back_surf = GC.IMAGESDICT['ObjectiveTitle']
        name_back_surf = GC.IMAGESDICT['ChapterSelect' + gameStateObj.mode.get('color', 'Green')]
        surfaces.append((name_back_surf, (24, 2)))
        # Text
        big_font = GC.FONT['chapter_green']
        name_size = (big_font.size(metaDataObj['name'])[0] + 1, big_font.height)
        name_surf = Engine.create_surface(name_size, transparent=True, convert=True)
        big_font.blit(metaDataObj['name'], name_surf, (0, 0))
        pos = (24 + name_back_surf.get_width()//2 - name_surf.get_width()//2, 3 + name_back_surf.get_height()//2 - name_surf.get_height()//2)
        surfaces.append((name_surf, pos))                    
        # Background
        back_surf = MenuFunctions.CreateBaseMenuSurf((GC.WINWIDTH - 8, 24), 'WhiteMenuBackgroundOpaque')
        surfaces.append((back_surf, (4, 34)))
        # Get Words
        golden_words_surf = GC.IMAGESDICT['GoldenWords']
        # Get Turn
        turn_surf = Engine.subsurface(golden_words_surf, (0, 17, 26, 10))
        surfaces.append((turn_surf, (10, 42)))
        # Get Funds
        funds_surf = Engine.subsurface(golden_words_surf, (0, 33, 32, 10))
        surfaces.append((funds_surf, (GC.WINWIDTH//3 - 8, 42)))
        # Get PlayTime
        playtime_surf = Engine.subsurface(golden_words_surf, (32, 15, 17, 13))
        surfaces.append((playtime_surf, (2*GC.WINWIDTH//3 + 6, 39)))
        # Get G
        g_surf = Engine.subsurface(golden_words_surf, (40, 47, 9, 12))
        surfaces.append((g_surf, (2*GC.WINWIDTH//3 - 8 - 1, 40)))
        # TurnCountSurf
        turn_count_size = (GC.FONT['text_blue'].size(str(gameStateObj.turncount))[0] + 1, GC.FONT['text_blue'].height)
        turn_count_surf = Engine.create_surface(turn_count_size, transparent=True, convert=True)
        GC.FONT['text_blue'].blit(str(gameStateObj.turncount), turn_count_surf, (0, 0))
        surfaces.append((turn_count_surf, (GC.WINWIDTH//3 - 16 - turn_count_surf.get_width(), 38)))                    
        # MoneySurf
        money = str(gameStateObj.get_money())
        money_size = (GC.FONT['text_blue'].size(money)[0] + 1, GC.FONT['text_blue'].height)
        money_surf = Engine.create_surface(money_size, transparent=True, convert=True)
        GC.FONT['text_blue'].blit(money, money_surf, (0, 0))
        surfaces.append((money_surf, (2*GC.WINWIDTH//3 - 8 - 4 - money_surf.get_width(), 38)))

        # Get win and loss conditions
        win_cons, win_connectives = gameStateObj.objective.get_win_conditions(gameStateObj)
        loss_cons, loss_connectives = gameStateObj.objective.get_loss_conditions(gameStateObj)

        hold_surf = MenuFunctions.CreateBaseMenuSurf((GC.WINWIDTH - 16, 8 + 16 + 16 + 16*len(win_cons) + 16 * len(loss_cons)))
        hold_surf.blit(GC.IMAGESDICT['Lowlight'], (2, 12))

        GC.FONT['text_yellow'].blit(cf.WORDS['Win Conditions'], hold_surf, (4, 4))

        for index, win_con in enumerate(win_cons):
            GC.FONT['text_white'].blit(win_con, hold_surf, (8, 20 + 16*index))

        hold_surf.blit(GC.IMAGESDICT['Lowlight'], (2, 28 + 16*len(win_cons)))

        GC.FONT['text_yellow'].blit(cf.WORDS['Loss Conditions'], hold_surf, (4, 20 + 16*len(win_cons)))

        for index, loss_con in enumerate(loss_cons):
            GC.FONT['text_white'].blit(loss_con, hold_surf, (8, 36 + 16*len(win_cons) + index*16))

        surfaces.append((hold_surf, (8, 34 + back_surf.get_height() + 2)))

        seed = str(gameStateObj.game_constants['_random_seed'])
        seed_size = GC.FONT['text_numbers'].size(seed)[0]
        seed_surf = Engine.create_surface((28, 16), transparent=True, convert=True)
        GC.FONT['text_numbers'].blit(seed, seed_surf, (14 - seed_size/2, 0))
        surfaces.append((seed_surf, (GC.WINWIDTH - 28, 0)))
            
        return surfaces

    def take_input(self, eventList, gameStateObj, metaDataObj):
        event = gameStateObj.input_manager.process_input(eventList)
        if event == 'BACK':
            GC.SOUNDDICT['Select 4'].play()
            gameStateObj.stateMachine.changeState('transition_pop')

    def update(self, gameStateObj, metaDataObj):
        pass

    def draw(self, gameStateObj, metaDataObj):
        self.background.draw(self.backSurf)

        # Non moving surfaces
        for (surface, rect) in self.surfaces:
            self.backSurf.blit(surface, rect)

        # Playtime
        time = datetime.timedelta(milliseconds=gameStateObj.playtime)
        seconds = int(time.total_seconds())
        hours = min(seconds//3600, 99)
        minutes = str((seconds%3600)//60)
        if len(minutes) < 2:
            minutes = '0' + minutes
        seconds = str(seconds%60)
        if len(seconds) < 2:
            seconds = '0' + seconds

        formatted_time = ':'.join([str(hours), str(minutes), str(seconds)])
        formatted_time_size = (GC.FONT['text_blue'].size(formatted_time)[0], GC.FONT['text_blue'].height)
        # Truncate seconds section. I don't care, and could add those later if I wished
        GC.FONT['text_blue'].blit(formatted_time, self.backSurf, (GC.WINWIDTH - 8 - formatted_time_size[0], 38))

        return self.backSurf
