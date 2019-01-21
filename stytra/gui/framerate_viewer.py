from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtGui import QPainter, QColor, QPen
#from stytra.gui.multiscope import MultiStreamPlot

import numpy as np
from numba import jit

from datetime import datetime


@jit(nopython=True)
def framerate_limits(framerates, goal_framerate):
    ll = min(framerates[0], goal_framerate)
    ul = max(goal_framerate, framerates[0])
    for i, fr in enumerate(framerates):
        if fr < ll:
            ll = fr
        if fr > ul:
            ul = fr
    return ll, ul


class FramerateWidget(QWidget):
    def __init__(self, acc):
        super().__init__()
        self.acc = acc
        self.g_fps = self.acc.goal_framerate
        self.fps = self.g_fps
        self.set_fps = False

    def update(self):
        self.set_fps = False
        if len(self.acc.data) > 0:
            self.fps = self.acc.data[-1]
            self.set_fps = True

    def paintEvent(self, e):
        size = self.size()
        pad = 10
        w = size.width()
        h = size.height()

        p = QPainter()
        p.begin(self)

        min_bound = int(np.floor(min(self.fps, self.g_fps)*0.8 / 10)) * 10
        max_bound = int(np.ceil(max(self.fps, self.g_fps)*1.2 / 10)) * 10

        if max_bound == min_bound:
            max_bound += 1

        loc = (self.fps - min_bound) / (max_bound - min_bound)
        loc_g = (self.g_fps - min_bound) / (max_bound - min_bound)

        indicator_color = (230, 40, 0)
        limit_color = (200, 200, 200)
        goal_color = (210, 200, 10)

        w_min = pad
        w_max = w - pad
        text_height = 16
        h_max = h - pad
        h_min = text_height + pad

        if self.set_fps:
            # Draw the indicator line
            p.setPen(QPen(QColor(*indicator_color)))
            w_l = int(w_min + loc * (w_max - w_min))
            p.drawLine(w_l, h_min - 5, w_l, h_max)

        # Draw the goal line
        p.setPen(QPen(QColor(*goal_color), 2))
        w_l = int(w_min + loc_g * (w_max - w_min))
        p.drawLine(w_l, h_min - 5, w_l, h_max)

        # Draw the limits
        p.setPen(QPen(QColor(*limit_color)))
        p.drawLine(w_min, h_min, w_min, h_max)
        p.drawLine(w_max, h_min, w_max, h_max)

        p.drawText(QPoint(w_min, text_height), str(min_bound))
        fm = p.fontMetrics()
        maxst = str(max_bound)
        textw = fm.width(maxst)
        p.drawText(QPoint(w_max - textw, text_height), maxst)
        p.end()


class MultiFrameratesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.fr_widgets = []
        self.setLayout(QHBoxLayout())

    def update(self):
        for wid in self.fr_widgets:
            wid.update()

    def add_framerate(self, framerate_acc):
        lbl_name = QLabel(framerate_acc.name)
        fr_disp = FramerateWidget(framerate_acc)
        self.layout().addWidget(lbl_name)
        self.fr_widgets.append(fr_disp)
        self.layout().addWidget(fr_disp)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    w = FramerateWidget()
    w.show()
    app.exec_()