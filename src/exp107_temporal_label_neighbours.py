"""Experiment 107 (measurement only): what the known labels of training flows opened at the same moment would add
(protocol: experiments/107_temporal_label_neighbours.md). Capture time is excluded from our submissions; this runner never
touches the test set.

Usage (from the repository root):
  .venv/bin/python src/exp107_temporal_label_neighbours.py --smoke
  .venv/bin/python src/exp107_temporal_label_neighbours.py --all          # both tasks: P, N05, N10, N20, NN on seeds 2126-2130
  .venv/bin/python src/exp107_temporal_label_neighbours.py --task t1 --arm N10 --seed 2126
  .venv/bin/python src/exp107_temporal_label_neighbours.py --analyse
Runs go to results/<stamp>_107_<T1|T2>_<arm>_s<seed>/; other evidence to experiments/107_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate, load_task
from models import TASK_MODELS
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASKS = {"t1": "task1_static", "t2": "task2_realtime_prefix5"}
SEEDS = (2126, 2127, 2128, 2129, 2130)
ARMS = {"P": None, "N05": 0.5, "N10": 1.0, "N20": 2.0, "NN": "nearest"}
W_MIN, SHARE_MIN = 0.5, 0.8
EVIDENCE = ROOT / "experiments/107_evidence"
_T = {}


def start_times(task):
    """start_rel of the train + validation flows, in the row order of cv.evaluate (the task's own file)."""
    if task not in _T:
        _T[task] = load_task(task)[0].start_rel.to_numpy(dtype=float)
    return _T[task]


def neighbour_votes(t_query, t_train, y_train, classes, sigma):
    W = np.exp(-((t_query[:, None] - t_train[None, :]) ** 2) / (2 * sigma ** 2))
    return np.stack([W[:, y_train == c].sum(axis=1) for c in classes], axis=1)


class TemporalNeighbours(BaseEstimator, ClassifierMixin):
    def __init__(self, t="t1", arm="N10", seed=0):
        self.t, self.arm, self.seed = t, arm, seed

    def fit(self, X, y):
        self.task_ = TASKS[self.t]
        y = np.asarray(y, dtype=object)
        self.t_train_ = start_times(self.task_)[np.asarray(X.index)]
        self.y_train_ = y
        self.classes_ = np.array(sorted(set(y)), dtype=object)
        if self.arm != "NN":
            self.base_ = TASK_MODELS[self.task_](self.seed).fit(X, y)
        return self

    def predict(self, X):
        tq = start_times(self.task_)[np.asarray(X.index)]
        if self.arm == "NN":
            return self.y_train_[np.abs(tq[:, None] - self.t_train_[None, :]).argmin(axis=1)]
        pred = np.asarray(self.base_.predict(X), dtype=object).copy()
        V = neighbour_votes(tq, self.t_train_, self.y_train_, list(self.classes_), ARMS[self.arm])
        Wt = V.sum(axis=1)
        share = V.max(axis=1) / np.clip(Wt, 1e-12, None)
        m = (Wt >= W_MIN) & (share >= SHARE_MIN)
        pred[m] = self.classes_[V[m].argmax(axis=1)]
        return pred


def factory(t, arm):
    if arm == "P":
        return TASK_MODELS[TASKS[t]]

    def f(seed):
        return TemporalNeighbours(t=t, arm=arm, seed=seed)
    f.__name__ = f"temporal_neighbours_{t}_{arm.lower()}"
    return f


def run_id(t, arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_107_{t.upper()}_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(t, arm, seed):
    task, feats, f = TASKS[t], TASK_FEATURES[TASKS[t]], factory(t, arm)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    rid = record_run("107", f"{t.upper()}_{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id(t, "P", seed),
                     question=f"{task} 107 {arm} (labels of flows opened at the same moment; measurement only) cv_seed {seed}",
                     config={"arm": arm, "sigma_s": ARMS[arm], "w_min": W_MIN, "share_min": SHARE_MIN, "cv_seed": seed,
                             "signal": "start_rel (capture time; excluded from submissions)"}, started=t0)
    print(rid, flush=True)


def smoke():
    tq = np.array([10.0, 50.0])
    tt = np.array([10.2, 10.4, 49.0, 80.0])
    yt = np.array(["a", "a", "b", "b"], dtype=object)
    V = neighbour_votes(tq, tt, yt, ["a", "b"], 0.5)
    print("votes (expect flow 1 -> a, flow 2 -> b weakly):", np.round(V, 3).tolist())
    X1 = TASK_FEATURES[TASKS["t1"]](load_task(TASKS["t1"])[0])
    print("Task 1 feature index is 0..329:", list(X1.index[:3]), X1.index.max(),
          "| start_rel identical in both task files:", bool((start_times(TASKS["t1"]) == start_times(TASKS["t2"])).all()))


def analyse():
    out = {}
    for t in ("t1", "t2"):
        task = TASKS[t]
        f1 = lambda a, s: pd.read_csv(ROOT / "results" / run_id(t, a, s) / task / "folds.csv").macro_f1.values  # noqa: E731
        res = {"means": {a: [round(float(f1(a, s).mean()), 4) for s in SEEDS] for a in ARMS}, "vs_P": {}}
        for a in ("N05", "N10", "N20", "NN"):
            per, acc = [], Counter()
            for s in SEEDS:
                d = f1(a, s) - f1("P", s)
                per.append([round(float(d.mean()), 4), int((d > 1e-12).sum()), int((d < -1e-12).sum())])
                new = pd.read_csv(ROOT / "results" / run_id(t, a, s) / task / "oof.csv")
                ref = pd.read_csv(ROOT / "results" / run_id(t, "P", s) / task / "oof.csv")
                ch = new.y_pred.values != ref.y_pred.values
                acc.update({"changed": int(ch.sum()), "fixed": int((ch & (new.y_pred.values == new.y_true.values)).sum()),
                            "broken": int((ch & (ref.y_pred.values == ref.y_true.values)).sum())})
            res["vs_P"][a] = {"mean_delta": round(float(np.mean([p[0] for p in per])), 4), "per_seed": per, "changes": dict(acc)}
            print(t, a, res["vs_P"][a])
        out[t] = res
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", choices=list(TASKS))
    ap.add_argument("--arm", choices=list(ARMS))
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        smoke()
    elif a.analyse:
        analyse()
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
