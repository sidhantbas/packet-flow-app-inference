"""Experiment 103: reproduce LLM_ops's Lookup-Ensemble-v7 (protocol: experiments/103_lookup_ensemble_reproduction.md).
Components come from src/flowkit (features, lookup, members, postprocess, counts); this runner assembles the ladder L0-L5.

Usage (from the repository root):
  .venv/bin/python src/exp103_lookup_ensemble_reproduction.py --smoke
  .venv/bin/python src/exp103_lookup_ensemble_reproduction.py --task t1 --arm P --seed 2106     # production reference first
  .venv/bin/python src/exp103_lookup_ensemble_reproduction.py --task t1 --arm L2 --seed 2106    # compared with that P run
  .venv/bin/python src/exp103_lookup_ensemble_reproduction.py --all                             # both tasks, every arm and seed
  .venv/bin/python src/exp103_lookup_ensemble_reproduction.py --analyse
  .venv/bin/python src/exp103_lookup_ensemble_reproduction.py --test-effect                     # L0-L3 on the 81 test flows
L3-L5 reuse L2's held-out probabilities from ~/.cache/mission-p/exp103/ (same task, seed, fold rows), so run L2 before them.
Runs go to results/<stamp>_103_<T1|T2>_<arm>_s<seed>/; other evidence to experiments/103_evidence/.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, basic_features, evaluate, load_task
from flowkit.counts import label_counts, quota_assign
from flowkit.features import ratio_features
from flowkit.lookup import ExactLookup
from flowkit.members import Aligned, build, tune
from flowkit.postprocess import prior_correct, temporal_smooth
from models import T1_COLS, TASK_MODELS, TwoClerks, rest_from_columns
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASKS = {"t1": "task1_static", "t2": "task2_realtime_prefix5"}
SEEDS = (2106, 2107, 2108, 2109, 2110)
ARMS = ("P", "L0", "L1", "L2", "L3", "L4", "L5")
CLASSES = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
MEMBERS = {"t1": ["lgbm", "xgb", "et", "rf"], "t2": ["lgbm", "lgbm", "et", "knn_manhattan"]}
SIGMA = {"t1": 0.5, "t2": 1.0}
BETA, BAGS, TRIALS = 0.25, 3, 15
KEY_T1 = list(TwoClerks.OPEN_COLS)
KEY_T2 = [c[len("p5_"):] for c in TwoClerks.OPEN_COLS]
CACHE = Path.home() / ".cache/mission-p/exp103"
EVIDENCE = ROOT / "experiments/103_evidence"
_RAW = {}


def raw(task):
    if task not in _RAW:
        X, y = load_task(task)
        _RAW[task] = (X.start_rel.to_numpy(dtype=float), np.asarray(y.values, dtype=object))
    return _RAW[task]


def feature_fn(t):
    return TASK_FEATURES[TASKS["t1"]] if t == "t1" else basic_features


def base_features(X, t):
    if t == "t1":
        raw17 = X[list(T1_COLS)]
        return pd.concat([raw17, ratio_features(raw17), rest_from_columns(X)], axis=1)
    return pd.concat([X, ratio_features(X)], axis=1)


class LookupEnsemble(BaseEstimator, ClassifierMixin):
    def __init__(self, t="t1", level=0, seed=0, use_cache=True):
        self.t, self.level, self.seed, self.use_cache = t, level, seed, use_cache

    def _key(self, index):
        h = hashlib.sha1(np.asarray(index, dtype=np.int64).tobytes()).hexdigest()[:16]
        return CACHE / f"{self.t}_s{self.seed}_{h}.npz"

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.classes_ = np.asarray(CLASSES, dtype=object)
        self.shares_ = {c: n / len(y) for c, n in label_counts(y).items()}
        self.cache_ = self._key(X.index) if self.use_cache else None
        if self.level >= 3 and self.cache_ is not None and self.cache_.exists():
            self.cached_ = True
            return self
        self.cached_ = False
        F = base_features(X, self.t)
        if self.level >= 1:
            self.lookup_ = ExactLookup(KEY_T1 if self.t == "t1" else KEY_T2, CLASSES).fit(X, y)
            F = pd.concat([F, self.lookup_.transform(X, y)], axis=1)
        self.members_ = []
        tuned = {}
        for k, name in enumerate(MEMBERS[self.t]):
            params = {}
            if self.level >= 2:
                if name not in tuned:
                    tuned[name] = tune(name, F, y, CLASSES, self.seed, trials=TRIALS)
                params = tuned[name]
            seeds = [self.seed * 100 + 10 * k + b for b in range(BAGS if self.level >= 2 else 1)]
            self.members_.append([Aligned(build(name, params, s), CLASSES).fit(F, y) for s in seeds])
        self.params_ = tuned
        return self

    def _l2_proba(self, X):
        F = base_features(X, self.t)
        if self.level >= 1:
            L = self.lookup_.transform(X)
            F = pd.concat([F, L], axis=1)
        P = np.mean([np.mean([m.predict_proba(F) for m in bag], axis=0) for bag in self.members_], axis=0)
        if self.level >= 1:
            seen = L["lookup_n"].to_numpy() > 0
            P[seen] = 0.5 * P[seen] + 0.5 * L[[f"lookup_{c}" for c in CLASSES]].to_numpy()[seen]
        return P

    def predict_proba(self, X):
        if self.cached_:
            z = np.load(self.cache_)
            pos = {i: k for k, i in enumerate(z["index"])}
            P = z["P"][[pos[i] for i in X.index]]
        else:
            P = self._l2_proba(X)
            if self.level == 2 and self.cache_ is not None:
                CACHE.mkdir(parents=True, exist_ok=True)
                np.savez(self.cache_, index=np.asarray(X.index), P=P)
        if self.level >= 3:
            P = prior_correct(P, CLASSES, self.shares_, BETA)
        if self.level >= 4:
            P = temporal_smooth(P, raw(TASKS[self.t])[0][np.asarray(X.index)], SIGMA[self.t])
        return P

    def predict(self, X):
        P = self.predict_proba(X)
        if self.level >= 5:
            return quota_assign(P, CLASSES, label_counts(raw(TASKS[self.t])[1][np.asarray(X.index)]))
        return self.classes_[P.argmax(axis=1)]


def factory(t, arm):
    if arm == "P":
        return TASK_MODELS[TASKS[t]]

    def f(seed):
        return LookupEnsemble(t=t, level=int(arm[1]), seed=seed)
    f.__name__ = f"lookup_ensemble_{t}_{arm.lower()}"
    return f


def run_id(t, arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_103_{t.upper()}_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(t, arm, seed):
    task = TASKS[t]
    feats = TASK_FEATURES[task] if arm == "P" else feature_fn(t)
    f = factory(t, arm)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    rid = record_run("103", f"{t.upper()}_{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id(t, "P", seed),
                     question=f"{task} 103 {arm} (Lookup-Ensemble-v7 ladder) on never-used cv_seed {seed}",
                     config={"arm": arm, "task": task, "cv_seed": seed, "beta": BETA, "bags": BAGS, "trials": TRIALS,
                             "sigma": SIGMA[t], "members": MEMBERS[t]}, started=t0)
    print(rid, flush=True)


def smoke():
    lk = ExactLookup(["k"], ["a", "b"]).fit(pd.DataFrame({"k": [1, 1, 1, 2]}), ["a", "a", "b", "b"])
    tr = lk.transform(pd.DataFrame({"k": [1, 1, 1, 2]}), ["a", "a", "b", "b"])
    print("lookup leave-one-out:", tr.values.tolist(), "(expect [[.5,.5,2],[.5,.5,2],[1,0,2],[0,0,0]])")
    P = np.random.default_rng(0).dirichlet(np.ones(6), 10)
    print("prior beta=0 unchanged:", bool(np.allclose(prior_correct(P, CLASSES, {c: 1 / 6 for c in CLASSES}, 0.0), P)))
    print("smoothing sigma->0 unchanged:", bool(np.allclose(temporal_smooth(P, np.arange(10) * 10.0, 1e-3), P)))
    from sklearn.model_selection import RepeatedStratifiedKFold
    for t in ("t1", "t2"):
        task = TASKS[t]
        Xr, y = load_task(task)
        X, yv = feature_fn(t)(Xr), np.asarray(y.values, dtype=object)
        tr_i, te_i = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2106).split(X, yv))
        for lev in (0, 1):
            p = LookupEnsemble(t=t, level=lev, seed=0, use_cache=False).fit(X.iloc[tr_i], yv[tr_i]).predict(X.iloc[te_i])
            print(t, f"L{lev}", "fold-0 accuracy", round(float(np.mean(p == yv[te_i])), 3))
        global CACHE
        keep, CACHE = CACHE, CACHE.parent / "exp103-smoke"
        try:
            LookupEnsemble(t=t, level=2, seed=0).fit(X.iloc[tr_i], yv[tr_i]).predict(X.iloc[te_i])
            a = LookupEnsemble(t=t, level=3, seed=0).fit(X.iloc[tr_i], yv[tr_i])
            b = LookupEnsemble(t=t, level=3, seed=0, use_cache=False).fit(X.iloc[tr_i], yv[tr_i])
            print(t, "L3 from cache:", a.cached_, "| cached == uncached:",
                  bool((a.predict(X.iloc[te_i]) == b.predict(X.iloc[te_i])).all()))
        finally:
            for f in CACHE.glob("*.npz"):
                f.unlink()
            CACHE = keep


def analyse():
    out = {}
    for t in ("t1", "t2"):
        task = TASKS[t]
        f1 = lambda rid: pd.read_csv(ROOT / "results" / rid / task / "folds.csv").macro_f1.values  # noqa: E731
        means = {a: [round(float(f1(run_id(t, a, s)).mean()), 4) for s in SEEDS] for a in ARMS}
        steps = [("L0", "P"), ("L1", "L0"), ("L2", "L1"), ("L3", "L2"), ("L4", "L3"), ("L5", "L4"), ("L3", "P"), ("L5", "P")]
        pairs = []
        for a, b in steps:
            per = []
            for s in SEEDS:
                d = f1(run_id(t, a, s)) - f1(run_id(t, b, s))
                per.append([round(float(d.mean()), 4), int((d > 1e-12).sum()), int((d < -1e-12).sum())])
            pairs.append({"a": a, "b": b, "mean_delta": round(float(np.mean([p[0] for p in per])), 4), "per_seed": per})
            print(t, f"{a} vs {b}: {pairs[-1]['mean_delta']:+.4f}", per)
        out[t] = {"means": means, "pairs": pairs}
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())
    out = {}
    for t in ("t1", "t2"):
        task = TASKS[t]
        Xr, y = load_task(task)
        X, yv = feature_fn(t)(Xr), np.asarray(y.values, dtype=object)
        Xt_raw = load_test(task)
        Xt = feature_fn(t)(Xt_raw)
        submitted = np.array([sub[task][f] for f in Xt_raw.flow_id], dtype=object)
        out[t] = {"submitted_counts": dict(Counter(submitted))}
        for lev in (0, 1, 2, 3):
            p = LookupEnsemble(t=t, level=lev, seed=0, use_cache=False).fit(X, yv).predict(Xt)
            ch = p != submitted
            out[t][f"L{lev}"] = {"predicted_counts": dict(Counter(p)), "changed_vs_submitted": int(ch.sum()),
                                 "transitions": dict(Counter(f"{a} -> {b}" for a, b in zip(submitted[ch], p[ch])))}
            print(t, f"L{lev}", out[t][f"L{lev}"], flush=True)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2, default=int) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", choices=list(TASKS))
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--all", action="store_true", help="both tasks, every arm on every seed (P first, L2 before L3-L5)")
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
                for arm in ARMS:
                    run(t, arm, s)
    else:
        if not (a.task and a.arm and a.seed):
            ap.error("--task, --arm and --seed are required")
        run(a.task, a.arm, a.seed)


if __name__ == "__main__":
    main()
