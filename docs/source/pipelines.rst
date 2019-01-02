Image processing pipelines
==========================

Image processing pipelines are defined by subclassing the pipeline class.
The pipelines are defined as trees of nodes, starting from the camera image
with each node parametrized using lightparam.
The image processing nodes are subclasses of `ImageToImageNode` whereas the terminal
nodes are `ImageToDataNode`