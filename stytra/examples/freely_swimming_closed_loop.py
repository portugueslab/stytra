from stytra import Stytra

if __name__ == "__main__":
    video_file = "/Users/vilimstich/PhD/TempData/Fish_recordings/20160406/20160406T141555m.avi"

    camera_config = dict(video_file=video_file,
                         rotation=0)
    tracking_config = dict(preprocessing_method="bgsub",
                           tracking_method="fish",
                           estimator="fish")

    s = Stytra(camera_config=camera_config,
               tracking_config=tracking_config,
               protocols=[])