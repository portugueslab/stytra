class Camera:
    """Abstract class for controlling a camera.

    Subclasses implement minimal
    control over the following cameras:
     - Ximea (uses ximea python API `xiAPI <https://www.ximea.com/support/wiki/apis/Python>`_;
     - AVT   (uses `pymba <https://github.com/morefigs/pymba>`_,
       a python wrapper for AVT Vimba package).

    Examples
    --------
    Simple usage of a camera class::

        cam = AvtCamera()
        cam.open_camera()  # initialize the camera
        cam.set('exposure', 10)  # set exposure time in ms
        frame = cam.read()  # read frame
        cam.release()  # close the camera


    Attributes
    ----------
    cam :
        camera object (class depends on camera type).

    debug : bool
        if true, state of the camera is printed.


    """

    def __init__(self, downsampling=1, roi=(-1, -1, -1, -1), **kwargs):
        """
        Parameters
        ----------
        debug : str
            if True, info about the camera state will be printed.
        """
        self.cam = None
        self.downsampling = downsampling
        self.roi = roi

    def open_camera(self):
        """Initialise the camera."""

    def set(self, param, val):
        """Set exposure time or the framerate to the camera.

        Parameters
        ----------
        param : str
            parameter key ('exposure', 'framerate'));
        val :
            value to be set (exposure time in ms, or framerate in Hz);

        """
        pass

    def read(self):
        """Grab frame from the camera and returns it as an NxM numpy array.

        Returns
        -------
        np.array
                the grabbed frame, or None if an error occurred.

        """
        return None

    def release(self):
        """Close the camera.
        """
        pass
