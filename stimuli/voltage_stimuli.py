try:
    import nidaqmx
except:
    pass
from stytra.stimulation.stimuli import Stimulus, InterpolatedStimulus, DynamicStimulus
from time import sleep

try:
    import u3
except ImportError:
    pass

# Code of this section tend to be hard to be general across setups. Please use
# the stimulus classes below as examples of interaction with a LabJAck or a NI device,
# but consider having to reimplement custom classes for your purposes.


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

        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan("Dev1/ai1")
            print(task.read())


class U3LabJackVoltageStimulus(Stimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SetU3LabJackVoltageStimulus(U3LabJackVoltageStimulus):
    name = "u3_volt_stim"

    def __init__(self, *args, voltage=0.0, **kwargs):
        self.voltage_out = voltage
        super().__init__(*args, **kwargs)

    def start(self):
        chan_value = self.device.voltageToDACBits(
            self.voltage_out, dacNumber=0, is16Bits=False
        )
        self.device.getFeedback(self.chan(chan_value))


class InterpolatedU3LabJackVoltageStimulus(
    InterpolatedStimulus, DynamicStimulus, U3LabJackVoltageStimulus
):
    def __init__(self, *args, **kwargs):
        self.voltage_out = 0
        new_dynamic_params = ["voltage_in_thermo", "voltage_in_peltier", "voltage_out"]
        super().__init__(*args, dynamic_parameters=new_dynamic_params, **kwargs)
        self.name = "u3_dyn_volt_stim"

        self.voltage_in_thermo = 0
        self.voltage_in_peltier = 0

    def update(self):
        super().update()
        device = u3.U3()
        chan = u3.DAC0_8
        chan_value = device.voltageToDACBits(
            self.voltage_out, dacNumber=0, is16Bits=False
        )
        device.getFeedback(chan(chan_value))

        device.configIO(FIOAnalog=15)
        self.voltage_in_thermo = device.getAIN(2, 32)
        self.voltage_in_peltier = device.getAIN(1, 32)


if __name__ == "__main__":
    stim = SetU3LabJackVoltageStimulus()
    stim.start()
    print("sending pulse")
