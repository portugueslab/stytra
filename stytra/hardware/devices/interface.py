class Board:
    """Abstract class for controlling I/O voltage boards.

    """

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        """

    def start_ao_task(self):
        """Initialize device"""

    def write(self):
        """Write value in pin"""

    def read(self):
        """Read value from pin"""
