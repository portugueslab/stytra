Data and metadata saving
========================

Data saving class in Stytra
---------------------------


Configuring Stytra for updating external database:
--------------------------------------------------
In addition to the JSON file, the metadata can be saved to a database, such as MongoDB.
For this, an appropriate database class has to be created and
passed to the Stytra class.

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
