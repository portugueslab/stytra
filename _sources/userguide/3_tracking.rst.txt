Tracking configuration
======================


Here are some tips to adjust tracking on your setup. If you have not done
that yet, you probably want to have a look at the
:ref:`User interface` description first. Remember to use the dropdown menu to
 display the diagnostic images from intermediate stages of the image
 processing! That is the best way to ensure that all parameters are set
 correctly.


.. _fishtracking:

Freely-swimming fish
--------------------

.. image:: ../../screenshots/freeswim_tracking.png
   :scale: 30%
   :alt: freely-swimming tracking screenshot
   :align: center

1) Open the tracking settings window

2) Input the number of fish in the dish

3) Determine the parameters for background subtraction
   bglearning_rate and bglearn_every. bglearning_rate specifies what is the
   weight which is assigned to every new image in the background computation,
    from 0 (only the first frame acquired will be used at the background) to
    1 (every new frame is set as the background). bglearn_every specifies
    every how many frames a new image is used to compute background. This
    should change
   Under the camera view, you can select the currently displayed image (raw for the )

4) Once you see the fish nicely, adjust the thresholded image,
   so that the full fish, but nothing more, is white bgdif_threshold

5) Adjust the eye threshold so that the eyes and swim bladder are highlighted (by changing the display_processed parameter)
   threshold_eyes

6) Adjust the target area:
   look at the biggest_area plot, if the background is correctly subtracted and a fish is in the field of view,
   the value should equal the current area of the fish. Choose a range that is comfortably around the current fish are

7) Adjust the tail length: the red line tracing the tail should not go over the actual tail.

8) If the fish jumps around too much, adjust the prediction uncertainty.


Tracking results
................
A dataframe with position, orientation and tail shape data for each fish tracked.
Data per fish are prefixed with ``fN_`` where N is the number of the fish
(fish identities can change if they exit the field of view, cross or lose tracking)
``x`` and ``y`` are positions in camera coordinates, ``theta`` the direction of the tail of the fish
(to get the heading direction, add pi) and ``theta_XX`` the angles of the tail segments.
To get the position in the projector coordinates, if the camera to projector
mapping was properly calibrated :ref:`Calibration`,
use the ``cam_to_proj`` matrix from the calibrator (saved in the metadata.json file)

.. _tailtracking:

Embedded fish
-------------

1) Ensure that the exposure time is not longer than 1.5 milliseconds, otherwise
   the tracking will not be correct for fast tail movements

2) Open the tracking settings window

3) Invert the image if the tail is dark with respect to the background

4) Set the camera display to filtered and adjust clipping until the fish is the only
   bright thing with respect to the background, which has to be completely black.

5) Make the image as small as possible (with image_scale) as long as the tail is mostly more than 3px wide
   and filter it a bit (usually using filter_size=3)

6) Adjust the number of tail segments, around 30 is a good number. Usually, not more than 10 n_output_segments are required

7) Tap the dish or the stage so that fish flicks its tail, and ensure the that it is tracked correctly. There should be no breaks in the tail_sum plot, if there are, it is likely the tail length line is too long. You can use the replay function to ensure the whole movement is tracked smoothly

8) To ensure the tracking is correct, you can enable the plotting of the last bout in the windows


Tracking results
................
A dataframe with the columns: ``tail_sum`` - the total curvature of the fish tail, i.e. the angle between the first and last segment
and ``theta_XX`` - the angle of each tail segment


.. _replaying:

Replaying the camera feed to refine tracking
--------------------------------------------

The replay functionality allows a frame-by-frame view of the camera feed during
a period of interest (e.g. a bout or a struggle).
After an interesting event happens and you can see it in the plot, pause the camera with the
pause button. Use the two gray bars in the plots, select the time-period of interest.
Then, enable the replay with the button underneath the camera, and unpause the camera feed.
Now, the selected slice of time is replayed, and the framerate of the replay can be adjusted in the
camera parameters. To go back to the live feed, toggle the replay button.
