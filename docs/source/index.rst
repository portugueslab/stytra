.. Stytra documentation master file, created by
   sphinx-quickstart on Tue Apr 17 15:22:25 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Stytra's documentation!
==================================

Stytra is a package to build and run behavioral experiments.


..  toctree::
    :maxdepth: 2
    :caption: Contents:

    install_guide
    examples_gallery
    stimulation_intro
    configuring_computer
    data_saving
    calibration
    triggering_intro
    parameters_stytra
    coordinate_systems
    hardware_list
    interface
    pipelines
    tracking


Modules
-------
.. glossary::
    :py:mod:`stytra`
        The root module, contains the Stytra class for running the experiment
        (selecting the appropriate experiment subtypes and setting the parameters)

    :py:mod:`stytra.experiments`
        The controller classes organizing different kinds of experiments
        (with and without behavioral tracking, closed loop stimulation and with
        video recording). The classes put together everything required for a
        particular kind of experiment

    :py:mod:`stytra.gui`
        Defines windows and widgets used for the different experiment types

    :py:mod:`stytra.hardware`
        Communication with external hardware, from cameras to NI boards

    :py:mod:`stytra.triggering`
        Communication with other equipment for starting or stopping experiments

    :py:mod:`stytra.metadata`
        Classes that manage the metadata

    :py:mod:`stytra.stimulation`
        Definitions of various stimuli and management of experimental protocols

    :py:mod:`stytra.calibration`
        Classes to register the camera view to the projector display and
        set physical dimensions

    :py:mod:`stytra.tracking`
        Fish, eye and tail tracking functions together with appropriate interfaces




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
