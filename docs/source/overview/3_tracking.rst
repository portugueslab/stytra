.. _tracking-desc:

Image acquisition and tracking
==============================

Image acquisition
-----------------

A key feature of Stytra is the extraction of relevant behavioral features in real time from video inputs. The :class:`Camera <stytra.hardware.video.cameras.interface.Camera>` object provides an interface for grabbing frames and setting parameters for a range of different camera types. Currently supported models include those by XIMEA, AVT, PointGray/FLIR, and Mikrotron, as well as webcams supported by OpenCV :cite:`opencv_library`. Support for other cameras can be added as long as a Python or C API exists. In addition, previously-recorded videos can also be processed, allowing for offline tracking. Frames are acquired from the original source in a process separated from the user interface and stimulus display. This ensures that the acquisition and tracking frame rate are independent of the stimulus display, which, depending on the complexity of the stimulus and output resolution, can be between 30 and 60 Hz.


Tracking pipelines
------------------

The :class:`tracking process <stytra.tracking.tracking_process.TrackingProcess>` receives acquired frames and handles animal tracking (as described :ref:`here <dataflow-block>`). Image processing and tracking are defined in subclasses of :class:`Pipeline <stytra.tracking.pipelines.Pipeline>` objects and contain a tree of processing nodes, starting from input images and ending with tracking nodes that take images as input and give tracking results as output. This structure allows for multiple tracking functions to be applied on the same input image(s). Currently implemented image processing nodes include image filtering (down-sampling, inversion and low-pass filtering) and background subtraction.
The outputs of the tracking nodes are assembled together and streamed to the main process, where the data is saved and visualized. The :class:`Pipeline <stytra.tracking.pipelines.Pipeline>` object also allows specifying a custom camera overlay to display the results of the tracking and an additional plotting widget for an alternative visualization of data.

The developer documentation section on :ref:`tracking pipelines <dev-pipelines>` describes the implementation in detail.

Tracking the behavior of head-restrained fish
---------------------------------------------

Zebrafish larvae swim in discrete units called bouts, and different types of swim bouts, from startle responses to forward swimming are caused by different tail motion patterns :cite:`Budick2565`. The tail of the larvae can be easily skeletonized and described as a curve discretized into 7-10 segments :cite:`portugues2014whole` (Fig~\ref{embed_tracking}A). The tail tracking functions work by finding the angle of a tail segment given the position and the orientation of the previous one. The starting position of the tail, as well as a rough tail orientation and length need to be specified beforehand using start and end points, movable over the camera image displayed in the user interface (as can be seen in Fig~\ref{embed_tracking}A).

To find the tail segments, two different functions are implemented. The first one looks at pixels along an arc to find their maximum (or minimum, if the image is inverted) where the current segment would end (as already described in e.g. :cite:`portugues2014whole`). The second method, introduced here, is based on centers of mass of sampling windows (Fig~\ref{embed_tracking}), and provides a more reliable and smoother estimate over a wider range of resolutions and illumination methods. The image contrast and tail segment numbers have to be adjusted for each setup, which can be easily accomplished through the live view of the filtering and tracking results. In the documentation we provide guidelines on choosing these parameters. To compare results across different setups which might have different camera resolutions, the resulting tail shape can be interpolated  to a fixed number of segments regardless of the number of traced points.


.. bibliography:: biblio.bib
