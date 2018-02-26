from stytra import HasPyQtGraphParams

try:
    from ximea import xiapi
except ImportError:
    pass

from multiprocessing import Process, Queue, Event
from queue import Empty, Full
import numpy as np
from datetime import datetime

from stytra.collectors import HasPyQtGraphParams

import cv2

import av

class FrameProcessor(Process):
    def __init__(self, n_fps_frames=10, check_mem=True, print_framerate=False):
        """ A basic class for a process that deals with frames, provides
        framerate calculation

        :param n_fps_frames:
        :param print_framerate:
        :param check_mem:
        """
        super().__init__()

        # framerate calculation parameters
        self.n_fps_frames = n_fps_frames
        self.i_fps = 0
        self.previous_time_fps = None
        self.current_framerate = None
        self.print_framerate = print_framerate
        self.check_mem = check_mem

        self.current_time = datetime.now()
        self.starting_time = datetime.now()

    def update_framerate(self):
        if self.i_fps == self.n_fps_frames - 1:
            self.current_time = datetime.now()
            if self.previous_time_fps is not None:
                try:
                    self.current_framerate = self.n_fps_frames / (
                        self.current_time - self.previous_time_fps).total_seconds()
                except ZeroDivisionError:
                    self.current_framerate = 0
                if self.print_framerate:
                    print('FPS: ' + str(self.current_framerate))
            self.previous_time_fps = self.current_time
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames


class VideoSource(FrameProcessor):
    def __init__(self, rotation=0, max_frames_in_queue=500):
        super().__init__()
        self.rotation = rotation
        self.control_queue = Queue()
        self.frame_queue = Queue(maxsize=max_frames_in_queue)
        self.kill_signal = Event()


class XimeaCamera(VideoSource):
    def __init__(self, downsampling=2,
                 **kwargs):
        """
        Class for controlling a XimeaCamera
        :param frame_queue: queue for frame dispatching from camera
        :param control_queue: queue with parameters to feed to the camera
                              (gain, exposure, fps)
        :param downsampling: downsampling factor (default 1)
        """
        super().__init__(**kwargs)
        self.downsampling = downsampling

    def run(self):
        self.cam = xiapi.Camera()

        self.cam.open_device()
        img = xiapi.Image()
        self.cam.start_acquisition()
        self.cam.set_exposure(1000)

        # for the camera on the lightsheet which supports hardware downsampling
        # MQ013MG-ON lightsheet
        # MQ003MG-CM behaviour
        print(str(self.cam.get_device_name()))
        if self.cam.get_device_name() == b'MQ013MG-ON':
            self.cam.set_sensor_feature_selector('XI_SENSOR_FEATURE_ZEROROT_ENABLE')
            self.cam.set_sensor_feature_value(1)
            print("Python camera")
            if self.downsampling>1:
                self.cam.set_downsampling_type("XI_SKIPPING")
                self.cam.set_downsampling("XI_DWN_{}x{}".format(self.downsampling,
                                                                self.downsampling))

        self.cam.set_acq_timing_mode('XI_ACQ_TIMING_MODE_FRAME_RATE')
        while True:
            self.kill_signal.wait(0.0001)
            if self.control_queue is not None:
                try:
                    control_params = self.control_queue.get(timeout=0.0001)
                    try:
                        self.cam.set_exposure(1000)
                        if 'exposure' in control_params.keys():
                            print('setting exposure')
                            self.cam.set_exposure(int(control_params['exposure'])*1000)
                        if 'gain' in control_params.keys():
                            self.cam.set_gain(control_params['gain'])
                        if 'framerate' in control_params.keys():
                            print(self.cam.get_framerate())
                            self.cam.set_framerate(control_params['framerate'])
                    except xiapi.Xi_error:
                        print('Invalid camera settings')
                except Empty:
                    pass
            if self.kill_signal.is_set():
                break
            try:
                self.cam.get_image(img)
                # TODO check if it does anything to add np.array
                arr = np.array(img.get_image_data_numpy())
                try:
                    if self.rotation != 0:
                        arr = np.rot90(arr, self.rotation)
                    self.frame_queue.put((datetime.now(), arr))
                except Full:
                    print('frame dropped')
            except xiapi.Xi_error:
                print('Unable to acquire frame')
                pass
        self.cam.close_device()


class VideoFileSource(VideoSource):
    """ A class to display videos from a file to test parts of
    stytra without a camera available

    """
    def __init__(self, source_file=None,
                 loop=True, framerate=300,
                 **kwargs):
        super().__init__(**kwargs)
        self.source_file = source_file
        self.loop = loop

    def run(self):
        import cv2
        cap = cv2.VideoCapture(self.source_file)
        ret = True

        while ret and not self.kill_signal.is_set():
            ret, frame = cap.read()
            if ret:
                self.frame_queue.put((datetime.now(), frame[:, :, 0]))
            else:
                if self.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret = True
                else:
                    break
            self.update_framerate()
        return


class VideoWriter(FrameProcessor):
    def __init__(self, filename, input_queue, finished_signal, kbit_rate=2000):
        super().__init__()
        self.filename = filename
        self.input_queue = input_queue
        self.finished_signal = finished_signal
        self.kbit_rate = kbit_rate

    def run(self):
        out_container = av.open(self.filename, mode='w')
        out_stream = None
        video_frame = None
        while True:
            try:
                if out_stream is None:
                    current_frame = self.input_queue.get(timeout=1)
                    print("Writing to ", self.filename)
                    out_stream = out_container.add_stream('mpeg4', rate=50)
                    out_stream.width, out_stream.height = current_frame.shape
                    out_stream.pix_fmt = 'yuv420p'
                    out_stream.bit_rate = self.kbit_rate*1000
                    video_frame = av.VideoFrame(current_frame.shape[1], current_frame.shape[0], "gray")
                    video_frame.planes[0].update(current_frame)
                else:
                    video_frame.planes[0].update(self.input_queue.get(timeout=1))

                video_frame = av.VideoFrame(current_frame.shape[1], current_frame.shape[0], "gray")

                packet = out_stream.encode(video_frame)
                out_container.mux(packet)
                self.update_framerate()

            except Empty:
                if self.finished_signal.is_set():
                    print('Empty and finished')
                    break

        if out_stream is not None:
            out_container.close()


class CameraParams(HasPyQtGraphParams):
    def __init__(self):
        """
        A widget to show the camera and display the controls
        :param experiment: experiment to which this belongs
        """

        super().__init__(name='tracking_camera_params')

        standard_params_dict = dict(exposure={'value': 1000.,
                                              'type': 'float',
                                              'limits': (0.1, 50),
                                              'suffix': 'ms',
                                              'tip': 'Exposure (ms)'},
                                    gain={'value': 1.,
                                          'type': 'float',
                                          'limits': (0.1, 3),
                                          'tip': 'Camera amplification gain'})


class CameraControlParameters(HasPyQtGraphParams):
    """ General tail tracking method.
    """
    def __init__(self):
        super().__init__(name='tracking_camera_params')
        standard_params_dict = dict(exposure={'value': 1.,
                                              'type': 'float',
                                              'limits': (0.1, 50),
                                              'suffix': ' ms',
                                              'tip': 'Exposure (ms)'},
                                    framerate={'value': 150.,
                                               'type': 'float',
                                               'limits': (10, 700),
                                               'suffix': ' Hz',
                                               'tip': 'Framerate (Hz)'},
                                    gain={'value': 1.,
                                          'type': 'float',
                                          'limits': (0.1, 3),
                                          'tip': 'Camera amplification gain'})

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)

        self.exp = self.params.param('exposure')
        self.fps = self.params.param('framerate')

        self.exp.sigValueChanged.connect(self.change_fps)
        self.fps.sigValueChanged.connect(self.change_exp)

    def change_fps(self):
        pass
        # self.fps.setValue(1000 / self.exp.value(), blockSignal=self.change_exp)

    def change_exp(self):
        pass
        # self.exp.setValue(1000 / self.fps.value(), blockSignal=self.change_fps)