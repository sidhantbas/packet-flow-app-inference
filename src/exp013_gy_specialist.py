"""Experiment 013: google-vs-youtube specialist (largest share of task 2 errors on unseen vectors, 011).

Two stages: the champion SoftVote predicts all six classes on the champion columns; every flow it calls
google or youtube is re-decided by a specialist trained only on the google + youtube flows of the
training fold.

  spec_same    specialist = SoftVote on the champion columns
  spec_extra   specialist = SoftVote on the champion columns + ratio families from 008
               (task 1: reltiming, rates, direction, sizecv; task 2: direction, sizecv, no timing)
  spec_extra_nocw  as spec_extra, without class weights (two roughly balanced classes: 131 google, 55 youtube)
Passing variants are re-tested on cv_seeds 2027 and 2028 against the champion re-run on the same folds.
"""
import sys
from datetime import datetime, timezone

from cv import TASK_FEATURES, TASKS, evaluate
from exp008_feature_families import FAMILIES
from models import PairSpecialist, SoftVote
from runlog import record_run

PAIR = ("google", "youtube")
EXTRA = {"task1_static": ["reltiming", "rates", "direction", "sizecv"],
         "task2_realtime_prefix5": ["direction", "sizecv"]}


def features_with(task, names):
    base = TASK_FEATURES[task]

    def f(X_raw):
        X = base(X_raw)
        for n in names:
            for col, v in FAMILIES[n](X_raw).items():
                X[col] = v
        return X
    f.__name__ = f"{base.__name__}+{'+'.join(names)}"
    return f


def variant(task, name):
    from cv import load_task
    base_cols = list(TASK_FEATURES[task](load_task(task)[0].head()).columns)
    if name == "spec_same":
        return TASK_FEATURES[task], lambda s: PairSpecialist(base_cols, s, spec_all_cols=False)
    feats = features_with(task, EXTRA[task])
    cw = None if name == "spec_extra_nocw" else "balanced"
    return feats, lambda s: PairSpecialist(base_cols, s, spec_class_weight=cw)


NAMES = ["spec_same", "spec_extra", "spec_extra_nocw"]


def run(name, cv_seed=2026, reference="champion", tag=""):
    t0 = datetime.now(timezone.utc)
    res, cfg = {}, {}
    for t in TASKS:
        feats, factory = variant(t, name)
        res[t] = evaluate(t, feats, factory, cv_seed=cv_seed)
        cfg[t] = feats.__name__
    return record_run("013", name + tag, res, model_factory=factory, reference=reference,
                      question=f"Does a google/youtube specialist ({name}) beat the champion (cv_seed {cv_seed})?",
                      config={"model": f"PairSpecialist:{name}", "features": cfg, "cv_seed": cv_seed}, started=t0)


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("013", f"champion_s{seed}",
                         {t: evaluate(t, TASK_FEATURES[t], lambda s: SoftVote(seed=s), cv_seed=seed) for t in TASKS},
                         reference=None, model_factory=lambda s: SoftVote(seed=s),
                         question=f"Confirmation reference: champions, cv_seed {seed}.",
                         config={"model": "SoftVote", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, cv_seed=seed, reference=ref, tag=f"_s{seed}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["confirm"]:
        confirm(sys.argv[2:])
    else:
        for n in NAMES:
            run(n)
