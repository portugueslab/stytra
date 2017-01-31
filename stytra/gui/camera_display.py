from PyQt5.QtCore import QTimer, Qt, QRectF
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QWidget
import pyqtgraph as pg
from queue import Empty
import numpy as np

class CameraDisplayWidget(pg.GraphicsLayoutWidget):
    def __init__(self, camera_queue):
        super().__init__()
        self.display_area = pg.ViewBox()
        self.addItem(self.display_area)
        self.display_area.setRange(QRectF(0, 0, 640, 480), update=True,
                                   disableAutoRange=True)
        self.image_item = pg.ImageItem()
        self.display_area.addItem(self.image_item)
        self.timer = QTimer()
        self.timer.start(0)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.update_image)
        self.camera_queue = camera_queue
        self.update_image()


    def update_image(self):
        try:
            self.image_item.setImage(self.camera_queue.get(timeout=1))
        except Empty:
            self.timer.timeout.disconnect()
            self.timer.stop()


class CameraTailSelection(CameraDisplayWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = pg.TextItem('Select tail of the fish:\n' +
                                 'left click start, right click end')
        self.roi_tail = pg.LineSegmentROI(((320, 480), (320, 0)),
                                          pen=dict(color=(250, 10, 10),width=4))
        self.display_area.addItem(self.roi_tail)

    def get_tail_coords(self):
        return self.roi_tail.listPoints()


if __name__=='__main__':
    from multiprocessing import Queue
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    q = Queue()
    for i in range(100):
        q.put(np.random.randint(0, 255, (640, 480), dtype=np.uint8))

    w = CameraTailSelection(q)
    w.show()
    app.exec_()