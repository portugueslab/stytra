Coordinate systems in Stytra
============================

Stytra follows the common convention for displaying images on screens: the x axis increases to the right
and the y axis increases downward, with (0,0) being the upper left corner.
For the recorded coordinates, the same holds. The angles correspondingly increase clockwise.

up to v0.8
Fish angle is defined as the direction of the first segment of the tail with respect to the head. The angle is 0 when the fish faces left.

.. image:: ../../figures/coordinate_v0_8.svg
   :scale: 50%
   :alt: coordinate system
   :align: center

up to v0.8
x and y coordinates are labelled the other way around in the estimator log. Those recorded as 'x' in the estimator log are actually the coordinates of y, and vice versa.

:ref:`calibration` establishes a mapping between the camera and projector coordinate systems.
The :attr:`~stytra.calibration.CircleCalibrator.cam_to_proj` and :attr:`~stytra.calibration.CircleCalibrator.proj-to_cam`
matrices transform points from one coordinate system to another.

Visual stimuli are usually configured to take dimensions in millimeters, whereas the scaling factor is taken from
the calibration procedure.