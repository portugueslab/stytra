import datetime
from collections import namedtuple
from stytra.collectors.accumulators import DataFrameAccumulator

import colorspacious
import numpy as np
import pyqtgraph as pg
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QSpacerItem,
    QGroupBox,
    QCheckBox,
    QSizePolicy,
)

PlotTuple = namedtuple(
    "PlotTuple", ["curve", "curve_label", "min_label", "max_label", "value_label"]
)


class MultiStreamPlot(QWidget):
    """Window to plot live data that are accumulated by a DAtaAccumulator
    object.
    New plots can be added via the add_stream() method.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self,
        time_past=5,
        bounds_update=0.1,
        compact=False,
        n_points_max=500,
        accumulators=None,
        precision=None,
        experiment=None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.experiment = experiment
        self.time_past = time_past
        self.compact = compact
        self.n_points_max = n_points_max

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.precision = precision or 3
        self.penwidth = 2

        if not compact:
            self.control_layout = QHBoxLayout()
            self.control_layout.setContentsMargins(0, 0, 0, 0)

            self.btn_select = QPushButton("Choose variables")
            self.btn_select.clicked.connect(self.show_select)
            self.control_layout.addWidget(self.btn_select)
            self.wnd_config = None

            self.btn_freeze = QPushButton()
            self.btn_freeze.setMinimumSize(80, 16)
            self.btn_freeze.clicked.connect(self.toggle_freeze)
            self.control_layout.addWidget(self.btn_freeze)

            try:
                tm = self.experiment.tracking_method_name
                if tm == "tail" or tm == "fish":
                    self.btn_extra = QPushButton(
                        "Show tail curvature" if tm == "tail" else "Show last bouts"
                    )

                    self.btn_extra.clicked.connect(self.show_extra_plot)
                    self.control_layout.addWidget(self.btn_extra)
            except AttributeError:
                pass

            self.lbl_zoom = QLabel("Plot past ")
            self.spn_zoom = QDoubleSpinBox()
            self.spn_zoom.setValue(time_past)
            self.spn_zoom.setSuffix("s")
            self.spn_zoom.setMinimum(0.1)
            self.spn_zoom.setMaximum(30)
            self.spn_zoom.valueChanged.connect(self.update_zoom)

            self.control_layout.addItem(
                QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            )
            self.control_layout.addWidget(self.lbl_zoom)
            self.control_layout.addWidget(self.spn_zoom)

            self.layout().addLayout(self.control_layout)

        self.plotContainer = pg.PlotWidget()
        self.plotContainer.showAxis("left", False)
        self.plotContainer.plotItem.hideButtons()

        self.replay_left = pg.InfiniteLine(
            -1, pen=(220, 220, 220), movable=True, hoverPen=(230, 30, 0)
        )
        self.replay_right = pg.InfiniteLine(
            -1, pen=(220, 220, 220), movable=True, hoverPen=(230, 30, 0)
        )

        for rep_line in [self.replay_left, self.replay_right]:
            rep_line.sigDragged.connect(self.update_replay_limits)

        self.layout().addWidget(self.plotContainer)

        self.active_plots = []

        self.accumulators = accumulators or []
        self.selected_columns = []

        self.stream_items = []
        self.stream_scales = []

        self.bounds = []
        self.bounds_update = bounds_update

        self.colors = []

        self.frozen = True
        self.bounds_visible = None

        # trick to set color on update
        self.color_set = False

        self.toggle_freeze()
        self.update_zoom(time_past)
        self.update_buflen(time_past)

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
        return (
            np.clip(
                colorspacious.cspace_convert(
                    np.stack(
                        [
                            np.ones_like(hues) * lightness,
                            np.ones_like(hues) * saturation,
                            hues,
                        ],
                        1,
                    ),
                    "CIELCh",
                    "sRGB1",
                ),
                0,
                1,
            )
            * 255
        )

    def refresh_streams(self):
        for accumulator, sel_columns in self.accumulators:
            pass

    def add_stream(self, accumulator: DataFrameAccumulator, header_items=None):
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
        try:
            if header_items is None:
                if accumulator.plot_columns is not None:
                    header_items = accumulator.plot_columns
                else:
                    header_items = accumulator.columns[1:]  # first column is always t
            self.colors = self.get_colors(len(self.stream_items) + len(header_items))
            self.accumulators.append(accumulator)
            self.selected_columns.append(header_items)
        except ValueError:
            return
        self.bounds.append(None)
        i_curve = len(self.stream_items)

        for header_item in header_items:
            c = pg.PlotCurveItem(
                x=np.array([0]), y=np.array([i_curve]), connect="finite"
            )
            curve_label = pg.TextItem(header_item, anchor=(0, 1))
            curve_label.setPos(-self.time_past * 0.9, i_curve)

            value_label = pg.TextItem("", anchor=(0, 0.5))
            font_bold = QFont("Sans Serif", 8)
            font_bold.setBold(True)
            value_label.setFont(font_bold)
            value_label.setPos(0, i_curve + 0.5)

            max_label = pg.TextItem("", anchor=(0, 0))
            max_label.setPos(0, i_curve + 1)

            min_label = pg.TextItem("", anchor=(0, 1))
            min_label.setPos(0, i_curve)

            self.stream_items.append(
                PlotTuple(c, curve_label, min_label, max_label, value_label)
            )

            i_curve += 1

        for sitems, color in zip(self.stream_items, self.colors):
            for itm in sitems:
                self.plotContainer.addItem(itm)
                if isinstance(itm, pg.PlotCurveItem):
                    itm.setPen(color, width=self.penwidth)
                else:
                    itm.setColor(color)
        self.plotContainer.setYRange(-0.1, len(self.stream_items) + 0.1)

    def remove_streams(self):
        for itmset in self.stream_items:
            for itm in itmset:
                self.plotContainer.removeItem(itm)
        self.stream_items = []

        self.selected_columns = []
        self.accumulators = []
        self.bounds = []

    def _set_labels(self, labels, values=None, precision=3):
        if values is None:
            txts = ["-", "-", "NaN"]
        else:
            fmt = "{:7.{prec}f}"
            txts = [fmt.format(x, prec=precision) for x in values]

        if not self.bounds_visible:
            txts[0] = ""
            txts[1] = ""

        for lbl, txt in zip(
            [labels.min_label, labels.max_label, labels.value_label], txts
        ):
            if lbl is not None:
                lbl.setText(txt)

    def update_bounds(self, i_acc, new_bounds):
        if self.bounds[i_acc] is None:
            self.bounds[i_acc] = new_bounds
        else:
            self.bounds[i_acc] = (
                self.bounds_update * new_bounds
                + (1 - self.bounds_update) * self.bounds[i_acc]
            )

    def update(self):
        """Function called by external timer to update the plot"""

        if not self.color_set:
            self.plotContainer.setBackground(self.palette().color(QPalette.Button))
            self.color_set = True

        if self.frozen:
            return None

        try:
            if self.experiment.camera_state.paused:
                return None
        except AttributeError:
            pass

        current_time = datetime.datetime.now()

        i_stream = 0
        for i_acc, (acc, sel_cols) in enumerate(
            zip(self.accumulators, self.selected_columns)
        ):

            # try:
            # difference from data accumulator time and now in seconds:
            delta_t = (self.experiment.t0 - current_time).total_seconds()
            data_frame = acc.get_last_t(self.time_past)

            # if this accumulator does not have enough data to plot, skip it
            if data_frame is None or data_frame.shape[0] <= 1:
                for _ in sel_cols:
                    self._set_labels(self.stream_items[i_stream])
                    self.stream_items[i_stream].curve.setData(x=[], y=[])
                    i_stream += 1
                continue

            # downsampling if there are too many points
            if len(data_frame) > self.n_points_max:
                data_frame = data_frame[:: len(data_frame) // self.n_points_max]

            time_array = delta_t + data_frame.t.values

            # loop to handle nan values in a single column
            new_bounds = np.zeros((len(sel_cols), 2))

            for id, col in enumerate(sel_cols):
                # Exclude nans from calculation of percentile boundaries:
                d = data_frame[col].values
                if d.dtype != np.float64:
                    continue
                b = ~np.isnan(d)
                if np.any(b):
                    non_nan_data = data_frame[col][b]
                    new_bounds[id, :] = np.percentile(non_nan_data, (0.5, 99.5), 0)
                    # if the bounds are the same, set arbitrary ones
                    if new_bounds[id, 0] == new_bounds[id, 1]:
                        new_bounds[id, 1] += 1

            self.update_bounds(i_acc, new_bounds)

            for col, (lb, ub) in zip(sel_cols, self.bounds[i_acc]):
                scale = ub - lb
                if scale < 0.00001:
                    self.stream_items[i_stream].curve.setData(x=[], y=[])
                else:
                    self.stream_items[i_stream].curve.setData(
                        x=time_array,
                        y=i_stream + ((data_frame[col].values - lb) / scale),
                    )
                self._set_labels(
                    self.stream_items[i_stream],
                    values=(lb, ub, data_frame[col].values[-1]),
                )
                i_stream += 1

    def show_extra_plot(self):
        self.experiment.window_main.docks["dock_extra"].setVisible(True)

    def _qcolorstring(self, color):
        colorname = self.palette().color(QPalette.Background).name().lstrip("#")
        return "rgb({},{},{})".format(
            *(int(colorname[i * 2 : i * 2 + 2], 16) for i in range(3))
        )

    def toggle_freeze(self):
        self.frozen = not self.frozen
        if self.frozen:
            if not self.compact:
                self.btn_freeze.setText("Live plot")
            self.btn_freeze.setStyleSheet("background-color:rgb(207, 132, 5);")
            self.plotContainer.setBackground(QColor(69, 78, 86))
            self.plotContainer.plotItem.vb.setMouseEnabled(x=True, y=True)
            for rep_line in [self.replay_left, self.replay_right]:
                self.plotContainer.addItem(rep_line)

        else:
            if not self.compact:
                self.btn_freeze.setText("Freeze plot")
            for rep_line in [self.replay_left, self.replay_right]:
                self.plotContainer.removeItem(rep_line)

            if self.color_set:
                self.plotContainer.setBackground(self.palette().color(QPalette.Button))
                self.btn_freeze.setStyleSheet(
                    "background-color:" + self._qcolorstring(QPalette.Mid)
                )
            self.plotContainer.plotItem.vb.setMouseEnabled(x=False, y=False)
            self.plotContainer.setXRange(-self.time_past * 0.9, self.time_past * 0.05)
            self.plotContainer.setYRange(-0.1, len(self.stream_items) + 0.1)

    def update_buflen(self, time_past):
        if self.experiment is not None:
            try:
                self.experiment.camera_state.ring_buffer_length = time_past
            except (IndexError, AttributeError):
                pass

    def update_zoom(self, time_past=1):
        # we use the current zoom level and the framerate to determine the rolling buffer length
        self.update_buflen(time_past)

        self.time_past = time_past
        self.plotContainer.setXRange(-self.time_past * 0.9, self.time_past * 0.05)
        self.plotContainer.plotItem.vb.setRange(
            xRange=(-self.time_past * 0.9, self.time_past * 0.05)
        )
        # shift the labels
        for (i_curve, items) in enumerate(self.stream_items):
            items.curve_label.setPos(-self.time_past * 0.9, i_curve)

    def update_replay_limits(self):
        if self.experiment is not None:
            try:
                left_lim = self.replay_left.getXPos()
                right_lim = self.replay_right.getXPos()

                self.experiment.camera_state.replay_limits = (
                    min(left_lim, right_lim),
                    max(left_lim, right_lim),
                )
            except AttributeError:
                pass

    def show_select(self):
        self.wnd_config = StreamPlotConfig(self)
        self.wnd_config.show()


class StreamPlotConfig(QWidget):
    """ Widget for configuring streaming plots
    """

    def __init__(self, sp: MultiStreamPlot):
        super().__init__()
        self.sp = sp
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.accs = sp.accumulators
        self.checkboxes = []

        for ac, sel_col in zip(sp.accumulators, sp.selected_columns):
            acccheck = []
            gb = QGroupBox(ac.name)
            gb.setLayout(QVBoxLayout())
            for i_it, item in enumerate(ac.columns[1:]):
                chk = QCheckBox(item)
                chk.setChecked(item in sel_col)
                chk.stateChanged.connect(self.refresh_plots)
                acccheck.append(chk)
                gb.layout().addWidget(chk)
            self.checkboxes.append(acccheck)
            self.main_layout.addWidget(gb)

    def refresh_plots(self):
        self.sp.remove_streams()
        for chkboxes, ac in zip(self.checkboxes, self.accs):
            sel_headers = []
            for item, chk in zip(ac.columns[1:], chkboxes):
                if chk.isChecked():
                    sel_headers.append(item)
            self.sp.add_stream(ac, sel_headers)


class FrameratePlot(MultiStreamPlot):
    def __init__(self, *args, round_bounds=0.1, framerate_limits=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.framerate_limits = framerate_limits or dict()
        self.round_bounds = round_bounds

    def update(self):
        super().update()
        for acc in self.accumulators:
            lim = self.framerate_limits.get(acc.name, None)
            if (
                lim is not None
                and len(acc.stored_data) > 0
                and acc.stored_data[-1][0] < lim
            ):
                print("BAD ", acc.name)

    def _round_bounds(self, bounds):
        rounded = np.stack(
            [
                np.floor(bounds[:, 0] / self.round_bounds) * self.round_bounds,
                np.ceil(bounds[:, 1] / self.round_bounds) * self.round_bounds,
            ],
            1,
        )
        if self.round_bounds >= 1:
            return rounded.astype(np.int32)
        else:
            return rounded

    def _update_round_bounds(self, old_bounds, new_bounds, tolerance=0.1):
        """ If bounds are exceeed by tolerance

        Parameters
        ----------
        old_bounds
        new_bounds

        Returns
        -------

        """
        to_update = np.any(
            np.abs(old_bounds - new_bounds) > tolerance * np.abs(old_bounds), 1
        )
        old_bounds[to_update, :] = self._round_bounds(new_bounds[to_update, :])
        return old_bounds

    def update_bounds(self, i_acc, new_bounds):
        if self.bounds[i_acc] is None:
            self.bounds[i_acc] = self._round_bounds(new_bounds)
        else:
            self.bounds[i_acc] = self._update_round_bounds(
                self.bounds[i_acc], new_bounds
            )
