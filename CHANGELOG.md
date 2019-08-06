# 0.8.21
## New features
- recording videos along with online tracking is supported

## Fixes
- the tracking pipeline output type changes work again (Stytra does not crash anymore when changing the number of fish or tail segments) 

# 0.8.20
## Fixes
- Maximal exposure fo the camera can now be 1s, minimal framerate 1Hz

# 0.8.19
## Fixes
- Tracking a video from a file loops it now
- Fixed parts of the video recording experiment (#15)

## Improvements
- Background subtractor has an option
- Added an option to track every nth frame, for running slow and fast tracking functions at the same time

# 0.8.17
## Fixes
- Experiment parameters saved more consistently

## Improvements
- Initial support for Basler camera
- Added example to test camera in computer config

# 0.8.16
## Fixes
- Tests on Travis working properly now for full experiments with tracking

## Improvements
- Switched to PyAV for video reading 

# 0.8.15
## Fixes
- Fix for eye contour detection due to a change in the OpenCV API

# 0.8.14
## Fixes
- replay working again
- if the camera is paused before the first frame arrives Stytra does not crash anymore
- the replay buffer has a maximum length to prevent memory overflow

# 0.8.12
## Fixes
- fixed Ximea bug introduced by the previous version
- tests run again and work on Travis

# 0.8.11
## Improvements
- Full-featured FLIR/PointGray camera support by @EricThomson and @vigji

# 0.8.10
## Fixes
- fixed tracking crash for displaying diagnostics in fish tracking

# 0.8.8 and 0.8.9
## Fixes
- fixed offline tracking issues

# 0.8.7
## Improvements
- improved workflow for offline tracking

## Fixes
- offline tracking works on OS X

# 0.8.6

## New features
- added script for running Stytra offline on pre-recorded videos

# 0.8.4

## New features
- maximal stimulus display framerate can be set
- added a new conditional stimulus that has a different conditions for the two possible switches
(stim_on->stim_off) on condition_off and and (stim_on->stim_off) on condition_on
This enables the TwoRadiusCenteringWrapper, a centering stimulus which appears when the fish disappears
from the outer border and disappears when the fish is close to the center.
- more improvements to conditional stimuli, please see API documentation for stimuli/conditional.
- fish position estimator also allows querying velocity

## Fixes
- after long runs, Stytra does not hang on exit anymore (fix in ArrayQueues 1.2)
- remaining protocol duration estimate is refreshed during execution, so protocols
whose duration depends on the animal behavior (such as those with a CenteringWrapper)
display more sensible numbers.
- Stytra version, in addition to condition, is now saved
- single source for log names, so that metadata corresponds to file names
- the accumulators keep only a partial history if the protocol is not running, in order to
prevent overflowing the memory.
- fixed crash on capturing camera image if the experiment was not started yet

## Changes in default behavior
- `CenteringWrapper` has the radial centering stimulus by default, the non-centering
stimulus is specified as the `stimulus` keyword argument 

## Documentation updates
- large reorganization and inclusion of the mansucript


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

