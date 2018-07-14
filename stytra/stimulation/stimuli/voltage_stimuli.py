try:
    import nidaqmx
except:
    print("No nidamax module found")
from stytra.stimulation.stimuli import Stimulus, InterpolatedStimulus


class NIVoltageStimulus(Stimulus):
    def __init__(self, *args, dev="Dev1", chan="ao0"):
        self.dev = dev
        self.chan = chan


class SetVoltageStimulus(NIVoltageStimulus):
    def __init__(self, *args, voltage=0.0, **kwargs):
        self.voltage = voltage
        super().__init__(*args, **kwargs)

    def start(self):
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan("{}/{}".format(self.dev, self.chan))
            task.write(self.voltage)


class InterpolatedVoltageStimulus(NIVoltageStimulus, InterpolatedStimulus):
    def __init__(self, *args, **kwargs):
        self.voltage = 0
        super().__init__(*args, **kwargs)

    def update(self):
        super().update()
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan("{}/{}".format(self.dev, self.chan))
            task.write(self.voltage)

        # with nidaqmx.Task() as task:
        #     task.ai_channels.add_ai_voltage_chan("Dev1/ai1")
        #     print(task.read())
