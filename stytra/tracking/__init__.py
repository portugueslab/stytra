from multiprocessing import Process
from queue import Empty
from stytra.tracking.tail import detect_tail


class TrackingProcess(Process):
    def __init__(self, image_queue, tail_queue, tracking_params):
        self.image_queue = image_queue
        self.tail_queue = tail_queue
        self.tracking_params = tracking_params

    def run(self):
        while True:
            try:
                img = self.image_queue.get()
                tail_angles = detect_tail(img, **self.tracking_params)
                self.tail_queue.put(tail_angles)
            except Empty:
                break