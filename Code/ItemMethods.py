from . import GlobalConstants as GC
from . import configuration as cf
from . import Image_Modification, Utility, Weapons, Engine, TextChunk
from . import BaseMenuSurf, HelpMenu

# === GENERIC ITEM OBJECT ========================================
class ItemObject(object):
    next_uid = 100

    def __init__(self, i_id, name, spritetype, spriteid, components, value, RNG,
                 desc, aoe, weapontype, status, status_on_hold, status_on_equip,
                 droppable=False, event_combat=False):        
        self.uid = ItemObject.next_uid
        ItemObject.next_uid += 1
        self.id = i_id
        self.item_owner = 0
        self.name = str(name)
        self.spritetype = spritetype # Consumable, Sword, Used for spriting in list of sprites
        self.spriteid = spriteid # Number of sprite to be picked from spritesheet list
        self.value = int(value) # Value for one use of item, or for an infinite item
        self.RNG = RNG.split('-') # Comes in the form of looking like '1-2' or '1' or '2-3' or '3-10'
        self.event_combat = event_combat
        self.droppable = droppable # Whether this item is given to its owner's killer upon death
        self.desc = desc # Text description of item
        # Status IDs
        self.status = status
        self.status_on_hold = status_on_hold
        self.status_on_equip = status_on_equip
        
        self.aoe = aoe
        self.TYPE = weapontype
        if self.TYPE:
            self.icon = Weapons.Icon(self.TYPE)
        else:
            self.icon = None
        
        # Creates component slots
        self.components = components # Consumable, Weapon, Spell Bigger Picture
        for component_key, component_value in self.components.items():
            self.__dict__[component_key] = component_value

        if self.droppable == self.locked == True:
            print("%s can't be both droppable and locked to a unit!" % self.name)
            self.droppable = False

        self.loadSprites()

    def get_range(self, unit):
        return get_item_range(self, unit)

    def get_true_range_string(self, unit):
        item_rng = get_item_range(self, unit)
        if min(item_rng) == max(item_rng):
            return str(item_rng[0])
        else:
            return str(item_rng[0]) + '-' + str(item_rng[-1])

    def get_range_string(self):
        # If is actually a burst from current position, display that in item.
        if self.RNG[-1] == '0' and self.aoe and self.aoe.mode in ('Blast', 'EnemyBlast'):
            return self.aoe.number.replace('MAG', 'MP')
        return '-'.join(self.RNG).replace('MAG', 'MP')

    def is_ranged(self):
        # Whether maximum range is not 0 or 1
        return not (self.RNG[-1] == '0' or self.RNG[-1] == '1')

    def is_magic(self):
        return self.magic or self.magic_at_range or self.TYPE in Weapons.TRIANGLE.magic_types

    def serialize(self):
        serial_dict = {}
        serial_dict['uid'] = self.uid
        serial_dict['id'] = self.id
        serial_dict['owner'] = self.item_owner
        serial_dict['droppable'] = self.droppable
        serial_dict['event_combat'] = self.event_combat
        serial_dict['uses'] = self.uses.uses if self.uses is not None else None
        serial_dict['c_uses'] = self.c_uses.uses if self.c_uses is not None else None
        
        serial_dict['cd_data'] = self.cooldown.serialize() if self.cooldown is not None else None
        
        return serial_dict

    # If the attribute is not found
    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            return super(ItemObject, self).__getattr__(attr)
        return None

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)

    def __getitem__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, item):
        self.__dict__[key] = item
    
    def draw(self, surf, topleft, white=False, cooldown=False):
        ItemSurf = self.image
        if white:
            ItemSurf = Image_Modification.flickerImageWhite(ItemSurf.convert_alpha(), abs(255 - Engine.get_time()%510))
            # ItemSurf = Image_Modification.transition_image_white(ItemSurf)
        surf.blit(ItemSurf, topleft)
        if self.locked:
            locked_icon = GC.IMAGESDICT['LockedIcon']
            surf.blit(locked_icon, topleft)

    def removeSprites(self):
        self.image = None
        self.help_box = None
        
    def loadSprites(self):
        # Support for skill icons as item icons
        split_id = self.spriteid.split(',')
        if len(split_id) > 1:
            sprite_id = (int(split_id[0]), int(split_id[1]))
        else:
            sprite_id = (0, int(self.spriteid))
        # actually build
        try:
            self.image = Engine.subsurface(GC.ITEMDICT[self.spritetype], (16*sprite_id[0], 16*sprite_id[1], 16, 16))
        except ValueError:
            print("Item %s is trying to read from position %s on %s sprite which does not exist." % (self.id, sprite_id[1], self.spritetype))
            try:
                self.image = Engine.subsurface(GC.ITEMDICT[self.spritetype], (0, 0, 16, 16))
            except ValueError:
                raise ValueError("Item %s is trying to read from %s sprite which does not exist." % (self.id, self.spritetype))
        self.help_box = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def get_help_box(self):
        if not self.help_box:
            self.help_box = self.create_help_box()
        return self.help_box

    def create_help_box(self):
        if self.weapon or self.spell:
            return Help_Dialog(self)
        else:
            return HelpMenu.Help_Dialog(self.desc)

    def drawType(self, surf, left, top):
        if self.icon:  
            self.icon.draw(surf, (left, top))

def get_item_range(item, unit):
    if len(item.RNG) == 1:
        r = item.RNG[0]
        if r == 'MAG/2':
            r1 = max(1, GC.EQUATIONS.get_magic_damage(unit, item)//2)
        else:
            r1 = int(r)
        if item.longshot:
            return [r1, r1 + item.longshot]
        else:
            return [r1]
    elif len(item.RNG) == 2:
        r1 = item.RNG[0]
        r2 = item.RNG[1]
        if r1 == 'MAG/2':
            r1 = GC.EQUATIONS.get_magic_damage(unit, item)//2
        else:
            r1 = int(r1)
        if r2 == 'MAG/2':
            r2 = GC.EQUATIONS.get_magic_damage(unit, item)//2
        else:
            r2 = int(r2)
        r2 += item.longshot if item.longshot else 0
        return list(range(r1, max(r2, 1) + 1))
    else:
        print('%s has an unsupported range: %s' % (item, item.get_range_string()))
        return []

class Help_Dialog(HelpMenu.Help_Dialog_Base):
    def __init__(self, item):
        self.last_time = self.start_time = 0
        self.transition_in = self.transition_out = False
        self.item = item
        font1 = GC.FONT['text_blue']
        font2 = GC.FONT['text_yellow']

        if self.item.weapon:
            weaponLVL = self.item.weapon.strLVL
            self.first_line_text = [' ', weaponLVL, ' Mt ', str(self.item.weapon.MT), ' Hit ', str(self.item.weapon.HIT)]
            if cf.CONSTANTS['crit']:
                self.first_line_text += [' Crit ', str(self.item.crit) if self.item.crit is not None else '--']
            if self.item.weight:
                self.first_line_text += [' Wt ', str(self.item.weight)]
            self.first_line_text += [' Rng ', self.item.get_range_string()]
            self.first_line_font = [font1, font1, font2, font1, font2, font1]
            if cf.CONSTANTS['crit']:
                self.first_line_font += [font2, font1]
            if self.item.weight:
                self.first_line_font += [font2, font1]
            self.first_line_font += [font2, font1]

        elif self.item.spell:
            spellLVL = self.item.spell.strLVL
            self.first_line_text = [' ', spellLVL]
            self.first_line_font = [font1, font1]
            if self.item.damage is not None:
                self.first_line_text += [' Mt ', str(self.item.damage)]
                self.first_line_font += [font2, font1]
            if self.item.hit is not None:
                self.first_line_text += [' Hit ', str(self.item.hit)]
                self.first_line_font += [font2, font1]
            if cf.CONSTANTS['crit'] and self.item.crit is not None:
                self.first_line_text += [' Crit ', str(self.item.crit)]
                self.first_line_font += [font2, font1]
            self.first_line_text += [' Rng ', self.item.get_range_string()]
            self.first_line_font += [font2, font1]

        first_line_length = max(font1.size(''.join(self.first_line_text))[0] + (16 if self.item.icon else 0) + 4, 112) # 112 was 96
        if self.item.desc:
            self.output_desc_lines = TextChunk.line_wrap(TextChunk.line_chunk(self.item.desc), first_line_length, GC.FONT['convo_black']) 
            self.output_desc_lines = [''.join(line) for line in self.output_desc_lines]
        else:
            self.output_desc_lines = []
        size_x = first_line_length + 24
        size_y = 32 + len(self.output_desc_lines)*16
        self.help_surf = BaseMenuSurf.CreateBaseMenuSurf((size_x, size_y), 'MessageWindowBackground')  
        self.h_surf = Engine.create_surface((size_x, size_y + 3), transparent=True)

    def draw(self, surf, pos):
        time = Engine.get_time()
        if time > self.last_time + 1000:  # If it's been at least a second since last update
            self.start_time = time - 16
        self.last_time = time

        help_surf = Engine.copy_surface(self.help_surf)
        self.item.drawType(help_surf, 8, 8)
        
        # Actually blit first line
        word_index = 24 if self.item.icon else 8
        for index, word in enumerate(self.first_line_text):
            self.first_line_font[index].blit(word, help_surf, (word_index, 8))
            word_index += self.first_line_font[index].size(word)[0]
        
        if cf.OPTIONS['Text Speed'] > 0:
            num_characters = int(2*(time - self.start_time)/float(cf.OPTIONS['Text Speed']))
        else:
            num_characters = 1000
        for index, line in enumerate(self.output_desc_lines):
            if num_characters > 0:
                GC.FONT['convo_black'].blit(line[:num_characters], help_surf, (8, GC.FONT['convo_black'].height*index + 8 + 16))  
                num_characters -= len(line)

        self.final_draw(surf, pos, time, help_surf)

# A subclass of int so that if the int is negative, it will instead output "--"
class NonNegative(int):
    def __new__(cls, num):
        return int.__new__(cls, num)

    def __repr__(self):
        if self.num < 0:
            return "--"
        else:
            return str(self.num)

class UsesComponent(object):
    def __init__(self, uses):
        self.uses = int(uses)
        self.total_uses = self.uses

    def __repr__(self):
        return str(self.uses)

    def decrement(self):
        self.uses -= 1

    def reset(self):
        self.uses = self.total_uses

    def increment(self):
        self.uses += 1
        self.uses = min(self.uses, self.total_uses)

    def set(self, uses):
        self.uses = uses

    def can_repair(self):
        return self.uses < self.total_uses

class CooldownComponent(object):
    def __init__(self, turns, cd_speed=1, persist='No', cd_uses=1):
        self.cd_turns = int(turns)
        self.total_cd_turns = self.cd_turns
        self.old_total_cd_turns = self.total_cd_turns

        self.charged = True
        self.cd_speed = cd_speed
        self.persist = persist.lower() in ('yes', 'y', 'true')

        self.cd_uses = int(max(1, cd_uses))
        self.total_cd_uses = self.cd_uses

    def __repr__(self):
        return str(self.turns)

    def discharge(self, prior_turns):
        """
        Reverses getting a charge each turn
        """
        self.cd_turns -= self.cd_speed
        if self.cd_turns < prior_turns:
            self.charged = False
            self.cd_uses = 0
            self.total_cd_turns = prior_turns

    def recharge(self):
        """
        Get a charge each turn
        """
        self.cd_turns += self.cd_speed
        if self.cd_turns >= self.total_cd_turns:
            self.charged = True
            self.cd_uses = self.total_cd_uses
            self.total_cd_turns = self.old_total_cd_turns

    def decrement(self, item, gameStateObj):
        """
        Remove a use from the item
        """
        self.cd_uses -= 1
        if self.cd_uses == 0:
            owner = (gameStateObj.get_unit_from_id(item.item_owner))
            cut_amount = 1
            for status in owner.status_effects:
                if status.cd_percent:
                    cut_amount -= float(int(status.cd_percent) / 100)
                    cut_amount = max(.01, cut_amount)
            # Enter charging mode
            self.total_cd_turns = max(int(self.old_total_cd_turns * cut_amount), 1)
            self.charged = False
            self.cd_turns = 0

    def increment(self, prior_cd):
        """
        Reverse removing a use from the item
        """ 
        self.cd_uses += 1
        if self.cd_uses > 0:
            self.charged = True
            self.cd_turns = prior_cd
            self.total_cd_turns = self.old_total_cd_turns

    def reset(self):
        self.charged = True
        self.total_cd_turns = self.old_total_cd_turns
        self.cd_turns = self.total_cd_turns
        self.cd_uses = self.total_cd_uses

    def can_repair(self):
        return False

    def add(self, val):
        self.cd_speed += val

    def remove(self, val):
        self.cd_speed -= val

    def serialize(self):
        serial_dict = {}
        serial_dict['cd_turns'] = self.cd_turns
        serial_dict['cd_uses'] = self.cd_uses
        serial_dict['charged'] = self.charged
        serial_dict['total_cd_turns'] = self.total_cd_turns
        return serial_dict

    def deserialize(self, ser_dict):
        self.cd_turns = ser_dict['cd_turns']
        self.cd_uses = ser_dict['cd_uses']
        self.charged = ser_dict['charged']
        self.total_cd_turns = ser_dict['total_cd_turns']

class WeaponComponent(object):
    def __init__(self, stats):
        MT, HIT, LVL = stats
        self.MT = int(MT)
        self.HIT = int(HIT)
        self.LVL = LVL
        if self.LVL in ('A', 'B', 'C', 'D', 'E', 'S', 'SS'):
            self.strLVL = self.LVL
        elif self.LVL:
            self.strLVL = 'Prf'
        else:
            self.strLVL = '--'

class ExtraSelectComponent(object):
    def __init__(self, RNG, targets):
        self.RNG = RNG.split('-')
        self.targets = targets

    def get_range_string(self):
        return '-'.join(self.RNG)

    def get_range(self, unit):
        return get_item_range(self, unit)

class AOEComponent(object):
    def __init__(self, mode, number=0):
        self.mode = mode
        self.number = number

    def get_number(self, item, gameStateObj):
        if self.number == 'MAG/2':
            num = GC.EQUATIONS.get_magic_damage(gameStateObj.get_unit_from_id(item.item_owner), item)//2
        else:
            num = int(self.number)
        return num

    def get_positions(self, unit_position, cursor_position, gameStateObj, item):
        tileMap = gameStateObj.map
        if self.mode == 'Normal':
            return cursor_position, []
        elif self.mode == 'Cleave_Old':
            other_position = []
            if cursor_position[1] < unit_position[1]:
                other_position.append((cursor_position[0] - 1, cursor_position[1]))
                other_position.append((cursor_position[0] + 1, cursor_position[1]))
            if cursor_position[0] < unit_position[0]:
                other_position.append((cursor_position[0], cursor_position[1] - 1))
                other_position.append((cursor_position[0], cursor_position[1] + 1))
            if cursor_position[0] > unit_position[0]:
                other_position.append((cursor_position[0], cursor_position[1] - 1))
                other_position.append((cursor_position[0], cursor_position[1] + 1))
            if cursor_position[1] > unit_position[1]:
                other_position.append((cursor_position[0] - 1, cursor_position[1]))
                other_position.append((cursor_position[0] + 1, cursor_position[1]))
            splash_positions = [position for position in other_position if tileMap.check_bounds(position)]
            return cursor_position, splash_positions
        elif self.mode == 'Cleave':
            p = unit_position
            other_position = [(p[0] - 1, p[1] - 1), (p[0], p[1] - 1), (p[0] + 1, p[1] - 1),
                              (p[0] - 1, p[1]), (p[0] + 1, p[1]),
                              (p[0] - 1, p[1] + 1), (p[0], p[1] + 1), (p[0] + 1, p[1] + 1)]
            item_owner = gameStateObj.get_unit_from_id(item.item_owner)
            splash_positions = {pos for pos in other_position if tileMap.check_bounds(pos) and 
                                not gameStateObj.compare_teams(item_owner.team, gameStateObj.grid_manager.get_team_node(pos))}
            return cursor_position, list(splash_positions - {cursor_position})
        elif self.mode == 'Blast' or self.mode == 'EnemyBlast':
            num = self.get_number(item, gameStateObj)
            splash_positions = Utility.find_manhattan_spheres(range(num + 1), cursor_position)
            if self.mode == 'Blast':
                splash_positions = {position for position in splash_positions if tileMap.check_bounds(position)}
            elif self.mode == 'EnemyBlast':
                item_owner = gameStateObj.get_unit_from_id(item.item_owner)
                splash_positions = {pos for pos in splash_positions if tileMap.check_bounds(pos) and 
                                    not gameStateObj.compare_teams(item_owner.team, gameStateObj.grid_manager.get_team_node(pos))}
            if item.weapon:
                return cursor_position, list(splash_positions - {cursor_position})
            else:
                return None, list(splash_positions)
        elif self.mode == 'Line':
            splash_positions = Utility.raytrace(unit_position, cursor_position)
            splash_positions = [position for position in splash_positions if position != unit_position]
            return None, splash_positions
        elif self.mode == 'AllAllies':
            item_owner = gameStateObj.get_unit_from_id(item.item_owner)
            splash_positions = [unit.position for unit in gameStateObj.allunits if unit.position and item_owner.checkIfAlly(unit)]
            return None, splash_positions
        elif self.mode == 'AllEnemies':
            item_owner = gameStateObj.get_unit_from_id(item.item_owner)
            splash_positions = [unit.position for unit in gameStateObj.allunits if unit.position and item_owner.checkIfEnemy(unit)]
            return None, splash_positions
        elif self.mode == 'AllUnits':
            splash_positions = [unit.position for unit in gameStateObj.allunits if unit.position]
            return None, splash_positions
        elif self.mode == 'AllTiles':
            splash_positions = tileMap.tiles.keys()
            return None, splash_positions
        else:
            print('Error! ' + self.mode + ' AOE mode is not supported yet!')
            return cursor_position, []

class UsableComponent(object):
    def __init__(self):
        self.name = 'usable'

class EffectiveComponent(object):
    def __init__(self, effective_against, bonus):
        # List of types its effective against
        self.against = effective_against
        self.bonus = bonus

    def add(self, val):
        self.against.append(val)

    def remove(self, val):
        if val in self.against:
            self.against.remove(val)

class SpellComponent(object):
    def __init__(self, LVL, targets):
        self.name = 'spell'
        self.LVL = LVL
        self.targets = targets # Ally, Enemy, Tile... maybe more?
        if self.LVL in ('A', 'B', 'C', 'D', 'E', 'S', 'SS'):
            self.strLVL = self.LVL
        elif self.LVL:
            self.strLVL = 'Prf'
        else:
            self.strLVL = '--'

class MovementComponent(object):
    def __init__(self, mode, magnitude):
        self.name = 'movement'
        self.mode = mode
        self.magnitude = magnitude

class SummonComponent(object):
    def __init__(self, klass, items, name, desc):
        self.klass = klass
        self.item_line = items
        self.name = name
        self.desc = desc

# === ITEM PARSER ======================================================
# Takes an item id, as well as the database of item data, and outputs an item
def itemparser(itemid, gameStateObj=None):
    droppable = False
    event_combat = False
    if itemid.startswith('d'):
        itemid = itemid[1:] # Strip the first d off
        droppable = True
    elif itemid.startswith('e'):
        itemid = itemid[1:]
        event_combat = True
    try:
        item = GC.ITEMDATA[itemid]
    except KeyError as e:
        print("Key Error %s. %s cannot be found in items.xml"%(e, itemid))
        return None

    components = item['components']
    if components:
        components = components.split(',')
    else:
        components = []

    aoe = AOEComponent('Normal', 0)
    if 'weapon' in components or 'spell' in components:
        weapontype = item['weapontype']
        if weapontype == 'None':
            weapontype = None
    else:
        weapontype = None

    status = []
    status_on_hold = []
    status_on_equip = []

    my_components = {}
    for component in components:
        if component == 'uses':
            try:
                my_components['uses'] = UsesComponent(int(item['uses']))
            except KeyError as e:
                raise KeyError("You are missing uses component line for %s item" % itemid)
        elif component == 'c_uses':
            my_components['c_uses'] = UsesComponent(int(item['c_uses']))
        elif component == 'cooldown':
            cd_speed = int(item.get('cd_speed', 1))
            persist = item.get('cd_persist', 'No')
            my_components['cooldown'] = CooldownComponent(int(item['cooldown']), cd_speed,
                                                          persist, int(item['cd_uses']))
        elif component == 'weapon':
            stats = [item['MT'], item['HIT'], item['LVL']]
            my_components['weapon'] = WeaponComponent(stats)
        elif component == 'usable':
            my_components['usable'] = UsableComponent()
        elif component == 'spell':
            my_components['spell'] = SpellComponent(item['LVL'], item['targets'])
        elif component == 'extra_select':
            my_components['extra_select'] = [ExtraSelectComponent(*c.split(',')) for c in item['extra_select'].split(';')]
            my_components['extra_select_index'] = 0
            my_components['extra_select_targets'] = []
        elif component == 'status':
            statusid = item['status'].split(',')
            for s_id in statusid:
                status.append(s_id)
        elif component == 'status_on_hold':
            statusid = item['status_on_hold'].split(',')
            for s_id in statusid:
                status_on_hold.append(s_id)
        elif component == 'status_on_equip':
            statusid = item['status_on_equip'].split(',')
            for s_id in statusid:
                status_on_equip.append(s_id)
        elif component == 'effective':
            try:
                effective_against, bonus = item['effective'].split(';')
                effective_against = effective_against.split(',')
                my_components['effective'] = EffectiveComponent(effective_against, int(bonus))
            except:
                continue
        elif component == 'permanent_stat_increase':
            stat_increase = Utility.intify_comma_list(item['stat_increase'])
            my_components['permanent_stat_increase'] = stat_increase
        elif component == 'permanent_growth_increase':
            stat_increase = Utility.intify_comma_list(item['growth_increase'])
            my_components['permanent_growth_increase'] = stat_increase
        elif component in ('promotion', 'tag_locked', 'class_locked'):
            legal = item[component].split(',')
            my_components[component] = legal
        elif component == 'gender_locked':
            if '-' in item['gender_locked']:
                genders = [int(c) for c in item['gender_locked'].split('-')]
                my_components['gender_locked'] = list(range(*genders))
            else:
                my_components['gender_locked'] = [int(c) for c in item['gender_locked'].split(',')]
        elif component == 'aoe':
            info_line = item['aoe'].split(',')
            aoe = AOEComponent(*info_line)
        # Affects map animation
        elif component == 'map_hit_color':
            my_components['map_hit_color'] = tuple(int(c) for c in item['map_hit_color'].split(','))
            assert len(my_components['map_hit_color']) == 3 # No translucency allowed right now
        elif component in ('damage', 'hit', 'weight', 'exp', 'crit', 'wexp_increase', 'wexp', 'extra_tile_damage', 'fatigue', 'target_fatigue'):
            if component in item:
                my_components[component] = int(item[component])
            elif component == 'crit':
                my_components['crit'] = 0
        elif component in ('movement', 'self_movement'):
            mode, magnitude = item[component].split(',')
            my_components[component] = MovementComponent(mode, magnitude)
        elif component == 'summon':
            klass = item['summon_klass']
            items = item['summon_items']
            name = item['summon_name']
            desc = item['summon_desc']
            my_components['summon'] = SummonComponent(klass, items, name, desc)
        elif component in item:
            my_components[component] = item[component]
        else:
            my_components[component] = True
    current_item = ItemObject(itemid, item['name'], item['spritetype'], item['spriteid'], my_components,
                              item['value'], item['RNG'], item['desc'],
                              aoe, weapontype, status, status_on_hold, status_on_equip,
                              droppable=droppable, event_combat=event_combat)
    if gameStateObj:
        gameStateObj.register_item(current_item)

    return current_item

def deserialize(item_dict):
    item = itemparser(item_dict['id'])
    if not item:
        return None
    item.uid = item_dict['uid']

    if 'owner' in item_dict:
        item.item_owner = item_dict['owner']
    if item_dict['droppable']:
        item.droppable = True
    if item_dict['event_combat']:
        item.event_combat = True
    if item_dict.get('uses') is not None:
        item.uses.uses = item_dict['uses']
    if item_dict.get('c_uses') is not None:
        item.c_uses.uses = item_dict['c_uses']

    if item_dict.get('cd_data') is not None:
        item.cooldown.deserialize(item_dict['cd_data'])

    return item
