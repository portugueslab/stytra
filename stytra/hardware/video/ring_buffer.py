import numpy as np


class RingBuffer:
    def __init__(self, length):
        self.length = length
        self.arr = None
        self.insert_idx = 0
        self.read_idx = 0

    def put(self, item):
        if (
            self.arr is None
            or self.arr.shape[1:] != item.shape
            or self.arr.dtype != item.dtype
        ):
            self.arr = np.empty((self.length,) + item.shape, item.dtype)

        self.arr[self.insert_idx] = item
        self.insert_idx = (self.insert_idx + 1) % self.length

    def get(self):
        if self.arr is None:
            raise ValueError("Trying to get an item from an empty buffer")
        old_idx = self.read_idx
        self.read_idx = (self.read_idx + 1) % self.length
        return self.arr[old_idx]

    def get_most_recent(self):
        return self.arr[(self.insert_idx-1) % self.length]
