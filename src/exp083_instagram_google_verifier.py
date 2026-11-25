"""Experiment 083: google-vs-instagram verifier for production's instagram calls (protocol:
experiments/083_instagram_google_verifier.md, frozen first; stage 1 passed its gate).

Usage: python src/exp083_instagram_google_verifier.py [--seed N --ref RUN_ID]
Production Task 1 model; every flow it calls instagram is re-decided by a balanced SoftVote trained only on the google and
instagram rows of the training fold (34 production columns). No other call changes.
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate
from models import SoftVote, task1_meta_gate
from runlog import record_run

TASK = "task1_static"


class InstagramVerifier(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y)
        # Pinned to the 034 model (production when this ran; TASK_MODELS moved to 084 ALL on 2026-10-09).
        self.base_ = task1_meta_gate(self.seed).fit(X, y)
        m = np.isin(y, ("google", "instagram"))
        self.ver_ = SoftVote(seed=self.seed).fit(X.loc[m], y[m])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        p = np.asarray(self.base_.predict(X), dtype=object)
        m = p == "instagram"
        if m.any():
            p[m] = self.ver_.predict(X.loc[m])
        return p


def verifier(seed):
    return InstagramVerifier(seed=seed)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, verifier, cv_seed=seed)}
    rid = record_run("083", "IGV" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=verifier, feature_fn=feats,
                     reference=ref, question=f"Task 1 083: google-vs-instagram verifier for instagram calls; cv_seed {seed}",
                     config={"verifier": "balanced SoftVote on google + instagram rows, 34 production columns", "cv_seed": seed,
                             "features": feats.__name__}, started=t0)
    print(rid)
