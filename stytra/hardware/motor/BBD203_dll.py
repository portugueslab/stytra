"Bindings for Thorlabs Benchtop Brushless Motor DLL"
from ctypes import *
from time import sleep
import datetime
from typing import Any, List
import os
import sys

dll_path = r'C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.Benchtop.BrushlessMotor.dll'
lib = cdll.LoadLibrary(dll_path)


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
