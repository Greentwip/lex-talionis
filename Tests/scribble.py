# Scribble.py

from PyQt5 import QtGui, QtCore

class ScribbleArea(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ScribbleArea, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_StaticContents)
        self.modified = False
        self.scribbling = False
        self.my_pen_width = 1
        self.my_pen_color = QtCore.Qt.blue
        self.image = QtGui.QImage()
        self.last_point = QtCore.QPoint()

    def open_image(self, file_name):
        loaded_image = QtGui.QImage()
        if not loaded_image.load(file_name):
            return False

        new_size = loaded_image.size().expandedTo(self.size())
        self.resize_image(loaded_image, new_size)
        self.modified = False
        self.update()
        return True

    def save_image(self, file_name, file_format):
        visible_image = self.image
        self.resize_image(visible_image, self.size())

        if visible_image.save(file_name, file_format):
            self.modified = False
            return True
        else:
            return False

    def set_pen_color(self, new_color):
        self.my_pen_color = new_color

    def set_pen_width(self, new_width):
        self.my_pen_width = new_width

    def clear_image(self):
        self.image.fill(QtGui.qRgb(255, 255, 255))
        self.modified = True
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.last_point = event.pos()
            self.scribbling = True

    def mouseMoveEvent(self, event):
        if (event.buttons() & QtCore.Qt.LeftButton) and self.scribbling:
            self.draw_line_to(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.scribbling:
            self.draw_line_to(event.pos())
            self.scribbling = False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        dirty_rect = event.rect()
        painter.drawImage(dirty_rect, self.image, dirty_rect)

    def resizeEvent(self, event):
        if self.width() > self.image.width() or self.height() > self.image.height():
            new_width = max(self.width() + 128, self.image.width())
            new_height = max(self.height() + 128, self.image.height())
            self.resize_image(self.image, QtCore.QSize(new_width, new_height))
            self.update()

        super(ScribbleArea, self).resizeEvent(event)

    def draw_line_to(self, end_point):
        painter = QtGui.QPainter(self.image)
        painter.setPen(QtGui.QPen(self.my_pen_color, self.my_pen_width, QtCore.Qt.SolidLine,
                                  QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(self.last_point, end_point)
        self.modified = True

        rad = self.my_pen_width / 2 + 2
        self.update(QtCore.QRect(self.last_point, end_point).normalized().adjusted(-rad, -rad, +rad, +rad))
        self.last_point = QtCore.QPoint(end_point)

    def resize_image(self, image, new_size):
        print(image.size(), new_size)
        if image.size() == new_size:
            self.image = image
            return

        new_image = QtGui.QImage(new_size, QtGui.QImage.Format_RGB32)
        new_image.fill(QtGui.qRgb(255, 255, 255))
        painter = QtGui.QPainter(new_image)
        painter.drawImage(QtCore.QPoint(0, 0), image)
        self.image = new_image

    def print_(self):
        printer = QtGui.QPrinter(QtGui.QPrinter.HighResolution)

        print_dialog = QtGui.QPrintDialog(printer, self)
        if print_dialog.exec_() == QtGui.QPrintDialog.Accepted:
            painter = QtGui.QPainter(printer)
            rect = painter.viewport()
            size = self.image.size()
            size.scale(rect.size(), QtCore.Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.image.rect())
            painter.drawImage(0, 0, self.image)
            painter.end()

    def isModified(self):
        return self.modified

    def pen_color(self):
        return self.my_pen_color

    def pen_width(self):
        return self.my_pen_width

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.save_as_acts = []

        self.scribble_area = ScribbleArea()
        self.setCentralWidget(self.scribble_area)

        self.create_actions()
        self.create_menus()

        self.setWindowTitle("Scribble")
        self.resize(500, 500)

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def open(self):
        if self.maybe_save():
            file_name = QtGui.QFileDialog.getOpenFileName(self, "Open File", QtCore.QDir.currentPath())
            if file_name:
                self.scribble_area.open_image(file_name)

    def save(self):
        action = self.sender()
        file_format = action.data().toString()
        self.save_file(file_format)

    def pen_color(self):
        new_color = QtGui.QColorDialog.getColor(self.scribble_area.pen_color())
        if new_color.isValid():
            self.scribble_area.set_pen_color(new_color)

    def pen_width(self):
        new_width, ok = QtGui.QInputDialog.getInt(self, "Scribble", "Select pen width:", 
                                                  self.scribble_area.pen_width(), 1, 50, 1)
        if ok:
            self.scribble_area.set_pen_width(new_width)

    def about(self):
        QtGui.QMessageBox.about(self, "About Scribble",
            "<p>The <b>Scribble</b> example shows how to use "
            "QMainWindow as the base widget for an application, and how "
            "to reimplement some of QWidget's event handlers to receive "
            "the events generated for the application's widgets:</p>"
            "<p> We reimplement the mouse event handlers to facilitate "
            "drawing, the paint event handler to update the application "
            "and the resize event handler to optimize the application's "
            "appearance. In addition we reimplement the close event "
            "handler to intercept the close events before terminating "
            "the application.</p>"
            "<p> The example also demonstrates how to use QPainter to "
            "draw an image in real time, as well as to repaint "
            "widgets.</p>")

    def create_actions(self):
        self.open_act = QtGui.QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)

        for kind in QtGui.QImageWriter.supportedImageFormats():
            kind = str(kind)

            text = kind.upper() + "..."

            action = QtGui.QAction(text, self, triggered=self.save)
            action.setData(kind)
            self.save_as_acts.append(action)

        self.print_act = QtGui.QAction("&Print...", self, triggered=self.scribble_area.print_)

        self.exit_act = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)

        self.pen_color_act = QtGui.QAction("&Pen Color...", self, triggered=self.pen_color)

        self.pen_width_act = QtGui.QAction("Pen &Width", self, triggered=self.pen_width)

        self.clear_screen_act = QtGui.QAction("&Clear Screen", self, shortcut="Ctrl-L", triggered=self.scribble_area.clear_image)

        self.about_act = QtGui.QAction("&About", self, triggered=self.about)

        self.about_qt_act = QtGui.QAction("About &Qt", self, triggered=QtGui.QApplication.instance().aboutQt)

    def create_menus(self):
        self.save_as_menu = QtGui.QMenu("&Save As", self)
        for action in self.save_as_acts:
            self.save_as_menu.addAction(action)

        file_menu = QtGui.QMenu("&File", self)
        file_menu.addAction(self.open_act)
        file_menu.addMenu(self.save_as_menu)
        file_menu.addAction(self.print_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        option_menu = QtGui.QMenu("&Options", self)
        option_menu.addAction(self.pen_color_act)
        option_menu.addAction(self.pen_width_act)
        option_menu.addSeparator()
        option_menu.addAction(self.clear_screen_act)

        help_menu = QtGui.QMenu("&Help", self)
        help_menu.addAction(self.about_act)
        help_menu.addAction(self.about_qt_act)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(option_menu)
        self.menuBar().addMenu(help_menu)

    def maybe_save(self):
        if self.scribble_area.isModified():
            ret = QtGui.QMessageBox.warning(self, "Scribble", "The image has been modified.\n"
                                            "Do you want to save your changes?",
                                            QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)

            if ret == QtGui.QMessageBox.Save:
                return self.save_file('png')
            elif ret == QtGui.QMessageBox.Cancel:
                return False

        return True

    def save_file(self, file_format):
        initial_path = QtCore.QDir.currentPath() + '/untitled.' + file_format

        file_name = QtGui.QFileDialog.getSaveFileName(self, "Save As", initial_path,
            "%s Files (*.%s);;All Files (*)" % (file_format.upper(), file_format))
        if file_name:
            return self.scribble_area.save_image(file_name, file_format)

        return False

if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

