import cv2
import numpy as np
from numba import jit
import filterpy.kalman

from stytra.tracking.tail import find_fish_midline
from stytra.tracking import ParametrizedImageproc
from stytra.tracking.preprocessing import BackgorundSubtractor

from itertools import chain
from scipy.linalg import block_diag

import logging
from lightparam import Param, Parametrized


class FishTrackingMethod(ParametrizedImageproc):
    def __init__(self):
        super().__init__()
        self.accumulator_headers = None
        self.monitored_headers = None
        self.data_log_name = "fish_track"
        self.bg_subtractor = BackgorundSubtractor()
        self.track_state = None
        self.bg_im = None
        self.previous_fish = []
        self.idx_book = None
        self.dilation_kernel = np.ones((3, 3), dtype=np.uint8)
        self.recorded = None
        self.diagnostic_image = None
        self.logger = logging.getLogger()
        self.params = Parametrized(name="tracking/fish", params=self.detect)
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
                        for i in range(self.params.n_segments - 1)
                    ]
                    for i_fish in range(self.params.n_fish_max)
                ]
            )
        ) + ["biggest_area"]
        self.monitored_headers = [
            "f{:d}_theta".format(i_fish)
            for i_fish in range(self.params.n_fish_max)
        ] + ["biggest_area"]
        self.bg_subtractor = BackgorundSubtractor()
        self.previous_fish = []

        # used for booking a spot for one of the potentially tracked fish
        self.idx_book = IndexBooking(self.params.n_fish_max)
        self.recorded = np.full(
            (self.params.n_fish_max, 5 + self.params.n_segments-1), np.nan
        )
        self.logger = logging.getLogger()

    def detect(self, frame,
               reset: Param(False),
               n_fish_max: Param(1, (1, 10)),
               n_segments: Param(10, (2, 30)),

               bg_downsample: Param(1, (1, 8)),
               bg_learning_rate: Param(0.04, (0.0, 1.0)),
               bg_learn_every: Param(400, (1, 10000)),
               bg_dif_threshold: Param(25, (0, 255)),

               threshold_eyes: Param(35, (0, 255)),

               pos_uncertainty: Param(1.0, (0, 10.0),
                                      desc="Uncertainty in pixels about the location of the head center of mass"),
               persist_fish_for: Param(2, (1, 50), desc="How many frames does the fish persist for if it is not detected"),
               prediction_uncertainty: Param(0.1, (0.0, 10.0)),

               fish_area: Param((100, 400), (1, 2500)),
               border_margin: Param(10, (0, 100)),
               tail_length: Param(50.5, (1.0, 200.0)),
               tail_track_window: Param(3, (3, 70)),

               display_processed: Param("raw", ["raw",
                                               "background difference",
                                               "thresholded background difference",
                                               "fish detection",
                                               "thresholded for eye and swim bladder"]),


               ):

        # if the parameters affecting the dimensions of the result changed,
        # reset everything
        if (
            reset
            or n_fish_max != self.params.n_fish_max
            or n_segments != self.params.n_segments
            or bg_downsample != self.params.bg_downsample
        ):
            self.reset_state()
            self.params.params.bg_downsample.value = bg_downsample
            self.params.params.n_segments.value = n_segments
            self.params.params.n_fish_max = n_fish_max

        # update the previously-detected fish using the Kalman filter
        for pfish in self.previous_fish:
            pfish.predict()

        if bg_downsample != 1:
            frame_small = cv2.resize(frame, None, fx=1/bg_downsample,
                                     fy=1/bg_downsample, interpolation=cv2.INTER_AREA)
        else:
            frame_small = frame

        area_scale = bg_downsample*bg_downsample

        # subtract background
        bg = (
            self.bg_subtractor.process(
                frame_small, bg_learning_rate, bg_learn_every
            ))
        bg_thresh = cv2.dilate((bg > bg_dif_threshold).view(dtype=np.uint8), self.dilation_kernel)

        # find regions where there is a difference with the background
        n_comps, labels, stats, centroids = cv2.connectedComponentsWithStats(
            bg_thresh
        )


        try:
            max_area = np.max(stats[1:, cv2.CC_STAT_AREA])*area_scale
        except ValueError:
            max_area = 0

        # iterate through all the regions different from the background and try
        # to find fish
        new_fish = []

        for row, centroid in zip(stats, centroids):
            # check if the contour is fish-sized and central enough
            if not fish_area[0] < row[cv2.CC_STAT_AREA] * area_scale < \
                   fish_area[1]:
                continue

            ftop, fleft, fheight, fwidth = (int(round(row[x] * bg_downsample))
                                            for x in
                                            [cv2.CC_STAT_TOP,
                                             cv2.CC_STAT_LEFT,
                                             cv2.CC_STAT_HEIGHT,
                                             cv2.CC_STAT_WIDTH])

            if not ((fleft - border_margin >= 0)
                and (fleft + fwidth + border_margin < frame.shape[1])
                and (ftop - border_margin >= 0)
                and (ftop + fheight + border_margin < frame.shape[0])):
                continue

            # how much is this region shifted from the upper left corner of the image
            cent_shift = np.array(
                [fleft - border_margin, ftop - border_margin])

            # takes the area around the head contour
            oftop, ofleft, ofheight, ofwidth = (row[x]
                                            for x in
                                            [cv2.CC_STAT_TOP,
                                             cv2.CC_STAT_LEFT,
                                             cv2.CC_STAT_HEIGHT,
                                             cv2.CC_STAT_WIDTH])

            oborder_margin = int(round(border_margin/bg_downsample))
            slices = (
                slice(
                    oftop - oborder_margin,
                    oftop
                    + ofheight
                    + oborder_margin,
                ),
                slice(
                    ofleft - oborder_margin,
                    ofleft + ofwidth + oborder_margin,
                ),
            )
            ocent_shift = np.array(
                [ofleft - border_margin, oftop - oborder_margin])

            # take the region and mask the background away to aid detection
            fishdet = bg[slices].copy()
            fishdet[bg_thresh[slices] == 0] = 0

            # estimate the position of the head and the approximate
            # direction of the tail
            head_coords = fish_start_n(fishdet, threshold_eyes)

            # if no actual fish was found here, continue on to the next connected component
            if head_coords[0] == -1:
                continue

            head_coords_up = (head_coords+ocent_shift)*bg_downsample

            theta = _fish_direction_n(frame, head_coords_up,
                                      int(round(tail_length/2)))

            # find the points of the tail
            points = find_fish_midline(
                bg,
                *head_coords_up,
                theta,
                tail_track_window,
                tail_length / n_segments,
                n_segments+1,
            )

            # convert to angles
            angles = np.mod(points_to_angles(points)+np.pi, np.pi*2)-np.pi
            if len(angles) == 0:
                self.logger.info("Tail not completely detectable")
                continue

            # also, make the angles continuous
            angles[1:] = np.unwrap(angles[1:] - angles[0])

            # put the data together for one fish
            head_coords = np.concatenate([np.array(points[0][:2]), angles])

            # check if this is a new fish, or it is an update of
            # a fish detected previously
            for past_fish in self.previous_fish:
                if past_fish.is_close(head_coords) and past_fish.i_not_updated < 0:
                    past_fish.update(head_coords)
                    break
            # the else executes if no past fish is close, so a new fish
            # has to be instantiated for this measurement
            else:
                new_fish.append(
                    Fish(head_coords, self.idx_book,
                         pred_coef=prediction_uncertainty,
                         pos_std=pos_uncertainty)
                )
        current_fish = []

        # remove fish not detected in two subsequent frames
        for pf in self.previous_fish:
            if pf.i_not_updated < -persist_fish_for:
                self.idx_book.full[pf.i_ar] = False
                self.recorded[pf.i_ar, :] = np.nan
            else:
                current_fish.append(pf)

        # add the new fish to the previously updated fish
        current_fish.extend(new_fish)
        self.previous_fish = current_fish

        # serialize the fish data for queue communication
        for pf in self.previous_fish:
            self.recorded[pf.i_ar, :] = pf.serialize()

        # if a debugging image is to be shown, set it
        if display_processed == "background difference":
            self.diagnostic_image = bg
        elif display_processed == "thresholded background difference":
            self.diagnostic_image = bg_thresh
        elif display_processed == "fish detection":
            fishdet = bg.copy()
            fishdet[bg_thresh == 0] = 0
            self.diagnostic_image = fishdet
        elif display_processed == "thresholded for eye and swim bladder":
            self.diagnostic_image = (np.maximum(bg, threshold_eyes) - threshold_eyes)

        return tuple(self.recorded.flatten()) + (max_area*1.0, )


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
        pred_coef=20,
    ):
        self.i_not_updated = 0
        self.i_ar = idx_book.get_next()
        self.n_dof = 2

        # the position will be Kalman-filtered
        self.f = filterpy.kalman.KalmanFilter(dim_x=self.n_dof * 2, dim_z=self.n_dof)

        uncertanties = np.array(
            [pos_std, pos_std]
        )
        self.f.x[::2, 0] = initial_state[: self.n_dof]
        self.f.F = block_diag(
            *[np.array([[1.0, 1.0], [0.0, 1.0]]) for _ in range(self.n_dof)]
        )
        self.f.R = np.diag(uncertanties)
        self.f.P = np.diag(np.ravel(np.column_stack((uncertanties, uncertanties))))

        self.f.Q = block_diag(
            *[  np.array([[0.,0.],[0., uc*pred_coef]])
                # filterpy.common.Q_discrete_white_noise(2, 0.01, uc * pred_coef)
                for uc in uncertanties
            ]
        )
        self.f.H[:, ::2] = np.eye(self.n_dof)

        self.unfiltered = initial_state[self.n_dof :]

    def predict(self):
        self.f.predict()
        self.i_not_updated -= 1

    def update(self, new_fish_state):
        self.f.update(new_fish_state[: self.n_dof])
        self.unfiltered[:] = new_fish_state[self.n_dof :]
        self.i_not_updated = 0

    def serialize(self):
        return np.concatenate([self.f.x.flatten(), self.unfiltered])

    def is_close(self, new_fish, n_px=12, d_theta=np.pi / 2):
        """ Check whether the new coordinates are
        within a certain number of pixels of the old estimate
        and within a certain angle
        """
        dists = np.array([(new_fish[i] - self.f.x[i * 2]) for i in range(2)])
        dtheta = np.abs(np.mod(new_fish[3] - self.unfiltered[0]+np.pi, np.pi*2)-np.pi)
        return np.sum(dists ** 2) < n_px ** 2 and dtheta < d_theta


@jit(nopython=True)
def points_to_angles(points):
    angles = np.empty(len(points) - 1, dtype=np.float64)
    for i, (p1, p2) in enumerate(zip(points[0:-1], points[1:])):
        angles[i] = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    return angles


def fish_start_n(mask, take_min=50):
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
    return np.array([x0, y0])

@jit(nopython=True)
def _symmetry_points(x0, y0, x, y):
    return [
        (x0 + x, y0 + y),
        (x0 - x, y0 + y),
        (x0 + x, y0 - y),
        (x0 - x, y0 - y),
        (x0 + y, y0 + x),
        (x0 - y, y0 + x),
        (x0 + y, y0 - x),
        (x0 - y, y0 - x),
    ]

@jit(nopython=True)
def _circle_points(x0, y0, radius):
    """ Bresenham's circle algorithm

    Parameters
    ----------
    xc : center x
    yc : center y
    r : radius

    Returns
    -------
    a list of points

    """
    f = 1 - radius
    ddf_x = 1
    ddf_y = -2 * radius
    x = 0
    y = radius
    points = [
        (x0, y0 + radius),
        (x0, y0 - radius),
        (x0 + radius, y0),
        (x0 - radius, y0),
    ]
    while x < y:
        if f >= 0:
            y -= 1
            ddf_y += 2
            f += ddf_y
        x += 1
        ddf_x += 2
        f += ddf_x
        points.extend(_symmetry_points(x0, y0, x, y))
    return points


@jit(nopython=True)
def _fish_direction_n(image, start_loc, radius):
    centre_int = start_loc.astype(np.int16)
    pixels_rad = _circle_points(centre_int[0], centre_int[1], radius)
    min_point = pixels_rad[0]
    min_val = 255
    for x, y in pixels_rad:
        if image[y, x] < min_val:
            min_val = image[y, x]
            min_point = (x, y)
    return np.arctan2(min_point[1]-centre_int[1], min_point[0]-centre_int[0])