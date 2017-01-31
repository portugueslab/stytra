from ximea import xiapi
from multiprocessing import Process, Queue, Event


class XimeaCamera(Process):
    def __init__(self, frame_queue, signal):
        super().__init__()
        self.cap = xiapi.Camera()
        self.cam.open_device()
        self.q = frame_queue
        self.signal = signal

    def run(self):
        img = xiapi.Image()
        self.cam.start_acquisition()
        while True:
            self.signal.wait(0.0001)
            if self.signal.is_set():
                break
            self.cam.get_image(img)
            self.q.put(img.get_image_data_numpy())


if __name__=='__main__':
    cam = XimeaCamera()
