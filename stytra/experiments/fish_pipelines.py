from stytra.tracking.pipelines import Pipeline
from stytra.tracking.preprocessing import Prefilter
from stytra.tracking.tail import CentroidTrackingMethod
from stytra.gui.fishplots import TailStreamPlot
from stytra.gui.camera_display import TailTrackingSelection


class TailTrackingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.filter = Prefilter(parent=self.root)
        self.tailtrack = CentroidTrackingMethod(parent=self.filter)
        self.extra_widget = TailStreamPlot
        self.display_overlay = TailTrackingSelection

pipeline_dict = dict(tail=TailTrackingPipeline)
