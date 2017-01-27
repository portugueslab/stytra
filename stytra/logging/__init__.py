from multiprocessing import Process, Queue
import pandas as pd
import datetime

class Logger:
    """Generic logger class. The idea is for it to have a 'source' to log
    and a 'destination', the final data collector. Additional methods are
    defined for printing the log or save it to  a csv file."""

    def __init__(self, log_print=True):
        self.log = []
        self.log_print = log_print

    def add_to_log(self, new_dict):
        if self.log_print:
            print(new_dict)
        self.log.append(new_dict)

    def save(self, destination='', file_format='csv'):
        log_df = pd.DataFrame(self.log)

        filename = destination + datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S")
        if file_format == 'csv':
            log_df.to_csv(self.destination)
        elif file_format == 'HDF5':
            log_df.to_hdf(self.destination, 'log')


class StimulusLogger(Logger):
    """ This class handles writing and saving logs for the stimulation protocol """

    def __init__(self, stim_protocol, destination=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Constructor

        :param stim_protocol: source to log with the class (Protocol object)
        :param destination: destination of the log (DataCollector object, optional)
        """
        self.destination = destination
        self.stim_protocol = stim_protocol

        # Connect the stim_change signal from the stimulation protocol to the update function.
        # This is called upon stimulus end.
        self.stim_protocol.sig_stim_change.connect(self.update_log)

        # Connect the protocol end signal with the function for sending the log to the collector.
        self.stim_protocol.sig_protocol_finished.connect(self.send_to_collector)

    def update_log(self):
        # Update with the data of the current stimulus:
        current_stim_dict = self.stim_protocol.stimuli[
            self.stim_protocol.i_current_stimulus].state()

        # Calculate starting and stopping time for the current stimulus
        t_start = self.stim_protocol.t - self.stim_protocol.current_stimulus.elapsed
        t_stop = self.stim_protocol.t

        self.add_to_log(dict(current_stim_dict, t_start=t_start, t_stop=t_stop))

    def send_to_collector(self):
        # TODO maybe
        # Something like
        # self.destination.add_entry('MetadataStimulus', 'protocol_log', self.log)
        pass
