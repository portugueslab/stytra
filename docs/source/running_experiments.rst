So, you want to run an experiment?
==================================

Here we will see how to run an experiment in Stytra. We will show how to run
a simple visual stimulation protocol for the fish, and then we'll introduce
how to add tracking for a restrained or a freely swimming fish.

Here, we'll assume you have already created a stimulation protocol. Every
experiment requires a protocol, even just an empty one. To see how to create
a protocol, go to the :ref:`Create stimulus sequence` section.

Run an experiment in stytra
---------------------------
In stytra, an experiment is started by creating in a script a
:class:`Stytra <stytra.Stytra.get_stim_sequence()>` object.


As we said before, the only required input to start an experiment is to have
a list or protocols that we will pass to the Stytra class. Here we create a
simple protocol for showing a flash of 1 second, and we run a stytra
experiment with it:


Example::

    # Here we create an empty protocol, end we start an experiment with it.

    from stytra import Stytra, Protocol
    from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
    class FlashProtocol(Protocol):
        name = "flash protocol"

        def __init__(self):
            super().__init__()

        def get_stim_sequence(self):
            stimuli = [Pause(duration=9),
                       FullFieldVisualStimulus(duration=1, color=(255, 255,
                       255))]
            return stimuli

     st = Stytra(protocols=[FlashProtocol])


Parameters for the Stytra class
-------------------------------

Obviously, there are many more things we might want to specify when running an
experiment, like setting the directory for saving data or making the
stimulus window full screen. For this reason, there is a number of
parameters accepted as inputs by the Stytra class.
Define different kinds of Stytra experiments requires simply to pass
different configuration parameters to initialize the Stytra object. In the
next sections we will have a look at how to set up different experiments.

For now, let's simply look at which basic parameters can be useful for our
simple experiment:
 - **dir_save**: directory where the experiment metadata will be saved (str);
 - **dir_assets**: directory where images or movies to be presented are
   located (str).
 - **display_config**: dictionary containing the settings for the stimulus
   window.
   Optional entries to the dictionary are:
      * full_screen: make the window full screen  on the second monitor (bool);
      * window_size: set size of display area (tuple(int, int))

Then if we want to start an experiment with the protocol we defined above,
that saves metadata in a defined folder and uses a full-screen monitor, we'll
write:

Example::


     st = Stytra(protocols=[FlashProtocol], dir_save='/Path/to/a/folder',
                 display_config=dict(full_screen=True))



Running an experiment


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

