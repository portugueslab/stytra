"Bindings for Thorlabs Benchtop Brushless Motor DLL"
from ctypes import *
from time import sleep
from typing import (
    Any,
    List,
)


######################################################

lib = cdll.LoadLibrary("Thorlabs.MotionControl.Benchtop.BrushlessMotor.dll")
print("lib", lib)


################### code taken from Tholabs-kinesis API on github ########################
# TODO parts of the code taken from thorlabs-kinesis API found on Github credit

c_word = c_ushort
c_dword = c_ulong

def bind(lib: CDLL, func: str,
         argtypes: List[Any]=None, restype: Any=None) -> CFUNCTYPE:
    _func = getattr(lib, func, null_function)
    _func.argtypes = argtypes
    _func.restype = restype

    return _func

def null_function():
    pass

TLI_BuildDeviceList = bind(lib, "TLI_BuildDeviceList", None, c_short)
TLI_GetDeviceListExt = bind(lib, "TLI_GetDeviceListExt", [POINTER(c_char), c_dword], c_short)

#####################################################
BMC_StartPolling = bind(lib, "BMC_StartPolling",[c_char_p, c_short, c_int], c_bool) #true is successful
BMC_Open = bind(lib, "BMC_Open",[c_char_p, c_short], c_int) # 0 is success
BMC_StopPolling = bind(lib, "BMC_StopPolling",[c_char_p, c_short], c_bool)
BMC_Close = bind(lib, "BMC_Close",[c_char_p,c_short], c_int)
BMC_Home = bind(lib, "BMC_Home", [c_char_p, c_short], c_int)
BMC_RequestVelParams = bind(lib, "BMC_RequestVelParams", [c_char_p, c_short],c_short)
BMC_GetVelParams = bind(lib, "BMC_GetVelParams", [c_char_p, c_short,POINTER(c_int), POINTER(c_int)], c_short)
BMC_SetVelParams = bind(lib, "BMC_SetVelParams", [c_char_p, c_short, c_int, c_int], c_short)
BMC_GetPosition = bind(lib, "BMC_GetPosition", [c_char_p, c_short], c_int)
BMC_MoveToPosition = bind(lib, "BMC_MoveToPosition", [c_char_p, c_short, c_int], c_int)
BMC_RequestPosition = bind(lib, "BMC_RequestPosition",[c_char_p, c_short], c_int)
BMC_RequestStatusBits = bind(lib, "BMC_RequestStatusBits",[c_char_p, c_short], c_short)
BMC_GetStatusBits = bind(lib, "BMC_GetStatusBits", [c_char_p, c_short],  c_dword)
BMC_DisableChannel = bind(lib, "BMC_DisableChannel", [c_char_p,c_short], c_short)
BMC_EnableChannel= bind(lib, " BMC_EnableChannel", [c_char_p,c_short], c_short)
BMC_GetHomingVelocity = bind(lib, "BMC_GetHomingVelocity", [c_char_p,c_short], c_short)
BMC_SetHomingVelocity = bind(lib, "BMC_SetHomingVelocity", [c_char_p, c_short, c_int], c_short)
BMC_StopProfiled = bind(lib, "BMC_StopProfiled", [c_char_p, c_short], c_short)
BMC_StopImmediate = bind(lib, "BMC_StopImmediate", [c_char_p, c_short], c_short)
################################################################################

# TODO .dll library bindings to a different file ????
# TODO add examples for this library in a seperate file

class Motor():
    """this parameters are for the Thorlabs Benchtop Brushless motor BBD203 taken
    from the XML file in the kinesis folder"""
    max_acc = 204552
    max_velo = 107374182
    encoder_counts_per_unit = 20000
    max_pos = 4400000

    def __init__(self, channel):

        """Building a List of devices and extracting the Serial Number"""

        if TLI_BuildDeviceList() == 0:
            # Extracting serial number for following code by building a buffer and filling it
            receive_buffer: c_char_p = c_char_p(bytes(" " * 250, "utf-8"))
            buffer_size = c_dword(250)
            TLI_GetDeviceListExt(receive_buffer, buffer_size)
            serial_nos = receive_buffer.value.decode("utf-8").strip().split(',')
            self.serial_nom = c_char_p(bytes(serial_nos[0], "utf-8"))

            if serial_nos[0] != '':
                print("Device detected with Serial number:", "{}".format(serial_nos[0]))
                self.serial_nom_set = True
            if serial_nos[0] == '':
                print ("No serial number detected. Please check Device Status.")
                self.serial_nom_set = False

            #Set some basics
            self.sleeptime = 0.01
            self.channel = channel
            self.tolerance = 100
            self.homing_velo = int(107374182/10)

    def sethomingvelo(self):

        """Will be called by homethatthing to make homing faster."""
        BMC_GetHomingVelocity(self.serial_nom, self.channel)
        BMC_SetHomingVelocity(self.serial_nom, self.channel, self.homing_velo)

    def homethatthing(self):

        """Opens the Device, Homes the stage at a set velocity and closes the Device again."""

        if self.serial_nom_set == True:

            if BMC_Open(self.serial_nom, self.channel) == 0:
                #print("Opening device and starting Polling")
                BMC_StartPolling(self.serial_nom, self.channel, 250)

                Motor.sethomingvelo(self)

                err = BMC_Home(self.serial_nom, self.channel)
                print("Called homing with error {}".format(err))

                BMC_StopPolling(self.serial_nom, self.channel)
                BMC_Close(self.serial_nom, self.channel)
                # print ("Closing device and stopping Polling")

            self.hometime = 5
            sleep(self.hometime)

        if self.serial_nom_set == False:
            print ("Serial number not found. No Device detected to be homed.")


    def open(self):

        """Opens the device"""
        if self.serial_nom_set == True:
            BMC_Open(self.serial_nom, self.channel)

        if self.serial_nom_set == False:
            print ("Serial number not found. No Device detected to be opened.")


    def setvelocity(self, acceleration, velocity):

        """Sets the velocity of the stage.acceleration: int, velocity: int"""
        if self.serial_nom_set == True:

            # if velocity in range(int (Motor.max_velo/2),int(Motor.max_velo+1)):
            if Motor.max_velo//200 <= velocity <= Motor.max_velo:
                print ("Velocity set to {}".format(velocity)) #what is the unit of that??????
                acc = c_int()  # containers
                max_vel = c_int()

                BMC_GetVelParams(self.serial_nom, self.channel, byref(acc), byref(max_vel))
                BMC_SetVelParams(self.serial_nom, self.channel, acceleration, velocity)
                sleep(self.sleeptime)
                self.setvelo = True
            else:
                print ("Velocity set was too low (range:53687091 - 107374182). Please enter a valid velocity. ")
                self.setvelo = False

        if self.serial_nom_set == False:
            print("Serial number not found. Velocity could not be set.")



    def movethatthing(self, move_to):
            """Moves the stage to a specified position.channel:int, move_to: int"""

            if self.serial_nom_set == True:
                if  0 <=  move_to <= int(Motor.max_pos + 1):

                    BMC_RequestPosition(self.serial_nom, self.channel)
                    pos = int(BMC_GetPosition(self.serial_nom, self.channel))
                    # print("Pos before moving: {}".format(pos))

                    err = BMC_MoveToPosition(self.serial_nom, self.channel, c_int(move_to))

                    print("Called movetopos with error {}".format(err))
                    # TODO print a error meesage depending on err variable

                    if err == 0:
                        while not abs(pos - move_to) <= self.tolerance:
                            print("Current pos {}".format(pos) + " moving to {}".format(move_to))
                            BMC_RequestPosition(self.serial_nom, self.channel)
                            pos = int(BMC_GetPosition(self.serial_nom, self.channel))
                            sleep(0.04)

                        # TODO assessment if motor gets stuck???
                else:
                    print("Invalid position provided. Range: 0 - 4400000")

            if self.serial_nom_set == False:
                print("Serial number not found. No Device to be moved.")


    def get_position(self):
        BMC_RequestPosition(self.serial_nom,self.channel)
        position = int(BMC_GetPosition(self.serial_nom, self.channel))
        # print ("position:", position)
        return position

    def stopprof(self):
        err = BMC_StopProfiled(self.serial_nom, self.channel)
        print("stopping profiled", err)

    def stopimm(self):
        err = BMC_StopImmediate(self.serial_nom, self.channel)
        print ("stopping immediate", err)

    def movesimple(self, move_to):
        err = BMC_MoveToPosition(self.serial_nom, self.channel, c_int(move_to))
        #sleep(self.sleeptime)
        # print("moving", err)
        #TODO might need to add a sleeptime estimator based on velo and dist here

    def diablechannel(self):
        BMC_DisableChannel(self.serial_nom, self.channel)
        print ("channel disabeled")

    def enablechannel(self):
        BMC_EnableChannel(self.serial_nom,self.channel)
        print("channel enableld")

    def close(self):

        """Closes the device and Stops polling"""
        BMC_StopPolling(self.serial_nom, self.channel)
        BMC_Close(self.serial_nom, self.channel)
        #TODO Error statement


    def movemanualo(self):
        #maybe something to move the stage manually by keyboard
        pass

    def exportlogfile(self):
        pass

