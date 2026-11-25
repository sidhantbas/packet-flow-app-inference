"""Experiment 095: the leader's "disclosed-count analysis" simulated in CV (protocol:
experiments/095_disclosed_count_simulation.md, frozen first). The test label counts are never read: arm A2's "disclosed"
counts are the held-out fold's own label counts (train + validation labels only).

Usage: python src/exp095_disclosed_counts.py --task task1_static|task2_realtime_prefix5 --arm A0|A1|A2|A3
"""
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV

from cv import TASK_FEATURES, evaluate, load_task
from models import SoftVote
from runlog import record_run

T1, T2 = "task1_static", "task2_realtime_prefix5"
_Y = {}


def labels_of(task):
    """Train + validation labels in the row order of cv.evaluate (verified: feature rows are indexed 0..n-1)."""
    if task not in _Y:
        _Y[task] = np.asarray(load_task(task)[1].values, dtype=object)
    return _Y[task]


def quota_assign(P, classes, counts):
    """Labels maximising the summed log-probability with exactly counts[c] flows of class c (linear assignment)."""
    slots = [k for k, c in enumerate(classes) for _ in range(int(counts.get(c, 0)))]
    assert len(slots) == P.shape[0]
    cost = -np.log(np.clip(P[:, slots], 1e-9, None))
    rows, cols = linear_sum_assignment(cost)
    out = np.empty(P.shape[0], dtype=object)
    out[rows] = np.asarray(classes, dtype=object)[np.asarray(slots)[cols]]
    return out


def prior_counts(classes, priors, n):
    raw = np.array([priors.get(c, 0.0) * n for c in classes])
    base = np.floor(raw).astype(int)
    for k in np.argsort(-(raw - base))[: n - base.sum()]:
        base[k] += 1
    return dict(zip(classes, base))


class LeaderStyle(BaseEstimator, ClassifierMixin):
    def __init__(self, task=T2, arm="A1", seed=0):
        self.task, self.arm, self.seed = task, arm, seed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        sv = SoftVote(seed=self.seed)
        self.model_ = sv.fit(X, y) if self.arm == "A0" else CalibratedClassifierCV(sv, method="sigmoid", cv=3).fit(X, y)
        self.classes_ = np.asarray(self.model_.classes_, dtype=object)
        c, n = np.unique(y, return_counts=True)
        self.priors_ = dict(zip(c, n / n.sum()))
        return self

    def predict(self, X):
        P = self.model_.predict_proba(X)
        if self.arm in ("A0", "A1"):
            return self.classes_[P.argmax(axis=1)]
        if self.arm == "A2":
            yb = labels_of(self.task)[np.asarray(X.index)]
            c, n = np.unique(yb, return_counts=True)
            counts = dict(zip(c, n))
        else:
            counts = prior_counts(list(self.classes_), self.priors_, len(X))
        return quota_assign(P, list(self.classes_), counts)


def factory(task, arm):
    def f(seed):
        return LeaderStyle(task=task, arm=arm, seed=seed)
    f.__name__ = f"leader_style_{arm.lower()}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    task, arm = args[args.index("--task") + 1], args[args.index("--arm") + 1]
    feats, f = TASK_FEATURES[task], factory(task, arm)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=2026)}
    rid = record_run("095", f"{'T1' if task == T1 else 'T2'}_{arm}", res, model_factory=f, feature_fn=feats, reference="champion",
                     question=f"{task} 095 arm {arm}: leader-style calibrated ensemble / quota labelling (CV simulation; test counts never read)",
                     config={"arm": arm, "calibration": None if arm == "A0" else "sigmoid, cv=3",
                             "counts": {"A2": "held-out fold's own labels (simulated disclosure)", "A3": "training class shares"}.get(arm),
                             "cv_seed": 2026, "features": feats.__name__}, started=t0)
    print(rid)
