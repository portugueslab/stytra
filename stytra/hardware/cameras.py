from ximea import xiapi
from multiprocessing import Process, JoinableQueue, Queue, Event
from queue import Empty
import numpy as np
from datetime import datetime

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
            arr = np.array(img.get_image_data_numpy())
            self.q.put(arr)

class FrameDispatcher(Process):
    def __init__(self, frame_queue, gui_queue, every_x=20):
        super().__init__()

        self.frame_queue = frame_queue
        self.gui_queue = gui_queue
        self.i = 0
        self.every_x = every_x

    def run(self):
        previous_time = datetime.now()
        n_fps_frames = 10
        i = 0
        while True:
            try:
                frame = self.frame_queue.get(timeout=5)

                # calculate the framerate
                if i == n_fps_frames-1:
                    current_time = datetime.now()
                    framerate = n_fps_frames/(current_time-previous_time).total_seconds()
                    print('{:.2f} FPS'.format(framerate))
                    previous_time = current_time
                i = (i+1) % n_fps_frames
                if self.i == 0:
                    self.gui_queue.put(np.swapaxes(frame,0,1))
                self.i = (self.i+1) % self.every_x
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
