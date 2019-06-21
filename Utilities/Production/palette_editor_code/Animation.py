from PyQt4 import QtGui, QtCore
COLORKEY = (128, 160, 128)

class ImageView(QtGui.QGraphicsView):
    def __init__(self, window=None):
        QtGui.QGraphicsView.__init__(self)
        self.window = window
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)
        self.setFixedSize(240, 160)
        # self.fitInView(0, 0, 240, 160, QtCore.Qt.KeepAspectRatio)

        self.image = QtGui.QImage(240, 160, QtGui.QImage.Format_ARGB32)
        self.screen_scale = 1

        # self.image_counter = 0

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.image:
            self.clear_scene()
            # bg = QtGui.QImage(240, 160, QtGui.QImage.Format_ARGB32)
            # self.scene.addPixmap(QtGui.QPixmap.fromImage(bg))
            self.scene.addPixmap(QtGui.QPixmap.fromImage(self.image))

    def new_frame(self, frame, offset):
        self.image = QtGui.QImage(240, 160, QtGui.QImage.Format_ARGB32)
        self.image.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter()
        painter.begin(self.image)
        painter.drawImage(offset[0], offset[1], frame.copy())  # Draw image on top of autotiles
        painter.end()
        # self.image = f
        # self.image.paste(QtGui.QImage(frame), offset)
        self.setSceneRect(0, 0, 240, 160)
        # self.image.save('image_%d.png' % self.image_counter)
        # self.image_counter += 1
        self.show_image()

class Animator(QtGui.QDialog):
    def __init__(self, image, index, script, window=None):
        super(Animator, self).__init__(window)
        self.setWindowTitle('View Animations')

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.image = image
        self.index = index
        self.script = script
        self.current_index = 0

        self.script_index = 0
        self.num_frames = 0

        self.playing = False

        self.view = ImageView()
        self.grid.addWidget(self.view, 0, 0, 1, 2)

        self.pose_box = QtGui.QComboBox()
        self.pose_box.uniformItemSizes = True
        self.pose_box.activated.connect(self.current_pose_changed)
        self.grid.addWidget(self.pose_box, 1, 0)

        self.play_button = QtGui.QPushButton('Play')
        # self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play)
        self.grid.addWidget(self.play_button, 1, 1)

        self.populate()

        for pose in self.poses:
            self.pose_box.addItem(pose)
        self.current_pose = str(self.pose_box.currentText())

        # === Timing ===
        self.main_timer = QtCore.QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.main_timer.start(200)  # 30 FPS  # TODO Fix

    def populate(self):
        self.frames = {}
        for line in self.index:
            x, y = tuple([int(i) for i in line[1].split(',')])
            width, height = tuple([int(i) for i in line[2].split(',')])
            offset = tuple([int(i) for i in line[3].split(',')])
            crop = self.image.copy(x, y, width, height)

            qCOLORKEY = QtGui.qRgb(*COLORKEY)
            new_color = QtGui.qRgba(0, 0, 0, 0)
            for x in range(crop.width()):
                for y in range(crop.height()):
                    if crop.pixel(x, y) == qCOLORKEY:
                        crop.setPixel(x, y, new_color)

            print(crop.width(), crop.height(), offset)
            self.frames[line[0]] = (crop, offset)

        self.poses = {}
        self.current_pose = None
        for line in self.script:
            if line[0] == 'pose':
                self.current_pose = line[1]
                self.poses[self.current_pose] = []
            else:
                self.poses[self.current_pose].append(line)

    def current_pose_changed(self, pose):
        self.current_pose = str(self.pose_box.currentText())

    def tick(self):
        print(self.playing, self.num_frames)
        if self.playing:
            self.num_frames -= 1
            self.num_frames = max(0, self.num_frames)
            self.read_script()

    def read_script(self):
        script = self.poses[self.current_pose]
        while self.script_index < len(script) and self.num_frames <= 0:
            line = script[self.script_index]
            print(line)
            self.parse_line(line)
            self.script_index += 1
            if self.script_index >= len(script):
                self.playing = False
                self.play_button.setEnabled(True)
                self.script_index = 0
                break

    def parse_line(self, line):
        if line[0] == 'f':
            self.num_frames = int(line[1])
            frame, offset = self.frames.get(line[2])
            self.view.new_frame(frame, offset)
        elif line[0] == 'of':
            self.num_frames = int(line[1])
            frame, offset = self.frames.get(line[2])
            self.view.new_frame(frame, offset)
        elif line[0] == 'uf':
            self.num_frames = int(line[1])
            frame, offset = self.frames.get(line[2])
            self.view.new_frame(frame, offset)

    def play(self):
        self.playing = True
        self.play_button.setEnabled(False)

    @classmethod
    def get_dialog(cls, image, index, script):
        dialog = cls(image, index, script)
        dialog.exec_()
        return True