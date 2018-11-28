import numpy as np
import datetime

from stytra.collectors import EstimatorLog, QueueDataAccumulator


def rot_mat(theta):
    """The rotation matrix for an angle theta """
    return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])


class Estimator:
    def __init__(self, acc_tracking: QueueDataAccumulator):
        self.acc_tracking = acc_tracking


class VigorMotionEstimator(Estimator):
    def __init__(self, *args, vigor_window=0.050, base_gain=-12, **kwargs):
        super().__init__(*args, **kwargs)
        self.vigor_window = vigor_window
        self.last_dt = 1 / 500.
        self.log = EstimatorLog(["vigor"])
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
        vigor_n_samples = max(int(round(self.vigor_window / self.last_dt)), 2)
        n_samples_lag = max(int(round(lag / self.last_dt)), 0)
        past_tail_motion = self.acc_tracking.get_last_n(
            vigor_n_samples + n_samples_lag
        )[0:vigor_n_samples]
        new_dt = (past_tail_motion[-1, 0] - past_tail_motion[0, 0]) / vigor_n_samples
        if new_dt > 0:
            self.last_dt = new_dt
        vigor = np.nanstd(np.array(past_tail_motion[:, 1]))
        if np.isnan(vigor):
            vigor = 0

        if self.log.get_last_n(1)[0, 0] < past_tail_motion[-1, 0]:
            self.log.update_list((past_tail_motion[-1, 0], vigor))
        return vigor * self.base_gain


class PositionEstimator(Estimator):
    def __init__(self, *args, calibrator, **kwargs):
        super().__init__(*args, **kwargs)
        self.calibrator = calibrator
        self.log = EstimatorLog(["x", "y", "theta"])

    def get_camera_position(self):
        past_coords = {
            name: value
            for name, value in zip(
                self.acc_tracking.header_list, self.acc_tracking.get_last_n(1)[0, :]
            )
        }
        return past_coords["f0_x"], past_coords["f0_y"], past_coords["f0_theta"]

    def get_position(self):
        past_coords = {
            name: value
            for name, value in zip(
                self.acc_tracking.header_list, self.acc_tracking.get_last_n(1)[0, :]
            )
        }
        if self.calibrator.cam_to_proj is None or not np.isfinite(
            past_coords["f0_x"]
        ):
            self.log.update_list((past_coords["t"], -1, -1, 0))
            return -1, -1, 0

        projmat = np.array(self.calibrator.cam_to_proj)
        x, y = projmat @ np.array([past_coords["f0_x"], past_coords["f0_y"], 1.0])
        theta = np.arctan2(
            *(
                projmat[:, :2]
                @ np.array(
                    [np.cos(past_coords["f0_theta"]), np.sin(past_coords["f0_theta"])]
                )[::-1]
            )
        )
        self.log.update_list((past_coords["t"], y, x, theta))
        return y, x, theta


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
