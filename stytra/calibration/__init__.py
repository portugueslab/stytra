from PyQt5.QtCore import QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
import math


def paint_cross(p, h, w, dw):
    p.setPen(QPen(QColor(255, 0, 0)))
    p.drawRect(QRect(1, 1, w - 2, h - 2))
    p.drawLine(w // 4, h // 2, w * 3 // 4, h // 2)
    p.drawLine(w // 2, h * 3 // 4, w // 2, h // 4)
    p.drawLine(w // 2, h * 3 // 4, w // 2, h // 4)
    p.drawLine(w // 2, h * 3 // 4, w * 3 // 4, h * 3 // 4)


def paint_circles(p, h, w, dh=100, r=5):
    assert isinstance(p, QPainter)
    p.setPen(QPen(QColor(255, 0, 0)))
    dw = int(dh*math.sqrt(3))
    ch = h//2
    cw = w//2
    centres = [(cw-dw//2, ch+dh//2), (cw+dw//2, ch+dh//2),
               (cw - dw // 2, ch - dh // 2)]
    print(centres)
    p.setBrush(QBrush(QColor(255, 0, 0)))
    for centre in centres:
        p.drawEllipse(QPoint(*centre), r, r)
