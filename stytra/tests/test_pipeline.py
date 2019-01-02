from stytra.pipelines import Pipeline, ImageToImageNode, ImageToDataNode
from anytree import NodeMixin
from lightparam import Param
from collections import namedtuple



class TestNode(ImageToDataNode):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.name = "testnode"

    def _process(self, input, a:Param(1)):
        if self._ouput_type is None:
            self._ouput_type = namedtuple("o", "inp par")
        else:
            self.output_type_changed = False
        return self._ouput_type(par=a, inp=input)


class TestPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.tp = TestNode()
        self.tp.parent = self.root


def test_a_pipeline():
    p = TestPipeline()
    p.setup()
    tt = namedtuple("o", "inp par")
    assert p.run(None) == tt(None, 1)
