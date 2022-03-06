from multiprocessing import Event, Process, Queue
from queue import Empty
from typing import Type

from stytra.collectors import QueueDataAccumulator
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from stytra.stimulation.estimators import Estimator


class EstimatorProcess(Process):
    def __init__(
        self,
        estimator_cls: Type[Estimator],
        tracking_queue: NamedTupleQueue,
        estimator_parameter_queue: Queue,
        finished_signal: Event,
    ):
        super().__init__()
        self.tracking_queue = tracking_queue
        self.tracking_output_queue = NamedTupleQueue()
        self.estimator_parameter_queue = estimator_parameter_queue
        self.estimator_queue = NamedTupleQueue()
        self.tracking_accumulator = QueueDataAccumulator(self.tracking_queue, self.tracking_output_queue)
        self.finished_signal = finished_signal
        self.estimator_cls = estimator_cls


    def update_estimator_params(self, estimator):
        while True:
            try:
                param_dict = self.estimator_parameter_queue.get(timeout=0.0001)
                estimator.update_params(param_dict)
            except Empty:
                break


    def run(self):
        estimator = self.estimator_cls(self.tracking_accumulator, self.estimator_queue)

        while not self.finished_signal.is_set():
            self.update_estimator_params(estimator)
            self.tracking_accumulator.update_list()
            estimator.update()
