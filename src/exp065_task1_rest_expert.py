"""Experiment 065: a rest-of-flow expert inside the Task 1 production model (protocol: experiments/065_task1_rest_expert.md,
frozen first).

Usage: python src/exp065_task1_rest_expert.py --arm R|RT [--seed N --ref RUN_ID]
Features: cv.task1_prefix_rest_features (34 production columns + 11 rest-of-flow columns). The production experts and gate
see only the 34 production columns; one extra balanced SoftVote sees the rest-of-flow columns (+ transport in RT).
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import evaluate, task1_prefix_rest_features
from models import MetaGate, SoftVote
from runlog import record_run

TASK = "task1_static"
REST = ["r_count_up", "r_bytes_up", "r_mean_size_up", "r_std_size_up", "r_count_down", "r_bytes_down", "r_mean_size_down",
        "r_std_size_down", "r_duration", "r_mean_iat", "r_std_iat"]
ARMS = {"R": REST, "RT": REST + ["transport"]}


class RestExpertMetaGate(MetaGate):
    def __init__(self, seed=0, mode="full", arm="R"):
        super().__init__(seed=seed, mode=mode)
        self.arm = arm

    def fit(self, X, y):
        self.base_cols_ = [c for c in X.columns if c not in REST]
        super().fit(X[self.base_cols_], y)
        self.rest_ = SoftVote(seed=self.seed).fit(X[ARMS[self.arm]], np.asarray(y))
        assert list(self.rest_.classes_) == list(self.classes_)
        return self

    def predict(self, X):
        Xr, X = X[ARMS[self.arm]], X[self.base_cols_]
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = (pw + po + self.rest_.predict_proba(Xr)) / 3                 # 065: was (pw + po) / 2
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
        return RestExpertMetaGate(seed=seed, arm=arm)
    f.__name__ = f"rest_expert_{arm.lower()}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    arm = args[args.index("--arm") + 1]
    feats, f = task1_prefix_rest_features, make_factory(arm)
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
    rid = record_run("065", arm + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"Task 1 065 arm {arm}: rest-of-flow expert inside the Meta-gate model; cv_seed {seed}",
                     config={"arm": arm, "extra_expert_cols": ARMS[arm], "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
