The structure of Stytra
=======================

.. image:: ../figures/data_flow.svg
   :scale: 80%
   :alt: dataflow diagram
   :align: center

We developed Stytra using the Python programming language. We endeavored to follow best practices in software engineering: separation of user interface and data processing code, modularity and consistent programming interfaces.

In Stytra, new experiments can be designed using very simple Python syntax, allowing even beginners in programming to develop their own stimulation paradigms. Once defined, the experiment is controlled through a graphical user interface which can be used with no knowledge of Python.


At the core of the Stytra package lies the :class:`~stytra.experiments.Experiment` object, which links all components that may be used in an experiment: stimulus presentation, camera, animal tracking, metadata and logging. This organization enables composing different experimental paradigms with full code reuse. Improvement of different modules (e.g. the user interface, plotting or tracking) is therefore reflected in all experimental setups, and support for a new piece of hardware or tracking function can be added with minimal effort and interference
with other parts of the project. Online image processing is organized along
a sequence of steps: first, images are acquired from the camera, then the image is filtered and tracked, and the tracking results are saved. Acquisition, tracking and data saving occur in separate processes (depicted in blue, purple, and green in the diagram below). This approach improves the reliability and the performance of online behavioral tracking, and exploits the advantages of multi-core processors. After processing, streaming numerical data (such as tracking results and dynamic parameters of stimuli) is passed into data accumulators in the main thread, and a user-selected subset can be plotted in real time and saved in one of the several supported formats. Moreover, for every experimental session all changeable properties impacting the execution of the experiment are recorded and saved. Finally, as the software package is version-controlled, the version (commit hash) of the software in use is saved as well, ensuring the complete reproducibility of every experiment.

.. image:: ../figures/dataflow_classes.svg
   :scale: 80%
   :alt: dataflow class diagram
   :align: center

Basic classes
_____________

