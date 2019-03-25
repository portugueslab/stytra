Coordinate systems in Stytra
============================

Stytra follows the common convention for displaying images on screens: the x axis increases to the right
and the y axis increases downward, with (0,0) being the upper right corner.
For the recorded coordinates, the same holds. The angles correspondingly increase clockwise.

:ref:`calibration` establishes a mapping between the camera and projector coordinate systems.
The :attr:`~stytra.calibration.CircleCalibrator.cam_to_proj` and :attr:`~stytra.calibration.CircleCalibrator.proj-to_cam`
matrices transform points from one coordinate system to another.

Visual stimuli are usually configured to take dimensions in millimeters, whereas the scaling factor is taken from
the calibration procedure.