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

    @property
    def output_type_changed(self):
        return False

    def process(self, *inputs):
        return self._process(*inputs, **self._params.params.values)

    def _process(self, *inputs, **kwargs):
        return [], None


class ImageToImageNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def output_type_changed(self):
        return any(c.output_type_chaged for c in self.children)


class SourceNode(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process(self):
        return [], None


class CameraSourceNode(ImageToImageNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process(self):
        return [], self.camera_queue.get(timeout=0.001)


class ImageToDataNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.name = "testnode"
        self._output_type = None
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

    def recursive_run(self, node: PipelineNode, *input_data):
        output = node.process(*input_data)
        if isinstance(node, ImageToDataNode):
            return output

        child_outputs = tuple(self.recursive_run(child, output[1])
                   for child in node.children)
        if self._output_type is None or node.output_type_changed:
            self._output_type = namedtuple("o",
                                           chain.from_iterable(
                                               map(lambda x:x[1]._fields,
                                                    child_outputs)))
        # collect all diagnostic messages and return a named tuple collecting
        # all the outputs
        return (output[0]+list(chain.from_iterable(map(lambda x:x[0], child_outputs))),
                self._output_type(*(chain.from_iterable(
                    map(lambda x:x[1], child_outputs)))))

    def run(self):
        return self.recursive_run(self.root)



