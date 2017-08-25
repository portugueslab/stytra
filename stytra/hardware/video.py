try:
    from ximea import xiapi
except ImportError:
    pass

from multiprocessing import Process, Queue, Event
from queue import Empty, Full
import numpy as np
from datetime import datetime, timedelta
from collections import deque

import time

import cv2

from numba import jit

import psutil

import param as pa


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
    def __init__(self, frame_queue=None, signal=None, control_queue=None, downsampling=2,
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
        if not(str(self.cam.get_device_name() == 'MQ003MG-CM')):
            downsampling_str = 'XI_DWN_' + str(self.downsampling) + 'x' + str(self.downsampling)
            self.cam.set_downsampling(downsampling_str)
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
    def __init__(self, frame_queue=None, signal=None, source_file=None, **kwargs):
        super().__init__(**kwargs)
        self.q = frame_queue
        self.signal = signal
        self.source_file = source_file

    def run(self):
        import cv2
        cap = cv2.VideoCapture(self.source_file)
        ret = True
        current_framerate = 100
        previous_time = datetime.now()

        while ret and not self.signal.is_set():
            ret, frame = cap.read()
            time.sleep(1./24)
            if ret:
                self.q.put((datetime.now(), frame[:, :, 0]))
            else:
                break
            self.update_framerate()

        return


class FrameDispatcher(FrameProcessor):
    """ A class which handles taking frames from the camera and processing them,
     as well as dispatching a subset for display

    """
    def __init__(self, frame_queue, gui_queue, finished_signal=None, output_queue=None,
                 processing_function=None, processing_parameter_queue=None,
                 gui_framerate=30, **kwargs):
        """
        :param frame_queue: queue dispatching frames from camera
        :param gui_queue: queue where to put frames to be displayed on the GUI
        :param finished_signal: signal for the end of the acquisition
        :param output_queue: queue for the output of the function applied on frames
        :param control_queue:
        :param processing_function: function to be applied to each frame
        :param processing_parameter_queue: queue for the parameters to be passed to the function
        :param gui_framerate: framerate of the display GUI
        """
        super().__init__(**kwargs)

        self.frame_queue = frame_queue
        self.gui_queue = gui_queue
        self.finished_signal = finished_signal
        self.i = 0
        self.gui_framerate = gui_framerate
        self.processing_function = processing_function
        self.processing_parameter_queue = processing_parameter_queue
        self.processing_parameters = dict()
        self.output_queue = output_queue
        self.control_queue = None

    def run(self):
        every_x = 10
        i_frame = 100
        while not self.finished_signal.is_set():
            try:
                time, frame = self.frame_queue.get()

                # acquire the processing parameters from a separate queue
                if self.processing_parameter_queue is not None:
                    try:
                        self.processing_parameters = self.processing_parameter_queue.get(timeout=0.0001)
                    except Empty:
                        pass

                if self.processing_function is not None:
                    output = self.processing_function(frame, **self.processing_parameters)
                    self.output_queue.put((datetime.now(), output))

                # calculate the frame rate
                self.update_framerate()
                # put the current frame into the GUI queue
                if self.current_framerate:
                    every_x = max(int(self.current_framerate/self.gui_framerate), 1)
                i_frame += 1
                if self.i == 0:
                    self.gui_queue.put((None, frame))
                self.i = (self.i+1) % every_x
            except Empty:
                break

        return


@jit(nopython=True)
def update_bg(bg, current, alpha):
    am = 1 - alpha
    dif = np.empty_like(current)
    for i in range(current.shape[0]):
        for j in range(current.shape[1]):
            bg[i, j] = bg[i, j] * am + current[i, j] * alpha
            if bg[i, j] > current[i, j]:
                dif[i, j] = bg[i, j] - current[i, j]
            else:
                dif[i, j] = current[i, j] - bg[i, j]
    return dif


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


class MovementDetectionParameters(pa.Parameterized):
    fish_threshold = pa.Integer(100, (0, 255))
    motion_threshold = pa.Integer(255*8)
    frame_margin = pa.Integer(10)
    n_previous_save = pa.Integer(400)
    n_next_save = pa.Integer(300)


class MovingFrameDispatcher(FrameDispatcher):
    def __init__(self, *args, output_queue,
                 framestart_queue, signal_start_rec,  **kwargs):
        super().__init__(*args, **kwargs)
        self.output_queue = output_queue
        self.framestart_queue = framestart_queue

        self.signal_start_rec = signal_start_rec
        self.mem_use = 0
        self.det_par = MovementDetectionParameters()

    def run(self):
        i = 0
        every_x = 10

        t, frame_0 = self.frame_queue.get(timeout=5)
        n_previous_compare = 3
        previous_ims = np.zeros((n_previous_compare, ) + frame_0.shape,
                                dtype=np.uint8)

        previous_images = deque()
        record_counter = 0

        i_frame = 0
        recording_state = False

        i_recorded = 0

        while not self.finished_signal.is_set():
            try:
                # process frames as they come, threshold them to roughly find the fish (e.g. eyes)
                current_time, current_frame = self.frame_queue.get()
                _, current_frame_thresh =  \
                    cv2.threshold(cv2.boxFilter(current_frame,-1,(3,3)), self.det_par.fish_threshold, 255, cv2.THRESH_BINARY)
                # compare the thresholded frame to the previous ones, if there are enough differences
                # because the fish moves, start recording to file

                difsum = 0
                n_crossed = 0
                image_crop = slice(self.det_par.frame_margin, -self.det_par.frame_margin)
                if i_frame >= n_previous_compare:
                    for j in range(n_previous_compare):
                        difsum = cv2.sumElems(cv2.absdiff(previous_ims[j, image_crop, image_crop],
                                                          current_frame_thresh[image_crop, image_crop]))[0]

                        if difsum > self.det_par.motion_threshold:
                            n_crossed += 1

                    if n_crossed == n_previous_compare:
                        record_counter = self.det_par.n_next_save

                    if record_counter > 0:
                        if self.signal_start_rec.is_set() and self.mem_use < 0.9:
                            if not recording_state:
                                while previous_images:
                                    time, im = previous_images.popleft()
                                    self.framestart_queue.put(time)
                                    self.output_queue.put(im)
                                    i_recorded += 1
                            self.output_queue.put(current_frame)
                            self.framestart_queue.put(current_time)
                            i_recorded += 1
                        recording_state = True
                        record_counter -= 1
                    else:
                        recording_state = False
                        previous_images.append((current_time, current_frame))
                        if len(previous_images) > self.det_par.n_previous_save:
                            previous_images.popleft()

                i_frame += 1

                previous_ims[i_frame % n_previous_compare, :, :] = current_frame_thresh

                # calculate the framerate
                self.update_framerate()
                if self.current_framerate is not None:
                    every_x = max(int(self.current_framerate / self.gui_framerate), 1)

                if self.i == 0:
                    self.mem_use = psutil.virtual_memory().used/psutil.virtual_memory().total
                    self.gui_queue.put((current_time, current_frame)) # frame
                    if self.current_framerate:
                        print('processing FPS: {:.2f}, difsum is: {}, n_crossed is {}'.format(
                            self.current_framerate, difsum, n_crossed))
                self.i = (self.i + 1) % every_x
            except Empty:
                print('empty_queue')
                break


if __name__ == '__main__':
    from stytra.gui.camera_display import CameraViewWidget
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication
    from stytra.metadata import MetadataCamera
    app = QApplication([])
    q_cam = Queue()
    q_gui = Queue()
    q_control = Queue()
    finished_sig = Event()
    meta = MetadataCamera()
    timer = QTimer()
    timer.setSingleShot(False)
    cam = XimeaCamera(q_cam, finished_sig, q_control)
    dispatcher = FrameDispatcher(q_cam, q_gui, finished_signal=finished_sig, print_framerate=True)

    cam.start()
    dispatcher.start()

    win = CameraViewWidget(q_gui, update_timer=timer)

    win.show()
    app.exec_()
