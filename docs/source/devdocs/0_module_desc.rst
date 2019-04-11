Module description
==================


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




:ref:`modindex`


