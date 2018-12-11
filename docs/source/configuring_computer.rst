.. _compconfig:

Configuring a computer for Stytra experiments
=============================================

By default, Stytra checks the user folder (on Windows usually C:/Users/user_name, ~ on Unix-based systems)
for the stytra_setup_config.json file. You can put default settings for the current computer in it,
specifying the e.g. saving format, camera type and ROI, full-screen stimulus display and anything
else that is specified when instantiating :class:`Stytra <stytra.Stytra>` .

An example is provided below:

`stytra_setup.config.json`

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





