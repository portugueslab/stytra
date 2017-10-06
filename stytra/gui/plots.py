from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.collectors import Accumulator
import time
import pandas as pd
import colorspacious

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


class MultiStreamPlot(pg.GraphicsWindow):
    def __init__(self, time_past=10, bounds_update =0.1,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_past = time_past

        self.value_label = pg.LabelItem(justify='right')
        self.addItem(self.value_label)

        self.plotContainter = pg.PlotItem()
        self.addItem(self.plotContainter)
        self.plotContainter.setXRange(-self.time_past*0.9, 0)

        self.accumulators = []
        self.stream_names = []
        self.header_indexes = []

        self.curves = []
        self.curvePoints = []
        self.valueLabels = []
        self.stream_scales = []

        self.vlinecolor = (210,200,200)
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=self.vlinecolor)
        self.plotContainter.addItem(self.vLine)
        self.bounds = []
        self.bounds_update = bounds_update

        self.colors = []

        self.proxy = pg.SignalProxy(self.plotContainter.scene().sigMouseMoved,
                                    rateLimit=60, slot=self.mouseMoved)

    @staticmethod
    def get_colors(n_colors=1, lightness=50, saturation=50, shift=0):
        """ Get colors on the LCh ring

        :param n_colors:
        :param lightness:
        :return:
        """
        hues = np.linspace(0, 360, n_colors + 1)[:-1] + shift
        return np.clip(colorspacious.cspace_convert(np.stack([
            np.ones_like(hues)*lightness,
            np.ones_like(hues)*saturation,
            hues
        ], 1), 'CIELCh', 'sRGB1'), 0, 1)*255

    def add_stream(self, accumulator, header_items):
        """ Adds a data collector stream to the plot

        """
        self.colors = self.get_colors(len(self.curves) + len(header_items))
        self.accumulators.append(accumulator)
        self.stream_names.append(header_items)
        self.header_indexes.append([accumulator.header_list.index(dv)
                                for dv in header_items])
        self.bounds.append(None)
        i_curve = len(self.curves)
        for header_item in header_items:
            c = pg.PlotCurveItem(x=np.array([0]),
                                 y=np.array([i_curve]))
            self.plotContainter.addItem(c)
            self.curves.append(c)

            curvePoint = pg.CurvePoint(c)

            value_label = pg.TextItem(anchor=(0, -1.0))
            value_label.setParentItem(curvePoint)

            self.curvePoints.append(curvePoint)
            self.valueLabels.append(value_label)
            i_curve += 1

        for curve, color in zip(self.curves, self.colors):
            print(color)
            curve.setPen(color)
        self.plotContainter.setYRange(-0.1, len(self.curves)+1.1)

    def mouseMoved(self, evt):
        pos = evt[0]
        if self.plotContainter.boundingRect().contains(pos):
            mousePoint = self.plotContainter.vb.mapSceneToView(pos)
            self.vLine.setPen(self.vlinecolor)
            self.vLine.setPos(mousePoint.x())

            active_curve = np.floor(mousePoint.y())
            # curvePoint.setPos(float(index) / (len(x) - 1))
            # text2.setText('[%0.1f, %0.1f]' % (x[index], y[index]))
        else:
            self.vLine.setPen(None)

    def update(self):
        """Function called by external timer to update the plot
        """
        self.start = datetime.datetime.now()

        i_stream = 0
        for i_acc, (acc, indexes) in enumerate(zip(self.accumulators, self.header_indexes)):
            try:

                # difference from data accumulator time and now in s...
                delta_t = (acc.starting_time -
                           self.start).total_seconds()

                data_array = acc.get_last_t(self.time_past)
                if len(data_array)>0:
                    # ...to be added to the array of times in s in the data accumulator
                    time_array = delta_t + data_array[:, 0]

                    new_bounds = np.percentile(data_array[:, indexes], (0.5, 99.5), 0).T
                    if self.bounds[i_acc] is None:
                        self.bounds[i_acc] = new_bounds
                    else:
                        self.bounds[i_acc] = self.bounds_update*new_bounds + \
                                      (1-self.bounds_update)*self.bounds[i_acc]
                    for i_var, (lb, ub) in zip(indexes, self.bounds[i_acc]):
                        scale = ub - lb
                        if scale < 0.00001:
                            scale = 1
                        self.curves[i_stream].setData(x=time_array,
                                                      y=i_stream+((data_array[:, i_var]-lb)/scale))
                        i_stream += 1

            except IndexError:
                pass
            except TypeError:
                pass



