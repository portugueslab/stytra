import cv2
import numpy as np
from numba import vectorize, uint8, jit

from stytra.utilities import HasPyQtGraphParams
from stytra.tracking.tail import find_fish_midline
from stytra.tracking import ParametrizedImageproc


class FishTrackingMethod(ParametrizedImageproc):
    def __init__(self):
        super().__init__(name="tracking_fish_params")
        self.add_params(function="fish", threshold=dict(type="int", limits=(0, 255)))

        self.accumulator_headers = ["x", "y", "theta"]
        self.data_log_name = ""

    @classmethod
    def detect(cls, im, threshold=128, image_scale=1, **extra_args):
        cent = centroid_bin(im < threshold)
        return cent[0] / image_scale, cent[1] / image_scale, 0.0


class ContourScorer:
    """ """

    def __init__(self, target_area, target_ratio, ratio_weight=1):
        self.target_area = target_area
        self.target_ratio = target_ratio
        self.ratio_weight = ratio_weight

    def score(self, cont):
        """

        Parameters
        ----------
        cont :
            

        Returns
        -------

        """
        area = cv2.contourArea(cont)
        if area < 2:
            return 10000
        err_area = ((area - self.target_area) / self.target_area) ** 2
        _, el_axes, _ = cv2.minAreaRect(cont)
        if el_axes[0] == 0.0:
            ratio = 0.0
        else:
            ratio = el_axes[1] / el_axes[0]
            if ratio > 1:
                ratio = 1 / ratio
        err_ratio = (ratio - self.target_ratio) ** 2

        return self.ratio_weight * err_ratio + err_area

    def best_n(self, contours, n=1):
        """

        Parameters
        ----------
        contours :
            
        n :
             (Default value = 1)

        Returns
        -------

        """
        idxs = np.argsort([self.score(cont) for cont in contours])
        if n == 1:
            return contours[idxs[0]]
        else:
            return [contours[idxs[i]] for i in range(n)]

    def above_threshold(self, contours, threshold):
        """

        Parameters
        ----------
        contours :
            
        threshold :
            

        Returns
        -------

        """
        print([self.score(cont) for cont in contours])
        good_conts = [cont for cont in contours if self.score(cont) < threshold]
        return good_conts


class EyeMeasurement:
    """ """

    def __init__(self):
        self.eyes = np.array([[0, 0], [0, 0]])

    def update(self, eyes):
        """

        Parameters
        ----------
        eyes :
            

        Returns
        -------

        """
        self.eyes = eyes

    def dx(self):
        """ """
        return self.eyes[1][0] - self.eyes[0][0]

    def dy(self):
        """ """
        return self.eyes[1][1] - self.eyes[0][1]

    def perpendicular(self):
        """ """
        return np.arctan2(-self.dx(), self.dy())

    def centre(self):
        """ """
        return np.mean(self.eyes, 0)


def detect_eyes_tail(frame, frame_tail, start_x, start_y, params, diag_image=None):
    """

    Parameters
    ----------
    frame :
        
    frame_tail :
        
    start_x :
        
    start_y :
        
    params :
        
    diag_image :
         (Default value = None)

    Returns
    -------

    """
    # find the eyes
    ret, thresh_eyes = cv2.threshold(
        frame, params.eye_threshold, 255, cv2.THRESH_BINARY
    )
    diag_image[
        start_y : start_y + frame.shape[0], start_x : start_x + frame.shape[1]
    ] = thresh_eyes
    _, eye_conts, _ = cv2.findContours(
        255 - thresh_eyes.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    # if no eye contours are present return error state
    if len(eye_conts) < 3:
        # erode to escape that sometimes eyes connect
        thresh_eyes = cv2.dilate(thresh_eyes, np.ones((3, 3), dtype=np.uint8))
        _, eye_conts, _ = cv2.findContours(
            255 - thresh_eyes.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if len(eye_conts) < 2:
            return -1, 0, 0, 0

    # find the darkest two contours which will presumably be eyes
    brightnesses = np.empty(len(eye_conts))
    for idx, eye_cont in enumerate(eye_conts):
        x, y, w, h = cv2.boundingRect(eye_cont)
        if cv2.contourArea(eye_cont) < 3:
            brightnesses[idx] = 255
        else:
            brightnesses[idx] = np.mean(
                frame_tail[
                    start_y + y : start_y + y + h, start_x + x : start_x + x + w
                ].flatten()
            )
            if diag_image is not None:
                cv2.putText(
                    diag_image,
                    str(brightnesses[idx]),
                    (start_x + x, start_y + y),
                    cv2.FONT_HERSHEY_PLAIN,
                    0.5,
                    0,
                )

    order = np.argsort(brightnesses)
    eye_locs = np.empty((2, 2))
    for i in range(2):
        eye_locs[i] = np.mean(eye_conts[order[i]], 0)

    centre_eyes = np.array([start_x, start_y]) + np.mean(eye_locs, 0)

    fish_length = params["fish_length"]
    tail_len = fish_length * params["tail_to_body_ratio"]
    eyes_to_tail = fish_length * params["tail_start_from_eye_centre"]

    dir_tail, tail_angles = detect_tail_unknown_dir(
        image=(255 - frame_tail),
        start_point=centre_eyes.copy(),
        tail_length=tail_len,
        eyes_to_tail=eyes_to_tail,
        segments=params.n_tail_segments,
    )

    theta = dir_tail - tail_angles[0]

    tail_segment = (eyes_to_tail) * np.array([np.cos(dir_tail), np.sin(dir_tail)]) + (
        tail_len / params["n_tail_segments"]
    ) * np.array([np.cos(theta), np.sin(theta)])
    dir_fish = np.arctan2(tail_segment[1], tail_segment[0]) + np.pi

    return centre_eyes[0], centre_eyes[1], dir_fish, -tail_angles


@vectorize([uint8(uint8, uint8)])
def bgdif(x, y):
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


class MidlineDetectionParams(HasPyQtGraphParams):
    """ """

    def __init__(self):
        super().__init__(name="stimulus_protocol_params")

        for child in self.params.children():
            self.params.removeChild(child)

        standard_params_dict = {
            "target_area": {"type": "int", "value": 450, "limits": (0, 1500)},
            "area_tolerance": {"type": "int", "value": 320, "limits": (0, 700)},
            "n_tail_segments": {"type": "int", "value": 14, "limits": (1, 20)},
            "tail_segment_length": {"type": "float", "value": 4., "limits": (0.5, 10)},
            "tail_detection_radius": {
                "type": "int",
                "value": 450,
                "limits": (0, 1500),
                "tip": "size of area used to find the next segment",
            },
            "eye_and_bladder_threshold": {
                "type": "int",
                "value": 100,
                "limits": (0, 255),
                "tip": "Threshold used to find head centre of mass",
            },
        }

        for key in standard_params_dict.keys():
            self.add_one_param(key, standard_params_dict[key])


def find_fishes_midlines(frame, mask, params):
    """Finds the fishes in the frame using the mask
    obtained by background subtraction

    Parameters
    ----------
    frame :
        video frame
    mask :
        corresponding mask
        obtained with background subtraction
    params :
        return: list of named tuples containing the fish measurements

    Returns
    -------
    type
        list of named tuples containing the fish measurements

    """
    _, contours, _ = cv2.findContours(
        mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    # if there are no contours, report no fish in this frame

    if len(contours) == 0:
        return []

    # find the contours corresponding to a fish
    measurements = []

    # go through all the contours
    for fish_contour in contours:

        # skip if the area is too small or too big
        if (
            np.abs(cv2.contourArea(fish_contour) - params.target_area)
            > params.area_tolerance
        ):
            continue

        fx, fy, fw, fh = cv2.boundingRect(fish_contour)

        # crop the frame around the contour
        mc = mask[fy : fy + fh, fx : fx + fw]

        # construct an image of the fish masked by the contour
        fc = (255 - frame[fy : fy + fh, fx : fx + fw]) * (mc // 255)

        # find the beginning
        y0, x0, angle = fish_start(fc, params.eye_and_bladder_threshold)

        # if the fish start has not been found, go to the next contour
        if y0 < 0:
            continue

        # find the midline (while also refining the beginning)
        points = find_fish_midline(
            fc,
            x0,
            y0,
            angle,
            m=params.tail_segment_length,
            r=params.tail_detection_radius,
            n_points_max=params.n_tail_segments,
        )

        # if all the points of the tail have been found, calculate
        # the angle of each segment
        if len(points) == params.n_tail_segments:
            angles = []
            for p1, p2 in zip(points[0:-1], points[1:]):
                angles.append(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))

            measurements.append(
                ((points[0][0] + fx, points[0][1] + fy) + tuple(angles))
            )

    return measurements


def fish_start(mask, take_min=100):
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
    mom = cv2.moments(
        np.maximum(mask.astype(np.int16) - take_min, 0)
    )  # cv2.erode(mask,np.ones((7,7), dtype=np.uint8))
    if mom["m00"] == 0:
        return -1, -1, 0
    y0 = mom["m01"] / mom["m00"]
    x0 = mom["m10"] / mom["m00"]
    angle = np.arctan2(mask.shape[0] / 2 - y0, mask.shape[1] / 2 - x0)
    return y0, x0, angle


@jit(nopython=True)
def centroid_bin(im):
    """ Binary centroid function """
    si = 0
    sj = 0
    sw = 0
    for i in range(im.shape[0]):
        for j in range(im.shape[1]):
            if im[i, j]:
                si += i
                sj += j
                sw += 1
    if sw > 0:
        return si / sw, sj / sw

    return (-1.0, -1.0)
