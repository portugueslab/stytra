# Stytra 0.8

## Features
- flexible tracking pipeline specification using the Pipeline class  
- OpenCV cameras supported, along with exposure and framerate adjustments
- combined tail and eye tracking works well
- stimulus display framerate is also shown

## Fixes
- all time-delta calculations are based on a single time-point
defined in the experiment class

## Changes in default behavior
-  Plotting is now frozen on experiment start, in order not to interfere
with stimulus display

## Known issues
- If using the current release of PyQtGraph (0.10) Stytra crashes on exit
this can be resolved by installing the master branch of PyQtGraph

## API changes
- Subclassing the estimator does not need to handle the estimator log creation, 
it is done automatically