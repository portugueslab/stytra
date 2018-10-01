import datetime
import os
import deepdish as dd
import numpy as np
import pandas as pd
import json

from copy import deepcopy
from pyqtgraph.parametertree import Parameter
from pyqtgraph.pgcollections import OrderedDict

from stytra.utilities import prepare_json

try:
    import dictdiffer  # optional dependency, for debugging
except ImportError:
    pass


def strip_values(it):
    """Convert OrderedDict of OrderedDict in dict of dict.

    Parameters
    ----------
    it :
        return:

    Returns
    -------

    """
    if isinstance(it, OrderedDict) or isinstance(it, dict):
        new_dict = dict()
        for key, value in sorted(it.items()):
            if not key == "value":
                new_dict[key] = strip_values(value)
        return new_dict
    else:
        return it


def metadata_dataframe(metadata_dict, time_step=0.005):
    """Function for converting a data_log dictionary into a pandas DataFrame
    for saving.

    Parameters
    ----------
    metadata_dict :
        data_log dictionary (containing stimulus log!)
    time_step :
        time step (used only if tracking is not present!) (Default value = 0.005)

    Returns
    -------
    type
        a pandas DataFrame with a 'stimulus' column for the stimulus

    """

    # Check if tail tracking is present, to use tracking dataframe as template.
    # If there is no tracking, generate a dataframe with time steps specified:
    if "tail" in metadata_dict["behaviour"].keys():
        final_df = metadata_dict["behaviour"]["tail"].copy()
    else:
        t = metadata_dict["stimulus"]["log"][-1]["t_stop"]
        timearr = np.arange(0, t, time_step)
        final_df = pd.DataFrame(timearr, columns=["t"])

    # Control for delays between tracking and stimulus starting points:
    delta_time = 0
    if "tail_tracking_start" in metadata_dict["behaviour"].keys():
        stim_start = metadata_dict["stimulus"]["log"][0]["started"]
        track_start = metadata_dict["behaviour"]["tail_tracking_start"]
        delta_time = (stim_start - track_start).total_seconds()

    # Assign in a loop a stimulus to each time point
    start_point = None
    for stimulus in metadata_dict["stimulus"]["log"]:
        if stimulus["name"] == "start_acquisition":
            start_point = stimulus

        final_df.loc[
            (final_df["t"] > stimulus["t_start"] + delta_time)
            & (final_df["t"] < stimulus["t_stop"] + delta_time),
            "stimulus",
        ] = str(stimulus["name"])

    # Check for the 'start acquisition' which run for a very short time and
    # can be missed:
    if start_point:
        start_idx = np.argmin(abs(final_df["t"] - start_point["t_start"]))
        final_df.loc[start_idx, "stimulus"] = "start_acquisition"

    return final_df


class DataCollector:
    """Class for saving all data and data_log produced during an experiment.

    There are two kind of data that are collected:

        - Metadata/parameters: values that should restored from previous
          sessions. These values don't have to be explicitely added.
          they are automatically read from all the objects
          in the stytra Experiment process which are
          instances of HasPyQtGraphParams.
        - Static data: (tail tracking, stimulus log...), that should not
          be restored. Those have to be added one by one
          via the add_data_source() method.


    Inputs from both types of sources are eventually saved in the .json file
    containing all the information from the experiment.
    In this file data are divided into fixed categories:

        - general: info about the experiment (date, setup, session...)
        - animal: info about the animal (line, age, etc.)
        - stimulus: info about the stimulation (stimuli log, screen
          dimensions, etc.)
        - imaging: info about the connected microscope, if present
        - behaviour: info about fish behaviour (tail log...)
        - camera: parameters of the camera for behaviour, if one is present
        - tracking: parameters for tracking


    See documentation of the clean_data_dict() method for a description
    of conventions for dividing the entries among the categories.
    In the future this function may structure its output in other standard
    formats for scientific data (e.g., NWB).

    In addition to the .json file, data_log and parameters from
    HasPyQtGraphParams objects are stored in a config.h5 file (located in the
    experiment directory) which is used for restoring the last configuration
    of the GUI and of the experiment parameters.

    Parameters
    ----------
    data_tuples_list : tuple
        (optional) tuple of data to be added
    folder_path : str
        destination where the final json file will be sabed

    Returns
    -------

    """

    def __init__(self, *data_tuples_list, folder_path="C:/"):
        """ """

        # Check validity of directory:
        if os.path.isdir(folder_path):
            if not folder_path.endswith("/"):
                folder_path += "/"
            self.folder_path = folder_path
        else:
            raise ValueError("The specified directory does not exist!")

        # Try to find previously saved data_log:
        self.last_metadata = None
        list_metadata = sorted(
            [fn for fn in os.listdir(folder_path) if fn.endswith("config.h5")]
        )

        if len(list_metadata) > 0:
            self.last_metadata = dd.io.load(folder_path + list_metadata[-1])

        self.log_data_dict = dict()
        self.params_metadata = None
        # Add all the data tuples provided upon instantiation:
        for data_element in data_tuples_list:
            self.add_static_data(*data_element)

    def restore_from_saved(self):
        """If a config.h5 file is available, use the data there to
        restore the state of the HasPyQtGraph._params tree to last
        session values.
        Before, we make sure that the dictionary that we try to restore
        differs from our parameter structure only in the values.
        Without this control, changing any of the parameters in the code
        could result in bugs and headaches due to the change of the values
        from a config.h5 file from the previous program version.

        Parameters
        ----------

        Returns
        -------

        """
        if self.last_metadata is not None:
            # Make clean dictionaries without the values:
            current_dict = strip_values(self.params_metadata.saveState())
            prev_dict = strip_values(self.last_metadata)

            # Restore only if equal:
            if current_dict == prev_dict:
                self.params_metadata.restoreState(self.last_metadata, blockSignals=True)
                # Here using the restoreState of the _params for some reason
                #  does not block signals coming from restoring the values
                # of its params children.
                # This means that functions connected to the treeStateChange
                # of the params of HasPyQtGraphParams instances may be called
                # multiple times.
            else:
                print("The parameter configuation has been changed, resetting: ",
                      list(dictdiffer.diff(current_dict, prev_dict)))


    def add_param_tree(self, params_tree):
        """Add the params tree that will be used for reading and restoring
        the parameters from the previous session.
        It should be the HasPyQtGraph._params tree for it to
        contain all the params branches in all the different experiment objects.

        Parameters
        ----------
        params_tree :


        Returns
        -------

        """
        if isinstance(params_tree, Parameter):
            self.params_metadata = params_tree
            # self.restore_from_saved()  # restoring is called by experiment
            # at a different time!
        else:
            print("Invalid params source passed!")

    def add_static_data(self, entry, name="unspecified_entry"):
        """Add new data to the dictionary.

        Parameters
        ----------
        entry :
            data that will be stored;
        name : str
            name in the dictionary. It should take the form
            "category_name",
            where "category" should be one of the possible keys
            of the dictionary produced in get_clean_dict() (animal, stimulus, *etc.*).
            (Default value = 'unspecified_entry')

        Returns
        -------

        """
        self.log_data_dict[name] = entry

    def get_clean_dict(
        self, paramstree=True, eliminate_df=False, convert_datetime=False
    ):
        """Collect data from all sources and put them together in
        the final hierarchical dictionary that will be saved in the .json file.
        The first level in the dictionary is fixed and defined by the keys
        of the clean_data_dict that will be returned. data from all sources
        are divided in these categories according to the key preceding the
        underscore in their name (e.g., value of general_db_idx will be put in
        ['general']['db_idx']).

        Parameters
        ----------
        paramstree :
            see sanitize_item docs; (Default value = True)
        eliminate_df : bool
            see sanitize_item docs; (Default value = False)
        convert_datetime : bool
            see sanitize_item docs; (Default value = False)

        Returns
        -------
        dict :
            dictionary with the sorted data.

        """
        clean_data_dict = dict(
            animal={},
            stimulus={},
            imaging={},
            behaviour={},
            general={},
            camera={},
            tracking={},
            unassigned={},
        )

        # Params data_log:
        value_dict = deepcopy(self.params_metadata.getValues())

        # Static data dictionary:
        value_dict.update(deepcopy(self.log_data_dict))

        for key in value_dict.keys():
            category = key.split("_")[0]
            value = prepare_json(
                value_dict[key],
                paramstree=paramstree,
                convert_datetime=convert_datetime,
                eliminate_df=eliminate_df,
            )
            if category in clean_data_dict.keys():
                split_name = key.split("_")
                if split_name[1] == "metadata":
                    clean_data_dict[category] = value
                else:
                    clean_data_dict[category]["_".join(split_name[1:])] = value
            else:
                clean_data_dict["unassigned"][key] = value

        return clean_data_dict

    def get_last_value(self, class_param_key):
        """Get the last saved value for a specific class_param_key.

        Parameters
        ----------
        class_param_key : str
            name of the parameter whose value is required.


        Returns
        -------
        - :
            value of the parameter in the config.h5 file.

        """
        if self.last_metadata is not None:
            # This syntax is ugly but apparently necessary to scan through
            # the dictionary saved by pyqtgraph.Parameter.saveState().
            return self.last_metadata["children"][class_param_key]["children"]["name"][
                "value"
            ]
        else:
            return None

    def save_config_file(self):
        """Save the config.h5 file with the current state of the params
        data_log.

        Parameters
        ----------

        Returns
        -------

        """
        dd.io.save(self.folder_path + "config.h5", self.params_metadata.saveState())

    def save_json_log(self, output_path):
        """Save the .json file with all the data from both static sources
        and the updated params.

        Parameters
        ----------
        timestamp :
             (Default value = None)

        Returns
        -------

        """
        clean_dict = self.get_clean_dict(convert_datetime=True)

        with open(output_path, "w") as outfile:
            json.dump(clean_dict, outfile, sort_keys=True)

    def save(self, output_path=""):
        """Save both the data_log.json log and the config.h5 file

        Parameters
        ----------
        output_path :
             (Default value = "")
             Path where to save the metadata

        Returns
        -------

        """

        self.save_json_log(output_path)
        self.save_config_file()
