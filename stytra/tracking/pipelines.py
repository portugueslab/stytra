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
        self._output_type = None

    def reset(self):
        pass

    def changed(self, vals):
        pass

    def setup(self):
        self._params = Parametrized(params=self._process, name="tracking+"+self.name)

    @property
    def output_type_changed(self):
        return False

    @property
    def strpath(self):
        return self.separator.join([""] + [str(node.name) for node in self.path])

    def process(self, *inputs) -> NodeOutput:
        out = self._process(*inputs, **self._params.params.values)
        try:
            assert isinstance(out, NodeOutput)
        except AssertionError:
            raise TypeError("Output type of "+self.name+" is wrong, "+str(type(out)))
        return out

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

    def _process(self, *input, **kwargs):
        return NodeOutput([], *input)


class ImageToDataNode(PipelineNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitored_headers = []
        self._params = None
        self._output_type_changed = True  # Has to be true to initialize the class

    @property
    def output_type_changed(self):
        if self._output_type_changed:
            self._output_type_changed = False
            return True
        return False

    def _process(self):
        # Node processing code

        # Output type handling
        return None


class Pipeline:
    def __init__(self):
        self.root = SourceNode()

        self.display_overlay = None
        self.extra_widget = None

        self.selected_output = None
        self._output_type = None
        self.all_params = dict()
        self._param_finder = Resolver()
        self.node_dict = dict()

    @property
    def headers_to_plot(self):
        hds = []
        for node in self.node_dict.values():
            if isinstance(node, ImageToDataNode):
                hds.extend(node.monitored_headers)
        return hds

    def setup(self, tree=None):
        """ Due to multiprocessing limitations, the setup is
        run separately from the constructor

        """
        diag_images = []
        for node in PreOrderIter(self.root):
            node.setup()
            if node._params is not None:
                self.all_params[node.strpath] = node._params
                if tree is not None:
                    tree.add(node._params)
                self.node_dict[node.strpath] = node
            diag_images.extend((node.strpath+"/"+imname for imname in node.diagnostic_image_options))
        self.all_params["diagnostics"] = Parametrized(name="tracking/diagnostics",
                                                      params=dict(image=Param("unprocessed",
                                                                              ["unprocessed"]+diag_images)),
                                                      tree=tree)
        self.all_params["reset"] = Parametrized(name="tracking/reset",
                                                params=dict(reset=Param(False,
                                                                        gui="button")),
                                                tree=tree)

    @property
    def diagnostic_image(self):
        imname = self.all_params["diagnostics"].image
        if imname == "unprocessed":
            return None
        # if we are setting the diagnostic image to one from the nodes,
        # navigate to the node and select the proper diagnostic image
        try:
            return self.node_dict["/".join(imname.split("/")[:-1])].diagnostic_image
        except KeyError:
            return None

    def serialize_changed_params(self):
        chg = {n: p.params.changed_values() for n, p in self.all_params.items()}
        for p in self.all_params.values():
            p.params.acknowledge_changes()
        return chg

    def serialize_params(self):
        return {n: p.params.values for n, p in self.all_params.items()}

    def deserialize_params(self, rec_params):
        for item, vals in rec_params.items():
            self.all_params[item].params.values = vals
            if item != "diagnostics" and item != "reset":
                self.node_dict[item].changed(vals)
        if "diagnostics" in rec_params.keys():
            imname = self.all_params["diagnostics"].image
            if imname == "unprocessed":
                for node in self.node_dict.values():
                    node.set_diagnostic = None
            else:
                try:
                    self.node_dict["/".join(imname.split("/")[:-1])].set_diagnostic \
                        = imname.split("/")[-1]
                except KeyError:  # this can happen on reloading if the pipeline is changed
                    self.all_params["diagnostics"].image = "unprocessed"
        # reset group always exists, checks if there are actual changes (the second and)
        if "reset" in rec_params.keys() and "reset" in rec_params["reset"].keys():
            for node in self.node_dict.values():
                node.reset()

    def recursive_run(self, node: PipelineNode, *input_data):
        output = node.process(*input_data)
        if isinstance(node, ImageToDataNode):
            return output

        child_outputs = tuple(self.recursive_run(child, output.data)
                   for child in node.children)
        if node._output_type is None or node.output_type_changed:
            node._output_type = namedtuple("o",
                                           chain.from_iterable(
                                               map(lambda x:x.data._fields,
                                                    child_outputs)))
        # collect all diagnostic messages and return a named tuple collecting
        # all the outputs

        # first element of the tuple concatenates all lists of diagnostic messages
        # second element makes a named tuple with fields from all the child named tuples
        return NodeOutput(output.messages+list(chain.from_iterable(map(lambda x: x.messages,
                                                             child_outputs))),
                node._output_type(*(chain.from_iterable(
                    map(lambda x: x.data, child_outputs)))))

    def run(self, input):
        return self.recursive_run(self.root, input)



