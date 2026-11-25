"""Experiment 011: follow-ups from 010 on task 2.

  A  drop burst_count from the task 2 champion (only feature with negative importance in 010)
  B  diagnostic: for each task 2 champion error (010-era champion run), does the flow's exact feature vector
     occur in the training part of that fold, and with which labels? Measures what exact-match lookup could fix.
"""
from datetime import datetime, timezone

import pandas as pd

from cv import TASK_FEATURES, evaluate, load_task
from models import SoftVote
from runlog import load_champions, load_oof, record_run

T2 = "task2_realtime_prefix5"


def softvote(s):
    return SoftVote(seed=s)


def no_burst(X):
    return TASK_FEATURES[T2](X).drop(columns=["burst_count"])


def part_a():
    t0 = datetime.now(timezone.utc)
    record_run("011", "t2_drop_burst", {T2: evaluate(T2, no_burst, softvote)}, model_factory=softvote,
               feature_fn=no_burst, question="Does task 2 improve without burst_count?",
               config={"model": "SoftVote", "features": "no_timing_features - burst_count"}, started=t0)


def part_b():
    from sklearn.model_selection import RepeatedStratifiedKFold
    from cv import CV_SEED
    X_raw, y = load_task(T2)
    X = TASK_FEATURES[T2](X_raw)
    key = X.round(6).astype(str).agg("|".join, axis=1)
    oof = load_oof(load_champions()[T2]["run_id"], T2)
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED)
    rows = []
    fid = X_raw.flow_id.values
    for i, (tr, te) in enumerate(cv.split(X, y)):
        train_keys = pd.DataFrame({"k": key.iloc[tr].values, "y": y.iloc[tr].values})
        lookup = train_keys.groupby("k").y.agg(lambda s: s.value_counts().to_dict())
        o = oof[oof.fold == i].set_index("flow_id")
        for j in te:
            labs = lookup.get(key.iloc[j])
            rows.append({"fold": i, "flow_id": fid[j], "y_true": y.iloc[j], "y_pred": o.y_pred[fid[j]],
                         "seen": labs is not None, "pure": labs is not None and len(labs) == 1,
                         "lookup": max(labs, key=labs.get) if labs else None})
    d = pd.DataFrame(rows)
    d["err"] = d.y_true != d.y_pred
    print(f"held-out predictions: {len(d)}, errors: {d.err.sum()} ({d.err.mean():.1%})")
    print(f"exact vector seen in training fold: {d.seen.mean():.1%} of predictions")
    for name, m in (("seen & pure", d.seen & d.pure), ("seen & mixed", d.seen & ~d.pure), ("unseen", ~d.seen)):
        s = d[m]
        fix = (s.err & (s.lookup == s.y_true)).sum()
        brk = (~s.err & s.lookup.notna() & (s.lookup != s.y_true)).sum()
        print(f"  {name:13s} n={len(s):5d}  errors={s.err.sum():4d} ({s.err.mean():.1%})  "
              f"lookup would fix {fix}, break {brk}")
    print("\nerrors on unseen vectors by true class:")
    print(d[~d.seen & d.err].y_true.value_counts().to_string())


if __name__ == "__main__":
    part_a()
    part_b()
