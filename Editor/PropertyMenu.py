from collections import OrderedDict

from PyQt4 import QtGui, QtCore

import CustomGUI as LtGui
import EditorUtilities

class PropertyMenu(QtGui.QWidget):
    def __init__(self, window=None):
        super(PropertyMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        # self.grid.setVerticalSpacing(1)
        self.setLayout(self.grid)
        self.window = window

        self.name = LtGui.StringBox('Chapter Name')
        self.grid.addWidget(self.name, 0, 0)

        self.prep = QtGui.QCheckBox('Show Prep Menu?')
        self.grid.addWidget(self.prep, 1, 0)

        self.prep_music = LtGui.MusicBox('Prep Music')
        self.grid.addWidget(self.prep_music, 2, 0)

        self.pick = QtGui.QCheckBox('Allow Pick Units?')
        self.grid.addWidget(self.pick, 3, 0)

        self.prep.stateChanged.connect(self.prep_enable)

        self.base = QtGui.QCheckBox('Show Base Menu?')
        self.grid.addWidget(self.base, 4, 0)

        self.base_music = LtGui.MusicBox('Base Music')
        self.grid.addWidget(self.base_music, 5, 0)

        self.base_bg = LtGui.ImageBox('Base Image')
        self.grid.addWidget(self.base_bg, 6, 0)

        self.base.stateChanged.connect(self.base_enable)

        self.market = QtGui.QCheckBox('Allow Prep/Base Market?')
        self.grid.addWidget(self.market, 7, 0)

        self.transition = QtGui.QCheckBox('Show Chpt. Transition?')
        self.grid.addWidget(self.transition, 8, 0)

        # Main music
        music_grid = QtGui.QGridLayout()
        self.grid.addLayout(music_grid, 10, 0)
        music_grid.setVerticalSpacing(0)

        EditorUtilities.add_line(music_grid, 0)
        self.player_music = LtGui.MusicBox('Player Phase Music')
        music_grid.addWidget(self.player_music, 1, 0)
        self.enemy_music = LtGui.MusicBox('Enemy Phase Music')
        music_grid.addWidget(self.enemy_music, 2, 0)
        self.other_music = LtGui.MusicBox('Other Phase Music')
        music_grid.addWidget(self.other_music, 3, 0)
        EditorUtilities.add_line(music_grid, 4)

        self.create_weather(12)
        EditorUtilities.add_line(self.grid, 14)
        self.create_objective(15)

        self.update()

    def create_weather(self, row):
        grid = QtGui.QGridLayout()
        weather = QtGui.QLabel('Weather')
        grid.addWidget(weather, 1, 0)

        self.weathers = ('Light', 'Dark', 'Rain', 'Sand', 'Snow')
        self.weather_boxes = []
        for idx, weather in enumerate(self.weathers):
            label = QtGui.QLabel(weather)
            grid.addWidget(label, 0, idx + 1, alignment=QtCore.Qt.AlignHCenter)
            check_box = QtGui.QCheckBox()
            grid.addWidget(check_box, 1, idx + 1, alignment=QtCore.Qt.AlignHCenter)
            self.weather_boxes.append(check_box)

        self.grid.addLayout(grid, row, 0, 2, 1)

    def create_objective(self, row):
        label = QtGui.QLabel('WIN CONDITION')
        self.grid.addWidget(label, row, 0, alignment=QtCore.Qt.AlignHCenter)

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

    def update(self):
        self.prep_enable(self.prep.isChecked())
        self.base_enable(self.base.isChecked())

    def new(self):
        self.name.setText('Example Name')
        self.prep.setChecked(False)
        self.base.setChecked(False)
        self.market.setChecked(False)
        self.transition.setChecked(True)
        self.player_music.setText('')
        self.enemy_music.setText('')
        self.other_music.setText('')
        self.prep_music.setText('')
        self.pick.setChecked(True)
        self.base_music.setText('')
        self.base_bg.setText('')

        for box in self.weather_boxes:
            box.setChecked(False)

        self.simple_display.setText('Defeat Boss')
        self.win_condition.setText('Defeat Boss')
        self.loss_condition.setText('Lord dies,OR,Party size falls below 5. Currently {gameStateObj.get_total_party_members()}')

    def load(self, overview):
        self.name.setText(overview['name'])
        self.prep.setChecked(bool(int(overview['prep_flag'])))
        self.base.setChecked(overview['base_flag'] != '0')
        self.market.setChecked(bool(int(overview['market_flag'])))
        self.transition.setChecked(bool(int(overview['transition_flag'])))
        self.player_music.setText(overview['player_phase_music'])
        self.enemy_music.setText(overview['enemy_phase_music'])
        self.other_music.setText(overview['other_phase_music'] if 'other_phase_music' in overview else '')
        self.prep_music.setText(overview['prep_music'] if self.prep.isChecked() else '')
        self.pick.setChecked(bool(int(overview['pick_flag'])))
        self.base_music.setText(overview['base_music'] if self.base.isChecked() else '')
        self.base_bg.setText(overview['base_flag'] if self.base.isChecked() else '')

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
        overview['prep_flag'] = '1' if self.prep.isChecked() else '0'
        overview['prep_music'] = self.prep_music.text()
        overview['pick_flag'] = '1' if self.pick.isChecked() else '0'
        overview['base_flag'] = self.base_bg.text() if self.base.isChecked() else '0'
        overview['base_music'] = self.base_music.text()
        overview['market_flag'] = '1' if self.market.isChecked() else '0'
        overview['transition_flag'] = '1' if self.transition.isChecked() else '0'
        
        overview['display_name'] = self.simple_display.text()
        overview['win_condition'] = self.win_condition.text()
        overview['loss_condition'] = self.loss_condition.text()

        overview['player_phase_music'] = self.player_music.text()
        overview['enemy_phase_music'] = self.enemy_music.text()
        overview['other_phase_music'] = self.other_music.text()

        overview['weather'] = ','.join([w for i, w in enumerate(self.weathers) if self.weather_boxes[i].isChecked()])

        return overview
