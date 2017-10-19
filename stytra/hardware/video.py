try:
    from ximea import xiapi
except ImportError:
    pass

from multiprocessing import Process, Queue, Event
from queue import Empty, Full
import numpy as np
from datetime import datetime

import cv2


class FrameProcessor(Process):
    def __init__(self, n_fps_frames=10, check_mem=True, framerate_queue=None, print_framerate=False):
        """ A basic class for a process that deals with frames, provides framerate calculation

        :param n_fps_frames:
        :param framerate_queue:
        :param print_framerate:
        """
        #  frame_input_queue=None, frame_output_queue=None, start_signal=None, end_signal=None
        # self.frame_input_queue = frame_input_queue
        # self.frame_output_queue = frame_input_queue
        # self.start_signal = start_signal
        # self.end_signal = end_signal
        super().__init__()

        # framerate calculation parameters
        self.n_fps_frames = n_fps_frames
        self.i_fps = 0
        self.previous_time_fps = None
        self.current_framerate = None
        self.print_framerate = print_framerate
        self.framerate_queue = framerate_queue
        self.check_mem = check_mem

        self.current_time = datetime.now()
        self.starting_time = datetime.now()

    def update_framerate(self):
        if self.i_fps == self.n_fps_frames - 1:
            self.current_time = datetime.now()
            if self.previous_time_fps is not None:
                self.current_framerate = self.n_fps_frames / (
                    self.current_time - self.previous_time_fps).total_seconds()
                if self.print_framerate:
                    print('FPS: ' + str(self.current_framerate))# int(self.current_framerate*10/500)*'#')
                if self.framerate_queue:
                    self.framerate_queue.put(self.current_framerate)
            self.previous_time_fps = self.current_time
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames


class XimeaCamera(FrameProcessor):
    def __init__(self, frame_queue=None, signal=None, control_queue=None, downsampling=4,
                 **kwargs):
        """
        Class for controlling a XimeaCamera
        :param frame_queue: queue for frame dispatching from camera
        :param signal:
        :param control_queue: queue with parameters to feed to the camera (gain, exposure, fps)
        :param downsampling: downsampling factor (default 1)
        """
        super().__init__(**kwargs)

        self.q = frame_queue
        self.control_queue = control_queue
        self.signal = signal
        self.downsampling = downsampling

    def run(self):
        self.cam = xiapi.Camera()

        self.cam.open_device()
        img = xiapi.Image()
        self.cam.start_acquisition()
        self.cam.set_exposure(1000)

        # for the camera on the lightsheet rig which supports hardware downsampling
        # MQ013MG-ON lightsheet
        # MQ003MG-CM behaviour

        if str(self.cam.get_device_name()) == 'MQ013MG-ON':
            self.cam.set_downsampling(self.downsampling)
            self.cam.set_sensor_feature_selector('XI_SENSOR_FEATURE_ZEROROT_ENABLE')
            self.cam.set_sensor_feature_value(1)

        self.cam.set_acq_timing_mode('XI_ACQ_TIMING_MODE_FRAME_RATE')
        while True:
            self.signal.wait(0.0001)
            if self.control_queue is not None:
                try:
                    control_params = self.control_queue.get(timeout=0.0001)
                    try:
                        if 'exposure' in control_params.keys():
                            self.cam.set_exposure(int(control_params['exposure']*1000))
                        if 'gain' in control_params.keys():
                            self.cam.set_gain(control_params['gain'])
                        if 'framerate' in control_params.keys():
                            print(self.cam.get_framerate())
                            self.cam.set_framerate(control_params['framerate'])
                    except xiapi.Xi_error:
                        print('Invalid camera settings')
                except Empty:
                    pass
            if self.signal.is_set():
                break
            try:
                self.cam.get_image(img)
                # TODO check if it does anything to add np.array
                arr = np.array(img.get_image_data_numpy())
                try:
                    self.q.put((datetime.now(), arr))
                except Full:
                    print('frame dropped')
            except xiapi.Xi_error:
                print('Unable to acquire frame')
                pass
        self.cam.close_device()


class VideoFileSource(FrameProcessor):
    """ A class to display videos from a file to test parts of
    stytra without a camera available

    """
    def __init__(self, frame_queue=None, signal=None, source_file=None,
                 loop=True, framerate=300,
                 **kwargs):
        super().__init__(**kwargs)
        self.q = frame_queue
        self.signal = signal
        self.loop = loop
        self.source_file = source_file

    def run(self):
        import cv2
        cap = cv2.VideoCapture(self.source_file)
        ret = True

        while ret and not self.signal.is_set():
            ret, frame = cap.read()
            if ret:
                self.q.put((datetime.now(), frame[:, :, 0]))
            else:
                if self.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret = True
                else:
                    break
            self.update_framerate()
        return


class VideoWriter(Process):
    def __init__(self, filename, input_queue, finished_signal):
        super().__init__()
        self.filename = filename
        self.input_queue = input_queue
        self.finished_signal = finished_signal

    def run(self):
        fc = cv2.VideoWriter_fourcc(*'H264')
        outfile = cv2.VideoWriter(self.filename, -1, 25, (648, 488))
        n_fps_frames = 10
        i = 0
        previous_time = datetime.now()
        while True:
            try:
                # process frames as they come, threshold them to roughly find the fish (e.g. eyes)
                current_frame = self.input_queue.get(timeout=1)
                outfile.write(current_frame)

                if (i % n_fps_frames) == 0:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames / (
                        current_time - previous_time).total_seconds()

                    print('Saving framerate: {:.2f} FPS'.format(current_framerate))
                    previous_time = current_time
                i += 1

            except Empty:
                if self.finished_signal.is_set():
                    print('Empty and finished')
                    break
        print('Finished saving, {} frames in total'.format(i))
        outfile.release()
