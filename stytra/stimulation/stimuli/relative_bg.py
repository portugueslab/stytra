# Look again after Vilim's refactoring

# Note: We should look into refernece in all of these stimuli to figure
# out what they do and where it goes wrong
from stytra.stimulation.stimuli.visual import BackgroundStimulus
from stytra.stimulation.stimuli.visual import SeamlessImageStimulus
from stytra.stimulation.stimuli.closed_loop import FishTrackingStimulus

# TODO detangle background x,y,theta from fish x,y, theta with constant remaining
# TODO for that checking what they do in the mentioned stimuli above
# TODO maybe program a GUI to show and rotate the stimulus in a controlled fashion
# TODO get a fish video snippet where the fish behaves well for testing


class RelativeBackgroundStimulus(BackgroundStimulus):
    """ This background shoudl be fully controllable on where it is placed.
    It shoudl transform AND translate with the fish.
    It should have a:
     1) TRUE center = its own stimulus center (0,0)
     2) RELATIVE center which can be set arbituary (e.g. to the fish) (fish x,y).
     This relative center needs a kind of translation from fish coords
     and maybe is also related to true center
     3) Theta  which can be set """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass

    def get_rot_transform(self, w, h):
        # Viims new defined fucntion for my stytra config code. It could help in rewriting it
        return (
            QTransform()
            .translate(-self.x, -self.y)
            .rotate(self.theta * 180 / np.pi)
            .translate(self.x, self.y)
        )


class ForwardMotion(SeamlessImageStimulus, FishTrackingStimulus):
    # The actual stimulus i want later
    # TODO seamlessimage stim inherits from background stim not
    #  reelative background stim, change before writing this or subclass this anew

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass
