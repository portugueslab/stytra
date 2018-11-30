Configuring tracking of embedded fish
============================================

1) Ensure that the exposure time is not longer than 1.5 miliseconds, otherwise
   the tracking will not be correct for fast tail movements

2) Open the tracking settings window

3) Invert the image if the tail is dark with respect to the background

4) Set the display_processed to filtered and adjust clipping until the fish is the only
   bright thing with respect to the background

5) Make the image as small as possible (with image_scale) as long as the tail is mostly more than 3px wide
   and filter it a bit (usually using filter_size=3)

6) Adjust the number of tail segments, around 30 is a good number. Usually, not more than 10 n_output_segments are required

7) Tap the dish of the fish so that it moves, and ensure the tail is tracked correctly. You can use the replay function to
ensure the whole movement is tracked smoothly