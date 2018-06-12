from stytra.stimulation.visual import MovingSeamless
from stytra.bouter.angles import transform_affine
import numpy as np
import cv2


class MovingBackground:
    """A class to manage transformations of the bacground to enable studying of
    different aspectos of backgound follwing in OMR

    Parameters
    ----------

    Returns
    -------

    """
    def __init__(self, exp):
        self.exp = exp
        self.stim = MovingSeamless(background=exp['stimulus']['background'],
                    motion=exp['stimulus']['motion'],
                    output_shape=tuple(map(int, exp['stimulus']['window']['size'])))
        self.tm = exp['stimulus']['calibration_to_cam']

    def plot_motion(self):
        """ """
        pass

    def get_bg_point(self, t):
        """

        Parameters
        ----------
        t :
            

        Returns
        -------

        """
        self.stim.elapsed = t
        self.stim.update()
        p_proj = np.array(
            [np.interp(t, self.motion.t, self.motion[dim]) for dim in
             ['y', 'x']])
        return transform_affine(p_proj, self.tm)

    def get_bg_image(self, t):
        """Get the backgroud image in camera coordinates at time t

        Parameters
        ----------
        t :
            

        Returns
        -------

        """
        x = np.interp(t, self.motion.t, self.motion.x)
        y = np.interp(t, self.motion.t, self.motion.y)
        tm = np.array([[1, 0, y],
                       [0, 1, x]]).astype(np.float32)
        bgim = cv2.warpAffine(self.bg, tm, borderMode=cv2.BORDER_WRAP,
                              dsize=tuple(map(int,
                                              self.exp['stimulus']['window'][
                                                  'size'])))

        dsize = (488, 648)
        return cv2.warpAffine(bgim, self.tm, dsize=dsize[::-1])

    def motion_direction_velocity(self, t, window_length=0.5):
        """Get the direction and velocity of motion prior to the time point t
            in the camera coordinates

        Parameters
        ----------
        t :
            
        window_length :
             (Default value = 0.5)

        Returns
        -------

        """
        ts = (t - window_length, t)
        points = np.empty((2, 2))
        for i, dim in enumerate(['y', 'x']):
            points[:, i] = [np.interp(t1, self.motion.t, self.motion[dim]) for
                            t1 in ts]
        points_t = transform_affine(points, self.tm)
        return (np.arctan2(points_t[1, 1] - points_t[0, 1],
                           points_t[1, 0] - points_t[0, 0]),
                np.sqrt((points_t[1, 1] - points_t[0, 1]) ** 2 +
                        (points_t[1, 0] - points_t[0, 0]) ** 2))

    def get_position(self, t):
        """

        Parameters
        ----------
        t :
            

        Returns
        -------

        """
        return tuple(
            np.interp(t, self.motion.t, self.motion[dim]) for dim in ['x', 'y'])