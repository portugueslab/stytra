import nidaqmx
from nidaqmx.stream_readers import AnalogSingleChannelReader
from nidaqmx.stream_writers import AnalogSingleChannelWriter
from stytra.stimulation.stimuli import Stimulus, InterpolatedStimulus


class SetVoltageStimulus(Stimulus):
    def __init__(self, *args, voltage=0.0, **kwargs):
        self.voltage = voltage
        super().__init__(*args, **kwargs)

    def start(self):
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
            task.write(self.voltage)


class InterpolatedVoltageStimulus(InterpolatedStimulus):
    def __init__(self, *args, **kwargs):
        self.voltage = 0
        super().__init__(*args, **kwargs)

    def update(self):
        super().update()
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
            task.write(self.voltage)

        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan("Dev1/ai1")
            print(task.read())

    def make_window(self):
        self.window_main = TrackingExperimentWindow(experiment=self,
                                                    tail=tail,
                                                    eyes=eyes)

        # add streams
        self.window_main.stream_plot.add_stream(self.data_acc)

        if self.estimator is not None:
            self.window_main.stream_plot.add_stream(self.estimator.log)

        self.window_main.show()





