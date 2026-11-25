"""Experiment 094: seed-bagging the whole pipeline (SB1, SB2) and nested feature selection (FS1), judged on never-used
cv_seeds 2041-2045 (protocol: experiments/094_variance_reduction.md, frozen first).

Usage: python src/exp094_variance_reduction.py --task T --production --seed N
       python src/exp094_variance_reduction.py --task T --arm SB|FS --seed N --ref RUN_ID
       python src/exp094_variance_reduction.py --describe     (columns FS1 neutralises on all train + validation)
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import StratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from models import ScopedH1, SoftVote, Task1Bundle, _bundle_verifiers, task1_bundle, task2_model
from runlog import record_run

T1, T2 = "task1_static", "task2_realtime_prefix5"
PROD = {T1: task1_bundle, T2: task2_model}
BAG = 5


class SeedBag(BaseEstimator, ClassifierMixin):
    def __init__(self, task=T1, seed=0):
        self.task = task
        self.seed = seed

    def fit(self, X, y):
        self.models_ = [PROD[self.task](self.seed + 1000 * k).fit(X, y) for k in range(BAG)]
        self.classes_ = self.models_[0].classes_
        return self

    def predict(self, X):
        L = np.array([np.asarray(m.predict(X), dtype=object) for m in self.models_])
        out = L[0].copy()
        for j in range(L.shape[1]):
            vals, cnt = np.unique(L[:, j], return_counts=True)
            best = vals[cnt == cnt.max()]
            out[j] = L[0, j] if L[0, j] in best else best[0]
        return out


def unimportant(X, y, seed):
    """Columns whose inner-CV permutation importance (accuracy drop, balanced SoftVote) is <= 0 (protocol)."""
    y = np.asarray(y, dtype=object)
    drops = np.zeros(X.shape[1])
    folds = list(StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y))
    for f, (tr, te) in enumerate(folds):
        sv = SoftVote(seed=seed).fit(X.iloc[tr], y[tr])
        Xte = X.iloc[te]
        base = (sv.predict(Xte) == y[te]).mean()
        rng = np.random.default_rng(f)
        for k, c in enumerate(X.columns):
            Xp = Xte.copy()
            Xp[c] = rng.permutation(Xp[c].values)
            drops[k] += base - (sv.predict(Xp) == y[te]).mean()
    drops /= len(folds)
    return [c for c, d in zip(X.columns, drops) if d <= 0]


class FSBundle(Task1Bundle):
    def fit(self, X, y):
        self.neutral_ = unimportant(X, y, self.seed)
        Xa = self._with_rest(X)
        Xa[self.neutral_] = 0
        self.model_ = ScopedH1(base_factory=_bundle_verifiers, seed=self.seed).fit(Xa, y)
        self.classes_ = self.model_.classes_
        return self

    def predict(self, X):
        Xa = self._with_rest(X)
        Xa[self.neutral_] = 0
        return self.model_.predict(Xa)


def factory(task, arm):
    def f(seed):
        return SeedBag(task=task, seed=seed) if arm == "SB" else FSBundle(seed=seed)
    f.__name__ = f"{arm.lower()}_{'t1' if task == T1 else 't2'}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--describe" in args:
        Xr, y = load_task(T1)
        print("FS1 neutralises on all train + validation:", unimportant(TASK_FEATURES[T1](Xr), y.values, 0))
        sys.exit()
    task = args[args.index("--task") + 1]
    seed = int(args[args.index("--seed") + 1])
    assert 2041 <= seed <= 2045, "094 uses only the fresh cv_seeds 2041-2045"
    tag = "T1" if task == T1 else "T2"
    feats = TASK_FEATURES[task]
    t0 = datetime.now(timezone.utc)
    if "--production" in args:
        f = PROD[task]
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("094", f"{tag}_production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"{task} production reference on fresh cv_seed {seed} (094)",
                         config={"model": f.__name__, "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm, ref = args[args.index("--arm") + 1], args[args.index("--ref") + 1]
        assert not (arm == "FS" and task == T2), "FS is Task 1 only"
        f = factory(task, arm)
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("094", f"{arm}{tag[1]}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"{task} 094 arm {arm}{tag[1]}: {'seed-bagging (5 seeds, majority vote)' if arm == 'SB' else 'nested feature selection'}; cv_seed {seed}",
                         config={"arm": arm + tag[1], "bag": BAG if arm == "SB" else None, "cv_seed": seed,
                                 "features": feats.__name__}, started=t0)
    print(rid)
