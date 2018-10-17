from numba import jit
import numpy as np


class SimpleKalman:
    def __init__(self, x0, F, R, P, Q, H):
        self.x = x0
        self.F = F
        self.R = R
        self.P = P
        self.Q = Q
        self.H = H

    def predict(self):
        self.x, self.P = _predict(self.x, self.P, self.F, self.Q)

    def update(self, z):
        self.x, self.P = _update(z, self.x, self.P, self.F, self.Q, self.H,
                                 self.R)


@jit(nopython=True)
def _predict(x, P, F=1, Q=0):
    x = np.dot(F, x)
    P = np.dot(np.dot(F, P), F.T) + Q
    return x, P


@jit(nopython=True)
def _update(z, x, P, F, Q, H, R):
    # error (residual) between measurement and prediction
    y = z - (H @ x)

    # project system uncertainty into measurement space
    S = (H @ P) @ H.T + R
    K = (P @ H.T) @ np.linalg.inv(S)

    x = x + K @ y

    KH = K @ H

    I_KH = np.eye(KH.shape[0]) - KH

    P = ((I_KH @ P) @ I_KH.T) + ((K @ R) @ K.T)

    return x, P