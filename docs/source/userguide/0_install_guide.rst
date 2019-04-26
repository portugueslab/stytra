Installation
============

Stytra was developed and tested using Python 3.7 installed as part of the
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

If you are using Windows, git (used for tracking software versions) might not be
installed. Git can also be easily installed with conda::

    conda install git


Also, for some video-related operations (offline tracking and saving of stimulus videos), a version of ffmpeg with libx264 has to be installed, for this, use the conda-forge channel::

    conda install -c conda-forge ffmpeg

These are all requirements not covered by the next installation step.

.. note::
    PyQt5 is not listed as an explicit requirement because it should
    come with
    the Anaconda package. If you are not using Anaconda, make sure you have it
    installed and updated before installing Stytra!

The simplest way to install Stytra is with pip::

    pip install stytra

You can verify the installation by running one of the examples in stytra
examples folder. To run a simple looming stimulus experiment, you can
type::

    python -m stytra.examples.looming_exp

If the GUI opens correctly and pressing the play button starts the stimulus:
congratulations, installation was successful! If it crashes, check
if you have all dependencies correctly installed. If it still does not work,
open an issue on the `Stytra github page <https://github
.com/portugueslab/stytra>`_.

Editable installation
.....................

On the other hand, if you want to modify the internals of stytra or use the
unreleased features, clone or download stytra from `github <https://github.com/portugueslab/stytra>`_ and install it with::

    pip install path_to_stytra/stytra

If you want to be able to change the stytra code and use the changed version,
install using the -e argument::


    pip install -e path_to_stytra/stytra



Now you can have a look at the stytra :ref:`Examples gallery <examples-gallery>`, or you can start
:ref:`Configuring a computer for Stytra experiments`.
In the second case, you might want to have a look at the camera APIs section below first.

.. note::
    Stytra might raise an error after quitting because of a bug in the current
    version of pyqtgraph (a package we are using for online plotting).
    If you are annoyed by the error messages
    when closing the program you can install the develop version of pyqtgraph
    from their `github repository <https://github.com/pyqtgraph/pyqtgraph>`_.
    The problem will be resolved once the next pyqtgraph version is released.


Installing camera APIs
----------------------
xiCam: Ximea
............

Download the `Ximea SDK software pacakge for your operating system <https://www.ximea.com/support/wiki/apis/APIs>`_,
during the installation wizard make sure that you select the python API checkbox.
After installation, copy the python wrapper API (in the folder where you installed XIMEA, ...\XIMEA\API\Python\v3\ximea) into
the Python site-packages folder (for anaconda, usually the folder ...\anaconda3\Lib\site-packages)


pymba: AVT
............

Go to the `Allied Vision software webpage <https://www.alliedvision.com/en/products/software.html>`_
and download and install the Vimba SDK. Then install the python wrapper
`pymba <https://github.com/morefigs/pymba>`_. You can install it from source::

    pip install git+https://github.com/morefigs/pymba.git

or, if using 64bit windows, you can grab the installation file from `here <http://www.portugueslab.com/files/pymba-0.1-py3-none-any.whl>`_.
Open the terminal in the folder where you downloaded it and install::

    pip install pymba-0.1-py3-none-any.whl


spinnaker: Point Grey / FLIR
............................

Go the the `FLIR support website <https://eu.ptgrey.com/support/downloads?countryid=2147483647>`_, download the SDK and the Python API.

1. Install the SDK, by chosing the camera and OS, and then downloading e.g. Spinnaker 1.15.0.63 Full SDK - Windows (64-bit) — 07/27/2018 - 517.392MB or the equivalent for your operating system

2. Install the python module::

    pip install "path_to_extracted_zip/spinnaker_python-1.15.0.63-cp36-cp36m-win_amd64.whl"

(with the file with the appropriate OS and Python versions)


.. note::
    The FLIR/Spinnaker Python API currently does not support Python 3.7, so you might need to install a Python 3.6 conda environment to use it. 

National Instruments framegrabber with Mikrotron camera
.......................................................

Install the NI vision SDK. For the Mikrotron MC1362 camera, you can use `this <http://www.portugueslab.com/files/MikrotronMC1362.icd>`_
camera file. The camera file usually needs to be put into C:\Users\Public\Public Documents\National Instruments\NI-IMAQ\Data
After putting the camera file there, is should be selected for the image acquisition device in NI MAX.