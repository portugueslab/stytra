import numpy as np
import datetime

from stytra.bouter.angles import rot_mat
from stytra.bouter.kinematic_features import velocities_to_coordinates
from stytra.bouter.angles import smooth_tail_angles_series, reduce_to_pi
from stytra.collectors import EstimatorLog, QueueDataAccumulator


class VigourMotionEstimator:
    """ """

    def __init__(self, data_acc, vigour_window=0.050, base_gain=-30):
        assert isinstance(data_acc, QueueDataAccumulator)
        self.data_acc = data_acc
        self.vigour_window = vigour_window
        self.last_dt = 1 / 500.
        self.log = EstimatorLog(["vigour"])
        self.base_gain = base_gain

    def get_velocity(self, lag=0):
        """

        Parameters
        ----------
        lag :
             (Default value = 0)

        Returns
        -------

        """
        # TODO implement lag here
        vigour_n_samples = max(int(round(self.vigour_window / self.last_dt)), 2)
        n_samples_lag = max(int(round(lag / self.last_dt)), 0)
        past_tail_motion = self.data_acc.get_last_n(vigour_n_samples + n_samples_lag)[
            0:vigour_n_samples
        ]
        new_dt = (past_tail_motion[-1, 0] - past_tail_motion[0, 0]) / vigour_n_samples
        if new_dt > 0:
            self.last_dt = new_dt
        vigor = np.std(np.array(past_tail_motion[:, 1]))
        self.log.update_list((past_tail_motion[-1, 0], vigor))
        return vigor * self.base_gain

    # n_samples_lag = max(int(round(lag / self.last_dt)), 0)
    # past_tail_motion = self.data_acc.get_last_n(vigour_n_samples + n_samples_lag)[
    #     0:vigour_n_samples]
    # new_dt = (past_tail_motion[-1, 0] - past_tail_motion[
    #     0, 0]) / vigour_n_samples
    # if new_dt > 0:
    #     self.last_dt = new_dt
    # return np.std(past_tail_motion[:, 1])


class PositionEstimator:
    def __init__(self, data_acc, calibrator):
        self.data_acc = data_acc
        self.calibrator = calibrator
        self.log = EstimatorLog(["x", "y", "theta"])

    def get_position(self):
        past_coords = {
            name: value
            for name, value in zip(
                self.data_acc.get_last_n(1)[0, :], self.data_acc.header_list
            )
        }
        if self.calibrator.params["cam_to_proj"] is not None:
            projmat = np.array(self.calibrator.params["cam_to_proj"])
            y, x = projmat @ np.array([past_coords["x"], past_coords["y"], 1.0])
            theta = np.arctan2(
                *(
                    projmat
                    @ np.array(
                        [
                            np.sin(past_coords["theta"]),
                            np.cos(past_coords["theta"]),
                            1,
                            0,
                        ]
                    )
                )
            )
            self.log.update_list((past_coords["t"], x, y, theta))
            return y, x, 0

        self.log.update_list((past_coords["t"], -1, -1, 0))
        return -1, -1, 0


class LSTMLocationEstimator:
    """ """

    def __init__(
        self,
        data_acc,
        LSTM_file,
        PCA_weights=None,
        gains=[1, 1, 1],
        lstm_sample_rate=300,
        logging=True,
        model_px_per_mm=1,
        thresholds=(0.001, 0.001, 0.001),
        tail_first_mean=20,
        tail_thresholds=(0.01, 0.08),
    ):
        assert isinstance(data_acc, QueueDataAccumulator)
        self.data_acc = data_acc
        self.PCA_weights = PCA_weights
        self.model = load_model(LSTM_file)

        self.gains = gains
        self.lstm_sample_rate = lstm_sample_rate
        self.lstm_shape = self.model.input_shape[1][1]
        self.lstm_states = [
            np.zeros((1, self.lstm_shape)),
            np.zeros((1, self.lstm_shape)),
        ]
        self.thresholds = np.array(thresholds)
        self.tail_first_mean = tail_first_mean
        self.tail_thresholds = [np.sqrt(t) for t in tail_thresholds]
        self.tail_init = None

        self.processed_index = 0
        self.current_angle = 0
        self.current_coordinates = np.zeros(2)
        self.px_per_mm = model_px_per_mm

        if logging:
            self.log = EstimatorLog(headers=("v_ax", "v_lat", "v_ang", "theta"))
        else:
            self.log = None

    def reset(self):
        """ """
        self.processed_index = 0
        self.current_angle = 0
        self.current_coordinates = np.zeros(2)
        self.tail_init = None

    def get_displacements(self):
        """Calculates the position and rotation displacement using the LSTM
        model taking into account how much time has
        passed since the last estimation
        
        :return:

        Parameters
        ----------

        Returns
        -------

        """
        if self.log.starting_time is None:
            self.log.starting_time = self.data_acc.starting_time

        current_index = len(self.data_acc.stored_data)
        if current_index == 0 or self.processed_index == current_index:
            return np.r_[self.current_coordinates / self.px_per_mm, self.current_angle]

        all_data = np.array(
            self.data_acc.stored_data[self.processed_index : current_index]
        )
        tail = all_data[:, 2:]

        tail -= tail[:, :1]
        tail = smooth_tail_angles_series(reduce_to_pi(tail))[:, 1:]

        if self.tail_init is None:
            self.tail_init = np.mean(tail[: self.tail_first_mean, :], 0)

        tail -= self.tail_init
        tail[
            np.abs(tail)
            < (
                np.linspace(
                    self.tail_thresholds[0], self.tail_thresholds[1], tail.shape[1]
                )
                ** 2
            )[None, :]
        ] = 0

        if self.PCA_weights is not None:
            tail = tail @ self.PCA_weights

        Y, s1, s2 = self.model.predict([tail[None, :, :]] + self.lstm_states)
        self.lstm_states = [s1, s2]
        Y = Y[0]
        Y[np.abs(Y) < self.thresholds[None, :]] = 0

        displacement = velocities_to_coordinates(
            Y, start_angle=self.current_angle, cumulative_angle=False
        )

        self.current_coordinates += displacement[-1, :2]
        self.current_angle = displacement[-1, 2]

        if self.log is not None:
            for i_y in range(Y.shape[0]):
                self.log.update_list(
                    (
                        all_data[i_y, 0],
                        Y[i_y, 0],
                        Y[i_y, 1],
                        Y[i_y, 2],
                        displacement[i_y, 2],
                    )
                )

        self.processed_index = current_index

        return np.r_[self.current_coordinates / self.px_per_mm, self.current_angle]


class SimulatedLocationEstimator:
    """ """

    def __init__(self, bouts):
        self.bouts = bouts
        self.start_t = None
        self.i_bout = 0
        self.past_theta = 0
        self.current_coordinates = np.zeros(2)

    def get_displacements(self):
        """ """
        if self.start_t is None:
            self.start_t = datetime.datetime.now()

        dt = (datetime.datetime.now() - self.start_t).total_seconds()
        if self.i_bout < len(self.bouts) and dt > self.bouts[self.i_bout].t:
            this_bout = self.bouts[self.i_bout]
            delta = rot_mat(self.past_theta) @ np.array([this_bout.dx, this_bout.dy])
            self.current_coordinates += delta
            self.past_theta = self.past_theta + this_bout.theta
            self.i_bout += 1

        return np.r_[self.current_coordinates, self.past_theta]

    def reset(self):
        """ """
        self.current_coordinates = np.zeros(2)
        self.start_t = None
        self.i_bout = 0
        self.past_theta = 0
