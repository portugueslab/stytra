"Bindings for Thorlabs Benchtop Brushless Motor DLL"
import ctypes
from ctypes import *
from time import sleep
from multiprocessing import Process, Queue
from queue import Empty
import datetime
import numpy as np

from thorlabs_kinesis._utils import (
    c_dword,
    bind
)

from thorlabs_kinesis import benchtop_brushless_motor as bbm
import random
##############################################

lib = cdll.LoadLibrary("Thorlabs.MotionControl.Benchtop.BrushlessMotor.dll")
print("lib", lib)

#####################################################
BMC_StartPolling = bind(lib, "BMC_StartPolling",[c_char_p, c_short, c_int], c_bool) #true is successful
BMC_Open = bind(lib, "BMC_Open",[c_char_p, c_short], c_int) # 0 is success
BMC_StopPolling = bind(lib, "BMC_StopPolling",[c_char_p, c_short], c_bool)
BMC_Close = bind(lib, "BMC_Close",[c_char_p,c_short], c_int)
BMC_Home = bind(lib, "BMC_Home", [c_char_p, c_short], c_int)
BMC_RequestVelParams = bind(lib, "BMC_RequestVelParams", [c_char_p, c_short],c_short)
#BMC_GetVelParams = bind(lib, "BMC_GetVelParams", [c_char_p, c_short,c_int, c_int], c_short)
BMC_GetVelParams = bind(lib, "BMC_GetVelParams", [c_char_p, c_short,POINTER(c_int), POINTER(c_int)], c_short)
BMC_SetVelParams = bind(lib, "BMC_SetVelParams", [c_char_p, c_short, c_int, c_int], c_short)
BMC_GetPosition = bind(lib, "BMC_GetPosition", [c_char_p, c_short], c_int)
BMC_MoveToPosition = bind(lib, "BMC_MoveToPosition", [c_char_p, c_short, c_int], c_int)
BMC_RequestPosition = bind(lib, "BMC_RequestPosition",[c_char_p, c_short], c_int)
BMC_RequestStatusBits = bind(lib, "BMC_RequestStatusBits",[c_char_p, c_short], c_short)
BMC_GetStatusBits = bind(lib, "BMC_GetStatusBits", [c_char_p, c_short],  c_dword)
BMC_DisableChannel = bind(lib, "BMC_DisableChannel", [c_char_p,c_short], c_short)
BMC_EnableChannel= bind(lib, " BMC_EnableChannel", [c_char_p,c_short], c_short)

################################################################################
# .dll library bindings to a different file
# add examples for this library in a seperate file
# parts of the code taken from thorlabs-kinesis API found on Github. Rewrite for easier integration?

class Motor():
    """this parameters are for the Thorlabs Benchtop Brushless motor BBD203 taken
    from the XML file in the kinesis folder"""
    max_acc = 204552
    max_velo = 107374182
    encoder_counts_per_unit = 20000
    max_pos = 4400000

    def __init__(self, channel):

        """Building a List of devices and extracting the Serial Number"""

        if bbm.TLI_BuildDeviceList() == 0:
            # Extracting serial number for following code by building a buffer and filling it
            receive_buffer: c_char_p = c_char_p(bytes(" " * 250, "utf-8"))
            buffer_size = bbm.c_dword(250)
            bbm.TLI_GetDeviceListExt(receive_buffer, buffer_size)
            serial_nos = receive_buffer.value.decode("utf-8").strip().split(',')
            self.serial_nom = c_char_p(bytes(serial_nos[0], "utf-8"))
            print("Device detected with Serial number:", "{}".format(serial_nos[0]),
                     "Serial number set")

            #set some basic stuff
            self.sleeptime = 0.01
            #self.nextposition = None
            self.channel = channel

            #Needs an error statement if device could not be found

    #def set_channel(self, channel):
        #self.channel = channel
        #print ("channel set to:", channel)

    def homethatthing(self):

        """Opens the Device, Homes the stage at a set velocity and closes the Device again."""

        if BMC_Open(self.serial_nom, self.channel) == 0:
            print("Opening device and starting Polling")
            BMC_StartPolling(self.serial_nom, self.channel, 250)

            home =BMC_Home(self.serial_nom, self.channel)
            print("Homing", home)
            #self.homed = True

            #BMC_StopPolling(self.serial_nom, self.channel)
            #BMC_Close(self.serial_nom, self.channel)
            #print ("Closing device and stopping Polling")

        self.hometime = 15 #if the velocity for the homing is not set otherwise
        sleep(self.hometime)

        #Needs error statement if stage cant be homed for some reason

    #def open(self):

        #"""Opens the device and starts polling"""

        #BMC_Open(self.serial_nom,self.channel)
        #BMC_StartPolling(self.serial_nom, self.channel, 250)
        #return True

        #Error statement

    def setvelocity(self, acceleration, velocity):

        """Sets the velocity of the stage.acceleration: int, velocity: int"""

        if velocity in range(int (Motor.max_velo/2),int(Motor.max_velo+1)):
            print ("Velocity set to {}".format(velocity)) #what is the unit of that??????
            acc = c_int()  # containers
            max_vel = c_int()

            BMC_GetVelParams(self.serial_nom, self.channel, byref(acc), byref(max_vel))
            BMC_SetVelParams(self.serial_nom, self.channel, acceleration, velocity)
            #BMC_RequestVelParams(self.serial_nom, channel)
            sleep(self.sleeptime)
            #print (acc, max_vel)
            #self.setvelo = velocity #now not needed except for printing, originally for sleeptime estimate
            #self.setacc = acceleration #now not needed except for printing, originally for sleeptime estimate

            return True
        else:
            print ("Velocity set was too low (range:53687091 - 107374182). Please enter a valid velocity. ")
            return False

    def movethatthing(self, move_to):

        """Moves the stage to a specified position.channel:int, move_to: int"""

        if move_to in range(int(0), int(Motor.max_pos+1)):

            #if velocity wasnt set set it to max here or raise error

            err = BMC_MoveToPosition(self.serial_nom, self.channel, c_int(move_to))
            sleep(self.sleeptime)
            dd =BMC_RequestPosition(self.serial_nom, self.channel)
            sleep(self.sleeptime)
            pos1 = int(BMC_GetPosition(self.serial_nom, self.channel))

            print (err,dd, pos1)

            if err == 0:
                BMC_RequestPosition(self.serial_nom, self.channel)
                sleep(self.sleeptime)
                pos = int(BMC_GetPosition(self.serial_nom, self.channel))

                while not pos == move_to:
                    print("Current pos {}".format(pos) + " moving to {}".format(move_to))
                    BMC_RequestPosition(self.serial_nom, self.channel)
                    sleep(self.sleeptime)
                    pos = int(BMC_GetPosition(self.serial_nom, self.channel))
                    sleep(self.sleeptime)

                    #break statement if pos doesnt change otherwise hangs itself
        else:
            print("Invalid position provided. Range: 0 - 4400000")
            return False


    def get_position(self):
        position = int(BMC_GetPosition(self.serial_nom, self.channel))
        return position

    def diablechannel(self):
        BMC_DisableChannel(self.serial_nom, self.channel)
        print ("channel disabeled")

    def enablechannel(self):
        BMC_EnableChannel(self.serial_nom,self.channel)
        print("channel enableld")

    def close(self):

        """Closes the device and Stops polling. channel: int"""

        BMC_StopPolling(self.serial_nom, self.channel)
        BMC_Close(self.serial_nom, self.channel)

        #Error statement

    def convertunits(self):
        # this needs to be tied to the calibration file during stytra aquisition
        # so far used bouter function(from bouter.spatial import get_scale_mm)
        # conversionfactor = get_scale_mm(calibrationfilefromexperiment)*encoder_counts_per_unit
        #newunit = fishposition*conversionfactor
        #return newunit
        #needs to be continiously used
        pass

    def followfish(self):
        #needs some input from stytra to follow the fish
        pass

    def movemanualo(self):
        #maybe something to move the stage manually by keyboard
        # Alternative: disable stage lock to move it by hand until you are over the fish
        pass

    def exportlogfile(self):
        #im sure there is already something in stytra
        #f = open("logfile.txt", "w")
        #f.close()
        pass


#######################################################################################


acc = 204552
velo = 107374182
position = int(2200000 /2)

acc2 = 204552
velo2 = 107374182
position2 = int(2200000 /2)

#positions = [2200000 *2, 3620000, 400, 655000, 2200000 ]


for i in range(0, 10):
    i = random.randint(1, 4400000)
    print(i)