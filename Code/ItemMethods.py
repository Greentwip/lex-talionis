try:
    import GlobalConstants as GC
    import configuration as cf
    import InfoMenu, MenuFunctions, Image_Modification, Utility, Weapons, Engine, TextChunk
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import InfoMenu, MenuFunctions, Image_Modification, Utility, Weapons, Engine, TextChunk

# === GENERIC ITEM OBJECT ========================================
class ItemObject(object):
    def __init__(self, i_id, name, spritetype, spriteid, components, value, RNG,
                 desc, aoe, weapontype, status, status_on_hold, status_on_equip,
                 droppable=False, locked=False, event_combat=False):
        self.spritetype = spritetype # Consumable, Sword, Used for spriting in list of sprites
        self.spriteid = spriteid # Number of sprite to be picked from spritesheet list
        
        self.id = i_id
        self.owner = 0
        self.name = str(name)
        self.value = int(value) # Value for one use of item, or for an infinite item
        self.RNG = RNG.split('-') # Comes in the form of looking like '1-2' or '1' or '2-3' or '3-10'
        self.event_combat = event_combat
        self.droppable = droppable # Whether this item is given to its owner's killer upon death
        self.locked = locked # Whether this item can be traded, sold, or dropped.
        assert not(self.droppable == self.locked == True), "%s can't be both droppable and locked to a unit!" %(self.name)
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

        self.loadSprites()

    def get_range(self):
        if self.owner:
            return get_range(self, self.owner)
        else:
            return []

    def get_range_string(self):
        return '-'.join(self.RNG)

    def serialize(self):
        serial_dict = {}
        serial_dict['id'] = self.id
        serial_dict['owner'] = self.owner
        serial_dict['droppable'] = self.droppable
        serial_dict['locked'] = self.locked
        serial_dict['event_combat'] = self.event_combat
        serial_dict['uses'] = self.uses.uses if self.uses else None
        serial_dict['c_uses'] = self.c_uses.uses if self.c_uses else None
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
        
    def draw(self, surf, topleft, white=False, cooldown=False):
        ItemSurf = self.image
        if white:
            ItemSurf = Image_Modification.flickerImageWhite(ItemSurf.convert_alpha(), abs(255 - Engine.get_time()%510))
            # ItemSurf = Image_Modification.transition_image_white(ItemSurf)
        surf.blit(ItemSurf, topleft)
        # if self.locked:
        #    locked_icon = GC.IMAGESDICT['LockedIcon']
        #    locked_rect = locked_icon.get_rect()
        #    locked_rect.bottomright = (ItemRect.right - 1, ItemRect.bottom - 1)
        #    surf.blit(locked_icon, locked_rect)

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
            raise ValueError("Item %s is trying to read from position %s on %s sprite which does not exist." % (self.id, sprite_id[1], self.spritetype))
        self.help_box = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def equip(self, ownerunit):
        ownerunit.equip(self)

    def get_help_box(self):
        if not self.help_box:
            self.help_box = self.create_help_box()
        return self.help_box

    def create_help_box(self):
        if self.weapon or self.spell:
            return Help_Dialog(self)
        else:
            return InfoMenu.Help_Dialog(self.desc)

    def drawType(self, surf, left, top):
        if self.icon:  
            self.icon.draw(surf, (left, top))

def get_range(item, unit):
    if len(item.RNG) == 1:
        r = item.RNG[0]
        if r == 'MAG/2':
            return [unit.stats['MAG']//2]
        elif r == 'MAG/2 + 1':
            return [unit.stats['MAG']//2 + 1]
        else:
            return [int(r)]
    elif len(item.RNG) == 2:
        r1 = item.RNG[0]
        r2 = item.RNG[1]
        if r1 == 'MAG/2':
            r1 = unit.stats['MAG']//2
        elif r1 == 'MAG/2 + 1':
            return unit.stats['MAG']//2 + 1
        else:
            r1 = int(r1)
        if r2 == 'MAG/2':
            r2 = unit.stats['MAG']//2
        elif r2 == 'MAG/2 + 1':
            return unit.stats['MAG']//2 + 1
        else:
            r2 = int(r2)
        return list(range(r1, r2 + 1))
    else:
        print('%s has an unsupported range: %s' % (item, item.get_range_string()))
        return []

class Help_Dialog(InfoMenu.Help_Dialog_Base):
    def __init__(self, item):
        self.last_time = self.start_time = 0
        self.transition_in = self.transition_out = False
        self.item = item
        font1 = GC.FONT['text_blue']
        font2 = GC.FONT['text_yellow']

        if self.item.weapon:
            if ',' in self.item.weapon.LVL:
                weaponLVL = 'Prf'
            else:
                weaponLVL = self.item.weapon.LVL
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
            if ',' in self.item.spell.LVL:
                spellLVL = 'Prf'
            else:
                spellLVL = self.item.spell.LVL
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
        self.help_surf = MenuFunctions.CreateBaseMenuSurf((size_x, size_y), 'MessageWindowBackground')  
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
               
class WeaponComponent(object):
    def __init__(self, stats):
        MT, HIT, LVL = stats
        self.MT = int(MT)
        self.HIT = int(HIT)
        self.LVL = LVL
        self.strLVL = self.LVL if self.LVL in ('A', 'B', 'C', 'D', 'E', 'S', 'SS') else 'Prf' # Display Prf if Lvl is weird

class ExtraSelectComponent(object):
    def __init__(self, RNG, targets):
        self.RNG = RNG.split('-')
        self.targets = targets

    def get_range_string(self):
        return '-'.join(self.RNG)

    def get_range(self, unit):
        return get_range(self, unit)

class AOEComponent(object):
    def __init__(self, mode, number=0):
        self.mode = mode
        self.number = number

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
            splash_positions = {position for position in other_position if tileMap.check_bounds(position)}
            return cursor_position, list(splash_positions - {cursor_position})
        elif self.mode == 'Blast':
            if self.number == 'MAG/2':
                num = item.owner.stats['MAG']//2
            else:
                num = int(self.number)
            splash_positions = Utility.find_manhattan_spheres(range(num + 1), cursor_position)
            splash_positions = {position for position in splash_positions if tileMap.check_bounds(position)}
            if item.weapon:
                return cursor_position, list(splash_positions - {cursor_position})
            else:
                return None, list(splash_positions)
        elif self.mode == 'Line':
            splash_positions = Utility.raytrace(unit_position, cursor_position)
            splash_positions = [position for position in splash_positions if position != unit_position]
            return None, splash_positions
        elif self.mode == 'AllAllies':
            splash_positions = [unit.position for unit in gameStateObj.allunits if item.owner.checkIfAlly(unit)]
            return None, splash_positions
        elif self.mode == 'AllEnemies':
            splash_positions = [unit.position for unit in gameStateObj.allunits if item.owner.checkIfEnemy(unit)]
            return None, splash_positions
        elif self.mode == 'AllUnits':
            splash_positions = [unit.position for unit in gameStateObj.allunits]
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

class SpellComponent(object):
    def __init__(self, LVL, targets):
        self.name = 'spell'
        self.LVL = LVL
        self.targets = targets # Ally, Enemy, Tile... maybe more?
        self.strLVL = self.LVL if self.LVL in ['A', 'B', 'C', 'D', 'E', 'S', 'SS'] else 'Prf' # Display Prf is Lvl is weird

class MovementComponent(object):
    def __init__(self, mode, magnitude):
        self.name = 'movement'
        self.mode = mode
        self.magnitude = magnitude

class SummonComponent(object):
    def __init__(self, klass, items, name, desc, ai, s_id):
        self.klass = klass
        self.name = name
        self.item_line = items
        self.desc = desc
        self.ai = ai
        self.s_id = s_id

# === ITEM PARSER ======================================================
# Takes a string of item ids, as well as the database of item data, and outputs a list of items.
def itemparser(itemstring):
    Items = []
    if itemstring: # itemstring needs to exist
        idlist = itemstring.split(',')
        for itemid in idlist:
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
                continue

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

            if 'locked' in components:
                locked = True
            else:
                locked = False
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
                elif component == 'promotion':
                    legal_classes = item['promotion'].split(',')
                    my_components['promotion'] = legal_classes
                elif component == 'aoe':
                    info_line = item['aoe'].split(',')
                    aoe = AOEComponent(*info_line)
                # Affects map animation
                elif component == 'map_hit_color':
                    my_components['map_hit_color'] = tuple(int(c) for c in item['map_hit_color'].split(','))
                    assert len(my_components['map_hit_color']) == 3 # No translucency allowed right now
                elif component in ('damage', 'hit', 'weight', 'exp', 'crit', 'wexp_increase', 'wexp', 'extra_tile_damage'):
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
                    ai = item['summon_ai']
                    s_id = item['summon_s_id']
                    my_components['summon'] = SummonComponent(klass, items, name, desc, ai, s_id)
                elif component in item:
                    my_components[component] = item[component]
                else:
                    my_components[component] = True
            currentItem = ItemObject(itemid, item['name'], item['spritetype'], item['spriteid'], my_components,
                                     item['value'], item['RNG'], item['desc'],
                                     aoe, weapontype, status, status_on_hold, status_on_equip,
                                     droppable=droppable, locked=locked, event_combat=event_combat)

            Items.append(currentItem)          
    return Items

def deserialize(item_dict):
    items = itemparser(item_dict['id'])
    if not items:
        return None
    else:
        item = items[0]

    if 'owner' in item_dict:
        item.owner = item_dict['owner']
    if item_dict['droppable']:
        item.droppable = True
    if item_dict['event_combat']:
        item.event_combat = True
    if item_dict['locked']:
        item.locked = True
    if item_dict['uses']:
        item.uses.uses = item_dict['uses']
    if item_dict['c_uses']:
        item.c_uses.uses = item_dict['c_uses']
    return item
