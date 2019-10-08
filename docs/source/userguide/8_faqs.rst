Frequently Asked Questions
==========================

A little but expanding list of common user questions where maybe you can find
what you are looking for. If not, feel free to contact us on github or mail


What is Stytra good for?
........................
Animal experiments where different kinds of external devices have to be integrated, a paradigm is used where the stimulation depends on the behavior on the animal. The default feature set is especially well-suited to situations with video tracking and visual displays.

What is Stytra not good for?
............................
Experiments where visual or other stimulation needs to be provided with sub-milisecond precision.

I need to start a new experiment in the lab. Can I use Stytra?
..............................................................
If it involves behavior, probably, see above.

I don't know Python, can I use Stytra?
......................................
Yes, but only with the protocols we provide or for offline fish tracking (see )


I know only a bit of Python, can I use Stytra?
..............................................
Yes! Not much is needed to get started, look at examples.

I need to setup Stytra to run experiments on my computer. What should I do?
...........................................................................
Look at installation

I need to design a new stimulus. What should I do?
..................................................
Look at the stimuli library

What are all these Param(n.) things? Do I have to care?
.......................................................
The Param objects are used to automatically create user interfaces.

I need to use a custom tracking function. What should I do?
...........................................................
Consult the relevant section of the developer documentation

I have run a Stytra experiment. And now what? What's in the log files?
......................................................................
...

Can I run two setups from the same computer?
............................................
Yes! There should be no issues, as long as the computer has enough cores and the demanded tracking framerate is not too high.

I have used the freely swimming fish tracking. What are the units of my output?
...............................................................................
The fish location in camera pixel coordinates (see coordinate systems), the direction of the tail (theta) and relative tail angles (theta_00 -  theta_xx) describing the tail shape. The first 3 outputs additionally have velocities estimated through Kalman filtering that have to be normalised by the framerate.


