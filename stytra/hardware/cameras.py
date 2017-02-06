try:
    from ximea import xiapi
except ImportError:
    pass

from multiprocessing import Process, JoinableQueue, Queue, Event
from queue import Empty
import numpy as np
from datetime import datetime
import cv2

from numba import jit


class XimeaCamera(Process):
    def __init__(self, frame_queue=None, signal=None, control_queue=None):
        super().__init__()

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
            self.q.put(arr)


class VideoFileSource(Process):
    """ A class to display videos from a file to test parts of
    stytra without a camera available

    """
    def __init__(self, frame_queue=None, signal=None, source_file=None):
        super().__init__()
        self.q = frame_queue
        self.signal = signal
        self.source_file = source_file

    def run(self):
        cap = cv2.VideoCapture(self.source_file)
        ret = True
        current_framerate = 100
        previous_time = datetime.now()
        n_fps_frames = 10
        i=0
        while ret and not self.signal.is_set():
            ret, frame = cap.read()
            self.q.put(frame[:, :, 0])
            if i == n_fps_frames - 1:
                current_time = datetime.now()
                current_framerate = n_fps_frames / (
                current_time - previous_time).total_seconds()

                # print('{:.2f} FPS'.format(current_framerate))
                previous_time = current_time
            i = (i + 1) % n_fps_frames


class FrameDispatcher(Process):
    """ A class which handles taking frames from the camera and processing them,
     as well as dispatching a subset for display

    """
    def __init__(self, frame_queue, gui_queue, finished_signal=None, output_queue=None,
                 processing_function=None, processing_parameters=None,
                 gui_framerate=30):
        super().__init__()

        self.frame_queue = frame_queue
        self.gui_queue = gui_queue
        self.finished_signal = finished_signal
        self.i = 0
        self.gui_framerate = gui_framerate
        self.processing_function = processing_function
        self.processing_parameters = processing_parameters
        self.output_queue = output_queue

    def run(self):
        previous_time = datetime.now()
        n_fps_frames = 10
        i = 0
        current_framerate = 100
        every_x = 10
        while not self.finished_signal.is_set():
            try:
                frame = self.frame_queue.get(timeout=5)
                if self.processing_function is not None:
                    self.output_queue.put(self.processing_function(frame))
                # calculate the framerate
                if i == n_fps_frames-1:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames/(current_time-previous_time).total_seconds()
                    every_x = max(int(current_framerate/self.gui_framerate), 1)
                    # print('{:.2f} FPS'.format(framerate))
                    previous_time = current_time
                i = (i+1) % n_fps_frames
                if self.i == 0:
                    self.gui_queue.put(np.swapaxes(frame,0,1))
                self.i = (self.i+1) % every_x
            except Empty:
                print('empty_queue')
                break


@jit(nopython=True)
def update_bg(bg, current, alpha):
    am = 1 - alpha
    dif = np.empty_like(current)
    for i in range(current.shape[0]):
        for j in range(current.shape[1]):
            bg[i, j] = bg[i, j] * am + current[i,j] * alpha
            if bg[i, j] > current[i,j]:
                dif[i, j] = bg[i, j] - current[i,j]
            else:
                dif[i, j] =current[i, j] -bg[i,j]
    return dif

class BgSepFrameDispatcher(FrameDispatcher):
    """ A frame dispatcher which additionaly separates the backgorund

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



    def run(self):
        previous_time = datetime.now()
        n_fps_frames = 10
        i = 0
        current_framerate = 100
        every_x = 10

        bgmodel = None
        alpha = 0.01
        bg_sub = cv2.bgsegm.createBackgroundSubtractorMOG(history=500,
                                                          nmixtures=3,
                                                          backgroundRatio=0.9)
        i_total = 0
        n_learn_background = 300
        n_every_bg = 400
        while not self.finished_signal.is_set():
            try:

                frame = self.frame_queue.get(timeout=5)
                # calculate the background
                # if bgmodel is None:
                #      bgmodel = frame
                #      mask = bgmodel
                # #     dif = frame
                # else:
                #     print('First apply')
                #     mask =bg_sub.apply(frame)
                #     print(np.sum(mask))
                # #     dif = update_bg(bgmodel, frame, alpha)

                if i_total < n_learn_background or i % n_every_bg == 0:
                    lr = 0.01
                else:
                    lr = 0

                mask = bg_sub.apply(frame, learningRate=lr)
                fishes = []
                if self.processing_function is not None and i_total>n_learn_background:
                    fishes = self.processing_function(frame, mask.copy(),
                                                      params=self.processing_parameters)
                    self.output_queue.put(fishes)
                # calculate the framerate
                if i == n_fps_frames - 1:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames / (
                        current_time - previous_time).total_seconds()
                    every_x = max(int(current_framerate / self.gui_framerate),
                                  1)
                    # print('{:.2f} FPS'.format(framerate))
                    previous_time = current_time
                i = (i + 1) % n_fps_frames
                i_total += 1
                if self.i == 0:
                    self.gui_queue.put(mask) # frame
                    print('processing FPS: {:.2f}, found {} fishes'.format(
                        current_framerate, len(fishes)))
                self.i = (self.i + 1) % every_x
            except Empty:
                print('empty_queue')
                break


if __name__=='__main__':
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
