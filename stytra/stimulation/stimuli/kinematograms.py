import numpy as np
from PyQt5.QtCore import Qt, QRect, QPointF
from PyQt5.QtGui import QBrush, QColor, QTransform
from stytra.stimulation.stimuli import VisualStimulus, InterpolatedStimulus


class DotDisplay(VisualStimulus, InterpolatedStimulus):
    def __init__(
        self,
        *args,
        dot_density=0.03,
        dot_radius=1,
        color_dots=(255, 255, 255),
        color_bg=(0, 0, 0),
        velocity=3,
        coherence=0,
        theta=0,
        max_coherent_for=0.5,
        display_size=(100, 100),
        **kwargs
    ):
        """
        Abstract class for display of dot populations

        Parameters
        ----------
        args
        dot_density
            number of dots per mm squared
        dot_radius
            dot radius in mm
        color_dots
            the color of the dots
        color_bg
            the color of the background
        velocity
            motion velocity in mm/s
        coherence
            default coherence (1: dots all move leftwards, -1: dots all move
            rightwards), for intermediate coherences a proportion of the dots
            move randomly
        theta
            angle of the display
        max_coherent_for
            number of seconds after a dot disappears and reappears in another
            location
        display_size
            size of display surface in millimiters
        kwargs
        """

        super().__init__(*args, **kwargs)
        self.dynamic_parameters.extend(["coherence", "frozen"])
        self.dot_density = dot_density
        self.dot_radius = dot_radius
        self.color_dots = color_dots
        self.color_bg = color_bg
        self.velocity = velocity
        self.max_coherent_for = max_coherent_for
        self.coherence = coherence
        self.display_size_mm = display_size
        self.display_size = display_size
        self.name = "random_dots"
        self.dots = None
        self.coherent_for = None
        self.frozen = 0
        self.theta = theta
        self.radius_px = self.dot_radius

    def get_dimensions(self):
        """
        Uses calibration data to calculate dimensions in pixels

        Returns
        -------
        number of dots to display and the displacement amount in pixel coordinates
        """
        if self._experiment.calibrator is not None:
            mm_px = self._experiment.calibrator.mm_px
        else:
            mm_px = 1

        self.display_size = np.round(np.array(self.display_size_mm) / mm_px).astype(
            np.int32
        )
        self.radius_px = int(round(self.dot_radius / mm_px))

        n_dots = int(
            round(self.display_size_mm[0] * self.display_size_mm[1] * self.dot_density)
        )

        dx = self._dt * self.velocity / mm_px

        return n_dots, dx

    def paint_dots(self, p, w, h):
        p.setBrush(QBrush(QColor(*self.color_dots)))

        dw = w / 2 - self.display_size[0] / 2
        dh = h / 2 - self.display_size[1] / 2

        for i_point in range(self.dots.shape[0]):
            p.drawEllipse(
                QPointF(self.dots[i_point, 0] + dw, self.dots[i_point, 1] + dh),
                self.radius_px,
                self.radius_px,
            )


class RandomDotKinematogram(DotDisplay):
    """ Moving dots where the motion coherence and persistence can be controlled
    """

    def update(self):
        super().update()

        n_dots, dx = self.get_dimensions()

        if self.dots is None:
            self.dots = np.random.rand(n_dots, 2) * np.array(self.display_size)[None, :]
            self.coherent_for = np.random.rand(n_dots) * self.max_coherent_for

        if self.frozen > 0:
            return None

        # select which dots are reset, and which are to be moved
        # in a coherent or random direction
        to_reset = self.coherent_for > self.max_coherent_for
        n_reset = np.sum(to_reset)
        coherent = np.random.rand(n_dots) < np.abs(self.coherence)

        # put random coordinates and lifetimes on the dots to be reset
        self.dots[to_reset, :] = np.random.rand(n_reset, 2) * self.display_size[None, :]
        self.coherent_for[to_reset] = np.random.rand(n_reset) * self.max_coherent_for

        # move the coherently moving dots in one direction
        self.dots[np.logical_and(np.logical_not(to_reset), coherent), 0] += (
            np.sign(self.coherence) * dx
        )

        # move the randomly moving dots in random directions
        sel_random_motion = np.logical_and(
            np.logical_not(to_reset), np.logical_not(coherent)
        )
        angles = np.random.rand(np.sum(sel_random_motion)) * (2 * np.pi)
        self.dots[sel_random_motion, :] += (
            np.stack([np.cos(angles), np.sin(angles)], 1) * dx
        )

        # wrap the dots around if they exceed the boundaries of the drawing area
        for dim in [0, 1]:
            self.dots[:, dim] = np.remainder(self.dots[:, dim], self.display_size[dim])

        # record the lifetime of a dot
        self.coherent_for[np.logical_not(to_reset)] += self._dt

    def get_rot_transform(self, w, h):
        xc = -w / 2
        yc = -h / 2
        return (
            QTransform()
            .translate(-xc, -yc)
            .rotate((self.theta - np.pi / 2) * 180 / np.pi)
            .translate(xc, yc)
        )

    def paint(self, p, w, h):
        # draw background
        p.resetTransform()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color_bg)))

        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))
        p.setTransform(self.get_rot_transform(w, h))

        self.paint_dots(p, w, h)


class ContinuousRandomDotKinematogram(DotDisplay):
    def __init__(self, *args, theta_relative=0, **kwargs):
        """ A version of the random dot kinematogram, as above, but with two
        improvements:

        1) dots which are chose to move coherently keep moving in
        the same direction through their lifetime

        2) the stimulus motion is rotated instead of the whole display, so there is
        less discontinuity on changes

        Parameters
        ----------

        theta_relative
            an amount of extra rotation
        """
        super().__init__(*args, **kwargs)
        self.is_coherent = None
        self.previous_coherence = None
        self.theta_relative = theta_relative

    def update(self):
        super().update()

        # get space and time dimensions
        n_dots, dx = self.get_dimensions()

        if self.dots is None:
            self.dots = np.random.rand(n_dots, 2) * np.array(self.display_size)[None, :]
            self.coherent_for = np.random.rand(n_dots) * self.max_coherent_for
            self.is_coherent = np.random.rand(n_dots) < np.abs(self.coherence)

        if self.frozen > 0:
            return None

        if self.previous_coherence != self.coherence:
            self.is_coherent = np.random.rand(n_dots) < np.abs(self.coherence)

        # select which dots are reset, and which are to be moved
        # in a coherent or random direction
        to_reset = self.coherent_for > self.max_coherent_for
        n_reset = np.sum(to_reset)

        # put random coordinates and lifetimes on the dots to be reset
        self.dots[to_reset, :] = np.random.rand(n_reset, 2) * self.display_size[None, :]
        self.coherent_for[to_reset] = np.random.rand(n_reset) * self.max_coherent_for

        # move the coherently moving dots in one direction
        theta_mov = (
            self.theta + self.theta_relative + (np.sign(self.coherence) < 0) * np.pi
        )
        self.dots[np.logical_and(np.logical_not(to_reset), self.is_coherent), :] += (
            dx * np.array([np.cos(theta_mov), np.sin(theta_mov)])[None, :]
        )

        # move the randomly moving dots in random directions
        sel_random_motion = np.logical_and(
            np.logical_not(to_reset), np.logical_not(self.is_coherent)
        )
        angles = np.random.rand(np.sum(sel_random_motion)) * (2 * np.pi)
        self.dots[sel_random_motion, :] += (
            np.stack([np.cos(angles), np.sin(angles)], 1) * dx
        )

        # wrap the dots around if they exceed the boundaries of the drawing area
        for dim in [0, 1]:
            self.dots[:, dim] = np.remainder(self.dots[:, dim], self.display_size[dim])

        # record the lifetime of a dot
        self.coherent_for[np.logical_not(to_reset)] += self._dt
        self.previous_coherence = self.coherence

    def paint(self, p, w, h):
        # draw background
        p.resetTransform()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color_bg)))

        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        self.paint_dots(p, w, h)
