"""Experiment 016: smoother models for never-seen patterns (68% of task 2 errors, 011).

Base-model variants (task 1: the base is the whole model; task 2: the base sits under the unchanged
facebook/instagram specialist of the champion, via MultiSpecialist(base_members=...)):
  check         Blend(rf, et, lgbm): must tie both champions
  leaf2, leaf3  RF and ExtraTrees with min_samples_leaf 2 / 3 (+ LightGBM as is)
  plus_lr       rf, et, lgbm + logistic regression on log1p + standardised features
  plus_knn      rf, et, lgbm + distance-weighted 7-NN on the same scaling
  plus_lr_knn   both
After each run the task 2 error rate is split into flows whose exact vector was / was not seen in the
training fold (as in 011).
Usage: python src/exp016_smooth_models.py [confirm NAME ...]
"""
import sys
from datetime import datetime, timezone

import pandas as pd
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import CV_SEED, TASK_FEATURES, TASKS, evaluate, load_task
from models import Blend, MultiSpecialist, et, et_leaf, knn, lgbm, logreg, rf, rf_leaf, task1_model, task2_model
from runlog import load_oof, record_run

T1, T2 = TASKS
MEMBERS = {
    "check": (rf, et, lgbm),
    "leaf2": (rf_leaf(2), et_leaf(2), lgbm),
    "leaf3": (rf_leaf(3), et_leaf(3), lgbm),
    "plus_lr": (rf, et, lgbm, logreg),
    "plus_knn": (rf, et, lgbm, knn),
    "plus_lr_knn": (rf, et, lgbm, logreg, knn),
}
FI = (("facebook", "instagram"), "base", None)


def factories(members):
    return {T1: lambda s: Blend(members, seed=s),
            T2: lambda s: MultiSpecialist(None, (FI,), seed=s, base_members=members)}


def seen_split(run_id, cv_seed=CV_SEED):
    """Task 2 error rate on held-out flows whose exact feature vector was / was not in the training fold."""
    X_raw, y = load_task(T2)
    X = TASK_FEATURES[T2](X_raw)
    key = pd.Series(X.round(6).astype(str).agg("|".join, axis=1).values, index=X_raw.flow_id.values)
    oof = load_oof(run_id, T2)
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=cv_seed)
    seen = []
    for i, (tr, _) in enumerate(cv.split(X, y)):
        train_keys = set(key.iloc[tr])
        o = oof[oof.fold == i]
        seen.extend(key[o.flow_id].isin(train_keys).values)
    oof["seen"], oof["err"] = seen, oof.y_true != oof.y_pred
    return oof.groupby("seen").err.mean().to_dict()


def run(name, cv_seed=2026, reference="champion", tag=""):
    t0 = datetime.now(timezone.utc)
    fs = factories(MEMBERS[name])
    res = {t: evaluate(t, TASK_FEATURES[t], fs[t], cv_seed=cv_seed) for t in TASKS}
    rid = record_run("016", name + tag, res, model_factory=fs[T1], reference=reference,
                     question=f"Base members {name} vs champions (cv_seed {cv_seed})?",
                     config={"model": "Blend / MultiSpecialist(base_members)", "members": [m.__name__ for m in MEMBERS[name]],
                             "cv_seed": cv_seed}, started=t0)
    e = seen_split(rid, cv_seed)
    print(f"SEEN-SPLIT {name}{tag}: task 2 error seen {e.get(True, float('nan')):.3f}, unseen {e.get(False, float('nan')):.3f}")
    return rid


def confirm(names):
    for seed in (2027, 2028):
        t0 = datetime.now(timezone.utc)
        ref = record_run("016", f"champion_s{seed}",
                         {T1: evaluate(T1, TASK_FEATURES[T1], task1_model, cv_seed=seed),
                          T2: evaluate(T2, TASK_FEATURES[T2], task2_model, cv_seed=seed)}, reference=None,
                         model_factory=task1_model, question=f"Confirmation reference: champions, cv_seed {seed}.",
                         config={"model": "TASK_MODELS", "cv_seed": seed}, started=t0)
        for n in names:
            run(n, cv_seed=seed, reference=ref, tag=f"_s{seed}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["confirm"]:
        confirm(sys.argv[2:])
    else:
        for n in MEMBERS:
            run(n)
