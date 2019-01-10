from stytra.tracking.pipelines import Pipeline
from stytra.tracking.preprocessing import Prefilter
from stytra.tracking.tail import CentroidTrackingMethod
from stytra.tracking.fish import FishTrackingMethod
from stytra.gui.fishplots import TailStreamPlot, BoutPlot
from stytra.gui.camera_display import TailTrackingSelection, CameraViewFish


class TailTrackingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.filter = Prefilter(parent=self.root)
        self.tailtrack = CentroidTrackingMethod(parent=self.filter)
        self.extra_widget = TailStreamPlot
        self.display_overlay = TailTrackingSelection


class FishTrackingPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.fishtrack = FishTrackingMethod(parent=self.root)
        self.extra_widget = BoutPlot
        self.display_overlay = CameraViewFish


pipeline_dict = dict(tail=TailTrackingPipeline,
                     fish=FishTrackingPipeline)



