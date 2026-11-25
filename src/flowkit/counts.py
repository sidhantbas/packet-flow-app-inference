"""Count-constrained labelling: give each class an exact number of flows in a batch, maximising the summed log-probability
(an exact linear assignment, one slot per expected flow). Same algorithm as experiment 095."""
import numpy as np
from scipy.optimize import linear_sum_assignment

KINDS = ("none", "shares", "disclosed")


def quota_assign(P, classes, counts):
    """Labels for the rows of probability matrix P with exactly counts[c] rows of class c."""
    slots = [k for k, c in enumerate(classes) for _ in range(int(counts.get(c, 0)))]
    if len(slots) != P.shape[0]:
        raise ValueError(f"counts sum to {len(slots)}, batch has {P.shape[0]} rows")
    rows, cols = linear_sum_assignment(-np.log(np.clip(P[:, slots], 1e-9, None)))
    out = np.empty(P.shape[0], dtype=object)
    out[rows] = np.asarray(classes, dtype=object)[np.asarray(slots)[cols]]
    return out


def share_counts(classes, shares, n):
    """Integer counts summing to n from class shares (largest remainder)."""
    raw = np.array([shares.get(c, 0.0) * n for c in classes])
    base = np.floor(raw).astype(int)
    for k in np.argsort(-(raw - base))[: n - base.sum()]:
        base[k] += 1
    return dict(zip(classes, base))


def label_counts(labels):
    c, n = np.unique(np.asarray(labels, dtype=object), return_counts=True)
    return dict(zip(c, n))
