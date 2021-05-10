from numba import jit
import numpy as np


@jit(nopython=True)
def predict_inplace(x, P, F, Q):
    x[0] = x[0] + x[1]
    P[:, :] = np.dot(np.dot(F, P), F.T) + Q


@jit(nopython=True)
def update_inplace(z, x, P, R):
    # error (residual) between measurement and prediction
    y = z - x[0]

    # project system uncertainty into measurement space
    S = P[0, 0] + R
    K = P[:, 0] / S

    x[:] = x + K * y

    I_KH = np.eye(2)
    I_KH[0, 0] -= K[0]
    I_KH[1, 0] = -K[1]

    P[:, :] = ((I_KH @ P) @ I_KH.T) + R * (K @ K.T)
