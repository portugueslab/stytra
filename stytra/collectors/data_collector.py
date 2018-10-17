import os
import json

import deepdish as dd
import numpy as np
import pandas as pd

from pathlib import Path
from lightparam import ParameterTree
from stytra.utilities import prepare_json


class DataCollector(ParameterTree):
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
        - behaviour: info about fish behaviour (tail log...) and parameters for tracking
        - camera: parameters of the camera for behaviour, if one is present


    See documentation of the clean_data_dict() method for a description
    of conventions for dividing the entries among the categories.
    In the future this function may structure its output in other standard
    formats for scientific data (e.g., NWB).

    In addition to the .json file, parameters from
    Parametrized objects are stored in a config.h5 file (located in the
    experiment directory) which is used for restoring the last configuration
    of the GUI and of the experiment parameters.

    Parameters
    ----------
    data_tuples_list : tuple
        (optional) tuple of data to be added
    folder_path : str
        destination where the final json file will be saved

    Returns
    -------

    """

    def __init__(self, *data_tuples_list, folder_path="C:/"):
        """ """
        super().__init__()
        self.metadata_fn = "config.h5"

        # Check validity of directory:
        self.folder_path = Path(folder_path)
        if not self.folder_path.is_dir():
            self.folder_path.mkdir(parents=True)

        # Try to find previously saved data_log:
        self.last_metadata = None
        metadata_files = list(self.folder_path.glob("*" + self.metadata_fn))
        if metadata_files:
            self.last_metadata = dd.io.load(str(metadata_files[0]))

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
            self.deserialize(self.last_metadata)

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

    def get_clean_dict(self, **kwargs):
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
        clean_data_dict = self.serialize()
        clean_data_dict.update(self.log_data_dict)
        return prepare_json(clean_data_dict, **kwargs)

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
        return None

    def save_config_file(self):
        """Save the config.h5 file with the current state of the params
        data_log.

        Parameters
        ----------

        Returns
        -------

        """
        dd.io.save(str(self.folder_path / "config.h5"), self.serialize())

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
