from multiprocessing import Process, Queue, Event
from queue import Empty
import time
import datetime
from stytra.hardware.motor.stageAPI import Motor
from collections import namedtuple
from time import sleep
from stytra.collectors.namedtuplequeue import NamedTupleQueue
import math
import numpy as np
import pandas as pd
import deepdish as dd
# import flammkuchen as fl

class SimpleReceiverProcess(Process):
    def __init__(self, dot_position_queue,
                 finished_event, motor_position_queue,
                 arena_lim):
        super().__init__()
        self.position_queue = dot_position_queue
        self.motor_position_queue = motor_position_queue
        self.finished_event = finished_event
        self. start_x = None
        self.start_y = None

        self.time_list = []


    def run(self):
        acc = int(204552)
        velo = int(107374182)

        self.motor_y = Motor(1, scale=1)
        self.motor_x = Motor(2, scale=1)
        self.motor_y.open()
        self.motor_x.open()
        self.motor_y.setvelocity(acceleration=acc, velocity=velo)
        self.motor_x.setvelocity(acceleration=acc, velocity=velo)


        self.start_x = self.motor_x.get_position()
        self.start_y = self.motor_y.get_position()

        # self.motor_x.set_settle_params(time=197, settledError=20, maxTrackingError=200, notUsed=0, lastNotUsed=0)

        # self.motor_x.request_pid()
        # self.motor_x.set_pos_loop_params(pgain=500, intgain=300, intlim=50000, diffgain=1000, derivcalc=4, factor=6554,
        #                             velo=1000, acc=1000)
        # self.motor_x.get_pos_loop_params()

        self.start_time = None
        second_output = namedtuple("fish_scaled", ["f0_x", "f0_y"])

        while not self.finished_event.is_set():
            pos_x = self.motor_x.get_position()
            pos_y = self.motor_y.get_position()
            pos = (pos_x, pos_y)
            self.motor_position_queue.put(0, second_output(*pos))

            while True:
                try:
                    tracked_time, last_position = self.position_queue.get(timeout=0.001)

                except Empty:
                    break

                if last_position is not None:
                    self.motor_x.get_status_bits()

                    self.motor_x.move_rel(int(last_position.f0_x))
                    self.motor_y.move_rel(int(last_position.f0_y))


        self.motor_x.close()
        self.motor_y.close()



class SimpleSendProcess(Process):
    def __init__(self, target_position_queue,
                 target_position_queue_copy,
                 motor_position_queue,
                 finished_event,
                 disp):
        super().__init__()

        df = pd.read_csv(r"C:\Users\portugueslab\Desktop\fake_fish_data.csv", index_col=0)

        x = disp / math.sqrt(2)
        y = disp / math.sqrt(2)
        self.target_position_queue = target_position_queue
        self.target_position_queue_copy = target_position_queue_copy
        self.motor_position_queue = motor_position_queue
        self.finished_event = finished_event
        # self.array_pos = [(-x, y), (x, y), (x, -y), (-x, -y)]
        self.array_pos = [(-x, -y)]

    def run(self) -> None:
        time.sleep(3)
        print('starting...')
        second_output = namedtuple("fish_scaled", ["f0_x", "f0_y"])
        i = 0
        while not self.finished_event.is_set():
            xy_dist = self.array_pos[0]
            self.target_position_queue.put(0, second_output(*xy_dist))
            self.target_position_queue_copy.put(0, second_output(*xy_dist))
            if i == 3:
                i = 0
            else:
                i += 1
            time.sleep(1/0.5)


class TemporalProcess(Process):
    def __init__(self, desired_position_queue_copy,
                 motti_position_queue,
                 end_event, name_file):
        super().__init__()
        self.motti_position_queue = motti_position_queue
        self.desired_position_queue_copy = desired_position_queue_copy
        self.end_event = end_event
        self.last_position = None
        self.last_target = None
        self.name_file = name_file

    def run(self) -> None:
        time_bin_list = []
        accumulator = 0
        prev_time = datetime.datetime.now()
        flag = False
        target = None
        position = None
        idx = 0
        t = []
        target_x = []
        target_y = []
        pos_x = []
        pos_y = []

        t.append(np.nan)
        target_x.append(np.nan)
        target_y.append(np.nan)
        pos_x.append(np.nan)
        pos_y.append(np.nan)


        while not self.end_event.is_set():
            now_time = datetime.datetime.now()
            try:
                tracked_time, position = self.motti_position_queue.get(timeout=0.001)
            except Empty:
                position = self.last_position
            try:
                tracked_time, target = self.desired_position_queue_copy.get(timeout=0.001)
                flag = False
            except Empty:
                flag = True

            delta_clock = (now_time - prev_time).microseconds
            accumulator += delta_clock

            if target is not None and position is not None:
                idx += 1

                if flag is False:
                    t.append(accumulator)
                    target_x.append(target.f0_x)
                    target_y.append(target.f0_y)
                    pos_x.append(position.f0_x)
                    pos_y.append(position.f0_y)

                elif flag is True:
                    t.append(accumulator)
                    target_x.append(0)
                    target_y.append(0)
                    pos_x.append(position.f0_x)
                    pos_y.append(position.f0_y)

            self.last_position = position
            self.last_target = target
            prev_time = now_time

        d = {'t': t, 'target_x': target_x, 'target_y': target_y, 'pos_x': pos_x, 'pos_y': pos_y, }
        time_bin_df = pd.DataFrame(data=d)
        time_bin_df.to_hdf("170620_diagonal_disp.h5", key='time_bin_df', mode='w')


if __name__ == "__main__":
    finished_event = Event()
    motor_position_queue = NamedTupleQueue()
    target_position_queue = NamedTupleQueue()
    target_position_queue_copy = NamedTupleQueue()
    displ = 100000 #test max at 100000
    arena_lim = 100
    name_file = "file.h5"
    source = SimpleSendProcess(target_position_queue,
                               target_position_queue_copy,
                               motor_position_queue,
                               finished_event,
                               displ)
    receiver = SimpleReceiverProcess(target_position_queue,
                                     finished_event,
                                     motor_position_queue,
                                     arena_lim)
    timing_process = TemporalProcess(target_position_queue_copy,
                                     motor_position_queue,
                                     finished_event, name_file)
    timing_process.start()
    source.start()
    receiver.start()

    time.sleep(20)
    print('time expired!')
    finished_event.set()
    source.join()
    receiver.join()
