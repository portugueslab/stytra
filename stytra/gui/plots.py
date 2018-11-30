from PyQt5.QtGui import QPalette, QFont
from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSpacerItem,
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QCheckBox,
    QGroupBox,
)
import pyqtgraph as pg
import numpy as np
import datetime
from stytra.collectors import Accumulator
import colorspacious
from collections import namedtuple


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
        self.ind_x = self.data_accumulator.header_list.index("x")
        self.ind_y = self.data_accumulator.header_list.index("y")

    def update(self):
        """ """
        try:
            data_array = self.data_accumulator.get_last_n(self.n_points)
            velocity = np.r_[
                np.clip(
                    np.diff(data_array[:, self.ind_x]) ** 2
                    + np.diff(data_array[:, self.ind_y]) ** 2,
                    0,
                    30,
                )
                / 30,
                [0],
            ]
            self.curve.setData(
                x=data_array[:, self.ind_x],
                y=data_array[:, self.ind_y],
                color=np.stack(
                    [
                        0.5 + 0.5 * velocity,
                        0.2 + 0.8 * velocity,
                        velocity,
                        np.ones_like(velocity),
                    ],
                    1,
                ),
            )

        except (IndexError, TypeError):
            pass


PlotTuple = namedtuple("PlotTuple", ["curve", "curve_label", "min_label", "max_label",  "value_label"])


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
        time_past=10,
        bounds_update=0.1,
        round_bounds=None,
        compact=False,
        n_points_max=500,
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

        self.round_bounds = round_bounds

        self.precision = precision or 3

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

        self.replay_left = pg.InfiniteLine(-1, pen=(220, 220, 220),
                                           movable=True, hoverPen=(230, 30, 0))
        self.replay_right = pg.InfiniteLine(-1, pen=(220, 220, 220),
                                           movable=True, hoverPen=(230, 30, 0))
        self.replay_right.sigDragged.connect(self.update_replay_limits)
        self.replay_left.sigDragged.connect(self.update_replay_limits)
        self.plotContainer.addItem(self.replay_left)
        self.plotContainer.addItem(self.replay_right)

        self.layout().addWidget(self.plotContainer)

        self.accumulators = []
        self.header_indexes = []

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
        self.colors = self.get_colors(len(self.stream_items) + len(header_items))
        self.accumulators.append(accumulator)
        self.header_indexes.append(
            [accumulator.header_list.index(dv) for dv in header_items]
        )
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

            self.stream_items.append(PlotTuple(c, curve_label, min_label, max_label, value_label))

            i_curve += 1

        for sitems, color in zip(self.stream_items, self.colors):
            for itm in sitems:
                self.plotContainer.addItem(itm)
                if isinstance(itm, pg.PlotCurveItem):
                    itm.setPen(color)
                else:
                    itm.setColor(color)
        self.plotContainer.setYRange(-0.1, len(self.stream_items) + 0.1)

    def remove_streams(self):
        for itmset in self.stream_items:
            for itm in itmset:
                self.plotContainer.removeItem(itm)
        self.stream_items = []

        self.header_indexes = []
        self.accumulators = []
        self.bounds = []

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

    def _set_labels(self, labels, values=None, precision=3):
        if values is None:
            txts = ["-", "-", "NaN"]
        else:
            fmt = "{:7.{prec}f}"
            txts = [fmt.format(x, prec=precision) for x in values]

        if not self.bounds_visible:
            txts[0] = ""
            txts[1] = ""

        for lbl, txt in zip([labels.min_label, labels.max_label, labels.value_label], txts):
            if lbl is not None:
                lbl.setText(txt)

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
        for i_acc, (acc, indexes) in enumerate(
            zip(self.accumulators, self.header_indexes)
        ):

            # try:
            # difference from data accumulator time and now in seconds:
            try:
                delta_t = (acc.starting_time - current_time).total_seconds()
            except (TypeError, IndexError):
                delta_t = 0

            # TODO improve so that not the full list is acquired

            data_array = acc.get_last_t(self.time_past)

            # downsampling if there are too many points
            if len(data_array) > self.n_points_max:
                data_array = data_array[:: len(data_array) // self.n_points_max]

            # if this accumulator does not have enough data to plot, skip it
            if data_array.shape[0] <= 1:
                for _ in indexes:
                    self._set_labels(self.stream_items[i_stream])
                    self.stream_items[i_stream].curve.setData(x=[], y=[])
                    i_stream += 1
                continue

            try:
                time_array = delta_t + data_array[:, 0]

                # loop to handle nan values in a single column
                new_bounds = np.zeros((len(indexes), 2))

                for id, i in enumerate(indexes):
                    # Exclude nans from calculation of percentile boundaries:
                    d = data_array[:, i]
                    if d.dtype != np.float64:
                        continue
                    b = ~np.isnan(d)
                    if np.any(b):
                        non_nan_data = data_array[b, i]
                        new_bounds[id, :] = np.percentile(
                            non_nan_data, (0.5, 99.5), 0
                        )
                        # if the bounds are the same, set arbitrary ones
                        if new_bounds[id, 0] == new_bounds[id, 1]:
                            new_bounds[id, 1] += 1

                if self.bounds[i_acc] is None:
                    if not self.round_bounds:
                        self.bounds[i_acc] = new_bounds
                    else:
                        self.bounds[i_acc] = self._round_bounds(new_bounds)
                else:
                    if not self.round_bounds:
                        self.bounds[i_acc] = (
                            self.bounds_update * new_bounds
                            + (1 - self.bounds_update) * self.bounds[i_acc]
                        )
                    else:
                        self.bounds[i_acc] = self._update_round_bounds(
                            self.bounds[i_acc], new_bounds
                        )

                for i_var, (lb, ub) in zip(indexes, self.bounds[i_acc]):
                    scale = ub - lb
                    if scale < 0.00001:
                        self.stream_items[i_stream].curve.setData(x=[], y=[])
                    else:

                        self.stream_items[i_stream].curve.setData(
                            x=time_array,
                            y=i_stream + ((data_array[:, i_var] - lb) / scale),
                        )
                    self._set_labels(self.stream_items[i_stream], values=(lb, ub, data_array[-1, i_var]))
                    i_stream += 1
            except IndexError:
                pass

    def toggle_freeze(self):
        self.frozen = not self.frozen
        if self.frozen:
            if not self.compact:
                self.btn_freeze.setText("Live plot")
            self.plotContainer.plotItem.vb.setMouseEnabled(x=True, y=True)
        else:
            if not self.compact:
                self.btn_freeze.setText("Freeze plot")
            self.plotContainer.plotItem.vb.setMouseEnabled(x=False, y=False)
            self.plotContainer.setXRange(-self.time_past * 0.9, self.time_past * 0.05)
            self.plotContainer.setYRange(-0.1, len(self.stream_items) + 0.1)

    def update_zoom(self, time_past=1):
        # we use the current zoom level and the framerate to determine the rolling buffer length
        if self.experiment is not None:
            try:
                self.experiment.camera_state.ring_buffer_length = int(round(time_past*self.experiment.camera_framerate_acc.stored_data[-1][1]))
            except IndexError:
                pass

        self.time_past = time_past
        self.plotContainer.setXRange(-self.time_past * 0.9, self.time_past * 0.05)
        self.plotContainer.plotItem.vb.setRange(
            xRange=(-self.time_past * 0.9, self.time_past * 0.05)
        )
        # shift the labels
        for (i_curve, (min_label, max_label, curve_label, value_label)) in enumerate(
            self.stream_items
        ):
            curve_label.setPos(-self.time_past * 0.9, i_curve)

    def update_replay_limits(self):
        if self.experiment is not None:
            try:
                cam_fps =self.experiment.camera_framerate_acc.stored_data[-1][1]
                left_lim =  int(round(self.replay_left.getXPos() * cam_fps))
                right_lim = int(round(self.replay_right.getXPos() * cam_fps))
                final_lim = (max(0, min(left_lim, right_lim)),
                             min(self.experiment.camera_state.ring_buffer_length,
                                 max(left_lim, right_lim)))

                self.experiment.camera_state.replay_limits = final_lim
            except AttributeError:
                pass


    def show_select(self):
        self.wnd_config = StreamPlotConfig(self)
        self.wnd_config.show()


class TailStreamPlot(QWidget):
    def __init__(self, acc, headers, n_points=300):
        super().__init__()
        self.acc = acc
        self.headers = headers
        self.n_points = n_points

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.display_widget = pg.GraphicsLayoutWidget()
        self.vb_display = pg.ViewBox()
        self.display_widget.addItem(self.vb_display)
        self.image_item = pg.ImageItem()
        self.vb_display.addItem(self.image_item)

        self.image_item.setLevels((-0.6, 0.6))
        self.image_item.setLookupTable(pg.ColorMap(np.linspace(0, 1, 5),
                                                  np.array([[0.42107294,0.80737975,0.49219722],
                                                            [0.23166242,
                                                             0.39962101,
                                                             0.32100403],
                                                            [0.0, 0.0, 0.0],
                                                            [0.46170494,
                                                             0.30327584,
                                                             0.38740225],
                                                            [0.91677407,0.58427975,0.92293321]])).getLookupTable(alpha=False))
        self.layout().addWidget(self.display_widget)

    def update(self):
        if not self.isVisible():
            return
        data_array = self.acc.get_last_n(self.n_points)
        if len(data_array) > 0:
            self.image_item.setImage(image=np.diff(data_array[:, 2:], axis=1).T,
                                       autoLevels=False)


class StreamPlotConfig(QWidget):
    """ Widget for configuring streaming plots
    """

    def __init__(self, sp: MultiStreamPlot):
        super().__init__()
        self.sp = sp
        self.setLayout(QVBoxLayout())
        self.accs = sp.accumulators
        self.checkboxes = []
        for ac in sp.accumulators:
            acccheck = []
            gb = QGroupBox(ac.name)
            gb.setLayout(QVBoxLayout())
            for item in ac.header_list[1:]:
                chk = QCheckBox(item)
                if ac.monitored_headers is None:
                    chk.setChecked(True)
                elif item in ac.monitored_headers:
                    chk.setChecked(True)

                chk.stateChanged.connect(self.refresh_plots)
                acccheck.append(chk)
                gb.layout().addWidget(chk)
            self.checkboxes.append(acccheck)
            self.layout().addWidget(gb)

    def refresh_plots(self):
        self.sp.remove_streams()
        for chkboxes, ac in zip(self.checkboxes, self.accs):
            sel_headers = []
            for item, chk in zip(ac.header_list[1:], chkboxes):
                if chk.isChecked():
                    sel_headers.append(item)
            self.sp.add_stream(ac, sel_headers)
