from . import Engine
from . import GlobalConstants as GC
from . import StateMachine, Dialogue, MenuFunctions

commands = []

class DebugState(StateMachine.State):
    num_back = 4

    def begin(self, gameStateObj, metaDataObj):
        # Draw Debug Commands onto screen
        self.current_command = ''
        self.buffer_count = 0

        self.dialogue_scene = Dialogue.Dialogue_Scene(None)

    def take_input(self, eventList, gameStateObj, metaDataObj):
        gameStateObj.input_manager.process_input(eventList)
        gameStateObj.cursor.take_input(eventList, gameStateObj)
        for event in eventList:
            if event.type == Engine.KEYDOWN:
                if event.key == Engine.key_map['enter']:
                    self.parse_command(self.current_command, gameStateObj)
                    if self.current_command != 'q' and self.current_command != 'exit':
                        commands.append(self.current_command)
                    self.current_command = ''
                    self.buffer_count = 0
                elif event.key == Engine.key_map['backspace']:
                    self.current_command = self.current_command[:-1]
                elif event.key == Engine.key_map['up'] and Engine.get_pressed()[Engine.key_map['ctrl']] and commands:
                    self.buffer_count += 1
                    self.current_command = commands[-self.buffer_count]
                else:
                    self.current_command += event.unicode

    def parse_command(self, command, gameStateObj):
        gameStateObj.cursor.currentHoveredUnit = [unit for unit in gameStateObj.allunits if unit.position == gameStateObj.cursor.position]
        if gameStateObj.cursor.currentHoveredUnit:
            gameStateObj.cursor.currentHoveredUnit = gameStateObj.cursor.currentHoveredUnit[0]
            cur_unit = gameStateObj.cursor.currentHoveredUnit
        else:
            cur_unit = None
        split_command = command.split(';')
        if split_command[0] == 'exit' or split_command[0] == 'q' or split_command[0] == '':
            gameStateObj.stateMachine.back()
        elif split_command[0] == 'damage':
            if cur_unit:
                cur_unit.change_hp(-int(split_command[1]))
        elif split_command[0] == 'wexp':
            if cur_unit:
                cur_unit.increase_wexp(int(split_command[1]), gameStateObj)
        elif split_command[0] == 'charge_skills':
            if cur_unit:
                for skill in cur_unit.status_effects:
                    if skill.activated_item_mod:
                        skill.activated_item_mod.set_to_max()
                    if skill.charged_status:
                        skill.charged_status.set_to_max()
        elif split_command[0] == 'win_game':
            gameStateObj.statedict['levelIsComplete'] = 'win'
            gameStateObj.message.append(Dialogue.Dialogue_Scene('Data/seizeScript.txt'))
            gameStateObj.stateMachine.changeState('dialogue')
        elif split_command[0] == 'lose_game':
            gameStateObj.statedict['levelIsComplete'] = 'loss'
            gameStateObj.message.append(Dialogue.Dialogue_Scene('Data/escapeScript.txt'))
            gameStateObj.stateMachine.changeState('dialogue')
        else:  # Dialog command
            if cur_unit:
                self.dialogue_scene.unit = cur_unit
            self.dialogue_scene.tile_pos = gameStateObj.cursor.position
            try:
                self.dialogue_scene.parse_line(split_command, gameStateObj)
            except Exception as e:
                print(e)

    def draw(self, gameStateObj, metaDataObj):
        mapSurf = StateMachine.State.draw(self, gameStateObj, metaDataObj)
        mapSurf.blit(GC.IMAGESDICT['DebugBackground'], (0, GC.WINHEIGHT - (5 * 16)))
        for idx, command in enumerate(reversed(commands[-self.num_back:])):
            # GC.FONT['text_blue'].blit(command, mapSurf, (0, GC.WINHEIGHT - idx * 16 - 32))
            MenuFunctions.OutlineFont(GC.BASICFONT, command, mapSurf, GC.COLORDICT['off_white'], GC.COLORDICT['off_black'], (0, GC.WINHEIGHT - idx * 16 - 32))
        # GC.FONT['text_blue'].blit(self.current_command, mapSurf, (0, GC.WINHEIGHT - 16))
        MenuFunctions.OutlineFont(GC.BASICFONT, self.current_command, mapSurf, GC.COLORDICT['off_white'], GC.COLORDICT['off_black'], (0, GC.WINHEIGHT - 16))
        return mapSurf
