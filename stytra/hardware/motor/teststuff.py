
class MotorCalib():

  def __init__(self, *args, dh=80, r=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.dh = dh
        self.r = r
        self.length_px = dh * 2
        self.points = None
        self.points_cam = None
        self.length_to_measure = "longest side of the triangle"

    def set_pixel_scale(self, w, h):
        """"Set pixel size, need to be called by the projector widget on resizes"""
        self.length_px = self.dh * 2

    @staticmethod
    def _find_triangle(image, blob_params=None):
        """Finds the three dots for calibration in the image
        (of a 30 60 90 degree triangle)

        Parameters
        ----------
        image :
            return: the three triangle points
        blob_params :
             (Default value = None)

        Returns
        -------
        type
            the three triangle points

        """
        if blob_params is None:
            blobdet = cv2.SimpleBlobDetector_create()
        else:
            blobdet = cv2.SimpleBlobDetector_create(blob_params)
        # TODO check if blob detection is robust
        scaled_im = 255 - (image.astype(np.float32) * 255 / np.max(image)).astype(
            np.uint8
        )
        keypoints = blobdet.detect(scaled_im)
        if len(keypoints) != 3:
            raise CalibrationException("3 points for calibration not found")
        kps = np.array([k.pt for k in keypoints])

        # Find the angles between the points
        # and return the points sorted by the angles

        return kps[np.argsort(CircleCalibrator._find_angles(kps)), :]

    @staticmethod
    def arr_to_tuple(arr):
        return tuple(tuple(r for r in row) for row in arr)

    def find_transform_matrix(self, image):
        self.points_cam = self._find_triangle(image)
        points_proj = self.points

        x_proj = np.vstack([points_proj.T, np.ones(3)])
        x_cam = np.vstack([self.points_cam.T, np.ones(3)])

        self.proj_to_cam = self.arr_to_tuple(self.points_cam.T @ np.linalg.inv(x_proj))
        self.cam_to_proj = self.arr_to_tuple(points_proj.T @ np.linalg.inv(x_cam))

    def calibrate(self):
        """ """
        _, frame  = self.experiment.frame_dispatcher.gui_queue.get()
        try:
            self.calibrator.find_transform_matrix(frame)

        except CalibrationException:
            pass



############################

acc = 204552
velo = 107374182
position = int(2200000 /2)

acc2 = 204552
velo2 = 107374182
position2 = int(2200000 /2)

#positions = [2200000 *2, 3620000, 400, 655000, 2200000 ]
mottione  = Motor(1)
mottitwo = Motor(2)

#mottione.set_channel(1)
mottione.homethatthing()

#mottitwo.set_channel(2)
mottitwo.homethatthing()

mottitwo.setvelocity(acc2,velo2)
mottitwo.movethatthing(position2)

mottione.setvelocity(acc,velo)
mottione.movethatthing(position)
mottione.close()
mottitwo.close()