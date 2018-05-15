import datetime
try:
    import av
except ImportError:
    pass

from arrayqueues.processes import FrameProcessor
from multiprocessing import Event


# TODO documentation
class VideoWriter(FrameProcessor):
    """
    """
    def __init__(self, folder, input_queue, finished_signal, kbit_rate=4000):
        super().__init__()
        self.folder = folder
        self.input_queue = input_queue
        self.finished_signal = finished_signal
        self.kbit_rate = kbit_rate
        self.reset_signal = Event()

    def run(self):
        while True:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_container = av.open(self.folder+timestamp+".mp4", mode='w')
            print("Recorder running, saving to ", self.folder+timestamp+".mp4")
            out_stream = None
            video_frame = None
            while True:
                if self.reset_signal.is_set() or self.finished_signal.is_set():
                    self.reset_signal.clear()
                    break
                try:
                    if out_stream is None:
                        current_frame = self.input_queue.get(timeout=1)
                        out_stream = out_container.add_stream('mpeg4', rate=50)
                        out_stream.width, out_stream.height = current_frame.shape[::-1]
                        out_stream.pix_fmt = 'yuv420p'
                        out_stream.bit_rate = self.kbit_rate*1000
                        video_frame = av.VideoFrame(current_frame.shape[1], current_frame.shape[0], "gray")
                        video_frame.planes[0].update(current_frame)
                    else:
                        video_frame.planes[0].update(self.input_queue.get(timeout=1))
                    print("Got and written frame")
                    packet = out_stream.encode(video_frame)
                    out_container.mux(packet)
                    self.update_framerate()

                except Empty:
                    pass
            if self.finished_signal.is_set():
                break

        if out_stream is not None:
            out_container.close()