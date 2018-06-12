import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def find_bouts_timeseries(time, tail_sum, vigour_duration=0.050,
                          vigour_threshold=0.3, diagnostic_axis=None):
    """

    Parameters
    ----------
    time :
        
    tail_sum :
        
    vigour_duration :
         (Default value = 0.050)
    vigour_threshold :
         (Default value = 0.3)
    diagnostic_axis :
         (Default value = None)

    Returns
    -------

    """
    dt = np.mean(np.diff(time[:10]))
    n_vigour_std = int(round(vigour_duration / dt))
    vigour = pd.Series(tail_sum).rolling(n_vigour_std).std()
    bouting = vigour > vigour_threshold
    if diagnostic_axis is not None:
        diagnostic_axis.plot(time, tail_sum/np.max(tail_sum), lw=0.5)
        mv = np.max(vigour)
        diagnostic_axis.axhline(vigour_threshold/mv)
        diagnostic_axis.plot(time, vigour/mv, lw=0.5)
        diagnostic_axis.plot(time, bouting, lw=0.5)
    bout_starts = np.where(np.diff(bouting * 1.) > 0)[0]
    bout_ends = np.where(np.diff(bouting * 1.) < 0)[0]
    return bout_starts, bout_ends
