"""Experiment 025: self-training with unlabelled flows (design fixed in TODO.md on 2026-09-30, before running).

In each CV fold the unlabelled pool = the fold's held-out flows (features only) + the 81 test flows of the same task
(features only). Pseudo-labels: champion prediction with confidence ≥ 0.9, never facebook/instagram; refit once.
Only held-out flows are scored. Each task uses its own feature function (Task 2: Task 2 files only).
Unlabelled test features are used for training: disclose in the report if adopted.
Usage: python src/exp025_self_training.py [2026|2027|2028 ...]   (default 2026)
"""
import sys
from datetime import datetime, timezone

import pandas as pd

from cv import DATA, TASK_FEATURES, TASKS, evaluate
from models import SelfTrain, TASK_MODELS
from runlog import load_champions, load_index, record_run


def test_features(task):
    return TASK_FEATURES[task](pd.read_csv(DATA / task / "test_features.csv")).reset_index(drop=True)


def factory(task):
    pool = test_features(task)
    return lambda s: SelfTrain(TASK_MODELS[task], seed=s, extra_pool=pool)


def references(seed):
    if seed == 2026:
        c = load_champions()
        return {t: c[t]["run_id"] for t in TASKS}
    idx = {e["name"]: e["run_id"] for e in load_index() if e["experiment"] == "025"}
    return idx.get(f"champions_s{seed}")


if __name__ == "__main__":
    for seed in [int(a) for a in sys.argv[1:]] or [2026]:
        if seed == 2026:
            refs = references(seed)
        else:
            t0 = datetime.now(timezone.utc)
            refs = record_run("025", f"champions_s{seed}",
                              {t: evaluate(t, TASK_FEATURES[t], TASK_MODELS[t], cv_seed=seed) for t in TASKS},
                              reference=None, model_factory=TASK_MODELS[TASKS[0]],
                              question=f"Reference: current TASK_MODELS, cv_seed {seed}.",
                              config={"model": "TASK_MODELS", "cv_seed": seed}, started=t0)
        for t in TASKS:
            t0 = datetime.now(timezone.utc)
            ref = refs[t] if isinstance(refs, dict) else refs
            record_run("025", f"{'t1' if t == TASKS[0] else 't2'}_selftrain_s{seed}",
                       {t: evaluate(t, TASK_FEATURES[t], factory(t), cv_seed=seed)}, reference=ref,
                       model_factory=factory(t), feature_fn=TASK_FEATURES[t],
                       question=f"Self-training (0.9, no fb/ig pseudo-labels), {t}, cv_seed {seed}?",
                       config={"model": "SelfTrain(TASK_MODELS)", "threshold": 0.9, "exclude": ["facebook", "instagram"],
                               "pool": "held-out fold + test features", "cv_seed": seed}, started=t0)
