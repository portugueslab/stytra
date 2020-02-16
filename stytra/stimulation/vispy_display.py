import vispy
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from multiprocessing import Process
from vispy.app import Application as VisApp
from vispy import scene
import time
import numpy as np
import pandas as pd
from vispy.visuals.transforms import MatrixTransform
from itertools import product

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
        self.x = self.w / 2
        self.y = self.h / 2
        self._elapsed = None
        self._elapsed = 0
        self.stimulus = None
        self.running = False

    def paint(self, t):
         self._elapsed = t

    def start(self):
        self.running = True

    def get_transform(self, x, y):
            transform_mat = np.diag([1.0, 1, 1, 1])
            transform_mat[3, 0] = x
            transform_mat[3, 1] = y
            transform_mat[3, 2] = 1
            return transform_mat


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
        self.imw = 10
        self.imh = 10
        self.color = (0, 1, 0)

    def negceil(self, x):
        """ negative ceiling function (e.g -0.2 gets rounded to -1, while 0.2 gets rounded to 1)
        """
        return int(-np.ceil(-x) if x < 0 else np.ceil(x))

    def get_tile_ranges(self, imw, imh, w, h, tr):
    # we find where the display surface is in the coordinate system of a single tile
        corner_points = [
            np.array([0.0, 0.0]),
            np.array([w, 0.0]),
            np.array([w, h]),
            np.array([0.0, h]),
        ]
        points_transformed = np.array(
            [tr.inverse()[0].map(*cp) for cp in corner_points]
        )

        # calculate the rectangle covering the transformed display surface
        min_x, min_y = np.min(points_transformed, 0)
        max_x, max_y = np.max(points_transformed, 0)

        # count which tiles need to be drawn
        x_start, x_end = (self.negceil(x / imw) for x in [min_x, max_x])
        y_start, y_end = (self.negceil(y / imh) for y in [min_y, max_y])
        return range(x_start, x_end + 1), range(y_start, y_end + 1)

    def paint(self, t):
        self._elapsed = t
        h = self.h
        w = self.w
        dx = self.x
        dy = self.y

        # rotate the coordinate transform around the position of the fish
        tr = self.get_transform(dx, dy)
        tr = MatrixTransform(tr)
        # self.stimulus_container.transform = tr
        for idx, idy in product(*self.get_tile_ranges(self.imw, self.imh, w, h, tr)):
            self.draw_block(idx * self.imw, idy * self.imh)

    def draw_block(self,x_pos, y_pos):
        pass


class MovingGratings(BackgroundStimulus):
    def __init__(self, grating_period=10, **kwargs):
        super().__init__(**kwargs)
        self.name = 'grating'
        self.grating_period = grating_period
        self.stimulus = []
        n_tiles, pos = self.get_tile_ranges(self.grating_period, self.h, self.w, self.h)
        for i in range(n_tiles - 1):
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

    def draw_block(self, p, point, w, h):
        # Get background image from folder:
        p.drawImage(point, self._qbackground)


class Circle(InterpolatedStimulus):
    def __init__(self, color=(1, 1, 1), w=10, h=10, duration=1.0, **kwargs):
        super().__init__(**kwargs)
        self.circle = None
        self.duration = duration
        self.name = 'circle'
        self.color = color
        self.w = w
        self.h = h
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


class MultipleCircles(InterpolatedStimulus):
    def __init__(self, n_circles=2, color=(1, 1, 1), w=10, h=10, duration=1.0, x_list=None, y_list=None, **kwargs):
        super().__init__(**kwargs)
        self.duration = duration
        self.name = 'multiple_circles'
        self.color = color
        self.w = w
        self.h = h
        self.n_circles = n_circles
        # for the time being
        if (x_list is None) and (y_list is None):
            x_list = np.random.randint(0, self.scene.canvas.physical_size[0], self.n_circles)
            y_list = np.random.randint(0, self.scene.canvas.physical_size[1], self.n_circles)
        self.stimulus = scene.node.Node(
            parent=self.scene, transforms=MatrixTransform()
        )
        for i in range(self.n_circles):
            vispy.scene.visuals.Ellipse(
                center=(x_list[i], y_list[i]),
                color=self.color,
                parent=self.stimulus,
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
        dx = 10
        dy = 10
        t = self.get_transform(dx, dy)
        tr = MatrixTransform(t)
        self.stimulus.transform = tr
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


class CircleProtocol(Protocol):
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


class MultiCirclesProtocol(Protocol):
    name = "flash_protocol"  # every protocol must have a name.

    def __init__(self, scene=None):
        super().__init__()
        self.scene = scene
        self.dur = 10
        self.n_repeats = 10
        self.n_circles = 1

    def get_stim_sequence(self, scene):
        t = [0, 10]
        x = [0, 10]
        y = [0, 10]

        df = pd.DataFrame(dict(t=t, x=x, y=y))

        stimuli = [
            MultipleCircles(n_circles=self.n_circles, duration=self.dur, df_param=df, scene=scene),
            Pause(duration=self.dur, scene=scene),
        ]

        return stimuli


if __name__ == "__main__":
    app = QApplication([])
    dp = DisplayProcess(protocol=MultiCirclesProtocol)
    wid = QWidget()
    wid.show()
    dp.start()
    app.exec_()
