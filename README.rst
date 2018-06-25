======
Stytra
======
A modular package to control stimulation and track behaviour in zebrafish experiments.
---------------

*screenshot goes here*

Stytra is divided into independent modules which can be assembled
depending on the experiemntal requirements.

Simple usage examples can be found in the examples folder.

Modules
-------

experiments
    The controller classes organizing different kinds of experiments
     (with and without behavioural tracking, closed loop stimulation and with
    video recording). The classes put together everything required for a
    particular kind of experiment

gui
    Defines windows and widgets used for the different experiment types

hardware
    Communication with external hardware, from cameras to NI boards

triggering
    Communication with other equipement for starting or stopping experiments

metadata
    Classes that manage the metadata

stimulation
    Definitions of varius stimuli and management of experimental protocols

calibration
    Classes to register the camera view to the projector display and
    set physical dimentions

tracking
    Fish, eye and tail tracking functions together with appropriate interfaces

bouter
    Uitilities for analysis of bouts