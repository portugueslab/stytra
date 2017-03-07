from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.tracking import DataAccumulator



class StramingPlotWidget(pg.GraphicsWindow):
    """
    Class for displaying data retrieved from a data_accumulator
    object. Use timestamp of the streamed data.
    """
    def __init__(self, *args, data_accumulator=None, **kwargs):
        """
        :param data_accumulator: DataAccumulator object to be displayed
        """
        super().__init__(*args, **kwargs)

        assert isinstance(data_accumulator, DataAccumulator)
        self.data_accumulator = data_accumulator

        # initialise the widgets
        self.streamplot = self.addPlot()

        self.curve = self.streamplot.plot()

        self.addItem(self.streamplot)
        self.start = datetime.datetime.now()

    def update(self):
        """This function will be called by an external timer
        """
        pass


class TailPlot(StramingPlotWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_points = 5000
        self.streamplot.setLabel('bottom', 'Time', 's')
        self.streamplot.setLabel('left', 'Tail sum')
        self.streamplot.setXRange(-5, 0)
        self.streamplot.setYRange(-1, 1)

    def update(self):
        self.data = np.ones(self.n_points)
        x = np.arange(self.n_points)
        self.start = datetime.datetime.now()
        try:
            last_n = min(self.n_points, len(self.data_accumulator.stored_data))
            d = np.array(self.data_accumulator.stored_data[-last_n:])

            unpacked_vals = list(zip(*d))

            x = np.array([(t - self.start).total_seconds()
                          for t in unpacked_vals[0]])
            self.data = np.array(unpacked_vals[1])[:, -1, 3]
            self.curve.setData(x=x, y=self.data)
        except IndexError:
            pass
        # self.curve.setData(x=np.arange(self.n_points), y=self.data)
