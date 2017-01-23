from multiprocessing import Process, Queue
import pandas as pd
import datetime


class Logger:
    """ This class handles writing and saving logs

    """
    def __init__(self, destination, stim_protocol, file_format='csv', log_print=True):
        """

        :param destination: log file path (string)
        :param stim_protocol: stimulation protocol (Protocol object)
        :param file_format: log file format (string) (optional)
        """
        self.destination = destination
        self.file_format = file_format
        self.stim_protocol = stim_protocol
        self.log_behavior = []
        self.log_stimuli = []

        self.log_print = log_print

        # Connect the stim_change signal from the stimulation protocol to the update function
        stim_protocol.sig_stim_change.connect(self.update_stimuli)

    def update_behavior(self, data):
        self.log_behavior.append(data)

    def update_stimuli(self):
        # Append the dictionary of the current stimulus:
        current_stim_dict = self.stim_protocol.stimuli[
            self.stim_protocol.i_current_stimulus].state()
        if self.log_print:
            print(current_stim_dict)

        self.log_stimuli.append(dict(current_stim_dict,
                                     t_start=self.stim_protocol.t - self.stim_protocol.current_stimulus.elapsed,
                                     t_stop=self.stim_protocol.t))

    def save(self):
        for log, logname in zip([self.log_behavior, self.log_stimuli],
                                ['behavior', 'stimuli']):
            log_df = pd.DataFrame(log)

            filename = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if self.file_format == 'csv':
                log_df.to_csv(self.destination) # TODO make datestamped filename
            elif self.file_format == 'HDF5':
                log_df.to_hdf(self.destination, 'log')
