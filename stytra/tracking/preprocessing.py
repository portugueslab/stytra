"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

import numpy as np
from numba import vectorize, uint8, float32
from lightparam import Param
from stytra.tracking.pipelines import ImageToImageNode, NodeOutput
from stytra.hardware.motor.stageAPI import Motor


class Prefilter(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="filtering", **kwargs)
        self.diagnostic_image_options = ["filtered"]

    def _process(
        self,
        im,
        image_scale: Param(0.5, (0.05, 1.0)),
        filter_size: Param(2, (0, 15)),
        color_invert: Param(True),
        clip: Param(150, (0, 255)),
        **extraparams
    ):
        """ Optionally resizes, smooths and inverts the image

        :param im:
        :param state:
        :param filter_size:
        :param image_scale:
        :param color_invert:
        :return:
        """
        if image_scale != 1:
            im = cv2.resize(
                im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA
            )
        if filter_size > 0:
            im = cv2.boxFilter(im, -1, (filter_size, filter_size))
        if color_invert:
            im = 255 - im
        if clip > 0:
            im = np.maximum(im, clip) - clip

        if self.set_diagnostic == "filtered":
            self.diagnostic_image = im

        return NodeOutput([], im)


@vectorize([uint8(float32, uint8)])
def negdif(xf, y):
    """

    Parameters
    ----------
    x :

    y :


    Returns
    -------

    """
    x = np.uint8(xf)
    if y < x:
        return x - y
    else:
        return 0


class BackgroundSubtractor(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="bgsub", **kwargs)
        self.background_image = None
        self.i = 0

    def reset(self):
        self.background_image = None

    def _process(
        self, im, learning_rate: Param(0.04, (0.0, 1.0)),
        learn_every: Param(400, (1, 10000))
    ):
        messages = []
        if self.background_image is None:
            self.background_image = im.astype(np.float32)
            messages.append("I:New backgorund image set")
        elif self.i == 0:
            self.background_image[:, :] = im.astype(np.float32) * np.float32(
                learning_rate
            ) + self.background_image * np.float32(1 - learning_rate)

        self.i = (self.i + 1) % learn_every

        return NodeOutput(messages, negdif(self.background_image, im))



class BackgroundSubtractorMotor(ImageToImageNode):
    def __init__(self, m1,m2,*args, **kwargs):
        super().__init__(*args, name="bgsubmot", **kwargs)
        self.background_image = None
        self.i = 0
        self.motti1 = m1
        self.motti2 = m2

    def reset(self):
        self.background_image = None

    def create_mask(self):
        # TODO tie in f0_x, f0_y from fish tracking and orientation as well as lenght for masking box
        # TODO fish_coords = np.concatenate([np.array(points[0][:2]), angles]) from FishTrackingMethod
        # TODO also  _fish_direction_n

        self.mask = np.ones(im.shape)
        bx = int(f0_x - 25)
        bxx = int(f0_x + 25)
        by = int(f0_y - 25)
        byy = int(f0_y + 25)
        self.mask[by:byy, bx:bxx] = 0

        self.masked = im * (-self.mask)
        return self.masked

    def global_bg(self,arenax, arenay):
        self.arena = (arenax, arenay)  # needs to be pixels
        self.background = np.zeros(self.arena)

    def convert_motor_global(self):
        con = 2200000 / (self.arena[0] / 2)
        print(con)

        motor_posx =self.motti1.get_position()
        motor_posy =self.motti2.get_position()

        motor_x = motor_posx / con
        motor_y = motor_posy / con

        mx = int(motor_x - im.shape[0] / 2)
        mxx = int(motor_x + im.shape[0] / 2)
        my = int(motor_y - im.shape[1] / 2)
        myy = int(motor_y + im.shape[1] / 2)

        return mx,mxx,my,myy

    def _process(
        self, im, learning_rate: Param(0.04, (0.0, 1.0)),
        learn_every: Param(400, (1, 10000))
    ):
        messages = []
        if self.background_image is None:
            BackgroundSubtractorMotor.create_mask(345, 669)
            BackgroundSubtractorMotor.global_bg(4800,488)
            mx, mxx, my, myy =BackgroundSubtractorMotor.convert_motor_global()
            # if condition for if background already filled at that point

            bg_filled = (background_image[mx:mxx, my:myy].any(0) == True)

            if bg_filled.any(0):
                print("filled is True")
                learning_rate = 0.04
                background_old = np.copy(background_image)
                background_image[mx:mxx, my:myy] = masked
                background_image[:, :] = background_image.astype(np.float32) * np.float32(
                    learning_rate) + background_old * np.float32(
                    1 - learning_rate)
            else:
                print("Notfilled is True")
                learning_rate = 0.1
                background_old = np.copy(background_image)
                background_image[mx:mxx, my:myy] = masked
                background_image[:, :] = background_image.astype(np.float32) * np.float32(
                    learning_rate) + background_old * np.float32(
                    1 - learning_rate)
        else:
            pass
        self.i = (self.i + 1) % learn_every

        return NodeOutput(messages, negdif(self.background_image[:, :], im))
        #TODO this (background_image[:, :]) will likely not work
