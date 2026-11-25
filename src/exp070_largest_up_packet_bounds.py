"""Experiment 070: bounds on the largest outgoing packet of the first five packets (protocol:
experiments/070_largest_up_packet_bounds.md, frozen first).

Usage: python src/exp070_largest_up_packet_bounds.py --arm T1A|T1B|T2A [--seed N --ref RUN_ID]
up_max_lo = m + s / sqrt(n - 1), up_max_hi = m + s * sqrt(n - 1) for n >= 2 (Samuelson; exact when n = 2), m for n = 1,
0 for n = 0; n, m, s = up-direction count, mean and population std of the first five packets.
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cv import _PREFIX_FILES, evaluate, no_timing_features, task1_with_prefix_features
from models import TASK_MODELS, MetaGate, PairSpecialist, SoftVote, TwoClerks, task1_model
from runlog import record_run

NEW = ["up_max_lo", "up_max_hi"]


def bounds(n, m, s):
    n, m, s = (np.asarray(v, float) for v in (n, m, s))
    k = np.sqrt(np.clip(n - 1, 1, None))
    lo = np.where(n >= 2, m + s / k, np.where(n == 1, m, 0.0))
    hi = np.where(n >= 2, m + s * k, np.where(n == 1, m, 0.0))
    return lo, hi


def t1_plus_bounds(X):
    B = task1_with_prefix_features(X)
    lo, hi = bounds(B.p5_packet_count_up, B.p5_mean_pkt_size_up, B.p5_std_pkt_size_up)
    return B.assign(p5_up_max_lo=lo, p5_up_max_hi=hi)


t1_plus_bounds.extra_data = _PREFIX_FILES


def t2_plus_bounds(X):
    B = no_timing_features(X).reset_index(drop=True)
    lo, hi = bounds(X.packet_count_up, X.mean_pkt_size_up, X.std_pkt_size_up)
    return B.assign(up_max_lo=lo, up_max_hi=hi)


class TwoClerksB(TwoClerks):
    OPEN_COLS = TwoClerks.OPEN_COLS + ("p5_up_max_lo", "p5_up_max_hi")


class MetaGateB(MetaGate):
    """MetaGate whose opening expert also sees the two bound columns (arm T1B)."""

    def fit(self, X, y):
        y = np.asarray(y)
        self.clerks_ = TwoClerksB(seed=self.seed, mode="avg_meta_whole").fit(X, y)
        self.gate_ = SoftVote(seed=self.seed).fit(X, np.where(np.isin(y, self.META), "meta", "rest"))
        self.classes_ = self.clerks_.classes_
        return self


def meta_gate_b(seed):
    return MetaGateB(seed=seed)


ARMS = {"T1A": ("task1_static", t1_plus_bounds, TASK_MODELS["task1_static"]),
        "T1B": ("task1_static", t1_plus_bounds, meta_gate_b),
        "T2A": ("task2_realtime_prefix5", t2_plus_bounds, TASK_MODELS["task2_realtime_prefix5"])}

if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    arm = args[args.index("--arm") + 1]
    task, feats, f = ARMS[arm]
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    rid = record_run("070", arm + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"{task} 070 arm {arm}: bounds on the largest up packet of the opening; cv_seed {seed}",
                     config={"arm": arm, "new_columns": NEW, "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
