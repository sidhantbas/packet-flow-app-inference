"""Experiment 085 stage 2: google-vs-mozilla verifier for Task 2 production's mozilla calls (protocol:
experiments/085_pair_verifier_sweep.md, frozen first; stage 1: only T2-MG passed its gate).

Usage: python src/exp085_task2_verifier.py [--seed N --ref RUN_ID]
       python src/exp085_task2_verifier.py --production --seed N   (production Task 2 reference on a confirmation seed)
Every flow production Task 2 calls mozilla is re-decided by a balanced SoftVote trained only on the google and mozilla rows of
the training fold (12 no-timing columns, Task 2 files only). No other call changes.
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate
from models import TASK_MODELS, SoftVote
from runlog import record_run

TASK = "task2_realtime_prefix5"


class MozillaVerifier(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y)
        self.base_ = TASK_MODELS[TASK](self.seed).fit(X, y)
        m = np.isin(y, ("google", "mozilla"))
        self.ver_ = SoftVote(seed=self.seed).fit(X.loc[m], y[m])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        p = np.asarray(self.base_.predict(X), dtype=object)
        m = p == "mozilla"
        if m.any():
            p[m] = self.ver_.predict(X.loc[m])
        return p


def verifier(seed):
    return MozillaVerifier(seed=seed)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    if "--production" in args:
        f = TASK_MODELS[TASK]
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("085", f"t2_production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 2 production reference on cv_seed {seed} (for 085 confirmation)",
                         config={"model": "task2_model", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        res = {TASK: evaluate(TASK, feats, verifier, cv_seed=seed)}
        rid = record_run("085", "T2MG" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=verifier, feature_fn=feats,
                         reference=ref, question=f"Task 2 085: google-vs-mozilla verifier for mozilla calls; cv_seed {seed}",
                         config={"verifier": "balanced SoftVote on google + mozilla rows, 12 no-timing columns", "cv_seed": seed,
                                 "features": feats.__name__}, started=t0)
    print(rid)
