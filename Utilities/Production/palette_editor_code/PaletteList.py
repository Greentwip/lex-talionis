from PyQt4 import QtGui, QtCore

class ColorDisplay(QtGui.QPushButton):
    colorChanged = QtCore.pyqtSignal(int, QtGui.QColor)

    def __init__(self, idx, window):
        super(ColorDisplay, self).__init__(window)
        self.window = window
        self.idx = idx
        self._color = None

        self.setMinimumHeight(16)
        self.setMaximumHeight(16)
        self.setMinimumWidth(16)
        self.setMaximumWidth(16)
        self.resize(16, 16)
        self.pressed.connect(self.onColorPicker)

    def set_color(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(self.idx, QtGui.QColor(color))

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        dlg = QtGui.QColorDialog()
        if self._color:
            dlg.setCurrentColor(QtGui.QColor(self._color))
        if dlg.exec_():
            self.set_color(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.RightButton:
            self.set_color(QtGui.QColor("black").name())

        return super(ColorDisplay, self).mousePressEvent(e)

class PaletteDisplay(QtGui.QWidget):
    def __init__(self, colors, window):
        super(PaletteDisplay, self).__init__(window)
        self.window = window
        self.main_editor = self.window.window.window

        self.color_display_list = []

        self.layout = QtGui.QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        for idx, color in enumerate(colors):
            color_display = ColorDisplay(idx, self)
            color_display.set_color(color.name())
            color_display.colorChanged.connect(self.on_color_change)
            self.layout.addWidget(color_display, 0, QtCore.Qt.AlignCenter)
            self.color_display_list.append(color_display)

    def set_color(self, idx, color):
        self.color_display_list[idx].set_color(color.name())

    def on_color_change(self, idx, color):
        self.main_editor.update_view()

class PaletteFrame(QtGui.QWidget):
    def __init__(self, idx, image_filename=None, window=None):
        super(PaletteFrame, self).__init__(window)
        self.window = window

        self.idx = idx
        if image_filename:
            self.name = image_filename[:-4].split('-')[-1]
            palette = self.get_palette_from_image(image_filename)

            self.create_widgets(palette)

    def create_widgets(self, palette):
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)

        radio_button = QtGui.QRadioButton()
        self.window.radio_button_group.addButton(radio_button, self.idx)
        radio_button.clicked.connect(lambda: self.window.set_current_palette(self.idx))
        self.name_label = QtGui.QLabel(self.name)
        copy = QtGui.QPushButton("Duplicate")
        copy.clicked.connect(lambda: self.window.duplicate(self.idx))
        self.palette_display = PaletteDisplay(palette, self)
        layout.addWidget(radio_button)
        layout.addWidget(self.name_label)
        layout.addWidget(self.palette_display)
        layout.addWidget(copy)

    def get_colors(self):
        return [color_display.color() for color_display in self.palette_display.color_display_list]

    def set_name(self, name):
        self.name = name
        self.name_label.setText(name)

    def set_color(self, idx, color):
        self.palette_display.set_color(idx, color)

    def get_palette_from_image(self, fn):
        colors = []
        pixmap = QtGui.QPixmap(fn)
        image = pixmap.toImage()
        for x in range(image.width()):
            for y in range(image.height()):
                color = QtGui.QColor(image.pixel(x, y))
                if color not in colors:
                    colors.append(color)
        return colors

    @classmethod
    def from_palette(cls, new_idx, palette_frame, window):
        p = cls(new_idx, None, window)
        p.name = palette_frame.name
        color_list = [QtGui.QColor(c) for c in palette_frame.get_colors()]
        p.create_widgets(color_list)
        return p

class PaletteList(QtGui.QListWidget):
    def __init__(self, window=None):
        super(PaletteList, self).__init__(window)
        self.window = window
        self.uniformItemSizes = True

        self.list = []
        self.current_index = 0
        self.radio_button_group = QtGui.QButtonGroup()

    def add_palette_from_image(self, image_filename):
        print(image_filename)
        item = QtGui.QListWidgetItem(self)
        self.addItem(item)
        pf = PaletteFrame(len(self.list), image_filename, self)
        self.list.append(pf)
        item.setSizeHint(pf.minimumSizeHint())
        self.setItemWidget(item, pf)
        # Try and make it the right size
        self.setMinimumWidth(self.sizeHintForColumn(0))
        return pf

    def remove_last_palette(self):
        print('Removing last palette!')
        self.takeItem(len(self.list) - 1)
        self.list.pop()

    def duplicate(self, idx):
        new_idx = len(self.list)
        item = QtGui.QListWidgetItem(self)
        self.addItem(item)
        new_pf = PaletteFrame.from_palette(new_idx, self.list[idx], self)
        self.list.append(new_pf)
        item.setSizeHint(new_pf.minimumSizeHint())
        self.setItemWidget(item, new_pf)

    def set_current_palette(self, idx):
        self.current_index = idx
        self.radio_button_group.button(idx).setChecked(True)
        self.window.palette_text.setText(self.get_current_palette().name)
        self.window.update_view()

    def get_current_palette(self):
        return self.list[self.current_index]

    def get_last_palette(self):
        return self.list[-1]

    def get_palette(self, idx):
        return self.list[idx]

    def clear(self):
        for idx, l in enumerate(self.list):
            self.takeItem(idx)
            l.deleteLater()
        self.list = []
        self.current_index = 0
        print(len(self.list))
