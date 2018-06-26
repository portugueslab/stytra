Stimulation
===========

One of the main purposes of stytra is to provide a framework to design and
run sequences of stimuli to be presented to the fish.

Stimuli and Protocols in stytra
-------------------------------
The :class:`~stytra.stimulation.stimuli.Stimulus` class constitutes
the building block for an experiment in stytra.
A sequence of Stimuli is bundled together and parameterized by the
:class:`~stytra.stimulation.protocols.Protocol` class.
See :ref:`Create stimulus sequence`
for a description of how to create a protocol in stytra.

The :class:`~stytra.stimulation.ProtocolRunner`  class is used to
keep track of time and set the Stimuli in the Protocol sequence with the proper pace.


