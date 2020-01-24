from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
from stytra.hardware.motor.stageAPI import Motor
from collections import namedtuple



class ReceiverProcess(Process):
    def __init__(self, dot_position_queue, calib_event,
                 home_event, finished_event, motor_position_queue,
                 tracking_event, motor_status_queue, arena_lim):
        super().__init__()
        self.position_queue = dot_position_queue
        self.motor_position_queue = motor_position_queue
        self.finished_event = finished_event
        self.calib_event = calib_event
        self.home_event = home_event
        self.tracking_event =tracking_event
        self.motor_status_queue = motor_status_queue
        self.arena_lim = arena_lim
        self.home = 2200000
        self.tracking_failure_timeout = 10 # 10 seconds
        self.arena_lim = 1000000/3


    def run(self):
        #Initialize the Motor here with standard scale
        self.motor_y = Motor(1, scale=1)
        self.motor_x = Motor(2, scale=1)

        ##########
        self.motor_y.open()
        self.motor_x.open()
        self.motor_x.set_jogmode(2, 1)
        self.motor_x.set_jogstepsize(20000)
        self.motor_y.set_jogmode(2, 1)
        self.motor_y.set_jogstepsize(20000)
        output_type = namedtuple("stagexy", ["x_", "y_", "dist_x", "dist_y", "tracking", "waiting"])
        status_type = namedtuple("motor_status", ["tracking", "waiting"])
        idle_status = (False, True)
        last_position = None
        self.motor_status = status_type(*idle_status)
        self.start_time = None

        while not self.finished_event.is_set():

            if self.home_event.is_set():
                self.motor_status = status_type(*idle_status)
                self.motor_y.motorminimal()
                self.motor_x.set_homing_reverse(1)
                self.motor_x.motorminimal()
                self.position_queue.clear()
                self.home_event.clear()

            if self.calib_event.is_set():
                self.motor_status = status_type(*idle_status)
                self.motor_x.calibrator_movement()
                self.motor_y.calibrator_movement()
                self.position_queue.clear()
                self.calib_event.clear()

            # if not self.tracking_event.is_set():
            #     self.position_queue.clear()
            #     self.motor_status = status_type(*idle_status)


            try:
                tracked_time, last_position = self.position_queue.get(timeout=0.001)
                t, status = self.motor_status_queue.get(timeout=0.001)
                self.motor_status = status

            except Empty:
                pass

            if last_position is not None:
                time = datetime.datetime.now()
                pos_x = self.motor_x.get_position()
                pos_y = self.motor_y.get_position()


                if last_position.f0_x > 0:
                    self.start_time = datetime.datetime.now()
                    tracking_status = (True, False)
                    self.motor_status = status_type(*tracking_status)

                else:
                    self.motor_status = status_type(*idle_status)
                    self.position_queue.clear()
                    if self.start_time is not None:
                        idle_time = (datetime.datetime.now() - self.start_time).total_seconds()
                        if idle_time > self.tracking_failure_timeout:
                            self.motor_x.set_homing_reverse(1)
                            self.motor_x.home()
                            self.motor_y.home()
                            self.start_time = None


                try:
                    #todo something wrong with this arena limiter

                    if (pos_x - self.home) ** 2 + (pos_y - self.home) ** 2 > self.arena_lim ** 2:
                        # self.motor_x.set_homing_reverse(1)
                        # self.motor_x.home()
                        # self.motor_y.home()
                        # self.start_time = None
                        print( ("out of bounds"))

                    self.motor_x.jogging(int(last_position.f0_x))
                    self.motor_y.jogging(int(last_position.f0_y))


                    e = (float(pos_x), float(pos_y), int(last_position.f0_x),
                         int(last_position.f0_y), self.motor_status.tracking,
                         self.motor_status.waiting)

                except (ValueError, TypeError, IndexError):
                    e = (pos_x, pos_y, 0.0, 0.0, self.motor_status.tracking,
                         self.motor_status.waiting)

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
