import datetime
from collections import namedtuple
from typing import NamedTuple, Optional, Tuple

import numpy as np

from stytra.collectors import QueueDataAccumulator
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from stytra.utilities import reduce_to_pi


class Estimator:
    """
    An estimator is an object that estimate quantities required for the
    control of the stimulus (animal position/speed etc.) from the output
    stream of the tracking pipelines (position in pixels, tail angles, etc.).
    """

    def __init__(self, acc_tracking: QueueDataAccumulator, experiment):
        self.exp = experiment
        self.acc_tracking = acc_tracking
        self.output_queue = NamedTupleQueue()
        self._output_type = None

    def update(self):
        raise NotImplementedError

    def reset(self):
        pass


class VigorEstimate(NamedTuple):
    vigor: float


class VigorMotionEstimator(Estimator):
    """
    A very common way of estimating velocity of an embedded animal is
    vigor, computed as the standard deviation of the tail cumulative angle in a
    specified time window - generally 50 ms.
    """

    def __init__(self, *args, vigor_window=0.050, base_gain=-12, **kwargs):
        super().__init__(*args, **kwargs)
        self.vigor_window = vigor_window
        self.last_dt = 1 / 500.0
        self.base_gain = base_gain
        self._output_type = namedtuple("vigor_estimate", ("vigor",))

    def get_vigor(self):
        vigor_n_samples = max(int(round(self.vigor_window / self.last_dt)), 2)
        if not self.acc_tracking.stored_data:
            return 0
        past_tail_motion = self.acc_tracking.get_last_n(vigor_n_samples)[
            0:vigor_n_samples
        ]
        end_t = past_tail_motion.t.iloc[-1]
        start_t = past_tail_motion.t.iloc[0]
        new_dt = (end_t - start_t) / vigor_n_samples
        if new_dt > 0:
            self.last_dt = new_dt
        vigor = np.nanstd(np.array(past_tail_motion.tail_sum))
        if np.isnan(vigor):
            vigor = 0
        return end_t, vigor

    def update(self):
        end_t, vigor = self.get_vigor()
        self.output_queue.put(end_t, self._output_type(vigor))


class BoutEstimate(NamedTuple):
    is_bouting: bool


class BoutsEstimator(VigorMotionEstimator):
    def __init__(
        self, *args, bout_threshold=0.05, vigor_window=0.05, min_interbout=0.1, **kwargs
    ):
        super().__init__(*args, base_gain=1, **kwargs)
        self.bout_threshold = bout_threshold
        self.vigor_window = vigor_window
        self.min_interbout = min_interbout
        self.last_bout_t = None
        self._output_type = namedtuple("bouts", ("is_bouting",))

    def update(self):
        end_t, vigor = self.get_vigor()
        is_bouting = False
        if vigor > self.base_gain * self.bout_threshold:
            if (
                self.last_bout_t is None
                or (datetime.datetime.now() - self.last_bout_t).total_seconds()
                > self.min_interbout
            ):
                self.last_bout_t = datetime.datetime.now()
                is_bouting = True
        self.output_queue.put(end_t, self._output_type(is_bouting))


class EmbeddedBoutEstimate(NamedTuple):
    vigor: float
    theta: float
    bout_on: bool


class PositionEstimate(NamedTuple):
    x: float
    y: float
    theta: float


def _propagate_change_above_threshold(
    current_estimate: PositionEstimate,
    previous_estimate: Optional[PositionEstimate],
    thresholds: PositionEstimate,
) -> PositionEstimate:
    """Return updated components of a position if the component changed enough, otherwise return the old component"""
    if previous_estimate is None:
        return current_estimate

    return PositionEstimate(
        x=current_estimate.x
        if abs(current_estimate.x - previous_estimate.x) > thresholds.x
        else previous_estimate.x,
        y=current_estimate.x
        if abs(current_estimate.y - previous_estimate.y) > thresholds.y
        else previous_estimate.y,
        theta=current_estimate.x
        if abs(reduce_to_pi(current_estimate.theta - previous_estimate.theta))
        > thresholds.theta
        else previous_estimate.theta,
    )


class PositionEstimator(Estimator):
    def __init__(self, *args, change_thresholds:Optional[PositionEstimate]=None, velocity_window:int=10, **kwargs):
        """Uses the projector-to-camera calibration to give fish position in
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
        self.previous_position = None

        self.velocity_window = velocity_window
        self.change_thresholds = change_thresholds

        self._output_type = PositionEstimate

    def get_camera_position(self):
        past_coords = {
            name: value
            for name, value in zip(
                self.acc_tracking.columns, self.acc_tracking.get_last_n(1)[0, :]
            )
        }
        return past_coords["f0_x"], past_coords["f0_y"], past_coords["f0_theta"]

    def get_velocity(self):
        vel = np.diff(
            self.acc_tracking.get_last_n(self.velocity_window)[["f0_x", "f0_y"]].values,
            0,
        )
        return np.sqrt(np.sum(vel ** 2))

    def reset(self):
        self.previous_position = None

    def get_position(self) -> Tuple[float, PositionEstimate]:
        if len(self.acc_tracking.stored_data) == 0 or not np.isfinite(
            self.acc_tracking.stored_data[-1].f0_x
        ):
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

        current_position = PositionEstimate(x, y, theta)

        if self.change_thresholds is not None:
            if self.previous_position is None:
                self.previous_position = current_position

            current_position = _propagate_change_above_threshold(
                current_position, self.previous_position, self.change_thresholds
            )
            self.previous_position = current_position

        return t, current_position

    def update(self):
        self.output_queue.put(*self.get_position())


class SimulatedPositionEstimator(Estimator):
    def __init__(self, *args, motion, **kwargs):
        """Uses the projector-to-camera calibration to give fish position in
        scree coordinates. If change_thresholds are set, update only the fish
        position after there is a big enough change (which prevents small
        oscillations due to tracking)

        :param args:
        :param calibrator:
        :param change_thresholds: a 3-tuple of thresholds, in px and radians
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.motion = motion
        self._output_type = PositionEstimate

    def get_position(self) -> Tuple[float, PositionEstimate]:
        t = (datetime.datetime.now() - self.exp.t0).total_seconds()

        kt = PositionEstimate(
            *(np.interp(t, self.motion.t, self.motion[p]) for p in ("x", "y", "theta"))
        )
        return t, kt

    def update(self):
        self.output_queue.put(*self.get_position())


estimator_dict = dict(
    position=PositionEstimator, vigor=VigorMotionEstimator, bouts=BoutsEstimator
)
