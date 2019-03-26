Comparison with existing software packages
==========================================
Many general-purpose systems have been proposed over the years
to present visual and other kinds of stimuli and control behavioral
experiments, each with its own strengths and limitations.
Below we sum up some of the systems which are currently maintained,
and we present how they compare to Stytra.

Bonsai
------
`Bonsai <http://www.kampff-lab.org/bonsai>`_
is a visual programming language built
on top of the language C\# with a reactive, dataflow-based paradigm.
In Bonsai, users with little experience in programming can implement
their own tracking pipelines and basic stimuli.
By default Bonsai offers visualization of any data processing node,
and custom visualizers. In principle, due to the generality of Bonsai,
all functions of Stytra could be implemented within it. Still,
implementing many features would require using a programming language
uncommon in science (C#). Also, the use of several Python libraries,
such as DeepLabCut, is in many cases not possible, as only a subset of
Python is supported in C# through the IronPython interpreter.

Psychophysics Toolbox
---------------------
`Psychophysics Toolbox <http://psychtoolbox.org/>`_ offers a
large toolbox to build visual stimuli and stimulation protocols.
The toolbox has been developed with human psychophysics in mind,
in particular visual and auditory psychophysics. It provides large
control over display and sound hardware, and many tools for acquiring
responses from the subject through the mouse and keyboard. Still, its
application is restricted to the stimulus design, as it does not offer
any camera integration or animal tracking modules. This makes
the toolbox ill-suited for developing closed-loop stimuli where
behavior and responses of the animal need to be fed back to the
stimulus control software. Moreover, it relies on the proprietary
software package Matlab.

Psychopy
--------
`PsychoPy <https://www.psychopy.org/>`_ is a library similar to the
Psychophysics Toolbox, written in Python. It provides precise
control over displaying visual and auditory stimuli (not currently
implemented in Stytra), and a set of tools for recording responses
through standard computer inputs (mouse and keyboard). Due to its
wide use in human psychophysics experiments, it has a larger library
of stimuli than Stytra. However, it is also purely a stimulation
library without video or other data acquisition support. Moreover,
it does not provide a system for easy online control of stimulus
parameters, an essential feature for closed-loop experiments.

MWorks
-----------
`MWorks <https://mworks.github.io/>`_ is a C/C++ library to
control neurophysiological
experiments, developed mostly for (visual) neurophysiology
in primates and rodents. It provides support for building complex
tasks involving trials with different possible outcomes, and contains
a dedicated library for handling visual stimuli. Due to being
implemented in a compiled language, higher and more consistent
performance can be obtained than with our package, which is
Python based. However, it is not designed for online video analysis
of behavior, which is essential for behaviorally-controlled closed-loop
experiments. Furthermore, while scripting and expanding
Stytra requires pure Python syntax, experiments in MonkeyWorks
are coded in  custom high-level scripting language based on C++.
Most importantly, it runs only on MacOS, which depends on Apple
hardware, available only in a minority of laboratories.

ZebEyeTrack
-----------
`ZebEyeTrack <http://www.zebeyetrack.com/>`_
covers a small subset of Stytra functionality - eye tracking
and eye-motion related stimulus presentation. It is implemented
in LabView and Matlab, which adds two expensive proprietary
software dependencies. Running an experiment requires launching
separate programs and many manual steps as described in the
publication. The tracking frame rate is limited to 30 Hz in real-time
while Stytra can perform online eye tracking at 500 Hz, and Stytra's
performance is mainly limited by the camera frame rate.


