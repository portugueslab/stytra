from stytra.hardware.video.cameras.interface import Camera
import ctypes
import numpy as np


class MikrotronCLCamera(Camera):
    def __init__(self, *args, camera_id="img0", **kwargs):
        super().__init__(*args, **kwargs)
        self.cam_id = ctypes.c_char_p(bytes(camera_id, "ansi"))
        self.interface_id = ctypes.c_uint32()
        self.session_id = ctypes.c_uint32()
        self.w, self.h = ctypes.c_uint32(), ctypes.c_uint32()
        self.b_per_px = ctypes.c_uint32()
        self.img_buffer = None
        self.buffer_address = None
        self.exp_current = None
        self.framerate_current = None
        try:
            self.imaq = ctypes.windll.imaq
        except OSError:
            print("NI Vision drivers not installed")

    def open_camera(self):
        int_opened = self.imaq.imgInterfaceOpen(
            self.cam_id, ctypes.byref(self.interface_id)
        )
        session_opened = self.imaq.imgSessionOpen(
            self.interface_id, ctypes.byref(self.session_id)
        )
        self.imaq.imgSessionSerialFlush(self.session_id)

        # set 8x8 tap mode
        self._send_command(":M5")
        response = self._read_response(16)

        self.imaq.imgSessionSerialFlush(self.session_id)
        # set dimensions
        if self.roi[0] >= 0:
            self._send_command(":d{:03X}{:03X}{:03X}{:03X}".format(*self.roi))
            response = self._read_response(16)

        self.imaq.imgSessionSerialFlush(self.session_id)
        # get dimensions
        # if residual response left, clear it
        try:
            self._send_command(":d?")
            response = self._read_response(16)
            _, _, w, h = [int(x, 16) for x in response.split(" ")]
            self.imaq.imgSessionSerialFlush(self.session_id)
        except ValueError:
            return "E:Invalid message received " + response

        self.imaq.imgSessionConfigureROI(
            self.session_id,
            ctypes.c_uint32(0),
            ctypes.c_uint32(0),
            ctypes.c_uint32(h),
            ctypes.c_uint32(w),
        )
        self.imaq.imgGrabSetup(self.session_id, 1)

        self.img_buffer = np.ndarray(shape=(h, w), dtype=ctypes.c_uint8)
        self.buffer_address = self.img_buffer.ctypes.data_as(
            ctypes.POINTER(ctypes.c_long)
        )
        if self.buffer_address is None:
            return "E:Error in opening Mikrotron camera! Restart the program"
        return "I:Mikrotron camera succesfully opened, frame size is {}x{}".format(w, h)

    def _send_command(self, com):
        command = ctypes.c_char_p(bytes(com, "ansi"))
        comlen = ctypes.c_uint32(len(command.value))
        timeout = ctypes.c_uint32(500)
        return self.imaq.imgSessionSerialWrite(
            self.session_id, command, ctypes.byref(comlen), timeout
        )

    def _read_response(self, resplen=256):
        response = ctypes.create_string_buffer(256)
        comlen = ctypes.c_uint32(resplen)
        timeout = ctypes.c_uint32(500)
        self.imaq.imgSessionSerialReadBytes(
            self.session_id, response, ctypes.byref(comlen), timeout
        )
        return response.value.decode("ansi")

    def set(self, param, val):
        if param == "exposure":
            exptime = int(val * 1000)
            if exptime != self.exp_current:
                self._send_command(":t{:06X}".format(exptime))
                self._read_response()
                self.exp_current = exptime
        if param == "framerate":
            if int(val) != self.framerate_current:
                self._send_command(":q{:06X}".format(int(val)))
                self._read_response()
                self.framerate_current = int(val)
        return ""

    def read(self):
        err = self.imaq.imgGrab(self.session_id, ctypes.byref(self.buffer_address), 1)
        return self.img_buffer

    def release(self):
        self.imaq.imgSessionStopAcquisition(self.session_id)
        self.imaq.imgClose(self.session_id, True)
        self.imaq.imgClose(self.interface_id, True)
