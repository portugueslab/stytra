Create protocols in stytra
==========================

Here we see examples of how to create a Protocol in stytra.

Create stimulus sequence
------------------------
In order to design a new experiment, we need to implement a new Protocol.
The essential feature of the protocol is the list of stimuli that composes it
. To create it, we need to define the
protocol  method :meth:`Protocol.get_stim_sequence() <stytra.stimulation.protocols.Protocol.get_stim_sequence()>`.
This metod will return a list of stimuli that stytra will run.

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

Stytra uses a custom `Parameter`_ class from the lightparam library (https://github.com/portugueslab/lightparam) to
handle parameterization of its
classes, including the Protocol class.
For a complete description of Parameters
inside stytra see :ref:`Parameterisation`.
A protocol does not necessarily need to be parameterized. This is just
convenient in case we want the possibility of changing parameters from the
interface.
:meth:`Protocol.__init__() <stytra.stimulation.protocols.Protocol.__init__()>`


Example::

    # When the same stimulus, we can parameterise
    # pause and flash duration so that the user
    # can change them in the GUI:

    class FlashProtocol(Protocol):
        name = 'flash protocol'

        def __init__(self):
            super().__init__()

            # Add new parameters to the Protocol parameters:
            self.pause_duration = Param(9, limits=(0, 10)  # default value 9 (sec)
            self.flash_duration = Param(1, limits=(0, 10))  # default value 1 (sec)

        def get_stim_sequence(self):
            stimuli = [Pause(duration=self.pause_duration)),
                       FullFieldPainterStimulus(self.flash_duration,
                                                color=(255, 255, 255)))]

            return stimuli

.. Note::
   Parameters in Protocol param are the ones that can be changed from the GUI, but
   all stimulus attributes will be saved in the final log, both parameterized and unparameterized ones!

