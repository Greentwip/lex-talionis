from . import GlobalConstants as GC
from . import configuration as cf
from . import Counters, Engine
from . import BaseMenuSurf
from . import ClassData, TextChunk

class HelpGraph(object):
    def __init__(self, state, unit, gameStateObj):
        self.help_boxes = {}
        self.unit = unit
        self.current = None

        if state == 'Personal Data':
            self.populate_personal_data(gameStateObj)
            self.initial = "Strength"
        elif state == 'Personal Growths':
            self.populate_personal_data(gameStateObj, growths=True)
            self.initial = "Strength"
        elif state == 'Equipment':
            self.populate_equipment()
            if self.unit.items:
                self.initial = "Item0"
            else:
                self.initial = "Unit Desc"
        elif state == 'Support & Status':
            self.populate_status(gameStateObj)
            if [wexp for wexp in self.unit.wexp if wexp > 0]:
                self.initial = "Wexp0"
            else:
                self.initial = "Unit Desc"

    def populate_personal_data(self, gameStateObj, growths=False):
        self.help_boxes["Strength"] = Help_Box("Strength", (88, 26), Help_Dialog(cf.WORDS['STR_desc']))
        self.help_boxes["Magic"] = Help_Box("Magic", (88, GC.TILEHEIGHT + 26), Help_Dialog(cf.WORDS['MAG_desc']))
        self.help_boxes["Skill"] = Help_Box("Skill", (88, GC.TILEHEIGHT*2 + 26), Help_Dialog(cf.WORDS['SKL_desc']))
        self.help_boxes["Speed"] = Help_Box("Speed", (88, GC.TILEHEIGHT*3 + 26), Help_Dialog(cf.WORDS['SPD_desc']))
        self.help_boxes["Defense"] = Help_Box("Defense", (88, GC.TILEHEIGHT*4 + 26), Help_Dialog(cf.WORDS['DEF_desc']))
        self.help_boxes["Resistance"] = Help_Box("Resistance", (88, GC.TILEHEIGHT*5 + 26), Help_Dialog(cf.WORDS['RES_desc']))

        self.help_boxes["Luck"] = Help_Box("Luck", (152, 26), Help_Dialog(cf.WORDS['LCK_desc']))
        self.help_boxes["Movement"] = Help_Box("Movement", (152, GC.TILEHEIGHT + 26), Help_Dialog(cf.WORDS['MOV_desc']))
        self.help_boxes["Con"] = Help_Box("Con", (152, GC.TILEHEIGHT*2 + 26), Help_Dialog(cf.WORDS['CON_desc']))
        if growths:
            self.help_boxes["Aid"] = Help_Box("Aid", (152, GC.TILEHEIGHT*3 + 26), Help_Dialog(cf.WORDS['HP_desc']))
        else:
            self.help_boxes["Aid"] = Help_Box("Aid", (152, GC.TILEHEIGHT*3 + 26), Help_Dialog(cf.WORDS['Aid_desc']))
        self.help_boxes["Traveler"] = Help_Box("Traveler", (152, GC.TILEHEIGHT*4 + 26), Help_Dialog(cf.WORDS['Trv_desc']))
        if cf.CONSTANTS['support']:
            if self.unit.name in gameStateObj.support.node_dict:
                affinity_desc = gameStateObj.support.node_dict[self.unit.name].affinity.desc
                affinity_desc = 'Gives ' + affinity_desc
            else:
                affinity_desc = cf.WORDS['NoAffin_desc']
            self.help_boxes["Affin"] = Help_Box("Affin", (152, GC.TILEHEIGHT*5 + 26), Help_Dialog(affinity_desc))
        else:
            self.help_boxes["Affin"] = Help_Box("Affin", (152, GC.TILEHEIGHT*5 + 26), Help_Dialog(cf.WORDS['Rat_desc']))

        # Connect personal data
        self.help_boxes["Strength"].down = "Magic"
        self.help_boxes["Magic"].down = "Skill"
        self.help_boxes["Skill"].down = "Speed"
        self.help_boxes["Speed"].down = "Defense"
        self.help_boxes["Defense"].down = "Resistance"
        self.help_boxes["Resistance"].up = "Defense"
        self.help_boxes["Magic"].up = "Strength"
        self.help_boxes["Skill"].up = "Magic"
        self.help_boxes["Speed"].up = "Skill"
        self.help_boxes["Defense"].up = "Speed"
        self.help_boxes["Strength"].right = "Luck"
        self.help_boxes["Magic"].right = "Movement"
        self.help_boxes["Skill"].right = "Con"
        self.help_boxes["Speed"].right = "Aid"
        self.help_boxes["Defense"].right = "Traveler"
        self.help_boxes["Resistance"].right = "Affin"

        self.help_boxes["Luck"].down = "Movement"
        self.help_boxes["Movement"].down = "Con"
        self.help_boxes["Con"].down = "Aid"
        self.help_boxes["Aid"].down = "Traveler"
        self.help_boxes["Traveler"].down = "Affin"
        self.help_boxes["Movement"].up = "Luck"
        self.help_boxes["Con"].up = "Movement"
        self.help_boxes["Aid"].up = "Con"
        self.help_boxes["Traveler"].up = "Aid"
        self.help_boxes["Affin"].up = "Traveler"
        self.help_boxes["Luck"].left = "Strength"
        self.help_boxes["Movement"].left = "Magic"
        self.help_boxes["Con"].left = "Skill"
        self.help_boxes["Aid"].left = "Speed"
        self.help_boxes["Traveler"].left = "Defense"
        self.help_boxes["Affin"].left = "Resistance"

        # Populate Class Skills
        skills = [status for status in self.unit.status_effects if status.class_skill]

        for index, skill in enumerate(skills):
            if skill.combat_art and skill.combat_art.charge_max > 0:
                description = skill.desc + ' ' + str(skill.combat_art.current_charge) + '/' + str(skill.combat_art.charge_max)
            elif skill.activated_item and skill.activated_item.charge_max > 0:
                description = skill.desc + ' ' + str(skill.activated_item.current_charge) + '/' + str(skill.activated_item.charge_max)
            else:
                description = skill.desc
            left_pos = index*((GC.WINWIDTH - 96)//max(cf.CONSTANTS['num_skills'], len(skills))) + 92
            self.help_boxes["Skill"+str(index)] = Help_Box("Skill"+str(index), (left_pos, GC.WINHEIGHT - 32), Help_Dialog(description, name=skill.name))

        for i in range(len(skills)):
            self.help_boxes["Skill"+str(i)].up = "Resistance"
            self.help_boxes["Skill"+str(i)].right = ("Skill"+str(i+1)) if i < (len(skills) - 1) else None
            self.help_boxes["Skill"+str(i)].left = ("Skill"+str(i-1)) if i > 0 else None

        self.populate_info_menu_default()

        if skills:
            self.help_boxes["Skill0"].left = "HP"
            self.help_boxes["HP"].right = "Skill0"
            self.help_boxes["Experience"].right = "Skill0"
            self.help_boxes["Resistance"].down = "Skill0"
            self.help_boxes["Affin"].down = "Skill0"

        # Connect default with personal data
        self.help_boxes["Unit Desc"].right = "Speed"
        self.help_boxes["Class Desc"].right = "Resistance"
        self.help_boxes["Resistance"].left = "Class Desc"
        self.help_boxes["Defense"].left = "Unit Desc"
        self.help_boxes["Speed"].left = "Unit Desc"
        self.help_boxes["Magic"].left = "Unit Desc"
        self.help_boxes["Strength"].left = "Unit Desc"
        self.help_boxes["Skill"].left = "Unit Desc"

        if cf.CONSTANTS['fatigue'] and self.unit.team == 'player' and \
                'Fatigue' in gameStateObj.game_constants:
            self.help_boxes["Fatigue"] = Help_Box("Fatigue", (88, GC.WINHEIGHT - 15), Help_Dialog(cf.WORDS['Ftg_desc']))
            self.help_boxes["HP"].right = "Fatigue"
            self.help_boxes["Fatigue"].left = "HP"
            if skills:
                for i in range(len(skills)):
                    self.help_boxes["Skill" + str(i)].down = 'Fatigue'
                self.help_boxes["Fatigue"].up = "Skill0"
            else:
                self.help_boxes["Resistance"].down = "Fatigue"
                self.help_boxes["Affin"].down = "Fatigue"
                self.help_boxes['Fatigue'].up = "Resistance"

    def populate_equipment(self):
        for index, item in enumerate(self.unit.items):
            pos = (88, GC.TILEHEIGHT*index + 24)
            self.help_boxes["Item"+str(index)] = Help_Box("Item"+str(index), pos, item.get_help_box())

        self.help_boxes["Atk"] = Help_Box("Atk", (100, GC.WINHEIGHT - 40), Help_Dialog(cf.WORDS['Atk_desc']))
        self.help_boxes["Hit"] = Help_Box("Hit", (100, GC.WINHEIGHT - 24), Help_Dialog(cf.WORDS['Hit_desc']))
        self.help_boxes["Rng"] = Help_Box("Rng", (158, GC.WINHEIGHT - 56), Help_Dialog(cf.WORDS['Rng_desc']))
        self.help_boxes["AS"] = Help_Box("AS", (158, GC.WINHEIGHT - 40), Help_Dialog(cf.WORDS['AS_desc']))
        self.help_boxes["Avoid"] = Help_Box("Avoid", (158, GC.WINHEIGHT - 24), Help_Dialog(cf.WORDS['Avoid_desc']))

        # Add connections
        for i in range(len(self.unit.items)):
            self.help_boxes["Item"+str(i)].down = ("Item"+str(i+1)) if i < (len(self.unit.items) - 1) else None
            self.help_boxes["Item"+str(i)].up = ("Item"+str(i-1)) if i > 0 else None

        if self.unit.items:
            self.help_boxes["Item" + str(len(self.unit.items) - 1)].down = "Atk"

        self.help_boxes["Atk"].right = "AS"
        self.help_boxes["Atk"].down = "Hit"
        self.help_boxes["Atk"].up = ("Item"+str(len(self.unit.items) - 1)) if self.unit.items else "Unit Desc"
        self.help_boxes["Atk"].left = "Experience"

        self.help_boxes["Hit"].left = "HP"
        self.help_boxes["Hit"].right = "Avoid"
        self.help_boxes["Hit"].up = "Atk"

        self.help_boxes["Avoid"].left = "Hit"
        self.help_boxes["Avoid"].up = "AS"

        self.help_boxes["AS"].left = "Atk"
        self.help_boxes["AS"].up = "Rng"
        self.help_boxes["AS"].down = "Avoid"

        self.help_boxes["Rng"].left = "Atk"
        self.help_boxes["Rng"].up = ("Item"+str(len(self.unit.items) - 1)) if self.unit.items else "Unit Desc"
        self.help_boxes["Rng"].down = "AS"

        self.populate_info_menu_default()

        # Connect default with equipment
        for i in range(len(self.unit.items)):
            self.help_boxes["Item"+str(i)].left = "Unit Desc"

        if self.unit.items:
            self.help_boxes['Unit Desc'].up = "Item0"
            self.help_boxes['Unit Desc'].right = "Item" + str(min(3, len(self.unit.items) - 1))

        self.help_boxes["Class Desc"].right = "Atk"
        self.help_boxes["Experience"].right = "Atk"
        self.help_boxes["HP"].right = "Hit"

    def populate_status(self, gameStateObj):
        # Populate Weapon Exp
        good_weapons = [wexp for wexp in self.unit.wexp if wexp > 0]
        for index, wexp in enumerate(good_weapons):
            self.help_boxes["Wexp"+str(index)] = Help_Box("Wexp"+str(index), (92 + 60*index, 26), Help_Dialog("Weapon Rank: %s"%(wexp)))

        for i in range(len(good_weapons)):
            self.help_boxes["Wexp"+str(i)].right = ("Wexp"+str(i+1)) if i < (len(good_weapons) - 1) else None
            self.help_boxes["Wexp"+str(i)].left = ("Wexp"+str(i-1)) if i > 0 else None

        # Non-class skills
        statuses = [status for status in self.unit.status_effects if not (status.class_skill or status.hidden)]

        for index, status in enumerate(statuses):
            left_pos = index*((GC.WINWIDTH - 96)//max(5, len(statuses))) + 92
            self.help_boxes["Status"+str(index)] = Help_Box("Status"+str(index), (left_pos, GC.WINHEIGHT - 20), Help_Dialog(status.desc, name=status.name))

        # Connect them together
        for i in range(len(statuses)):
            self.help_boxes["Status"+str(i)].right = ("Status"+str(i+1)) if i < (len(statuses) - 1) else None
            self.help_boxes["Status"+str(i)].left = ("Status"+str(i-1)) if i > 0 else 'HP'

        # Supports
        if gameStateObj.support:
            supports = gameStateObj.support.get_supports(self.unit.id)
            supports = [support for support in supports if support[2]]
        else:
            supports = []
        for index, support in enumerate(supports):
            affinity = support[1]
            desc = affinity.desc
            pos = (96, 16*index + 48)
            self.help_boxes["Support"+str(index)] = Help_Box("Support"+str(index), pos, Help_Dialog(desc))

        # Connect supports
        for i in range(len(supports)):
            self.help_boxes["Support"+str(i)].down = ("Support"+str(i+1)) if i < (len(supports) - 1) else None
            self.help_boxes["Support"+str(i)].up = ("Support"+str(i-1)) if i > 0 else None

        self.populate_info_menu_default()
        
        for i in range(len(supports)):
            self.help_boxes["Support"+str(i)].left = "Unit Desc"

        if good_weapons:
            self.help_boxes["Wexp0"].left = "Unit Desc"
            self.help_boxes['Unit Desc'].up = "Wexp0"
        if good_weapons and supports:
            for i in range(len(good_weapons)):
                self.help_boxes["Wexp"+str(i)].down = "Support0"
            self.help_boxes["Support0"].up = "Wexp0"
        elif good_weapons and statuses:
            for i in range(len(good_weapons)):
                self.help_boxes["Wexp"+str(i)].down = "Status0"
            for i in range(len(statuses)):
                self.help_boxes["Status"+str(i)].up = "Wexp0"
        if statuses and supports:
            for i in range(len(statuses)):
                self.help_boxes["Status"+str(i)].up = "Support"+str(len(supports)-1)
            self.help_boxes["Support" + str(len(supports)-1)].down = "Status0"
        if supports:
            self.help_boxes['Unit Desc'].right = "Support" + str(min(3, len(supports) - 1))
            self.help_boxes['Experience'].right = "Support" + str(min(3, len(supports) - 1))
            self.help_boxes['HP'].right = "Support" + str(min(3, len(supports) - 1))
        elif good_weapons:
            self.help_boxes['Unit Desc'].right = "Wexp0"
            self.help_boxes['Experience'].right = "Wexp0"
            self.help_boxes['HP'].right = "Wexp0"
        elif statuses:
            self.help_boxes['Unit Desc'].right = "Status0"
            self.help_boxes['Experience'].right = "Status0"
            self.help_boxes['HP'].right = "Status0"

    def populate_info_menu_default(self):
        self.help_boxes["Unit Desc"] = Help_Box("Unit Desc", (16, 82), Help_Dialog(self.unit.desc))
        self.help_boxes["Class Desc"] = Help_Box("Class Desc", (-8, 107), Help_Dialog(ClassData.class_dict[self.unit.klass]['desc']))
        self.help_boxes["Unit Level"] = Help_Box("Unit Level", (-8, 123), Help_Dialog(cf.WORDS['Level_desc']))
        self.help_boxes["Experience"] = Help_Box("Experience", (22, 123), Help_Dialog(cf.WORDS['Exp_desc']))
        self.help_boxes["HP"] = Help_Box("HP", (-8, 139), Help_Dialog(cf.WORDS['HP_desc']))

        # Connections
        self.help_boxes["Unit Desc"].down = "Class Desc"
        self.help_boxes["Class Desc"].up = "Unit Desc"
        self.help_boxes["Class Desc"].down = "Unit Level"
        self.help_boxes["Unit Level"].up = "Class Desc"
        self.help_boxes["Unit Level"].right = "Experience"
        self.help_boxes["Unit Level"].down = "HP"
        self.help_boxes["Experience"].left = "Unit Level"
        self.help_boxes["Experience"].up = "Class Desc"
        self.help_boxes["Experience"].down = "HP"
        self.help_boxes["HP"].up = "Unit Level"

class Help_Box(Counters.CursorControl):
    def __init__(self, name, cursor_position, help_surf):
        self.name = name
        self.cursor_position = cursor_position
        self.help_dialog = help_surf
        # Determine help_topleft position
        if self.cursor_position[0] + self.help_dialog.get_width() > GC.WINWIDTH:
            helpleft = GC.WINWIDTH - self.help_dialog.get_width() - 8
        else:
            helpleft = self.cursor_position[0] - min(GC.TILEWIDTH*2, self.cursor_position[0]) # Don't go to far to the left
        if self.cursor_position[1] >= GC.WINHEIGHT//2 + 8:
            helptop = self.cursor_position[1] - self.help_dialog.get_height()
        else:
            helptop = self.cursor_position[1] + 16
        self.help_topleft = (helpleft, helptop)

        self.left = None
        self.right = None
        self.up = None
        self.down = None

        Counters.CursorControl.__init__(self)

    def draw(self, surf, info=True):
        surf.blit(self.cursor, (self.cursor_position[0] + self.cursorAnim[self.cursorCounter], self.cursor_position[1]))
        if info:
            self.help_dialog.draw(surf, self.help_topleft)

class Help_Dialog_Base(object):
    def get_width(self):
        return self.help_surf.get_width()

    def get_height(self):
        return self.help_surf.get_height()

    def handle_transition_in(self, time, h_surf):
        # Handle transitioning in
        if self.transition_in:
            perc = (time - self.start_time) / 130.
            if perc >= 1:
                self.transition_in = False
            else:
                h_surf = Engine.transform_scale(h_surf, (int(perc*h_surf.get_width()), int(perc*h_surf.get_height())))
                # h_surf = Image_Modification.flickerImageTranslucent255(h_surf, perc*255)
        return h_surf

    def set_transition_out(self):
        self.transition_out = Engine.get_time()

    def handle_transition_out(self, time, h_surf):
        # Handle transitioning in
        if self.transition_out:
            perc = 1. - ((time - self.transition_out) / 100.)
            if perc <= 0:
                self.transition_out = -1
                perc = 0.1
            h_surf = Engine.transform_scale(h_surf, (int(perc*h_surf.get_width()), int(perc*h_surf.get_height())))
            # h_surf = Image_Modification.flickerImageTranslucent255(h_surf, perc*255)
        return h_surf

    def final_draw(self, surf, pos, time, help_surf):
        # Draw help logo
        h_surf = Engine.copy_surface(self.h_surf)
        h_surf.blit(help_surf, (0, 3))
        h_surf.blit(GC.IMAGESDICT['HelpLogo'], (9, 0))

        if self.transition_in:
            h_surf = self.handle_transition_in(time, h_surf)
        elif self.transition_out:
            h_surf = self.handle_transition_out(time, h_surf)

        surf.blit(h_surf, pos)

class Help_Dialog(Help_Dialog_Base):
    def __init__(self, description, num_lines=2, name=False):
        self.font = GC.FONT['convo_black']
        self.name = name
        self.last_time = self.start_time = 0
        self.transition_in = self.transition_out = False
        # Set up variables needed for algorithm
        if not description:
            description = ''
        # Hard set num_lines if description is very short.
        if len(description) < 24:
            num_lines = 1

        self.strings = TextChunk.split(self.font, description, num_lines)

        # Find the greater of the two lengths
        greater_line_len = max([self.font.size(string)[0] for string in self.strings])
        if self.name:
            greater_line_len = max(greater_line_len, self.font.size(self.name)[0])

        self.width = greater_line_len + 24
        if name:
            num_lines += 1
        self.height = self.font.height * num_lines + 16

        self.help_surf = BaseMenuSurf.CreateBaseMenuSurf((self.width, self.height), 'MessageWindowBackground')
        self.h_surf = Engine.create_surface((self.width, self.height + 3), transparent=True)

    def draw(self, surf, pos):
        time = Engine.get_time()
        if time > self.last_time + 1000:  # If it's been at least a second since last update
            self.start_time = time - 16
        self.last_time = time

        help_surf = Engine.copy_surface(self.help_surf)
        # Now draw
        if self.name:
            self.font.blit(self.name, help_surf, (8, 8))

        if cf.OPTIONS['Text Speed'] > 0:
            num_characters = int(2*(time - self.start_time)/float(cf.OPTIONS['Text Speed']))
        else:
            num_characters = 1000
        for index, string in enumerate(self.strings):
            if num_characters > 0:
                self.font.blit(string[:num_characters], help_surf, (8, self.font.height*index + 8 + (16 if self.name else 0)))
                num_characters -= len(string)
    
        self.final_draw(surf, pos, time, help_surf)

class LevelUpQuote_Dialog(Help_Dialog_Base):
    def __init__(self, description):
        self.font = GC.FONT['convo_black']
        self.last_time = self.start_time = 0
        self.transition_in = True
        self.transition_out = False
        self.waiting_cursor_offset = [0]*20 + [1]*2 + [2]*8 + [1]*2
        self.waiting_cursor_offset_index = 0
        self.end_text_position = None
        
        # Set up variables needed for algorithm
        num_lines = 2
        if self.font.size(description)[0] < 212:
            num_lines = 1

        self.strings = TextChunk.split(self.font, description, num_lines)

        # Find the greater of the two lengths
        greater_line_len = max([self.font.size(string)[0] for string in self.strings])
        self.width = greater_line_len + 28
        self.height = self.font.height * num_lines + 8

        self.help_surf = BaseMenuSurf.CreateBaseMenuSurf((self.width, self.height), 'MessageWindowBackground')
        self.h_surf = Engine.create_surface((self.width, self.height + 3), transparent=True)

    def draw(self, surf, pos):
        time = Engine.get_time()
        if time > self.last_time + 1000:  # If it's been at least a second since last update
            self.start_time = time - 16
        self.last_time = time

        h_surf = Engine.copy_surface(self.help_surf)

        if cf.OPTIONS['Text Speed'] > 0:
            num_characters = int((time - self.start_time)/float(cf.OPTIONS['Text Speed']))
        else:
            num_characters = 1000
        
        for index, string in enumerate(self.strings):
            if num_characters > 0:
                self.font.blit(string[:num_characters], h_surf, (8, self.font.height*index + 4))
                if index == len(self.strings) - 1 and len(string[:num_characters]) == len(string):
                    self.end_text_position = (8 + self.font.size(string[:num_characters])[0], self.font.height*index + 4)
                num_characters -= len(string)
    
        if self.transition_in:
            h_surf = self.handle_transition_in(time, h_surf)
        elif self.transition_out:
            h_surf = self.handle_transition_out(time, h_surf)

        if pos[0] + h_surf.get_width()//2 > GC.WINWIDTH - 4:
            new_pos = (GC.WINWIDTH - h_surf.get_width() - 4, pos[1] - h_surf.get_height()//2)
        else:
            new_pos = (pos[0] - h_surf.get_width()//2, pos[1] - h_surf.get_height()//2)
        surf.blit(h_surf, new_pos)

        # Message tail
        if not self.transition_in and not self.transition_out:
            message_tail_pos = (pos[0], pos[1] + h_surf.get_height()//2 - 2)
            tail_surf = GC.IMAGESDICT['MessageWindowTail']
            surf.blit(tail_surf, message_tail_pos)

        # Draw waiting cursor
        if self.end_text_position:
            self.waiting_cursor_offset_index += 1
            if self.waiting_cursor_offset_index > len(self.waiting_cursor_offset) - 1:
                self.waiting_cursor_offset_index = 0

            cursor_pos = (2 + new_pos[0] + self.end_text_position[0],
                          5 + new_pos[1] + self.end_text_position[1] + self.waiting_cursor_offset[self.waiting_cursor_offset_index])
            surf.blit(GC.IMAGESDICT['WaitingCursor'], cursor_pos)
