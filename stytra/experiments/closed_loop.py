from stytra.experiments.tracking_experiments import TrackingExperiment


class FreelySwimmingClosedLoop(TrackingExperiment):
    def __init__(self):
        super().__init__()
        self.position_estimator