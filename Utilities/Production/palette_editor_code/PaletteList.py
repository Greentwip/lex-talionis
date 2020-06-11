from PyQt5.QtWidgets import QColorDialog, QPushButton, QWidget, QHBoxLayout, QRadioButton, \
    QLabel, QListWidget, QButtonGroup, QListWidgetItem, QUndoCommand
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap

class ColorDisplay(QPushButton):
    colorChanged = pyqtSignal(int, QColor)

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

    def set_color(self, color, create=False):
        if create:
            self.change_color(color)
        else:
            palette_list = self.window.window.window
            command = CommandColorChange(
                palette_list, self.window.window.idx, self.idx, color, 
                "%d: Changing Color from %s to %s" % (self.idx, self._color, color))
            self.window.main_editor.undo_stack.push(command)

    def change_color(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(self.idx, QColor(color))

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        dlg = QColorDialog()
        if self._color:
            dlg.setCurrentColor(QColor(self._color))
        if dlg.exec_():
            self.set_color(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.set_color(QColor("black").name())

        return super(ColorDisplay, self).mousePressEvent(e)

class PaletteDisplay(QWidget):
    def __init__(self, colors, window):
        super(PaletteDisplay, self).__init__(window)
        self.window = window
        self.main_editor = self.window.window.window

        self.color_display_list = []

        self.layout = QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        for idx, color in enumerate(colors):
            color_display = ColorDisplay(idx, self)
            color_display.set_color(color.name(), create=True)
            color_display.colorChanged.connect(self.on_color_change)
            self.layout.addWidget(color_display, 0, Qt.AlignCenter)
            self.color_display_list.append(color_display)

    def set_color(self, idx, color):
        self.color_display_list[idx].set_color(color.name())

    def on_color_change(self, idx, color):
        self.main_editor.update_view()

class PaletteFrame(QWidget):
    def __init__(self, idx, image_filename=None, image_map=None, window=None):
        super(PaletteFrame, self).__init__(window)
        self.window = window

        self.idx = idx
        if image_filename and image_map:
            self.name = image_filename[:-4].split('-')[-1]
            palette = self.get_palette_from_image(image_filename, image_map)

            self.create_widgets(palette)

    def create_widgets(self, palette):
        layout = QHBoxLayout()
        self.setLayout(layout)

        radio_button = QRadioButton()
        self.window.radio_button_group.addButton(radio_button, self.idx)
        radio_button.clicked.connect(lambda: self.window.set_current_palette(self.idx))
        self.name_label = QLabel(self.name)
        copy = QPushButton("Duplicate")
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

    def get_color_display(self, idx):
        return self.palette_display.color_display_list[idx]

    def get_color(self, idx):
        return self.palette_display.color_display_list[idx].color()

    def set_color(self, idx, color):
        self.palette_display.set_color(idx, color)

    def get_palette_from_image(self, fn, image_map):
        colors = []
        pixmap = QPixmap(fn)
        image = pixmap.toImage()
        colors = [QColor("black")] * 16
        for x in range(image.width()):
            for y in range(image.height()):
                grid_index = image_map.get(x, y)
                color = QColor(image.pixel(x, y))
                while grid_index > len(colors) - 1:
                    colors.append(QColor("black"))  # Sometimes more than 16 colors
                # if color != colors[grid_index]:
                #     print(grid_index, colors[grid_index].getRgb(), color.getRgb())
                colors[grid_index] = color
        # Make sure there are always at least 16 colors
        # print(len(colors))
        # colors.extend([QColor("black")] * (16 - len(colors)))

        return colors

    @classmethod
    def from_palette(cls, new_idx, palette_frame, window):
        p = cls(new_idx, None, None, window)
        p.name = palette_frame.name
        color_list = [QColor(c) for c in palette_frame.get_colors()]
        p.create_widgets(color_list)
        return p

class PaletteList(QListWidget):
    def __init__(self, window=None):
        super(PaletteList, self).__init__(window)
        self.window = window
        self.uniformItemSizes = True

        self.list = []
        self.current_index = 0
        self.radio_button_group = QButtonGroup()

    def add_palette_from_image(self, image_filename, image_map):
        print(image_filename)
        item = QListWidgetItem(self)
        self.addItem(item)
        pf = PaletteFrame(len(self.list), image_filename, image_map, self)
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
        command = CommandDuplicate(self, idx, "Duplicate Palette %d" % idx)
        self.window.undo_stack.push(command)

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
        print('PaletteList clear')
        # Need to remove things in reverse order, duh
        for idx, l in reversed(list(enumerate(self.list))):
            print(idx)
            self.takeItem(idx)
            l.deleteLater()
        self.list = []
        self.current_index = 0

class CommandDuplicate(QUndoCommand):
    def __init__(self, palette_list, idx, description):
        super(CommandDuplicate, self).__init__(description)
        self.palette_list = palette_list
        self.old_idx = palette_list.current_index
        self.idx = idx

    def redo(self):
        new_idx = len(self.palette_list.list)
        item = QListWidgetItem(self.palette_list)
        self.palette_list.addItem(item)
        new_pf = PaletteFrame.from_palette(new_idx, self.palette_list.list[self.idx], self.palette_list)
        self.palette_list.list.append(new_pf)
        item.setSizeHint(new_pf.minimumSizeHint())
        self.palette_list.setItemWidget(item, new_pf)

    def undo(self):
        # Delete last item
        self.palette_list.takeItem(self.palette_list.count() - 1)
        self.palette_list.list.pop()
        self.palette_list.set_current_palette(self.old_idx)

class CommandColorChange(QUndoCommand):
    def __init__(self, palette_list, palette_idx, color_idx, new_color, description):
        super(CommandColorChange, self).__init__(description)
        self.palette_list = palette_list
        self.palette_idx = palette_idx
        self.color_idx = color_idx
        self.old_color = self.palette_list.get_palette(palette_idx).get_color(color_idx)
        self.new_color = new_color

    def change_color(self, color):
        color_display = self.palette_list.get_palette(self.palette_idx).get_color_display(self.color_idx)
        color_display.change_color(color)

    def redo(self):
        self.change_color(self.new_color)

    def undo(self):
        self.change_color(self.old_color)
