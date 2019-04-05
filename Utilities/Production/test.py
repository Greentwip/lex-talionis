from PyQt4 import QtCore, QtGui

class ColorListEditor(QtGui.QComboBox):
    def __init__(self, parent):
        QtGui.QComboBox.__init__(self, parent)
        self.populateList()

    def getColor(self):
        return self.itemData(self.currentIndex(),
                             QtCore.Qt.DecorationRole).toPyObject()

    def setColor(self, color):
        self.setCurrentIndex(self.findData(QtCore.QVariant(color),
                             QtCore.Qt.DecorationRole))

    color = QtCore.pyqtProperty('QColor', getColor, setColor, user=True)

    def populateList(self):
        for i, name in enumerate(QtGui.QColor.colorNames()):
            self.insertItem(i, name)
            self.setItemData(i, QtCore.QVariant(QtGui.QColor(name)),
                             QtCore.Qt.DecorationRole)

class ColorListCreator(QtGui.QItemEditorCreatorBase):
    def __init__(self):
        QtGui.QItemEditorCreatorBase.__init__(self)

    def createWidget(self, parent):
        return ColorListEditor(parent)

class Window(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        factory = QtGui.QItemEditorFactory()
        colorListCreator = ColorListCreator()
        factory.registerEditor(QtCore.QVariant.Color, colorListCreator)
        QtGui.QItemEditorFactory.setDefaultFactory(factory)
        self.createGUI()

    def createGUI(self):
        data = ((self.tr('Alice'), QtGui.QColor('aliceblue')),
                (self.tr('Neptun'), QtGui.QColor('aquamarine')),
                (self.tr('Ferdinand'), QtGui.QColor('springgreen')))
        table = QtGui.QTableWidget(3, 2)
        table.setHorizontalHeaderLabels(QtCore.QStringList()
                                        << self.tr('Name')
                                        << self.tr('Hair Color'))
        table.verticalHeader().setVisible(False)
        table.resize(150, 50)
        for i, (name, color) in enumerate(data):
            nameItem = QtGui.QTableWidgetItem(name)
            colorItem = QtGui.QTableWidgetItem()
            colorItem.setData(QtCore.Qt.DisplayRole,
                              QtCore.QVariant(color))
            table.setItem(i, 0, nameItem)
            table.setItem(i, 1, colorItem)
        table.resizeColumnToContents(0)
        table.horizontalHeader().setStretchLastSection(True)
        layout = QtGui.QGridLayout()
        layout.addWidget(table, 0, 0)
        self.setLayout(layout)
        self.setWindowTitle(self.tr('Color Editor Factory'))


if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
