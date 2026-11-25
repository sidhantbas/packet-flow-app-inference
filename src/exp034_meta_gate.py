"""Experiment 034: hierarchical Meta gate for Task 1 (from the Facebook/Instagram data-flow analysis, 2026-10-01).
Settings fixed before running (balanced SoftVote gate on all Task 1 columns; plain probability factorisation).
Reference: Task 1 champion (two clerks, 028). Confirmation on 2027/2028 vs the 028 runs at those seeds, only after a pass.
034b "rescue" (designed after seeing 034: only flows sent outside Meta can move into Meta) must pass on cv_seeds
2026-2030, each vs the two-clerks run on the same folds.
Usage: python src/exp034_meta_gate.py [rescue] [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

from cv import TASKS, TASK_FEATURES, evaluate
from models import MetaGate
from runlog import record_run

T1 = TASKS[0]

if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    mode = "rescue" if "rescue" in args else "full"
    f = lambda s, m=mode: MetaGate(seed=s, mode=m)
    t0 = datetime.now(timezone.utc)
    record_run("034", ("meta_gate" if mode == "full" else "meta_rescue") + ("" if seed == 2026 else f"_s{seed}"),
               {T1: evaluate(T1, TASK_FEATURES[T1], f, cv_seed=seed)}, model_factory=f, feature_fn=TASK_FEATURES[T1],
               reference=ref, question=f"Task 1: two clerks + Meta gate ({mode}), cv_seed {seed}?",
               config={"model": f"MetaGate(TwoClerks avg_meta_whole, mode={mode})", "cv_seed": seed}, started=t0)
