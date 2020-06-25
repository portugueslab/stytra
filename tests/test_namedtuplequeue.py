from stytra.collectors.namedtuplequeue import NamedTupleQueue
from multiprocessing import Process
from collections import namedtuple
from time import sleep


class TupProc(Process):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.q.tuple_type = None

    def run(self):
        _, m = self.q.get(timeout=1.0)
        mtype = type(m)
        self.q.put(None, mtype(m[0] + 1, *m[1:]))


def test_ntqueue():
    t = namedtuple("t", "a b c")
    q = NamedTupleQueue()

    tup = t(1, 2, 3)
    tp = TupProc(q)
    tp.start()
    tp.q.put(None, tup)
    print("started sleeping")
    sleep(0.1)
    print("stopped sleeping")
    #
    tp.join()
    _, tup2 = tp.q.get()
    assert tup2 == t(2, 2, 3)
