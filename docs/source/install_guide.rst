Installation guide
==================

Stytra was developed and tested using Python 3.6 and 3.7 installed as part of the
`Anaconda Python <https://www.anaconda.com/download/>`_ distribution. Other Python versions have not been tested.
Make sure you have the latest version of Anaconda installed before proceeding
with the installation. Installation with custom python environments,
Miniconda, or in Anaconda virtual environments could be achieved but might
give dependencies issues. The following instructions have been tested and
work for an installation in the Anaconda root environment.


Installing stytra
-----------------

Stytra relies on `opencv <https://docs.opencv.org/3
.0-beta/doc/py_tutorials/py_tutorials.html>`_ for some of its fish tracking
functions. If you don't have it installed, open the Anaconda prompt and type::

    conda install opencv

This should be everything you need to make ready before installing stytra.

.. note::
    PyQt5 is not listed as an explicit requirement because it should
    come with
    the Anaconda package. If you are not using Anaconda, make sure you have it
    installed and updated before installing stytra!

Now, download stytra in a directory and install it via pip by::

    pip install path_to_stytra/stytra

If you want to be able to change the stytra code and use the current version of the
code, install using the -e argument::


    pip install -e path_to_stytra/stytra


You can test now the installation by running one of the examples in stytra
example folder! To run a simple looming stimulus experiment, you can try to
type::

    python -m stytra.examples.looming_exp

If the GUI opens correctly and you can press the play button:
congratulations, installation was successful! If it crashes horribly, check
if you have all dependencies correctly installed. If it still does not work,
contact us for support through the `stytra github page <https://github
.com/portugueslab/stytra>`_.

Now you can have a look at the stytra :ref:`Examples gallery`, or you can start
:ref:`Configuring a computer for Stytra experiments`.
In the second case, you might want to have a look at the camera APIs section below first.

.. note::
    Stytra might have some problem on quit because of a bug in the current
    version of pyqtgraph (a package we are using for online plotting).
     If you are really annoyed by the error messages
    when closing the program you can install the develop version of pyqtgraph
    from their `github repository <https://github.com/pyqtgraph/pyqtgraph>`_.
    The problem will be solved when
    the new pyqtgraph version will is relased.


Installing camera APIs
----------------------
xiCam: Ximea
............

Download the `Ximea SDK software pacakge for your operating system <https://www.ximea.com/support/wiki/apis/APIs>`_, install it with Python support and copy the contents
of the relevant directory (python3)


pymba: AVT
............

Go to the `Allied Vision software webpage <https://www.alliedvision.com/en/products/software.html>`_
and download and install the Vimba SDK. Then install the python wrapper
`pymba <https://github.com/morefigs/pymba>`_.


spinnaker: Point Grey / FLIR
............................

Go the the `FLIR support website <https://eu.ptgrey.com/support/downloads?countryid=2147483647>`_, download the SDK and the Python API.

1. Install the SDK, by chosing the camera and OS, and then downloading
    e.g. Spinnaker 1.15.0.63 Full SDK - Windows (64-bit) — 07/27/2018 - 517.392MB
    or the equivalent for your operating system

2. Install the python module
    pip install "path_to_extracted_zip/spinnaker_python-1.15.0.63-cp36-cp36m-win_amd64.whl"

(with the file with appropriate OS and Python version)


National Instruments framegrabber with Mikrotron camera
.......................................................

Install the NI vision SDK. For the Mikrotron MC1362 camera, you can use `this <www.portugueslab.com/files/MikrotronMC1362.icd>`_
camera file. The camera file usually needs to be put into C:\Users\Public\Public Documents\National Instruments\NI-IMAQ\Data
After putting the camera file there, is should be selected for the image acquisition device in NI MAX.