"""Experiment 092: confident-learning cleaning of non-Meta training rows before training production (protocol:
experiments/092_training_pile_cleaning.md, frozen first). Judged on never-used cv_seeds 2036-2040.

Usage: python src/exp092_cleaning.py --task task1_static|task2_realtime_prefix5 --production --seed N
       python src/exp092_cleaning.py --task ... --seed N --ref RUN_ID
       python src/exp092_cleaning.py --describe        (rows flagged on the full train + validation set)
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.model_selection import StratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from models import SoftVote, task1_bundle, task2_model
from runlog import record_run

T1, T2 = "task1_static", "task2_realtime_prefix5"
PROTECT = ("facebook", "instagram")
PROD = {T1: task1_bundle, T2: task2_model}


def flagged(X, y, seed):
    """Confident-learning flags (protocol steps 1-4) for the rows of X; Meta rows are never flagged."""
    y = np.asarray(y, dtype=object)
    classes = np.array(sorted(set(y)))
    P = np.zeros((len(y), len(classes)))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        sv = SoftVote(seed=seed).fit(X.iloc[tr], y[tr])
        P[np.ix_(te, [list(classes).index(c) for c in sv.classes_])] = sv.predict_proba(X.iloc[te])
    lab = np.array([list(classes).index(c) for c in y])
    t = np.array([P[lab == j, j].mean() for j in range(len(classes))])
    own = P[np.arange(len(y)), lab]
    other = (P >= t[None, :])
    other[np.arange(len(y)), lab] = False
    return (own < t[lab]) & other.any(axis=1) & ~np.isin(y, PROTECT)


def clean(X_tr, y_tr, seed):
    keep = ~flagged(X_tr, y_tr, seed)
    return X_tr.loc[keep], y_tr.loc[keep] if hasattr(y_tr, "loc") else np.asarray(y_tr)[keep]


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--describe" in args:
        for task in (T1, T2):
            Xr, y = load_task(task)
            f = flagged(TASK_FEATURES[task](Xr), y.values, 0)
            print(task, "flagged", int(f.sum()), "of", len(y), dict(zip(*np.unique(np.asarray(y.values)[f], return_counts=True))))
        sys.exit()
    task = args[args.index("--task") + 1]
    seed = int(args[args.index("--seed") + 1])
    assert 2036 <= seed <= 2040, "092 uses only the fresh cv_seeds 2036-2040"
    tag = "T1" if task == T1 else "T2"
    f, feats = PROD[task], TASK_FEATURES[task]
    t0 = datetime.now(timezone.utc)
    if "--production" in args:
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("092", f"{tag}_production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"{task} production reference on fresh cv_seed {seed} (092)",
                         config={"model": f.__name__, "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        ref = args[args.index("--ref") + 1]
        res = {task: evaluate(task, feats, f, resample=clean, cv_seed=seed)}
        rid = record_run("092", f"C{tag[1]}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"{task} 092: confident-learning cleaning of non-Meta training rows; cv_seed {seed}",
                         config={"arm": f"C{tag[1]}", "rule": "confident learning, inner SoftVote 5-fold, Meta protected",
                                 "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
