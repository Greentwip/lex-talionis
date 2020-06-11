from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QDialog, QGridLayout, QComboBox, \
    QSpinBox, QPushButton
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, qRgb, qRgba

COLORKEY = (128, 160, 128)

class ImageView(QGraphicsView):
    def __init__(self, window=None):
        QGraphicsView.__init__(self)
        self.window = window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setFixedSize(240, 160)
        # self.fitInView(0, 0, 240, 160, Qt.KeepAspectRatio)

        self.image = QImage(240, 160, QImage.Format_ARGB32)
        self.screen_scale = 1

        # self.image_counter = 0

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.image:
            self.clear_scene()
            # bg = QImage(240, 160, QImage.Format_ARGB32)
            # self.scene.addPixmap(QPixmap.fromImage(bg))
            self.scene.addPixmap(QPixmap.fromImage(self.image))

    def new_frame(self, frame, offset):
        self.image = QImage(240, 160, QImage.Format_ARGB32)
        self.image.fill(QColor(128, 160, 128))
        painter = QPainter()
        painter.begin(self.image)
        painter.drawImage(offset[0], offset[1], frame.copy())  # Draw image on top of autotiles
        painter.end()
        # self.image = f
        # self.image.paste(QImage(frame), offset)
        self.setSceneRect(0, 0, 240, 160)
        # self.image.save('image_%d.png' % self.image_counter)
        # self.image_counter += 1
        self.show_image()

    def new_over_frame(self, frame, offset):
        painter = QPainter()
        painter.begin(self.image)
        painter.drawImage(offset[0], offset[1], frame.copy())  # Draw image on top of autotiles
        painter.end()
        self.show_image()

class Animator(QDialog):
    def __init__(self, image, index, script, window=None):
        super(Animator, self).__init__(window)
        self.setWindowTitle('View Animations')

        self.grid = QGridLayout()
        self.setLayout(self.grid)

        self.image = image
        self.index = index
        self.script = script
        self.current_index = 0

        self.script_index = 0
        self.num_frames = 0

        self.playing = False

        self.view = ImageView()
        self.grid.addWidget(self.view, 0, 0, 1, 3)

        self.pose_box = QComboBox()
        self.pose_box.uniformItemSizes = True
        self.pose_box.activated.connect(self.current_pose_changed)
        self.grid.addWidget(self.pose_box, 1, 0)

        self.fps_box = QSpinBox(self)
        self.fps_box.setSuffix(' fps')
        self.fps_box.setValue(30)
        self.fps_box.setMaximum(60)
        self.fps_box.setMinimum(1)
        self.fps_box.valueChanged.connect(self.change_fps)
        self.grid.addWidget(self.fps_box, 1, 1)

        self.play_button = QPushButton('Play')
        # self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play)
        self.grid.addWidget(self.play_button, 1, 2)

        self.populate()

        for pose in self.poses:
            self.pose_box.addItem(pose)
        self.current_pose = str(self.pose_box.currentText())

        # === Timing ===
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.change_timer_speed(30)
        self.main_timer.start()

    def change_timer_speed(self, fps):
        self.timer_speed = int(1000/float(fps))
        self.main_timer.setInterval(self.timer_speed)

    def change_fps(self, val):
        self.change_timer_speed(val)

    def populate(self):
        self.frames = {}
        for line in self.index:
            x, y = tuple([int(i) for i in line[1].split(',')])
            width, height = tuple([int(i) for i in line[2].split(',')])
            offset = tuple([int(i) for i in line[3].split(',')])
            crop = self.image.copy(x, y, width, height)

            qCOLORKEY = qRgb(*COLORKEY)
            new_color = qRgba(0, 0, 0, 0)
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
        self.playing = False
        self.play_button.setEnabled(True)
        self.script_index = 0

    def tick(self):
        # print(self.playing, self.num_frames)
        if self.playing:
            self.num_frames -= 1
            self.num_frames = max(0, self.num_frames)
            self.read_script()
        else:  # Display standing anim by default
            self.num_frames = 0
            self.read_script('Stand')

    def read_script(self, pose=None):
        script = self.poses[pose] if pose else self.poses[self.current_pose]
        while self.script_index < len(script) and self.num_frames <= 0:
            line = script[self.script_index]
            #print(line)
            self.parse_line(line)
            self.script_index += 1
            if self.script_index >= len(script):
                self.playing = False
                self.play_button.setEnabled(True)
                self.script_index = 0
                break

    def parse_line(self, line):
        if line[0] == 'f' or line[0] == 'of':
            self.num_frames = int(line[1])
            frame, offset = self.frames.get(line[2])
            if len(line) > 3:
                under_frame, under_offset = self.frames.get(line[3])
                self.view.new_frame(under_frame, under_offset)
                self.view.new_over_frame(frame, offset)
            else:
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
