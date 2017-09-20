import argparse
from stytra import TailTrackingExperiment, Experiment, LightsheetExperiment
import stytra.stimulation.protocols as prot

from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--tail_tracking',
                        action='store_true')
    parser.add_argument('--tail-invert',
                        action='store_true')
    parser.add_argument('--debug',
                        action='store_true')
    parser.add_argument('--lightsheet',
                        action='store_true')
    parser.add_argument('--directory', action='store',
                        default='D:/vilim/stytra')

    args = parser.parse_args()

    bases = [Experiment]

    app = QApplication([])

    class_kwargs = dict(app=app, directory=args.directory, debug_mode=args.debug)

    if args.tail_tracking:
        bases.append(TailTrackingExperiment)
        class_kwargs['tracking_method_parameters'] = dict(n_segments=9,
                                                          filtering=True,
                                                          color_invert=args.tail_invert)
    if args.lightsheet:
        bases.append(LightsheetExperiment)

    ExpClass = type('exp_class', bases)
    exp = ExpClass(**class_kwargs)

    app.exec()
