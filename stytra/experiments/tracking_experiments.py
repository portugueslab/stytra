import traceback

import numpy as np
from multiprocessing import Queue, Event
from pathlib import Path

from stytra.experiments import VisualExperiment
from stytra.gui.container_windows import (
    CameraExperimentWindow,
    TrackingExperimentWindow,
)
from stytra.hardware.video import (
    CameraControlParameters,
    VideoControlParameters,
    VideoFileSource,
    CameraSource,
)

# imports for tracking
from stytra.collectors import (
    QueueDataAccumulator,
    EstimatorLog,
    FramerateQueueAccumulator,
)
from stytra.tracking.tracking_process import TrackingProcess, DispatchProcess
from stytra.tracking.pipelines import Pipeline
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from stytra.experiments.fish_pipelines import pipeline_dict

from stytra.stimulation.estimators import estimator_dict

from stytra.hardware.video.write import H5VideoWriter, StreamingVideoWriter

import sys
from typing import *


class CameraVisualExperiment(VisualExperiment):
    """
    General class for Experiment that need to handle a camera.
    It implements a view of frames from the camera in the control GUI, and the respective parameters.
    For debugging it can be used with a video read from file with the VideoFileSource class.
    """

    def __init__(
        self,
        *args,
        camera: dict,
        camera_queue_mb: int = 100,
        recording: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Parameters
        ----------
        camera
            dictionary containing the parameters for the camera setup (i.e. for offline processing it would contain
            an entry 'video_file' with the path to the video).
        camera_queue_mb
            the maximum size of frames that are kept at once, if the limit is exceeded, frames will be dropped.
        recording
            dictionary containing the parameters for the recording (i.e. to save to an mp4 file, add the 'extension'
            entry with the 'mp4' value). If None, no recording is performed.
        """
        super().__init__(*args, **kwargs)
        if camera.get("video_file", None) is None:
            self.camera = CameraSource(
                camera["type"],
                rotation=camera.get("rotation", 0),
                downsampling=camera.get("downsampling", 1),
                roi=camera.get("roi", (-1, -1, -1, -1)),
                max_mbytes_queue=camera_queue_mb,
                camera_params=camera.get("camera_params", dict()),
            )
            self.camera_state = CameraControlParameters(tree=self.dc)
        else:
            self.camera = VideoFileSource(
                camera["video_file"],
                rotation=camera.get("rotation", 0),
                max_mbytes_queue=camera_queue_mb,
            )
            self.camera_state = VideoControlParameters(tree=self.dc)

        self.acc_camera_framerate = FramerateQueueAccumulator(
            self,
            queue=self.camera.framerate_queue,
            goal_framerate=camera.get("min_framerate", None),
            name="camera",  # TODO implement no goal
        )

        # New parameters are sent with GUI timer:
        self.gui_timer.timeout.connect(self.send_gui_parameters)
        self.gui_timer.timeout.connect(self.acc_camera_framerate.update_list)

        self.recording = recording
        if recording is not None:
            self._setup_recording(
                kbit_framerate=recording.get("kbit_rate", 1000),
                extension=recording["extension"],
            )

    def reset(self) -> None:
        super().reset()
        self.acc_camera_framerate.reset()

    def initialize_plots(self) -> None:
        super().initialize_plots()

    def send_gui_parameters(self) -> None:
        self.camera.control_queue.put(self.camera_state.params.changed_values())
        self.camera_state.params.acknowledge_changes()

    def start_experiment(self) -> None:
        """ """
        self.go_live()
        super().start_experiment()

    def start_protocol(self) -> None:
        """
        Starts the recording if the recording parameters are set.
        """
        if self.recording is not None:
            # Slight work around, the problem is in when set_id() is updated.
            # See issue #71.
            p = Path()
            fb = p.joinpath(
                self.folder_name, self.current_timestamp.strftime("%H%M%S") + "_"
            )
            self.dc.add_static_data(fb, "recording/filename")
            self._start_recording(fb)

        super().start_protocol()

    def end_protocol(self, save: bool = True) -> None:
        """
        Stops the recording if the recording parameters are set.
        """
        if self.recording is not None:
            self._stop_recording()

        super().end_protocol(save=save)

    def make_window(self) -> None:
        """ """
        self.window_main = CameraExperimentWindow(experiment=self)
        self.window_main.construct_ui()
        self.window_main.show()
        self.restore_window_state()
        self.initialize_plots()

    def go_live(self) -> None:
        """ """
        sys.excepthook = self.excepthook
        self.camera.start()

    def wrap_up(self, *args, **kwargs) -> None:
        self.gui_timer.stop()
        super().wrap_up(*args, **kwargs)
        self.camera.kill_event.set()

        for q in [self.camera.frame_queue]:
            q.clear()

        self.camera.join()

    def _setup_frame_dispatcher(self, recording_event: Event = None) -> DispatchProcess:
        """
        Creates a dispatcher that handles the frames of the camera. It will trigger the recording (i.e. stop it) using
        the given 'recording_event' event.

        Parameters
        ----------
        recording_event
            The event used for recording (if relevant).
        """
        return DispatchProcess(
            self.camera.frame_queue, self.camera.kill_event, recording_event
        )

    def _setup_recording(
        self, kbit_framerate: int = 1000, extension: str = "mp4"
    ) -> None:
        """
        Does the necessary setup before performing the recording, such as creating events, setting up the dispatcher
        (via _setup_frame_dispatcher) and initialising the VideoWriter.

        Parameters
        ----------
        kbit_framerate
            the byte rate at which the video is encoded.
        extension
            the extension used at the end of the video file.
        """
        self.recording_event = Event()
        self.reset_event = Event()
        self.finish_event = Event()

        self.frame_dispatcher = self._setup_frame_dispatcher(self.recording_event)
        self.frame_dispatcher.start()

        if extension == "h5":
            self.frame_recorder = H5VideoWriter(
                input_queue=self.frame_dispatcher.frame_copy_queue,
                recording_event=self.recording_event,
                reset_event=self.reset_event,
                finish_event=self.finish_event,
                log_format=self.log_format,
            )
        else:
            self.frame_recorder = StreamingVideoWriter(
                input_queue=self.frame_dispatcher.frame_copy_queue,
                recording_event=self.recording_event,
                reset_event=self.reset_event,
                finish_event=self.finish_event,
                kbit_rate=kbit_framerate,
                log_format=self.log_format,
            )

        self.frame_recorder.start()

    def _start_recording(self, filename: str) -> None:
        """
        Pushes the filename to the queue and sets the recording event in order to start the recording.

        Parameters
        ----------
        filename
            a unique identifier that will be added to the video file.
        """
        self.frame_recorder.filename_queue.put(filename)
        self.recording_event.set()

    def _stop_recording(self) -> None:
        """
        Stops the recording by clearing the recording event.
        """
        self.recording_event.clear()

    def _finish_recording(self) -> None:
        """
        Finishes the recording process and joins the frame recorder.
        """
        self.frame_recorder.finish_event.set()
        self.frame_recorder.join()

    def excepthook(self, exctype, value, tb) -> None:
        if self.recording is not None:
            self._finish_recording()

        traceback.print_tb(tb)
        print("{0}: {1}".format(exctype, value))
        self.camera.kill_event.set()
        self.camera.join()


class TrackingExperiment(CameraVisualExperiment):
    """
    Abstract class for an experiment which contains tracking.

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
    """

    def __init__(
        self,
        *args,
        tracking: dict,
        recording: Optional[Dict[str, Any]] = None,
        second_output_queue: Queue = None,
        **kwargs
    ) -> None:
        """
        tracking
            containing fields:  tracking_method
                                estimator: can be vigor for embedded fish, position
                                    for freely-swimming, or a custom subclass of Estimator
        recording
            dictionary containing the parameters for the recording (i.e. to save to an mp4 file, add the 'extension'
            entry with the 'mp4' value). If None, no recording is performed.
        data_name
            name of the data in the final experiment log (defined in the child).
        """

        self.processing_params_queue = Queue()
        self.second_output_queue = second_output_queue
        self.tracking_output_queue = NamedTupleQueue()
        self.finished_sig = Event()

        self.pipeline_cls = (
            pipeline_dict.get(tracking["method"], None)
            if isinstance(tracking["method"], str)
            else tracking["method"]
        )

        super().__init__(recording=recording, *args, **kwargs)
        self.arguments.update(locals())

        if self.pipeline_cls is None:
            raise NameError("The selected tracking method does not exist!")
        self.pipeline = self.pipeline_cls()
        assert isinstance(self.pipeline, Pipeline)
        self.pipeline.setup(tree=self.dc)

        if recording is None:
            # start frame dispatcher process:
            self.frame_dispatcher = self._setup_frame_dispatcher()
            self.frame_dispatcher.start()

        self.acc_tracking = QueueDataAccumulator(
            name="tracking",
            experiment=self,
            data_queue=self.tracking_output_queue,
            monitored_headers=self.pipeline.headers_to_plot,
        )
        self.acc_tracking.sig_acc_init.connect(self.refresh_plots)

        # Create and connect framerate accumulator.
        self.acc_tracking_framerate = FramerateQueueAccumulator(
            self,
            queue=self.frame_dispatcher.framerate_queue,
            name="tracking",
            goal_framerate=kwargs["camera"].get("min_framerate", None),
        )

        self.gui_timer.timeout.connect(self.acc_tracking_framerate.update_list)

        # Data accumulator is updated with GUI timer:
        self.gui_timer.timeout.connect(self.acc_tracking.update_list)

        # Tracking is reset at experiment start:
        self.protocol_runner.sig_protocol_started.connect(self.acc_tracking.reset)

        est_type = tracking.get("estimator", None)
        if est_type is None:
            est = None
        elif isinstance(est_type, str):
            est = estimator_dict.get(est_type, None)
        else:
            est = est_type

        if est is not None:
            self.estimator_log = EstimatorLog(experiment=self)
            self.estimator = est(
                self.acc_tracking,
                experiment=self,
                **tracking.get("estimator_params", {})
            )
            self.estimator_log.sig_acc_init.connect(self.refresh_plots)
        else:
            self.estimator = None

    def _setup_frame_dispatcher(self, recording_event: Event = None) -> TrackingProcess:
        """
        Initialises and returns a dispatcher.
        Can be extended by subclasses to initialise their own dispatcher.

        Parameters
        ----------
        recording_event
            event used to signal the start and end of the recording.
        """
        return TrackingProcess(
            in_frame_queue=self.camera.frame_queue,
            finished_signal=self.camera.kill_event,
            pipeline=self.pipeline_cls,
            processing_parameter_queue=self.processing_params_queue,
            output_queue=self.tracking_output_queue,
            second_output_queue=self.second_output_queue,
            recording_signal=recording_event,
            gui_framerate=20,
        )

    def reset(self) -> None:
        super().reset()
        self.acc_tracking_framerate.reset()
        self.acc_tracking.reset()
        if self.estimator is not None:
            self.estimator.reset()
            self.estimator_log.reset()

    def make_window(self) -> None:
        self.window_main = TrackingExperimentWindow(experiment=self)
        self.window_main.construct_ui()
        self.initialize_plots()
        self.window_main.show()
        self.restore_window_state()

    def initialize_plots(self) -> None:
        super().initialize_plots()
        self.refresh_plots()

    def refresh_plots(self) -> None:
        self.window_main.stream_plot.remove_streams()
        self.window_main.stream_plot.add_stream(self.acc_tracking)
        if self.estimator is not None:
            self.window_main.stream_plot.add_stream(self.estimator_log)

            # We display the stimulus log only if we have vigor estimator, meaning 1D closed-loop experiments
            self.window_main.stream_plot.add_stream(self.protocol_runner.dynamic_log)

        if self.stim_plot:  # but also if forced:
            self.window_main.stream_plot.add_stream(self.protocol_runner.dynamic_log)

    def send_gui_parameters(self) -> None:
        """
        Called upon gui timeout, put tracking parameters in the relative queue.
        """
        super().send_gui_parameters()
        self.processing_params_queue.put(self.pipeline.serialize_changed_params())

    def start_protocol(self) -> None:
        # Freeze the plots so the plotting does not interfere with
        # stimulus display
        if not self.window_main.stream_plot.frozen:
            self.window_main.stream_plot.toggle_freeze()

        # Reset data accumulator when starting the protocol.
        self.gui_timer.stop()

        super().start_protocol()

        self.gui_timer.start(1000 // 60)

    def end_protocol(self, save: bool = True) -> None:
        super().end_protocol(save)
        if self.window_main.stream_plot.frozen:
            self.window_main.stream_plot.toggle_freeze()

    def save_data(self) -> None:
        """Save tail position and dynamic parameters and terminate."""

        self.window_main.camera_display.save_image(
            name=self.filename_base() + "img.png"
        )
        self.dc.add_static_data(self.filename_prefix() + "img.png", "tracking/image")

        # Save log and estimators:
        self.save_log(self.acc_tracking, "behavior_log")
        try:
            self.save_log(self.estimator.log, "estimator_log")
        except AttributeError:
            pass

        super().save_data()

    def set_protocol(self, protocol: np.ndarray) -> None:
        """
        Connect new protocol start to resetting of the data accumulator.
        """
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.acc_tracking.reset)

    def wrap_up(self, *args, **kwargs) -> None:
        super().wrap_up(*args, **kwargs)

        self.frame_dispatcher.gui_queue.clear()

        self.frame_dispatcher.join()

    def excepthook(self, exctype, value, tb) -> None:
        """
        If an exception happens in the main loop, close all the processes so nothing is left hanging.
        """
        traceback.print_tb(tb)
        print("{0}: {1}".format(exctype, value))
        super()._finish_recording()
        self.camera.join()
        self.frame_dispatcher.join()
