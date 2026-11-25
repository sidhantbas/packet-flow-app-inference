"""Experiment 084: pair verifiers for production's Task 1 calls (protocol: experiments/084_pair_verifiers.md, frozen first;
stage 1: VX passed its gate, VM and VG failed).

Usage: python src/exp084_pair_verifiers.py --arm VX|ALL [--seed N --ref RUN_ID]
VX: every flow production calls x is re-decided by a balanced SoftVote trained only on the google and x rows of the training
fold (34 production columns). ALL: 083 (instagram calls vs google) + VX, each applied to production's original call.
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate
from models import SoftVote, task1_meta_gate
from runlog import record_run

TASK = "task1_static"
ARMS = {"VX": {"x": ("google", "x")},
        "ALL": {"instagram": ("google", "instagram"), "x": ("google", "x")}}


class PairVerifiers(BaseEstimator, ClassifierMixin):
    def __init__(self, arm="VX", seed=0):
        self.arm = arm
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y)
        # Pinned to the 034 model (production when this ran; TASK_MODELS moved to 084 ALL on 2026-10-09).
        self.base_ = task1_meta_gate(self.seed).fit(X, y)
        self.ver_ = {}
        for call, pair in ARMS[self.arm].items():
            m = np.isin(y, pair)
            self.ver_[call] = SoftVote(seed=self.seed).fit(X.loc[m], y[m])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        base = np.asarray(self.base_.predict(X), dtype=object)
        p = base.copy()
        for call, ver in self.ver_.items():
            m = base == call
            if m.any():
                p[m] = ver.predict(X.loc[m])
        return p


def factory(arm):
    def f(seed):
        return PairVerifiers(arm=arm, seed=seed)
    f.__name__ = f"pair_verifiers_{arm}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    arm = args[args.index("--arm") + 1]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats, f = TASK_FEATURES[TASK], factory(arm)
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
    rid = record_run("084", arm + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats,
                     reference=ref, question=f"Task 1 084 arm {arm}: pair verifiers {ARMS[arm]}; cv_seed {seed}",
                     config={"arm": arm, "verifiers": {k: list(v) for k, v in ARMS[arm].items()},
                             "verifier_model": "balanced SoftVote on the pair's rows, 34 production columns",
                             "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
