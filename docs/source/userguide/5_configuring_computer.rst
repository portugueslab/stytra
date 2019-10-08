.. _compconfig:

Configuring a computer for Stytra experiments
=============================================

By default, Stytra checks the user folder (on Windows usually C:/Users/user_name, ~ on Unix-based systems)
for the stytra_setup_config.json file. You can put default settings for the current computer in it,
specifying the e.g. saving format, camera type and ROI, full-screen stimulus display and anything
else that is specified when instantiating :class:`Stytra <stytra.Stytra>` .

An example is provided below:

`stytra_setup_config.json`

.. code-block:: json

    {
    "display": {"full_screen": true},
    "dir_save": "J:/_Shared/experiments",
    "dir_assets": "J:/_Shared/stytra_resources",
    "log_format": "hdf5",
    "camera": {"type": "ximea", "rotation":-1, "roi":[0, 0, 784, 784]},
    "tracking": {"method":"fish"},
    "embedded" : false
    }


Camera configuration
--------------------

The currently supported cameras and features controllable from Stytra are:

==============  ==================  ===  ========  =========  ====
Manufacturer    Stytra camera type  ROI  Exposure  Framerate  Gain
--------------  ------------------  ---  --------  ---------  ----
Ximea           ximea               Yes  Yes       Yes        Yes
FLIR/PointGrey  spinnaker           Yes  Yes       Yes        Yes
AVT             avt                 No   No        No         No
Basler          basler              No   Yes       ?          ?
Mikrotron       mikrotron           Yes  Yes       Yes        No
OpenCV          opencv              No   ?         ?          ?
==============  ==================  ===  ========  =========  =====

To use a camera with Stytra, either put it in the stytra_setup_config.json file or, in a script that runs Stytra set the camera argument, e.g.::

    Stytra(protocol=ClosedLoopProtocol(), camera=dict(type="ximea")


The priority of the configuration settings is the stytra_setup_config.json (lowest), the stytra_config dictionary in the Protocol class and the keyword arguments when calling Stytra.


Trying example protocols on your setup
--------------------------------------

Copy the example file you are interested in from the repository (e.g. `stytra/examples/closed_loop_exp.py <https://github.com/portugueslab/stytra/blob/master/stytra/examples/closed_loop_exp.py>`_) and either:

- remove the camera entry from the stytra_config dictionary in the protocol class and create the stytra_setup_config.json file

- change the stytra_config dictionary in the protocol definition

- add a keyword argument to the stytra call specifying the camera
