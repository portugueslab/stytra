import cv2
import numpy as np
from numba import vectorize, uint8, jit
import filterpy.kalman

from stytra.tracking.tail import find_fish_midline
from stytra.tracking import ParametrizedImageproc
from stytra.tracking.preprocessing import BackgorundSubtractor
from stytra.tracking.tail import find_direction, _next_segment

from itertools import chain
from scipy.linalg import block_diag


class FishTrackingMethod(ParametrizedImageproc):
    def __init__(self):
        super().__init__(name="tracking_fish_params")
        self.add_params(
            function="fish",
            n_fish_max=3,
            n_segments=10,
            threshold_eyes=dict(type="int", limits=(0, 255), value=30),
            bg_preresize=2,
            bglearning_rate=0.04,
            reset=False,
            bglearn_every=400,
            bgdif_threshold=10,
            fish_target_area=150,
            fish_area_std=60,
            fish_length=10.5,
            margin_fish=10,
            tail_track_window=3,
            tail_seglen=2.5,
            display_processed=dict(type="int", limits=(0, 2), value=0),
        )
        self.accumulator_headers = None
        self.data_log_name = "fish_track"
        self.bg_subtractor = BackgorundSubtractor()
        self.track_state = None
        self.bg_im = None
        self.previous_fish = []
        self.idx_book = None
        self.dilation_kernel = np.ones((3, 3), dtype=np.uint8)
        self.recorded = None
        self.diagnostic_image = None
        self.reset_state()

    def reset_state(self):
        self.accumulator_headers = list(
            chain.from_iterable(
                [
                    [
                        "f{:d}_x".format(i_fish),
                        "f{:d}_vx".format(i_fish),
                        "f{:d}_y".format(i_fish),
                        "f{:d}_vy".format(i_fish),
                        "f{:d}_theta".format(i_fish),
                    ]
                    + [
                        "f{:d}_theta_{:02d}".format(i_fish, i)
                        for i in range(self.params["n_segments"]-2)
                    ]
                    for i_fish in range(self.params["n_fish_max"])
                ]
            )
        )

        self.monitored_headers = ["f{:d}_theta".format(i_fish) for i_fish in range(self.params["n_fish_max"])]
        self.bg_subtractor = BackgorundSubtractor()
        self.previous_fish = []
        self.idx_book = IndexBooking(self.params["n_fish_max"])
        self.recorded = np.full(
            (self.params["n_fish_max"], 4 + self.params["n_segments"]), np.nan
        )

    def detect(self, frame, **new_params):

        # if the parameters affecting the dimensions of the result changed,
        # reset everything
        if (
            new_params["reset"]
            or new_params["n_fish_max"] != self.params["n_fish_max"]
            or self.params["n_segments"] != new_params["n_segments"]
        ):
            self.reset_state()
        self.update_params(**new_params)
        inv_thresh_eyes = 255 - self.params["threshold_eyes"]

        # update the previously-detected fish using the Kalman filter
        for pfish in self.previous_fish:
            pfish.predict()

        # subtract background
        bg = (
            self.bg_subtractor.process(
                frame, self.params["bglearning_rate"], self.params["bglearn_every"]
            )
            > self.params["bgdif_threshold"]
        ).view(dtype=np.uint8)

        # find regions where there is a difference with the backgorund
        n_comps, labels, stats, centroids = cv2.connectedComponentsWithStats(
            (bg).view(dtype=np.uint8)
        )

        # iterate through all the regions different from the backgorund and try
        # to find fish
        new_fish = []
        for row, centroid in zip(stats, centroids):
            # check if the contour is fish-sized and central enough
            if not (
                (
                    self.params["fish_target_area"] - self.params["fish_area_std"]
                    < row[cv2.CC_STAT_AREA]
                    < self.params["fish_target_area"] + self.params["fish_area_std"]
                )
                and (row[cv2.CC_STAT_LEFT] - self.params["margin_fish"] >= 0)
                and (
                    row[cv2.CC_STAT_LEFT]
                    + row[cv2.CC_STAT_WIDTH]
                    + self.params["margin_fish"]
                    < frame.shape[1]
                )
                and (row[cv2.CC_STAT_TOP] - self.params["margin_fish"] >= 0)
                and (
                    row[cv2.CC_STAT_TOP]
                    + row[cv2.CC_STAT_HEIGHT]
                    + self.params["margin_fish"]
                    < frame.shape[0]
                )
            ):
                continue

            # how much is this region shifted from the upper left corner of the image
            cent_shift = np.array(
                [
                    row[cv2.CC_STAT_LEFT] - self.params["margin_fish"],
                    row[cv2.CC_STAT_TOP] - self.params["margin_fish"],
                ]
            )

            slices = (
                slice(
                    row[cv2.CC_STAT_TOP] - self.params["margin_fish"],
                    row[cv2.CC_STAT_TOP]
                    + row[cv2.CC_STAT_HEIGHT]
                    + self.params["margin_fish"],
                ),
                slice(
                    row[cv2.CC_STAT_LEFT] - self.params["margin_fish"],
                    row[cv2.CC_STAT_LEFT]
                    + row[cv2.CC_STAT_WIDTH]
                    + self.params["margin_fish"],
                ),
            )

            # take the region and mask the backgorund away to aid detection
            fishdet = (255 - frame[slices]) * cv2.dilate(
                (bg[slices]).view(dtype=np.uint8), self.dilation_kernel
            )

            # estimate the position of the head and the approximate
            # direction of the tail
            this_fish = fish_start_n(fishdet, inv_thresh_eyes)

            # if no actual fish was found here, continue on to the next connected component
            if this_fish[0] == -1:
                continue

            # find the points of the tail
            points = find_fish_midline(
                fishdet,
                *this_fish,
                self.params["tail_track_window"],
                self.params["tail_seglen"],
                self.params["n_segments"]
            )

            # convert to angles
            angles = points_to_angles(points)
            if len(angles) == 0:
                continue

            # put the data together for one fish
            print(len(angles))
            this_fish = np.concatenate([cent_shift + np.array(points[0][:2]), angles])

            # check if this is a new fish, or it is an update of
            # a fish detected previously
            for past_fish in self.previous_fish:
                if past_fish.is_close(this_fish):
                    past_fish.update(this_fish)
                    break
            # the else exectes if no past fish is close
            else:
                new_fish.append(Fish(this_fish, self.idx_book))
        current_fish = []

        # remove fish not detected in two subsequent drames
        for pf in self.previous_fish:
            if pf.i_not_updated <= -1:
                self.idx_book.full[pf.i_ar] = False
            else:
                current_fish.append(pf)

        # add the new fish to the previously updated fish
        current_fish.extend(new_fish)
        self.previous_fish = current_fish

        # serialize the fish data for queue communication
        for pf in self.previous_fish:
            self.recorded[pf.i_ar, :] = pf.serialize()

        # if a debugging image is to be shown, set it
        if self.params["display_processed"]:
            if self.params["display_processed"] == 1:
                self.diagnostic_image = (
                    frame < self.params["threshold_eyes"]
                ).view(dtype=np.uint8)
            else:
                self.diagnostic_image = bg

        return tuple(self.recorded.flatten())


class IndexBooking:
    """ Class that keeps track of which array columns
    are free to put in fish data

    """

    def __init__(self, n_max=3):
        self.full = np.zeros(n_max, dtype=np.bool)

    def get_next(self):
        i_next = np.argmin(self.full)
        self.full[i_next] = True
        return i_next


class Fish:
    """ Class for Kalman-filtered tracking of individual fish

    """

    def __init__(
        self,
        initial_state,
        idx_book,
        pos_std=1.0,
        angle_std=np.pi / 10,
        pred_coef=3,
        filter_tail=False,
    ):
        self.i_not_updated = -1
        self.i_ar = idx_book.get_next()
        self.n_dof = len(initial_state) if filter_tail else 3

        # the position will be Kalman-filtered
        self.f = filterpy.kalman.KalmanFilter(dim_x=self.n_dof * 2, dim_z=self.n_dof)

        uncertanties = np.array(
            [pos_std, pos_std] + [angle_std for _ in range(self.n_dof - 2)]
        )
        self.f.x[::2, 0] = initial_state[:self.n_dof]
        self.f.F = block_diag(
            *[np.array([[1.0, 1.0], [0.0, 1.0]]) for _ in range(self.n_dof)]
        )
        self.f.R = np.diag(uncertanties)
        self.f.P = np.diag(np.ravel(np.column_stack((uncertanties, uncertanties))))

        self.f.Q = block_diag(
            *[
                filterpy.common.Q_discrete_white_noise(2, 0.02, uc * pred_coef)
                for uc in self.f.R[0]
            ]
        )
        self.f.H[:, ::2] = np.eye(self.n_dof)

        self.unfiltered = initial_state[self.n_dof:]

    def predict(self):
        self.f.predict()
        self.i_not_updated -= 1

    def update(self, new_fish_state):
        self.f.update(new_fish_state[: self.n_dof])
        self.unfiltered[:] = new_fish_state[self.n_dof:]
        self.i_not_updated = 0

    def serialize(self):
        return np.concatenate([self.f.x.flatten(), self.unfiltered])

    def is_close(self, new_fish, n_px=5):
        """ Check whether the new coordinates are
        within a certain number of pixels of the old estimate
        """
        dists = np.array([(new_fish[i] - self.f.x[i * 2]) for i in range(2)])
        return np.sum(dists ** 2) < n_px ** 2


@vectorize([uint8(uint8, uint8)])
def absdif(x, y):
    """

    Parameters
    ----------
    x :
        
    y :
        

    Returns
    -------

    """
    if x > y:
        return x - y
    else:
        return y - x


@jit(nopython=True)
def points_to_angles(points):
    angles = np.empty(len(points) - 1, dtype=np.float64)
    for i, (p1, p2) in enumerate(zip(points[0:-1], points[1:])):
        angles[i] = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    return angles


def fish_start_n(mask, take_min=100):
    """Find the centre of head of the fish

    Parameters
    ----------
    mask :
        param take_min:
    take_min :
         (Default value = 100)

    Returns
    -------

    """
    # take the centre of mass of only the darkest parts, the eyes and the
    mom = cv2.moments(np.maximum(mask, take_min) - take_min)  #
    if mom["m00"] == 0:
        return np.array([-1, -1, 0])
    y0 = mom["m01"] / mom["m00"]
    x0 = mom["m10"] / mom["m00"]
    angle = np.arctan2(mask.shape[0] / 2 - y0, mask.shape[1] / 2 - x0)
    return np.array([x0, y0, angle])
