from stytra.tracking.pipelines import Pipeline
from stytra.tracking.preprocessing import BackgroundSubtractor
from stytra.gui.camera_display import CameraSelection
from collections import namedtuple
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from stytra import Stytra
from stytra.stimulation.stimuli import Pause

from stytra.stimulation import Protocol
from lightparam import Param
from pathlib import Path
import numpy as np
import cv2
import pyqtgraph as pg


# Here we showcase the steps required to add your custom tracking function in
#  stytra. It might look a bit complicated at the beginning, but
# following closely the example and use this script as a template will make
# it easier.


# First of all, we need to create a new tracking method. You should have read
#  in the documentation that in Stytra the image processing analysis is
# defined in a branching way, appending nodes for image transformations (
# ImageToImage nodes) followed by nodes for extracting numbers, such as
# animal position or posture (ImageToDataNode). For this particular example,
# we will use the powerful adaptive background subraction that we just import
#  from stytra in line 2, followed by the following new custo method.

# To track the drosophila, we will fit an ellipse to its body, and we will
# log the 5 variables of the ellipse (xy position, yx dimension, orientation).


class FlyTrackingMethod(ImageToDataNode):
    """Fly tracking method using ellipse fit.
    """

    def __init__(self, *args, **kwargs):
        # Initialise the "Node" object passing the name of our tracking method:
        super().__init__(*args, name="fly_track", **kwargs)

        # Those headers specify the names of the quantities we will get out
        # of the tracking function. In our case ellipse position on x and y,
        # dimension on x and y, and orientation. With them, we generate the
        # "type" of the output, which will be a namedtuple with the specified
        #  keys.
        headers = ["x", "y", "dim_x", "dim_y", "theta"]
        self._output_type = namedtuple("t", headers)

        # Monitored headers list specify which quantities will be displayed
        # in the streaming plot:
        self.monitored_headers = ["x", "y", "theta"]

        # The data log name specify under which name we will find the tracked
        #  quantities in the log:
        self.data_log_name = "fly_track"

        # To adjust the tracking, we can display diagnostic images instead of
        #  the raw image from the camera. Here we list the options:
        self.diagnostic_image_options = ["input", "thresholded"]

    def _process(
        self,
        im,
        threshold: Param(56, limits=(1, 254)),
        fly_area: Param((5, 1000), (1, 4000)),
        **extraparams
    ):
        """
        :param im: input image
        :param threshold: threshold for binarization
        :param fly_area: tuple with minimum and maximum size for the blob
        :return: NodeOutput with the tracking results
        """
        # Diagnostic messages can be outputted with info on what went wrong:
        message = ""

        # Binarize the image with the specified threshold:
        thesholded = (im[:, :] < threshold).view(dtype=np.uint8).copy()

        # Find contours with OpenCV:
        cont_ret = cv2.findContours(
            thesholded.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        # Small compatibility fix on OpenCV versions.
        # API change, in OpenCV 4 there are 2 values unlike OpenCV3
        if len(cont_ret) == 3:
            _, contours, hierarchy = cont_ret
        else:
            contours, hierarchy = cont_ret

        ell = False
        if len(contours) >= 2:

            # Get the largest ellipse:
            contour = sorted(contours, key=lambda c: c.shape[0], reverse=True)[0]

            # Fit the ellipse for the fly, if contours has a minimal length:
            if fly_area[0] < len(contour) < fly_area[1]:
                # ell will be a tuple ((y, x), (dim_y, dim_x), theta)
                ell = cv2.fitEllipse(contour)

                max_approx_radius = np.sqrt(fly_area[1] / np.pi) * 10
                if ell[1][0] > max_approx_radius or ell[1][1] > max_approx_radius:
                    # If ellipse axis much larger than max area set to false:
                    ell = False
                    message = "W:Wrong fit - fly close to borders?"
            else:
                # Otherwise, set a diagnostic message:
                message = "W:Blob area ouside the area range!"
        else:
            # No blobs found:
            message = "W:No contours found!"

        # Here we have the option to specify a diagnostic image if the
        # set_diagnostic attribute (set somewhere else in Stytra) is matching
        #  one of our options:
        if self.set_diagnostic == "input":
            # show the preprocessed, background-subtracted image
            self.diagnostic_image = im
        if self.set_diagnostic == "thresholded":
            # show the thresholded image:
            self.diagnostic_image = thesholded

        if ell is False:
            # If e is not valid, return tuple eof nans
            ell = (np.nan,) * 5
        else:
            # If valid, reshape it to a plain tuple:
            ell = ell[0][::-1] + ell[1][::-1] + (-ell[2],)

        # Return a NodeOutput object which combines the message and the
        # output named tuple created from the output type defined in the init
        #  and the tuple with our tracked values
        return NodeOutput([message], self._output_type(*ell))


# To monitor the results of the tracking from the interface, we would like to
#  have a way of displaying the fly ellipse on top of the gui interface. This
#  kind of display can be customized using the CameraSelection class. The
# same class allow us to manipulate an ROI on the image, as happening
# in the eyes or tail fish tracking, hereby the name.
# In our case, we will use it only for display. We will rely on pyqtgraph to
# draw and control the ellipse position:


class FlyTrackingSelection(CameraSelection):
    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)

        # We need to initialise the ellipse, add it to the area, and remove
        # the handles from the ellipseROI:
        self.fly_ell = pg.EllipseROI(pos=(0, 0), size=(10, 10), movable=False, pen=None)

        self.display_area.addItem(self.fly_ell)
        [self.fly_ell.removeHandle(h) for h in self.fly_ell.getHandles()]
        self.pre_th = 0

    def retrieve_image(self):
        """
        This is the function that is called from the Stytra GUI at every
        update loop. Here, we get the fly ellipse parameters from the queue
        and we use them to place the ellipse correctly.

        Note that this function run in the same process of the rest of the
        GUI and of the stimulus. If you pur here some slow code, it will slow
        down the entire interface and the stimulation update as well!
        """
        super().retrieve_image()

        # Pass if there is still no image from the camera:
        if self.current_image is None:
            return

        # Get data from the tracking queue (first is timestamp):
        if len(self.experiment.acc_tracking.stored_data) > 1:
            # To match tracked points and frame displayed looks for matching
            # timestamps of the displayed frame and of tracked queue:
            retrieved_data = self.experiment.acc_tracking.values_at_abs_time(
                self.current_frame_time
            )

            # Check for valid data to be displayed:
            if len(self.experiment.acc_tracking.stored_data) > 1:
                checkifnan = getattr(retrieved_data, "theta")

                if checkifnan == checkifnan:  # will be false if np.nan
                    # Make visible if previously hidden:
                    self.fly_ell.setPen(color=(5, 40, 230), width=3)

                    # Here we take care of of rotation and translation
                    # of the ROI from ellipse center, axis and rotation.
                    # Some geometry is required because pyqtgraph rotation
                    # happens around lower corner and not around center.
                    th = -getattr(retrieved_data, "theta")
                    dim_x = int(getattr(retrieved_data, "dim_x") / 2)
                    dim_y = int(getattr(retrieved_data, "dim_y") / 2)

                    if dim_x != 0 and dim_y != 0:
                        th_conv = th * (np.pi / 180)  # in radiants now

                        # rotate based on difference from previous angle:
                        self.fly_ell.rotate(th - self.pre_th)

                        # Angle and rad of center point from left lower corner:
                        c_th = np.arctan(dim_x / dim_y)
                        c_r = np.sqrt(dim_x ** 2 + dim_y ** 2)

                        # Coords of the center after rotation around left lower
                        # corner, to be corrected when setting position:
                        center_after = (
                            np.cos(c_th + th_conv) * c_r,
                            np.sin(c_th + th_conv) * c_r,
                        )

                        # Calculate pos for fly ROIs. This require correction
                        # for the rotation around corner instead of center.
                        self.fly_ell.setPos(
                            getattr(retrieved_data, "y")
                            - dim_x
                            + (dim_x - center_after[0]),
                            getattr(retrieved_data, "x")
                            - dim_y
                            + (dim_y - center_after[1]),
                        )
                        self.fly_ell.setSize((dim_y * 2, dim_x * 2))

                        # Update previous theta:
                        self.pre_th = th

                else:
                    # Hide ROI if no eyes detected:
                    self.fly_ell.setPen(None)


# Finally, we assemble a "pipeline" where we specify the order of the
# functions that we will apply to the image. Each pipeline node will take as
# "parent" the node from which it reads the input frames. In this case,
# we first apply adaptive background subtraction, and only afterward we apply
#  our tracking function.
# The "display overlay" attribute, which does not necessarily have to be
# specified, will allow us to overimpose on the GUI an ellipse to monitor
#  live our tracking.


class DrosophilaPipeline(Pipeline):
    def __init__(self):
        super().__init__()

        self.bgsub = BackgroundSubtractor(parent=self.root)
        self.eyetrack = FlyTrackingMethod(parent=self.bgsub)
        self.display_overlay = FlyTrackingSelection


# Here we define our stumulus protocol (empty in this case), passing in the
# config dictionary our custom pipeline:
class FlyTrackingProtocol(Protocol):
    name = "fly_tracking"
    stytra_config = dict(
        tracking=dict(method=DrosophilaPipeline),
        camera=dict(video_file=str(r"/Users/luigipetrucco/Desktop/video.hdf5")),
    )

    def get_stim_sequence(self):
        # Empty protocol of specified duration:
        return [Pause(duration=10)]


if __name__ == "__main__":
    s = Stytra(protocol=FlyTrackingProtocol())
