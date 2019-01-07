from lightparam import Parametrized, Param
from anytree import PreOrderIter, Node, Resolver
from multiprocessing import Queue
from collections import namedtuple
from itertools import chain


NodeOutput = namedtuple("NodeOutput", "messages data")


class PipelineNode(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._params = None
        self.diagnostic_image_options = []
        self.diagnostic_image = None
        self.set_diagnostic = None

    def setup(self):
        self._params = Parametrized(params=self._process)

    @property
    def output_type_changed(self):
        return False

    @property
    def strpath(self):
        return self.separator.join([""] + [str(node.name) for node in self.path])

    def process(self, *inputs) -> NodeOutput:
        return self._process(*inputs, set_diagnostic=self.set_diagnostic, **self._params.params.values)

    def _process(self, *inputs, set_diagnostic=None, **kwargs) -> NodeOutput:
        return NodeOutput([], None)


class ImageToImageNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def output_type_changed(self):
        return any(c.output_type_changed for c in self.children)


class SourceNode(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__("source", *args, **kwargs)

    def _process(self, **kwargs):
        return [], None


class CameraSourceNode(SourceNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process(self):
        return [], self.camera_queue.get(timeout=0.001)


class ImageToDataNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.display_overlay = None
        self.display_handles = None
        self.root = SourceNode()
        self.selected_output = None
        self._output_type = None
        self.all_params = dict()
        self._param_finder = Resolver()
        self.node_dict = dict()

    def setup(self):
        """ Due to multiprocessing limitations, the setup is
        run separately from the constructor

        """
        diag_images = []
        for node in PreOrderIter(self.root):
            node.setup()
            if node._params is not None:
                self.all_params[node.strpath] = node._params
                self.node_dict[node.strpath] = node
            diag_images.extend((node.strpath+"/"+imname for imname in node.diagnostic_image_options))
        self.all_params["diagnostic_image"] = Parametrized(params=dict(image=Param("unprocessed",
                                                                                   ["unprocessed"]+diag_images)))
    @property
    def diagnostic_image(self):
        imname = self.all_params["diagnostic_image"].image
        if imname == "unprocessed":
            return None
        # if we are setting the diagnostig image to one from the nodes,
        # navigate to the node and select the proper diagnostic image
        return self.node_dict["/".join(imname.split("/")[:-1])].diagnostic_image

    def serialize_params(self):
        return {n: p.params.values for n, p in self.all_params.items()}

    def deserialize_params(self, rec_params):
        for item, vals in rec_params.items():
            self.all_params[item].params.values = vals
        imname = self.all_params["diagnostic_image"].image
        if imname != "unprocessed":
            self.node_dict["/".join(imname.split("/")[:-1])].set_diagnostic = imname.split("/")[-1]

    def recursive_run(self, node: PipelineNode, *input_data):
        output = node.process(*input_data)
        if isinstance(node, ImageToDataNode):
            return output

        child_outputs = tuple(self.recursive_run(child, output[1])
                   for child in node.children)
        if self._output_type is None or node.output_type_changed:
            self._output_type = namedtuple("o",
                                           chain.from_iterable(
                                               map(lambda x:x.data._fields,
                                                    child_outputs)))
        # collect all diagnostic messages and return a named tuple collecting
        # all the outputs

        # first element of the tuple concatenates all lists of diagnostic messages
        # second element makes a named tuple with fields from all the child named tuples
        return (output[0]+list(chain.from_iterable(map(lambda x: x.messages, child_outputs))),
                self._output_type(*(chain.from_iterable(
                    map(lambda x: x.data, child_outputs)))))

    def run(self):
        return self.recursive_run(self.root)



