from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen

import numpy as np


class FramerateWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.framerate_queues = dict()

    def paintEvent(self, e):
        size = self.size()
        pad = 10
        w = size.width()
        h = size.height()

        framerates = np.array([15, 17.5, 19.2, 15.5])

        min_bound = int(np.floor(np.min(framerates) / 10)) * 10
        max_bound = int(np.ceil(np.max(framerates) / 10)) * 10

        fps = framerates[-1]
        loc = (fps - min_bound) / (max_bound - min_bound)

        indicator_color = (230, 40, 0)
        limit_color = (30, 30, 30)

        p = QPainter()
        p.begin(self)
        w_min = pad
        w_max = w - pad
        text_height = 10
        h_max = h - pad
        h_min = text_height + pad
        p.setPen(QPen(QColor(*limit_color)))
        p.drawLine(w_min, h_min, w_min, h_max)
        p.drawLine(w_max, h_min, w_max, h_max)

        # Draw the indicator line
        p.setPen(QPen(QColor(*indicator_color)))
        w_l = int(w_min + loc * (w_max - w_min))
        p.drawLine(w_l, h_min - 5, w_l, h_max)

        p.drawText(QPoint(w_min, pad), str(min_bound))
        fm = p.fontMetrics()
        maxst = str(max_bound)
        textw = fm.width(maxst)
        p.drawText(QPoint(w_max - textw, pad), maxst)


# if __name__ == "__main__":
#     from PyQt5.QtWidgets import QApplication
#     app = QApplication([])
#     w = FramerateWidget()
#     w.show()
#     app.exec_()
