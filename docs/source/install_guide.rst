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
The SDK can be installed with the online installer, and the Python module after unzipping with pip
::

    pip install "path_to_extracted_zip/spinnaker_python-1.15.0.63-cp36-cp36m-win_amd64.whl"

(with the file with appropriate OS and Python version)