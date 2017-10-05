import pymongo
import numpy as np
import datetime
import time


def sanitize_item(it):
    """ Used to create a dictionary which will be safe to put in MongoDB

    :param it: the item which will be recursively sanitized
    :return:
    """
    safe_types = (int, float, str)
    for st in safe_types:
        if isinstance(it, st):
            return it
    if isinstance(it, dict):
        new_dict = dict()
        for key, value in it.items():
            new_dict[key] = sanitize_item(value)
        return new_dict
    if isinstance(it, tuple):
        return tuple([sanitize_item(el) for el in it])
    if isinstance(it, list):
        return [sanitize_item(el) for el in it]
    if isinstance(it, np.generic):
        return np.asscalar(it)
    if isinstance(it, datetime.datetime):
        temptime = time.mktime(it.timetuple())
        return datetime.datetime.utcfromtimestamp(temptime)
    return 0


def put_experiment_in_db(exp_dict):
    """ Puts a record of the experiment in the default lab MongoDB database

    :param exp_dict: a dictionary from the experiment data collector
    :return: the database id of the inserted item
    """
    new_dict = sanitize_item(exp_dict)
    client = pymongo.MongoClient('mongodb://192.168.235.12:27017')
    db = client.experiment_database
    collection = db['experiments']
    db_id = collection.insert_one(new_dict).inserted_id
    return str(db_id)
