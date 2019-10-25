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

        self.proj_to_cam = self.arr_to_tuple(self.points_cam.T @ np.linalg.inv(x_proj))
        self.cam_to_proj = self.arr_to_tuple(points_proj.T @ np.linalg.inv(x_cam))


class MotorPointCalibrator(Calibrator):
    """Displays a Point for Motor Calibration"""

    def __init__(self, *args, dh=80, r=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.dh = dh
        self.r = r
        self.length_px = dh * 2
        self.points = None
        self.points_cam = None


    def make_calibration_pattern(self, p, h, w, draw=True):
        assert isinstance(p, QPainter)

        d2h = self.dh // 2
        d2w = int(self.dh * math.sqrt(3) // 2)
        ch = h // 2
        cw = w // 2
        centres = np.array ([(cw + d2h, ch + d2w)])

        if draw:
            p.setPen(QPen(QColor(255, 0, 0)))
            p.setBrush(QBrush(QColor(255, 0, 0)))
            for centre in centres:
                p.drawEllipse(QPoint(*centre), self.r, self.r)


    @staticmethod
    def _find_blobs(image, blob_params=None):
        if blob_params is None:
            blobdet = cv2.SimpleBlobDetector_create()
        else:
            blobdet = cv2.SimpleBlobDetector_create(blob_params)
        # TODO check if blob detection is robust
        scaled_im = 255 - (image.astype(np.float32) * 255 / np.max(image)).astype(
            np.uint8
        )
        keypoints = blobdet.detect(scaled_im)
        if len(keypoints) != 1:
            raise CalibrationException("Calibration needs one point")
        kps = np.array([k.pt for k in keypoints])
        return kps

    def find_transform_matrix(self, image):
        self.points_cam = self._find_blobs(image)
        points_proj = self.points

        x_proj = np.vstack([points_proj.T, np.ones(1)])
        x_cam = np.vstack([self.points_cam.T, np.ones(1)])

        self.proj_to_cam = self.arr_to_tuple(self.points_cam.T @ np.linalg.inv(x_proj))
        self.cam_to_proj = self.arr_to_tuple(points_proj.T @ np.linalg.inv(x_cam))
        print ("cam to projector", self.cam_to_proj)
        print ("proj to cam", self.proj_to_cam)
        #TODO does this work?


    # def calibrate_motor(self):
    #     self.point_x_prev, self.point_y_prev, im = MotorCalibrator.find_dot(self)
    #
    #     posx = self.motx.get_position()
    #     print("moving x")
    #     self.motx.movethatthing(posx + 20000)  # 20000 motor units is 1 mm
    #     sleep(0.5)
    #     posy = self.moty.get_position()
    #     print("moving y")
    #     self.moty.movethatthing(posy + 20000)  # 20000 motor units is 1 mm
    #     sleep(0.5)
    #     self.point_x_after, self.point_y_after, im = MotorCalibrator.find_dot(self)
    #
    #     self.distance_points_x = int(self.point_x_prev - self.point_x_after)
    #     self.distance_points_y = int(self.point_y_prev - self.point_y_after)
    #
    #     self.conversion_x = int(20000 / abs(self.distance_points_x))
    #     self.conversion_y = int(20000 / abs(self.distance_points_y))
    #
    #     print("conversion factors x,y: ", self.conversion_x, self.conversion_y)
    #
    #     return self.conversion_x, self.conversion_y
    #
    # def find_dot(self):  # same as dot tracking method
    #     self.cam = SpinnakerCamera()
    #     self.cam.open_camera()
    #     self.cam.set("exposure", 12)
    #     # TODO initiate camera somewhere else- cant be double initiated.
    #
    #     im = self.cam.read()
    #     cv2.imshow("img", im)
    #     cv2.waitKey(10)
    #
    #     # identify dot
    #     idxs = np.unravel_index(np.nanargmin(im), im.shape)
    #     e = (np.float(idxs[1]), np.float(idxs[0]))
    #     self.point_x = e[0]
    #     self.point_y = e[1]
    #     # print ("dot x,y", self.point_x, self.point_y)
    #
    #     self.cam.cam.EndAcquisition()
    #
    #     return self.point_x, self.point_y, im
    #
