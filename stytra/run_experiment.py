import argparse
from stytra import TailTrackingExperiment, Experiment, LightsheetExperiment, MovementRecordingExperiment
import stytra.stimulation.protocols as prot

from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--freely-swimming',
                        action='store_true')
    parser.add_argument('--tail-tracking',
                        action='store_true')
    parser.add_argument('--tail-tracking-method',
                        action='store', default='angle_sweep')

    parser.add_argument('--tail-invert',
                        action='store_true')
    parser.add_argument('--vr',
                        action='store_true')
    parser.add_argument('--debug',
                        action='store_true')
    parser.add_argument('--lightsheet',
                        action='store_true')
    parser.add_argument('--video-file',
                        action='store',
                        default=None)

    parser.add_argument('--directory', action='store',
                        default='D:/vilim/stytra')
    parser.add_argument('--asset-dir', action='store',
                        default='/Users/vilimstich/PhD/j_sync/underwater')
    parser.add_argument('--full-screen',
                        action='store_true')
    parser.add_argument('--setup', action='store', default='')

    args = parser.parse_args()

    bases = [Experiment]

    app = QApplication([])

    class_kwargs = dict(app=app,
                        directory=args.directory,
                        debug_mode=args.debug,
                        asset_directory=args.asset_dir)

    bases = []

    if args.tail_tracking:
        bases.append(TailTrackingExperiment)
        class_kwargs['video_file'] = args.video_file
        class_kwargs['tracking_method_parameters'] = dict(n_segments=12,
                                                          filter_size=5,
                                                          color_invert=args.tail_invert)
        class_kwargs['tracking_method'] = args.tail_tracking_method
        if args.vr:
            class_kwargs['motion_estimation'] = 'LSTM'
            class_kwargs['motion_estimation_parameters'] = dict(model='lstm_300Hz.h5')

    elif args.freely_swimming:
        bases.append(MovementRecordingExperiment)

    if args.lightsheet:
        bases.append(LightsheetExperiment)

    if len(bases) == 0:
        bases.append(Experiment)

    ExpClass = type('exp_class', tuple(bases), dict())
    exp = ExpClass(**class_kwargs)
    exp.show_stimulus_screen(full_screen=args.full_screen)
    app.exec_()
