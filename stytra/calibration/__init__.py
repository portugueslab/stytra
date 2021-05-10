import math

import cv2
import numpy as np
from PyQt5.QtCore import QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

from lightparam.param_qt import ParametrizedQt, Param
from stytra.hardware.motor.stageAPI import Motor



class CalibrationException(Exception):
    """ """

    pass


class Calibrator(ParametrizedQt):
    """ """

    def __init__(self, mm_px=0.2):
        super().__init__(name="stimulus/calibration_params")
        self.enabled = False

        self.mm_px = Param(mm_px)
        self.length_mm = Param(30., limits=(1, 800))
        self.length_px = Param(None)
        self.cam_to_proj = Param(None)
        self.proj_to_cam = Param(None)
        self.motor_to_cam = Param(None)

        self.length_to_measure = "do not use the base class as a calibrator"

        self.sig_param_changed.connect(self.set_physical_scale)

    def toggle(self):
        """ """
        self.enabled = ~self.enabled

    def set_physical_scale(self, change):
        """Calculate mm/px from calibrator length"""
        if change.get("length_mm", None) is not None:
            if self.length_px is not None:
                self.block_signal = True
                self.mm_px = self.length_mm / self.length_px
                self.block_signal = False

        if change.get("length_px", None) is not None:
            if self.length_px is not None:
                self.block_signal = True
                self.length_mm = self.length_px * self.mm_px
                self.block_signal = False

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        self.block_signal = True
        self.length_px = w
        self.length_mm = self.length_px * self.mm_px
        self.block_signal = False

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

    def __init__(
        self,
        *args,
        fixed_length=60,
        calibration_length="outside",
        transparent=True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.length_px = self.length_mm/self.mm_px
        self.length_is_fixed = False
        self.transparent = transparent

        if calibration_length == "outside":
            self.outside = True

            self.length_to_measure = "height of the rectangle (mm)"

        else:
            self.outside = False
            self.length_to_measure = (
                "a line of the cross"
            )  # TODO: world this better, unclear
            if fixed_length is not None:
                self.length_px = fixed_length
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
        if self.transparent:
            p.setBrush(QBrush(QColor(0, 0, 0, 0)))
        else:
            p.setBrush(QBrush(QColor(0, 0, 0, 255)))
        p.drawRect(QRect(1, 1, w - 2, h - 2))
        l2 = self.length_px / 2
        p.drawLine(w // 2 - l2, h // 2, w // 2 + l2, h // 2)
        p.drawLine(w // 2, h // 2 + l2, w // 2, h // 2 - l2)
        p.drawLine(w // 2, h // 2 + l2, w // 2 + l2, h // 2 + l2)

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        if not self.length_is_fixed:
            if self.outside:
                self.length_px = h
            else:
                self.length_px = max(h / 2, w / 2)


class CircleCalibrator(Calibrator):
    """" Class for a calibration pattern which displays 3 dots in a 30 60 90 triangle"""

    def __init__(self, *args, dh=80, r=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.dh = dh
        self.r = r
        self.length_px = dh * 2
        self.points = None
        self.points_cam = None
        self.length_to_measure = "longest side of the triangle"

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        self.length_px = self.dh * 2

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

        scaled_im = 255 - (image.astype(np.float32) * 255 / np.max(image)).astype(
            np.uint8
        )
        # Blur image to remove noise
        frame = cv2.GaussianBlur(scaled_im, (15, 15), 0)

        keypoints = blobdet.detect(frame)

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
        #Define your points for camera and projector
        self.points_cam = self._find_triangle(image)
        points_proj = self.points

        #These  lines add a row of ones under the 3 points
        x_proj = np.vstack([points_proj.T, np.ones(3)])
        x_cam = np.vstack([self.points_cam.T, np.ones(3)])

        self.proj_to_cam = self.arr_to_tuple(self.points_cam.T @ np.linalg.inv(x_proj))
        self.cam_to_proj = self.arr_to_tuple(points_proj.T @ np.linalg.inv(x_cam))



class MotorCalibrator(CircleCalibrator):
    """Displays a pattern for Motor Calibration"""
    def __init__(self, *args, dh=10, r=1, **kwargs):
        super().__init__(*args,dh=50, **kwargs)
        self.encoder_counts_per_unit = 20000 #motor unit to mm conversion gotten from motor

    def _find_triangle(self, image, blob_params=None):
        params = cv2.SimpleBlobDetector_Params()
        params.minThreshold = 1
        params.maxThreshold = 255
        params.filterByArea = True
        params.minArea = 1
        params.maxArea = 50
        params.filterByCircularity = False
        params.filterByConvexity = False
        params.filterByInertia = False

        if blob_params is None:
            blobdet = cv2.SimpleBlobDetector_create()
        else:
            blobdet = cv2.SimpleBlobDetector_create(params)

        scaled_im = 255 - (image.astype(np.float32) * 255 / np.max(image)).astype(
            np.uint8
        )
        # Blur image to remove noise
        frame = cv2.GaussianBlur(scaled_im, (15, 15), 0)

        keypoints = blobdet.detect(frame)

        if len(keypoints) != 3:
            raise CalibrationException("3 points for calibration not found")
        kps = np.array([k.pt for k in keypoints])

        # Find the angles between the points
        # and return the points sorted by the angles
        return kps[np.argsort(CircleCalibrator._find_angles(kps)), :]


    def find_transform_matrix(self, image):
        # Define your points for camera and projector
        self.points_cam = self._find_triangle(image)
        points_proj = self.points

        # These  lines add a row of ones under the 3 points
        x_proj = np.vstack([points_proj.T, np.ones(3)])
        x_cam = np.vstack([self.points_cam.T, np.ones(3)])

        self.proj_to_cam = self.arr_to_tuple(self.points_cam.T @ np.linalg.inv(x_proj))
        self.cam_to_proj = self.arr_to_tuple(points_proj.T @ np.linalg.inv(x_cam))

        return self.points_cam

    def find_motor_transform(self, kps_prev, kps_after):
        diff = kps_prev - kps_after
        x_points = np.mean(diff[0:, 0:1])
        y_points = np.mean(diff[0:, 1:])

        self.conversion_x = int(self.encoder_counts_per_unit / abs(x_points))
        self.conversion_y = int(self.encoder_counts_per_unit / abs(y_points))
        self.motor_to_cam = [self.conversion_x, self.conversion_y]

        return self.conversion_x, self.conversion_y

