import vispy
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from multiprocessing import Process
from vispy.app import Application as VisApp
from vispy import scene
import time
import numpy as np
import pandas as pd


class Protocol:
    def __init__(self, n_repeats=10):
        self.n_repeats = n_repeats

    def get_stim_sequence(self, scene):
        pass

    def get_list_sequence(self, scene):
        stim_brick = self.get_stim_sequence(scene)
        stimuli = []
        for _ in range(self.n_repeats):
            stimuli.extend(stim_brick)
        return stimuli


class Stimulus:
    def __init__(self, scene=None, duration=1):
        self.scene = scene
        self.circle = None
        self.duration = duration
        self.name = 'stimulus'
        self.color = (0, 0, 0)
        self.w = self.scene.canvas.physical_size[0]
        self.h = self.scene.canvas.physical_size[1]
        self.x = 100
        self.y = 100
        self._elapsed = None
        self._elapsed = 0
        self.stimulus = None
        self.running = False

    def paint(self, t):
         self._elapsed = t

    def start(self):
        self.running = True


class InterpolatedStimulus(Stimulus):
    """Stimulus that interpolates its internal parameters with a data frame

    Parameters
    ----------
    df_param : DataFrame
        A Pandas DataFrame containing the values to be interpolated
        it has to contain a column named t for the defined time points,
        and additional columns for each parameter of the stimulus that is
        to be changed.
        A constant velocity of the parameter change can be specified,
        in that case the column name has to be prefixed with "vel_"

        Example:
        t | x
        -------
        0 | 1.0
        4 | 7.8

    """

    def __init__(self, *args, df_param=None, **kwargs):
        """"""
        super().__init__(**kwargs)
        #self.dynamic_parameters.append("current_phase")
        self.df_param = df_param
        self.duration = float(df_param.t.iat[-1])
        self.phase_times = np.unique(df_param.t)
        self.current_phase = 0
        self._past_t = 0
        self._dt = 1 / 60.0

    def update(self):
        """ """
        # to use parameters defined as velocities, we need the time
        # difference before previous display
        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed

        # the phase has to be found by searching, as there are situation where it does not always increase
        self.current_phase = np.searchsorted(self.phase_times, self._elapsed) - 1

        for col in self.df_param.columns:
            if col != "t":
                # for defined velocities, integrates the parameter
                if col.startswith("vel_"):
                    setattr(
                        self,
                        col[4:],
                        getattr(self, col[4:])
                        + self._dt
                        * np.interp(self._elapsed, self.df_param.t, self.df_param[col]),
                    )
                # otherwise it is set by interpolating the column of the
                # dataframe
                # else:
                setattr(
                    self,
                    col,
                    np.interp(self._elapsed, self.df_param.t, self.df_param[col]),
                )


class BackgroundStimulus(Stimulus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_tile_ranges(self, imw, imh, w, h):
        n_tiles = int(w / imw)
        pos = np.arange(imw/2, imw * (n_tiles - 1), imw)
        return n_tiles, pos


class MovingGratings(BackgroundStimulus):
    def __init__(self, grating_period=10, **kwargs):
        super().__init__(**kwargs)
        self.name = 'grating'
        self.grating_period = grating_period
        self.stimulus = []
        n_tiles, pos = self.get_tile_ranges(self.grating_period, self.h, self.w, self.h)
        for i in range(n_tiles - 1):
            print(i)
            if i % 2 > 0: color = (1, 1, 1)
            else: color = (0, 0, 0)
            self.stimulus.append(vispy.scene.visuals.Rectangle(
                center=(pos[i], self.h / 2),
                color=self.color,
                parent=self.scene,
                name=self.name
            )
            )
            self.stimulus.visible = False

    def paint(self, t):
        self._elapsed = t
        self.stimulus.visible = True



class Circle(InterpolatedStimulus):
    def __init__(self, color=(1, 1, 1), w=10, h=10, duration=1.0, **kwargs):
        super().__init__(**kwargs)
        self.circle = None
        self.duration = duration
        self.name = 'circle'
        self.color = color
        self.w = w
        self.h = h
        # self.stimulus = vispy.scene.visuals.Markers(edge_color=self.color,
        #                                             face_color=self.color,
        #                                             size=15,
        #                                             parent=self.scene)
        self.stimulus = vispy.scene.visuals.Ellipse(
            center=(self.x, self.y),
            color=self.color,
            parent=self.scene,
            radius=(self.w, self.h),
            name=self.name
        )
        self.stimulus.visible = False

    def paint(self, t):
        if self.running is False:
            self.start()
        else:
            self._elapsed = t
            if hasattr(self, 'df_param'):
                self.update()
        self.stimulus.center = (self.x, self.y)
        self.stimulus.visible = True


    def clear(self):
        self.stimulus.visible = False
        self.stimulus.update()


class Pause(Stimulus):
    def __init__(self, color=(0, 0, 0), duration=1.0, **kwargs):
        super().__init__(**kwargs)
        self.circle = None
        self.duration = duration
        self.color = color
        self.stimulus = vispy.scene.visuals.Rectangle(
            center=(self.w, self.h),
            color=self.color,
            parent=self.scene,
            height=self.h,
            width=self.w
        )
        self.stimulus.visible = False

    def paint(self, t):
        if self.running is False:
            self.start()
        else:
            self._elapsed = t
            self.stimulus.visible = True


    def clear(self):
        self.stimulus.visible = False
        self.stimulus.update()


class DisplayProcess(Process):
    def __init__(self, protocol=None):
        super().__init__()
        self.el = None
        self.txt = None
        self.prev_time = None
        self.stimuli = None
        self.current_stimulus = None
        self.canvas = None
        self.scene = None
        self.protocol = protocol()
        self.stimulus_elapsed = None
        self.i_stimulus = 0
        self.is_running = False
        vispy.use("PyQt5")
        self.canvas = scene.SceneCanvas(size=(800, 600), show=True)
        view = self.canvas.central_widget.add_view()
        self.scene = view.scene
        self.txt = scene.visuals.Text(parent=view.scene, color="white", pos=(40, 40))
        self.timer = vispy.app.Timer(interval=0.001, connect=self.update)
        self.start()
        self.interval = []
        vispy.app.run()

    def run(self) -> None:
        pass

    def update(self, *args):
        ctime = time.monotonic_ns()
        if self.prev_time is not None:
            dif = ctime - self.prev_time
            dif = dif / 1e9
            self.stimulus_elapsed += dif
        self.prev_time = ctime
        if self.stimulus_elapsed >= self.current_stimulus.duration:
            self.interval.append(self.current_stimulus.duration - self.stimulus_elapsed)
            self.stimulus_elapsed = 0
            if self.i_stimulus < len(self.stimuli) - 1:
                self.i_stimulus += 1
                self.current_stimulus.clear()
                self.current_stimulus = self.stimuli[self.i_stimulus]
            else:
                self.current_stimulus.clear()
                self.stop()
        self.current_stimulus.paint(self.stimulus_elapsed)

    def start(self) -> None:
        self.update_protocol()
        self.is_running = True
        self.stimulus_elapsed = 0
        self.timer.start()

    def update_protocol(self):
        self.stimuli = self.protocol.get_list_sequence(self.scene)
        self.current_stimulus = self.stimuli[self.i_stimulus]

    def stop(self):
        self.timer.stop()
        print('stop')
        #self.time_list = [x - (1 / self.protocol.freq) for x in self.time_list]
    # def deserialize_stim(self, stim, stim_params):
    #     self.stim = stim_dict[stim_params](scene=self.scene, **stim_params)


class FlashProtocol(Protocol):
    name = "flash_protocol"  # every protocol must have a name.

    def __init__(self, scene=None):
        super().__init__()
        self.scene = scene
        self.dur = 10
        self.n_repeats = 10

    def get_stim_sequence(self, scene):
        t = [0, 10]
        x = [0, 1000]
        y = [0, 1000]

        df = pd.DataFrame(dict(t=t, x=x, y=y))

        stimuli = [
            Circle(duration=self.dur, df_param=df, scene=scene),
            Pause(duration=1/self.dur, scene=scene),
        ]

        return stimuli

class GratingProtocol(Protocol):
    name = "grating_protocol"  # every protocol must have a name.

    def __init__(self, scene=None):
        super().__init__()
        self.scene = scene
        self.dur = 10
        self.n_repeats = 10

    def get_stim_sequence(self, scene):

        stimuli = [
           MovingGratings(duration=1/self.dur, scene=scene),
            Pause(duration=1/self.dur, scene=scene),
        ]

        return stimuli

if __name__ == "__main__":
    app = QApplication([])
    dp = DisplayProcess(protocol=FlashProtocol)
    wid = QWidget()
    wid.show()
    dp.start()
    app.exec_()
