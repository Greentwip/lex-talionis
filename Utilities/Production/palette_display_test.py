import sys
from PyQt4 import QtGui, QtCore

class ColorDisplay(QtGui.QPushButton):
    colorChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(ColorDisplay, self).__init__(parent)
        self._color = None
        self.setMaximumHeight(16)
        self.setMaximumWidth(16)
        self.pressed.connect(self.onColorPicker)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit()

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
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.RightButton:
            self.setColor(None)

        return super(ColorDisplay, self).mousePressEvent(e)

class PaletteDisplay(QtGui.QWidget):
    def __init__(self, colors, window=None):
        super(PaletteDisplay, self).__init__(window)
        self.window = window

        self.colors = colors

        self.layout = QtGui.QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        for color in self.colors:
            color_display = ColorDisplay(self)
            color_display.setColor(color)
            self.layout.addWidget(color_display, 0, QtCore.Qt.AlignTop)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    colors = [QtGui.QColor("red").name(), QtGui.QColor("blue").name(), QtGui.QColor("green").name()]*4
    window = PaletteDisplay(colors)
    window.show()
    app.exec_()
