from imagesDict import getImages
from GlobalConstants import *
import InfoMenu, MenuFunctions, StatusObject, SaveLoad, Image_Modification, Utility, CustomObjects, Engine, bmpfont
import copy

# === GENERIC ITEM OBJECT ========================================
class ItemObject(object):
    def __init__(self, i_id, name, spritetype, spriteid, components, value, RNG, \
                 desc, aoe, weapontype, status, status_on_hold, status_on_equip, \
                 droppable=False, locked=False, event_combat=False):
        self.spritetype = spritetype # Consumable, Sword, Used for spriting in list of sprites
        self.spriteid = spriteid # Number of sprite to be picked from spritesheet list
        
        self.id = i_id
        self.owner = 0
        self.name = str(name)
        self.value = int(value) # Value for one use of item, or for an infinite item
        self.RNG = self.parseRNG(RNG) # Comes in the form of looking like '1-2' or '1' or '2-3' or '3-10'
        self.strRNG = RNG # string version of RNG for display
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
        self.icons = []
        for weapon_type in self.TYPE:
            self.icons.append(CustomObjects.WeaponIcon(weapon_type))
        
        # Creates component slots
        self.components = components # Consumable, Weapon, Spell Bigger Picture
        for component_key, component_value in self.components.iteritems():
            self.__dict__[component_key] = component_value

        self.loadSprites()

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

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)
        
    def draw(self, surf, topleft, white=False, cooldown=False):
        ItemSurf = self.image
        if white:
            ItemSurf = Image_Modification.flickerImageWhite(ItemSurf.convert_alpha(), 255)
            #ItemSurf = Image_Modification.transition_image_white(ItemSurf)
        surf.blit(ItemSurf, topleft)
        #if self.locked:
        #    locked_icon = IMAGESDICT['LockedIcon']
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
        self.image = Engine.subsurface(ITEMDICT[self.spritetype], (16*sprite_id[0], 16*sprite_id[1], 16, 16))

        #self.image = Engine.subsurface(ITEMDICT[self.spritetype], (0, 16*int(self.spriteid), 16, 16))
        self.help_box = self.get_help_box()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def equip(self, ownerunit):
        ownerunit.equip(self)

    def get_help_box(self):
        if self.weapon or self.spell:
            font1 = FONT['text_blue']
            font2 = FONT['text_yellow']

            if self.weapon:
                first_line_text = [' ', self.weapon.LVL, ' Mt ', str(self.weapon.MT), ' Hit ', str(self.weapon.HIT)]
                if self.WT:
                    first_line_text += [' Wt ', str(self.WT)]
                first_line_text += [' Rng ', self.strRNG]
                first_line_font = [font1, font1, font2, font1, font2, font1]
                if self.WT:
                    first_line_font += [font2, font1]
                first_line_font += [font2, font1]

            elif self.spell:
                first_line_text = [' ', self.spell.LVL]
                first_line_font = [font1, font1]
                if self.damage is not None:
                    first_line_text += [' Mt ', str(self.damage)]
                    first_line_font += [font2, font1]
                if self.hit is not None:
                    first_line_text += [' Hit ', str(self.hit)]
                    first_line_font += [font2, font1]
                first_line_text += [' Rng ', self.strRNG]
                first_line_font += [font2, font1]

            first_line_length = max(font1.size(''.join(first_line_text))[0] + 16 * len(self.TYPE) + 4, 112) # 112 was 96
            if self.desc:
                output_desc_lines = MenuFunctions.line_wrap(MenuFunctions.line_chunk(self.desc), first_line_length, FONT['convo_black']) 
            else:
                output_desc_lines = ''
            size_x = first_line_length + 16
            size_y = 24 + len(output_desc_lines)*16
            help_surf = MenuFunctions.CreateBaseMenuSurf((size_x, size_y), 'MessageWindowBackground')  
            self.drawType(help_surf, 4, 4)
            
            # Actually blit first line
            word_index = 4 + 16 * len(self.TYPE)
            for index, word in enumerate(first_line_text):
                first_line_font[index].blit(word, help_surf, (word_index, 4))
                word_index += first_line_font[index].size(word)[0]
            
            for index, line in enumerate(output_desc_lines):
                FONT['convo_black'].blit(''.join(line), help_surf, (4, FONT['convo_black'].height*index + 4 + 16))  

            return help_surf

        else:
            return InfoMenu.create_help_box(self.desc)

    def drawType(self, surf, left, top):
        for index, icon in enumerate(self.icons):    
            icon.draw(surf, (left + index*16, top))

    def parseRNG(self, RNG):
        # Should output a list of integers corresponding to acceptable ranges
        if '-' in RNG:
            rngsplit = RNG.split('-')
            return range(int(rngsplit[0]), int(rngsplit[1]) + 1)
        else:
            return [int(RNG)]

    def get_str_RNG(self):
        max_rng = max(self.RNG)
        min_rng = min(self.RNG)
        if max_rng == min_rng:
            return str(max_rng)
        else:
            return ''.join([str(min_rng), '-', str(max_rng)])

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
        self.name = 'uses'
        self.uses = int(uses)
        self.total_uses = self.uses

    def __repr__(self):
        return str(self.uses)

    def decrement(self):
        self.uses -= 1

class CUsesComponent(object):
    def __init__(self, uses):
        self.name = 'c_uses'
        self.uses = int(uses)
        self.total_uses = self.uses

    def __repr__(self):
        return str(self.uses)

    def decrement(self):
        self.uses -= 1
        self.uses = max(self.uses, 0)
               
class WeaponComponent(object):
    def __init__(self, (MT, HIT, LVL)):
        self.name = 'weapon'
        self.MT = int(MT)
        self.HIT = int(HIT)
        self.LVL = LVL
        self.strLVL = self.LVL if self.LVL in ['A', 'B', 'C', 'D', 'E', 'S', 'SS'] else 'Prf' # Display Prf if Lvl is weird

class AOEComponent(object):
    def __init__(self, mode, number):
        self.mode = mode
        self.number = number

    def get_positions(self, unit_position, cursor_position, tileMap):
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
            other_position = [(p[0] - 1, p[1] - 1), (p[0], p[1] - 1), (p[0] + 1, p[1] - 1), \
                              (p[0] - 1, p[1]), (p[0] + 1, p[1]), \
                              (p[0] - 1, p[1] + 1), (p[0], p[1] + 1), (p[0] + 1, p[1] + 1)]
            splash_positions = {position for position in other_position if tileMap.check_bounds(position)}
            return cursor_position, list(splash_positions - {cursor_position})
        elif self.mode == 'Blast':
            splash_positions = [(cursor_position)]
            for r in range(1, self.number + 1):
                # Finds manhattan spheres of radius r
                for x in range(-r, r + 1):
                    for y in [(r - abs(x)), -(r - abs(x))]:
                        splash_positions.append((cursor_position[0] + x, cursor_position[1] + y))
            splash_positions = [position for position in splash_positions if tileMap.check_bounds(position)]
            # remove dupes
            splash_positions = list(set(splash_positions))
            return None, splash_positions
        elif self.mode == 'Line':
            splash_positions = Utility.raytrace(unit_position, cursor_position)
            splash_positions = [position for position in splash_positions if position != unit_position]
            return None, splash_positions
        else:
            print('Error! ' + self.mode + ' AOE mode is not supported yet!')
            return cursor_position, []

class UsableComponent(object):
    def __init__(self):
        self.name = 'usable'

class EffectiveComponent(object):
    def __init__(self, effective_against):
        # List of types its effective against
        self.against = effective_against

class PermanentStatIncreaseComponent(object):
    def __init__(self, stat_increase):
        self.stat_increase = stat_increase

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
                item = ITEMDATA[itemid]
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
                    weapontype = []
                else:
                    weapontype = weapontype.split(',')
            else:
                weapontype = []

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
                    my_components['uses'] = UsesComponent(int(item['uses']))
                elif component == 'c_uses':
                    my_components['c_uses'] = CUsesComponent(int(item['c_uses']))
                elif component == 'weapon':
                    stats = [item['MT'], item['HIT'], item['LVL']]
                    my_components['weapon'] = WeaponComponent(stats)
                elif component == 'usable':
                    my_components['usable'] = UsableComponent()
                elif component == 'spell':
                    my_components['spell'] = SpellComponent(item['LVL'], item['targets'])
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
                    effective_against = item['effective'].split(',')
                    my_components['effective'] = EffectiveComponent(effective_against)
                elif component == 'permanent_stat_increase':
                    stat_increase = SaveLoad.intify_comma_list(item['stat_increase'])
                    my_components['permanent_stat_increase'] = PermanentStatIncreaseComponent(stat_increase)
                elif component == 'aoe':
                    info_line = item['aoe'].split(',')
                    aoe = AOEComponent(info_line[0], int(info_line[1]))
                # Affects both player and ai
                elif component == 'target_restrict':
                    my_components['target_restrict'] = item['target_restrict']
                # Only affects ai
                elif component == 'custom_ai':
                    my_components['custom_ai'] = item['custom_ai']
                elif component == 'custom_ai_value':
                    my_components['custom_ai_value'] = item['custom_ai_value']
                elif component == 'heal':
                    my_components['heal'] = item['heal']
                elif component == 'damage':
                    my_components['damage'] = int(item['damage'])
                elif component == 'hit':
                    my_components['hit'] = int(item['hit'])
                elif component == 'weight':
                    my_components['WT'] = int(item['WT'])
                elif component == 'exp':
                    my_components['exp'] = int(item['exp'])
                elif component == 'wexp_increase':
                    my_components['wexp_increase'] = int(item['wexp_increase'])
                elif component in ['movement', 'self_movement']:
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
                else:
                    my_components[component] = True
            currentItem = ItemObject(itemid, item['name'], item['spritetype'], item['spriteid'], my_components, \
                                     item['value'], item['RNG'], item['desc'], \
                                     aoe, weapontype, status, status_on_hold, status_on_equip, \
                                     droppable=droppable, locked=locked, event_combat=event_combat)

            Items.append(currentItem)          
    return Items

def deserialize(item_dict):
    item = itemparser(item_dict['id'])[0]
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