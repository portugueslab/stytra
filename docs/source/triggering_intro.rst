Triggering a trytra protocol
============================

Stytra is designed to be used in setups where the presentation of stimuli to
the  animal needs to be synchronized with an acquisition program running on a
different computer, e.g. controlling a two-photon microscope. To this end, the
triggering module provides classes to ensure communication with external devices
to time the beginning of the experiment. Two methods are already supported in
the triggering library:

TTL pulse triggering on a Labjack/NI board and serial ports.
............................................................

In the first simple configuration, Stytra simply waits for a TTL pulse
received on a Labjack or a NI board to start the experiment.

ZeroMQ
......
Stytra employs the ZeroMQ library to synchronize the beginning
of the experiment through a message coming from the acquisition computer over
the local network. ZeroMQ is supported in a number of programming and scripting
languages, including LabView, and the exchange of the synchronizing message
can easily be added to custom-made or open-source software. The messages
can also be used to communicate to Stytra data such as the microscope
configuration that will be logged together with the rest of experiment
metadata.

A common framework to build custom software for hardware control is LabView.
In our laboratory, a LabView program is used to control the scanning from the
 two-photon microscope. Below we report a screenshot of a very simple subVI
 that can be used together with Stytra for triggering the start of the
 stimulation. A ZMQ context is created, and than used to send a json file
 with the information about microscope configuration over the network to the
 ip of the computer running Stytra, identified by its IP. Stytra uses by
 default port 5555 to listen for triggering messages.

.. image:: ../hardware_list/pictures/zmq.png
   :scale: 80%
   :alt: alternate text
   :align: center



Additional methods
..................
The triggering module is also designed to be expandable.
It is possible to define new kinds of triggers, which consists of
a processes that continuously checks a condition.
To define a new trigger, e.g., starting the acquisition when a new file is
created in a folder, it is enough to write a method that uses the python
standard library to monitor folder contents.

