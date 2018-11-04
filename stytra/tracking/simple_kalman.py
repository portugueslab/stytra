from numba import jit
import numpy as np


class NewtonianKalman:
    def __init__(self, x0, stdev, dt, pred_coef):
        self.x = np.array([x0, 0.0])
        self.F = np.array([[1.0, 1.0], [0.0, 1.0]])
        self.R = stdev
        self.P = np.diag([stdev, stdev])
        self.Q = (
            np.array([[0.25 * dt ** 4, 0.5 * dt ** 3], [0.5 * dt ** 3, dt ** 2]])
            * pred_coef
        )

    def predict(self):
        self.x, self.P = _predict(self.x, self.P, self.F, self.Q)

    def update(self, z):
        self.x, self.P = _update(z, self.x, self.P, self.R)


@jit(nopython=True)
def _predict(x, P, F, Q):
    x = np.dot(F, x)
    P = np.dot(np.dot(F, P), F.T) + Q
    return x, P


@jit(nopython=True)
def _update(z, x, P, R):
    # error (residual) between measurement and prediction
    y = z - x[0]

    # project system uncertainty into measurement space
    S = P[0, 0] + R
    K = P[:, 0] / S

    x = x + K * y

    I_KH = np.eye(2)
    I_KH[0, 0] -= K[0]
    I_KH[1, 0] = -K[1]

    P = ((I_KH @ P) @ I_KH.T) + R * (K @ K.T)

    return x, P
