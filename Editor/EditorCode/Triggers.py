from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QInputDialog, QListWidgetItem

from EditorCode.CustomGUI import SignalList

class TriggerMenu(QWidget):
    def __init__(self, unit_data, view, window=None):
        super(TriggerMenu, self).__init__(window)
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.window = window
        self.view = view

        self.list = SignalList(self, del_func=self.remove_trigger)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True

        self.unit_data = unit_data
        self.load(unit_data)

        self.arrow = None

        self.add_trigger_button = QPushButton('Add Trigger')
        self.add_trigger_button.clicked.connect(self.add_trigger)
        self.remove_trigger_button = QPushButton('Remove Trigger')
        self.remove_trigger_button.clicked.connect(self.remove_trigger)

        self.grid.addWidget(self.list, 0, 0)
        self.grid.addWidget(self.add_trigger_button, 1, 0)
        self.grid.addWidget(self.remove_trigger_button, 2, 0)

    def add_trigger(self):
        trigger, ok = QInputDialog.getText(self, "New Trigger", 'Enter name of new move trigger:')
        if ok:
            item = QListWidgetItem(trigger)
            self.list.addItem(item)
            self.unit_data.add_trigger(trigger)
            self.list.scrollToBottom()
            self.list.setCurrentItem(item)

    def remove_trigger(self):
        idx = self.list.currentRow()
        self.list.takeItem(idx)
        self.unit_data.remove_trigger(idx)

    def get_current_trigger(self):
        if self.unit_data.triggers:
            return self.unit_data.get_trigger(self.list.currentRow())
        return None

    def get_current_trigger_name(self):
        if self.unit_data.triggers:
            return self.unit_data.get_trigger_name(self.list.currentRow())

    def get_current_arrow(self):
        return self.arrow

    def set_current_arrow(self, unit, pos):
        self.arrow = unit, pos

    def clear_current_arrow(self):
        self.arrow = None

    def load(self, unit_data):
        self.clear()
        self.unit_data = unit_data
        # Ingest Data
        for trigger_name in self.unit_data.triggers:
            item = QListWidgetItem(trigger_name)
            self.list.addItem(item)

    def clear(self):
        self.list.clear()
        self.clear_current_arrow()
