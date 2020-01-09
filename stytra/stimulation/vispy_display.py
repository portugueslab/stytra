import vispy
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from multiprocessing import Process
from vispy.app import Application as VisApp
from vispy import scene, app
from time import process_time_ns


class Circle:
    def __init__(self, scene):
        self.scene = scene
        self.circle = scene.visuals.Ellipse(
            center=(100, 100), color="white", parent=scene, radius=(10, 10)
        )

    def update(self, t):
        self.circle = None


stim_dict = dict(circle=Circle)


class DisplayProcess(Process):
    def __init__(self):
        super().__init__()
        self.el = None
        self.txt = None
        self.prev_time = None
        self.stim = None
        self.canvas = None
        self.scene = None
        self.protocol = None

    def run(self) -> None:
        vispy.use("Glfw")
        self.canvas = scene.SceneCanvas(size=(800, 600), show=True)
        view = self.canvas.central_widget.add_view()
        self.scene = view.scene
        self.el = scene.visuals.Ellipse(
            center=(100, 100), color="white", parent=view.scene, radius=(10, 10)
        )
        self.txt = scene.visuals.Text(parent=view.scene, color="white", pos=(40, 40))
        self.timer = app.Timer("auto", connect=self.update, start=True)
        app.run()

    def set_protocol(self):
        pass

    def update(self, *args):
        ctime = process_time_ns()
        if self.prev_time is not None:
            dif = ctime - self.prev_time
            if dif > 0:
                fps = 1e9 / dif
                self.txt.text = "FPS: {:.2f}".format(fps)
        self.prev_time = ctime

    # def deserialize_stim(self, stim, stim_params):
    #     self.stim = stim_dict[stim_params](scene=self.scene, **stim_params)


if __name__ == "__main__":
    app = QApplication([])
    dp = DisplayProcess()
    wid = QWidget()
    wid.show()
    dp.start()
    app.exec_()
