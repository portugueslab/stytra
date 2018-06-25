from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.collectors import Accumulator
import time
import pandas as pd
import colorspacious


class StreamingPositionPlot(pg.GraphicsWindow):
    """Plot that displays the virtual position of the fish"""
    def __init__(self, *args, data_accumulator, n_points=500, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(data_accumulator, Accumulator)
        self.positionPlot = self.addPlot()
        self.positionPlot.setAspectLocked(True)
        self.curve = self.positionPlot.plot()

        self.n_points = n_points
        self.start = datetime.datetime.now()
        self.data_accumulator = data_accumulator
        self.ind_x = self.data_accumulator.header_list.index('x')
        self.ind_y = self.data_accumulator.header_list.index('y')

    def update(self):
        """ """
        try:
            data_array = self.data_accumulator.get_last_n(self.n_points)
            velocity = np.r_[np.clip(np.diff(data_array[:, self.ind_x])**2 + \
                       np.diff(data_array[:, self.ind_y])**2, 0, 30)/30, [0]]
            self.curve.setData(x=data_array[:, self.ind_x],
                               y=data_array[:, self.ind_y],
                               color=np.stack([0.5+0.5*velocity,
                                               0.2+0.8*velocity,
                                               velocity,
                                               np.ones_like(velocity)], 1))

        except (IndexError, TypeError):
            pass


class MultiStreamPlot(pg.GraphicsWindow):
    """Window to plot live data that are accumulated by a DAtaAccumulator
    object.
    New plots can be added via the add_stream() method.

    Parameters
    ----------

    Returns
    -------

    """
    def __init__(self, time_past=6, bounds_update=0.1,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_past = time_past

        self.value_label = pg.LabelItem(justify='right')
        self.addItem(self.value_label)

        self.plotContainter = pg.PlotItem()
        self.addItem(self.plotContainter)
        self.plotContainter.setXRange(-self.time_past*0.9, self.time_past*0.05)
        self.plotContainter.showAxis('left', False)
        self.plotContainter.vb.setMouseEnabled(x=True, y=False)

        self.accumulators = []
        self.stream_names = []
        self.header_indexes = []

        self.curves = []
        self.curvePoints = []
        self.valueLabels = []
        self.stream_scales = []

        self.bounds = []
        self.bounds_update = bounds_update

        self.colors = []

    @staticmethod
    def get_colors(n_colors=1, lightness=50, saturation=50, shift=0):
        """Get colors on the LCh ring

        Parameters
        ----------
        n_colors :
            param lightness: (Default value = 1)
        lightness :
             (Default value = 50)
        saturation :
             (Default value = 50)
        shift :
             (Default value = 0)

        Returns
        -------

        """
        hues = np.linspace(0, 360, n_colors + 1)[:-1] + shift
        return np.clip(colorspacious.cspace_convert(np.stack([
            np.ones_like(hues)*lightness,
            np.ones_like(hues)*saturation,
            hues
        ], 1), 'CIELCh', 'sRGB1'), 0, 1)*255

    def add_stream(self, accumulator, header_items=None):
        """Adds a data collector stream to the plot:

        Parameters
        ----------
        accumulator :
            instance of the DataAccumulator class
        header_items :
            specify elements in the DataAccumulator to be plot
            by their header name.

        Returns
        -------

        """
        if header_items is None:
            if accumulator.monitored_headers is not None:
                header_items = accumulator.monitored_headers
            else:
                header_items = accumulator.header_list[1:]  # first column is always t
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

            curve_label = pg.TextItem(header_item, anchor=(0, 1))
            curve_label.setPos(-self.time_past*0.9, i_curve)

            max_label = pg.TextItem('', anchor=(0, 0))
            max_label.setPos(0, i_curve+1)

            min_label = pg.TextItem('', anchor=(0, 1))
            min_label.setPos(0, i_curve)

            fps_label = pg.TextItem('', anchor=(0, 0))
            fps_label.setPos(-self.time_past*0.9, i_curve+1)

            value_label = pg.TextItem('', anchor=(0, 0.5))
            value_label.setPos(0, i_curve + 0.5)

            self.plotContainter.addItem(curve_label)
            self.plotContainter.addItem(min_label)
            self.plotContainter.addItem(max_label)
            self.plotContainter.addItem(fps_label)
            self.plotContainter.addItem(value_label)

            self.valueLabels.append((min_label, max_label, fps_label, curve_label, value_label))
            i_curve += 1

        for curve, color, labels in zip(self.curves, self.colors, self.valueLabels):
            curve.setPen(color)
            for label in labels:
                label.setColor(color)
        self.plotContainter.setYRange(-0.1, len(self.curves)+0.1)

    def update(self):
        """Function called by external timer to update the plot"""
        self.start = datetime.datetime.now()

        i_stream = 0
        for i_acc, (acc, indexes) in enumerate(zip(self.accumulators,
                                                   self.header_indexes)):

            # try:
            # difference from data accumulator time and now in seconds:
            try:
                delta_t = (acc.starting_time -
                           self.start).total_seconds()
            except (TypeError, IndexError):
                delta_t = 0
            data_array = acc.get_last_t(self.time_past)
            if len(data_array) > 1:
                try:
                    # ...to be added to the array of times in s in the data accumulator
                    fps = acc.get_fps()

                    time_array = delta_t + data_array[:, 0]

                    # Exclude nans from calculation of percentile boundaries:
                    b = ~(np.isnan(data_array[:, indexes])).any(1)
                    non_nan_data = data_array[b, :]

                    new_bounds = np.percentile(non_nan_data[:, indexes],
                                               (0.5, 99.5), 0).T
                    if self.bounds[i_acc] is None:
                        self.bounds[i_acc] = new_bounds
                    else:
                        self.bounds[i_acc] = self.bounds_update*new_bounds + \
                                      (1-self.bounds_update)*self.bounds[i_acc]
                    for i_var, (lb, ub) in zip(indexes, self.bounds[i_acc]):
                        scale = ub - lb
                        if scale < 0.00001:
                            scale = 1
                        self.valueLabels[i_stream][0].setText('{:7.3f}'.format(lb))
                        self.valueLabels[i_stream][1].setText('{:7.3f}'.format(ub))
                        self.valueLabels[i_stream][2].setText(
                            '{:7.2f} FPS'.format(fps))
                        self.valueLabels[i_stream][4].setText(
                            '{:7.3f}'.format(data_array[-1, i_var]))

                        self.curves[i_stream].setData(x=time_array,
                                                      y=i_stream+((data_array[:, i_var]-lb)/scale))
                        i_stream += 1
                except IndexError:
                    pass

            # except IndexError:
            #     pass
            # except TypeError:
            #     pass



