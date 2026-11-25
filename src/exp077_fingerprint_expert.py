"""Experiment 077: the 076 V3 opening-fingerprint view as a separate expert in Task 1 (protocol:
experiments/077_fingerprint_expert.md, frozen first; post hoc from 076, BETTER on all five seeds required).

Usage: python src/exp077_fingerprint_expert.py --arm F|FR [--seed N --ref RUN_ID]
Production experts and gate see the 34 production columns; extra balanced SoftVote experts see the V3 fingerprint columns
(and, in FR, the 11 rest-of-flow columns). p = mean of all experts; later production rules unchanged.
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cv import evaluate, task1_prefix_rest_features
from exp065_task1_rest_expert import REST
from exp076_view_screen import view_table
from models import MetaGate, SoftVote
from runlog import record_run

TASK = "task1_static"


def features(X):
    B = task1_prefix_rest_features(X)
    V = view_table(X)
    return pd.concat([B.reset_index(drop=True), V[[c for c in V.columns if c.startswith("v3_")]].reset_index(drop=True)], axis=1)


features.extra_data = task1_prefix_rest_features.extra_data
V3 = None  # filled from the first table


class ExtraExpertsMetaGate(MetaGate):
    def __init__(self, seed=0, mode="full", arm="F"):
        super().__init__(seed=seed, mode=mode)
        self.arm = arm

    def fit(self, X, y):
        y = np.asarray(y)
        v3 = [c for c in X.columns if c.startswith("v3_")]
        self.base_cols_ = [c for c in X.columns if c not in REST and c not in v3]
        self.expert_cols_ = [v3] + ([REST] if self.arm == "FR" else [])
        super().fit(X[self.base_cols_], y)
        self.extra_ = [SoftVote(seed=self.seed).fit(X[c], y) for c in self.expert_cols_]
        assert all(list(m.classes_) == list(self.classes_) for m in self.extra_)
        return self

    def predict(self, X):
        extras = [m.predict_proba(X[c]) for m, c in zip(self.extra_, self.expert_cols_)]
        X = X[self.base_cols_]
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = np.mean([pw, po] + extras, axis=0)                       # 077: was (pw + po) / 2
        g = self.gate_.predict_proba(X)[:, list(self.gate_.classes_).index("meta")]
        meta = np.isin(cls, self.META)
        pm = p[:, meta].sum(axis=1, keepdims=True)
        pr = p[:, ~meta].sum(axis=1, keepdims=True)
        q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
        pred = cls[q.argmax(axis=1)]
        in_meta = np.isin(pred, self.META)
        fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
        pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
        whole = c.whole_.predict(X)
        w_meta = np.isin(whole, self.META)
        pred[w_meta] = whole[w_meta]
        first = c.whole_.models_[0].predict(X[c.whole_.cols_[0]])
        pred[first == "facebook"] = "facebook"
        return pred


def make_factory(arm):
    def f(seed):
        return ExtraExpertsMetaGate(seed=seed, arm=arm)
    f.__name__ = f"extra_experts_{arm.lower()}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    arm = args[args.index("--arm") + 1]
    f = make_factory(arm)
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, features, f, cv_seed=seed)}
    rid = record_run("077", arm + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=features, reference=ref,
                     question=f"Task 1 077 arm {arm}: opening-fingerprint expert{' + rest expert' if arm == 'FR' else ''}; cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed, "features": features.__name__,
                             "origin": "post hoc from the 076 screen; BETTER on all five seeds required"}, started=t0)
    print(rid)
