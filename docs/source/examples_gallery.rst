Examples gallery
================

You don't need to get acquainted with the full feature set of stytra to start
running experiments. Here and in the stytra/examples directory, we  provide a number of example protocols that you
can use to get inspiration for your own. In this section, we will illustrate general concepts of
designing and running experiments with examples.

All examples in this section can be run in two ways: copy and paste the code in a python script
and run it from your favorite IDE, or simply type on the command prompt::

   python -m stytra.examples.name_of_the_example


.. _protocol-definition:

Create a new protocol
---------------------
To run a stytra experiment, we simply need to create a script were we define a protocol,
and we assign it to a :class:`Stytra <stytra.Stytra>` object. Running this script will create
the Stytra GUI with controls for editing and running the protocol.

The essential ingredient of protocols is the list of stimuli that will be displayed.
To create it, we need to define the
:meth:`Protocol.get_stim_sequence() <stytra.stimulation.protocols.Protocol.get_stim_sequence()>` method.
This method returns a list of :class:`Stimulus <stytra.stimulation.stimuli.Stimulus>` objects
which will be presented in succession.

In stytra.examples.most_basic_exp.py we define a very simple experiment:

.. literalinclude:: ../../stytra/examples/most_basic_exp.py
   :language: python
   :caption:

It is important to note that stimuli should be instances, not classes!

Try to run this code or type in the command prompt::

   python -m stytra.examples.most_basic_exp

This will open two windows: one is the main control GUI to run the experiments,
the second is the screen used to display the visual stimuli. In a real experiment, you want
to make sure this second window is presented to the animal. For details on positioning and calibration, please refer to
:ref:`calibration`

For an introduction to the functionality of the user interface, see :ref:`Stytra user interface`.
To start the experiment, just press the play button: a flash will appear on the screen after 4 seconds.


Parametrise the protocol
.........................
Sometimes, we want to control a protocol parameters from the interface. To do this, we can define
protocol class attributes as `Param <https://github.com/portugueslab/lightparam>`_.
All attributes defined as ``Param``s will be modifiable from the user interface.

For a complete description of Params inside stytra see :ref:`parameters`.

.. literalinclude:: ../../stytra/examples/flash_exp.py
   :language: python
   :caption:

Note that Parameters in Protocol param are the ones that can be changed from the GUI, but
all stimulus attributes will be saved in the final log, both parameterized and unparameterized ones.
No aspect of the stimulus configuration will be unsaved.


Define dynamic stimuli
----------------------
Many stimuli may have quantities, such as velocity for gratings or
angular velocity for windmills, that change over time. To define these
kind of stimuli Stytra use a convenient syntax: a param_df `pandas <https://pandas.pydata.org>`_ DataFrame
with the specification of the desired parameter value at specific timepoints.
The value at all the other timepoints will be linearly interpolated from the
DataFrame. The dataframe has to contain a `t` column with the time, and one
column for each quantity that has to change over time (`x`, `theta`, etc.).
This stimulus behaviour is handled by the :class:`Stimulus <stytra.stimulation.stimuli.InterpolatedStimulus>`
class.

In this example, we use a dataframe for changing the diameter of a circle
stimulus, making it a looming object:

.. literalinclude:: ../../stytra/examples/looming_exp.py
   :language: python
   :caption:


Use velocities instead of quantities
....................................

For every quantity we can specify the velocity at which it changes instead of
the value itself. This can be done prefixing `vel_` to the quantity name
in the DataFrame.
In the next example, we use this syntax to create moving gratings. What is
dynamically updated is the
position `x` of the gratings, but with the dictionary we specify its velocity
with `vel_x`.

.. literalinclude:: ../../stytra/examples/gratings_exp.py
   :language: python
   :caption:

You can look in the code of the windmill_exp.py example to see how to use
the dataframe to specify a more complex motion - in this case, a rotation with
sinusoidal velocity.

.. note::
    If aspects of your stimulus change abruptly, you can put twice the same
    timepoint in the param_df, for example:
    param_df = pd.DataFrame(dict(t = [0, 10, 10, 20], vel_x = [0, 0, 10, 10])


Visualise with stim_plot parameter
..................................

If you want to monitor in real time the changes in your experiment
parameters, you can pass the stim_plot argument to the call to stytra to add
to the interface an online plot:

.. literalinclude:: ../../stytra/examples/plot_dynamic_exp.py
   :language: python
   :caption:


Stimulation and tracking
------------------------

Add a camera to a protocol
..........................

We often need to have frames streamed from a file or a camera. In the following
example we comment on how to achieve this when defining a protocol:

.. literalinclude:: ../../stytra/examples/display_camera_exp.py
   :language: python
   :caption:

Note however that usually the camera settings are always the same on the
computer that controls a setup, therefore the camera settings are defined in
the user config file and generally not required at the protocol level.
See :ref:`compconfig` for more info.

Add tracking to a defined protocol
..................................

To add tail or eye tracking to a protocol, it is enough to change the
`stytra_config` attribute to contain a tracking argument as well. See the
experiment documentation for a description of the available tracking methods.

In this example, we redefine the previously defined windmill protocol (which
displays a rotating windmill) to add tracking of the eyes as well:

.. literalinclude:: ../../stytra/examples/tail_tracking_exp.py
   :language: python
   :caption:

Now a window with the fish image an a ROI to control tail position will appear,
and the tail will be tracked! See :ref:`tailtracking` for instructions on
how to adjust tracking parameters.

Closed-loop experiments
-----------------------

Stytra allows to simple definition of closed-loop experiments where quantities
tracked from the camera are dynamically used to update some stimulus variable.
In the example below we create a full-screen stimulus that turns red when
the fish is swimming above a certain threshold (estimated with the vigour
method).

.. literalinclude:: ../../stytra/examples/custom_visual_exp.py
   :language: python
   :caption:


Freely-swimming experiments
---------------------------

For freely swimming experiments, it is important to calibrate the camera view
to the displayed image. This is explained in :ref:`calibration`. Then, we can
easily create stimuli that track or change depending on the location of the fish.
The following example shows the implementation of a simple phototaxis protocol,
where the bright field is always displayed on the right side of the fish, and
a centering stimulus is activated if the fish swims out of the field of view.
Configuring tracking for freely-swimming experiments is explained here :ref:`fishtracking`

.. literalinclude:: ../../stytra/examples/phototaxis.py
   :language: python
   :caption:


Defining custom Experiment classes
----------------------------------

New Experiment objects with custom requirements might be needed; for example, if one wants
to implement more events or controls when the experiment start and finishes, or if custom
UIs with new plots are desired. In this case, we will have to sublcass the stytra :class:`Experiment <stytra.experiments.Experiment>`
class. This class already has the minimal structure for running an experimental protocol and
collect metadata. Using it as a template, we can define a new custom class.

Start an Experiment bypassing the Stytra constructor
....................................................

First, to use a custom Experiment we need to see how we can start it bypassing the :class:`Stytra <stytra.Stytra>`
constructor class, which by design deals only with standard Experiment classes. This is very
simple, and it is described in the example below:


.. literalinclude:: ../../stytra/examples/no_stytra_exp.py
   :language: python
   :caption:


Customise an Experiment
.......................

To customize an experiment, we need to subclass :class:`Experiment <stytra.experiments.Experiment>`, or the existing subclasses
:class:`VisualExperiment <stytra.experiments.VisualExperiment>` and
:class:`TrackingExperiment <stytra.experiments.tracking_experiments.TrackingExperiment>`,
which deal with experiments with a projector or with tracking
from a camera, respectively.
In the example below, we see how to make a very simple subclass, with an additional event
(a mask waiting for an OK from the user) implemented at protocol onset. For a description
of how the :class:`Experiment <stytra.experiments.Experiment>` class work, refer to
its documentation.


.. literalinclude:: ../../stytra/examples/custom_exp.py
   :language: python
   :caption:










