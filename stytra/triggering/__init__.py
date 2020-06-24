"""
This module contains Trigger objects that can be used to trigger the
beginning of a stytra protocol from an external event, such as a message
received via ZMQ from a microscope.
"""

from multiprocessing import Process, Event, Queue
import datetime
import time
from queue import Empty

try:
    import zmq
except:
    pass
try:
    import u3
except:
    pass


class Trigger(Process):
    """ Stytra uses
    :class:`Trigger <stytra.triggering.Trigger.__init__()>` objects  to control
    the beginning of a stimulation protocol via an external event.
    In the most obvious case, the signal is sent by
    an acquisition device such as a microscope to synchronize data acquisition
    and stimulation.
    The trigger has a check_trigger function that is constantly called in a while
    loop in the run(). When :meth:`Trigger <stytra.triggering.Trigger.check_trigger(
    )>` returns True, the  start_event is
    set. The Experiment class, if it has a trigger assigned, will wait until the
    start_event to be set before starting. The control in check_trigger() is
    defined in subclasses to reflect the condition that we want to control the
    beginning of the protocol.
    The class has `Queue` objects to communicate from and to stytra from an
    external acquisition
    device. In particular, `self.queue_duration` queue can be use
    to send to the external
    device the duration of the Stytra experiment, and `self.queue_device_params`
    can be use to send the external acquisition device parameters to stytra.
    Usage of these queues must be implemented in `Trigger` subclasses;
    `ZmqTrigger` already offers full implementation for this.


    **Events**

    start_event:
        event that is set when check_trigger() returns True. It
        is used by stytra to control the beginning of the protocol;

    kill_event:
        can be set to kill the Trigger process;

    **Input Queues**

    queue_duration :
        Queue where the experiment update its duration so that it can be
        sent to the acquisition device.

    **Output Queues**

    queue_device_params:
        can be used to send to the Experiment data about
        the triggering event or device. For example, if triggering happens from
        a microscope via a ZMQ message, setting of the microscope can be sent in
        that message to be saved together with experiment metadata.



    """

    def __init__(self):
        super().__init__()

        self.start_event = Event()
        self.t = datetime.datetime.now()
        self.kill_event = Event()
        self.device_params_queue = Queue()
        self.duration_queue = Queue()

    def check_trigger(self):
        """ Check condition required for triggering to happen. Implemented in
        subclasses.

        Returns
        -------
        bool
            True if triggering condition is satisfied (e.g., message received);
            False otherwise.

        """
        return False

    def run(self):
        """ In this process, we constantly invoke the check_trigger class to control
        if start_event has to be set. Once it has been set, we wait an
        arbitrary time (0.1 s now) and then we clear it to be set again.
        """
        TIME_START_EVENT_ON = 0.1
        while not self.kill_event.is_set():
            if self.start_event.is_set():
                # Keep the signal on for at least 0.1 s
                time.sleep(TIME_START_EVENT_ON)
                self.start_event.clear()
                if self.start_event.is_set():
                    print("Trying to start when the start event is already set")

            if self.check_trigger():
                print("Trigger signal received")
                self.start_event.set()
                self.t = datetime.datetime.now()
        self.complete()

    def complete(self):
        pass


class ZmqTrigger(Trigger):
    """ This trigger uses the `ZMQ <http://zeromq.org/>`_ library to receive
    a json file from an external source such as a microscope. The port on which
    the communication is happening is taken as input. The source of the trigger
    must be configured with the IP and the port of the computer running the
    stytra session.
    """

    def __init__(self, port):
        """

        Parameters
        ----------
            port: string
            specifies the port on which communication will happen (e.g. '5555')

        """
        self.port = port
        self.protocol_duration = None
        self.scope_config = {}
        super().__init__()

    def check_trigger(self):
        """ Wait to receive the json file and reply with the duration of the
        experiment. Then, to the `queue_trigger_params` the received dict,
        so that the `Experiment` can store it with the rest of the data.
        """

        poller = zmq.Poller()
        poller.register(self.zmq_socket, zmq.POLLIN)
        try:
            self.protocol_duration = self.duration_queue.get(timeout=0.0001)
            print(self.protocol_duration)
        except Empty:
            pass
        if poller.poll(10):
            self.scope_config = self.zmq_socket.recv_json()
            self.device_params_queue.put(self.scope_config)
            self.zmq_socket.send_json(self.protocol_duration)
            return True
        else:
            return False

    def run(self):
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)
        self.zmq_socket.setsockopt(zmq.LINGER, 0)
        self.zmq_socket.bind("tcp://*:{}".format(self.port))
        self.zmq_socket.setsockopt(zmq.RCVTIMEO, -1)

        super().run()

    def complete(self):
        self.zmq_socket.close()


class U3LabJackPulseTrigger(Trigger):
    """" This triiger uses the `labjack <https://github.com/labjack/LabJackPython/>`_ u3
    to recieve a TTL pulse from an external source. The DIO number is used as input.
    The pin is initialized as input automatically"""

    def __init__(self, chan):
        """"

        Parameters
        ----------
            chan: int
            the DIO number used as input on the labjack
        """
        super().__init__()
        self.chan = chan
        self.device = None

    def check_trigger(self):
        """" Simply returns the state of the pin as a boolean """
        return bool(self.device.getFeedback(u3.BitStateRead(self.chan))[0])

    def run(self):
        self.device = u3.U3()
        self.device.getFeedback(u3.BitDirWrite(self.chan, 0))
        super().run()


if __name__ == "__main__":
    port = "5555"
    trigger = ZmqTrigger(port)
    trigger.start()
