"""Experiment 020: exact packet sizes on task 2.

Every task 2 flow has exactly 5 packets and std_pkt_size is the population std (ddof 0). So in a direction
with 1 or 2 packets the individual sizes are known exactly: mean ± std (integer for all 282 two-packet
directions). At least one direction has ≤ 2 packets in 329 of 330 flows. Trees cannot form mean ± std, so the
explicit sizes are new usable information. Directions with ≥ 3 packets get -1 (unknown).

  sizes     champion (task2_model) on the 12 champion columns + small_{up,down}_{min,max}
Usage: python src/exp020_exact_sizes.py [confirm]
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, TASKS, evaluate
from models import task2_model
from runlog import record_run

T2 = TASKS[1]


def exact_sizes(X_raw):
    out = {}
    for d in ("up", "down"):
        n, m, s = X_raw[f"packet_count_{d}"], X_raw[f"mean_pkt_size_{d}"], X_raw[f"std_pkt_size_{d}"]
        known = (n >= 1) & (n <= 2)
        out[f"size_{d}_min"] = np.where(known, m - s, -1.0)
        out[f"size_{d}_max"] = np.where(known, m + s, -1.0)
    return out


def with_sizes(X_raw):
    X = TASK_FEATURES[T2](X_raw)
    for k, v in exact_sizes(X_raw).items():
        X[k] = v
    return X


def run(cv_seed=2026, reference="champion", tag=""):
    t0 = datetime.now(timezone.utc)
    return record_run("020", "sizes" + tag, {T2: evaluate(T2, with_sizes, task2_model, cv_seed=cv_seed)},
                      model_factory=task2_model, feature_fn=with_sizes, reference=reference,
                      question=f"Does adding exact packet sizes help task 2 (cv_seed {cv_seed})?",
                      config={"model": "task2_model", "features": "no_timing + exact sizes", "cv_seed": cv_seed},
                      started=t0)


def confirm():
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("020", f"champion_s{seed}", {T2: evaluate(T2, TASK_FEATURES[T2], task2_model, cv_seed=seed)},
                         reference=None, model_factory=task2_model,
                         question=f"Confirmation reference: task 2 champion, cv_seed {seed}.",
                         config={"model": "task2_model", "cv_seed": seed}, started=t0)
        run(seed, ref, f"_s{seed}")


if __name__ == "__main__":
    confirm() if sys.argv[1:] == ["confirm"] else run()
