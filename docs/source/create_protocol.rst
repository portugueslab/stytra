Create protocols in stytra
==========================

Here we see examples of how to create a Protocol in stytra.

Create stimulus sequence
------------------------
In order to design a new experiment, a new Protocol has to be defined. By
defining the output list of the
protocol :meth:`Protocol.get_stim_sequence() <stytra.stimulation.protocols.Protocol.get_stim_sequence()>` method, the sequence of the experiment can be
defined.

Example::

    # Here we create a simple protocol where a white flash of 1 second is
    # presented after a pause on the screen.

    from stytra.stimulation.stimuli import Pause, FullFieldPainterStimulus
    class FlashProtocol(Protocol):
        name = 'flash protocol'  # it is important to assign a protocol name

        def get_stim_sequence(self):
            stimuli = [Pause(duration=9),  # black screen, 9 sec
                       FullFieldPainterStimulus(duration=1,  # flash, 1 sec
                                                color=(255, )*3))

            return stimuli


Parameterise the protocol
-------------------------

Stytra uses the `Parameter`_ class from pyqtgraph to handle parameterization of its
classes, including Protocol. For a complete description of Parameters inside
stytra see :ref:`Parameterisation`.
In the Protocol, parameters that have to be defined by the user can be defined by the
:meth:`Protocol.__init__() <stytra.stimulation.protocols.Protocol.__init__()>`
with the :meth:`Protocol.set_new_param() <stytra.stimulation.protocols.Protocol.set_new_param()>`
method.

.. _`Parameter`: http://www.pyqtgraph.org/documentation/parametertree/parameter.html

Example::

    # When the same stimulus, we can parameterise
    # pause and flash duration so that the user
    # can change them in the GUI:

    class FlashProtocol(Protocol):
        name = 'flash protocol'

        def __init__(self):
            super().__init__()

            # Add new parameters to the Protocol parameters:
            self.set_new_param('pause_duration', 9)  # default value 9 (sec)
            self.set_new_param('flash_duration', 1)  # default value 1 (sec)

        def get_stim_sequence(self):
            stimuli = [Pause(duration=self.params['pause_duration'])),
                       FullFieldPainterStimulus(self.params['flash_duration'],
                                                color=(255, 255, 255)))]

            return stimuli

.. Note::
   Parameters in Protocol param are the ones that can be changed from the GUI, but
   all stimulus attributes will be saved in the final log, both parameterized and unparameterized ones!

