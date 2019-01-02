from lightparam import Parametrized, Param
from anytree import PreOrderIter, NodeMixin
from multiprocessing import Queue
from collections import namedtuple
from itertools import chain


class PipelineNode(NodeMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._params = None
        self.diagnostic_images = dict()

    def setup(self):
        self._params = Parametrized(params=self._process)

    def process(self, *inputs):
        return self._process(*inputs, **self._params.params.values)

    def process(self, *inputs, **kwargs):
        return None


class ImageToImageNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def output_type_changed(self):
        return any(c.output_type_chaged for c in self.children)


class SourceNode(ImageToImageNode):
    def __init__(self, *args, camera_queue, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "source"
        self.camera_queue = camera_queue

    def process(self):
        return self.camera_queue.get(timeout=0.001)


class ImageToDataNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.name = "testnode"
        self._ouput_type = None
        self._params = None
        self._output_type_changed = False

    @property
    def output_type_changed(self):
        return self._output_type_changed

    def _process(self):
        # Node processing code

        # Output type handling
        return None


class Pipeline:
    def __init__(self):
        self.comm_queue = Queue()
        self.display_overlay = None
        self.display_handles = None
        self.root = SourceNode()
        self.selected_output = None
        self._output_type = None

    def setup(self):
        """ Due to multiprocessing limitations, the setup is
        run separately from the constructor

        """
        for node in PreOrderIter(self.root):
            node.setup()

    def recursive_run(self, node: NodeMixin, *input_data):
        if isinstance(node, ImageToDataNode):
            return node.process(*input_data)
        else:
            outputs = tuple(self.recursive_run(child, *input_data)
                       for child in node.children)
            if self._output_type is None or node.output_type_changed:
                self._output_type = namedtuple("o",
                                               chain.from_iterable(k._fields
                                                                   for k in outputs))

    def run(self):
        recursive_run(self.root)



