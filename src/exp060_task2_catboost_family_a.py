"""Experiment 060: Task 2 with unweighted CatBoost and Charles's family A features (protocol:
experiments/060_task2_catboost_family_a.md, frozen first).

Usage: python src/exp060_task2_catboost_family_a.py --arm CB|SVCB|A [--seed N --ref RUN_ID]
       python src/exp060_task2_catboost_family_a.py --production --seed N   (production reference on a confirmation seed)
All arms keep production's no-timing Task 2 columns and its unweighted facebook/instagram stage (014).
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate, no_timing_features
from exp027_handoff import fam_a
from models import TASK_MODELS, SoftVote, catboost
from runlog import record_run

TASK = "task2_realtime_prefix5"
PAIR = ("facebook", "instagram")


class Task2Variant(BaseEstimator, ClassifierMixin):
    """base "cb": unweighted CatBoost; "svcb": mean proba of balanced SoftVote and unweighted CatBoost; "sv": balanced
    SoftVote (production). Flows the base calls facebook/instagram are re-decided by an unweighted SoftVote on those two."""

    def __init__(self, seed=0, base="cb"):
        self.seed, self.base = seed, base

    def fit(self, X, y):
        y = np.asarray(y)
        self.models_ = []
        if self.base in ("sv", "svcb"):
            self.models_.append(SoftVote(seed=self.seed).fit(X, y))
        if self.base in ("cb", "svcb"):
            self.models_.append(catboost(self.seed, class_weight=None).fit(X, y))
        self.classes_ = np.asarray(self.models_[0].classes_)
        assert all((np.asarray(m.classes_) == self.classes_).all() for m in self.models_)
        m = np.isin(y, PAIR)
        self.spec_ = SoftVote(seed=self.seed, class_weight=None).fit(X.loc[m], y[m])
        return self

    def predict(self, X):
        p = np.mean([m.predict_proba(X) for m in self.models_], axis=0)
        pred = self.classes_[p.argmax(axis=1)].astype(object)
        m = np.isin(pred, PAIR)
        if m.any():
            pred[m] = self.spec_.predict(X.loc[m])
        return pred


def model_cb(seed):
    return Task2Variant(seed=seed, base="cb")


def model_svcb(seed):
    return Task2Variant(seed=seed, base="svcb")


def model_sv(seed):
    return Task2Variant(seed=seed, base="sv")


def no_timing_plus_a(X):
    """Production Task 2 columns + family A (027), computed from the Task 2 file's own columns only."""
    B = no_timing_features(X).reset_index(drop=True)
    for k, v in fam_a(X).items():
        B[k] = np.asarray(v)
    return B


no_timing_plus_a.extra_data = []

ARMS = {"CB": (model_cb, no_timing_features), "SVCB": (model_svcb, no_timing_features), "A": (model_sv, no_timing_plus_a)}

if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    t0 = datetime.now(timezone.utc)
    sfx = "" if seed == 2026 else f"_s{seed}"
    if "--production" in args:
        f, feats = TASK_MODELS[TASK], TASK_FEATURES[TASK]
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("060", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 2 production reference on cv_seed {seed} (for 060 confirmation)",
                         config={"model": "task2_model", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        f, feats = ARMS[arm]
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("060", f"{arm}{sfx}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"Task 2 060 arm {arm} vs production; cv_seed {seed}",
                         config={"arm": arm, "cv_seed": seed, "features": feats.__name__,
                                 "stage": "unweighted SoftVote facebook/instagram (014)"}, started=t0)
    print(rid)
