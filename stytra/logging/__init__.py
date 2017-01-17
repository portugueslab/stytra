from multiprocessing import Process, Queue
import pandas as pd


class Logger:
    """ This class handles writing and saving logs

    """
    def __init__(self, destination, file_format='csv'):
        self.destination = destination
        self.file_format = file_format
        self.log_behavior = []
        self.log_stimuli = []

    def update_behavior(self, data):
        self.log_behavior.append(data)

    def update_stimuli(self, data):
        self.log_stimuli.append(data)

    def save(self):
        for log, logname in zip([self.log_behavior, self.log_stimuli],
                                ['behavior', 'stimuli']):
            log_df = pd.DataFrame(log)
            if self.file_format == 'csv':
                log_df.to_csv(self.destination) # TODO make datestamped filename
            elif self.file_format == 'HDF5':
                log_df.to_hdf(self.destination, 'log')

