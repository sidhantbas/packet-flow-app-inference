"""Experiment 058: captured flows as a never-predicted "other" class in Task 1 (protocol:
experiments/058_capture_other_class.md, frozen first; idea is post hoc, so full five-seed rule v2).

Usage: python src/exp058_capture_other_class.py --arm O15|O149 [--seed N --ref RUN_ID]
       python src/exp058_capture_other_class.py --production --seed N   (reference on a confirmation seed)
The production model is fitted on the original rows plus captured rows labelled "other" (training folds only); held-out
flows it labels "other" get the prediction of production fitted on the original rows of the same fold.
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate
from exp056_capture_augmentation import captured_rows
from models import TASK_MODELS
from runlog import record_run

TASK = "task1_static"
OTHER = "other"
DOSE = 0.10
FALLBACK_LOG = []


class OtherClass(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y)
        orig = y != OTHER
        self.aug_ = TASK_MODELS[TASK](self.seed).fit(X, y)
        self.base_ = TASK_MODELS[TASK](self.seed).fit(X[orig], y[orig])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        p = np.asarray(self.aug_.predict(X), dtype=object)
        m = p == OTHER
        if m.any():
            p[m] = np.asarray(self.base_.predict(X.loc[m]), dtype=object)
        print(f"FALLBACK {int(m.sum())} {len(p)}", flush=True)
        return p


def other_model(seed):
    return OtherClass(seed=seed)


def make_resample(arm):
    C, yc = captured_rows()
    keep = np.isin(yc, ("facebook", "instagram"))
    C, yc = C[keep].reset_index(drop=True), yc[keep]
    idx = {a: np.flatnonzero(yc == a) for a in ("facebook", "instagram")}

    def resample(X_tr, y_tr, seed):
        if arm == "O15":
            rng = np.random.default_rng(seed)
            pick = np.concatenate([rng.choice(i, size=int(round(DOSE * len(i))), replace=False) for i in idx.values()])
        else:
            pick = np.arange(len(C))
        Cx = C.iloc[pick][X_tr.columns].copy()
        Cx.index = np.arange(len(Cx)) + int(X_tr.index.max()) + 1
        return pd.concat([X_tr, Cx]), pd.concat([pd.Series(np.asarray(y_tr), index=X_tr.index),
                                                 pd.Series([OTHER] * len(Cx), index=Cx.index)])
    resample.n_added = 15 if arm == "O15" else len(C)
    return resample


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    sfx = "" if seed == 2026 else f"_s{seed}"
    if "--production" in args:
        f = TASK_MODELS[TASK]
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("058", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 1 production reference on cv_seed {seed} (for 058 confirmation)",
                         config={"model": "task1_meta_gate", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        if arm not in ("O15", "O149"):
            raise SystemExit("arm must be O15 or O149")
        rs = make_resample(arm)
        res = {TASK: evaluate(TASK, feats, other_model, resample=rs, cv_seed=seed)}
        rid = record_run("058", f"{arm}{sfx}", res, model_factory=other_model, feature_fn=feats, reference=ref,
                         question=f"Task 1 058 arm {arm}: captured flows as a never-predicted 'other' class; cv_seed {seed}",
                         config={"arm": arm, "cv_seed": seed, "features": feats.__name__, "other_rows_per_fold": rs.n_added,
                                 "fallback": "production fitted on the original rows of the fold",
                                 "origin": "post hoc (057 D10 side effect); full five-seed rule v2",
                                 "user_decision": "2026-10-09 run despite gates 1-2 failing (056 override)"}, started=t0)
    print(rid)
