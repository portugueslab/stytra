from PyQt5.QtCore import QRectF, pyqtSignal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout,\
    QWidget, QLayout, QComboBox, \
    QMainWindow, QProgressBar, QLabel, QSplitter, QDoubleSpinBox

import pyqtgraph as pg
from pyqtgraph.parametertree import ParameterTree
import numpy as np
import inspect

from stytra.stimulation import protocols
from stytra.stimulation.protocols import Protocol

from stytra.gui.plots import MultiStreamPlot, StreamingPositionPlot

from stytra.stimulation.protocols import VRProtocol



class DebugLabel(QLabel):
    def __init__(self, *args, debug_on=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('border-radius: 2px')
        self.set_debug(debug_on)
        self.setMinimumHeight(36)

    def set_debug(self, debug_on=False):
        if debug_on:
            self.setText('Debug mode is on, data will not be saved!')
            self.setStyleSheet('background-color: #dc322f;color:#fff')
        else:
            self.setText('Experiment ready, please ensure the metadata is correct')
            self.setStyleSheet('background-color: #002b36')


class ProjectorViewer(pg.GraphicsLayoutWidget):
    def __init__(self, *args, display_size=(1280, 800), ROI_desc=None,  **kwargs):
        super().__init__(*args, **kwargs)

        self.view_box = pg.ViewBox(invertY=True, lockAspect=1,
                                   enableMouse=False)
        self.addItem(self.view_box)

        self.roi_box = pg.ROI(maxBounds=QRectF(0, 0, display_size[0],
                                               display_size[1]),
                              size=ROI_desc['size'],
                              pos=ROI_desc['pos'])
        self.roi_box.addScaleHandle([0, 0], [1, 1])
        self.roi_box.addScaleHandle([1, 1], [0, 0])
        self.view_box.addItem(self.roi_box)
        self.view_box.setRange(QRectF(0, 0, display_size[0], display_size[1]),
                               update=True, disableAutoRange=True)
        self.view_box.addItem(pg.ROI(pos=(1, 1), size=(display_size[0]-1,
                              display_size[1]-1), movable=False,
                                     pen=(80, 80, 80)),
                              )
        self.calibration_points = pg.ScatterPlotItem()
        self.calibration_frame = pg.PlotCurveItem(brush=(120, 10, 10),
                                                  pen=(200, 10, 10),
                                                  fill_level=1)
        self.view_box.addItem(self.calibration_points)
        self.view_box.addItem(self.calibration_frame)

    def display_calibration_pattern(self, calibrator,
                                    camera_resolution=(480, 640),
                                    image=None):
        cw = camera_resolution[0]
        ch = camera_resolution[1]
        points_cam = np.array([[0, 0], [0, cw],
                              [ch, cw], [ch, 0], [0, 0]])

        points_cam = np.pad(points_cam, ((0, 0), (0, 1)),
                            mode='constant', constant_values=1)
        points_calib = np.pad(calibrator.points, ((0, 0), (0, 1)),
                              mode='constant', constant_values=1)
        points_proj = (points_cam @ calibrator.cam_to_proj.T)
        x0, y0 = self.roi_box.pos()
        self.calibration_frame.setData(x=points_proj[:, 0]+x0,
                                       y=points_proj[:, 1]+y0)
        self.calibration_points.setData(x=points_calib[:, 0]+x0,
                                        y=points_calib[:, 1]+y0)
        if image is not None:
            pass
            # TODO place transformed image


class ProtocolDropdown(QComboBox):
    def __init__(self):
        super().__init__()
        prot_classes = inspect.getmembers(protocols, inspect.isclass)

        self.setEditable(False)
        self.prot_classdict = {prot[1].name: prot[1]
                               for prot in prot_classes if issubclass(prot[1],
                                                                      Protocol)}

        self.addItems(list(self.prot_classdict.keys()))


class ParameterSpinBox(QDoubleSpinBox):
    def __init__(self, *args, parameter, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameter = parameter
        param_state = parameter.saveState()
        self.setValue(param_state['value'])
        self.setMinimum(param_state['limits'][0])
        self.setMaximum(param_state['limits'][1])
        self.parameter.sigValueChanged.connect(self.update_val)
        self.valueChanged.connect(self.set_param_val)

    def set_param_val(self):
        self.parameter.setValue(self.value())

    def update_val(self):
        self.setValue(self.parameter.value())



class ProtocolControlWindow(QMainWindow):
    sig_closing = pyqtSignal()

    def __init__(self, display_window=None,
                 experiment=None, *args):
        # TODO passing the experiment may overcome the necessity of the other parameters
        """
        Widget for controlling the stimulation.
        :param app: Qt5 app
        :param protocol: Protocol object with the stimulus
        :param display_window: ProjectorViewer object for the projector
        :param protocol_runner: ProtocolRunner object with the stimuli
        :param experiment: Experiment object
        """
        super().__init__(*args)
        self.controls_widget = QWidget()
        self.display_window = display_window
        self.protocol_runner = experiment.protocol_runner
        self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        self.experiment = experiment

        self.calibrator = self.experiment.calibrator
        if self.display_window:
            ROI_desc = self.display_window.params
            self.widget_view = ProjectorViewer(ROI_desc=ROI_desc)
        else:
            self.widget_view = None

        # Create parametertree for protocol parameter control
        self.protocol_params_tree = ParameterTree(showHeader=False)
        self.protocol_params_tree.setParameters(self.protocol_runner.protocol.params)

        # Widgets for calibration displaying
        self.layout_calibrate = QHBoxLayout()
        self.button_show_calib = QPushButton('Show calibration')
        self.label_calibrate = QLabel('size of calib. pattern in mm')
        self.layout_calibrate.addWidget(self.button_show_calib)
        self.layout_calibrate.addWidget(self.label_calibrate)

        # mm/px widget is instantiated with parametertree
        self.calibrator_len_spin = ParameterSpinBox(parameter=self.calibrator.params.param('length_mm'))

        self.layout_calibrate.addWidget(self.calibrator_len_spin)

        self.button_show_calib.clicked.connect(self.toggle_calibration)

        # Widgets for protocol choosing
        self.layout_choose = QHBoxLayout()
        self.combo_prot = ProtocolDropdown()
        self.combo_prot.currentIndexChanged.connect(self.set_protocol)
        self.protocol_params_butt = QPushButton('Protocol parameters')
        self.protocol_params_butt.clicked.connect(self.show_stim_params_gui)
        self.layout_choose.addWidget(self.combo_prot)
        self.layout_choose.addWidget(self.protocol_params_butt)

        # Widgets for protocol running
        self.layout_run = QHBoxLayout()
        self.button_toggle_prot = QPushButton("▶")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat('%p% %v/%m')
        self.layout_run.addWidget(self.button_toggle_prot)
        self.layout_run.addWidget(self.progress_bar)

        self.button_metadata = QPushButton('Edit metadata')
        self.button_metadata.clicked.connect(self.experiment.metadata.show_metadata_gui)

        self.button_toggle_prot.clicked.connect(self.toggle_protocol_running)
        self.combo_prot.currentIndexChanged.connect(self.set_protocol)

        self.timer = None
        self.layout = QVBoxLayout()
        for widget in [self.label_debug,
                       self.widget_view,
                        self.layout_choose,
                       self.layout_calibrate, self.layout_run,
                       self.button_metadata]:
            if isinstance(widget, QWidget):
                self.layout.addWidget(widget)
            if isinstance(widget, QLayout):
                self.layout.addLayout(widget)

        self.protocol_runner.sig_protocol_updated.connect(self.update_stim_duration)
        self.protocol_runner.sig_timestep.connect(self.update_progress)

        self.controls_widget.setLayout(self.layout)
        self.reset_ROI()
        self.widget_view.roi_box.sigRegionChangeFinished.connect(self.refresh_ROI)
        self.setCentralWidget(self.controls_widget)

    def reset_ROI(self):
        self.widget_view.roi_box.setPos(self.display_window.params['pos'], finish=False)
        self.widget_view.roi_box.setSize(self.display_window.params['size'])
        self.refresh_ROI()

    def refresh_ROI(self):
        if self.display_window:
            self.display_window.set_dims(tuple([int(p) for p in
                                                self.widget_view.roi_box.pos()]),
                                         tuple([int(p) for p in
                                                self.widget_view.roi_box.size()]))

    def show_stim_params_gui(self):
        self.protocol_params_tree.setParameters(self.protocol_runner.protocol.params)
        self.protocol_params_tree.show()
        self.protocol_params_tree.setWindowTitle('Stimulus parameters')
        self.protocol_params_tree.resize(300, 600)

    def toggle_protocol_running(self):
        # Start/stop the protocol:
        if self.protocol_runner.running:
            self.experiment.end_protocol()
        else:
            self.experiment.start_protocol()

        # swap the symbol: #TODO still buggy!
        if self.button_toggle_prot.text() == "▶":
            self.button_toggle_prot.setText("■")
        else:
            self.button_toggle_prot.setText("▶")

    def toggle_calibration(self):
        self.calibrator.toggle()
        print(self.calibrator)
        if self.calibrator.enabled:
            self.button_show_calib.setText('Hide calibration')
        else:
            self.button_show_calib.setText('Show calibration')
        self.display_window.widget_display.update()
        self.experiment.sig_calibrating.emit()

    def update_stim_duration(self):
        self.progress_bar.setMaximum(int(self.protocol_runner.duration))

    def update_progress(self):
        self.progress_bar.setValue(int(self.protocol_runner.t))

    def protocol_changed(self):
        self.progress_bar.setValue(0)

    def set_protocol(self):
        """Use dropdown menu to change the protocol. Maybe to be implemented in
        the control widget and not here.
        """
        Protclass = self.combo_prot.prot_classdict[
            self.combo_prot.currentText()]
        protocol = Protclass()
        self.protocol_runner.set_new_protocol(protocol)
        self.reconfigure_ui()


    def reconfigure_ui(self):
        if isinstance(self.protocol_runner.protocol, VRProtocol):
            self.main_layout = QSplitter()
            self.monitoring_widget = QWidget()
            self.monitoring_layout = QVBoxLayout()
            self.monitoring_widget.setLayout(self.monitoring_layout)

            self.positionPlot = StreamingPositionPlot(data_accumulator=self.protocol.dynamic_log)
            self.monitoring_layout.addWidget(self.positionPlot)
            self.gui_refresh_timer.timeout.connect(self.positionPlot.update)

            self.stream_plot = MultiStreamPlot()

            self.monitoring_layout.addWidget(self.stream_plot)
            self.gui_refresh_timer.timeout.connect(self.stream_plot.update)

            self.stream_plot.add_stream(self.experiment.data_acc_tailpoints,
                                        ['tail_sum', 'theta_01'])

            self.stream_plot.add_stream(self.experiment.position_estimator.log,
                                        ['v_ax',
                                             'v_lat',
                                             'v_ang',
                                             'middle_tail',
                                             'indexes_from_past_end'])

            self.main_layout.addWidget(self.monitoring_widget)
            self.main_layout.addWidget(self.controls_widget)
            self.setCentralWidget(self.main_layout)

        else:
            pass
            # GUI elements
            # TODO update for multistreamplot

















