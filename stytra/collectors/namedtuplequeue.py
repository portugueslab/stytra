from multiprocessing import Queue
from collections import namedtuple


class NamedTupleQueue:
    def __init__(self, *args, **kwargs):
        self.q = Queue()
        self.tuple_type = None

    def put(self, t, obj, block=True, timeout=None):
        if self.tuple_type != type(obj):
            self.tuple_type = type(obj)
            self.q.put((t, ("_fieldnames",)+obj._fields), block=block, timeout=timeout)
        self.q.put((t, tuple(obj)), block=block, timeout=timeout)

    def get(self, block=True, timeout=-1):
        t, el = self.q.get(block=block, timeout=timeout)
        if self.tuple_type is None or el[0] == "_fieldnames":
            self.tuple_type = namedtuple("t", el[1:])
            t, obtained = self.q.get(block=block, timeout=timeout)
            return t, self.tuple_type(*obtained)
        else:
            return t, self.tuple_type(*el)


