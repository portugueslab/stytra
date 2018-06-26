======
Stytra
======

.. image:: https://readthedocs.org/projects/stytra/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://stytra.readthedocs.io/en/latest/?badge=latest

A modular package to control stimulation and track behaviour in zebrafish experiments.
---------------

*screenshot goes here*

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
functions. If you don't have it install, open the Anaconda prompt and type::

    conda install opencv -c conda-forge

Once you have that, download stytra in a directory and install it via pip by::

    pip install path_to_stytra/stytra


.. note::
    PyQt5 is not listed as an explicit requirement because it should
    come with
    the Anaconda package. If you are not using Anaconda, make sure you have it
    installed and updated before installing stytra.
