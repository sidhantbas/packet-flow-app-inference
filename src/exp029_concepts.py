"""Experiment 029: "teach concepts first" for Task 1 (zero-shot idea from the clerk analogy, 2026-10-01).

Concepts are learned from or defined over ALL apps' flows, so rare apps (Facebook) borrow from every app's examples.
  rules     6 behaviour flags with first-principles thresholds fixed before running (models.concept_flags)
  clusters  distances to 8 KMeans "kinds of run" fitted without labels inside each training fold
Both are added to the input of the Task 1 champion (task1_model; its 34-column part sees them; facebook rule kept).
Confirmation on 2027/2028 only after a pass at 2026.
Usage: python src/exp029_concepts.py [rules|clusters ...] [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

import pandas as pd

from cv import TASKS, TASK_FEATURES, evaluate, load_task
from models import ConceptAugment, T1_COLS, concept_flags, task1_model
from runlog import record_run

T1 = TASKS[0]


def describe_rules():
    X, y = load_task(T1)
    C = concept_flags(X[list(T1_COLS)].assign(transport=0))
    print("concept flags by app (train + validation flows):")
    print(C.groupby(y.values).sum().assign(flows=y.value_counts()).to_string())


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    if seed == 2026 and "--quiet" not in args:
        describe_rules()
    for kind in [a for a in args if a in ("rules", "clusters")] or ["rules", "clusters"]:
        f = lambda s, k=kind: ConceptAugment(task1_model, seed=s, kind=k)
        t0 = datetime.now(timezone.utc)
        record_run("029", f"concepts_{kind}" + ("" if seed == 2026 else f"_s{seed}"),
                   {T1: evaluate(T1, TASK_FEATURES[T1], f, cv_seed=seed)}, model_factory=f, feature_fn=TASK_FEATURES[T1],
                   reference=ref, question=f"Task 1 + {kind} concepts vs champion, cv_seed {seed}?",
                   config={"model": f"ConceptAugment(task1_model, {kind})", "cv_seed": seed}, started=t0)
