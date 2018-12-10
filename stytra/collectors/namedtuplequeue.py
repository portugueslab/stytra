from multiprocessing import Queue
from collections import namedtuple

class NamedTupleQueue:
    def __init__(self, *args, **kwargs):
        self.q = Queue()
        self.tuple_type = None

    def put(self, obj, block=True, timeout=None):
        if self.tuple_type != type(obj):
            self.tuple_type = type(obj)
            self.q.put(("_fieldnames",)+obj._fields, block=block, timeout=timeout)
        self.q.put(tuple(obj), block=block, timeout=timeout)

    def get(self, block=True, timeout=-1):
        el = self.q.get(block=block, timeout=timeout)
        if self.tuple_type is None or el[0] == "_fieldnames":
            self.tuple_type = namedtuple("t", el[1:])
            obtained = self.q.get(block=block, timeout=timeout)
            return self.tuple_type(*obtained)
        else:
            return self.tuple_type(*el)


