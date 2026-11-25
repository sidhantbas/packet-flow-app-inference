"""Experiment 028: "two clerks" for Task 1 (whole-run expert + opening expert), from the error decoding of 2026-10-01:
of the 44 Task 1 flows wrong in >= 5/10 CV repeats, the Task 2 model gets 22 mostly right.

Variants fixed before running: avg (mean probabilities), confident (per flow, the more confident expert).
Features: cv.task1_with_prefix_features (17 Task 1 + 17 prefix-5 columns; the opening expert uses the 12 prefix-5
columns without timing). Facebook calls of the 17-column model kept. Confirmation on 2027/2028 only after a pass.
Variant added after seeing seed 2026 (Instagram -0.06): avg_meta_whole; held to all 5 seeds.
Usage: python src/exp028_two_clerks.py [avg|confident|avg_meta_whole ...] [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

from cv import TASKS, TASK_FEATURES, evaluate
from models import TwoClerks
from runlog import record_run

T1 = TASKS[0]

if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    for mode in [a for a in args if a in ("avg", "confident", "avg_meta_whole")] or ["avg", "confident"]:
        f = lambda s, m=mode: TwoClerks(seed=s, mode=m)
        t0 = datetime.now(timezone.utc)
        record_run("028", f"two_clerks_{mode}" + ("" if seed == 2026 else f"_s{seed}"),
                   {T1: evaluate(T1, TASK_FEATURES[T1], f, cv_seed=seed)}, model_factory=f, feature_fn=TASK_FEATURES[T1],
                   reference=ref, question=f"Task 1 two clerks ({mode}) vs champion, cv_seed {seed}?",
                   config={"model": f"TwoClerks(mode={mode})", "cv_seed": seed}, started=t0)
