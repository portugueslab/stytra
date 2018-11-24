import pandas as pd
from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from stytra.stimulation.stimuli.voltage_stimuli import (
    SetVoltageStimulus,
    InterpolatedVoltageStimulus,
)


class VoltageProtocol(Protocol):
    name = "voltage_protocol"

    def __init__(self):
        super().__init__()
        self.add_params(v_min=1., v_max=4., time_up=5., time_down=10.)

    def get_stim_sequence(self):
        v_list = [self.params["v_min"], self.params["v_max"], self.params["v_min"]]
        t_list = [0, self.params["time_up"], self.params["time_down"]]
        df = pd.DataFrame(dict(t=t_list, voltage=v_list))

        stimuli = [InterpolatedVoltageStimulus(df_param=df)]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=VoltageProtocol())
