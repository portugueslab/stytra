Installation guide
==================

Stytra was developed and tested using Python 3.6 installed as part of the
`Anaconda Python <https://www.anaconda.com/download/>`_ distribution. Make
sure you have the latest version of Anaconda installed before proceeding with
the installation.
Other Python versions have not been tested.


Installing stytra
-----------------

Stytra relies on `opencv <https://docs.opencv.org/3
.0-beta/doc/py_tutorials/py_tutorials.html>`_ for some of its fish tracking
functions. If you don't have it installed, open the Anaconda prompt and type::

    conda install opencv

Once you have that, download stytra in a directory and install it via pip by::

    pip install path_to_stytra/stytra


.. note::
    PyQt5 is not listed as an explicit requirement because it should
    come with
    the Anaconda package. If you are not using Anaconda, make sure you have it
    installed and updated before installing stytra.


Installing camera APIs
----------------------


spinnaker: Point Grey / FLIR
............................

Go the the `FLIR support website <https://eu.ptgrey.com/support/downloads?countryid=2147483647>`_, download the SDK and the Python API.

1. Install the SDK, by chosing the camera and OS, and then downloading
    e.g. Spinnaker 1.15.0.63 Full SDK - Windows (64-bit) — 07/27/2018 - 517.392MB
    or the equivalent for your operating system

2. Install the python module
    pip install "path_to_extracted_zip/spinnaker_python-1.15.0.63-cp36-cp36m-win_amd64.whl"

(with the file with appropriate OS and Python version)