from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np


class DotLivePlotter(QtGui.QMainWindow):  # , dotx, doty, stagex, stagey):
    def __init__(self, parent=None):
        super(DotLivePlotter, self).__init__(parent)
        self.central_widget = QtGui.QStackedWidget()
        self.setCentralWidget(self.central_widget)
        self.login_widget = LoginWidget(self)
        self.login_widget.button.clicked.connect(
            self.plotter
        )  # TODO just initiate self plotter here
        self.central_widget.addWidget(self.login_widget)

    def plotter(self):  # TODO rename acoording to input variables
        self.x = []
        self.y = []
        self.last_x = []
        self.last_y = []
        self.dot = self.login_widget.plot.getPlotItem().plot()
        self.curve = self.login_widget.plot.getPlotItem().plot()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updater)
        self.timer.start(10)
        self.t = 0

    def updater(self):
        self.t = self.t + 1
        self.x = [np.sin(0.002 * self.t)]  # feed data in here
        self.y = [np.cos(0.002 * self.t)]

        if len(self.last_x) > 100:
            self.last_x = self.last_x[1:]
            self.last_y = self.last_y[1:]
        self.last_x.extend(self.x)
        self.last_y.extend(self.y)

        self.dot.setData(x=self.x, y=self.y, symbol="o", pen=None)
        self.curve.setData(x=self.last_x, y=self.last_y)


class LoginWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(LoginWidget, self).__init__(parent)
        layout = QtGui.QHBoxLayout()
        self.button = QtGui.QPushButton("Start Plotting")  # TODO remove this
        layout.addWidget(self.button)  # TODO remove this
        self.plot = pg.PlotWidget()
        self.plot.setXRange(-2, 2)  # axis range according to stage measurements
        self.plot.setYRange(-2, 2)
        layout.addWidget(self.plot)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QtGui.QApplication([])
    window = DotLivePlotter()
    window.show()
    app.exec_()
