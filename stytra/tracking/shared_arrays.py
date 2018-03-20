from multiprocessing import Queue, Array
import numpy as np


class ArrayQueue:
    def __init__(self, maxsize=0):
        self.dtype = None
        self.shape = None
        self.byte_count = None

        self.maxsize = maxsize

        # make a pool of numpy arrays, each backed by shared memory,
        # and create a queue to keep track of which ones are free
        self.array_pool = [None] * maxsize
        self.free_arrays = Queue(maxsize)

        self.q = Queue(maxsize)

        self.initialized = False

    def initialize_shared(self, template):
        self.dtype = template.dtype
        self.shape = template.shape
        self.byte_count = len(template.data)
        self.array_pool = [None] * self.maxsize
        for i in range(self.maxsize):
            buf = Array('c', self.byte_count, lock=False)
            self.array_pool[i] = np.frombuffer(buf, dtype=self.dtype).reshape(self.shape)
            self.free_arrays.put(i)
        self.initialized = True

    def put(self, item, *args, **kwargs):
        if type(item) is np.ndarray:
            if self.initialized is False or item.shape != self.array_pool[0].shape:
                self.initialize_shared(item)
            if item.dtype == self.dtype and item.shape == self.shape and len(item.data)==self.byte_count:
                # get the ID of an available shared-memory array
                id = self.free_arrays.get()
                # copy item to the shared-memory array
                self.array_pool[id][:] = item
                # put the array's id (not the whole array) onto the queue
                new_item = id
            else:
                raise ValueError(
                    'ndarray does not match type or shape of template used to initialize ArrayQueue'
                )
        else:
            # not an ndarray
            # put the original item on the queue (as a tuple, so we know it's not an ID)
            new_item = (item,)
        self.q.put(new_item, *args, **kwargs)

    def get(self, *args, **kwargs):
        item = self.q.get(*args, **kwargs)
        if type(item) is tuple:
            # unpack the original item
            return item[0]
        else:
            # item is the id of a shared-memory array
            # copy the array
            arr = self.array_pool[item].copy()
            # put the shared-memory array back into the pool
            self.free_arrays.put(item)
            return arr


class __EndToken:
    pass