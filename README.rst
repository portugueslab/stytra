======
Stytra
======

A modular package to control stimulation and track behavior in zebrafish experiments.
---------------

.. image:: https://cdn.rawgit.com/portugueslab/stytra/644a23d5/stytra/icons/stytra_logo.svg
    :scale: 50%
    :alt: Logo

.. image:: https://badge.fury.io/py/stytra.svg
    :target: https://pypi.org/project/stytra/

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3238310.svg
   :target: https://doi.org/10.5281/zenodo.3238310

.. image:: https://img.shields.io/badge/docs-0.8-yellow.svg
    :target: http://www.portugueslab.com/stytra/
    
.. image:: https://travis-ci.org/portugueslab/stytra.svg?branch=master
    :target: https://travis-ci.org/portugueslab/stytra


If you are using Stytra for your own research, please `cite us <https://doi.org/10.1371/journal.pcbi.1006699>`_!
    
Stytra is divided into independent modules which can be assembled
depending on the experimental requirements.

Simple usage examples can be found in the examples folder.


Quick installation guide
------------------------

Stytra relies on `opencv <https://docs.opencv.org/3
.0-beta/doc/py_tutorials/py_tutorials.html>`_ for some of its fish tracking
functions. If you don't have it installed, open the Anaconda prompt and type::

    conda install opencv

If you are using Windows, git (used for tracking software versions) might not be
installed. Git can also be easily installed with conda::

    conda install git


This should be everything you need to make ready before installing stytra.

 > PyQt5 is not listed as an explicit requirement because it should come with the Anaconda package. If you are not using Anaconda, make sure you have it installed and updated before installing Stytra!

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



Now you can have a look at the stytra :ref:`Examples gallery`, or you can start
:ref:`Configuring a computer for Stytra experiments`.
In the second case, you might want to have a look at the camera APIs section below first.

.. note::
    Stytra might raise an error after quitting because of a bug in the current
    version of pyqtgraph (a package we are using for online plotting).
    If you are annoyed by the error messages
    when closing the program you can install the develop version of pyqtgraph
    from their `github repository <https://github.com/pyqtgraph/pyqtgraph>`_.
    The problem will be resolved once the next pyqtgraph version is released.

For further details please consult the `documentation <http://www.portugueslab.com/stytra/>`_
