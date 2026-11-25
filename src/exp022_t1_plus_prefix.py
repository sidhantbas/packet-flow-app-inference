"""Experiment 022: Task 1 with the first-5-packet statistics added.

Condition 2 forbids Task 1 (full-flow) features in Task 2 predictions; it does not forbid Task 2 files as extra
input for Task 1. Both tasks share flow_ids and splits. Here Task 1 = its 17 champion columns + the Task 2 file's
columns for the same flow (prefixed p5_), joined on flow_id. To be disclosed in the report.

  plus_p5_all     + all 17 prefix-5 columns
  plus_p5_notime  + the 12 prefix-5 columns without timing (the Task 2 champion columns)
Usage: python src/exp022_t1_plus_prefix.py [confirm NAME ...]
"""
import sys
from datetime import datetime, timezone

import pandas as pd

from cv import DATA, TASK_FEATURES, TASKS, basic_features, evaluate, no_timing_features
from models import task1_model
from runlog import record_run

T1, T2 = TASKS


def prefix_table(fn):
    parts = [pd.read_csv(DATA / T2 / f"{s}_features.csv") for s in ("train", "validation", "test")]
    P = pd.concat(parts, ignore_index=True)
    F = fn(P)
    F.columns = [f"p5_{c}" for c in F.columns]
    F.index = P.flow_id.values
    return F


def with_prefix(fn):
    table = prefix_table(fn)

    def f(X_raw):
        X = TASK_FEATURES[T1](X_raw)
        P = table.loc[X_raw.flow_id.values].reset_index(drop=True)
        return pd.concat([X.reset_index(drop=True), P], axis=1)
    f.__name__ = f"{TASK_FEATURES[T1].__name__}+p5_{fn.__name__}"
    return f


VARIANTS = {"plus_p5_all": basic_features, "plus_p5_notime": no_timing_features}


def run(name, cv_seed=2026, reference="champion", tag=""):
    f = with_prefix(VARIANTS[name])
    t0 = datetime.now(timezone.utc)
    return record_run("022", name + tag, {T1: evaluate(T1, f, task1_model, cv_seed=cv_seed)}, model_factory=task1_model,
                      feature_fn=f, reference=reference,
                      question=f"Task 1 + prefix-5 statistics ({name}) vs champion (cv_seed {cv_seed})?",
                      config={"model": "task1_model", "features": f.__name__, "cv_seed": cv_seed}, started=t0)


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("022", f"t1_champion_s{seed}", {T1: evaluate(T1, TASK_FEATURES[T1], task1_model, cv_seed=seed)},
                         reference=None, model_factory=task1_model,
                         question=f"Confirmation reference: task 1 champion, cv_seed {seed}.",
                         config={"model": "task1_model", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, seed, ref, f"_s{seed}")


if __name__ == "__main__" and sys.argv[1:2] not in (["blend"], ["keepfb"]):
    confirm(sys.argv[2:]) if sys.argv[1:2] == ["confirm"] else [run(n) for n in VARIANTS]


def blend(cv_seed=2026, reference="champion", tag=""):
    """blend_t1_p5all: mean proba of the champion (17 task 1 columns) and the 34-column prefix-augmented SoftVote."""
    from cv import load_task
    from models import ColumnBlend
    f = with_prefix(basic_features)
    t1_cols = tuple(TASK_FEATURES[T1](load_task(T1)[0].head()).columns)
    factory = lambda s: ColumnBlend((t1_cols, "all"), seed=s)
    t0 = datetime.now(timezone.utc)
    return record_run("022", "blend_t1_p5all" + tag, {T1: evaluate(T1, f, factory, cv_seed=cv_seed)}, model_factory=factory,
                      feature_fn=f, reference=reference,
                      question=f"Task 1: mean of champion and prefix-augmented SoftVote (cv_seed {cv_seed})?",
                      config={"model": "ColumnBlend(t1_17, all_34)", "cv_seed": cv_seed}, started=t0)


if __name__ == "__main__" and sys.argv[1:2] == ["blend"]:
    blend()


def blend_keep_fb(cv_seed=2026, reference="champion", tag=""):
    """blend_keep_fb: as blend_t1_p5all, but flows the champion alone calls facebook stay facebook."""
    from cv import load_task
    from models import KeepClassBlend
    f = with_prefix(basic_features)
    t1_cols = tuple(TASK_FEATURES[T1](load_task(T1)[0].head()).columns)
    factory = lambda s: KeepClassBlend((t1_cols, "all"), seed=s, keep="facebook")
    t0 = datetime.now(timezone.utc)
    return record_run("022", "blend_keep_fb" + tag, {T1: evaluate(T1, f, factory, cv_seed=cv_seed)}, model_factory=factory,
                      feature_fn=f, reference=reference,
                      question=f"Task 1: blend with prefix-5, champion keeps facebook (cv_seed {cv_seed})?",
                      config={"model": "KeepClassBlend(t1_17, all_34, keep=facebook)", "cv_seed": cv_seed}, started=t0)


if __name__ == "__main__" and sys.argv[1:2] == ["keepfb"]:
    from runlog import load_index
    refs = {e["name"]: e["run_id"] for e in load_index() if e["experiment"] == "022"}
    blend_keep_fb()
    for seed in (2027, 2028):
        blend_keep_fb(seed, refs[f"t1_champion_s{seed}"], f"_s{seed}")
