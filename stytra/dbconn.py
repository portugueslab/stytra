import pymongo
import numpy as np
import datetime
import time
import pandas as pd

import numpy as np
import datetime
import requests
import json


class Slacker:
    """ Class which posts updates on slack

    """
    def __init__(self):
        # set up slack notifications
        self.slack_message = dict(username='pythonbot', channel='#experiment_progress', text='Hello there from python!', icon_emoji=':robot_face:')
        self.slack_headers = {'content-type': 'application/json'}
        self.slack_url = 'https://hooks.slack.com/services/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'

    def post_update(self, text):
        self.slack_message['text'] = text
        print(text)
        return requests.post(self.slack_url, data=json.dumps(self.slack_message),
                             headers=self.slack_headers)


def sanitize_item(it, **kwargs):
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
            new_dict[key] = sanitize_item(value, **kwargs)
        return new_dict
    if isinstance(it, tuple):
        tuple_out = tuple([sanitize_item(el, **kwargs)
                           for el in it])
        if len(tuple_out) == 2 and kwargs['paramstree'] and \
                isinstance(tuple_out[1], dict):
            if len(tuple_out[1]) == 0:
                return tuple_out[0]
            else:
                return tuple_out[1]
        else:
            return tuple_out
    if isinstance(it, list):
        return [sanitize_item(el, **kwargs) for el in it]
    if isinstance(it, np.generic):
        return np.asscalar(it)
    if isinstance(it, datetime.datetime):
        if kwargs["convert_datetime"]:
            return it.isoformat()
        else:
            temptime = time.mktime(it.timetuple())
            return datetime.datetime.utcfromtimestamp(temptime)
    if isinstance(it, pd.DataFrame):
        if kwargs["eliminate_df"]:
            return 0
        else:
            return it.to_dict('list')
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
