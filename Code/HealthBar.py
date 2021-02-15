from . import GlobalConstants as GC
from . import Utility, Engine
from . import Weapons

class HealthBar(object):
    def __init__(self, draw_method, unit, item, other=None, stats=None, swap_stats=None):
        self.last_update = 0
        self.time_for_change = 200
        self.transition_flag = False
        self.blind_speed = 1/8. # 8 frames to fully transition
        self.true_position = None

        self.reset()
        self.fade_in()
        self.change_unit(unit, item, other, stats, draw_method, swap_stats)

    def force_position_update(self, gameStateObj):
        if self.unit:
            width, height = self.bg_surf.get_width(), self.bg_surf.get_height()
            self.determine_position(gameStateObj, (width, height))

    def draw(self, surf, gameStateObj):
        from . import UnitObject
        if self.unit:
            width, height = self.bg_surf.get_width(), self.bg_surf.get_height()
            true_height = height + self.c_surf.get_height()
            if self.stats:
                bg_surf = Engine.create_surface((width, true_height))
            else:
                bg_surf = Engine.create_surface((width, height))
            bg_surf.blit(self.bg_surf, (0, 0))
            # Blit Name
            name_size = GC.FONT['text_numbers'].size(self.unit.name)
            position = width - name_size[0] - 4, 3
            GC.FONT['text_numbers'].blit(self.unit.name, bg_surf, position)
            # Blit item -- Must be blit every frame
            if self.item:
                if self.other:
                    if isinstance(self.other, UnitObject.UnitObject):
                        white = self.other.check_effective(self.item)
                    else:  # Tile Object
                        white = True if self.item.extra_tile_damage else False
                else:
                    white = False
                self.item.draw(bg_surf, (2, 3), white)

                # Blit advantage -- This must be blit every frame
                if isinstance(self.other, UnitObject.UnitObject) and self.unit.checkIfEnemy(self.other):
                    advantage, e_advantage = Weapons.TRIANGLE.compute_advantage(self.item, self.other.getMainWeapon())
                    if advantage > 0:
                        UpArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (self.unit.arrowAnim[self.unit.arrowCounter]*7, 0, 7, 10))
                        bg_surf.blit(UpArrow, (11, 7))
                    elif advantage < 0:
                        DownArrow = Engine.subsurface(GC.IMAGESDICT['ItemArrows'], (self.unit.arrowAnim[self.unit.arrowCounter]*7, 10, 7, 10))
                        bg_surf.blit(DownArrow, (11, 7))

            # Blit health bars -- Must be blit every frame
            if self.unit.stats['HP']:
                fraction_hp = min(float(self.true_hp)/self.unit.stats['HP'], 1)
            else:
                fraction_hp = 0
            index_pixel = int(50*fraction_hp)
            position = 25, 22
            bg_surf.blit(Engine.subsurface(GC.IMAGESDICT['HealthBar'], (0, 0, index_pixel, 2)), position)

            # Blit HP -- Must be blit every frame
            font = GC.FONT['number_small2']
            if self.transition_flag:
                font = GC.FONT['number_big2']
            position = 22 - font.size(str(int(self.true_hp)))[0], height - 17
            font.blit(str(int(self.true_hp)), bg_surf, position)

            # C surf
            if self.stats:
                if not self.stats_surf:
                    self.stats_surf = self.build_c_surf()
                bg_surf.blit(self.stats_surf, (0, height))

            if not self.true_position:
                self.determine_position(gameStateObj, (width, height))

            if self.stats:
                blit_surf = Engine.subsurface(bg_surf, (0, true_height//2 - int(true_height*self.blinds//2), width, int(true_height*self.blinds)))
                y_pos = self.true_position[1] + true_height//2 - int(true_height*self.blinds//2)
            else:
                blit_surf = Engine.subsurface(bg_surf, (0, height//2 - int(height*self.blinds//2), width, int(height*self.blinds)))
                y_pos = self.true_position[1] + height//2 - int(height*self.blinds//2)
            surf.blit(blit_surf, (self.true_position[0] + self.shake_offset[0], y_pos + self.shake_offset[1]))

            # blit Gem
            if self.blinds == 1 and self.gem and self.order:
                x, y = self.true_position[0] + self.shake_offset[0], self.true_position[1] + self.shake_offset[1]
                if self.order == 'left':
                    position = (x + 2, y - 3)
                elif self.order == 'right':
                    position = (x + 56, y - 3)
                elif self.order == 'middle':
                    position = (x + 27, y - 3)
                surf.blit(self.gem, position)

            # Blit skill icons
            for idx, skill_icon in enumerate(self.skill_icons):
                skill_icon.update()
                x, y = self.true_position[0] + width/2, self.true_position[1] - 16 - idx*16
                skill_icon.draw(surf, (x, y))
            self.skill_icons = [s for s in self.skill_icons if not s.done]

    def build_c_surf(self):
        c_surf = self.c_surf.copy()
        # Blit Hit
        if self.stats[0] is not None:
            hit = str(self.stats[0])
        else:
            hit = '--'
        position = c_surf.get_width()//2 - GC.FONT['number_small2'].size(hit)[0] - 1, -2
        GC.FONT['number_small2'].blit(hit, c_surf, position)
        # Blit Damage
        if self.stats[1] is not None:
            damage = str(self.stats[1])
        else:
            damage = '--'
        position = c_surf.get_width() - GC.FONT['number_small2'].size(damage)[0] - 2, -2
        GC.FONT['number_small2'].blit(damage, c_surf, position)
        return c_surf

    def determine_position(self, gameStateObj, pos):
        width, height = pos
        # Determine position
        self.true_position = self.topleft
        # logger.debug("Topleft %s", self.topleft)
        if self.topleft in ('p1', 'p2'):
            # Get the two positions, along with camera position
            pos1 = self.unit.position
            pos2 = self.other.position
            c_pos = gameStateObj.cameraOffset.get_xy()
            if self.topleft == 'p1':
                left = True if pos1[0] <= pos2[0] else False
            else:
                left = True if pos1[0] < pos2[0] else False
            self.order = 'left' if left else 'right'
            # logger.debug("%s %s %s", pos1, pos2, left)
            x_pos = GC.WINWIDTH//2 - width if left else GC.WINWIDTH//2
            rel_1 = pos1[1] - c_pos[1]
            rel_2 = pos2[1] - c_pos[1]
            # logger.debug("Health_Bar_Pos %s %s", rel_1, rel_2)
            # If both are on top of screen
            if rel_1 < 5 and rel_2 < 5:
                rel = max(rel_1, rel_2)
                y_pos = (rel+1)*GC.TILEHEIGHT + 12
            # If both are on bottom of screen
            elif rel_1 >= 5 and rel_2 >= 5:
                rel = min(rel_1, rel_2)
                y_pos = rel*GC.TILEHEIGHT - 12 - height - 13 # c_surf
            # Find largest gap and place it in the middle
            else:
                top_gap = min(rel_1, rel_2)
                bottom_gap = (GC.TILEY-1) - max(rel_1, rel_2)
                middle_gap = abs(rel_1 - rel_2)
                # logger.debug("Gaps %s %s %s", top_gap, bottom_gap, middle_gap)
                if top_gap > bottom_gap and top_gap > middle_gap:
                    y_pos = top_gap * GC.TILEHEIGHT - 12 - height - 13 # c_surf
                elif bottom_gap > top_gap and bottom_gap > middle_gap:
                    y_pos = (bottom_gap+1) * GC.TILEHEIGHT + 12
                else:
                    y_pos = GC.WINHEIGHT//4 - height//2 - 13//2 if rel_1 < 5 else 3*GC.WINHEIGHT//4 - height//2 - 13//2
                    x_pos = GC.WINWIDTH//4 - width//2 if pos1[0] - c_pos[0] > GC.TILEX//2 else 3*GC.WINWIDTH//4 - width//2
                    self.order = 'middle'
            self.true_position = (x_pos, y_pos)
            # logger.debug('True Position %s %s', x_pos, y_pos)
        elif self.topleft == 'splash': # self.topleft == 'auto':
            # Find x Position
            pos_x = self.unit.position[0] - gameStateObj.cameraOffset.get_x()
            pos_x = Utility.clamp(pos_x, 3, GC.TILEX - 2)
            # Find y position
            if self.unit.position[1] - gameStateObj.cameraOffset.get_y() < GC.TILEY//2: # IF unit is at top of screen
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() + 2
            else:
                pos_y = self.unit.position[1] - gameStateObj.cameraOffset.get_y() - 3
            self.true_position = pos_x*GC.TILEWIDTH - width//2, pos_y*GC.TILEHEIGHT - 8
            self.order = 'middle'
            # logger.debug('Other True Position %s %s', pos_x, pos_y)

    def fade_in(self):
        self.blinds = 0

    def fade_out(self):
        pass

    def shake(self, num):
        self.current_shake = 1
        if num == 1: # Normal hit
            self.shake_set = [(-3, -3), (0, 0), (3, 3), (0, 0)]
        elif num == 2: # Kill
            self.shake_set = [(3, 3), (0, 0), (0, 0), (3, 3), (-3, -3), (3, 3), (-3, -3), (0, 0)]
        elif num == 3:
            self.shake_set = [(3, 3), (0, 0), (0, 0), (-3, -3), (0, 0), (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), (3, 3), (0, 0), (-3, -3), (3, 3), (0, 0)]

    def add_skill_icon(self, skill_icon):
        self.skill_icons.append(skill_icon)

    def update(self, status_obj=False):
        # Make blinds wider
        self.blinds = Utility.clamp(self.blinds, self.blinds + self.blind_speed, 1)
        # Handle HP bar
        if self.unit and self.blinds == 1:
            # Handle shake
            if self.current_shake:
                self.shake_offset = self.shake_set[self.current_shake - 1]
                self.current_shake += 1
                if self.current_shake > len(self.shake_set):
                    self.current_shake = 0
            if self.true_hp != self.unit.currenthp and not self.transition_flag:
                self.transition_flag = True
                if status_obj:
                    self.time_for_change = max(400, abs(self.true_hp - self.unit.currenthp)*4*GC.FRAMERATE)
                    self.last_update = Engine.get_time() + 200
                else: # Combat
                    self.time_for_change = max(200, abs(self.true_hp - self.unit.currenthp)*2*GC.FRAMERATE)
                    self.last_update = Engine.get_time()
            if self.transition_flag and Engine.get_time() > self.last_update:
                self.true_hp = Utility.easing(Engine.get_time() - self.last_update, self.oldhp, self.unit.currenthp - self.oldhp, self.time_for_change)
                # print(self.true_hp, Engine.get_time(), self.oldhp, self.unit.currenthp, self.time_for_change)
                if self.unit.currenthp - self.oldhp > 0 and self.true_hp > self.unit.currenthp:
                    self.true_hp = self.unit.currenthp
                    self.oldhp = self.true_hp
                    self.transition_flag = False
                elif self.unit.currenthp - self.oldhp < 0 and self.true_hp < self.unit.currenthp:
                    self.true_hp = self.unit.currenthp
                    self.oldhp = self.true_hp
                    self.transition_flag = False

    def change_unit(self, unit, item, other=None, stats=None, draw_method=None, force_stats=None):
        self.stats_surf = None
        if draw_method:
            self.topleft = draw_method
            self.true_position = None # Reset true position
        if unit: 
            if unit != self.unit or other != self.other: # Only if truly new...
                self.fade_in()
            self.oldhp = unit.currenthp
            self.true_hp = unit.currenthp
            self.last_update = Engine.get_time()

            self.unit = unit
            self.item = item
            if other:
                self.other = other
            if stats:
                self.stats = stats

            from . import UnitObject
            team = 'enemy' if not isinstance(unit, UnitObject.UnitObject) else unit.team
            color = Utility.get_color(team)
            self.bg_surf = GC.IMAGESDICT[color + 'Health']
            self.c_surf = GC.IMAGESDICT[color + 'CombatStats']
            self.gem = GC.IMAGESDICT[color + 'CombatGem'] 

            # Swaps combat stat color
            if force_stats:
                self.c_surf = GC.IMAGESDICT[color + 'CombatStats']
        else:
            self.reset()

    def update_stats(self, stats):
        self.stats_surf = None
        self.stats = stats
        
    def reset(self):
        self.unit = None
        self.item = None
        self.other = None
        self.true_hp = 0
        self.bg_surf = None
        self.c_surf = None
        self.gem = None
        self.stats = None
        # for shake
        self.shake_set = [(0, 0)]
        self.shake_offset = (0, 0)
        self.current_shake = 0
        # for skill icons
        self.skill_icons = []
