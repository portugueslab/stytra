import traceback

from multiprocessing import Queue, Event
from queue import Empty

from stytra.experiments import Experiment
from stytra.gui.container_windows import (
    CameraExperimentWindow,
    TrackingExperimentWindow,
)
from stytra.hardware.video import (
    CameraControlParameters,
    VideoControlParameters,
    VideoWriter,
    VideoFileSource,
    CameraSource,
)

from stytra.tracking.movement import MovementDetectionParameters

# imports for tracking

from stytra.collectors import QueueDataAccumulator
from stytra.tracking.processes import FrameDispatcher, MovingFrameDispatcher
from stytra.tracking.processes import get_tracking_method, get_preprocessing_method
from stytra.tracking.tail import TailTrackingMethod
from stytra.tracking.eyes import EyeTrackingMethod
from stytra.tracking.fish import FishTrackingMethod

from stytra.stimulation.estimators import (
    PositionEstimator,
    VigourMotionEstimator,
    LSTMLocationEstimator,
)

import sys


class CameraExperiment(Experiment):
    """General class for Experiment that need to handle a camera.
    It implements a view of frames from the camera in the control GUI, and the
    respective parameters.
    For debugging it can be used with a video read from file with the
    VideoFileSource class.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, camera_config, camera_queue_mb=100, **kwargs):
        """
        :param video_file: if not using a camera, the video file
        file for the test input
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        if camera_config.get("video_file", None) is None:
            self.camera = CameraSource(
                camera_config["type"],
                rotation=camera_config.get("rotation", 0),
                downsampling=camera_config.get("downsampling", 1),
                max_mbytes_queue=camera_queue_mb,
            )
            self.camera_control_params = CameraControlParameters(tree=self.dc)
        else:
            self.camera = VideoFileSource(
                camera_config["video_file"],
                rotation=camera_config.get("rotation", 0),
                max_mbytes_queue=camera_queue_mb,
            )
            self.camera_control_params = VideoControlParameters(tree=self.dc)

        self.camera_framerate_acc = QueueDataAccumulator(self.camera.framerate_queue, ["fps"])

        # New parameters are sent with GUI timer:
        self.gui_timer.timeout.connect(self.send_gui_parameters)
        self.gui_timer.timeout.connect(self.camera_framerate_acc.update_list)

    def initialize_plots(self):
        self.window_main.plot_framerate.add_stream(self.camera_framerate_acc)

    def send_gui_parameters(self):
        self.camera.control_queue.put(self.camera_control_params.params.values)

    def start_experiment(self):
        """ """
        self.go_live()
        super().start_experiment()

    def make_window(self):
        """ """
        self.window_main = CameraExperimentWindow(experiment=self)
        self.gui_timer.timeout.connect(self.window_main.plot_framerate.update)
        self.window_main.show()
        self.initialize_plots()

    def go_live(self):
        """ """
        self.gui_timer.start(1000 // 60)
        sys.excepthook = self.excepthook
        self.camera.start()

    def wrap_up(self, *args, **kwargs):
        """

        Parameters
        ----------
        *args :
            
        **kwargs :
            

        Returns
        -------

        """
        super().wrap_up(*args, **kwargs)
        self.camera.kill_event.set()
        self.camera.terminate()
        self.gui_timer.stop()

    def excepthook(self, exctype, value, tb):
        """

        Parameters
        ----------
        exctype :
            
        value :
            
        tb :
            

        Returns
        -------

        """
        traceback.print_tb(tb)
        print("{0}: {1}".format(exctype, value))
        self.camera.kill_event.set()
        self.camera.terminate()


class TrackingExperiment(CameraExperiment):
    """Abstract class for an experiment which contains tracking.

    This class is the base for any experiment that tracks behaviour (being it
    eyes, tail, or anything else).
    The general purpose of the class is handle a frame dispatcher,
    the relative parameters queue and the output queue.
    
    The frame dispatcher take two input queues:

        - frame queue from the camera;
        - parameters queue from parameter window.
    
    and it puts data in three queues:

        - subset of frames are dispatched to the GUI, for displaying;
        - all the frames, together with the parameters, are dispatched
          to perform tracking;
        - the result of the tracking function, is dispatched to a data
          accumulator for saving or other purposes (e.g. VR control).

    Parameters
    ----------
        tracking_config: dict
            containing fields:  tracking_method
                                estimator: can be vigor or lstm for embedded fish, position
                                    for freely-swimming

    Returns
    -------

    """

    def __init__(self, *args, tracking_config, **kwargs):
        """
        :param tracking_method: class with the parameters for tracking (instance
                                of TrackingMethod class, defined in the child);
        :param header_list: headers for the data accumulator (list of strings,
                            defined in the child);
        :param data_name:  name of the data in the final experiment log (defined
                           in the child).
        """

        self.processing_params_queue = Queue()
        self.finished_sig = Event()
        super().__init__(*args, **kwargs)

        method_name = tracking_config["tracking_method"]
        preproc_method_name = tracking_config.get("preprocessing_method", None)

        preproc_method = get_preprocessing_method(preproc_method_name)
        self.preprocessing_method = preproc_method() if preproc_method else None
        self.tracking_method = get_tracking_method(method_name)()

        self.data_name = self.tracking_method.data_log_name
        self.frame_dispatcher = FrameDispatcher(
            in_frame_queue=self.camera.frame_queue,
            finished_signal=self.camera.kill_event,
            preprocessing_class=preproc_method_name,
            processing_class=method_name,
            processing_parameter_queue=self.processing_params_queue,
            gui_framerate=20,
        )

        self.data_acc = QueueDataAccumulator(
            self.frame_dispatcher.output_queue,
            monitored_headers=getattr(self.tracking_method, "monitored_headers", None),
            header_list=self.tracking_method.accumulator_headers,
        )

        # Data accumulator is updated with GUI timer:
        self.gui_timer.timeout.connect(self.data_acc.update_list)

        # Tracking is reset at experiment start:
        self.protocol_runner.sig_protocol_started.connect(self.data_acc.reset)

        # start frame dispatcher process:
        self.frame_dispatcher.start()

        est_type = tracking_config.get("estimator", None)
        if est_type == "position":
            self.estimator = PositionEstimator(self.data_acc, self.calibrator)
        elif est_type == "vigor":
            self.estimator = VigourMotionEstimator(self.data_acc)
        elif est_type == "lstm":
            self.estimator = LSTMLocationEstimator(
                self.data_acc, self.asset_dir + "/swim_lstm.h5"
            )
        else:
            self.estimator = None

    def refresh_accumulator_headers(self):
        """ Refreshes the data accumulators if something changed
        """
        self.tracking_method.reset_state()
        self.data_acc.reset(header_list=self.tracking_method.accumulator_headers,
                            monitored_headers=self.tracking_method.monitored_headers)
        self.window_main.stream_plot.remove_streams()
        self.initialize_plots()

    def make_window(self):
        tail = isinstance(self.tracking_method, TailTrackingMethod)
        eyes = isinstance(self.tracking_method, EyeTrackingMethod)
        fish = isinstance(self.tracking_method, FishTrackingMethod)
        self.window_main = TrackingExperimentWindow(
            experiment=self, tail=tail, eyes=eyes, fish=fish
        )

        self.initialize_plots()

        self.window_main.show()

    def initialize_plots(self):
        super().initialize_plots()
        self.window_main.stream_plot.add_stream(self.data_acc)

        if self.estimator is not None:
            self.window_main.stream_plot.add_stream(self.estimator.log)

            # We display the stimulus log only if we have vigor estimator, meaning 1D closed-loop experiments
            self.window_main.stream_plot.add_stream(self.protocol_runner.dynamic_log)

    def send_gui_parameters(self):
        """Called upon gui timeout, put tracking parameters in the relative
        queue.

        Parameters
        ----------

        Returns
        -------

        """
        super().send_gui_parameters()

        # TODO deal with parameters that impact the accumulators, maybe automatically link it to receiving something different
        # if isinstance(self.tracking_method, TailTrackingMethod):
        #     self.tracking_method.params.param("n_segments").sigValueChanged.connect(
        #         self.refresh_accumulator_headers
        #     )
        #
        # if isinstance(self.tracking_method, FishTrackingMethod):
        #     self.tracking_method.params.param("n_segments").sigValueChanged.connect(
        #         self.refresh_accumulator_headers
        #     )
        #     self.tracking_method.params.param("n_fish_max").sigValueChanged.connect(
        #         self.refresh_accumulator_headers
        #     )
        #

        self.processing_params_queue.put(
            {
                **self.tracking_method.params.params.values,
                **(
                    self.preprocessing_method.get_clean_values()
                    if self.preprocessing_method is not None
                    else {}
                ),
            }
        )

    def start_protocol(self):
        """Reset data accumulator when starting the protocol."""
        # TODO camera queue should be emptied to avoid accumulation of frames!!
        # when waiting for the microscope!
        super().start_protocol()
        self.data_acc.reset()
        try:
            self.estimator.log.reset()
        except AttributeError:
            pass

    def end_protocol(self, save=True):
        """Save tail position and dynamic parameters and terminate.

        """
        if save:
            self.save_log(self.data_acc, "log")
            try:
                print('saving estimator log')
                self.save_log(self.estimator.log, "estimator_log")
                print('save log')
            except AttributeError:
                pass
        try:
            print('trying resetting')
            self.estimator.log.reset()
            print('reset')
        except AttributeError:
            pass

        super().end_protocol(save)

    def set_protocol(self, protocol):
        """Connect new protocol start to resetting of the data accumulator.

        Parameters
        ----------
        protocol :
            

        Returns
        -------

        """
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc.reset)

    def wrap_up(self, *args, **kwargs):
        """

        Parameters
        ----------
        *args :
            
        **kwargs :
            

        Returns
        -------

        """
        super().wrap_up(*args, **kwargs)
        self.frame_dispatcher.terminate()

    def excepthook(self, exctype, value, tb):
        """

        Parameters
        ----------
        exctype :
            
        value :
            
        tb :
            

        Returns
        -------

        """
        traceback.print_tb(tb)
        print("{0}: {1}".format(exctype, value))
        self.finished_sig.set()
        self.camera.terminate()
        self.frame_dispatcher.terminate()


class VRExperiment(TrackingExperiment):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SwimmingRecordingExperiment(CameraExperiment):
    """Experiment where the fish is recorded while it is moving"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, camera_queue_mb=500, **kwargs)
        self.logger.info("Motion recording experiment")
        self.processing_params_queue = Queue()
        self.signal_start_rec = Event()
        self.finished_signal = Event()

        self.frame_dispatcher = MovingFrameDispatcher(
            in_frame_queue=self.camera.frame_queue,
            finished_signal=self.camera.kill_event,
            signal_start_rec=self.signal_start_rec,
            processing_parameter_queue=self.processing_params_queue,
            gui_framerate=20,
        )

        self.frame_recorder = VideoWriter(
            self.folder_name, self.frame_dispatcher.save_queue, self.finished_signal
        )  # TODO proper filename

        self.motion_acc = QueueDataAccumulator(
            self.frame_dispatcher.diagnostic_queue,
            header_list=self.frame_dispatcher.diagnostic_params,
        )
        self.frametime_acc = QueueDataAccumulator(
            self.frame_dispatcher.framestart_queue, header_list=["i_frame"]
        )

        self.motion_detection_params = MovementDetectionParameters()
        self.gui_timer.timeout.connect(self.send_params)
        self.gui_timer.timeout.connect(self.motion_acc.update_list)
        self.gui_timer.timeout.connect(self.frametime_acc.update_list)

    def make_window(self):
        """ """
        self.window_main = TrackingExperimentWindow(
            experiment=self, tail=False, eyes=False
        )
        self.window_main.stream_plot.add_stream(self.motion_acc)
        self.window_main.show()

    def go_live(self):
        """ """
        super().go_live()
        self.frame_dispatcher.start()
        self.frame_recorder.start()

    def send_params(self):
        """ """
        self.processing_params_queue.put(
            self.motion_detection_params.get_clean_values()
        )

    def start_protocol(self):
        """ """
        self.signal_start_rec.set()
        super().start_protocol()

    def wrap_up(self, *args, **kwargs):
        """ Ends all the processes in the application

        """
        super().wrap_up(*args, **kwargs)
        self.frame_dispatcher.terminate()
        self.frame_recorder.terminate()

    def end_protocol(self, save=True):
        """Save tail position and dynamic parameters. Reset what is necessary

        """

        self.frame_recorder.reset_signal.set()
        try:
            recorded_filename = self.frame_recorder.filename_queue.get(timeout=0.01)
            self.dc.add_static_data(recorded_filename, "tracking_recorded_video")

        except Empty:
            pass

        if save:
            self.save_log(self.frametime_acc, "frametimes")

        self.frametime_acc.reset()
        super().end_protocol(save)
