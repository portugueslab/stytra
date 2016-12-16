from stytra.tracking import track_tail


if __name__ == '__main__':

    log = Logger()

    camera_input = XimeaCamera()


    # set up the tail location
    tail_coordinates = GetCoordsManual(camera_input)

    # set up the tail recording

    tail_tracker = TailTracker(camera_input, tail_coordinates)

    # set up stimuli

    stimuli = [Pause(), Closed_loop_motion(gain=1, duration=0.5),
               Pause(duration=0.5), Flash(duration=0.05), Pause(duration=0.5), Flash(color=(255,0,0), duration=0.5)]

    protocol = StimulationProtocol(stimuli, tail_tracker, logger)


    # set up gui

    gui = MonitoringWindow(tail_tracker, stimuli)

    trigger = ttlTrigger()
    protocol.set_trigger(trigger)

