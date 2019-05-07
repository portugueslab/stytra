from pathlib import Path
from stytra import Stytra
from PyQt5.QtWidgets import QFileDialog, QApplication, QDialog, QPushButton,\
    QComboBox, QGridLayout, QLabel, QToolBar, QProgressBar, QVBoxLayout
import qdarkstyle
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import Stimulus
from stytra.experiments.fish_pipelines import pipeline_dict
from stytra.utilities import save_df
import imageio
import pandas as pd
import json


class EmptyProtocol(Protocol):
    name = "Offline"

    def get_stim_sequence(self):
        return [Stimulus(duration=5.),]


class TrackingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.setWindowTitle("Tracking")
        self.prog_track = QProgressBar()
        self.lbl_status = QLabel()
        self.layout().addWidget(self.prog_track)
        self.layout().addWidget(self.lbl_status)


class OfflineToolbar(QToolBar):
    def __init__(self, app, exp, input_path, pipeline_type):
        super().__init__()
        self.app = app
        self.setObjectName("toolbar_offline")
        self.exp = exp
        self.input_path = Path(input_path)
        self.pipeline_type = pipeline_type
        self.output_path = self.input_path.parent / self.input_path.stem

        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems([
            "csv", "feather", "hdf5"])

        self.addAction("Track video", self.track)
        self.addAction("Output format")
        self.addWidget(self.cmb_fmt)
        self.addSeparator()
        self.addAction("Save tracking params", self.save_params)

        self.diag_track = TrackingDialog()


    def track(self):
        fileformat = self.cmb_fmt.currentText()

        self.exp.camera.kill_event.set()
        reader = imageio.get_reader(str(self.input_path))
        data = []
        self.exp.window_main.stream_plot.toggle_freeze()

        output_name = str(self.output_path)+"."+fileformat
        self.diag_track.show()
        l = reader.get_length()
        if not (0 < l < 100000):
            l = 1
        self.diag_track.prog_track.setMaximum(l)
        self.diag_track.lbl_status.setText("Tracking to "+
                                           output_name)

        for i, frame in enumerate(reader):
            data.append(self.exp.pipeline.run(frame[:, :, 0]).data)
            self.diag_track.prog_track.setValue(i)
            if i % 100 == 0:
                self.app.processEvents()

        self.diag_track.lbl_status.setText("Saving " +
                                           output_name)
        df = pd.DataFrame.from_records(data,
                                       columns=data[0]._fields)
        save_df(df, self.output_path, fileformat)
        self.diag_track.lbl_status.setText("Completed " +
                                           output_name)
        self.exp.wrap_up()

    def save_params(self):
        params = self.exp.pipeline.serialize_params()
        json.dump(dict(pipeline_type=self.pipeline_type,
                       pipeline_params=params),
                  open(str(self.output_path) +
                           "_trackingparams.json", "w"))


class StytraLoader(QDialog):
    """ A quick-and-dirty monkey-patch of Stytra for easy offline tracking

    """
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle("Select video for offline tracking")
        self.app = app

        self.btn_vid = QPushButton("Select video")
        self.btn_vid.clicked.connect(self.select_video)
        self.filename = None
        self.lbl_filename = QLabel("")

        self.lbl_whattrack = QLabel("What to track")
        self.cmb_tracking = QComboBox()
        self.cmb_tracking.addItems(list(pipeline_dict.keys()))

        self.btn_start = QPushButton("Start stytra")
        self.btn_start.clicked.connect(self.run_stytra)
        self.btn_start.setEnabled(False)

        self.setLayout(QGridLayout())
        self.layout().addWidget(self.btn_vid, 0, 0)
        self.layout().addWidget(self.lbl_filename, 0, 1)

        self.layout().addWidget(self.lbl_whattrack, 1, 0)
        self.layout().addWidget(self.cmb_tracking, 1, 1)

        self.layout().addWidget(self.btn_start, 2, 0, 1, 2)

        self.stytra = None

    def select_video(self):
        fn, _ = QFileDialog.getOpenFileName(None, "Select video file",
                                            filter="Videos (*.avi *.mov *.mp4)")
        self.filename = fn
        self.lbl_filename.setText(self.filename)
        self.btn_start.setEnabled(True)

    def run_stytra(self):
        self.stytra = Stytra(app=self.app, protocol=EmptyProtocol(),
                             camera=dict(video_file=self.filename),
                             tracking=dict(method=self.cmb_tracking.currentText()),
                             exec=False,display=dict(gl_display=False))

        offline_toolbar = OfflineToolbar(self.app,
                                         self.stytra.exp,
                                         self.filename,
                                         pipeline_type=self.cmb_tracking.currentText())

        self.stytra.exp.window_main.toolbar_control.hide()
        self.stytra.exp.window_main.addToolBar(offline_toolbar)
        offline_toolbar.show()

        self.stytra.exp.window_display.hide()
        self.close()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    ld = StytraLoader(app)
    ld.show()
    app.exec()



