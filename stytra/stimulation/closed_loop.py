import numpy as np
from stytra.tracking import DataAccumulator


class VigourMotionEstimator:
    def __init__(self, data_acc, vigour_window=50, gain=1):
        assert(isinstance(data_acc, DataAccumulator))
        self.data_acc = data_acc
        self.vigour_window = vigour_window
        self.gain = gain

    def get_velocity(self):
        return self.gain * np.std(self.data_acc.get_last_n(self.vigour_window)[:,1])