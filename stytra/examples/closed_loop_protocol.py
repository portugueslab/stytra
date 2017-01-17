from stytra.logging import Logger
from stytra.gui import GetCoordsManual
from stytra.tracking import TailTracker
from stytra.stimulation.stimuli import Closed_loop_motion, Pause, Flash
from stytra.stimulation import StimulationProtocol
from stytra.gui import MonitoringWindow
from stytra.triggering import TtlTrigger


if __name__ == '__main__':

    log = Logger()

    camera_input = XimeaCamera()

    # set up the tail location
    tail_coordinates = GetCoordsManual(camera_input, eyes=False)

    # set up the tail recording

    tail_tracker = TailTracker(camera_input, tail_coordinates)

    # set up stimuli

    stimuli = [Pause(), Closed_loop_motion(gain=1, duration=0.5),
               Pause(duration=0.5), Flash(duration=0.05), Pause(duration=0.5),
               Flash(color=(255,0,0), duration=0.5)]

    protocol = StimulationProtocol(stimuli, tail_tracker, log)

    # set up gui

    gui = MonitoringWindow(tail_tracker, stimuli)

    trigger = TtlTrigger()
    trigger.triggered.connect(protocol.start)

