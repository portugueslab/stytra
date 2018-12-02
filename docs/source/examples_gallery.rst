Examples gallery
================

You don't need to get acquainted with the full complexity of stytra to start
running experiments. We provide a number of example protocols that you
can use to get inspiration for your own ones! In this section, we introduce
general ideas on stytra and we use the examples to illustrate them.

All examples in this section can be run in two ways: copy and paste the code in a python script
and run it from your favorite IDE, or simply type on the command prompt::

   python -m stytra.examples.name_of_the_example


Create a new protocol
---------------------
To run a stytra experiment, we simply need to create a script were we define a protocol,
and we assign it to a :class:`Stytra <stytra.Stytra>` object. Running this script will create
a Stytra GUI that enable us to control and run that protocol.

How do we create a protocol?
The essential feature of the protocol is the list of stimuli that composes it.
To create it, we need to define the
:meth:`Protocol.get_stim_sequence() <stytra.stimulation.protocols.Protocol.get_stim_sequence()>` method.
This method returns a list of :class:`Stimulus <stytra.stimulation.stimuli.Stimulus>` objects
which will be presented in succession to the animal.

In stytra.examples.most_basic_example.py we define a very simple experiment:

.. literalinclude:: ../../stytra/examples/most_basic_exp.py
   :language: python

Try to run this code or type in the command prompt::

   python -m stytra.examples.most_basic_exp

This will open two windows: one is the main control GUI to run the experiments,
the second is the screen used to display the visual stimuli. In a real experiment, you want
to make sure this second window is presented to the animal.

For an introduction to the functionalities of the interface, see :ref:`Stytra user interface`.
To start the experiment, just press the play button: a flash will appear on the screen after 4 seconds.



Parameterise the protocol
.........................
Sometimes, we want to control a protocol parameters from the interface. To do this, we can define
protocol class attributes as Param. This will allow us to open a mask to control stimulus
parameters within the Stytra GUI.

For a complete description of Params inside stytra see :ref:`Parameterisation`.

:meth:`Protocol.__init__() <stytra.stimulation.protocols.Protocol.__init__()>`

.. literalinclude:: ../../stytra/examples/flash_exp.py
   :language: python

Note that Parameters in Protocol param are the ones that can be changed from the GUI, but
all stimulus attributes will be saved in the final log, both parameterized and unparameterized ones!
You don't need to worry about parameters get lost.


Define dynamic stimuli
----------------------
Many stimuli may have some quantities, such as velocity for gratings or
angular velocity for windmills, that have to change over time. To define these
kind of stimuli Stytra use a convenient syntax: a param_df pandas DataFrame
with the specification of the desired parameter value at specific timepoints.
The value at all the other timepoints will be linearly interpolated from the
DataFrame. The dataframe has to contain a `t` column with the time, and one
column for each quantity that has to change over time (`x`, `theta`, etc.).
This stimulus behaviour is handled by the :class:`Stimulus <stytra.stimulation.stimuli.DynamiStimulus>`
class

In this example, we use a dataframe for changing the diameter of a circle
stimulus, making it a looming object:

.. literalinclude:: ../../stytra/examples/looming_exp.py
   :language: python


Use velocities instead of quantities
....................................

For every quantity we can specify the velocity at which it changes instead of
the value itself. This can be done premitting `vel_` to the quantity name
in the DataFrame.
In the next example, we use this syntax to create moving gratings. What is
dynamically updated is the
position `x` of the gratings, but with the dictionary we specify its velocity
with `vel_x`.

.. literalinclude:: ../../stytra/examples/gratings_exp.py
   :language: python

You can look in the code of the windmill_exp.py example to see how to use
the dataframe to specify a more complex motion - in this case, a rotation with
sinusoidal velocity.

Visualise with stim_plot parameter
..................................

If you want to monitor in real time the changes in your experiment
parameters, you can pass the stim_plot argument to the call to stytra to add
to the interface an online plot:

.. literalinclude:: ../../stytra/examples/plot_dynamic_exp.py
   :language: python


Stimulation and tracking:
-------------------------

Add a camera to a protocol
..........................

We often need to have frames streamed from a file or a camera. In the following
example we comment on how to achieve this when defining a protocol:

.. literalinclude:: ../../stytra/examples/display_camera_exp.py
   :language: python

Note however that usually the camera settings are always the same on the
computer that controls a setup, therefore the camera settings are defined in
the user config file and generally not required at the protocol level.
See :ref:`Configuring a computer for Stytra experiments` for more info.

Add tracking to a defined protocol
..................................

To add tail or eye tracking to a protocol, it is enough to change the
`stytra_config` attribute to contain a tracking argument as well. See the
experiment documentation for a description of the available tracking methods.

In this example, we redefine the previously defined windmill protocol (which
displays a rotating windmill) to add tracking of the eyes as well:

.. literalinclude:: ../../stytra/examples/tail_tracking_exp.py
   :language: python

Now a window with the fish image an a ROI to control tail position will appear,
and the tail will be tracked! See relative documentation for instructions on
how to adjust tracking parameters.

Closed-loop experiments
-----------------------

Stytra allows to easily define close-loop experiments where quantities
tracked from the image are dynamically used to update some stimulus variable.
In the example below we create a wait full-screen stimulus that turn red when
the fish is swimming above a certain threshold (estimated with the vigour
method).

.. literalinclude:: ../../stytra/examples/custom_visual_exp.py
   :language: python













