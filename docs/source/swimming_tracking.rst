Configuring tracking of freely-swimming fish
============================================

1) Input the number of fish in the dish

2) Determine the thresholding parameters for background subtraction
    bglearning_rate and bglearn_every
    The diagnostic display can be invoked by putting display_processed to different states

3) Once you see the fish nicely, adjust the thresholded image,
    so that the full fish, but nothing more, is whitebgdif_threshold

4) Adjust the eye threshold so that the eyes and swim bladder are highlighted (display_processed=3)
    threshold_eyes

5) Adjust the target area and area margin
    (for now saving the picture and counting the on pixels with python/fiji
    is a possible method, otherwise guessing works

6) Adjust the tail length

7) If the fish jumps around too much, adjust the kalman coefficient