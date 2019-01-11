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
