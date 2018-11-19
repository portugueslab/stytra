Triggering stimulation
======================

Stytra is designed to be used in setups where the presentation of stimuli to
the  animal needs to be synchronized with an acquisition program running on a
different computer, e.g. controlling a two-photon microscope. To this end, the
triggering module provides classes to ensure communication with external devices
to time the beginning of the experiment. Two methods are already supported in
the triggering library:

TTL pulse triggering on a Labjack/NI board and serial ports.
............................................................

In the first simple configuration, stytra simply waits for a TTL pulse
received on a Labjack or a NI board to start the experiment.

ZeroMQ
......
Stytra employs the ZeroMQ library to synchronize the beginning
of the experiment through a message coming from the acquisition computer over
the local network. ZeroMQ is supported in a number of programming and scripting
languages, including LabView, and the exchange of the synchronizing message
can easily be added to custom-made or open-source software. The messages
can also be used to communicate to stytra data such as the microscope
configuration that will be logged together with the rest of experiment
metadata.

Additional methods
..................
The triggering module is also designed to be expandable.
It is possible to define new kinds of triggers, which consists of
a processes that continuously checks a condition.
To define a new trigger, e.g., starting the acquisition when a new file is
created in a folder, it is enough to write a method that uses the python
standard library to monitor folder contents.

