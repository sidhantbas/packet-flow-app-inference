"""Experiment 108: exact-opening lookup (LLM_ops's first-5 lookup, as 036's override) on top of Task 2 production
(protocol: experiments/108_task2_exact_opening_override.md). Reads only Task 2 files.

Usage (from the repository root):
  .venv/bin/python src/exp108_task2_exact_opening_override.py --smoke
  .venv/bin/python src/exp108_task2_exact_opening_override.py --all          # P, H, HA on seeds 2131-2135
  .venv/bin/python src/exp108_task2_exact_opening_override.py --arm H --seed 2131
  .venv/bin/python src/exp108_task2_exact_opening_override.py --analyse
  .venv/bin/python src/exp108_task2_exact_opening_override.py --test-effect
Runs go to results/<stamp>_108_<arm>_s<seed>/; other evidence to experiments/108_evidence/.
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
from models import task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T2 = "task2_realtime_prefix5"
SEEDS = (2131, 2132, 2133, 2134, 2135)
ARMS = ("P", "H", "HA")
META = ("facebook", "instagram")
EVIDENCE = ROOT / "experiments/108_evidence"


def keys(X):
    return X.astype(str).agg("|".join, axis=1).values


class OpeningOverride(BaseEstimator, ClassifierMixin):
    """task2_model; a flow whose exact opening (all 12 production columns) was seen in training with a single label L takes L.
    scoped=True skips the override when L or the model's call is facebook/instagram (036's rule)."""

    def __init__(self, scoped=True, seed=0):
        self.scoped, self.seed = scoped, seed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.model_ = task2_model(self.seed).fit(X, y)
        self.classes_ = self.model_.classes_
        t = pd.DataFrame({"k": keys(X), "y": y}).groupby("k").y.agg(lambda v: v.unique())
        self.table_ = {k: v[0] for k, v in t.items() if len(v) == 1}
        return self

    def predict(self, X):
        pred = np.asarray(self.model_.predict(X), dtype=object).copy()
        for i, k in enumerate(keys(X)):
            lab = self.table_.get(k)
            if lab is None or (self.scoped and (lab in META or pred[i] in META)):
                continue
            pred[i] = lab
        return pred


def factory(arm):
    if arm == "P":
        return task2_model

    def f(seed):
        return OpeningOverride(scoped=arm == "H", seed=seed)
    f.__name__ = f"task2_opening_override_{arm.lower()}"
    return f


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_108_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    f, feats = factory(arm), TASK_FEATURES[T2]
    t0 = datetime.now(timezone.utc)
    res = {T2: evaluate(T2, feats, f, cv_seed=seed)}
    rid = record_run("108", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id("P", seed),
                     question=f"Task 2 108 {arm} (exact-opening override on production) on never-used cv_seed {seed}",
                     config={"arm": arm, "scoped": arm == "H" if arm != "P" else None, "cv_seed": seed}, started=t0)
    print(rid, flush=True)


def smoke():
    from sklearn.model_selection import RepeatedStratifiedKFold
    Xr, y = load_task(T2)
    X, yv = TASK_FEATURES[T2](Xr), np.asarray(y.values, dtype=object)
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEEDS[0]).split(X, yv))
    p = np.asarray(task2_model(0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te]), dtype=object)
    for scoped in (True, False):
        m = OpeningOverride(scoped=scoped, seed=0).fit(X.iloc[tr], yv[tr])
        q = m.predict(X.iloc[te])
        seen = np.array([k in m.table_ for k in keys(X.iloc[te])])
        print(f"scoped={scoped}: equals P where the opening is unseen: {bool((q[~seen] == p[~seen]).all())}",
              f"| openings seen with one label: {int(seen.sum())} of {len(te)} | changed: {int((q != p).sum())}")


def analyse():
    f1 = lambda a, s: pd.read_csv(ROOT / "results" / run_id(a, s) / T2 / "folds.csv").macro_f1.values  # noqa: E731
    out = {"means": {a: [round(float(f1(a, s).mean()), 4) for s in SEEDS] for a in ARMS}, "vs_P": {}}
    for a in ("H", "HA"):
        per, acc, tr = [], Counter(), Counter()
        for s in SEEDS:
            d = f1(a, s) - f1("P", s)
            per.append([round(float(d.mean()), 4), int((d > 1e-12).sum()), int((d < -1e-12).sum())])
            new = pd.read_csv(ROOT / "results" / run_id(a, s) / T2 / "oof.csv")
            ref = pd.read_csv(ROOT / "results" / run_id("P", s) / T2 / "oof.csv")
            ch = new.y_pred.values != ref.y_pred.values
            acc.update({"changed": int(ch.sum()), "fixed": int((ch & (new.y_pred.values == new.y_true.values)).sum()),
                        "broken": int((ch & (ref.y_pred.values == ref.y_true.values)).sum())})
            tr.update(f"{x} -> {z}" for x, z in zip(ref.y_pred.values[ch], new.y_pred.values[ch]))
        out["vs_P"][a] = {"mean_delta": round(float(np.mean([p[0] for p in per])), 4), "per_seed": per, "changes": dict(acc),
                          "transitions": dict(tr.most_common(8))}
        print(a, out["vs_P"][a])
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T2]
    Xr, y = load_task(T2)
    X, yv = TASK_FEATURES[T2](Xr), np.asarray(y.values, dtype=object)
    Xt_raw = load_test(T2)
    Xt, ids = TASK_FEATURES[T2](Xt_raw), list(Xt_raw.flow_id)
    s = np.array([sub[f] for f in ids], dtype=object)
    out = {}
    for a in ARMS:
        p = np.asarray(factory(a)(0).fit(X, yv).predict(Xt), dtype=object)
        out[a] = {"changed_vs_submitted": int((p != s).sum()),
                  "changes": {ids[i]: f"{s[i]} -> {p[i]}" for i in np.flatnonzero(p != s)}}
    print(out)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=ARMS)
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
        for s in SEEDS:
            for arm in ARMS:
                run(arm, s)
    else:
        if not (a.arm and a.seed):
            ap.error("--arm and --seed are required")
        run(a.arm, a.seed)


if __name__ == "__main__":
    main()
