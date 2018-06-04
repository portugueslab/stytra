Introduction
============

Overview
--------
Stytra is a package to build and run behavioural experiments. It is developed with a focus
on imaging and behavioural experiments on larval zebrafish


Features
--------
Stytra implements many functions:
 - easily design sequences of visual stimuli and/or trigger external stimulation
   devices via serial communication or **to be implemented TTL pulses**
 - acquire video from a camera, and process images to extract behaviourally relevant
   quantities like eyes and tail position;
 - multiprocessing framework to handle video streaming and processing with APIs for
   adding other custom tracking functions;
 - save experiment metadata together with experiment and behaviour log;