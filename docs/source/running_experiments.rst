So, you want to run an experiment?
==================================

Here we will see how to run an experiment in Stytra. We will show how to run
a simple visual stimulation protocol for the fish, and then we'll introduce
how to add tracking for a restrained or a freely swimming fish.

Here, we'll assume you have already created a stimulation protocol. Every
experiment requires a protocol, even just an empty one. To see how to create
a protocol, go to the :ref:`Create stimulus sequence` section.

Run a basic experiment in stytra
--------------------------------
In stytra, an experiment is started by creating in a script a
:class:`Stytra <stytra.Stytra.get_stim_sequence()>` object.


As mentioned before, the only required input to start an experiment is to have
a list or protocols that we will pass to the Stytra class. Here we create a
simple protocol for showing a flash of 1 second, and we run a stytra
experiment with it:


Example::

   # Here we create an empty protocol, and we start an experiment with it.

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


General parameters for the Stytra class
---------------------------------------

Obviously, there are many more things we might want to specify when running an
experiment, like setting the directory for saving data or making the
stimulus window full screen. For this reason, there is a number of
parameters accepted as inputs by the Stytra class.
Different kinds of Stytra experiments require different configuration parameters
 to initialize the Stytra object. In the next sections we will have a look at how
  to set up different experiments.

For now, let's simply look at which basic parameters can be useful for our
simple experiment:
 - **dir_save**: directory where the experiment metadata will be saved (str);
 - **log_format**: format for the dynamic logs (for details see the
:ref:`Data and metadata saving` section)
 - **dir_assets**: directory where images or movies to be presented are
   located (str).
 - **display_config**: dictionary containing the settings for the stimulus
   window.
   Optional entries to the dictionary are:
      * full_screen: make the window full screen  on the second monitor (bool);
      * window_size: set size of display area (tuple(int, int))

Therefore, if we want to start an experiment with the protocol we defined above,
that saves metadata in a defined folder and uses a full-screen monitor, we'll
write::

   st = Stytra(protocols=[FlashProtocol], dir_save='/Path/to/a/folder',
               display_config=dict(full_screen=True))



Run an experiment synchronized with a trigger
---------------------------------------------

In many cases we want to use stytra in a setup, like a 2p microscope, which
require the synchronization of the stimulation protocol with the data
acquisition. To this aim, stytra uses triggers (for details on how to
implement and triggers, consult the :ref:`Triggering stimulation` section).
For running an experiment with a zmq trigger, it is sufficient to specify::

   st = Stytra(protocols=[FlashProtocol], scope_triggering='zmq')

For another custom trigger, we will simply pass an instance of the custom
trigger class to scope_triggering::

   from stytra.triggering import Trigger
   class NewTrigger(Trigger):
      # Definition of new trigger, see relative section
      pass
   st = Stytra(protocols=[FlashProtocol], scope_triggering=NewTrigger())


Run an experiment with camera and behaviour tracking
----------------------------------------------------

In the event we want to stream images from a camera and track behaviour
during the experiment, we first need to create the camera and tracking
configuration dictionary and then pass them to the stytra class. For a complete
description of the required and optional keys of the dictionary go to the
documentation for the :class:`Stytra <stytra.Stytra.get_stim_sequence()>` class.

Once we have defined the dictionaries, it is sufficient to pass them to the
stytra class::

   camera_config = dict(type='ximea')

    tracking_config = dict(embedded=True,
                           tracking_method="centroid",
                           estimator="vigor",
                           preprocessing_method='prefilter')

   st = Stytra(protocols=[FlashProtocol],
        camera_config=camera_config,
        tracking_config=tracking_config)



.. Note::
   Example note

