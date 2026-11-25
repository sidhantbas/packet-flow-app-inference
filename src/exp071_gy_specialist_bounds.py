"""Experiment 071: google-vs-youtube specialist with the 070 largest-packet bounds (protocol:
experiments/071_gy_specialist_bounds.md, frozen first; post hoc, BETTER on all five seeds required).

Usage: python src/exp071_gy_specialist_bounds.py --arm T1S0|T1SB|T2S0|T2SB [--seed N --ref RUN_ID]
       python src/exp071_gy_specialist_bounds.py --production-t2 --seed N   (Task 2 production reference)
Production of the task is trained on its production columns; flows it predicts google or youtube are re-decided by a
balanced SoftVote trained on the google and youtube rows (with or without the two bound columns).
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate
from exp070_largest_up_packet_bounds import t1_plus_bounds, t2_plus_bounds
from models import TASK_MODELS, SoftVote
from runlog import record_run

PAIR = ("google", "youtube")
BOUNDS = {"task1_static": ["p5_up_max_lo", "p5_up_max_hi"], "task2_realtime_prefix5": ["up_max_lo", "up_max_hi"]}


class GYStage(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0, task="task1_static", use_bounds=False):
        self.seed, self.task, self.use_bounds = seed, task, use_bounds

    def fit(self, X, y):
        y = np.asarray(y)
        b = BOUNDS[self.task]
        self.base_cols_ = [c for c in X.columns if c not in b]
        self.spec_cols_ = self.base_cols_ + (b if self.use_bounds else [])
        self.base_ = TASK_MODELS[self.task](self.seed).fit(X[self.base_cols_], y)
        m = np.isin(y, PAIR)
        self.spec_ = SoftVote(seed=self.seed).fit(X.loc[m, self.spec_cols_], y[m])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        p = np.asarray(self.base_.predict(X[self.base_cols_]), dtype=object)
        m = np.isin(p, PAIR)
        if m.any():
            p[m] = self.spec_.predict(X.loc[m, self.spec_cols_])
        return p


ARMS = {"T1S0": ("task1_static", t1_plus_bounds, False), "T1SB": ("task1_static", t1_plus_bounds, True),
        "T2S0": ("task2_realtime_prefix5", t2_plus_bounds, False), "T2SB": ("task2_realtime_prefix5", t2_plus_bounds, True)}


def make_factory(arm):
    task, _, ub = ARMS[arm]

    def f(seed):
        return GYStage(seed=seed, task=task, use_bounds=ub)
    f.__name__ = f"gy_stage_{arm.lower()}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    t0 = datetime.now(timezone.utc)
    if "--production-t2" in args:
        task = "task2_realtime_prefix5"
        f, feats = TASK_MODELS[task], TASK_FEATURES[task]
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("071", f"production_t2_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 2 production reference on cv_seed {seed} (for 071 confirmation)",
                         config={"model": "task2_model", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        task, feats, ub = ARMS[arm]
        f = make_factory(arm)
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("071", arm + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"{task} 071 arm {arm}: google-vs-youtube specialist {'with' if ub else 'without'} bounds; cv_seed {seed}",
                         config={"arm": arm, "use_bounds": ub, "cv_seed": seed, "features": feats.__name__,
                                 "origin": "post hoc from 070; test arms need BETTER on all five seeds"}, started=t0)
    print(rid)
