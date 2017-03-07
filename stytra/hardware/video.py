try:
    from ximea import xiapi
except ImportError:
    pass

#import multiprocessing
from multiprocessing import Process, Queue, Event
from queue import Empty
import numpy as np
from datetime import datetime, timedelta
from collections import deque

from numba import jit


class FrameProcessor(Process):
    def __init__(self, n_fps_frames=10, framerate_queue=None, print_framerate=False):
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

        self.current_time = datetime.now()
        self.starting_time = datetime.now()

    def update_framerate(self):
        if self.i_fps == self.n_fps_frames - 1:
            self.current_time = datetime.now()
            if self.previous_time_fps is not None:
                self.current_framerate = self.n_fps_frames / (
                    self.current_time - self.previous_time_fps).total_seconds()
                if self.print_framerate:
                    print('{:.2f} FPS'.format(self.current_framerate))
                if self.framerate_queue:
                    self.framerate_queue.put(self.current_framerate)
            self.previous_time_fps = self.current_time
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames


class XimeaCamera(FrameProcessor):
    def __init__(self, frame_queue=None, signal=None, control_queue=None, **kwargs):
        super().__init__(**kwargs)

        self.q = frame_queue
        self.control_queue = control_queue
        self.signal = signal

    def run(self):
        self.cam = xiapi.Camera()
        self.cam.open_device()
        img = xiapi.Image()
        self.cam.start_acquisition()
        self.cam.set_exposure(1000)
        while True:
            self.signal.wait(0.0001)
            if self.control_queue is not None:
                try:
                    control_params = self.control_queue.get(timeout=0.0001)
                    if 'exposure' in control_params.keys():
                        self.cam.set_exposure(int(control_params['exposure']*1000))
                    if 'gain' in control_params.keys():
                        self.cam.set_gain(control_params['gain'])
                except Empty:
                    pass
            if self.signal.is_set():
                break
            self.cam.get_image(img)
            # TODO check if it does anything to add np.array
            arr = np.array(img.get_image_data_numpy())
            self.q.put((datetime.now(), arr))
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
            #print('Read a frame')
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
                if self.current_framerate:
                    every_x = max(int(self.current_framerate/self.gui_framerate), 1)
                #print(self.current_framerate)
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

                if i == n_fps_frames - 1:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames / (
                        current_time - previous_time).total_seconds()

                    print('Saving framerate: {:.2f} FPS'.format(current_framerate))
                    previous_time = current_time
                i = (i + 1) % n_fps_frames

            except Empty:
                if self.finished_signal.is_set():
                    print('Empty and finished')
                    break
        print('Finished saving!')
        outfile.release()


class MovingFrameDispatcher(FrameDispatcher):
    def __init__(self, *args, output_queue,
                 framestart_queue, signal_start_rec, diag_queue, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_queue = output_queue
        self.framestart_queue = framestart_queue
        self.diag_queue = diag_queue
        self.signal_start_rec = signal_start_rec

    def run(self):
        previous_time = datetime.now()
        n_fps_frames = 10
        i = 0
        current_framerate = 100
        every_x = 10

        t, frame_0 = self.frame_queue.get(timeout=5)
        n_previous_compare = 3
        i_previous = 0
        previous_ims = np.zeros((n_previous_compare, ) + frame_0.shape,
                                dtype=np.uint8)
        fish_threshold = 40
        motion_threshold = 400
        frame_margin = 10

        previous_images = deque()
        n_previous_save = 300
        n_next_save = 200
        record_counter = 0

        i_frame = 0
        recording_state = False

        i_recorded = 0

        while not self.finished_signal.is_set():
            try:
                # process frames as they come, threshold them to roughly find the fish (e.g. eyes)
                current_time, current_frame = self.frame_queue.get()
                _, current_frame_thresh =  \
                    cv2.threshold(current_frame, fish_threshold, 255, cv2.THRESH_BINARY)
                # compare the thresholded frame to the previous ones, if there are enough differences
                # because the fish moves, start recording to file

                difsum = 0
                n_crossed = 0
                if i_frame >= n_previous_compare:
                    for j in range(n_previous_compare):
                        difsum = cv2.sumElems(cv2.absdiff(previous_ims[j, frame_margin:- frame_margin,
                                                          frame_margin:- frame_margin],
                                                          current_frame_thresh[frame_margin:- frame_margin,
                                                          frame_margin:- frame_margin]))[0]
                        # self.diag_queue.put(difsum)
                        if difsum > motion_threshold:
                            n_crossed += 1
                    if n_crossed == n_previous_compare:
                        record_counter = n_next_save

                    if record_counter > 0:
                        if self.signal_start_rec.is_set():
                            if not recording_state:
                                frame_start = i_recorded
                                i_previous = 0
                                while previous_images:
                                    time, im = previous_images.pop()
                                    self.framestart_queue.put(time)
                                    self.output_queue.put(im)
                                    i_recorded += 1
                                    i_previous += 1
                            self.output_queue.put(current_frame)
                            self.framestart_queue.put(current_time)
                            i_recorded += 1
                        recording_state = True
                        record_counter -= 1
                    else:
                        recording_state = False

                i_frame += 1
                previous_images.append((current_time, current_frame))
                previous_ims[i_frame % n_previous_compare, :, :] = current_frame_thresh
                if len(previous_images) > n_previous_save:
                    previous_images.popleft()

                # calculate the framerate
                if i == n_fps_frames - 1:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames / (
                        current_time - previous_time).total_seconds()
                    every_x = max(int(current_framerate / self.gui_framerate), 1)
                    # print('{:.2f} FPS'.format(framerate))
                    previous_time = current_time
                i = (i + 1) % n_fps_frames

                if self.i == 0:
                    self.gui_queue.put(current_frame)  # frame
                    print('processing FPS: {:.2f}, difsum is: {}, n_crossed is {}'.format(
                        current_framerate, difsum, n_crossed))
                self.i = (self.i + 1) % every_x
            except Empty:
                print('empty_queue')
                break


if __name__ == '__main__':
    from stytra.gui.camera_display import CameraDisplayWidget
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    q_cam = Queue()
    q_gui = Queue()
    q_control = Queue()
    finished_sig = Event()
    cam = XimeaCamera(q_cam, finished_sig, q_control)
    dispatcher = FrameDispatcher(q_cam, q_gui)

    cam.start()
    dispatcher.start()

    win = CameraDisplayWidget(q_gui, q_control)

    win.show()
    app.exec_()
