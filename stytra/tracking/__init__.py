from multiprocessing import Process
from queue import Empty
import cv2
from datetime import datetime
from stytra.tracking.diagnostics import draw_found_fish
from stytra.utilities import HasPyQtGraphParams


class ParametrizedImageproc():
    def process(self, im, state=None, **kwargs):
        return im

    def reset_state(self):
        pass