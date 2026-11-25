"""Experiment 104: reproduce RahmaniJ's Early-Flow Ensemble (protocol: experiments/104_early_flow_reproduction.md).
One balanced SoftVote on first-5-packet features only, the same predictions for both tasks, optional count assignment
(src/flowkit). Task 1 arms read the Task 2 file's columns for each flow (allowed: Task 2 -> Task 1).

Usage (from the repository root):
  .venv/bin/python src/exp104_early_flow_reproduction.py --smoke
  .venv/bin/python src/exp104_early_flow_reproduction.py --task t2 --arm P --seed 2111      # production reference first
  .venv/bin/python src/exp104_early_flow_reproduction.py --task t2 --arm E1 --seed 2111     # compared with that P run
  .venv/bin/python src/exp104_early_flow_reproduction.py --all                              # both tasks, every arm and seed
  .venv/bin/python src/exp104_early_flow_reproduction.py --analyse
  .venv/bin/python src/exp104_early_flow_reproduction.py --test-effect                      # E0, E0N, E1S on the 81 test flows
Runs go to results/<stamp>_104_<T1|T2>_<arm>_s<seed>/; other evidence to experiments/104_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cv import _PREFIX_FILES, TASK_FEATURES, TIMING, basic_features, evaluate, load_task, no_timing_features, task1_with_prefix_features
from flowkit import DecisionPipeline
from models import TASK_MODELS
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASKS = {"t1": "task1_static", "t2": "task2_realtime_prefix5"}
SEEDS = (2111, 2112, 2113, 2114, 2115)
ARMS = {"E0": ("all", "none"), "E0N": ("notiming", "none"), "E1": ("all", "disclosed"), "E1S": ("all", "shares")}
EVIDENCE = ROOT / "experiments/104_evidence"


def first5_all_t1(X):
    """Task 1 rows -> the Task 2 file's 17 first-5-packet columns for the same flows, named as in the Task 2 file."""
    T = task1_with_prefix_features(X)
    cols = [c for c in T.columns if c.startswith("p5_")]
    return T[cols].set_axis([c[len("p5_"):] for c in cols], axis=1)


def first5_notiming_t1(X):
    return first5_all_t1(X).drop(columns=TIMING)


first5_all_t1.extra_data = first5_notiming_t1.extra_data = _PREFIX_FILES
FEATURES = {("t1", "all"): first5_all_t1, ("t1", "notiming"): first5_notiming_t1,
            ("t2", "all"): basic_features, ("t2", "notiming"): no_timing_features}


def factory(t, arm):
    if arm == "P":
        return TASK_MODELS[TASKS[t]]
    counts = ARMS[arm][1]
    labels = np.asarray(load_task(TASKS[t])[1].values, dtype=object) if counts == "disclosed" else None

    def f(seed):
        return DecisionPipeline(base="softvote", counts=counts, seed=seed, disclosed_labels=labels)
    f.__name__ = f"early_flow_{t}_{arm.lower()}"
    return f


def feats(t, arm):
    return TASK_FEATURES[TASKS[t]] if arm == "P" else FEATURES[(t, ARMS[arm][0])]


def run_id(t, arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_104_{t.upper()}_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(t, arm, seed):
    task, fn, f = TASKS[t], feats(t, arm), factory(t, arm)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, fn, f, cv_seed=seed)}
    rid = record_run("104", f"{t.upper()}_{arm}_s{seed}", res, model_factory=f, feature_fn=fn,
                     reference=None if arm == "P" else run_id(t, "P", seed),
                     question=f"{task} 104 {arm} (Early-Flow Ensemble) on never-used cv_seed {seed}",
                     config={"arm": arm, "task": task, "cv_seed": seed, "features": fn.__name__,
                             "counts": None if arm == "P" else ARMS[arm][1]}, started=t0)
    print(rid, flush=True)


def smoke():
    from sklearn.model_selection import RepeatedStratifiedKFold
    X1, y = load_task(TASKS["t1"])
    X2, _ = load_task(TASKS["t2"])
    A, B = first5_all_t1(X1), basic_features(X2)
    print("Task 1 first-5 columns equal the Task 2 file:", bool((A.values == B.values).all()), list(A.columns) == list(B.columns))
    yv = np.asarray(y.values, dtype=object)
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2111).split(A, yv))
    p1 = factory("t1", "E0")(0).fit(A.iloc[tr], yv[tr]).predict(A.iloc[te])
    p2 = factory("t2", "E0")(0).fit(B.iloc[tr], yv[tr]).predict(B.iloc[te])
    print("E0 predictions identical for Task 1 and Task 2 on fold 0:", bool((np.asarray(p1) == np.asarray(p2)).all()))


def f1(t, rid):
    return pd.read_csv(ROOT / "results" / rid / TASKS[t] / "folds.csv").macro_f1.values


def analyse():
    out = {}
    for t in ("t1", "t2"):
        means = {a: [round(float(f1(t, run_id(t, a, s)).mean()), 4) for s in SEEDS] for a in ["P"] + list(ARMS)}
        pairs = []
        for a, b in (("E0", "P"), ("E0N", "P"), ("E1", "P"), ("E1S", "P"), ("E0", "E0N"), ("E1", "E0"), ("E1S", "E0"), ("E1", "E1S")):
            per = []
            for s in SEEDS:
                d = f1(t, run_id(t, a, s)) - f1(t, run_id(t, b, s))
                per.append([round(float(d.mean()), 4), int((d > 1e-12).sum()), int((d < -1e-12).sum())])
            pairs.append({"a": a, "b": b, "mean_delta": round(float(np.mean([p[0] for p in per])), 4), "per_seed": per})
            print(t, f"{a} vs {b}: {pairs[-1]['mean_delta']:+.4f}", per)
        out[t] = {"means": means, "pairs": pairs}
    same = {a: all((f1("t1", run_id("t1", a, s)) == f1("t2", run_id("t2", a, s))).all() for s in SEEDS) for a in ARMS}
    out["same_fold_scores_both_tasks"] = same
    print("identical fold scores in both tasks:", same)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())
    Xr, y = load_task(TASKS["t2"])
    yv = np.asarray(y.values, dtype=object)
    Xt_raw = load_test(TASKS["t2"])
    out = {}
    for arm in ("E0", "E0N", "E1S"):
        fn = FEATURES[("t2", ARMS[arm][0])]
        p = np.asarray(factory("t2", arm)(0).fit(fn(Xr), yv).predict(fn(Xt_raw)), dtype=object)
        out[arm] = {"predicted_counts": dict(Counter(p))}
        for t in ("t1", "t2"):
            s = np.array([sub[TASKS[t]][f] for f in Xt_raw.flow_id], dtype=object)
            ch = p != s
            out[arm][f"changed_vs_submitted_{t}"] = int(ch.sum())
            out[arm][f"transitions_{t}"] = dict(Counter(f"{a} -> {b}" for a, b in zip(s[ch], p[ch])))
        print(arm, out[arm], flush=True)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2, default=int) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", choices=list(TASKS))
    ap.add_argument("--arm", choices=["P"] + list(ARMS))
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--test-effect", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        smoke()
    elif a.analyse:
        analyse()
    elif a.test_effect:
        test_effect()
    elif a.all:
        for t in ("t1", "t2"):
            for s in SEEDS:
                for arm in ["P"] + list(ARMS):
                    run(t, arm, s)
    else:
        if not (a.task and a.arm and a.seed):
            ap.error("--task, --arm and --seed are required")
        run(a.task, a.arm, a.seed)


if __name__ == "__main__":
    main()
