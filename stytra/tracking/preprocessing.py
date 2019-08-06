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


class AdaptivePrefilter(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="adaptive_filtering", **kwargs)
        self.diagnostic_image_options = ["filtered"]

    def _process(
        self,
        im,
        image_scale: Param(0.5, (0.05, 1.0)),
        filter_size: Param(2, (0, 15)),
        color_invert: Param(True),
        clip: Param(96.9, (0.,100.)),
        # percentile: Param(96.9, (0.,100.)),
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
            clipp = np.percentile(im, clip)
            im = np.maximum(im, clip) - clipp

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


#
# class BackgroundSubtractorMotor(ImageToImageNode):
#     def __init__(self, motorx, motory, *args, **kwargs):
#         super().__init__(*args, name="bgsubmot", **kwargs)
#         self.background_image = None
#         # self.background_global = global background_0
#         #TODO how to give him global bg - set global_bg as global variable or import from config file?
#         self.i = 0
#         self.motorx = motorx
#         self.motory = motory
#
#     def reset(self):
#         self.background_image = None
#
#     def convert_motor_global(self):
#         self.motor_posx = self.motorx.get_position()
#         self.motor_posy = self.motory.get_position()
#
#         self.con = self.motor_posx / (arenaw / 2)
#         #TODO: self.arena from somewhere, maybe motor config as well?
#         #TODO: constant motor position stream somewhere, but accurate enough to relate to specific time points?
#
#         motor_x = self.motor_posx / self.con
#         motor_y = self.motor_posy / self.con
#         mx = int(motor_x - self.im.shape[0] / 2)
#         mxx = int(motor_x + self.im.shape[0] / 2)
#         my = int(motor_y - self.im.shape[1] / 2)
#         myy = int(motor_y + self.im.shape[1] / 2)
#         return mx, mxx, my, myy
#
#     def find_fish(self):
#         self.im = 255 - self.im
#         idxs = np.unravel_index(np.nanargmax(self.im),self.im.shape)
#         e = (np.float(idxs[1]), np.float(idxs[0]))
#         x = int(e[0])
#         y = int(e[1])
#         return x, y
#
#     def create_mask(self, x, y):
#         # circle_image = np.ones(self.im.shape[0], self.im.shape[1]), np.uint8)
#         mask = cv2.circle(circle_image, (x, y), 60, 255, -1)
#         return mask
#
#     def _process(
#         self, im, learning_rate: Param(0.04, (0.0, 1.0)),
#         global_learning_rate: Param(0.04, (0.0, 1.0)),
#         learn_every: Param(400, (1, 10000))
#     ):
#         messages = []
#         if self.background_image is None:
#             x, y = find_fish(self.im)
#             mask = create_mask(x, y, self.im)
#             self.background_image[mask == True] = self.im[mask == True]
#             messages.append("I:New background image set")
#         elif self.i == 0:
#             print ("Ready to roll.")
#             mx, mxx, my, myy =BackgroundSubtractorMotor.convert_motor_global(self)
#             self.background_old =self.background_global[mx:mxx, my:myy] #getting bg from global
#             self.background_image[:, :] = self.im.astype(np.float32) * np.float32(
#                 learning_rate) + self.background_old * np.float32(
#                 1 - learning_rate)
#
#             #Updating gloabl bg as well
#             print ("Global update this.")
#             background_global_old = np.copy(self.background_global)
#             self.background_global[mx:mxx, my:myy] = self.background_image #setting new bg to global
#             self.background_global[:, :] = self.background_global.astype(np.float32) * np.float32(
#                 global_learning_rate) + background_global_old * np.float32(
#                 1 - global_learning_rate)
#
#         self.i = (self.i + 1) % learn_every
#
#         return NodeOutput(messages, negdif(self.background_image, im))
