import numpy as np
import datetime

from stytra.collectors import QueueDataAccumulator
from stytra.utilities import reduce_to_pi
from collections import namedtuple


def rot_mat(theta):
    """The rotation matrix for an angle theta """
    return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])


class Estimator:
    def __init__(self, acc_tracking: QueueDataAccumulator, experiment):
        self.exp = experiment
        self.log = experiment.estimator_log
        self.acc_tracking = acc_tracking

    def reset(self):
        self.log.reset()


class VigorMotionEstimator(Estimator):
    def __init__(self, *args, vigor_window=0.050, base_gain=-12, **kwargs):
        super().__init__(*args, **kwargs)
        self.vigor_window = vigor_window
        self.last_dt = 1 / 500.
        self.base_gain = base_gain
        self._output_type = namedtuple("s", "vigor")

    def get_velocity(self, lag=0):
        """

        Parameters
        ----------
        lag :
             (Default value = 0)

        Returns
        -------

        """
        vigor_n_samples = max(int(round(self.vigor_window / self.last_dt)), 2)
        n_samples_lag = max(int(round(lag / self.last_dt)), 0)
        if not self.acc_tracking.stored_data:
            return 0
        past_tail_motion = self.acc_tracking.get_last_n(
            vigor_n_samples + n_samples_lag
        )[0:vigor_n_samples]
        end_t = past_tail_motion.t.iloc[-1]
        start_t = past_tail_motion.t.iloc[ 0]
        new_dt = (end_t-start_t) / vigor_n_samples
        if new_dt > 0:
            self.last_dt = new_dt
        vigor = np.nanstd(np.array(past_tail_motion.tail_sum))
        if np.isnan(vigor):
            vigor = 0

        if len(self.log.times) == 0 or self.log.times[-1] < end_t:
            self.log.update_list(end_t, self._output_type(vigor))
        return vigor * self.base_gain


class PositionEstimator(Estimator):
    def __init__(self, *args, change_thresholds=None,
                 velocity_window=10, **kwargs):
        """ Uses the projector-to-camera calibration to give fish position in
        scree coordinates. If change_thresholds are set, update only the fish
        position after there is a big enough change (which prevents small
        oscillations due to tracking)

        :param args:
        :param calibrator:
        :param change_thresholds: a 3-tuple of thresholds, in px and radians
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.calibrator = self.exp.calibrator
        self.last_location = None
        self.past_values = None

        self.velocity_window = velocity_window
        self.change_thresholds = change_thresholds
        if change_thresholds is not None:
            self.change_thresholds = np.array(change_thresholds)

        self._output_type = namedtuple("f", ["x", "y", "theta"])

    def get_camera_position(self):
        past_coords = {
            name: value
            for name, value in zip(
                self.acc_tracking.columns, self.acc_tracking.get_last_n(1)[0, :]
            )
        }
        return past_coords["f0_x"], past_coords["f0_y"], past_coords["f0_theta"]

    def get_velocity(self):
        vel = np.diff(self.acc_tracking.get_last_n(self.velocity_window)[["f0_x", "f0_y"]].values, 0)
        return np.sqrt(np.sum(vel**2))
    
    def get_istantaneous_velocity(self):
        vel_xy = self.acc_tracking.get_last_n(self.velocity_window)[["f0_vx", "f0_vy"]].values
        return np.sqrt(np.sum(vel_xy**2))

    def reset(self):
        super().reset()
        self.past_values = None

    def get_position(self):
        if len(self.acc_tracking.stored_data) == 0 or not np.isfinite(self.acc_tracking.stored_data[-1].f0_x):
            o = self._output_type(np.nan, np.nan, np.nan)
            return o


        past_coords = self.acc_tracking.stored_data[-1]
        t = self.acc_tracking.times[-1]

        if not self.calibrator.cam_to_proj is None:
            projmat = np.array(self.calibrator.cam_to_proj)
            if projmat.shape != (2, 3):
                projmat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

            x, y = projmat @ np.array([past_coords.f0_x, past_coords.f0_y, 1.0])

            theta = np.arctan2(
                *(
                    projmat[:, :2]
                    @ np.array(
                        [np.cos(past_coords.f0_theta), np.sin(past_coords.f0_theta)]
                    )[::-1]
                )
            )
        else:
            x, y, theta = past_coords.f0_x, past_coords.f0_y, past_coords.f0_theta

        c_values = np.array((y, x, theta))

        if self.change_thresholds is not None:

            if self.past_values is None:
                self.past_values = np.array(c_values)
            else:
                deltas = c_values - self.past_values
                deltas[2] = reduce_to_pi(deltas[2])
                sel = np.abs(deltas) > self.change_thresholds
                self.past_values[sel] = c_values[sel]
                c_values = self.past_values

        logout = self._output_type(*c_values)
        self.log.update_list(t, logout)

        return c_values

    
estimator_dict = dict(position=PositionEstimator,
                      vigor=VigorMotionEstimator)
