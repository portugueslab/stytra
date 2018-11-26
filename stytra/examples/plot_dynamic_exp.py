from stytra import Stytra


if __name__ == "__main__":
    from stytra.examples.eye_tracking_exp import WindmillProtocol
    # We make a new instance of Stytra with this protocol as the only option:
    s = Stytra(protocol=WindmillProtocol(), stim_plot=True)
