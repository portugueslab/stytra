from stytra import Stytra

if __name__ == "__main__":
    video_file = r"J:\Vilim Stih\fish_recordings\20180719_170349.mp4"

    camera_config = dict(video_file=video_file, rotation=0)
    tracking_config = dict(
        preprocessing_method="bgsub", tracking_method="fish", estimator="fish"
    )

    s = Stytra(
        camera_config=camera_config, tracking_config=tracking_config, protocols=[]
    )
