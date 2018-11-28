Configuring tracking of freely-swimming fish
============================================

.. image:: ../screenshots/freeswim_tracking.png
   :scale: 30%
   :alt: freely-swimming tracking screenshot
   :align: center

1) Open the tracking settings window

2) Input the number of fish in the dish

3) Determine the parameters for background subtraction
   bglearning_rate and bglearn_every
   The diagnostic display can be invoked by putting display_processed to different states

4) Once you see the fish nicely, adjust the thresholded image,
   so that the full fish, but nothing more, is white bgdif_threshold

5) Adjust the eye threshold so that the eyes and swim bladder are highlighted (by changing the display_processed parameter)
   threshold_eyes

6) Adjust the target area:
   look at the biggest_area plot, if the background is correctly subtracted and a fish is in the field of view,
   the value should equal the current area of the fish. Choose a range that is comfortably around the current fish are

7) Adjust the tail length: the red line tracing the tail should not go over the actual tail.

8) If the fish jumps around too much, adjust the prediction uncertainty.