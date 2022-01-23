from multiprocessing import Event, Process
from typing import Type

from stytra.collectors import QueueDataAccumulator
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from stytra.stimulation.estimators import Estimator


class EstimatorProcess(Process):
    def __init__(
        self,
        estimator_cls: Type[Estimator],
        tracking_queue: NamedTupleQueue,
        finished_signal: Event,
    ):
        super().__init__()
        self.tracking_queue = tracking_queue
        self.tracking_output_queue = NamedTupleQueue()
        self.estimator_queue = NamedTupleQueue()
        self.tracking_accumulator = QueueDataAccumulator(self.tracking_queue, self.tracking_output_queue)
        self.finished_signal = finished_signal
        self.estimator_cls = estimator_cls

    def run(self):
        estimator = self.estimator_cls(self.tracking_accumulator, self.estimator_queue)

        while not self.finished_signal.is_set():
            self.tracking_accumulator.update_list()
            estimator.update()
