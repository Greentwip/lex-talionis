from PyQt4 import QtGui
import sys
sys.path.append('../')
import Code.Engine as Engine
import Code.imagesDict as images

class ImageWidget(QtGui.QWidget):
    def __init__(self, surface, parent=None):
        super(ImageWidget, self).__init__(parent)
        w = surface.get_width()
        h = surface.get_height()
        self.data = surface.get_buffer().raw
        self.image = QtGui.QImage(self.data, w, h, QtGui.QImage.Format_RGB32)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.drawImage(0, 0, self.image)
        qp.end()

class MainWindow(QtGui.QMainWindow):
    def __init__(self, surface, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setCentralWidget(ImageWidget(surface))

Engine.simple_init()
# Display creation is necessary to use convert and convert alpha
surf = Engine.build_display((240, 160))
IMAGESDICT, UNITDICT, ICONDICT, ITEMDICT, ANIMDICT = images.getImages(home='../')
Engine.remove_display()

surf = Engine.create_surface((640, 480))
Engine.fill(surf, (64, 128, 192, 224))
Engine.blit(surf, IMAGESDICT['Clearing'], (0, 0))

app = QtGui.QApplication(sys.argv)
window = MainWindow(surf)

def b1_clicked():
    print("Button 1 clicked")

b1 = QtGui.QPushButton(window)
b1.setText("Button1")
b1.move(50, 20)
b1.clicked.connect(b1_clicked)

window.setGeometry(100, 100, 640, 480)
window.show()
app.exec_()
