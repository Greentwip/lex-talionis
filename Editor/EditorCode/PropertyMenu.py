from collections import OrderedDict

from PyQt5.QtWidgets import QGridLayout, QDialog, QWidget, QCheckBox, QPushButton
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

from . import CustomGUI as LtGui
from . import EditorUtilities

class MusicDialog(QDialog):
    def __init__(self, parent):
        super(MusicDialog, self).__init__(parent)
        music_grid = QGridLayout(self)
        music_grid.setVerticalSpacing(0)

        self.player_music = LtGui.MusicBox('Player Phase Music')
        music_grid.addWidget(self.player_music, 1, 0)
        self.enemy_music = LtGui.MusicBox('Enemy Phase Music')
        music_grid.addWidget(self.enemy_music, 2, 0)
        self.other_music = LtGui.MusicBox('Other Phase Music')
        music_grid.addWidget(self.other_music, 3, 0)
        self.player_battle_music = LtGui.MusicBox('Player Battle Music')
        music_grid.addWidget(self.player_battle_music, 4, 0)
        self.enemy_battle_music = LtGui.MusicBox('Enemy Battle Music')
        music_grid.addWidget(self.enemy_battle_music, 5, 0)

    def load(self, music_text):
        self.player_music.setText(music_text[0])
        self.enemy_music.setText(music_text[1])
        self.other_music.setText(music_text[2])
        self.player_battle_music.setText(music_text[3])
        self.enemy_battle_music.setText(music_text[4])

    def save(self):
        overview = {}
        overview['player_music'] = self.player_music.text()
        overview['enemy_music'] = self.enemy_music.text()
        overview['other_music'] = self.other_music.text()
        overview['player_battle_music'] = self.player_battle_music.text()
        overview['enemy_battle_music'] = self.enemy_battle_music.text()
        return overview

    @staticmethod
    def editMusic(parent, music_text):
        dialog = MusicDialog(parent)
        dialog.load(music_text)
        dialog.setWindowTitle('Set Chapter Music')
        result = dialog.exec_()
        return dialog.save(), True

class PropertyMenu(QWidget):
    def __init__(self, window=None):
        super(PropertyMenu, self).__init__(window)
        self.grid = QGridLayout()
        # self.grid.setVerticalSpacing(1)
        self.setLayout(self.grid)
        self.window = window

        self.name = LtGui.StringBox('Chapter Name')
        self.grid.addWidget(self.name, 0, 0)

        self.party = LtGui.IntBox('Chapter Party')
        self.party.setMinimum(0)
        self.party.setMaximum(15)
        self.grid.addWidget(self.party, 1, 0)

        self.prep = QCheckBox('Show Prep Menu?')
        self.grid.addWidget(self.prep, 2, 0)

        self.prep_music = LtGui.MusicBox('Prep Music')
        self.grid.addWidget(self.prep_music, 3, 0)

        self.pick = QCheckBox('Allow Pick Units?')
        self.grid.addWidget(self.pick, 4, 0)

        self.prep.stateChanged.connect(self.prep_enable)

        self.base = QCheckBox('Show Base Menu?')
        self.grid.addWidget(self.base, 5, 0)

        self.base_music = LtGui.MusicBox('Base Music')
        self.grid.addWidget(self.base_music, 6, 0)

        self.base_bg = LtGui.ImageBox('Base Image')
        self.grid.addWidget(self.base_bg, 7, 0)

        self.base.stateChanged.connect(self.base_enable)

        self.market = QCheckBox('Allow Prep/Base Market?')
        self.grid.addWidget(self.market, 8, 0)

        self.transition = QCheckBox('Show Chpt. Transition?')
        self.grid.addWidget(self.transition, 9, 0)

        EditorUtilities.add_line(self.grid, 10)
        self.music_button = QPushButton('Phase Music')
        self.music_button.clicked.connect(self.edit_music)
        self.grid.addWidget(self.music_button, 11, 0)
        EditorUtilities.add_line(self.grid, 12)

        self.create_weather(13)
        EditorUtilities.add_line(self.grid, 15)
        self.create_objective(16)

        self.update()

        self.new()

    def edit_music(self):
        music, ok = MusicDialog.editMusic(self, (self.player_music, self.enemy_music, self.other_music, self.player_battle_music, self.enemy_battle_music))
        if ok:
            self.player_music = music['player_music']
            self.enemy_music = music['enemy_music']
            self.other_music = music['other_music']
            self.player_battle_music = music['player_battle_music']
            self.enemy_battle_music = music['enemy_battle_music']

    def create_weather(self, row):
        grid = QGridLayout()
        weather = QLabel('Weather')
        grid.addWidget(weather, 1, 0)

        self.weathers = ('Light', 'Dark', 'Rain', 'Sand', 'Snow', 'Fire')
        # This stupidity is necessary for some reason
        self.functions = (self.light_check, self.dark_check, self.rain_check, self.sand_check, self.snow_check, self.fire_check)
        self.weather_boxes = []
        for idx, weather in enumerate(self.weathers):
            label = QLabel(weather)
            grid.addWidget(label, 0, idx + 1, alignment=Qt.AlignHCenter)
            check_box = QCheckBox()
            check_box.stateChanged.connect(self.functions[idx])
            grid.addWidget(check_box, 1, idx + 1, alignment=Qt.AlignHCenter)
            self.weather_boxes.append(check_box)

        self.grid.addLayout(grid, row, 0, 2, 1)

    def weather_check(self, idx):
        if self.weather_boxes[idx].isChecked():
            self.window.add_weather(self.weathers[idx])
        else:
            self.window.remove_weather(self.weathers[idx])

    def light_check(self): self.weather_check(0)
    def dark_check(self): self.weather_check(1)
    def rain_check(self): self.weather_check(2)
    def sand_check(self): self.weather_check(3)
    def snow_check(self): self.weather_check(4)
    def fire_check(self): self.weather_check(5)

    def create_objective(self, row):
        label = QLabel('WIN CONDITION')
        self.grid.addWidget(label, row, 0, alignment=Qt.AlignHCenter)

        self.simple_display = LtGui.StringBox('Simple Display')
        self.grid.addWidget(self.simple_display, row + 1, 0)

        self.win_condition = LtGui.StringBox('Win Condition')
        self.grid.addWidget(self.win_condition, row + 2, 0)

        self.loss_condition = LtGui.StringBox('Loss Condition')
        self.grid.addWidget(self.loss_condition, row + 3, 0)

    def prep_enable(self, b):
        self.prep_music.setEnabled(b)
        self.pick.setEnabled(b)

    def base_enable(self, b):
        self.base_music.setEnabled(b)
        self.base_bg.setEnabled(b)

    def get_weather_strings(self):
        return [w for i, w in enumerate(self.weathers) if self.weather_boxes[i].isChecked()]

    def update(self):
        self.prep_enable(self.prep.isChecked())
        self.base_enable(self.base.isChecked())

    def new(self):
        self.name.setText('Example Name')
        self.party.setValue(0)
        self.prep.setChecked(False)
        self.base.setChecked(False)
        self.market.setChecked(False)
        self.transition.setChecked(True)
        self.prep_music.setText('')
        self.pick.setChecked(True)
        self.base_music.setText('')
        self.base_bg.setText('')

        self.player_music = ''
        self.enemy_music = ''
        self.other_music = ''
        self.player_battle_music = ''
        self.enemy_battle_music = ''

        for box in self.weather_boxes:
            box.setChecked(False)

        self.simple_display.setText('Defeat Boss')
        self.win_condition.setText('Defeat Boss')
        self.loss_condition.setText('Lord dies,OR,Party size falls below 5. Currently {gameStateObj.get_total_party_members()}')

    def load(self, overview):
        self.name.setText(overview['name'])
        self.party.setValue(int(overview.get('current_party', 0)))
        self.prep.setChecked(bool(int(overview['prep_flag'])))
        self.base.setChecked(overview['base_flag'] != '0')
        self.market.setChecked(bool(int(overview['market_flag'])))
        self.transition.setChecked(bool(int(overview['transition_flag'])))
        self.prep_music.setText(overview.get('prep_music', '') if self.prep.isChecked() else '')
        self.pick.setChecked(bool(int(overview['pick_flag'])))
        self.base_music.setText(overview.get('base_music', '') if self.base.isChecked() else '')
        self.base_bg.setText(overview.get('base_flag', '') if self.base.isChecked() else '')

        self.player_music = overview.get('player_phase_music', '')
        self.enemy_music = overview.get('enemy_phase_music', '')
        self.other_music = overview.get('other_phase_music', '')
        self.player_battle_music = overview.get('player_battle_music', '')
        self.enemy_battle_music = overview.get('enemy_battle_music', '')

        weather = overview['weather'].split(',') if 'weather' in overview else []
        for box in self.weather_boxes:
            box.setChecked(False)
        for name in weather:
            if name in self.weathers:
                idx = self.weathers.index(name)
                print(name)
                self.weather_boxes[idx].setChecked(True)

        self.simple_display.setText(overview['display_name'])
        self.win_condition.setText(overview['win_condition'])
        self.loss_condition.setText(overview['loss_condition'])

    def save(self):
        overview = OrderedDict()
        overview['name'] = self.name.text()
        overview['current_party'] = str(self.party.value())
        overview['prep_flag'] = '1' if self.prep.isChecked() else '0'
        overview['prep_music'] = self.prep_music.text()
        overview['pick_flag'] = '1' if self.pick.isChecked() else '0'
        overview['base_flag'] = self.base_bg.text() if self.base.isChecked() else '0'
        overview['base_music'] = self.base_music.text()
        overview['market_flag'] = '1' if self.market.isChecked() else '0'
        overview['transition_flag'] = '1' if self.transition.isChecked() else '0'

        overview['player_phase_music'] = self.player_music
        overview['enemy_phase_music'] = self.enemy_music
        overview['other_phase_music'] = self.other_music
        overview['player_battle_music'] = self.player_battle_music
        overview['enemy_battle_music'] = self.enemy_battle_music
        
        overview['display_name'] = self.simple_display.text()
        overview['win_condition'] = self.win_condition.text()
        overview['loss_condition'] = self.loss_condition.text()

        overview['weather'] = ','.join(self.get_weather_strings())

        return overview
