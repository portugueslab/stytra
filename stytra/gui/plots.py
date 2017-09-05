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
                 y_range=(-1, 1), data_acc_var=None, processing_function=None,
                 xlink=None, *args, **kwargs):
        """
        :param data_accumulator: DataAccumulator object to be displayed
        :param n_points: number of collected points
        :param x_range_s: time range
        :param y_range: variable range
        :param data_acc_col: column of data accumulator plotted (index)
        :param processing_function: how to process the paremeter which is plotted
        :param xlink: another axis to link y to (so that the time is synchronised)
        """

        super().__init__(*args, **kwargs)

        assert isinstance(data_accumulator, Accumulator)
        self.data_accumulator = data_accumulator

        # initialise the widgets
        self.streamplot = self.addPlot()

        self.curve = self.streamplot.plot()

        self.addItem(self.streamplot)
        self.start = datetime.datetime.now()
        self.data_accum_idx = self.data_accumulator.header_list.index(data_acc_var)

        self.n_points = n_points
        self.streamplot.setLabel('bottom', 'Time', 's')
        self.streamplot.setLabel('left', self.data_accumulator.header_list[self.data_accum_idx])
        print(self.data_accum_idx)
        self.streamplot.setXRange(x_range_s[0], x_range_s[1])
        self.streamplot.setYRange(y_range[0], y_range[1])
        if xlink is not None:
            self.streamplot.setXLink(xlink)

        self.processing_function = processing_function

    def update(self):
        """Function called by external timer to update the plot
        """
        self.start = datetime.datetime.now()
        try:

            # difference from data accumulator time and now in s...
            delta_t = (self.data_accumulator.starting_time -
                       self.start).total_seconds()

            # debugging
            if self.data_accumulator.header_list[1] == 'x':
                print(delta_t)

            data_array = self.data_accumulator.get_last_n(self.n_points)
            # ...to be added to the array of times in s in the data accumulator
            time_array = delta_t + data_array[:, 0]
            self.curve.setData(x=time_array, y=data_array[:, self.data_accum_idx])

        except IndexError:
            pass#print(self.data_accumulator.header_list)
        except TypeError:
            pass#print(self.data_accumulator.header_list)