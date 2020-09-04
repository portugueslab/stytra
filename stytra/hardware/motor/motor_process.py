from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
from stytra.hardware.motor.stageAPI import Motor
from collections import namedtuple
import time as tim
from stytra.collectors.namedtuplequeue import NamedTupleQueue
import pickle


class ReceiverProcess(Process):
    def __init__(self, dot_position_queue, calib_event,
                 home_event, finished_event, motor_position_queue,
                 tracking_event, motor_status_queue, arena_lim, time_queue2):
        super().__init__()
        self.position_queue = dot_position_queue
        self.motor_position_queue = motor_position_queue
        self.finished_event = finished_event
        self.calib_event = calib_event
        self.home_event = home_event
        self.tracking_event = tracking_event
        self.motor_status_queue = motor_status_queue
        self.arena_lim = arena_lim *20000 #put in mm, get our motor units,
        self.home = 2200000
        self.tracking_failure_timeout = 10 # 10 seconds
        self.time_queue2 = time_queue2
        self.time_list = []


    def run(self):
        #Initialize the Motor here with standard scale
        self.motor_y = Motor(1, scale=1)
        self.motor_x = Motor(2, scale=1)

        ##########
        self.motor_y.open()
        self.motor_x.open()
        self.motor_x.set_jogmode(2, 1)
        self.motor_y.set_jogmode(2, 1)
        # self.motor_x.set_settle_params(time=197, settledError=1000, maxTrackingError=8000, notUsed=88, lastNotUsed=10562)
        # self.motor_y.set_settle_params(time=197, settledError=1000, maxTrackingError=8000, notUsed=88, lastNotUsed=10562)

        output_type = namedtuple("stagexy", ["x_", "y_", "dist_x", "dist_y", "tracking", "waiting"])
        status_type = namedtuple("motor_status", ["tracking", "waiting"])
        idle_status = (False, True)
        last_position = None
        status = None
        self.motor_status = status_type(*idle_status)
        self.start_time = None

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

            while True:
                try:
                    out = self.time_queue2.get(timeout=0.001)
                    out[1] = tim.time_ns() - out[1]
                except Empty:
                    break


            self.motor_status = status

            if last_position is not None:
                time = datetime.datetime.now()
                pos_x = self.motor_x.get_position()
                pos_y = self.motor_y.get_position()
                # print('home:', self.home, 'x_pos:', pos_x, 'y_pos:', pos_y)

                #if it actually is tracking something
                if abs(last_position.f0_x) > 0:
                    tracking_status = (True, False)
                    self.motor_status = status_type(*tracking_status)
                    if (pos_x - self.home) ** 2 + (pos_y - self.home) ** 2 <= self.arena_lim ** 2:
                        self.start_time = datetime.datetime.now()
                        # self.motor_y.jogging(int(last_position.f0_y))
                        # self.motor_x.jogging(int(last_position.f0_x))
                        self.motor_x.move_rel(int(last_position.f0_x))
                        self.motor_y.move_rel(int(last_position.f0_y))
                        self.time_list.append(out)


                        e = (float(pos_x), float(pos_y), int(last_position.f0_x),
                             int(last_position.f0_y), self.motor_status.tracking,
                             self.motor_status.waiting)

                    else:
                        print ("out of bounds", self.arena_lim, pos_x, pos_y)
                        self.motor_x.movesimple(position=self.home)
                        self.motor_y.movesimple(position=self.home)
                        self.start_time = None
                        print ("position reset")


                #if tracking failure takes too long, go home and wait
                else:
                    self.motor_status = status_type(*idle_status)

                    e = (pos_x, pos_y, 0.0, 0.0, self.motor_status.tracking, self.motor_status.waiting)

                    if self.start_time is not None:
                        idle_time = (datetime.datetime.now() - self.start_time).total_seconds()
                        if idle_time > self.tracking_failure_timeout:
                            print ("tracking failure timeout called")
                            self.motor_x.movesimple(position=self.home)
                            self.motor_y.movesimple(position=self.home)
                            self.start_time = None

                #save the output
                self.motor_position_queue.put(time, output_type(*e))



        self.motor_x.close()
        self.motor_y.close()
        # with open("test_timing_software_Motti.txt", "wb") as fp:  # Pickling
        #     pickle.dump(self.time_list, fp)
        #     print(self.time_list)


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
