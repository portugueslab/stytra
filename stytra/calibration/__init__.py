import math

import cv2
import numpy as np
from PyQt5.QtCore import QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

from stytra.utilities import HasPyQtGraphParams


class CalibrationException(Exception):
    """ """

    pass


class Calibrator(HasPyQtGraphParams):
    """ """

    def __init__(self, mm_px=1):
        super().__init__()
        self.enabled = False

        self.params.setName("stimulus_calibration_params")
        self.params.addChildren(
            [
                {"name": "mm_px", "value": mm_px, "visible": True},
                {
                    "name": "length_mm",
                    "value": None,
                    "type": "float",
                    "suffix": "mm",
                    "siPrefix": True,
                    "limits": (1, 200),
                    "visible": True,
                },
                {"name": "length_px", "value": None, "visible": True},
                {"name": "cam_to_proj", "value": None, "visible": False},
                {"name": "proj_to_cam", "value": None, "visible": False},
            ]
        )
        self.length_to_measure = "do not use the base class as a calibrator"

        self.params["length_mm"] = 30
        self.params.child("length_mm").sigValueChanged.connect(self.set_physical_scale)

    def toggle(self):
        """ """
        self.enabled = ~self.enabled

    def set_physical_scale(self):
        """Calculate mm/px from calibrator length"""
        self.params["mm_px"] = self.params["length_mm"] / self.params["length_px"]

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        self.params["length_px"] = w

    def make_calibration_pattern(self, p, h, w):
        """

        Parameters
        ----------
        p :
            
        h :
            
        w :
            

        Returns
        -------

        """
        pass


class CrossCalibrator(Calibrator):
    """ """

    def __init__(self, *args, fixed_length=60, calibration_length="outside", **kwargs):
        super().__init__(*args, **kwargs)

        self.params["length_px"] = 1
        self.length_is_fixed = False

        if calibration_length == "outside":
            self.outside = True

            self.length_to_measure = "height of the rectangle (mm)"

        else:
            self.outside = False
            self.length_to_measure = (
                "a line of the cross"
            )  # TODO: world this better, unclear
            if fixed_length is not None:
                self.params["length_px"] = fixed_length
                self.length_is_fixed = True

    def make_calibration_pattern(self, p, h, w):
        """

        Parameters
        ----------
        p :
            
        h :
            
        w :
            

        Returns
        -------

        """
        p.setPen(QPen(QColor(255, 0, 0)))
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(1, 1, w - 2, h - 2))
        l2 = self.params["length_px"] / 2
        p.drawLine(w // 2 - l2, h // 2, w // 2 + l2, h // 2)
        p.drawLine(w // 2, h // 2 + l2, w // 2, h // 2 - l2)
        p.drawLine(w // 2, h // 2 + l2, w // 2 + l2, h // 2 + l2)

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        if not self.length_is_fixed:
            if self.outside:
                self.params["length_px"] = h
            else:
                self.params["length_px"] = max(h / 2, w / 2)


class CircleCalibrator(Calibrator):
    """" Class for a calibration pattern which displays 3 dots in a 30 60 90 triangle"""

    def __init__(self, *args, dh=80, r=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.dh = dh
        self.r = r
        self.params["length_px"] = dh*2
        self.points = None
        self.points_cam = None
        self.length_to_measure = "longest side of the triangle"

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        self.params["length_px"] = self.dh*2

    def make_calibration_pattern(self, p, h, w, draw=True):
        """

        Parameters
        ----------
        p :
            
        h :
            
        w :
            
        draw :
             (Default value = True)

        Returns
        -------

        """
        assert isinstance(p, QPainter)

        d2h = self.dh // 2
        d2w = int(self.dh * math.sqrt(3) // 2)
        ch = h // 2
        cw = w // 2
        # the three points sorted in ascending angle order (30, 60, 90)
        centres = [(cw - d2h, ch + d2w), (cw + d2h, ch + d2w), (cw - d2h, ch - d2w)]
        centres = np.array(centres)
        self.points = centres[np.argsort(CircleCalibrator._find_angles(centres)), :]

        if draw:
            p.setPen(QPen(QColor(255, 0, 0)))
            p.setBrush(QBrush(QColor(255, 0, 0)))
            for centre in centres:
                p.drawEllipse(QPoint(*centre), self.r, self.r)

    @staticmethod
    def _find_angles(kps):
        """

        Parameters
        ----------
        kps :
            

        Returns
        -------

        """
        angles = np.empty(3)
        for i, pt in enumerate(kps):
            pt_prev = kps[(i - 1) % 3]
            pt_next = kps[(i + 1) % 3]
            # angles are calculated from the dot product
            angles[i] = np.abs(
                np.arccos(
                    np.sum((pt_prev - pt) * (pt_next - pt))
                    / np.product(
                        [np.sqrt(np.sum((pt2 - pt) ** 2)) for pt2 in [pt_prev, pt_next]]
                    )
                )
            )
        return angles

    @staticmethod
    def _find_triangle(image, blob_params=None):
        """Finds the three dots for calibration in the image
        (of a 30 60 90 degree triangle)

        Parameters
        ----------
        image :
            return: the three triangle points
        blob_params :
             (Default value = None)

        Returns
        -------
        type
            the three triangle points

        """
        if blob_params is None:
            blobdet = cv2.SimpleBlobDetector_create()
        else:
            blobdet = cv2.SimpleBlobDetector_create(blob_params)
        # TODO check if blob detection is robust
        scaled_im = 255 - (image.astype(np.float32) * 255 / np.max(image)).astype(
            np.uint8
        )
        keypoints = blobdet.detect(scaled_im)
        if len(keypoints) != 3:
            raise CalibrationException("3 points for calibration not found")
        kps = np.array([k.pt for k in keypoints])

        # Find the angles between the points
        # and return the points sorted by the angles

        return kps[np.argsort(CircleCalibrator._find_angles(kps)), :]

    @staticmethod
    def arr_to_tuple(arr):
        """

        Parameters
        ----------
        arr :
            

        Returns
        -------

        """
        return tuple(tuple(r for r in row) for row in arr)

    def find_transform_matrix(self, image):
        """

        Parameters
        ----------
        image :
            

        Returns
        -------

        """
        self.points_cam = self._find_triangle(image)
        points_proj = self.points

        x_proj = np.vstack([points_proj.T, np.ones(3)])
        x_cam = np.vstack([self.points_cam.T, np.ones(3)])

        self.params["proj_to_cam"] = self.arr_to_tuple(
            self.points_cam.T @ np.linalg.inv(x_proj)
        )
        self.params["cam_to_proj"] = self.arr_to_tuple(
            points_proj.T @ np.linalg.inv(x_cam)
        )
