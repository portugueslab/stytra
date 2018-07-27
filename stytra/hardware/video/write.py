import datetime

try:
    import av
except ImportError:
    pass

from stytra.utilities import FrameProcess
from multiprocessing import Event, Queue
from queue import Empty
import os


class VideoWriter(FrameProcess):
    """Writes behavior movies into video files using PyAV

    Parameters
    ----------
    folder
        output folder
    input_queue
        queue of incoming frames
    finished_signal
        signal to finish recording
    kbit_rate
        ouput movie bitrate
    """

    def __init__(self, folder, input_queue, finished_signal, kbit_rate=4000):
        super().__init__()
        self.folder = folder
        self.input_queue = input_queue
        self.filename_queue = Queue()
        self.finished_signal = finished_signal
        self.kbit_rate = kbit_rate
        self.reset_signal = Event()
        if not os.path.isdir(folder):
            os.makedirs(folder)

    def run(self):
        while True:
            filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".mp4"
            out_container = av.open(os.path.join(self.folder, filename), mode="w")

            self.filename_queue.put(filename)
            out_stream = None
            video_frame = None
            while True:
                if self.reset_signal.is_set() or self.finished_signal.is_set():
                    out_container.close()
                    self.reset_signal.clear()
                    break
                try:
                    if out_stream is None:
                        current_frame = self.input_queue.get(timeout=1)
                        out_stream = out_container.add_stream("mpeg4", rate=50)
                        out_stream.width, out_stream.height = current_frame.shape[::-1]
                        out_stream.pix_fmt = "yuv420p"
                        out_stream.bit_rate = self.kbit_rate * 1000
                        video_frame = av.VideoFrame(
                            current_frame.shape[1], current_frame.shape[0], "gray"
                        )
                        video_frame.planes[0].update(current_frame)
                    else:
                        video_frame.planes[0].update(self.input_queue.get(timeout=1))
                    packet = out_stream.encode(video_frame)
                    out_container.mux(packet)
                    self.update_framerate()

                except Empty:
                    pass
            if self.finished_signal.is_set():
                break

        if out_stream is not None:
            out_container.close()
