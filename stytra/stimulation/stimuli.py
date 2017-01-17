import numpy as np

class Stimulus:
    def __init__(self, canvas_size=(100, 100), duration=0.0):
        self.elapsed = 0.0
        self.duration = duration
        self.canvas_size = canvas_size

    def state(self):
        return dict(elapsed=self.elapsed)

    def update(self):
        pass

    def get_image(self):
        pass


class Flash(Stimulus):
    def __init__(self, *args, color=(255, 255, 255), **kwargs):
        super(Flash, self).__init__(*args, **kwargs)
        self.color = color

    def get_image(self):
        return np.ones(self.canvas_size + (3,), dtype=np.uint8) * \
                np.array(self.color)[None, None, :]


class Pause(Flash):
    def __init__(self, *args, **kwargs):
        super(Pause, self).__init__(*args, color=(0,0,0), **kwargs)


class ClosedLoopStimulus(Stimulus):
    pass


class ClosedLoop1D(ClosedLoopStimulus):
    def update(self):
        pass