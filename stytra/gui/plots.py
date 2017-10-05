from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.collectors import Accumulator
import time
import pandas as pd


class StreamingPlotWidget(pg.GraphicsWindow):
    """
    Class for displaying data retrieved from a data_accumulator
    object. Use timestamp of the streamed data.
    """
    def __init__(self, data_accumulator=None, n_points=500, x_range_s=(-5, 0),
                 y_range=(-1, 1), data_acc_var=None,
                 xlink=None, *args, **kwargs):
        """
        :param data_accumulator: DataAccumulator object to be displayed
        :param n_points: number of collected points
        :param x_range_s: time range
        :param y_range: variable range
        :param data_acc_col: column of data accumulator plotted (index)
        :param xlink: another axis to link y to (so that the time is synchronised)
        """

        super().__init__(*args, **kwargs)

        assert isinstance(data_accumulator, Accumulator)
        self.data_accumulator = data_accumulator

        # initialise the widgets
        self.streamplot = self.addPlot()

        self.addItem(self.streamplot)
        self.start = datetime.datetime.now()

        if isinstance(data_acc_var, str):
            data_acc_var = [data_acc_var]

        self.data_accum_idxs = [self.data_accumulator.header_list.index(dv)
                                for dv in data_acc_var]

        self.curves = []
        for i in range(len(data_acc_var)):
            c = pg.PlotCurveItem(pen=(i, len(data_acc_var) * 1.3))
            self.streamplot.addItem(c)
            c.setPos(0, i * 6)
            self.curves.append(c)

        self.n_points = n_points
        self.streamplot.setLabel('bottom', 'Time', 's')
        self.streamplot.setLabel('left', self.data_accumulator.header_list[self.data_accum_idxs[0]])
        self.streamplot.setXRange(x_range_s[0], x_range_s[1])
        self.streamplot.setYRange(y_range[0], y_range[1])

        if xlink is not None:
            self.streamplot.setXLink(xlink)

    def update(self):
        """Function called by external timer to update the plot
        """
        self.start = datetime.datetime.now()
        try:

            # difference from data accumulator time and now in s...
            delta_t = (self.data_accumulator.starting_time -
                       self.start).total_seconds()

            data_array = self.data_accumulator.get_last_n(self.n_points)
            # ...to be added to the array of times in s in the data accumulator
            time_array = delta_t + data_array[:, 0]
            self.streamplot.setTitle('FPS: {:.2f}'.format(self.data_accumulator.get_fps()))
            for idx, curve in zip(self.data_accum_idxs, self.curves):
                curve.setData(x=time_array, y=data_array[:, idx])

        except IndexError:
            pass
        except TypeError:
            pass


class StreamingPositionPlot(pg.GraphicsWindow):
    """ Plot that displays the virtual position of the fish

    """
    def __init__(self, *args, data_accumulator, n_points=500, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(data_accumulator, Accumulator)
        self.positionPlot = self.addPlot()
        self.curve = self.positionPlot.plot()

        self.n_points = n_points
        self.start = datetime.datetime.now()
        self.data_accumulator = data_accumulator
        self.ind_x = self.data_accumulator.header_list.index('x')
        self.ind_y = self.data_accumulator.header_list.index('y')

    def update(self):
        try:
            data_array = self.data_accumulator.get_last_n(self.n_points)

            self.curve.setData(x=data_array[:, self.ind_x], y=data_array[:, self.ind_y])

        except (IndexError, TypeError):
            pass