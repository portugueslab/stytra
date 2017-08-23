import numpy as np
from stytra.tracking import DataAccumulator
# from keras.models import load_model


class VigourMotionEstimator:
    def __init__(self, data_acc, vigour_window=50):
        assert(isinstance(data_acc, DataAccumulator))
        self.data_acc = data_acc
        self.vigour_window = vigour_window

    def get_velocity(self, lag=0):
        # TODO implement lag here
        return np.std(self.data_acc.get_last_n(self.vigour_window)[:, 1])


class LSTMMotionEstimator:
    def __init__(self, data_acc, LSTM_file, PCA_weights, gains=[1,1,1], delay=0):
        assert (isinstance(data_acc, DataAccumulator))
        self.data_acc = data_acc
        self.PCA_weights = PCA_weights
        self.model = load_model(LSTM_file)

    def get_displacement(self, delta_t_last):
        """ Calculates the position and rotation displacement using the LSTM
        model taking into account how much time has
        passeed since the last estimation

        :param delta_t_last:
        :return:
        """
        n_past = self.model.input_shape[1]
        tail = self.data_acc.get_last_n(n_past)[:, 1]

        Y = self.model.predict(tail @ self.PCA_weights)
        return Y