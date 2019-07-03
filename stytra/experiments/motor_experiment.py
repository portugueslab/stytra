from stytra.experiments.tracking_experiments import TrackingExperiment
from stytra.tracking.tracking_process import TrackingProcessMotor
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from stytra.hardware.motor.motor_process import ReceiverProcess
from stytra.collectors import QueueDataAccumulator, EstimatorLog, FramerateQueueAccumulator

class Motor_Experiment(TrackingExperiment):
    """"""
    def __init__(self):
        self.tracked_position_queue = NamedTupleQueue()
        # self.motor_position_queue = NamedTupleQueue()
        super().__init__()
        # self.motor_pos_queue = NamedTupleQueue()
        self.motor_process = ReceiverProcess(dot_position_queue=self.tracked_position_queue,
                                             finished_event=self.camera.kill_event)
        self.motor_position_queue = self.motor_process.motor_position_queue

        self.acc_motor = QueueDataAccumulator(
            name="motor",
            experiment=self,
            data_queue=self.motor_position_queue,
            # monitored_headers=self.pipeline.headers_to_plot
        )

    def start_experiment(self):
        super().start_experiment()
        self.motor_process.run()

    def wrap_up(self, *args, **kwargs):
        super().wrap_up(*args, **kwargs)
        self.motor_process.join()

    def initialize_tracking_meth(self):
        self.frame_dispatcher = TrackingProcessMotor(
            second_output_queue=self.tracked_position_queue,
            in_frame_queue=self.camera.frame_queue,
            finished_signal=self.camera.kill_event,
            pipeline=self.pipeline_cls,
            processing_parameter_queue=self.processing_params_queue,
            output_queue=self.tracking_output_queue,
            gui_dispatcher=True,
            gui_framerate=20)


# exp = Motor_Experiment()
# exp.initialize_tracking_meth()