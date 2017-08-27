from PyQt4 import QtGui
import sys
sys.path.append('../')
import Code.configuration as cf
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad

import Code.ItemMethods as ItemMethods
import Code.CustomObjects as CustomObjects
import Code.StatusObject as StatusObject

# === DATA IMPORTING ===
def build_units():
    units = []
    class_dict = SaveLoad.create_class_dict()
    for unit in GC.UNITDATA.getroot().findall('unit'):
        u_i = {}
        u_i['id'] = unit.find('id').text
        u_i['name'] = unit.get('name')

        classes = unit.find('class').text.split(',')
        u_i['klass'] = classes[-1]

        u_i['gender'] = unit.find('gender').text
        u_i['level'] = int(unit.find('level').text)
        u_i['faction'] = unit.find('faction').text

        stats = SaveLoad.intify_comma_list(unit.find('bases').text)
        for n in xrange(len(stats), cf.CONSTANTS['num_stats']):
            stats.append(class_dict[u_i['klass']]['bases'][n])
        assert len(stats) == cf.CONSTANTS['num_stats'], "bases %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])
        u_i['stats'] = SaveLoad.build_stat_dict(stats)
        # print("%s's stats: %s", u_i['name'], u_i['stats'])

        u_i['growths'] = SaveLoad.intify_comma_list(unit.find('growths').text)
        u_i['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(u_i['growths'])))
        assert len(u_i['growths']) == cf.CONSTANTS['num_stats'], "growths %s must be exactly %s integers long"%(stats, cf.CONSTANTS['num_stats'])

        u_i['items'] = ItemMethods.itemparser(unit.find('inventory').text)
        # Parse wexp
        u_i['wexp'] = unit.find('wexp').text.split(',')
        for index, wexp in enumerate(u_i['wexp'][:]):
            if wexp in CustomObjects.WEAPON_EXP.wexp_dict:
                u_i['wexp'][index] = CustomObjects.WEAPON_EXP.wexp_dict[wexp]
        u_i['wexp'] = [int(num) for num in u_i['wexp']]

        assert len(u_i['wexp']) == len(CustomObjects.WEAPON_TRIANGLE.types), "%s's wexp must have as many slots as there are weapon types."%(u_i['name'])
        
        u_i['desc'] = unit.find('desc').text
        # Tags
        u_i['tags'] = set(unit.find('tags').text.split(',')) if unit.find('tags') is not None and unit.find('tags').text is not None else set()

        # Personal Skills
        personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []
        u_i['skills'] = [StatusObject.statusparser(status) for status in personal_skills]

        units.append(Unit(u_i))
    return units

# === MODEL CLASS ===
class Unit(object):
    def __init__(self, info):
        self.id = info['id']
        self.name = info['name']

        self.level = int(info['level'])
        self.gender = info['gender']
        self.klass = info['klass']
        self.tags = info['tags']

        self.stats = info['stats']
        self.growths = info['growths']

        self.wexp = info['wexp']

        self.items = info['items']

        self.skills = info['skills']

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

# class MainWindow(QtGui.QMainWindow):
#     def __init__(self, surface, parent=None):
#         super(MainWindow, self).__init__(parent)
#         self.setCentralWidget(ImageWidget(surface))

# surf = Engine.create_surface((640, 480))
# Engine.fill(surf, (64, 128, 192, 224))
# Engine.blit(surf, IMAGESDICT['Clearing'], (0, 0))

if __name__ == '__main__':
    Engine.remove_display()
    units = build_units()

    app = QtGui.QApplication(sys.argv)
    window = QtGui.QMainWindow()
    window.setWindowTitle('Unit Editor')
    window.setMinimumSize(640, 480)

    unit_list = QtGui.QListView(window)
    unit_list.setMinimumSize(200, 480)
    model = QtGui.QStandardItemModel(unit_list)

    for unit in units:
        print(unit.name)
        item = QtGui.QStandardItem(unit.name)
        model.appendRow(item)

    # apply the model to the list view
    unit_list.setModel(model)
    # icon = ImageWidget(GC.IMAGESDICT['Clearing'])
    # icon = QtGui.QPixmap(icon.image)
    # icon = QtGui.QIcon(icon)
    # item.setIcon(icon)

    # window.setGeometry(100, 100, 640, 480)
    window.show()
    app.exec_()
