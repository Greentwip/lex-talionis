# Custom GUI widgets
import os, shutil
from PyQt4 import QtGui, QtCore

class MusicBox(QtGui.QWidget):
    def __init__(self, label, music='', window=None):
        super(MusicBox, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.label = QtGui.QLabel(label)
        self.txt = QtGui.QLineEdit(music)
        self.button = QtGui.QPushButton('...')
        self.button.clicked.connect(self.change)

        self.grid.addWidget(self.label, 0, 0)
        self.grid.addWidget(self.txt, 0, 1)
        self.grid.addWidget(self.button, 0, 2)

    def change(self):
        starting_path = QtCore.QDir.currentPath() + '/../Audio/music'
        print(starting_path)
        music_file = QtGui.QFileDialog.getOpenFileName(self, "Select Music File", starting_path,
                                                       "OGG Files (*.ogg);;All Files (*)")
        if music_file:
            music_file = str(music_file)
            starting_path = str(starting_path)
            head, tail = os.path.split(music_file)
            print(head)
            if os.path.normpath(head) != os.path.normpath(starting_path):
                print('Copying ' + music_file + ' to ' + starting_path)
                shutil.copy(music_file, starting_path)
            self.text.setText(tail.split('.')[0])

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class ImageBox(QtGui.QWidget):
    def __init__(self, label, image='', window=None):
        super(ImageBox, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        self.label = QtGui.QLabel(label)
        self.txt = QtGui.QLineEdit(image)
        self.button = QtGui.QPushButton('...')
        self.button.clicked.connect(self.change)

        self.grid.addWidget(self.label, 0, 0)
        self.grid.addWidget(self.txt, 0, 1)
        self.grid.addWidget(self.button, 0, 2)

    def change(self):
        starting_path = QtCore.QDir.currentPath() + '/../Sprites/General/Panoramas'
        print(starting_path)
        image_file = QtGui.QFileDialog.getOpenFileName(self, "Select Image File", starting_path,
                                                       "PNG Files (*.png);;All Files (*)")
        if image_file:
            image = QtGui.QImage(image_file)
            if image.width() != 240 or image.height() != 160:
                QtGui.QErrorMessage().showMessage("Image chosen is not 240 pixels wide by 160 pixels high!")
                return
            image_file = str(image_file)
            starting_path = str(starting_path)
            head, tail = os.path.split(image_file)
            print(head)
            if os.path.normpath(head) != os.path.normpath(starting_path):
                print('Copying ' + image_file + ' to ' + starting_path)
                shutil.copy(image_file, starting_path)
            self.text.setText(tail.split('.')[0])

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)

class StringBox(QtGui.QWidget):
    def __init__(self, label, text='', max_length=None, window=None):
        super(StringBox, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window

        label = QtGui.QLabel(label)
        self.grid.addWidget(label, 0, 0)
        self.txt = QtGui.QLineEdit(text)
        if max_length:
            self.txt.setMaxLength(max_length)
        self.grid.addWidget(self.txt, 0, 1)

    def text(self):
        return self.txt.text()

    def setText(self, text):
        self.txt.setText(text)
