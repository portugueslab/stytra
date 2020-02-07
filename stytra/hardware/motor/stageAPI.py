"Bindings for Thorlabs Benchtop Brushless Motor DLL"
from ctypes import *
from time import sleep
import datetime
from typing import Any, List


######################################################

lib = cdll.LoadLibrary("Thorlabs.MotionControl.Benchtop.BrushlessMotor.dll")
print("lib", lib)


################### code taken from Tholabs-kinesis API on github ########################
# TODO parts of the code taken from thorlabs-kinesis API found on Github credit

c_word = c_ushort
c_dword = c_ulong


def bind(
    lib: CDLL, func: str, argtypes: List[Any] = None, restype: Any = None
) -> CFUNCTYPE:
    _func = getattr(lib, func, null_function)
    _func.argtypes = argtypes
    _func.restype = restype

    return _func


def null_function():
    pass


class MOT_BrushlessPositionLoopParameters(Structure):
    _fields_ = [
        ("proportionalGain", c_word),
        ("integralGain", c_word),
        ("integralLimit", c_dword),
        ("differentialGain", c_word),
        ("derivativeRecalculationTime", c_word),
        ("factorForOutput", c_word),
        ("velocityFeedForward", c_word),
        ("accelerationFeedForward", c_word),
        ("positionErrorLimit", c_dword),
        ("notUsed", c_word),
        ("lastNotUsed", c_word),
    ]

# enum MOT_JogModes
MOT_JogModeUndefined = c_short(0x00)
MOT_Continuous = c_short(0x01)
MOT_SingleStep = c_short(0x02)
MOT_JogModes = c_short

# enum MOT_StopModes
MOT_StopModeUndefined = c_short(0x00)
MOT_Immediate = c_short(0x01)
MOT_Profiled = c_short(0x02)
MOT_StopModes = c_short

# enum MOT_TravelDirection
MOT_TravelDirectionUndefined = c_short(0x00)
MOT_Forwards = c_short(0x01)
MOT_Reverse = c_short(0x02)
MOT_TravelDirection = c_short

# enum MOT_HomeLimitSwitchDirection
MOT_LimitSwitchDirectionUndefined = c_short(0x00)
MOT_ReverseLimitSwitch = c_short(0x01)
MOT_ForwardLimitSwitch = c_short(0x04)
MOT_HomeLimitSwitchDirection = c_short


class MOT_HomingParameters(Structure):
    _fields_ = [("direction", MOT_TravelDirection),
                ("limitSwitch", MOT_HomeLimitSwitchDirection),
                ("velocity", c_uint),
                ("offsetDistance", c_uint)]



TLI_BuildDeviceList = bind(lib, "TLI_BuildDeviceList", None, c_short)
TLI_GetDeviceListExt = bind(
    lib, "TLI_GetDeviceListExt", [POINTER(c_char), c_dword], c_short
)
##################
BMC_GetHomingParamsBlock = bind(lib, "BMC_GetHomingParamsBlock", [POINTER(c_char), c_short, POINTER(MOT_HomingParameters)], c_short)
BMC_SetHomingParamsBlock = bind(lib, "BMC_SetHomingParamsBlock", [POINTER(c_char), c_short, POINTER(MOT_HomingParameters)], c_short)


class MOT_VelocityParameters(Structure):
    _fields_ = [("minVelocity", c_int),
                ("acceleration", c_int),
                ("maxVelocity", c_int)]


class MOT_JogParameters(Structure):
    _fields_ = [("mode", MOT_JogModes),
                ("stepSize", c_uint),
                ("velParams", MOT_VelocityParameters),
                ("stopMode", MOT_StopModes)]


BMC_GetJogParamsBlock = bind(lib, "BMC_GetJogParamsBlock", [POINTER(c_char), POINTER(MOT_JogParameters)], c_short)
BMC_GetJogMode = bind(lib, "BMC_GetJogMode", [POINTER(c_char), c_short, POINTER(MOT_JogModes), POINTER(MOT_StopModes)], c_short)
BMC_SetJogMode = bind(lib, "BMC_SetJogMode", [POINTER(c_char), c_short, MOT_JogModes, MOT_StopModes], c_short)
BMC_GetJogStepSize = bind(lib, "BMC_GetJogStepSize", [POINTER(c_char), c_short], c_uint)
BMC_SetJogStepSize = bind(lib, "BMC_SetJogStepSize", [POINTER(c_char), c_short, c_uint], c_short)
BMC_GetJogVelParams = bind(lib, "BMC_GetJogVelParams", [POINTER(c_char), c_short, POINTER(c_int), POINTER(c_int)], c_short)
BMC_SetJogVelParams = bind(lib, "BMC_SetJogVelParams", [POINTER(c_char), c_short, c_int, c_int], c_short)
BMC_MoveJog = bind(lib, "BMC_MoveJog", [POINTER(c_char), c_short, MOT_TravelDirection], c_short)


BMC_RequestMoveAbsolutePosition = bind(lib, "BMC_RequestMoveAbsolutePosition", [POINTER(c_char), c_short], c_short)
BMC_GetMoveAbsolutePosition = bind(lib, "BMC_GetMoveAbsolutePosition", [POINTER(c_char), c_short], c_int)
BMC_MoveAbsolute = bind(lib, "BMC_MoveAbsolute", [POINTER(c_char), c_short], c_short)
BMC_SetMoveRelativeDistance = bind(lib, "BMC_SetMoveRelativeDistance", [POINTER(c_char), c_short, c_int], c_short)
BMC_MoveRelative = bind(lib, "BMC_MoveRelative", [POINTER(c_char), c_int], c_short)
BMC_SetMoveAbsolutePosition = bind(lib, "BMC_SetMoveAbsolutePosition", [POINTER(c_char), c_short, c_int], c_short)

#####################################################
BMC_StartPolling = bind(
    lib, "BMC_StartPolling", [c_char_p, c_short, c_int], c_bool
)  # true is successful
BMC_Open = bind(lib, "BMC_Open", [c_char_p, c_short], c_int)  # 0 is success
BMC_StopPolling = bind(lib, "BMC_StopPolling", [c_char_p, c_short], c_bool)
BMC_Close = bind(lib, "BMC_Close", [c_char_p, c_short], c_int)
BMC_Home = bind(lib, "BMC_Home", [c_char_p, c_short], c_int)
BMC_RequestVelParams = bind(lib, "BMC_RequestVelParams", [c_char_p, c_short], c_short)
BMC_GetVelParams = bind(
    lib,
    "BMC_GetVelParams",
    [c_char_p, c_short, POINTER(c_int), POINTER(c_int)],
    c_short,
)
BMC_SetVelParams = bind(
    lib, "BMC_SetVelParams", [c_char_p, c_short, c_int, c_int], c_short
)
BMC_GetPosition = bind(lib, "BMC_GetPosition", [c_char_p, c_short], c_int)
BMC_MoveToPosition = bind(lib, "BMC_MoveToPosition", [c_char_p, c_short, c_int], c_int)
BMC_RequestPosition = bind(lib, "BMC_RequestPosition", [c_char_p, c_short], c_int)
BMC_RequestStatusBits = bind(lib, "BMC_RequestStatusBits", [c_char_p, c_short], c_short)
BMC_GetStatusBits = bind(lib, "BMC_GetStatusBits", [c_char_p, c_short], c_dword)
BMC_DisableChannel = bind(lib, "BMC_DisableChannel", [c_char_p, c_short], c_short)
BMC_EnableChannel = bind(lib, "BMC_EnableChannel", [c_char_p, c_short], c_short)
BMC_GetHomingVelocity = bind(lib, "BMC_GetHomingVelocity", [c_char_p, c_short], c_short)
BMC_SetHomingVelocity = bind(
    lib, "BMC_SetHomingVelocity", [c_char_p, c_short, c_int], c_short
)
BMC_StopProfiled = bind(lib, "BMC_StopProfiled", [c_char_p, c_short], c_short)
BMC_StopImmediate = bind(lib, "BMC_StopImmediate", [c_char_p, c_short], c_short)
BMC_GetPosLoopParams = bind(
    lib,
    "BMC_GetPosLoopParams",
    [c_char_p, c_short, POINTER(MOT_BrushlessPositionLoopParameters)],
    c_short,
)
BMC_SetPosLoopParams = bind(
    lib,
    "BMC_SetPosLoopParams",
    [c_char_p, c_short, POINTER(MOT_BrushlessPositionLoopParameters)],
    c_short,
)

################################################################################

# TODO .dll library bindings to a different file ????
# TODO add examples for this library in a seperate file


class Motor:
    """this parameters are for the Thorlabs Benchtop Brushless motor BBD203 taken
    from the XML file in the kinesis folder"""

    max_acc = 204552
    max_velo = 107374182
    encoder_counts_per_unit = 20000
    max_pos = 4400000

    def __init__(self, channel, scale):

        """Building a List of devices and extracting the Serial Number"""

        if TLI_BuildDeviceList() == 0:
            # Extracting serial number for following code by building a buffer and filling it
            receive_buffer: c_char_p = c_char_p(bytes(" " * 250, "utf-8"))
            buffer_size = c_dword(250)
            TLI_GetDeviceListExt(receive_buffer, buffer_size)
            serial_nos = receive_buffer.value.decode("utf-8").strip().split(",")
            self.serial_nom = c_char_p(bytes(serial_nos[0], "utf-8"))

            if serial_nos[0] != "":
                print("Device detected with Serial number:", "{}".format(serial_nos[0]))
                self.serial_nom_set = True
            if serial_nos[0] == "":
                print("No serial number detected. Please check Device Status.")
                self.serial_nom_set = False

            # Set some basics
            self.sleeptime = 0.01
            self.channel = channel
            self.tolerance = 100
            self.homing_velo = int(107374182 / 18)
            self.scale = scale

    def sethomingvelo(self):

        """Will be called by homethatthing to make homing faster."""
        BMC_GetHomingVelocity(self.serial_nom, self.channel)
        BMC_SetHomingVelocity(self.serial_nom, self.channel, self.homing_velo)

    def homethatthing(self):

        """Opens the Device, Homes the stage at a set velocity and closes the Device again."""

        if self.serial_nom_set == True:

            # if BMC_Open(self.serial_nom, self.channel) == 0:
                # print("Opening device and starting Polling")
            BMC_StartPolling(self.serial_nom, self.channel, 250)

            Motor.sethomingvelo(self)

            err = BMC_Home(self.serial_nom, self.channel)
            print("Called homing with error {}".format(err))

                # BMC_StopPolling(self.serial_nom, self.channel)
                # BMC_Close(self.serial_nom, self.channel)
                # print ("Closing device and stopping Polling")

            self.hometime = 5
            sleep(self.hometime)

        if self.serial_nom_set == False:
            print("Serial number not found. No Device detected to be homed.")

    def home(self):
        err = BMC_Home(self.serial_nom, self.channel)
        print("Called homing with error {}".format(err))

    def open(self):

        """Opens the device"""
        if self.serial_nom_set == True:
            BMC_Open(self.serial_nom, self.channel)

        if self.serial_nom_set == False:
            print("Serial number not found. No Device detected to be opened.")

    def setvelocity(self, acceleration, velocity):

        """Sets the velocity of the stage.acceleration: int, velocity: int"""
        if self.serial_nom_set == True:

            # if velocity in range(int (Motor.max_velo/2),int(Motor.max_velo+1)):
            if Motor.max_velo // 200 <= velocity <= Motor.max_velo:
                print(
                    "Velocity set to {}".format(velocity)
                )  # what is the unit of that??????
                acc = c_int()  # containers
                max_vel = c_int()

                BMC_GetVelParams(
                    self.serial_nom, self.channel, byref(acc), byref(max_vel)
                )
                BMC_SetVelParams(self.serial_nom, self.channel, acceleration, velocity)
                sleep(self.sleeptime)
                self.setvelo = True
            else:
                print(
                    "Velocity set was too low (range:53687091 - 107374182). Please enter a valid velocity. "
                )
                self.setvelo = False

        if self.serial_nom_set == False:
            print("Serial number not found. Velocity could not be set.")

    def movethatthing(self, move_to):
        """Moves the stage to a specified position.channel:int, move_to: int"""

        if self.serial_nom_set == True:
            if 0 <= move_to <= int(Motor.max_pos + 1):

                BMC_RequestPosition(self.serial_nom, self.channel)
                pos = int(BMC_GetPosition(self.serial_nom, self.channel))
                # print("Pos before moving: {}".format(pos))

                err = BMC_MoveToPosition(self.serial_nom, self.channel, c_int(move_to))

                # print("Called movetopos with error {}".format(err))
                # TODO print a error meesage depending on err variable

                if err == 0:
                    while not abs(pos - move_to) <= self.tolerance:
                        print(
                            "Current pos {}".format(pos)
                            + " moving to {}".format(move_to)
                        )
                        BMC_RequestPosition(self.serial_nom, self.channel)
                        pos = int(BMC_GetPosition(self.serial_nom, self.channel))
                        sleep(0.04)

                    # TODO assessment if motor gets stuck???
            else:
                print("Invalid position provided. Range: 0 - 4400000")

        if self.serial_nom_set == False:
            print("Serial number not found. No Device to be moved.")

    def get_position(self):
        BMC_RequestPosition(self.serial_nom, self.channel)
        position = int(BMC_GetPosition(self.serial_nom, self.channel))
        # print ("position:", position)
        return position

    def get_homing_params(self):
        homing_info = MOT_HomingParameters()  # container
        err = BMC_GetHomingParamsBlock(self.serial_nom, self.channel, byref(homing_info))
        if err == 0:
            print("direction: ", homing_info.direction)
            print("limitSwitch: ", homing_info.limitSwitch)
            print("velocity: ", homing_info.velocity)
            print("offsetDistance: ", homing_info.offsetDistance)
        else:
            print("Error getting Homing Info Block. Error Code:{}".format(err))

    def set_homing_params(
        self, direction=int(), lim_switch=int(), velocity=int(), offset=int()):
        homing_info = MOT_HomingParameters()  # container
        homing_info.direction = direction
        homing_info.limitSwitch = lim_switch
        homing_info.velocity = velocity
        homing_info.offsetDistance = offset
        # print("direction: ", homing_info.direction)
        # print("limitSwitch: ", homing_info.limitSwitch)
        # print("velocity: ", homing_info.velocity)
        # print("offsetDistance: ", homing_info.offsetDistance)

        BMC_SetHomingParamsBlock(self.serial_nom, self.channel, byref(homing_info))
        print("New homing parameters set.")

    def set_homing_reverse(self, direction):
        self.get_homing_params()
        self.set_homing_params(direction=direction, lim_switch=1, velocity=5965232, offset=60000)
        print ("homing in reverse direction")


    def get_pos_loop_params(self):
        posloop_info = MOT_BrushlessPositionLoopParameters()  # container
        err = BMC_GetPosLoopParams(self.serial_nom, self.channel, byref(posloop_info))
        if err == 0:
            print("proportionalGain: ", posloop_info.proportionalGain)
            print("integralGain: ", posloop_info.integralGain)
            print("integralLimit: ", posloop_info.integralLimit)
            print("differentialGain: ", posloop_info.differentialGain)
            print(
                "derivativeRecalculationTime: ",
                posloop_info.derivativeRecalculationTime,
            )
            print("factorForOutput: ", posloop_info.factorForOutput)
            print("velocityFeedForward: ", posloop_info.velocityFeedForward)
            print("accelerationFeedForward: ", posloop_info.accelerationFeedForward)
            print("positionErrorLimit: ", posloop_info.positionErrorLimit)
            print("notUsed: ", posloop_info.notUsed)
            print("lastNotUsed: ", posloop_info.lastNotUsed)
        else:
            print("Error getting position loop Info Block. Error Code:{}".format(err))

    def set_pos_loop_params(
        self, pgain=int(), intgain=int(), intlim=int(), diffgain=int(), derivcalc=int()
    ):
        posloop_info = MOT_BrushlessPositionLoopParameters()  # container
        posloop_info.proportionalGain = pgain
        posloop_info.integralGain = intgain
        posloop_info.integralLimit = intlim
        posloop_info.differentialGain = diffgain
        posloop_info.derivativeRecalculationTime = derivcalc

        BMC_SetPosLoopParams(self.serial_nom, self.channel, byref(posloop_info))
        print("New loop parameters set.")

    def stopprof(self):
        err = BMC_StopProfiled(self.serial_nom, self.channel)
        print("stopping profiled", err)

    def stopimm(self):
        err = BMC_StopImmediate(self.serial_nom, self.channel)
        print("stopping immediate", err)

    def movesimple(self, position=int()):
        BMC_MoveToPosition(self.serial_nom, self.channel, c_int(position))

    def move_relative(self, distance):
        pos = self.get_position()
        to_move = distance * self.scale
        dotpos = int(round(pos + to_move))
        print("moving the motor to", int(round(pos + to_move)))
        self.movesimple(int(round(pos + to_move)))
        return dotpos

    def move_relative_without_move(self, distance):
        pos = self.get_position()
        to_move = distance * self.scale
        dotpos = int(round(pos + to_move))
        dot_c = int(dotpos - 2200000)
        return dotpos, dot_c


    def abs_pos(self, pos):
        BMC_SetMoveAbsolutePosition(self.serial_nom, self.channel, pos)

    def move_absolute(self):
        BMC_MoveAbsolute(self.serial_nom, self.channel)

    def move_rel(self, distance):
        BMC_MoveRelative(self.serial_nom, self.channel, distance)

    def movejog(self, direction):
        BMC_MoveJog(self.serial_nom, self.channel, direction)

    def jogging(self, number):
        stepsize = 20000
        jogs = int(abs(number)/stepsize) #todo rounding does over/undershoot

        print ("number input as distance", number, stepsize)
        flag = True
        direction = self.assess_direction(number)
        print("jogs taken {} in direction {}".format(jogs, direction))

        for i in range(jogs +1):
            while flag == True:
                BMC_MoveJog(self.serial_nom, self.channel, direction)
                flag = False
                print ("jogging", i)
            flag = True



    def get_jogstepsize(self):
        number = BMC_GetJogStepSize(self.serial_nom, self.channel)
        return number

    def set_jogstepsize(self, stepsize):
        BMC_SetJogStepSize(self.serial_nom, self.channel, stepsize)

    def get_jogmode(self):
        err = BMC_GetJogMode(self.serial_nom, self.channel)
        print (err)

    def set_jogmode(self, mode, stopmode):
        """ mode: 1 = continous, 2 = jog step,
            stopmode: 1 = immediate, 2 = profiled"""
        BMC_SetJogMode(self.serial_nom, self.channel, mode, stopmode)

    #Todo this function doesnt work

    # def get_jog_params(self):
    #     params = MOT_JogParameters()
    #     BMC_GetJogParamsBlock(self.serial_nom, self.channel, byref(params))
    #
    #     if err == 0:
    #         print("mode: ", params.mode)
    #         print("stepSize: ", params.stepSize)
    #         print("velParams: ", params.velParams)
    #         print("stopMode: ", params.stopMode)


    def diablechannel(self):
        BMC_DisableChannel(self.serial_nom, self.channel)
        print("channel disabeled")

    def enablechannel(self):
        BMC_EnableChannel(self.serial_nom, self.channel)
        print("channel enableld")

    def close(self):
        """Closes the device and Stops polling"""
        BMC_StopPolling(self.serial_nom, self.channel)
        BMC_Close(self.serial_nom, self.channel)

    def movemanualo(self):
        #TODO maybe something to move the stage manually by keyboard
        pass

    def motorminimal(self ,acceleration=int(204552 / 10),
                     velocity =int(107374182 / 10)):
        """Mini script to run before motor can be used"""
        self.homethatthing()
        self.setvelocity(acceleration, velocity)


    def calibrator_movement(self):
        pos = self.get_position()
        self.movethatthing(pos + 20000)  # 20000 motor units is 1 mm
        sleep(0.5)

    def assess_direction(self, number):
        """direction 1 - forward, direction 2- reverse"""
        if number > 0:
            direction = 1
        else:
            direction = 2
        return int(direction)


if __name__ == "__main__":
    mottione = Motor(1, scale=0)
    mottitwo = Motor(2, scale=0)
    mottione.open()
    mottitwo.open()

    mottitwo.close()
    mottione.close()

# self.motor_x.jogging(int(last_position.f0_x))
# self.motor_y.jogging(int(last_position.f0_y))

# self.motor_x.move_rel(int(last_position.f0_x))
# self.motor_y.move_rel(int(last_position.f0_y))

# self.motor_x.movesimple(int(pos_x + distance_x))
# self.motor_y.movesimple(int(pos_y + distance_y))