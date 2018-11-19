Calibration
===========

Simple calibration of a monitor for a visual stimulus
-----------------------------------------------------
To calibrate the monitor for your experiment, first position the black
stimulus screen on the monitor you are using for the experiment. Then, hit
the show calibration button and drag around the ROI in the stytra GUI until
the red rectangle covers the area you want to use for the stimulus and the
cross is at the center. Finally, specify in the spin box the final size of
the bottom edge of the calibrator in centimeters.

The calibration is saved in the last_stytra_config.json file, so once you
have done it it maintains the same calibration for all subsequent experiments.


Calibration of a monitor together with a camera
-----------------------------------------------

To calibrate the camera image to the projected image, the Circle Calibrator
is used (it is enabled automatically for freely-swimming experiments).

After Sytra starts, turn off the IR illuminationation and remove the IR filter
in front of the camera. Then, click the display calibration pattern button and
move the display window on the projector so that the 3 dots are visible.
Sometimes the camera exposure has to be adjusted as well.

(insert screenshot)

Then, click calibrate and verify that the location of the camera image
in the projected image makes sense. If not, try adjusting camera settings and
calibrating again.