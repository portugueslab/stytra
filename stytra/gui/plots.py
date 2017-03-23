from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.tracking import DataAccumulator
import time
import pandas as pd


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
        self.streamplot.setXRange(-0.015, 0)
        self.streamplot.setYRange(-1, 1)

    def update(self):
        x = np.arange(self.n_points)
        self.start = datetime.datetime.now()
        try:
            last_n = min(self.n_points, len(self.data_accumulator.stored_data))
            data_list = self.data_accumulator.stored_data[-last_n:]

            # apparently the fastest way
            data_array = pd.lib.to_object_array(data_list).astype(float)
            # print(d.shape)
            delta_t = (self.data_accumulator.starting_time -
                       self.start).total_seconds()

            time_array = delta_t + data_array[:, 0]
            self.curve.setData(x=time_array, y=data_array[:, 1])
        except IndexError:
            pass
        except TypeError:
            pass
        # self.curve.setData(x=np.arange(self.n_points), y=self.data)
