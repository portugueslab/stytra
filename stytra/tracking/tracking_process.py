from queue import Empty, Full
from multiprocessing import Event, Value
from time import sleep
from collections import namedtuple
import time as tim
import datetime
from stytra.utilities import FrameProcess
from arrayqueues.shared_arrays import TimestampedArrayQueue
from multiprocessing import Queue

class TrackingProcess(FrameProcess):
    """A class which handles taking frames from the camera and processing them,
     as well as dispatching a subset for display

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self,
        in_frame_queue,
        finished_signal: Event = None,
        pipeline=None,
        processing_parameter_queue=None,
        output_queue=None,
        recording_signal=None,
        gui_framerate=30,
        max_mb_queue=100,
        **kwargs
    ):
        """
        Frame dispatcher process

        Parameters
        ----------
        in_frame_queue:
            queue dispatching frames from camera
        finished_signal
            signal for the end of the acquisition
        pipeline: Pipeline
            tracking pipeline
        processing_parameter_queue
            queue for function&parameters
        output_queue:
            tracking output queue
        recording_signal: bool (false)

        processing_counter
        gui_framerate: int
            target framerate of the display GUI
        gui_dispatcher

        max_mb_queue: int (200)
            the maximal size of the image output queues

        kwargs
        """

        super().__init__(name="tracking", **kwargs)

        self.frame_queue = in_frame_queue
        self.gui_queue = TimestampedArrayQueue(max_mbytes=max_mb_queue)  # GUI queue for

        self.time_queue = Queue()
        self.recording_signal = recording_signal
        if recording_signal is not None:
            self.frame_copy_queue = TimestampedArrayQueue(max_mbytes=max_mb_queue)
        else:
            self.frame_copy_queue = None

        #  displaying
        #  the image
        self.output_queue = output_queue  # queue for processing output (e.g., pos)
        self.processing_parameter_queue = processing_parameter_queue

        self.finished_signal = finished_signal
        self.gui_framerate = gui_framerate

        self.pipeline_cls = pipeline
        self.pipeline = None

        self.i = 0

    def process_internal(self, frame):
        """Apply processing function to current frame with
        self.processing_parameters as additional inputs.

        Parameters
        ----------
        frame :
            frame to be processed;

        Returns
        -------
        type
            processed output

        """

    def retrieve_params(self):
        while True:
            try:
                param_dict = self.processing_parameter_queue.get(timeout=0.0001)
                self.pipeline.deserialize_params(param_dict)
            except Empty:
                break

    def send_to_queue(self, time, output):
        self.output_queue.put(time, output)

    def run(self):
        """Loop where the tracking function runs."""

        self.pipeline = self.pipeline_cls()
        self.pipeline.setup()

        while not self.finished_signal.is_set():

            # Gets the processing parameters from their queue
            self.retrieve_params()

            # Gets frame from its queue, if the input is too fast, drop frames
            # and process the latest, if it is too slow continue:
            try:
                time, frame_idx, frame = self.frame_queue.get(timeout=0.001)
            except Empty:
                continue

            messages = []
            # If we are copying the frames to another queue (e.g. for video recording), do it here
            if self.recording_signal is not None and self.recording_signal.is_set():
                try:
                    self.frame_copy_queue.put(frame.copy(), timestamp=time)
                except:
                    messages.append("W:Dropping frames from recording")

            # If a processing function is specified, apply it:

            new_messages, output = self.pipeline.run(frame)

            for msg in messages + new_messages:
                self.message_queue.put(msg)

            self.send_to_queue(time, output)

            # calculate the frame rate
            self.update_framerate()

            # put current frame into the GUI queue
            self.send_to_gui(
                time,
                self.pipeline.diagnostic_image
                if self.pipeline.diagnostic_image is not None
                else frame,
            )

        return

    def send_to_gui(self, frametime, frame):
        """ Sends the current frame to the GUI queue at the appropriate framerate"""
        if self.framerate_rec.current_framerate:
            every_x = max(
                int(self.framerate_rec.current_framerate / self.gui_framerate), 1
            )
        else:
            every_x = 1
        if self.i == 0:
            try:
                self.gui_queue.put(frame, timestamp=frametime)
            except Full:
                self.message_queue.put("E:GUI queue full")

        self.i = (self.i + 1) % every_x


class TrackingProcessMotor(TrackingProcess):
    def __init__(self, *args,
                 second_output_queue=None,
                 calib_queue= None, scale= None, time_queue=None, time_queue2=None, **kwargs):

        super().__init__(*args, **kwargs)
        self.second_output_queue = second_output_queue
        self.calib_queue = calib_queue
        self.calibration_event = Event()
        # self.time_queue= time_queue
        self.home_event = Event()
        self.tracking_event = Event()
        self.scale_x = None
        self.scale_y = None
        self.threshold = 100
        self.scale = scale
        #todo get center x, y from camera or something
        self.center_y = 268
        self.center_x = 360

        self.time_queue2 = time_queue2

    def send_to_queue(self, time, output):
        self.output_queue.put(time, output)

    def send_to_second_queue(self, time, output):
        self.second_output_queue.put(time, output)

    def run(self):
        """Loop where the tracking function runs."""
        second_output = namedtuple("fish_scaled", ["f0_x", "f0_y"])

        self.pipeline = self.pipeline_cls()
        self.pipeline.setup()

        while not self.finished_signal.is_set():

            # Gets the processing parameters from their queue
            self.retrieve_params()

            try:
                time, [scale_x, scale_y] = self.calib_queue.get(timeout=0.001)
                print("gotten from calibrator ", scale_x, scale_y)
                self.scale_x = scale_x
                self.scale_y = scale_y
                if abs(scale_x - scale_y) > self.threshold:
                    self.scale_x = self.scale[0]
                    self.scale_y = self.scale[1]
                    print("Calibrated scales difference too large. Setting default")
            except Empty:
                pass


            # Gets frame from its queue, if the input is too fast, drop frames
            # and process the latest, if it is too slow continue:
            try:
                time, frame_idx, frame = self.frame_queue.get(timeout=0.001)
                out = self.time_queue.get(timeout=0.001)


                start = datetime.datetime.now()
            except Empty:
                continue


            messages = []
            # If we are copying the frames to another queue (e.g. for video recording), do it here
            if self.recording_signal is not None and self.recording_signal.is_set():
                try:
                    self.frame_copy_queue.put(frame.copy(), timestamp=time)
                except:
                    messages.append("W:Dropping frames from recording")

            # If a processing function is specified, apply it:
            new_messages, output = self.pipeline.run(frame)
            # print ("fish identified", output.f0_x, output.f0_y)

            #Calculate new position for the motor if calibration was set
            if self.scale_x is None:
                print ("setting default")
                self.scale_x = self.scale[0]
                self.scale_y = self.scale[1]

            distance_y = (output.f0_y - self.center_y) * self.scale_y
            distance_x = (output.f0_x - self.center_x) * self.scale_x

            if (distance_x) ** 2 + (distance_y) ** 2 >= 500 ** 2:
                sec_output= (distance_x, distance_y)
            else:
                sec_output=(0.0,0.0)

            for msg in messages + new_messages:
                self.message_queue.put(msg)

            self.send_to_queue(time, output)
            self.send_to_second_queue(time, second_output(*sec_output))

            out[0] = tim.time_ns() - out[0]
            # print('first', out[0] / 1000)
            out.append(tim.time_ns())
            self.time_queue2.put(out)

            # calculate the frame rate
            self.update_framerate()

            # put current frame into the GUI queue
            self.send_to_gui(
                time,
                self.pipeline.diagnostic_image
                if self.pipeline.diagnostic_image is not None
                else frame,
            )

        return


class DispatchProcess(FrameProcess):
    """ A class which handles taking frames from the camera and dispatch them to both a separate
    process (e.g. for saving a movie) and to a gui for display

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self,
        in_frame_queue,
        finished_evt: Event = None,
        dispatching_set_evt: Event = None,
        gui_framerate=30,
        gui_dispatcher=False,
        **kwargs
    ):
        """
        :param in_frame_queue: queue dispatching frames from camera
        :param finished_evt: signal for the end of the acquisition
        :param processing_parameter_queue: queue for function&parameters
        :param gui_framerate: framerate of the display GUI
        """
        super().__init__(name="tracking", **kwargs)

        self.frame_queue = in_frame_queue
        self.gui_queue = TimestampedArrayQueue(max_mbytes=600)  # GUI queue
        # for displaying the image
        self.output_frame_queue = TimestampedArrayQueue(max_mbytes=600)

        self.dispatching_set_evt = dispatching_set_evt
        self.finished_signal = finished_evt
        self.gui_framerate = gui_framerate
        self.gui_dispatcher = gui_dispatcher

        self.i = 0

    def run(self):
        """Loop where the tracking function runs."""

        while not self.finished_signal.is_set():

            # Gets frame from its queue, if the input is too fast, drop frames
            # and process the latest, if it is too slow continue:
            try:
                time, frame_idx, frame = self.frame_queue.get(timeout=0.001)
            except Empty:
                continue

            if self.dispatching_set_evt.is_set():
                self.output_frame_queue.put(frame.copy(), time)

            # put current frame into the GUI queue
            self.send_to_gui(time, frame)

            # calculate the frame rate
            self.update_framerate()

        return

    def send_to_gui(self, frametime, frame):
        """ Sends the current frame to the GUI queue at the appropriate framerate"""
        if self.framerate_rec.current_framerate:
            every_x = max(
                int(self.framerate_rec.current_framerate / self.gui_framerate), 1
            )
        else:
            every_x = 1
        if self.i == 0:
            self.gui_queue.put(frame, timestamp=frametime)
        self.i = (self.i + 1) % every_x
