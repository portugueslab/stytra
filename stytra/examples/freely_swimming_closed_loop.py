from stytra import Stytra

if __name__ == "__main__":
    video_file = r"J:\Vilim Stih\fish_recordings\20180719_170349.mp4"

    camera_config = dict(video_file=video_file, rotation=0)
    tracking_config = dict(tracking_method="fish", estimator="fish", preprocessing_method="prefilter")

    s = Stytra(
        camera_config=camera_config,
        tracking_config=tracking_config,
        protocols=[],
        dir_save=r"C:\Users\vilim\Analysis\BehaviouralAnalysis\Tracking",
        log_format="csv",
        offline=True
    )
