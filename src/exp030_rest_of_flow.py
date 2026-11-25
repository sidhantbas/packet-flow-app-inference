"""Experiment 030: Task 1 + exact "after-opening" statistics (packets 6..N) derived from the Task 1 and Task 2 rows of
the same flow. Only the given dataset (user rule, 2026-10-01). Variants fixed before running:
  rest_add   022 features (17 + 17 prefix) + 11 rest columns
  rest_swap  17 Task 1 columns + 11 rest columns (no raw prefix columns)
Model: task1_model (KeepClassBlend; its first part = the 17 Task 1 columns; facebook kept). Confirm 2027/2028 after a pass.
Usage: python src/exp030_rest_of_flow.py [rest_add|rest_swap ...] [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

from cv import TASKS, evaluate, task1_prefix_rest_features, task1_rest_features
from models import task1_model
from runlog import record_run

T1 = TASKS[0]
FEATS = {"rest_add": task1_prefix_rest_features, "rest_swap": task1_rest_features}

if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    for name in [a for a in args if a in FEATS] or list(FEATS):
        t0 = datetime.now(timezone.utc)
        record_run("030", name + ("" if seed == 2026 else f"_s{seed}"),
                   {T1: evaluate(T1, FEATS[name], task1_model, cv_seed=seed)}, model_factory=task1_model,
                   feature_fn=FEATS[name], reference=ref,
                   question=f"Task 1 + rest-of-flow statistics ({name}) vs champion, cv_seed {seed}?",
                   config={"model": "task1_model", "features": FEATS[name].__name__, "cv_seed": seed}, started=t0)
