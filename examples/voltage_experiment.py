import pandas as pd
from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from stytra.stimulation.stimuli.voltage_stimuli import SetVoltageStimulus, InterpolatedVoltageStimulus


class VoltageProtocol(Protocol):
    name = 'voltage_protocol'

    def __init__(self):
        super().__init__()
        self.add_params(v_min=1.,
                        v_max=4.,
                        time_up=5.,
                        time_down=10.)

    def get_stim_sequence(self):
        v_list = [self.params['v_min'], self.params['v_max'], self.params['v_min']]
        t_list = [0, self.params['time_up'], self.params['time_down']]
        df = pd.DataFrame(dict(t=t_list, voltage=v_list))
        # stimuli = [Pause(duration=1),
        #            SetVoltageStimulus(duration=1, voltage=0),
        #            SetVoltageStimulus(duration=1, voltage=1),
        #            SetVoltageStimulus(duration=1, voltage=2)
        #            ]
        stimuli = [InterpolatedVoltageStimulus(df_param= df)]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocols=[VoltageProtocol])
    st.base.close()
    # import nidaqmx
    from nidaqmx.stream_readers import AnalogSingleChannelReader
    from nidaqmx.stream_writers import AnalogSingleChannelWriter

    # with nidaqmx.Task() as task:
    #     task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
    #     task.write(1.0)