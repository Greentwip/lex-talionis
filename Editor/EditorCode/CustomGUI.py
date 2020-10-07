# Custom GUI widgets
import os, shutil
from PyQt5.QtWidgets import QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtWidgets import QWidget, QErrorMessage, QSpinBox, QListWidget, QListWidgetItem, QAbstractItemView
from PyQt5.QtWidgets import QComboBox, QGroupBox, QRadioButton, QHBoxLayout
from PyQt5.QtWidgets import QButtonGroup
from PyQt5.QtGui import QImage, QStandardItemModel
from PyQt5.QtCore import Qt, pyqtSignal, QDir

class MusicBox(QWidget):
    def __init__(self, label, music='', window=None):
        super(MusicBox, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.label = QLabel(label)
        self.txt = QLineEdit(music)
        self.button = QPushButton('...')
        self.button.clicked.connect(self.change)

        self.grid.addWidget(self.label, 0, 0)
        self.grid.addWidget(self.txt, 0, 1)
        self.grid.addWidget(self.button, 0, 2)

    def change(self):
        starting_path = QDir.currentPath() + '/../Audio/music'
        print(starting_path)
        music_file, _ = QFileDialog.getOpenFileName(self, "Select Music File", starting_path,
                                                    "OGG Files (*.ogg);;All Files (*)")
        if music_file:
            music_file = str(music_file)
            starting_path = str(starting_path)
            head, tail = os.path.split(music_file)
            print(head)
            if os.path.normpath(head) != os.path.normpath(starting_path):
                print('Copying ' + music_file + ' to ' + starting_path)
                if os.path.isdir(starting_path):
                    shutil.copy(music_file, starting_path)
                else:
                    print("Error! %s is not a directory or does not exist!" % starting_path)
            self.setText(tail.split('.')[0])

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class ImageBox(QWidget):
    def __init__(self, label, image='', window=None):
        super(ImageBox, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.label = QLabel(label)
        self.txt = QLineEdit(image)
        self.button = QPushButton('...')
        self.button.clicked.connect(self.change)

        self.grid.addWidget(self.label, 0, 0)
        self.grid.addWidget(self.txt, 0, 1)
        self.grid.addWidget(self.button, 0, 2)

    def change(self):
        starting_path = QDir.currentPath() + '/../Sprites/General/Panoramas'
        print(starting_path)
        image_file, _ = QFileDialog.getOpenFileName(self, "Select Image File", starting_path,
                                                       "PNG Files (*.png);;All Files (*)")
        if image_file:
            image = QImage(image_file)
            if image.width() != 240 or image.height() != 160:
                QErrorMessage().showMessage("Image chosen is not 240 pixels wide by 160 pixels high!")
                return
            image_file = str(image_file)
            starting_path = str(starting_path)
            head, tail = os.path.split(image_file)
            print(head)
            if os.path.normpath(head) != os.path.normpath(starting_path):
                print('Copying ' + image_file + ' to ' + starting_path)
                shutil.copy(image_file, starting_path)
            self.setText(tail.split('.')[0])

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class StringBox(QWidget):
    def __init__(self, label, text='', max_length=None, window=None):
        super(StringBox, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        label = QLabel(label)
        self.grid.addWidget(label, 0, 0)
        self.txt = QLineEdit(text)
        if max_length:
            self.txt.setMaxLength(max_length)
        self.grid.addWidget(self.txt, 0, 1)

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class IntBox(QWidget):
    def __init__(self, label, window=None):
        super(IntBox, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        label = QLabel(label)
        self.grid.addWidget(label, 0, 0)
        self.txt = QSpinBox()
        self.grid.addWidget(self.txt, 0, 1)

    def setMinimum(self, i):
        self.txt.setMinimum(i)

    def setMaximum(self, i):
        self.txt.setMaximum(i)

    def value(self):
        return self.txt.value()

    def setValue(self, i):
        self.txt.setValue(i)

class SignalList(QListWidget):
    def __init__(self, parent=None, del_func=None):
        super(SignalList, self).__init__()
        self.parent = parent
        self.del_func = del_func
    #     self.currentItemChanged.connect(self.trigger)
    #     self.itemActivated.connect(self.trigger)

    # def trigger(self, *args, **kwargs):
    #     self.parent.trigger()

    def keyPressEvent(self, event):
        super(SignalList, self).keyPressEvent(event)
        if self.del_func and event.key() == Qt.Key_Delete:
            self.del_func()

class DragAndDropSignalList(SignalList):
    itemMoved = pyqtSignal(int, int, QListWidgetItem)

    def __init__(self, parent=None, del_func=None):
        super(DragAndDropSignalList, self).__init__(parent, del_func)

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.drag_item = None
        self.drag_row = None

    def dropEvent(self, event):
        super(DragAndDropSignalList, self).dropEvent(event)
        self.itemMoved.emit(self.drag_row, self.row(self.drag_item), self.drag_item)
        self.drag_item = None

    def startDrag(self, supportedActions):
        self.drag_item = self.currentItem()
        self.drag_row = self.row(self.drag_item)
        super(DragAndDropSignalList, self).startDrag(supportedActions)

class CheckableComboBox(QComboBox):
    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)

class GenderBox(QGroupBox):
    def __init__(self, window=None):
        super(GenderBox, self).__init__()
        self.window = window

        self.radios = (QRadioButton("Male:"), QRadioButton("Female:"))
        self.radios[0].setChecked(True)
        self.gender = 0

        hbox = QHBoxLayout()

        self.gender_buttons = QButtonGroup()
        for idx, radio in enumerate(self.radios):
            hbox.addWidget(radio)
            self.gender_buttons.addButton(radio, idx)
            radio.clicked.connect(self.radio_button_clicked)

        self.setLayout(hbox)

    def radio_button_clicked(self):
        self.gender = int(self.gender_buttons.checkedId()) * 5
        if self.window:
            self.window.gender_changed(self.gender)

    def value(self):
        return self.gender

    def setValue(self, value):
        self.radios[0].setChecked(not value)
        self.radios[1].setChecked(value)
