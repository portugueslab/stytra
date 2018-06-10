import argparse
from stytra.experiments import Experiment
from stytra.experiments.tracking_experiments import CameraExperiment, \
    EyeTrackingExperiment, MovementRecordingExperiment, TailTrackingExperiment

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon


class Stytra:
    def __init__(self, parser=None, protocols = [],
                 metadata_animal=None, metadata_general=None):
        if parser is None:
            parser = argparse.ArgumentParser()

        parser.add_argument('--freely-swimming',
                            action='store_true')
        parser.add_argument('--camera-rotation',
                            default=0,
                            type=int,
                            action='store')
        parser.add_argument('--tail-tracking',
                            action='store_true')
        parser.add_argument('--tail-tracking-method',
                            action='store', default='angle_sweep')
        parser.add_argument('--camera',
                            action='store', default=None)
        parser.add_argument('--display-w',
                            type=int,
                            action='store', default=0)
        parser.add_argument('--display-h',
                            type=int,
                            action='store', default=0)
        parser.add_argument('--tail-invert',
                            action='store_true')
        parser.add_argument('--shock-stimulus',
                            action='store_true')
        parser.add_argument('--vr',
                            action='store_true')
        parser.add_argument('--sim-vr',
                            action='store_true')
        parser.add_argument('--eye-tracking',
                            action='store_true')
        parser.add_argument('--debug',
                            action='store_true')
        parser.add_argument('--scope-triggering',
                            action='store_true')
        parser.add_argument('--video-file',
                            action='store',
                            default=None)
        parser.add_argument('--directory', action='store',
                            default='D:/vilim/stytra')
        parser.add_argument('--rec-stim-every', action='store',
                            default=None)
        parser.add_argument('--asset-dir', action='store',
                            default='/Users/vilimstich/PhD/j_sync/underwater')
        parser.add_argument('--full-screen',
                            action='store_true')
        parser.add_argument('--setup', action='store', default='')

        args = parser.parse_args()

        bases = [Experiment]

        app = QApplication([])

        try:
            rec_stim_every = int(args.rec_stim_every)
        except TypeError:
            rec_stim_every = None

        class_kwargs = dict(app=app,
                            directory=args.directory,
                            debug_mode=args.debug,
                            asset_directory=args.asset_dir,
                            scope_triggered=args.scope_triggering,
                            rec_stim_every=rec_stim_every,
                            shock_stimulus=args.shock_stimulus,
                            metadata_animal=metadata_animal,
                            metadata_general=metadata_general,
                            protocols=protocols)

        base = Experiment
        if args.video_file:
            base = CameraExperiment
            class_kwargs['video_file'] = args.video_file

        if args.tail_tracking or args.freely_swimming or args.eye_tracking:
            class_kwargs['camera_rotation'] = int(args.camera_rotation)
            class_kwargs['camera'] = args.camera
            class_kwargs['tracking_method_name'] = args.tail_tracking_method
        print(class_kwargs)
        if args.tail_tracking:
            base = TailTrackingExperiment

        elif args.freely_swimming:
            base = MovementRecordingExperiment
        elif args.eye_tracking:
            base = EyeTrackingExperiment
            class_kwargs['tracking_method_name'] = 'eyes'  # TODO temporary

        app_icon = QIcon()
        app_icon.addFile('icons/48.png', QSize(48, 48))
        app_icon.addFile('icons/128.png', QSize(128, 128))
        app_icon.addFile('icons/256.png', QSize(256, 256))
        app.setWindowIcon(app_icon)

        exp = base(**class_kwargs)

        exp.start_experiment()
        exp.show_stimulus_screen(full_screen=args.full_screen)
        if args.display_w and args.display_h:
            exp.window_display.params['size'] = (args.display_w, args.display_h)
            exp.window_display.set_dims()
        app.exec_()


if __name__ == "__main__":
    st = Stytra()