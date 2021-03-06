.. _hardware-list:

Hardware description
====================

In our effort to make experiments as open and reproducible as possible, we documented example setups that can be used together with the Stytra software for performing behavioral experiments in head-restrained and freely swimming fish. In general, the minimal setup for tracking the fish larvae requires a high-speed camera (a minimum of 100 Hz is required to capture the most common tail beats which have a frequency up to 50 Hz, but we recommend at least 300 Hz to describe the details of the tail kinematics). The camera must be equipped with a suitable objective: a macro lens for the head-restrained tail tracking or a normal lens for the freely swimming recordings, where a smaller magnification and a larger field of view are required.  Infrared illumination is then used to provide contrast without interfering with the animal's visual perception.
Since fish strongly rely on vision and many of their reflexes can be triggered by visual stimulation, the setup is usually equipped with a projector or screen to present the visual stimulus to the fish. Although in our setups stimuli are projected below the fish, a lateral projector would be fully compatible with Stytra.
Most of our rig frames consist of optomechanical parts commonly used for building microscopes. These parts are convenient but not strictly necessary to build a well-functioning rig. Replacing them with simple hardware-store and laser-cut components can significantly reduce the costs.  Therefore, we also provide instructions for a head-restrained setup built inside a cardboard box, where the most expensive item is the high-speed camera, bringing the price of the whole setup without the computer below 700 euros.

Here we describe two configurations of our setups: the first one is for detailed kinematic tracking of eyes and tail in a fish with head restrained in agarose, the second for tracking freely swimming fish in a petri dish.

Finally, we present a cheap version of the behavioral setup that can be
easily built for about 700 euros, and easily assembled using cardboard,
laser-cut parts or other custom-made enclosures.

Head-restrained fish setup
--------------------------

This configuration requires high magnification, provided by a 50 mm macro
objective. On the other side, illumination be provided only in a very
small field and can be accomplished by with a simple single IR-LED.

.. image:: ../../hardware_list/pictures/embedded.png
   :scale: 18%
   :alt: alternate text
   :align: center



Freely swimming fish setup
--------------------------

This configuration uses a camera with larger field of view and a custom-built
LED box for illuminating homogeneously a large area.

.. image:: ../../hardware_list/pictures/freely.png
   :scale: 18%
   :alt: alternate text
   :align: center


List of components
------------------
Below we provide a list of all components required for building the two
setups. Indicative prices in euros (Jul 2018) and links to
supplier pages are provided as well.


.. note::
    Many parts of the setup, such as the base, the stage and the holders can
    easily be replaced with custom solutions.


.. image:: ../../hardware_list/pictures/parts_full.png
   :scale: 30%
   :alt: alternate text
   :align: center


Head-restrained setup
.....................
.. csv-table:: Components for embedded configuration behavioral setup
   :file: ../../hardware_list/embedded.csv
   :widths: 10, 25, 25, 25, 25, 25, 25, 25, 25, 25
   :header-rows: 1


Freely-swimming setup
.....................
.. csv-table:: Components for freely swimming configuration behavioral setup
   :file: ../../hardware_list/freely_swimming.csv
   :widths: 10, 25, 25, 25, 25, 25, 25, 25, 25, 25
   :header-rows: 1

Low-cost behavioral setup
--------------------------
A very cheap version of the behavioral setup can be built by replacing the
projector with small LED display and the camera lens with a fixed focal length
objective. The dimensions of this setup are quite small and parts can be kept in place with
a basic custom-made frame that can be laser-cut or even made out of cardboard.


.. image:: ../../hardware_list/pictures/low_cost.png
   :scale: 15%
   :alt: alternate text
   :align: center