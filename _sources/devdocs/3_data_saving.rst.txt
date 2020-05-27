Data and metadata saving
========================

The design of Stytra encourages automatic data management. A dedicated :class:`DataCollector <stytra.collectors.data_collector.DataCollector>` object is used to log the metadata about the experiment. Parameters from the entire program are appended to a single hierarchical parameter tree, which is saved at the end of the experiment. Quantities in the tree can come from different sources. Firstly, parameters can be added at any point in the code. For example, at every run the current version number of Stytra and git commit are detected and saved, together with the versions of the dependencies. Secondly, many of the key objects of Stytra (tracking nodes, display and camera controllers...) are parametrized though a custom parameters package (:ref:`lightparam <parameters>`). When constructing them, one needs to pass the parameter tree that collects the data. This ensures that all quantities needed to replicate the experiment are collected within the metadata file. Finally, dedicated parametrized objects can be used to manually input metadata concerning the animal (age, genotype, etc.) or the experiment (setup, session, etc.). These classes can be customized to automatically include lab-specific metadata options, such as setup identifiers or animal lines (examples for this customization are provided in the documentation).

Various logs accompanying the experiment run (state of the stimuli, the raw tracking variables and the estimated state of the fish) are saved as tabular data. The supported data formats are CSV, HDF5 and Feather, but others could be added as long as they provide an interface to the Pandas library. To demonstrate the convenience of the data and metadata saving methods of Stytra, we made `example data <https://zenodo.org/record/1692080>`_ available together with `Jupyter notebooks <https://github.com/portugueslab/example_stytra_analysis>`_ for the analyses that can reproduce the figures in this paper. Finally, a central experiment database can be connected to keep track of all the experiments in a lab or institute, as described below.


Implementation notes
--------------------

All streaming data (tracking, stimulus state) is collected by subclasses of the :class:`Accumulator <stytra.collectors.accumulators.Accumulator>`
Accumulators collect named tuples of data and timing of data points. If the data format changes, the accumulator resets.

All other data (animal metadata, configuration information, GUI state etc. is collected inside the Experiment class via tha :class:`DataCollector <stytra.collectors.data_collector.DataCollector>`


Configuring Stytra for updating external database:
--------------------------------------------------
In addition to the JSON file, the metadata can be saved to a database, such as MongoDB.
For this, an appropriate database class has to be created and
passed to the Stytra class. This example uses PyMongo

Example::

    from stytra.utilities import Database, prepare_json
    import pymongo


    class PortuguesDatabase(Database):
        def __init__(self):
            # in the next line you have to put in the IP address and port of the
            # MongoDB instance
            self.client = pymongo.MongoClient("mongodb://192.???.???.???:????")
            # the database and collection are created in MongoDB before
            # the first use
            self.db = self.client.experiments
            self.collection = self.db["experiments"]

        def insert_experiment_data(self, exp_dict):
            """ Puts a record of the experiment in the default lab MongoDB database

            :param exp_dict: a dictionary from the experiment data collector
            :return: the database id of the inserted item
            """

            # we use the prepare_json function to clean the dictionary
            # before inserting into the database

            db_id = self.collection.insert_one(
                prepare_json(exp_dict, eliminate_df=True)
            ).inserted_id
            return str(db_id)
