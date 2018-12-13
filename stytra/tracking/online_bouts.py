from collections import namedtuple
from numba import jit

BoutState = namedtuple("BoutState", "state vel i_inbout i_below n_after")


@jit(nopython=True)
def _process_input(
    vel, prev, threshold=1, n_without_crossing=5, pad_after=5, min_bout_len=1
):
    """
    States:
    0 default
    1 in bout
    2 potential end of bout, could return to in bout
    3 bout has ended, padding

    Output states:
    0 nothing happened
    1 bout started
    2 bout ended

    """
    state, prev_vel, i_inbout, i_below, n_after = prev
    if state == 0:
        if prev_vel < threshold < vel:
            state = 1
            i_inbout = 1
    elif state == 1:
        i_inbout = i_inbout + 1
        i_below = 0
        if prev_vel > threshold > vel:
            state = 2
    elif state == 2:
        if i_below >= n_without_crossing:
            if i_inbout >= min_bout_len:
                state = 3
                n_after = pad_after
            else:
                state = 0
        else:
            i_inbout += 1
            i_below += 1
    elif state == 3:
        n_after = n_after-1
        if n_after == 0:
            state = 0
    return BoutState(state, vel, i_inbout, i_below, n_after)


@jit(nopython=True)
def find_bouts_online(
    velocities,
    coords,
    initial_state,
    bout_coords,
    shift=0,
    threshold=1,
    n_without_crossing=5,
    pad_after=5,
    min_bout_len=1,
    pad_before=5,
):
    """ Online bout detection

    Parameters
    ----------
    velocities
    coords
    initial_state
    bout_coords

    Returns
    -------

    """
    state = initial_state
    bout_finished = False

    for i in range(shift, len(velocities)):
        next_state = _process_input(
            velocities[i],
            state,
            threshold=threshold,
            n_without_crossing=n_without_crossing,
            pad_after=pad_after,
            min_bout_len=min_bout_len,
        )
        if state.state != 1 and next_state.state == 1:
            for j in range(i-pad_before, i):
                bout_coords.append(coords[j, :])
        if next_state.state > 0:
            bout_coords.append(coords[i, :])
        if state.state == 2 and next_state.state == 0:
            bout_coords.clear()
        if state.state == 3 and next_state.state == 0:
            bout_finished = True
        state = next_state
    return bout_coords, bout_finished, state
