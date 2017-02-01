from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
import pyqtgraph as pg
import json


class ProtocolControlWindow(QDialog):
    def __init__(self, app, protocol, display_window, *args):
        """ Class for controlling the stimuli
        """
        super().__init__(*args)
        self.app = app
        self.protocol = protocol
        self.display_window = display_window

        self.widget_view = pg.GraphicsLayoutWidget()
        self.window_mover = pg.ViewBox(invertY=True, lockAspect=1, enableMouse=False)
        self.widget_view.addItem(self.window_mover)

        try:
            ROI_desc = json.load(open('window_props.json', 'r'))
        except FileNotFoundError:
            ROI_desc = dict(pos=(10, 10), size=(100, 100))

        self.roi_box = pg.ROI(maxBounds=QRectF(0, 0, 1280, 800), **ROI_desc)
        self.roi_box.addScaleHandle([0, 0], [1, 1])
        self.roi_box.addScaleHandle([1, 1], [0, 0])
        self.window_mover.addItem(self.roi_box)

        self.window_mover.setRange(QRectF(0, 0, 1280, 800), update=True,
                                   disableAutoRange=True)

        self.button_update_display = QPushButton('Update display area')
        self.button_update_display.clicked.connect(self.update_ROI)

        self.button_calibrate = QPushButton('Show calibration')
        self.button_calibrate.clicked.connect(self.toggle_calibration)

        self.button_start = QPushButton('Start protocol')
        self.button_start.clicked.connect(self.protocol.start)

        self.button_end = QPushButton('End protocol')
        self.button_end.clicked.connect(self.protocol.end)

        self.button_metadata = QPushButton('Edit metadata')

        self.timer = None
        self.layout = QVBoxLayout()
        for widget in [self.widget_view, self.button_update_display,
                       self.button_calibrate, self.button_start,
                       self.button_end, self.button_metadata]:
            self.layout.addWidget(widget)

        self.setLayout(self.layout)

    def update_ROI(self):
        self.display_window.set_dims(self.roi_box)


    def closeEvent(self, QCloseEvent):
        """ On closing the app, save where the window was

        :param QCloseEvent:
        :return: None
        """
        json.dump(dict(pos=[int(k) for k in self.roi_box.pos()], size=
                       [int(k) for k in self.roi_box.size()]),
                  open('window_props.json', 'w'))
        self.deleteLater()
        self.app.quit()

    def toggle_calibration(self):
        dispw = self.display_window.widget_display
        dispw.calibrating = ~dispw.calibrating
        if dispw.calibrating:
            self.button_calibrate.setText('Hide calibration')
        else:
            self.button_calibrate.setText('Show calibration')
        dispw.update()
