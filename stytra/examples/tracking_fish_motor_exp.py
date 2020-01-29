from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from stytra.stimulation import Protocol
from lightparam import Param
import datetime
from collections import namedtuple
from pathlib import Path
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli.conditional import adaptiveRadialSineStimulus, RadialSineStimulus
from stytra.stimulation.stimuli.conditional import CenteringWrapper,\
    TwoRadiusCenteringWrapper, MottiCenteringWrapper
from stytra.stimulation.stimuli.visual import FullFieldVisualStimulus


class FullFieldVisualStimulus2(FullFieldVisualStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self):
        t = datetime.datetime.now()
        # tracking, waiting
        sec_output = (True, False)
        self._experiment.send_motor_status(t, sec_output)
        super().update()



class Motti(Protocol):
    name = "motti_protocol"
    stytra_config = dict(
        camera=dict(type="spinnaker"), tracking=dict(method="fish",estimator="position"),
        recording=dict(extension="mp4", kbit_rate=3000),
        motor=dict())

    def __init__(self):
        super().__init__()

        self.period_sec = Param(10., limits=(0.2, None))
        self.flash_duration = Param(1., limits=(0., None))


    def get_stim_sequence(self):

        # This is the
        stimuli = [
            MottiCenteringWrapper(stimulus=
            FullFieldVisualStimulus2(
                duration=self.flash_duration, color=(255, 255, 255)
            ),centering_stimulus =RadialSineStimulus(period=1, velocity=5, duration=1)),
        ]

        return stimuli

        # return [Pause(duration=10)]  # protocol does not do anything


if __name__ == "__main__":
    s = Stytra(protocol=Motti())
