import numpy as np
import flammkuchen as fl

from stytra.utilities import FrameProcess
from multiprocessing import Event, Queue
from queue import Empty
from stytra.utilities import save_df
import pandas as pd

try:
    import av
except ImportError:
    print("PyAv not installed, writing videos in formats other than H5 not possible.")


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

    def __init__(self, input_queue, finished_signal, saving_evt, log_format="hdf5"):
        super().__init__()
        self.filename_queue = Queue()
        self.filename_base = None
        self.input_queue = input_queue
        self.finished_signal = finished_signal
        self.saving_evt = saving_evt
        self.reset_signal = Event()
        self.times = []
        self.recording = False
        self.log_format = log_format

    def run(self):
        while True:
            toggle_save = False
            self.reset()
            while True:
                try:
                    t, current_frame = self.input_queue.get(timeout=0.01)
                    if self.saving_evt.is_set():
                        if not self.recording:
                            self.configure(current_frame.shape)
                            self.recording = True
                        self.ingest_frame(current_frame)
                        self.times.append(t)
                        toggle_save = True

                except Empty:
                    pass

                if not self.saving_evt.is_set() and toggle_save:
                    self.complete()
                    toggle_save = False

                if self.reset_signal.is_set() or self.finished_signal.is_set():
                    self.reset_signal.clear()
                    self.reset()
                    break

                self.framerate_rec.update_framerate()

            if self.finished_signal.is_set():
                break

    def configure(self, size):
        self.filename_base = self.filename_queue.get(timeout=0.01)

    def ingest_frame(self, frame):
        pass

    def complete(self):
        save_df(
            pd.DataFrame(self.times, columns="t"),
            self.filename_base + "video_times",
            self.log_format,
        )
        self.recording = False

    def reset(self):
        self.recording = False
        self.times = []


class H5VideoWriter(VideoWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frames = []

    def reset(self):
        super().reset()
        self.frames = []

    def ingest_frame(self, frame):
        self.frames.append(frame)

    def complete(self):
        super().complete()
        fl.save(
            self.filename_base + "video.hdf5", np.array(self.frames, dtype=np.uint8)
        )


class StreamingVideoWriter(VideoWriter):
    def __init__(
        self,
        *args,
        extension="mp4",
        output_framerate=24,
        format="mpeg4",
        kbit_rate=1000,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.extension = extension
        self.output_framerate = output_framerate
        self.format = format
        self.kbit_rate = kbit_rate
        self.container = None
        self.stream = None

    def configure(self, shape):
        super().configure(shape)
        filename = self.filename_base + "video." + self.extension
        self.container = av.open(filename, mode="w")
        self.stream = self.container.add_stream(self.format, rate=self.output_framerate)
        self.stream.height, self.stream.width = shape
        self.stream.codec_context.thread_type = "AUTO"
        self.stream.codec_context.bit_rate = self.kbit_rate * 1000
        self.stream.codec_context.bit_rate_tolerance = self.kbit_rate * 200
        self.stream.pix_fmt = "yuv420p"

    def ingest_frame(self, frame):
        if self.stream is None:
            self.configure(frame.shape)
        av_frame = av.VideoFrame.from_ndarray(frame, format="gray8")
        for packet in self.stream.encode(av_frame):
            self.container.mux(packet)

    def reset(self):
        super().reset()
        self.container = None
        self.stream = None

    def complete(self):
        super().complete()
        for packet in self.stream.encode():
            self.container.mux(packet)

        # Close the file
        self.container.close()
