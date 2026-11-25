"""Post-processing of a probability matrix: prior correction and temporal smoothing within a batch."""
import numpy as np


def prior_correct(P, classes, shares, beta):
    """p_c / pi_c**beta, renormalised. beta = 0 returns P unchanged."""
    pi = np.array([max(shares.get(c, 0.0), 1e-9) for c in classes])
    Q = P / pi ** beta
    return Q / Q.sum(axis=1, keepdims=True)


def temporal_smooth(P, t, sigma):
    """Each row becomes the Gaussian-weighted mean of the batch's rows by time t (seconds); sigma <= 0 returns P."""
    if sigma <= 0:
        return P
    t = np.asarray(t, dtype=float)
    W = np.exp(-((t[:, None] - t[None, :]) ** 2) / (2 * sigma ** 2))
    return (W @ P) / W.sum(axis=1, keepdims=True)
