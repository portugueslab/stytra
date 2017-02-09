from PyQt5.QtCore import QTimer
import pyqtgraph as pg


class StramingPlotWidget(pg.GraphicsLayoutWidget):
    def __init__(self, *args, diagnostic_queue, dt=1/100, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunkSize = 100
        self.updateTimer = QTimer()
        self.updateTimer.setSingleShot(False)
        self.updateTimer.timeout.connect(self.update)
        self.timer.start(dt)

        # initialise the widgets
        self.streamplot = pg.PlotCurveItem()
        self.addItem(self.streamplot)


    def update(self):
        chunkSize = 100
        # Remove chunks after we have 10
        maxChunks = 10
        startTime = pg.ptime.time()
        win.nextRow()
        curves = []
        data5 = np.empty((chunkSize + 1, 2))
        ptr5 = 0

        def update3():
            global p5, data5, ptr5, curves
            now = pg.ptime.time()
            for c in curves:
                c.setPos(-(now - startTime), 0)

            i = ptr5 % chunkSize
            if i == 0:
                curve = p5.plot()
                curves.append(curve)
                last = data5[-1]
                data5 = np.empty((chunkSize + 1, 2))
                data5[0] = last
                while len(curves) > maxChunks:
                    c = curves.pop(0)
                    p5.removeItem(c)
            else:
                curve = curves[-1]
            data5[i + 1, 0] = now - startTime
            data5[i + 1, 1] = np.random.normal()
            curve.setData(x=data5[:i + 2, 0], y=data5[:i + 2, 1])
            ptr5 += 1

