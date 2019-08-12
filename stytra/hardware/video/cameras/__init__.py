from stytra.hardware.video.cameras.ximea import XimeaCamera
from stytra.hardware.video.cameras.avt import AvtCamera
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
from stytra.hardware.video.cameras.mikrotron import MikrotronCLCamera
from stytra.hardware.video.cameras.opencv import OpenCVCamera
from stytra.hardware.video.cameras.basler import BaslerCamera


# Update this dictionary when adding a new camera!
camera_class_dict = dict(
    ximea=XimeaCamera,
    avt=AvtCamera,
    basler=BaslerCamera,
    spinnaker=SpinnakerCamera,
    mikrotron=MikrotronCLCamera,
    opencv=OpenCVCamera,
)
