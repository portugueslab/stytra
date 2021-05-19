import mecom
from mecom import commands
from mecom import mecom as mm
from mecom.mecom import MeCom, ResponseException, WrongChecksum
from stytra.stimulation.stimuli import Stimulus, InterpolatedStimulus, DynamicStimulus
import logging
import numpy as np



# default queries from command table below
DEFAULT_QUERIES = [
    "loop status",
    "object temperature",
    "target object temperature",
    "output current",
    "output voltage"
]

# syntax
# { display_name: [parameter_id, unit], }
COMMAND_TABLE = {
    "loop status": [1200, ""],
    "object temperature": [1000, "degC"],
    "target object temperature": [1010, "degC"],
    "output current": [1020, "A"],
    "output voltage": [1021, "V"],
    "sink temperature": [1001, "degC"],
    "ramp temperature": [1011, "degC"],}


class TECStimulus(Stimulus):
    """
    Controlling TEC devices via serial.
    """

    def __init__(self, port="COM3", channel=1, queries=DEFAULT_QUERIES, *args, **kwars):
        assert channel in (1, 2)
        self.channel = channel
        self.port = port
        self.queries = queries
        super().__init__(*args)
        with MeCom("COM3") as mc:
            self.address = mc.identify()
            self.status = mc.status()
            print("connected to device: {}, status: {}".format(self.address, self.status))


class SetTECtemperatureStimulus(TECStimulus):
    name = "TEC_temperature_stimulus"

    def __init__(self, *args, temperature=25.0, **kwargs):
        self.temperature = np.float(temperature)
        super().__init__(*args, **kwargs)

    def start(self):
        """
                Set object temperature of channel to desired value.
                :param value: float
                :param channel: int
                :return:
                """
        # assertion to explicitly enter floats
        super().start()
        with MeCom("COM3") as mc:
            assert type(self.temperature) is float
            value_set = mc.set_parameter(parameter_id=3000, value=self.temperature, address=self.address,
                                            parameter_instance=self.channel)
            print("setting temperature to {}C".format(self.temperature))
            print("Succesful: {}".format(value_set))
            # get object temperature
            temp = mc.get_parameter(parameter_name="Object Temperature", address=self.address)
            print("query for object temperature, measured temperature {}C".format(temp))


class InterpolatedTECTemperatureStimulus(InterpolatedStimulus, SetTECtemperatureStimulus):

    def __init__(self, *args, **kwargs):
        # self.temperature = 25.0
        # assert type(self.temperature) is float
        dynamic_params = ["object_temperature", "output_current", "output_voltage", "device_status"]
        super().__init__(*args, dynamic_parameters=dynamic_params, **kwargs)
        self.name = "TEC"

        self.output_current = 0.0
        self.output_voltage = 0.0
        self.device_status = 0
        self.object_temperature = 25.0
        self.k = 0

    def update(self):
        super().update()
        if self.k == 0:
            with MeCom("COM3") as mc:

                value_set = mc.set_parameter(parameter_id=3000, value=np.float(self.temperature), address=self.address,
                                             parameter_instance=self.channel)
                print("setting temperature to {}C".format(self.temperature))
                print("Succesful: {}".format(value_set))

                # get all the dynamic params
                self.object_temperature = mc.get_parameter(parameter_name="Object Temperature", address=self.address)
                # print("query for object temperature, measured temperature {}C".format(temp))
                self.output_current = mc.get_parameter(parameter_name="Actual Output Current", address=self.address)
                # print("query for output current, measured current {}A".format(out_current))
                self.output_voltage = mc.get_parameter(parameter_name="Actual Output Voltage", address=self.address)
                # print("query for output voltage, measured voltage {}V".format(out_voltage))
                self.device_status = mc.get_parameter(parameter_name="Device Status", address=self.address)
                # print("query for device status".format(device_status))
        else:
            pass


if __name__ == "__main__":
    import pandas as pd
    #stim = SetTECtemperatureStimulus(temperature=23.)
    #stim.start()
    stim = InterpolatedTECTemperatureStimulus(df_param=pd.DataFrame(dict(t=[0, 5, 5, 10], temperature=[25.0, 25.0, 23.0, 23.0])))
    stim.update()
    print("sending pulse bitches")