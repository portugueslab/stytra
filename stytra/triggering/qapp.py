from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from pathlib import Path
import datetime
import time


class QtTrigger(QObject):
    start_sig = pyqtSignal()

    def __init__(self, pathname):
        super().__init__()
        self.path = Path(pathname)
        self.files_n = len(list(self.path.glob('*')))

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_trig)  # connect timer to update fun
        self.timer.setSingleShot(False)
        self.timer.start()  # start the timer

    def check_trig(self):
        n = len(list(self.path.glob('*')))
        time.sleep(1)
        if n != self.files_n:
            self.files_n = n
            self.start_sig.emit()


class QtReceiver(QObject):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self.signal.connect(self.trigger)  # connect timer to update fun

        self.timer = QTimer()
        self.timer.timeout.connect(self.my_own_business)
        self.timer.setSingleShot(False)
        self.timer.start()  # start the timer

        self.t = datetime.datetime.now()
        self.k = 0

    def my_own_business(self):
        self.k += 1
        diff = datetime.datetime.now() - self.t
        self.t = datetime.datetime.now()

        if self.k == 10:
            self.k = 0
            print('my own business takes {}'.format(diff.microseconds))

    def trigger(self):
        print('Triggered!!!!')


if __name__ == '__main__':
    app = QApplication([])
    a = QtTrigger(pathname=r'C:\Users\lpetrucco\Desktop\dummydir')
    b = QtReceiver(a.start_sig)
    app.exec_()
