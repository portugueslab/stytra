# Stytra 0.8

## Features
- flexible tracking pipeline specification using the Pipeline class  
- OpenCV camera supported

## Fixes
- all time-delta calculations are based on a single time-point
defined in the experiment class

## Changes in default behavior
-  Plotting is now frozen on experiment start, in order not to interfere
with stimulus display

## Known issues
- If using the current release of PyQtGraph (0.10) Stytra crashes on exit
this can be resolved 