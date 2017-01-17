from stytra.logging import Logger
from stytra.gui import GetCoordsManual
from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol

if __name__ == '__main__':

    log = Logger()

    stim_duration = 0.5
    pause_duration = 1
    n_repeats = 10
    flash_color = (255, 0, 0)
    refresh_rate = 1/60.

    stimuli = []

    for i in range(n_repeats):
        stimuli.append(Pause(duration=pause_duration))
        stimuli.append(Flash(duration=stim_duration, color=flash_color))

    protocol = Protocol(stimuli, refresh_rate)

    protocol.sig_timestep.connect(log.update_stimuli)