import traceback

from multiprocessing import Queue, Event, Value
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

# imports for tracking
from stytra.collectors import QueueDataAccumulator, QueueSummingAccumulator
from stytra.tracking.processes import FrameDispatcher, MovingFrameDispatcher
from stytra.tracking.processes import get_tracking_method, get_preprocessing_method
from stytra.tracking.tail import TailTrackingMethod
from stytra.tracking.eyes import EyeTrackingMethod
from stytra.tracking.fish import FishTrackingMethod
from lightparam.param_qt import ParametrizedQt

from stytra.stimulation.estimators import (
    PositionEstimator,
    VigorMotionEstimator,
    Estimator,
)

from inspect import isclass

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

    def __init__(self, *args, camera, camera_queue_mb=100, **kwargs):
        """
        :param video_file: if not using a camera, the video file
        file for the test input
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        if camera.get("video_file", None) is None:
            self.camera = CameraSource(
                camera["type"],
                rotation=camera.get("rotation", 0),
                downsampling=camera.get("downsampling", 1),
                roi=camera.get("roi", (-1, -1, -1, -1)),
                max_mbytes_queue=camera_queue_mb,
            )
            self.camera_state = CameraControlParameters(tree=self.dc)
        else:
            self.camera = VideoFileSource(
                camera["video_file"],
                rotation=camera.get("rotation", 0),
                max_mbytes_queue=camera_queue_mb,
            )
            self.camera_state = VideoControlParameters(tree=self.dc)

        self.camera_framerate_acc = QueueDataAccumulator(
            self.camera.framerate_queue, ["camera"]
        )

        # New parameters are sent with GUI timer:
        self.gui_timer.timeout.connect(self.send_gui_parameters)
        self.gui_timer.timeout.connect(self.camera_framerate_acc.update_list)

    def initialize_plots(self):
        self.window_main.plot_framerate.add_stream(self.camera_framerate_acc)

    def send_gui_parameters(self):

        self.camera.control_queue.put(self.camera_state.params.changed_values())
        self.camera_state.params.acknowledge_changes()

    def start_experiment(self):
        """ """
        self.go_live()
        super().start_experiment()

    def make_window(self):
        """ """
        self.window_main = CameraExperimentWindow(experiment=self)
        self.window_main.construct_ui()
        self.window_main.show()
        self.restore_window_state()
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
        self.gui_timer.stop()
        super().wrap_up(*args, **kwargs)
        self.camera.kill_event.set()

        for q in [self.camera.frame_queue]:
            q.clear()

        self.camera.join()

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
        self.camera.join()


class TrackingExperiment(CameraExperiment):
    """Abstract class for an experiment which contains tracking.

    This class is the base for any experiment that tracks behavior (being it
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
                                estimator: can be vigor for embedded fish, position
                                    for freely-swimming, or a custom subclass of Estimator

    Returns
    -------

    """

    def __init__(self, *args, tracking, n_tracking_processes=1, **kwargs):
        """
        :param tracking_method: class with the parameters for tracking (instance
                                of TrackingMethod class, defined in the child);
        :param header_list: headers for the data accumulator (list of strings,
                            defined in the child);
        :param data_name:  name of the data in the final experiment log (defined
                           in the child).
        """

        self.processing_params_queue = Queue()
        self.tracking_output_queue = Queue()
        self.processing_counter = Value("i", -1)
        self.finished_sig = Event()
        super().__init__(*args, **kwargs)

        self.n_dispatchers = n_tracking_processes
        self.tracking_method_name = tracking["method"]
        preproc_method_name = tracking.get("preprocessing", None)

        # If centroid or eyes method is used, prefilter by default:
        if preproc_method_name is None and self.tracking_method_name in [
            "tail",
            "eyes",
        ]:
            preproc_method_name = "prefilter"

        preproc_method = get_preprocessing_method(preproc_method_name)
        self.preprocessing_method = preproc_method() if preproc_method else None
        if preproc_method:
            self.preprocessing_params = ParametrizedQt(
                name="tracking/preprocessing",
                params=self.preprocessing_method.process,
                tree=self.dc,
            )
        self.tracking_method = get_tracking_method(self.tracking_method_name)()
        self.tracking_params = ParametrizedQt(
            name="tracking/" + type(self.tracking_method).name,
            params=self.tracking_method.detect,
            tree=self.dc,
        )

        self.frame_dispatchers = [
            FrameDispatcher(
                in_frame_queue=self.camera.frame_queue,
                finished_signal=self.camera.kill_event,
                preprocessing_class=preproc_method_name,
                processing_class=self.tracking_method_name,
                processing_parameter_queue=self.processing_params_queue,
                output_queue=self.tracking_output_queue,
                processing_counter=self.processing_counter,
                gui_dispatcher=(i == 0),  # only the first process dispatches to the GUI
                gui_framerate=20,
            )
            for i in range(self.n_dispatchers)
        ]

        self.acc_tracking = QueueDataAccumulator(
            name="tracking",
            data_queue=self.tracking_output_queue,
            monitored_headers=getattr(self.tracking_method, "monitored_headers", None),
            header_list=self.tracking_method.accumulator_headers,
        )

        # Data accumulator is updated with GUI timer:
        self.gui_timer.timeout.connect(self.acc_tracking.update_list)

        # Tracking is reset at experiment start:
        self.protocol_runner.sig_protocol_started.connect(self.acc_tracking.reset)

        # start frame dispatcher process:
        for dispatcher in self.frame_dispatchers:
            dispatcher.start()

        est_type = tracking.get("estimator", None)
        if est_type == "position":
            self.estimator = PositionEstimator(
                self.acc_tracking, calibrator=self.calibrator
            )
        elif est_type == "vigor":
            self.estimator = VigorMotionEstimator(self.acc_tracking)
        elif isclass(est_type) and issubclass(est_type, Estimator):
            self.estimator = est_type(
                self.acc_tracking, **tracking.get("estimator_params", {})
            )
        else:
            self.estimator = None

        self.acc_framerate = QueueSummingAccumulator(
            [fd.framerate_queue for fd in self.frame_dispatchers], ["tracking"]
        )

        self.gui_timer.timeout.connect(self.acc_framerate.update_list)
        self.logger.info("Tracking with ", self.n_dispatchers, " processess")

    def refresh_accumulator_headers(self):
        """ Refreshes the data accumulators if something changed
        """
        self.tracking_method.reset_state()
        self.acc_tracking.reset(
            header_list=self.tracking_method.accumulator_headers,
            monitored_headers=self.tracking_method.monitored_headers,
        )
        self.refresh_plots()

    def make_window(self):
        tail = isinstance(self.tracking_method, TailTrackingMethod)
        eyes = isinstance(self.tracking_method, EyeTrackingMethod)
        fish = isinstance(self.tracking_method, FishTrackingMethod)
        self.window_main = TrackingExperimentWindow(
            experiment=self, tail=tail, eyes=eyes, fish=fish
        )
        self.window_main.construct_ui()
        self.initialize_plots()
        self.window_main.show()
        self.restore_window_state()

    def initialize_plots(self):
        super().initialize_plots()
        self.window_main.plot_framerate.add_stream(self.acc_framerate)
        self.refresh_plots()

    def refresh_plots(self):
        self.window_main.stream_plot.remove_streams()
        self.window_main.stream_plot.add_stream(self.acc_tracking)

        if self.estimator is not None:
            self.window_main.stream_plot.add_stream(self.estimator.log)

            # We display the stimulus log only if we have vigor estimator, meaning 1D closed-loop experiments
            self.window_main.stream_plot.add_stream(self.protocol_runner.dynamic_log)

        if self.stim_plot:  # but also if forced:
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
        changed = self.tracking_params.params.changed_values()

        if "n_segments" in changed.keys() or "n_fish_max" in changed.keys():
            self.refresh_accumulator_headers()

        for i in range(self.n_dispatchers):
            self.processing_params_queue.put(
                {
                    **changed,
                    **(
                        self.preprocessing_params.params.values
                        if self.preprocessing_method is not None
                        else {}
                    ),
                }
            )
        self.tracking_params.params.acknowledge_changes()

    def start_protocol(self):
        """Reset data accumulator when starting the protocol."""
        self.acc_tracking.reset()
        self.gui_timer.stop()
        try:
            self.estimator.reset()
            self.estimator.log.reset()
        except AttributeError:
            pass
        super().start_protocol()
        self.gui_timer.start(1000 // 60)

    def end_protocol(self, save=True):
        """Save tail position and dynamic parameters and terminate.

        """
        if save:
            # Save image of the fish:
            self.window_main.camera_display.save_image(
                name=self.filename_base() + "img.png"
            )
            self.dc.add_static_data(
                self.filename_prefix() + "img.png", "tracking/image"
            )

            # Save log and estimators:
            self.save_log(self.acc_tracking, "behavior_log")
            try:
                self.save_log(self.estimator.log, "estimator_log")
            except AttributeError:
                pass
        try:
            self.estimator.log.reset()
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
        self.protocol.sig_protocol_started.connect(self.acc_tracking.reset)

    def wrap_up(self, *args, **kwargs):
        """

        Parameters
        ----------
        *args :
            
        **kwargs :
            

        Returns
        -------

        """
        self.camera.kill_event.set()

        for q in [self.camera.frame_queue, self.frame_dispatchers[0].gui_queue]:
            q.clear()

        for dispatcher in self.frame_dispatchers:
            dispatcher.join()

        super().wrap_up(*args, **kwargs)


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
        self.camera.join()
        for dispatcher in self.frame_dispatchers:
            dispatcher.join()


class SwimmingRecordingExperiment(CameraExperiment):
    """Experiment where the fish is recorded while it is moving"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, camera_queue_mb=500, **kwargs)
        self.logger.info("Motion recording experiment")
        self.processing_params_queue = Queue()
        self.signal_recording = Event()
        self.signal_start_recording = Event()
        self.finished_signal = Event()

        self.frame_dispatcher = MovingFrameDispatcher(
            in_frame_queue=self.camera.frame_queue,
            finished_signal=self.camera.kill_event,
            signal_recording=self.signal_recording,
            signal_start_recording=self.signal_start_recording,
            processing_parameter_queue=self.processing_params_queue,
            gui_framerate=20,
        )

        self.frame_recorder = VideoWriter(
            self.folder_name, self.frame_dispatcher.save_queue, self.finished_signal
        )

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
        self.signal_start_recording.set()
        self.signal_recording.set()
        super().start_protocol()

    def wrap_up(self, *args, **kwargs):
        """ Ends all the processes in the application

        """
        super().wrap_up(*args, **kwargs)
        self.frame_dispatcher.join()
        self.frame_recorder.join()

    def end_protocol(self, save=True):
        """Save tail position and dynamic parameters. Reset what is necessary

        """
        self.frame_recorder.reset_signal.set()
        self.signal_recording.clear()
        try:
            recorded_filename = self.frame_recorder.filename_queue.get(timeout=0.01)
            self.dc.add_static_data(recorded_filename, "tracking/recorded_video")

        except Empty:
            pass

        if save:
            self.save_log(self.frametime_acc, "frametimes")

        self.frametime_acc.reset()
        super().end_protocol(save)
