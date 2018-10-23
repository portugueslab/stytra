import logging
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QMainWindow,
    QCheckBox,
    QVBoxLayout,
    QSplitter,
    QDockWidget,
)

from lightparam.gui.collapsible_widget import CollapsibleWidget
from lightparam.gui import ParameterTreeGui, ParameterGui
from lightparam import ParameterTree, Parametrized, Param



class ExperimentBuilderWindow(QMainWindow):
    """Window for controlling a simple experiment including only a monitor
    the relative controls and the buttons for data_log and protocol control.

    Parameters
    ----------
    experiment : `Experiment <stytra.experiments.Experiment>` object
        experiment for which the window is built.

    Returns
    -------

    """

    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)

        self.setWindowTitle("Stytra")
        self.param_tree = ParameterTree()
        self.folder_params = Parametrized(
            name='saving_folder',
            params=dict(name=Param('/',
                                   gui="folder")),
            tree=self.param_tree)
        self.monitor_params = Parametrized(
            name='monitor',
            params=dict(fullscreen=Param(True),
                        monitor=Param(1)),
            tree=self.param_tree)
        self.camera_params = Parametrized(
            name='camera',
            params=dict(type=Param(value='None',
                                   limits=['avt',
                                           'ximea',
                                       'spinnaker']),
                        rotation=Param(0)),
            tree=self.param_tree)
        self.tracking_params = Parametrized(
            name="tracking_params",
            params=dict(preprocessing_method=Param(value='None',
                                                   limits=["prefilter",
                                                           "bgsub"]),
                        tracking_method=Param(value='None',
                                              limits=["centroid",
                                                      "tail_angles",
                                                      "eyes",
                                                      "fish"]),
                        estimator=Param(value='None',
                                        limits=["vigor",
                                                "position"]),
                        n_tracking_processes=Param(1)),

            tree=self.param_tree)

        #
        # self.docks = []
        #
        # # self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        # if not self.experiment.offline:
        #     self.widget_projection = ProjectorAndCalibrationWidget(experiment)
        # self.toolbar_control = ProtocolControlToolbar(
        #     experiment.protocol_runner, self)
        #
        # # Connect signals from the protocol_control:
        # self.toolbar_control.sig_start_protocol.connect(
        #     experiment.start_protocol)
        # self.toolbar_control.sig_stop_protocol.connect(experiment.end_protocol)
        #
        # act_metadata = self.toolbar_control.addAction("Edit metadata")
        # act_metadata.triggered.connect(self.show_metadata_gui)
        #
        # if experiment.trigger is not None:
        #     self.chk_scope = QCheckBox("Wait for trigger signal")
        #
        #
        # self.metadata_win = None

        # self.lyt_main = QVBoxLayout()
        self.layout().addWidget(ParameterTreeGui(self.param_tree))
        # self.setLayout(self.lyt_main)
        # if not self.experiment.offline:
        #     proj_dock = QDockWidget("Projector configuration", self)
        #     proj_dock.setWidget(self.widget_projection)
        #     proj_dock.setObjectName("dock_projector")
        #     self.docks.append(proj_dock)
        #     self.addDockWidget(Qt.RightDockWidgetArea, proj_dock)
        #
        # log_dock = QDockWidget("Log", self)
        # log_dock.setObjectName("dock_log")
        # log_dock.setWidget(self.logger.widget)
        # self.docks.append(log_dock)
        # self.addDockWidget(Qt.RightDockWidgetArea, log_dock)
        #
        # if self.experiment.trigger is not None:
        #     self.toolbar_control.addWidget(self.chk_scope)
        #
        # self.setCentralWidget(None)
        # return None
    #
    # def closeEvent(self, *args, **kwargs):
    #     """
    #
    #     Parameters
    #     ----------
    #     *args :
    #
    #     **kwargs :
    #
    #
    #     Returns
    #     -------
    #
    #     """
    #     pass


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    tree = ParameterTree()
    app = QApplication([])
    p = ExperimentBuilderWindow()
    p.show()
    app.exec_()
