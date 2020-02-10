from PyQt5.QtWidgets import QComboBox, QLineEdit, QListWidget, QListWidgetItem, \
    QCheckBox
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import pyqtSignal

"""
Converted to PyQt from https://github.com/ThisIsClark/Qt-MultiSelectComboBox
"""

class MultiSelectComboBox(QComboBox):
    search_bar_index = 0

    updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.list_widget = QListWidget(self)
        self.line_edit = QLineEdit(self)
        self.search_bar = QLineEdit(self)

        current_item = QListWidgetItem(self.list_widget)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setClearButtonEnabled(True)
        # First item in the list is the SEARCH BAR
        self.list_widget.addItem(current_item)
        self.list_widget.setItemWidget(current_item, self.search_bar)

        self.line_edit.setReadOnly(True)
        self.line_edit.installEventFilter(self)

        self.setModel(self.list_widget.model())
        self.setView(self.list_widget)
        self.setLineEdit(self.line_edit)

        self.search_bar.textChanged.connect(self.onSearch)
        self.activated.connect(self.itemClicked)

    def hidePopup(self):
        width = self.width()
        height = self.list_widget.height()
        x = QCursor.pos().x() - self.mapToGlobal(self.geometry().topLeft()).x() + self.geometry().x()
        y = QCursor.pos().y() - self.mapToGlobal(self.geometry().topLeft()).y() + self.geometry().y()

        if x >= 0 and x <= width and y >= self.height() and y <= height + self.height():
            pass # Item was clicked do not hide popup
        else:
            super().hidePopup()

    def stateChanged(self, state=None):
        # state is unused
        selected_data = []
        count = self.list_widget.count()

        for i in range(1, count):
            check_box = self.list_widget.itemWidget(self.list_widget.item(i))
            if check_box.isChecked():
                selected_data.append(check_box.text())

        if selected_data:
            self.line_edit.setText(', '.join(selected_data))
        else:
            self.line_edit.clear()
        self.updated.emit()

    def addItem(self, text, user_data=None):
        # user_data is unused
        list_widget_item = QListWidgetItem(self.list_widget)
        check_box = QCheckBox(self)
        check_box.setText(text)
        self.list_widget.addItem(list_widget_item)
        self.list_widget.setItemWidget(list_widget_item, check_box)
        check_box.stateChanged.connect(self.stateChanged)

    def currentText(self):
        if self.line_edit.text():
            return [_.strip() for _ in self.line_edit.text().split(",")]
        return []

    def addItems(self, texts):
        for s in texts:
            self.addItem(s)

    def count(self):
        return max(0, self.list_widget.count() - 1)  # Do not count the search bar

    def onSearch(self, s):
        for i in range(self.list_widget.count()):
            check_box = self.list_widget.itemWidget(self.list_widget.item(i))
            if s.lower() in check_box.text().lower():
                self.list_widget.item(i).setHidden(False)
            else:
                self.list_widget.item(i).setHidden(True)

    def itemClicked(self, index):
        if index != self.search_bar_index:
            check_box = self.list_widget.itemWidget(self.list_widget.item(index))
            check_box.setChecked(not check_box.isChecked())

    def setSearchBarPlaceholderText(self, placeholder_text):
        self.search_bar.setPlaceholderText(placeholder_text)

    def setPlaceholderText(self, placeholder_text):
        self.line_edit.setPlaceholderText(placeholder_text)

    def clear(self):
        self.list_widget.clear()
        current_item = QListWidgetItem(self.list_widget)
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setClearButtonEnabled(True)
        self.list_widget.addItem(current_item)
        self.list_widget.setItemWidget(current_item, self.search_bar)

        self.search_bar.textChanged.connect(self.onSearch)

    def wheelEvent(self, wheel_event):
        pass  # Do not handle the wheel event

    def setCurrentText(self, text):
        pass

    def setCurrentTexts(self, texts):
        count = self.list_widget.count()

        for i in range(1, count):
            check_box = self.list_widget.itemWidget(self.list_widget.item(i))
            check_box_string = check_box.text()
            if check_box_string in texts:
                check_box.setChecked(True)

    def ResetSelection(self):
        count = self.list_widget.count()

        for i in range(1, count):
            check_box = self.list_widget.itemWidget(self.list_widget.item(i))
            check_box.setChecked(False)


# Testing
# Run "python -m app.editor.multi_select_combo_box" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog
    app = QApplication(sys.argv)

    class BasicDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            layout = QHBoxLayout(self)
            self.setLayout(layout)

            widget = MultiSelectComboBox()
            widget.addItem("Japan")
            widget.addItem("China")
            widget.addItem("Korea")
            layout.addWidget(widget)

    window = BasicDialog()
    window.show()
    app.exec_()
