import numpy as np
import flammkuchen as fl

from stytra.utilities import FrameProcess
from multiprocessing import Queue
from queue import Empty
from stytra.utilities import save_df
import pandas as pd

import os

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
    finish_event
        signal to finish recording
    kbit_rate
        ouput movie bitrate
    """

    CONST_FALLBACK_FILENAME = 'protocol'

    def __init__(self, input_queue, recording_event, reset_event, finish_event, log_format="hdf5"):
        super().__init__()
        self.filename_queue = Queue()
        self.__filename_base = None
        self.__input_queue = input_queue
        self.recording_event = recording_event
        self.finish_event = finish_event
        self.reset_event = reset_event
        self._times = []
        self._log_format = log_format

    def run(self):
        is_recording = False
        while True:
            # Even if we're not recording yet,
            # frames will be fed into the queue, so we need to discard them.
            try:
                t, current_frame = self.__input_queue.get(timeout=0.01)
                is_receiving_frames = True
            except Empty:
                is_receiving_frames = False

            if self.reset_event.is_set() or self.finish_event.is_set():
                is_recording = False
                self._reset()

                if self.finish_event.is_set():
                    # Stop the process
                    self.finish_event.clear()
                    break

            # is_receiving_frames makes sure we don't process the same frame twice.
            if self.recording_event.is_set() and is_receiving_frames:
                # We are recording.
                if is_recording is False:
                    # Do pre-recording configuration.
                    self._configure(current_frame.shape)
                    is_recording = True
                else:
                    self._ingest_frame(current_frame)
                    self._times.append(t)
            elif not self.recording_event.is_set():
                # We are not recording.
                if is_recording:
                    # We were recording, but are not anymore, save the data.
                    # Since the filename is given asynchronously, check if we have the filename.
                    # Otherwise, use the fallback.
                    if self.__filename_base is not None:
                        self._complete(self.__filename_base)
                    else:
                        try:
                            self.__filename_base = self.filename_queue.get(timeout=1)
                            self._complete(self.__filename_base)
                        except Empty:
                            self._complete(self.CONST_FALLBACK_FILENAME)

                    # Also reset any protocol specific variables.
                    self._reset()
                    is_recording = False

            self.framerate_rec.update_framerate()

    def _configure(self, size):
        # None check to prevent some process from taking a filename
        # that was waiting for a future time.
        if self.__filename_base is None:
            try:
                self.__filename_base = self.filename_queue.get(timeout=0.01)
            except Empty:
                # Try again later.
                pass

    def _ingest_frame(self, frame):
        pass

    def _complete(self, filename):
        save_df(
            pd.DataFrame(self._times, columns=["t"]),
            filename + "video_times",
            self._log_format,
        )

    def _reset(self):
        # Reset all protocol specific variables.
        self.__filename_base = None
        self._times = []
        self.recording_event.clear()
        self.reset_event.clear()

    # We want the filename to be accessible to subclasses, but prevent them from changing it.
    def _get_filename_base(self):
        return self.__filename_base


class H5VideoWriter(VideoWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._frames = []

    def _reset(self):
        super()._reset()
        self._frames = []

    def _ingest_frame(self, frame):
        self._frames.append(frame)

    def _complete(self, filename):
        super()._complete(filename)
        fl.save(
            filename + "video.hdf5", np.array(self._frames, dtype=np.uint8)
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
        self._extension = extension
        self._output_framerate = output_framerate
        self._format = format
        self._kbit_rate = kbit_rate
        self._container = None
        self._stream = None

        self.__container_filename = self.CONST_FALLBACK_FILENAME

    def __generate_filename(self, filename):
        return filename + "video." + self._extension

    def _configure(self, shape):
        super()._configure(shape)

        if self._get_filename_base() is not None:
            self.__container_filename = self.__generate_filename(self._get_filename_base())

        self._container = av.open(self.__container_filename, mode="w")
        self._stream = self._container.add_stream(self._format, rate=self._output_framerate)
        self._stream.height, self._stream.width = shape
        self._stream.codec_context.thread_type = "AUTO"
        self._stream.codec_context.bit_rate = self._kbit_rate * 1000
        self._stream.codec_context.bit_rate_tolerance = self._kbit_rate * 200
        self._stream.pix_fmt = "yuv420p"

    def _ingest_frame(self, frame):
        av_frame = av.VideoFrame.from_ndarray(frame, format="gray8")
        for packet in self._stream.encode(av_frame):
            self._container.mux(packet)

    def _reset(self):
        super()._reset()
        self._container = None
        self._stream = None
        self.__container_filename = self.CONST_FALLBACK_FILENAME

    def _complete(self, filename):
        super()._complete(filename)
        for packet in self._stream.encode():
            self._container.mux(packet)

        # Close the file
        self._container.close()

        # Check if the filename differs from filename, because then we used a fallback.
        # In which case we want to rename the file.
        generated_filename = self.__generate_filename(self._get_filename_base())
        if generated_filename != self.__container_filename:
            os.rename(self.__container_filename, generated_filename)
