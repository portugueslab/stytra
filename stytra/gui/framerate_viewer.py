from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy, QSpacerItem
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt

import numpy as np


class FramerateWidget(QWidget):
    def __init__(self, acc, inertia=0.985):
        super().__init__()
        self.acc = acc
        self.g_fps = self.acc.goal_framerate
        self.fps = None
        self.fps_inertia_max = None
        self.fps_inertia_min = None
        self.inertia = inertia
        self.set_fps = False
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Expanding))
        self.indicator_color = (40, 230, 150)
        self.indicator_shadow_color = (17, 147, 91)
        self.error_indicator_color = (230, 40, 0)
        self.error_indicator_shadow_color = (170, 30, 0)

    def update(self):
        self.set_fps = False
        if len(self.acc.stored_data) > 0:
            self.fps = self.acc.stored_data[-1]
            self.set_fps = self.fps is not None
            if self.fps_inertia_max is None:
                self.fps_inertia_max = self.fps
                self.fps_inertia_min = self.fps
            else:
                if self.fps > self.fps_inertia_max:
                    self.fps_inertia_max = self.fps
                else:
                    self.fps_inertia_max = self.fps_inertia_max * self.inertia + self.fps * (1 - self.inertia)

                if self.fps < self.fps_inertia_min:
                    self.fps_inertia_min = self.fps
                else:
                    self.fps_inertia_min = self.fps_inertia_min * self.inertia + self.fps * (
                                1 - self.inertia)

        super().update()

    def paintEvent(self, e):
        # Three valid cases: there are both a goal and current framerate
        # or either of them
        if self.fps is not None:
            if self.g_fps is not None:
                lb = min(self.fps_inertia_min, self.g_fps)
                ub = max(self.fps_inertia_max, self.g_fps)
            else:
                lb = self.fps_inertia_min
                ub = self.fps_inertia_max
        else:
            if self.g_fps is not None:
                lb = self.g_fps
                ub = self.g_fps
            else:
                return

        min_bound = np.floor(lb*0.08)*10
        max_bound = np.ceil(ub*0.12)*10
        delta_bound = max_bound-min_bound

        size = self.size()
        pad = 6
        w = size.width()
        h = size.height()

        p = QPainter()
        p.begin(self)
        fm = p.fontMetrics()

        if max_bound == min_bound:
            max_bound += 1

        limit_color = (200, 200, 200)
        goal_color = (80, 80, 80)

        if self.fps is not None and self.g_fps is not None and self.fps < self.g_fps:
            indicator_color = self.error_indicator_color
            shadow_color = self.error_indicator_shadow_color
        else:
            indicator_color = self.indicator_color
            shadow_color = self.indicator_shadow_color

        w_min = 0
        w_max = w - pad
        delta_w = w_max-w_min
        text_height = 16
        h_max = h - pad
        h_min = text_height + pad

        if self.set_fps and self.fps is not None:
            loc = (self.fps - min_bound) / delta_bound
            w_l = int(w_min + loc * delta_w)

            w_shadow_min = int(w_min + (
                        self.fps_inertia_min - min_bound) * delta_w / delta_bound)
            w_shadow_max = int(w_min + (self.fps_inertia_max - min_bound) * delta_w / delta_bound)


            # Draw the inertially moving rectangle
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(*shadow_color)))

            l_corner = w_shadow_min
            w_rect = w_shadow_max-w_shadow_min
            p.drawRect(l_corner, h_min, w_rect, h_max-h_min)

            # Draw the indicator line
            p.setPen(QPen(QColor(*indicator_color)))

            p.drawLine(w_l, h_min, w_l, h_max+5)

            val_str = "{:.1f}".format(self.fps)
            textw = fm.width(val_str)

            p.drawText(QPoint((w_max + w_min-textw) // 2, text_height),
                       val_str)

        if self.g_fps is not None:
            # Draw the goal line
            loc_g = (self.g_fps - min_bound) / delta_bound
            p.setPen(QPen(QColor(*goal_color), 3))
            w_l = int(w_min + loc_g * delta_w)
            p.drawLine(w_l, h_min, w_l, h_max)

        # Draw the limits
        p.setPen(QPen(QColor(*limit_color)))
        p.drawLine(w_min, h_min, w_min, h_max)
        p.drawLine(w_max, h_min, w_max, h_max)

        p.drawText(QPoint(w_min, text_height), str(min_bound))
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
        if len(self.fr_widgets) > 0:
            self.layout().addItem(QSpacerItem(40, 10))
        self.layout().addWidget(lbl_name)
        self.fr_widgets.append(fr_disp)
        self.layout().addWidget(fr_disp)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    w = FramerateWidget()
    w.show()
    app.exec_()