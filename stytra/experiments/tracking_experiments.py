import traceback

from multiprocessing import Queue, Event, Value, set_start_method
from queue import Empty

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
from stytra.collectors import QueueDataAccumulator, EstimatorLog, FramerateQueueAccumulator
from stytra.tracking.tracking_process import TrackingProcess
from stytra.tracking.pipelines import Pipeline
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from stytra.experiments.fish_pipelines import pipeline_dict

from stytra.stimulation.estimators import estimator_dict

from inspect import isclass

import sys


class CameraVisualExperiment(VisualExperiment):
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

        self.acc_camera_framerate = FramerateQueueAccumulator(self,
                                                              queue=self.camera.framerate_queue, goal_framerate=camera.get("min_framerate", None),
                                                              name="camera"  # TODO implement no goal
                                                              )

        # New parameters are sent with GUI timer:
        self.gui_timer.timeout.connect(self.send_gui_parameters)
        self.gui_timer.timeout.connect(self.acc_camera_framerate.update_list)

    def reset(self):
        super().reset()
        self.acc_camera_framerate.reset()

    def initialize_plots(self):
        super().initialize_plots()

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


class TrackingExperiment(CameraVisualExperiment):
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
        tracking: dict
            containing fields:  tracking_method
                                estimator: can be vigor for embedded fish, position
                                    for freely-swimming, or a custom subclass of Estimator

    Returns
    -------

    """

    def __init__(self, *args, tracking, **kwargs):
        """
        :param tracking_method: class with the parameters for tracking (instance
                                of TrackingMethod class, defined in the child);
        :param header_list: headers for the data accumulator (list of strings,
                            defined in the child);
        :param data_name:  name of the data in the final experiment log (defined
                           in the child).
        """

        self.processing_params_queue = Queue()
        self.tracking_output_queue = NamedTupleQueue()
        self.finished_sig = Event()
        super().__init__(*args, **kwargs)
        self.arguments.update(locals())

        self.pipeline_cls = pipeline_dict.get(tracking["method"], None) if isinstance(tracking["method"], str) else tracking["method"]

        self.frame_dispatcher = TrackingProcess(
                in_frame_queue=self.camera.frame_queue,
                finished_signal=self.camera.kill_event,
                pipeline=self.pipeline_cls,
                processing_parameter_queue=self.processing_params_queue,
                output_queue=self.tracking_output_queue,
                gui_dispatcher=True,
                gui_framerate=20,
            )
        if self.pipeline_cls is None:
            raise NameError("The selected tracking method does not exist!")
        self.pipeline = self.pipeline_cls()
        assert isinstance(self.pipeline, Pipeline)
        self.pipeline.setup(tree=self.dc)

        self.acc_tracking = QueueDataAccumulator(
            name="tracking",
            experiment=self,
            data_queue=self.tracking_output_queue,
            monitored_headers=self.pipeline.headers_to_plot
        )
        self.acc_tracking.sig_acc_init.connect(self.refresh_plots)

        # Data accumulator is updated with GUI timer:
        self.gui_timer.timeout.connect(self.acc_tracking.update_list)

        # Tracking is reset at experiment start:
        self.protocol_runner.sig_protocol_started.connect(self.acc_tracking.reset)

        # start frame dispatcher process:
        self.frame_dispatcher.start()

        est_type = tracking.get("estimator", None)
        if est_type is None:
            est = None
        elif isinstance(est_type, str):
            est = estimator_dict.get(est_type, None)
        else:
            est = est_type

        if est is not None:
            self.estimator_log = EstimatorLog(experiment=self)
            self.estimator = est(self.acc_tracking,
                                 experiment=self,
                                 **tracking.get("estimator_params", {}))
            self.estimator_log.sig_acc_init.connect(self.refresh_plots)
        else:
            self.estimator = None

        self.acc_tracking_framerate = FramerateQueueAccumulator(self,
                                                                queue=self.frame_dispatcher.framerate_queue, name="tracking",
                                                                goal_framerate=kwargs["camera"].get("min_framerate", None)
                                                                )

        self.gui_timer.timeout.connect(self.acc_tracking_framerate.update_list)

    def reset(self):
        super().reset()
        self.acc_tracking_framerate.reset()
        self.acc_tracking.reset()
        if self.estimator is not None:
            self.estimator_log.reset()

    def make_window(self):
        self.window_main = TrackingExperimentWindow(experiment=self)
        self.window_main.construct_ui()
        self.initialize_plots()
        self.window_main.show()
        self.restore_window_state()

    def initialize_plots(self):
        super().initialize_plots()
        self.refresh_plots()

    def refresh_plots(self):
        self.window_main.stream_plot.remove_streams()
        self.window_main.stream_plot.add_stream(self.acc_tracking)
        if self.estimator is not None:
            self.window_main.stream_plot.add_stream(self.estimator_log)

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
        self.processing_params_queue.put(self.pipeline.serialize_changed_params())

    def start_protocol(self):
        # Freeze the plots so the plotting does not interfere with
        # stimulus display
        if not self.window_main.stream_plot.frozen:
            self.window_main.stream_plot.toggle_freeze()

        # Reset data accumulator when starting the protocol.
        self.gui_timer.stop()

        if self.estimator is not None:
            self.estimator.reset()

        super().start_protocol()
        self.gui_timer.start(1000 // 60)

    def end_protocol(self, save=True):
        super().end_protocol(save)
        if self.window_main.stream_plot.frozen:
            self.window_main.stream_plot.toggle_freeze()

    def save_data(self):
        """Save tail position and dynamic parameters and terminate.

        """

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

        super().save_data()

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

        super().wrap_up(*args, **kwargs)

        self.frame_dispatcher.gui_queue.clear()

        self.frame_dispatcher.join()

    def excepthook(self, exctype, value, tb):
        """ If an exception happens in the main loop, close all the
        processes so nothing is left hanging.

        """
        traceback.print_tb(tb)
        print("{0}: {1}".format(exctype, value))
        self.finished_sig.set()
        self.camera.join()
        self.frame_dispatcher.join()
