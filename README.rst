======
Stytra
======

A modular package to control stimulation and track behaviour in zebrafish experiments.
---------------

.. image:: https://cdn.rawgit.com/portugueslab/stytra/644a23d5/stytra/icons/stytra_logo.svg
    :scale: 50%
    :alt: Logo

`Documentation <http://www.portugueslab.com/stytra/>`_ 

Stytra is divided into independent modules which can be assembled
depending on the experimental requirements.

Simple usage examples can be found in the examples folder.


Quick installation guide
------------------------
Stytra was developed and tested using Python 3.6 installed as part of the
`Anaconda Python <https://www.anaconda.com/download/>`_ distribution. Make
sure you have the latest version of Anaconda installed before proceeding with
the installation.
Other Python versions have not been tested.

Stytra relies on `opencv <https://docs.opencv.org/3
.0-beta/doc/py_tutorials/py_tutorials.html>`_ for some of its fish tracking
functions. If you don't have it installed, open the Anaconda prompt and type::

    conda install opencv

If you want to use video formats for stimulation or record videos, PyAV is required,
also easily installable with Anaconda:

    conda install -c conda-forge av

Download Stytra from github as a zip file or clone it with git and install it via pip by::

    pip install path_to_stytra/stytra

To test the installation, you can try to run an example experiment from the prompt with::
    
    python -m stytra.examples.looming_experiment


.. note::
    PyQt5 is not listed as an explicit requirement because it should
    come with
    the Anaconda package. If you are not using Anaconda, make sure you have it
    installed and updated before installing stytra.
