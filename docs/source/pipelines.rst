Image processing pipelines
==========================

Image processing and tracking pipelines are defined by subclassing the `Pipeline` class.
The pipelines are defined as trees of nodes, starting from the camera image
with each node parametrized using lightparam.
The image processing nodes are subclasses of `ImageToImageNode` whereas the terminal
nodes are `ImageToDataNode`

Attributes of pipelines are:

- a tree of processing nodes, along
- (optional) a subclass of the camera window which displays the tracking overlay
- (optional) an extra plotting window class

the nodes can be set as attributes of the class,
with names that are arbitrary except for how they are used
by the display and plotting classes (see the ... for exampls)

Processing nodes
----------------

There are two types of nodes: `ImageToImageNode`  and `ImageToDataNode`

Nodes must have:
A name

A _process function which contains optional parameters
as keyword arguments, annotated with Params for everything
that can be changed from the user interface. The _process
function **has to** output a NodeOutput named tuple
(from stytra.tracking.pipeline) which contains a list of
diagnostic messages (can be empty), and either an
image if the node is a ImageToImageNode
or a NamedTuple if the node is a ImageToDataNode

Optionally, if the processing function is stateful,
you can define a reset function which resets the state.

