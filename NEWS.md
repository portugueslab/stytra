# 0.8.4

## Fixes
get_velocity of the fish position estimator should work 

## Changes in default behavior
`CenteringWrapper` has the radial centering stimulus by default, the non-centering
stimulus is specified as the `stimulus` keyword argument 


# Stytra 0.8

## New features
- flexible tracking pipeline specification using the Pipeline class  
- OpenCV cameras supported, along with exposure and framerate adjustments
- combined tail and eye tracking works well
- stimulus display framerate is also shown, minimum framerates can be set

## Fixes
- all time-delta calculations are based on a single time-point
defined in the experiment class
- video file framerate setting works

## Changes in default behavior
-  Plotting is now frozen on experiment start, in order not to interfere
with stimulus display

## Known issues
- If using the current release of PyQtGraph (0.10) Stytra crashes on exit
this can be resolved by installing the master branch of PyQtGraph
- On macOS Experiments with tracking hang after closure and need to be
forced to close

## API changes
- Subclassing the estimator does not need to handle the estimator log creation, 
it is done automatically

