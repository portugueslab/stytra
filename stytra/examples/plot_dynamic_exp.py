from stytra import Stytra


if __name__ == "__main__":
    from stytra.examples.gratings_exp import GratingsProtocol

    # We make a new instance of Stytra with this protocol as the only option:
    s = Stytra(protocol=GratingsProtocol(), stim_plot=True)
