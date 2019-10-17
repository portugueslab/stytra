#Note: We should look into refernece in all of these stimuli to figure
# out what they do and where it goes wrong
from stytra.stimulation.stimuli.visual import BackgroundStimulus
from stytra.stimulation.stimuli.visual import SeamlessImageStimulus
from stytra.stimulation.stimuli.closed_loop import FishTrackingStimulus

#TODO detangle background x,y,theta from fish x,y, theta with constant remaining
#TODO for that checking what they do in the mentioned stimuli above

class  RelativeBackgroundStimulus(BackgroundStimulus):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass

    def get_rot_transform(self, w, h):
        #Viims new defined fucntion. It could help in rewriting it
        return (
        QTransform()
            .translate(-self.x, -self.y)
            .rotate(self.theta * 180 / np.pi)
            .translate(self.x, self.y)
        )






















class ForwardMotion(SeamlessImageStimulus, FishTrackingStimulus):
    #The actual stimulus i want later
    # TODO seamlessimage stim inherits from background stim not
    #  reelative background stim, change before writing this or subclass this anew

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass