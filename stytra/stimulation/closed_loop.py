import numpy as np
from stytra.tracking import QueueDataAccumulator
from keras.models import load_model
from bouter.kinematic_features import velocities_to_coordinates
from bouter.angles import smooth_tail_angles_series, reduce_to_pi
import datetime
from stytra.collectors import Accumulator


class EstimatorLog(Accumulator):
    def __init__(self, headers):
        self.header_list = ('t', ) + headers
        self.stored_data = []
        self.starting_time = 0

    def update_list(self, data):
        self.stored_data.append(data)

    def reset(self):
        self.starting_time = 0
        self.stored_data = []


class VigourMotionEstimator:
    def __init__(self, data_acc, vigour_window=0.050):
        assert(isinstance(data_acc, QueueDataAccumulator))
        self.data_acc = data_acc
        self.vigour_window = vigour_window
        self.last_dt = 1/500.

    def get_velocity(self, lag=0):
        # TODO implement lag here
        vigour_n_samples = max(int(round(self.vigour_window/self.last_dt)), 2)
        past_tail_motion = self.data_acc.get_last_n(vigour_n_samples)
        new_dt = (past_tail_motion[-1, 0] - past_tail_motion[0, 0])/vigour_n_samples
        if new_dt>0:
            self.last_dt = new_dt
        return np.std(past_tail_motion[:, 1])


class LSTMLocationEstimator:
    def __init__(self, data_acc, LSTM_file, PCA_weights=None,
                 gains=[1,1,1], update_interval=100, lstm_sample_rate=500,
                 logging=True):
        assert (isinstance(data_acc, QueueDataAccumulator))
        self.data_acc = data_acc
        self.PCA_weights = PCA_weights
        self.model = load_model(LSTM_file)
        self.n_past = self.model.input_shape[1]
        self.delta_t = datetime.timedelta(seconds=self.n_past/lstm_sample_rate)

        self.update_interval = update_interval
        self.gains = gains
        self.last_update = 0 # the position at which the last update occured
        self.past_coordinates = np.zeros((update_interval, 3))
        self.lstm_sample_rate = lstm_sample_rate

        self.first_t = None
        self.past_t = None
        self.past_coords = None

        if logging:
            self.log = EstimatorLog(headers=('v_ax',
                                             'v_lat',
                                             'v_ang',
                                             'middle_tail',
                                             'indexes_from_past_end'))
        else:
            self.log = None

    def reset(self):
        self.first_t = None
        self.past_t = None
        self.past_coords = None

    def get_coords(self):
        """ Calculates the position and rotation displacement using the LSTM
        model taking into account how much time has
        passeed since the last estimation

        :return:
        """
        if self.first_t is None:
            self.first_t = datetime.datetime.now()

        tail = self.data_acc.get_last_n(self.n_past)[:, 2:]
        tail -= tail[:, :1]
        tail = smooth_tail_angles_series(reduce_to_pi(tail))
        if self.PCA_weights is not None:
            tail = tail @ self.PCA_weights

        if tail.shape[0] != self.n_past:
            tail = np.pad(tail,
                          ((self.n_past-tail.shape[0], 0), (0,0)),
                          mode='constant')

        Y = self.model.predict(tail[None, :, :])[0]


        t_estimation = datetime.datetime.now()
        if self.past_t is not None:
            t_take_coords = t_estimation - self.delta_t
            t_from_past_end = (self.past_t-t_take_coords).total_seconds()
            indexes_from_past_end = int(t_from_past_end*self.lstm_sample_rate)

            start_coords = self.past_coords[-indexes_from_past_end, :]

        else:
            indexes_from_past_end = 0
            start_coords = np.zeros(3)

        self.past_t = t_estimation

        new_coordinates = start_coords + \
                          velocities_to_coordinates(Y,
                                                    start_angle=start_coords[2])
        self.past_coords = new_coordinates

        if self.log is not None:
            t = (t_estimation-self.first_t).total_seconds()
            self.log.update_list((t,
                                  Y[-1, 0],
                                  Y[-1, 1],
                                  Y[-1, 2],
                                  tail[-1, 5],
                                  indexes_from_past_end))

        return new_coordinates[-1]

