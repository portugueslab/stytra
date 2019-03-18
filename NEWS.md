# 0.8.4

## New features
- maximal stimulus display framerate can be set
- added a new conditional stimulus that has a different conditions for the two possible switches
(stim_true->stim_false) on condition_off and and (stim_false->stim_true) on condition_on
This enables the TwoRadiusCenteringWrapper, a centering stimulus which appears when the fish disappears
from the outer border and disappears when the fish is close to the center.
- more improvements to conditional stimuli, please see API documentation for stimuli/conditional.

## Fixes
- fish position estimator also allows querying velocity
- remaining protocol duration estimate is refreshed during execution, so protocols
whose duration depends on the animal behavior (such as those with a CenteringWrapper)
display more sensible numbers.
- Stytra version, in addition to condition, is now saved
- single source for log names, so that metadata corresponds to file names
- the accumulators keep only a partial history if the protocol is not running, in order to
prevent overflowing the memory.

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

