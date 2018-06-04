
from stytra.data_log import HasPyQtGraphParams
from random import sample
from stytra.stimulation.backgrounds import gratings
from itertools import product

from copy import deepcopy


class Protocol(HasPyQtGraphParams):
    """ The Protocol class is thought as an easily subclassable class that
     generate a list of stimuli according to some parameterization.
     It basically constitutes a way of keeping together:
      - the parameters that describe the protocol
      - the function to generate the list of stimuli.

     The function get_stimulus_list is the core of the class: it is called
     by the ProtocolRunner and it generates a list with the stimuli that
     have to be used in the protocol. Everything else concerning e.g.
     calibration, or asset directories that have to be passed to the
     stimulus, is handled in the ProtocolRunner class to leave this class
     as light as possible.
     """

    name = ''

    def __init__(self):
        """
        Add standard parameters common to all kind of protocols.
        """
        super().__init__(name='stimulus_protocol_params')

        for child in self.params.children():
            self.params.removeChild(child)

        self.add_params(name=self.name,
                        n_repeats=1,
                        pre_pause=0.,
                        post_pause=0.)


    def get_stimulus_list(self):
        """
        Generate protocol from specified parameters. Called by the
        ProtocolRunner class where the Protocol instance is defined.
        This function puts together the stimulus sequence defined by each
        child class with the initial and final pause and repeats it the
        specified number of times. It should not change in subclasses.
        """
        main_stimuli = self.get_stim_sequence()
        stimuli = []
        if self.params['pre_pause'] > 0:
            stimuli.append(Pause(duration=self.params['pre_pause']))

        for i in range(max(self.params['n_repeats'], 1)):
            stimuli.extend(deepcopy(main_stimuli))

        if self.params['post_pause'] > 0:
            stimuli.append(Pause(duration=self.params['post_pause']))

        return stimuli

    def get_stim_sequence(self):
        """ To be specified in each child class to return the proper list of
        stimuli.
        """
        return [Pause()]


class NoStimulation(Protocol):
    """ A protocol without stimulation
    """
    name = 'no stimulation'

    def __init__(self):
        super().__init__()
        self.add_params(duration=5)

    def get_stim_sequence(self):
        return [Pause(duration=self.params['duration'])]

