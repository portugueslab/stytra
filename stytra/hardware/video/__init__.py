from arrayqueues.processes import FrameProcessor
from arrayqueues.shared_arrays import TimestampedArrayQueue
from multiprocessing import Queue, Event


class VideoSource(FrameProcessor):
    """ Abstract class for a process that generates frames, being it a camera
    or a file source.
    """
    def __init__(self, rotation=0, max_mbytes_queue=100):
        """ Initialize the source
        :param rotation:
        :param max_mbytes_queue:
        """
        super().__init__()
        self.rotation = rotation
        self.control_queue = Queue()
        self.frame_queue = TimestampedArrayQueue(max_mbytes=max_mbytes_queue)
        self.kill_signal = Event()
