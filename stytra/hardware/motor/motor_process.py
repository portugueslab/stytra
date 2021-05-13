from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
from stytra.hardware.motor.stageAPI import Motor
from collections import namedtuple


class ReceiverProcess(Process):
    def __init__(
        self,
        dot_position_queue,
        calib_event,
        home_event,
        finished_event,
        motor_position_queue,
        tracking_event,
        motor_status_queue,
    ):
        super().__init__()
        self.position_queue = dot_position_queue
        self.motor_position_queue = motor_position_queue
        self.finished_event = finished_event
        self.calib_event = calib_event
        self.home_event = home_event
        self.tracking_event = tracking_event
        self.motor_status_queue = motor_status_queue
        self.home = 2200000
        self.tracking_failure_timeout = 10  # 10 seconds
        self.polling_time = 50

    def run(self):
        # Initialize the Motor here with standard scale
        self.motor_y = Motor(1, scale=1)
        self.motor_x = Motor(2, scale=1)

        max_acc = 204552
        max_velo = 107374182

        self.motor_y.open()
        self.motor_x.open()

        self.motor_x.setvelocity(int(max_acc / 10), int(max_velo / 10))
        self.motor_y.setvelocity(int(max_acc / 10), int(max_velo / 10))

        self.motor_x.polling(self.polling_time)
        self.motor_y.polling(self.polling_time)

        output_type = namedtuple(
            "stagexy", ["x_", "y_", "dist_x", "dist_y", "tracking", "waiting"]
        )
        status_type = namedtuple("motor_status", ["tracking", "waiting"])
        idle_status = (False, True)
        tracking_status = (True, False)
        last_position = None
        status = None
        self.motor_status = status_type(*idle_status)
        self.start_time = None  # for tracking timeout

        while not self.finished_event.is_set():

            if self.home_event.is_set():
                self.motor_status = status_type(*idle_status)
                self.motor_y.motorminimal()
                self.motor_x.set_homing_reverse(1)
                self.motor_x.motorminimal()
                self.home_event.clear()

            if self.calib_event.is_set():
                self.motor_status = status_type(*idle_status)
                self.motor_x.calibrator_movement()
                self.motor_y.calibrator_movement()
                self.calib_event.clear()

            while True:
                try:
                    tracked_time, last_position = self.position_queue.get(timeout=0.001)
                    start = datetime.datetime.now()
                except Empty:
                    break
            while True:
                try:
                    t, status = self.motor_status_queue.get(timeout=0.001)
                except Empty:
                    break

            self.motor_status = status

            if self.tracking_event.is_set():
                self.motor_status = status_type(*tracking_status)
                time = datetime.datetime.now()

                if last_position is not None:
                    self.motor_status = status_type(*tracking_status)
                    # time = datetime.datetime.now()
                    pos_x = self.motor_x.get_position()
                    pos_y = self.motor_y.get_position()

                    # if it actually is tracking something
                    if abs(last_position.f0_x) > 0:
                        self.motor_status = status_type(*tracking_status)
                        # self.start_time = datetime.datetime.now()
                        self.motor_x.move_rel(int(last_position.f0_x))
                        self.motor_y.move_rel(int(last_position.f0_y))

                        e = (
                            float(pos_x),
                            float(pos_y),
                            int(last_position.f0_x),
                            int(last_position.f0_y),
                            self.motor_status.tracking,
                            self.motor_status.waiting,
                        )

                # if tracking failure takes too long, go home and wait
                else:
                    self.motor_status = status_type(*idle_status)
                    self.start_time = (
                        datetime.datetime.now()
                    )  # start counting idle time
                    e = (
                        pos_x,
                        pos_y,
                        0.0,
                        0.0,
                        self.motor_status.tracking,
                        self.motor_status.waiting,
                    )

                    # if self.start_time is not None:

                    idle_time = (
                        datetime.datetime.now() - self.start_time
                    ).total_seconds()
                    if idle_time > self.tracking_failure_timeout:
                        print("tracking failure timeout called")
                        self.motor_x.movesimple(position=self.home)
                        self.motor_y.movesimple(position=self.home)
                        self.start_time = None

                # save the output
                self.motor_position_queue.put(time, output_type(*e))

        self.motor_x.close()
        self.motor_y.close()


################################


if __name__ == "__main__":
    event = Event()
    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue, finished_event=event)
    source.start()
    receiver.start()

    finishUp = True
    sleep(20)
    event.set()
    source.join()
    receiver.join()
