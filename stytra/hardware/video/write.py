import numpy as np
import flammkuchen as fl

from stytra.utilities import FrameProcess
from multiprocessing import Queue, Event
from queue import Empty
from pathlib import Path
from stytra.utilities import save_df
import pandas as pd

import os
import abc

try:
    import av
except ImportError:
    print("PyAv not installed, writing videos in formats other than H5 not possible.")


class VideoWriter(FrameProcess):
    """
    Allows for recording the camera frames during the experiment and save it to disk.
    The video file is written into the same directory as the behavioral data.
    """

    CONST_FALLBACK_FILENAME = "protocol"

    def __init__(
        self,
        input_queue: Queue,
        recording_event: Event,
        reset_event: Event,
        finish_event: Event,
        log_format: str = "hdf5",
    ) -> None:
        """
        Parameters
        ----------
        input_queue
            queue of incoming frames
        recording_event
            signal to start the recording or save the recording once finished (by clearing the event, which first
            triggers the _complete() and then the _reset() functions)
        reset_event
            signal to reset the recording, triggers the _reset() function
        finish_event
            signal to finish the recording, save the files, and quit the process, triggers the _reset() function
            and exits the run() function.
        log_format
            Format of the file that the timestamp data will be written to.
        """
        super().__init__()
        self.filename_queue = Queue()
        self.__filename_base = None
        self.__input_queue = input_queue
        self.recording_event = recording_event
        self.finish_event = finish_event
        self.reset_event = reset_event
        self._times = []
        self._log_format = log_format

    def run(self) -> None:
        """ "
        Runs the recording process and listens for events.
        Possible events and their effects are listed in the class description.
        """
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

    def _configure(self, size: np.ndarray.shape) -> None:
        """ "
        Runs the necessary configuration before the recording starts.
        Sets the filename of the video file.
        Can be extended by subclasses for additional configuration.

        Parameters
        ----------
        size
            the shape of the frame, necessary when using PyAv for recording.
        """

        # None check to prevent some process from taking a filename
        # that was waiting for a future time.
        if self.__filename_base is None:
            try:
                self.__filename_base = self.filename_queue.get(timeout=0.01)
            except Empty:
                # Try again later.
                pass

    @abc.abstractmethod
    def _ingest_frame(self, frame: np.ndarray) -> None:
        """ "
        Abstract method that should contain logic to process (and potentially save) the frame.

        Parameters
        ----------
        frame
            a numpy 2D array containing the frame recorded by the camera.
        """
        raise NotImplementedError("Should be implemented by subclass.")

    def _complete(self, filename: str) -> None:
        """ "
        Saves a dataframe containing the timestamps of all the frames.
        Can be extended by subclasses for other logic that should be executed upon finishing the recording.

        Parameters
        ----------
        filename
            part of the filename that the data will be saved to
            (other parts consist of 'video_times' and the log format).
        """
        save_df(
            pd.DataFrame(self._times, columns=["t"]),
            Path(str(filename) + "video_times"),
            self._log_format,
        )

    def _reset(self) -> None:
        """ "
        Resets the recording process by resetting all the recording specific variables.
        No data is saved, but data that is already written to disk (i.e. frames that immediately get written upon
        recording) are not explicitly removed.
        """

        # Reset all protocol specific variables.
        self.__filename_base = None
        self._times = []
        self.recording_event.clear()
        self.reset_event.clear()

    def _get_filename_base(self) -> str:
        """ "
        Getter for the filename_base variable.
        This allows the filename to be accessible to subclasses, but prevent them from changing it
        (as long as the conventions are followed).

        Returns
        -------
        the filename_base variable.
        """

        return self.__filename_base


class H5VideoWriter(VideoWriter):
    """
    Writes the recorded frames to a HDF5 file.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._frames = []

    def _reset(self) -> None:
        super()._reset()
        self._frames = []

    def _ingest_frame(self, frame) -> None:
        """
        Appends the frames to an array.
        """
        self._frames.append(frame)

    def _complete(self, filename) -> None:
        """
        Writes the frames to a hdf5 file.
        """
        super()._complete(filename)
        fl.save(filename + "video.hdf5", np.array(self._frames, dtype=np.uint8))


class StreamingVideoWriter(VideoWriter):
    """
    Writes the recorded frames to video file (mp4 by default).
    """

    def __init__(
        self,
        *args,
        extension: str = "mp4",
        output_framerate: int = 24,
        format: str = "mpeg4",
        kbit_rate: int = 1000,
        **kwargs
    ) -> None:
        """
        Parameters
        ----------
        extension
            the extension of the video file name (unrelated to the actual format).
        output_framerate
            the framerate at which the video will be saved.
        format
            the format in which the video is saved (mp4 by default).
        kbit_rate
            the bit rate at which the video is encoded.
        """
        super().__init__(*args, **kwargs)
        self._extension = extension
        self._output_framerate = output_framerate
        self._format = format
        self._kbit_rate = kbit_rate
        self._container = None
        self._stream = None

        self.__container_filename = self.__generate_filename(
            self.CONST_FALLBACK_FILENAME
        )

    def __generate_filename(self, filename: str) -> str:
        """
        Generates the filename dependent on the given filename and the extension.

        Parameters
        ----------
        filename
            a unique identifier to be used in the filename for saving the video file.
        """
        return str(filename) + "video." + self._extension

    def _configure(self, shape: np.ndarray.shape) -> None:
        """
        Sets up a container and stream to save the files to, using the format and parameters set on initialisation.

        Parameters
        ----------
        shape
            the width and height of the stream, should correspond to the shape of the frames.
        """
        super()._configure(shape)

        if self._get_filename_base() is not None:
            self.__container_filename = self.__generate_filename(
                self._get_filename_base()
            )

        self._container = av.open(self.__container_filename, mode="w")
        self._stream = self._container.add_stream(
            self._format, rate=self._output_framerate
        )
        self._stream.height, self._stream.width = shape
        self._stream.codec_context.thread_type = "AUTO"
        self._stream.codec_context.bit_rate = self._kbit_rate * 1000
        self._stream.codec_context.bit_rate_tolerance = self._kbit_rate * 200
        self._stream.pix_fmt = "yuv420p"

    def _ingest_frame(self, frame: np.ndarray) -> None:
        """
        Formats and encodes the frame after which it is added to the PyAv container.
        """
        av_frame = av.VideoFrame.from_ndarray(frame, format="gray8")
        for packet in self._stream.encode(av_frame):
            self._container.mux(packet)

    def _reset(self) -> None:
        super()._reset()
        self._container = None
        self._stream = None
        self.__container_filename = self.__generate_filename(
            self.CONST_FALLBACK_FILENAME
        )

    def _complete(self, filename: str) -> None:
        """
        Completes the recording process and closes the container.
        If the fallback filename was used, but the new filename has been retrieved, it will rename the file.

        Parameters
        ----------
        filename
            the unique identifier that the video filename should have. If it is different from the initial filename
            (i.e. because the fallback name was used) the video file will be renamed to this.
        """
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
