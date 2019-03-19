Stimulation
===========

One of the main purposes of stytra is to provide a framework to design and
run sequences of stimuli to be presented to the fish.

Stimuli and Protocols in stytra
-------------------------------
The :class:`~stytra.stimulation.stimuli.generic_stimuli.Stimulus` class constitutes
the building block for an experiment in stytra.
A sequence of Stimuli is bundled together and parameterized by the
:class:`~stytra.stimulation.Protocol` class.
See :ref:`protocol-definition`.
for a description of how to create a protocol in stytra.

The :class:`~stytra.stimulation.ProtocolRunner`  class is used to
keep track of time and advance the Stimuli in the Protocol sequence with the proper pace.


.. autoclass::`~stytra.stimulation.ProtocolRunner`

Stimuli examples
----------------

Full-field luminance
....................

.. raw:: html

        <video loop src="_static/stim_movie_full_field.mp4"
        width="200px" autoplay controls></video>

.. literalinclude:: ../../stytra/tests/record_stimuli.py
   :language: python
   :lines: 45-50

Gratings
........

.. raw:: html

        <video loop src="_static/stim_movie_grating.mp4"
        width="200px" autoplay controls></video>

.. literalinclude:: ../../stytra/tests/record_stimuli.py
   :language: python
   :lines: 70-74

OKR inducing rotating windmill stimulus
.......................................

.. raw:: html

        <video loop src="_static/stim_movie_okr.mp4"
        width="200px" autoplay controls></video>

.. literalinclude:: ../../stytra/tests/record_stimuli.py
   :language: python
   :lines: 60-64

Seamlessly-tiled image
......................

.. raw:: html

        <video loop src="_static/stim_movie_seamless_image.mp4"
        width="200px" autoplay controls></video>

.. literalinclude:: ../../stytra/tests/record_stimuli.py
   :language: python
   :lines: 80-87


Radial sine (freely-swimming fish centering stimulus)
.....................................................

.. raw:: html

        <video loop src="_static/stim_movie_radial_sine.mp4"
        width="200px" autoplay controls></video>

.. literalinclude:: ../../stytra/tests/record_stimuli.py
   :language: python
   :lines: 34-36