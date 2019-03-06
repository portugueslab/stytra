from stytra.tracking.pipelines import Pipeline, ImageToDataNode, NodeOutput
from lightparam import Param
from collections import namedtuple


class TestNode(ImageToDataNode):
    def __init__(self, *args, **kwargs):
        self.diagnostic_image_options = ["processed"]
        super().__init__("testnode", *args, **kwargs)

    def _process(self, input, a:Param(1), set_diagnostic=None):
        if self._output_type is None:
            self._output_type = namedtuple("o", "inp par")
        else:
            self._output_type_changed = False
        if self.set_diagnostic:
            self.diagnostic_image = "img"
        return NodeOutput([], self._output_type(par=a, inp=input))


class TestPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.tp = TestNode()
        self.tp.parent = self.root


def test_a_pipeline():
    p = TestPipeline()
    p.setup()
    tt = namedtuple("o", "inp par")
    assert p.run(None) == ([], tt(None, 1))
    assert p.diagnostic_image is None
    ser = p.serialize_params()
    print(ser)
    ser["/source/testnode"]["a"] = 2
    ser["diagnostics"]["image"] = "/source/testnode/processed"
    p.deserialize_params(ser)
    assert p.run(None) == NodeOutput([], tt(None, 2))
    assert p.diagnostic_image == "img"

