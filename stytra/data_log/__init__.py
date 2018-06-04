from pyqtgraph.parametertree import Parameter
from stytra.dbconn import sanitize_item


from pyqtgraph.pgcollections import OrderedDict


def strip_values(it):
    if isinstance(it, OrderedDict) or isinstance(it, dict):
        new_dict = dict()
        for key, value in it.items():
            if not key == 'value':
                new_dict[key] = strip_values(value)
        return new_dict
    else:
        return it


class HasPyQtGraphParams(object):
    """
    This class is used to have a number of objects (experiment interfaces and
    protocols) sharing a global pyqtgraph Parameter object that will be used
    for saving data_log and restoring the app to the last used state.
    _params is a class attribute and is shared among all subclasses; each
    subclass will have an alias, params, providing access to its private
    parameters.
    """
    _params = Parameter.create(name='global_params', type='group')

    def __init__(self, name=None):
        """ Create the params of the instance and add it to the global _params
        of the class. If the name passed already exists in the tree, it will be
        overwritten.
        :param name: Name for the tree branch where this parameters are stored.
                     If nothing is passed, child class name will be used.
        """

        if name is None:
            name = self.__class__.__name__

        self.params = Parameter.create(name=name,
                                       type='group')

        existing_children = self._params.children()

        # WARNING!!
        # Here there can be undesired emissions of the StateChanged signal!
        # If you are removing a child params, it will emit a signal you have
        # to block.
        for child in existing_children:
            if child.name() == name:
                self._params.removeChild(child)

        self._params.addChild(self.params)

    def set_new_param(self, name, value, get_var_type=True):
        """ Easy set for new parameters.
        :param name: name of new parameter
        :param value: either a value entry or a dictionary of valid keys
                      for a parameter (e.g. type, visible, editable, etc.)
        :param get_var_type: if True, value type will be set as parameter type
        :return:
        """
        if isinstance(value, dict):  # Allows passing dictionaries:
            entry_dict = {'name': name}  # add name
            entry_dict.update(value)
            self.params.addChild(entry_dict)
        else:
            if get_var_type:  # if specification of type is required, infer it
                self.params.addChild({'name': name, 'value': value,
                                      'type': type(value).__name__})
            else:
                self.params.addChild({'name': name, 'value': value})

    def get_clean_values(self):
        return sanitize_item(self.params.getValues(), paramstree=True)
