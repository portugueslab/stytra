import numpy as np
import pandas as pd


def df_from_metadata(metadata, timestep=0.2):
    """ Create pandas dataframe from metadata of an experiment. The appropriate
    function is used based on the name of the protocol.
    :param metadata: metadata dictionary.
    :param timestep: timestep for the dictionary
    """

    stim_list = metadata['stimulus']['log']

    if 'tail_log' in metadata['behaviour'].keys():
        df = pd.DataFrame(metadata['behaviour']['tail_log'])[['t', 'tail_sum']]
        df = df.set_index('t')
    else:
        df = pd.DataFrame(index=np.arange(timestep,
                                          stim_list[-1]['t_stop'], timestep))

    df['stim_id'] = 0
    df['trial_t'] = 0

    if metadata['stimulus']['protocol_params']['name'] == 'exp022 protocol':
        return df_from_exp022_list(df, metadata['stimulus'])
    else:
        print('no function defined for converting this protocol')


def df_from_exp022_list(df, metadata):
    """ Update stimulus dataframe based on stimulus list coming from an
    Exp022 experiment.
    """

    p = metadata['protocol_params']['inter_stim_pause']
    gd = metadata['protocol_params']['grating_duration']
    wd = metadata['protocol_params']['windmill_duration']

    for s in metadata['stimulus']['log']:
        if s['name'] == 'pause' and s['duration'] == 5:
            df.loc[s['t_start']:, 'trial_t'] = df.index[:len(df[s['t_start']:])]
        if s['name'] == 'moving_gratings':
            t_list = s['motion']['t']
            x_list = s['motion']['x']
            th_list = s['motion']['theta']
            gratings = []
            for i in range(1, len(t_list)):
                dt = t_list[i] - t_list[i - 1]
                dx = x_list[i] - x_list[i - 1]
                if dt != 0 and dx != 0:
                    try:
                        j = gratings.index((dx / dt, th_list[i]))
                    except ValueError:
                        gratings.append((dx / dt, th_list[i]))
                        j = gratings.index((dx / dt, th_list[i]))
                    df.loc[s['t_start'] + t_list[i-1]: s['t_start'] + t_list[i],
                           'stim_id'] = j + 1

        elif s['name'] == 'windmill':
            if s['clip_rect'] == 0:
                i = 7
            if s['clip_rect'] == [0, 0, 0.5, 1]:
                i = 9
            if s['clip_rect'] == [0.5, 0, 0.5, 1]:
                i = 11

            df.loc[s['t_start'] + p / 2: s['t_start'] + gd + p / 2,
            'stim_id'] = i
            df.loc[
            s['t_start'] + p + gd + p / 2: s['t_start'] + p + gd * 2 + p / 2,
            'stim_id'] = i+1

        elif s['name'] == 'flash':
            df.loc[s['t_start']:s['t_stop'], 'stim_id'] = 13

    return df
