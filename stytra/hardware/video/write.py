import datetime
import numpy as np
import imageio
import deepdish as dd

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

    def __init__(self, folder, input_queue, finished_signal, saving_evt,
                 format="hdf5", kbit_rate=4000):
        super().__init__()
        self.format = format
        self.folder = folder
        self.input_queue = input_queue
        self.finished_signal = finished_signal
        self.saving_evt = saving_evt
        self.kbit_rate = kbit_rate
        self.reset_signal = Event()
        if not os.path.isdir(folder):
            os.makedirs(folder)

    def run(self):
        while True:

            video_frame = None

            movie = []
            toggle_save = False
            while True:
                try:
                    t, current_frame = self.input_queue.get(timeout=0.01)
                    if self.saving_evt.is_set():
                        movie.append(current_frame)
                        toggle_save = True

                except Empty:
                    pass

                if not self.saving_evt.is_set() and toggle_save:
                    if self.format == "mp4":
                        imageio.mimwrite(self.folder + filename + "movie.mp4",
                                         np.array(movie, dtype=np.uint8), fps=3,
                                         quality=None,
                                         ffmpeg_params=["-pix_fmt", "yuv420p", "-profile:v", "baseline",
                                                        "-level", "3", ], )

                    elif self.format == "hdf5":
                        filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        print(self.folder + filename + "movie.hdf5")
                        dd.io.save(self.folder + filename + "movie.hdf5",
                                   np.array(movie, dtype=np.uint8))

                    toggle_save = False

                if self.reset_signal.is_set() or self.finished_signal.is_set():
                    self.reset_signal.clear()
                    movie = []
                    toggle_save = False
                    break

                self.framerate_rec.update_framerate()

            if self.finished_signal.is_set():
                break


