.. _tracking-desc:

Image acquisition and tracking
==============================

Image acquisition
-----------------

A key feature of Stytra is the extraction of relevant behavioral features in real time from video inputs. The :class:`Camera <stytra.hardware.video.camera.interface.Camera>` object provides an interface for grabbing frames and setting parameters for a range of different camera types. Currently supported models include those by XIMEA, AVT, PointGray FLIR, and Mikrotron, as well as webcams supported by OpenCV :cite:`opencv_library`. Support for other cameras can be added as long as a Python or C API exists. In addition, previously-recorded videos can also be processed, allowing for offline tracking. Frames are acquired from the original source in a process separated from the user interface and stimulus display. This ensures that the acquisition and tracking frame rate are independent of the stimulus display, which, depending on the complexity of the stimulus and output resolution, can be between 30 and 60 Hz.


.. bibliography:: biblio.bib


Implementation of image processing pipelines
============================================

Image processing and tracking pipelines are defined by subclassing the :class:`Pipeline <stytra.tracking.pipelines.Pipeline>` class.
The pipelines are defined as trees of nodes, starting from the camera image
with each node parametrized using lightparam.
The image processing nodes are subclasses of :class:`ImageToImageNode <stytra.tracking.pipelines.ImageToImageNode>` whereas the terminal
nodes are :class:`ImageToDataNode <stytra.tracking.pipelines.ImageToDataNode>`


Attributes of pipelines are:

- a tree of processing nodes, along
- (optional) a subclass of the camera window which displays the tracking overlay
- (optional) an extra plotting window class

the nodes can be set as attributes of the class,
with names that are arbitrary except for how they are used
by the display and plotting classes (see the :py:mod:`stytra.experiments.fish_pipelines` for examples)

Processing nodes
----------------

There are two types of nodes: :class:`ImageToImageNode <stytra.tracking.pipelines.ImageToImageNode>`
 and  :class:`ImageToDataNode <stytra.tracking.pipelines.ImageToDataNode>`
Nodes must have:

- A name

- A _process function which contains optional parameters
as keyword arguments, annotated with Params for everything
that can be changed from the user interface. The _process
function **has to** output a :class:`NodeOutput <stytra.tracking.pipelines.NodeOutput>` named tuple
(from :module:`stytra.tracking.pipelines.pipeline`) which contains a list of
diagnostic messages (can be empty), and either an
image if the node is a :class:`ImageToImageNode <stytra.tracking.pipelines.ImageToImageNode>`
or a NamedTuple if the node is a :class:`ImageToDataNode <stytra.tracking.pipelines.ImageToDataNode>`

Optionally, if the processing function is stateful (depends on previous inputs),
you can define a reset function which resets the state.

