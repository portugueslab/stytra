import numpy as np


class VigourMotionEstimator:
    def __init__(self, data_acc, vigour_window=50, gain=1):
        self.data_acc = data_acc
        self.vigour_window = vigour_window
        self.gain = gain

    def get_velocity(self):
        return self.gain * np.std(self.data_acc['tail_sum'][:-self.vigour_window])