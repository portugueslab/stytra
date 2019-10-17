.. _dev-pipelines:

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
with names that are arbitrary, except for how they are used
by the display and plotting classes (see the :py:mod:`stytra.experiments.fish_pipelines` for examples)
To pass data through nodes you have to set the parent attribute. The first nodes to receive data from the camera have to have the root node as parent (`parent=self.root`)


Processing nodes
----------------


There are two types of nodes: :class:`ImageToImageNode <stytra.tracking.pipelines.ImageToImageNode>` and  :class:`ImageToDataNode <stytra.tracking.pipelines.ImageToDataNode>`

Nodes must have:

- A name

- A _process method which contains optional parameters as keyword arguments, annotated with Params for everything that can be changed from the user interface.

The _process function **has to** output a :class:`NodeOutput <stytra.tracking.pipelines.NodeOutput>` named tuple (from :py:mod:`stytra.tracking.pipelines`) which contains a list of diagnostic messages (can be empty), and either an image if the node is a :class:`ImageToImageNode <stytra.tracking.pipelines.ImageToImageNode>` or a NamedTuple if the node is a :class:`ImageToDataNode <stytra.tracking.pipelines.ImageToDataNode>`

Optionally, if the processing function is stateful (depends on previous inputs),
you can define a reset function which resets the state.
