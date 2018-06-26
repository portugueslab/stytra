"""
This module contains Trigger objects that can be used to trigger the
beginning of a stytra protocol from an external event, such as a message
received via ZMQ from a microscope.
"""

from multiprocessing import Process, Event, Queue
import datetime
import time
import zmq


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

    **Events**

    start_event:
        event that is set when check_trigger() returns True. It
        is used by stytra to control the beginning of the protocol;

    kill_event:
        can be set to kill the Trigger process;


    **Output Queues**

    queue_trigger_params:
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
        self.queue_trigger_params = Queue()

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
        while True:
            self.kill_event.wait(0.0001)
            if self.kill_event.is_set():
                break

            if self.start_event.is_set():
                # Keep the signal on for at least 0.1 s
                time.sleep(TIME_START_EVENT_ON)
                self.start_event.clear()

            if self.check_trigger():
                self.start_event.set()
                self.t = datetime.datetime.now()


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
        super().__init__()

    def check_trigger(self):
        """ Wait to receive the json file and reply with a simple "received"
        string. Add to the queue_trigger_params Queue the received dictionary,
        so that the experiment class can store it with the rest of the data.
        """
        self.lightsheet_config = self.zmq_socket.recv_json()
        self.queue_trigger_params.put(self.lightsheet_config)
        self.zmq_socket.send_json("received")

        return True

    def run(self):
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)
        self.zmq_socket.bind("tcp://*:{}".format(self.port))
        self.zmq_socket.setsockopt(zmq.RCVTIMEO, -1)

        super().run()


if __name__ == "__main__":
    port = "5555"
    trigger = ZmqTrigger(port)
    trigger.start()
