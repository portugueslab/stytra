.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

.. _calibration:

Calibration
===========

Calibration for head-fixed zebrafish experiments
------------------------------------------------
To calibrate the monitor for your experiment, first position the black
stimulus screen on the monitor you are using for the experiment. Then, hit
the show calibration button and drag around the ROI in the stytra GUI until
the red rectangle covers the area you want to use for the stimulus and the
cross is at the center. Finally, specify in the spin box the final size of
the lateral edge of the calibrator in centimeters.

The calibration is saved in the last_stytra_config.json file, so once you
have done it it maintains the same calibration for all subsequent experiments.


Calibration for freely-swimming zebrafish experiments
-----------------------------------------------------

To calibrate the camera image to the displayed image, the Circle Calibrator
is used (it is enabled automatically for freely-swimming experiments).

.. image:: ../../screenshots/calibration.png
   :scale: 30%
   :alt: freely-swimming tracking screenshot
   :align: center

After Stytra starts, turn off the IR illumination and remove the IR filter
in front of the camera. Then, click the display calibration pattern button (:red:`a`) and
move the display window on the projector so that the 3 dots are clearly visible.
Sometimes the camera exposure has to be adjusted as well (:red:`b`) so that all 3 dots are visible.
Due to screen or projector framerates, usually setting the camera framerate to 30 and the exposure to 10ms works well.

Then, click calibrate (:red:`c`) and verify that the location of the camera image
in the projected image makes sense. If not, try adjusting camera settings and
calibrating again.