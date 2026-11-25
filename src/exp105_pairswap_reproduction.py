"""Experiment 105: reproduce Infralibre's FlowLens-v9-PairSwap on Task 1, with due diligence
(protocol: experiments/105_pairswap_reproduction.md). Components: src/flowkit (counts, swap); this runner builds the arms,
runs CV, and measures how often the label-blind swap fixes or breaks flows.

Usage (from the repository root):
  .venv/bin/python src/exp105_pairswap_reproduction.py --smoke
  .venv/bin/python src/exp105_pairswap_reproduction.py --arm P --seed 2116        # production reference first
  .venv/bin/python src/exp105_pairswap_reproduction.py --arm V1 --seed 2116       # compared with that P run
  .venv/bin/python src/exp105_pairswap_reproduction.py --all                      # every arm on every seed
  .venv/bin/python src/exp105_pairswap_reproduction.py --analyse                  # arms vs P and the swap accounting (D2, D3)
  .venv/bin/python src/exp105_pairswap_reproduction.py --test-effect              # swaps V1 and V2 would make on the test set
V3M (V0 matched to the true held-out counts, no swap) is recorded only as the reference for V3's swap accounting.
Runs go to results/<stamp>_105_<arm>_s<seed>/; other evidence to experiments/105_evidence/.
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
from flowkit.counts import label_counts, quota_assign
from flowkit.swap import consensus_pair_swap
from models import T1_COLS, SoftVote, TwoClerks, task1_cross_task, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
SEEDS = (2116, 2117, 2118, 2119, 2120)
ARMS = ("P", "V0", "V1", "V2", "V3M", "V3")
OPEN = list(TwoClerks.OPEN_COLS)
EVIDENCE = ROOT / "experiments/105_evidence"
LABELS = np.asarray(load_task(T1)[1].values, dtype=object)


class CrossView(BaseEstimator, ClassifierMixin):
    """Mean of balanced SoftVotes on the 17 Task 1 columns (view A) and the 12 first-5 columns (view B); then optional true-count
    matching (simulated disclosure) and optional consensus pair swap against view B."""

    def __init__(self, seed=0, swap=False, disclosed=False):
        self.seed, self.swap, self.disclosed = seed, swap, disclosed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.a_ = SoftVote(seed=self.seed).fit(X[list(T1_COLS)], y)
        self.b_ = SoftVote(seed=self.seed).fit(X[OPEN], y)
        self.classes_ = np.asarray(self.a_.classes_, dtype=object)
        assert list(self.b_.classes_) == list(self.classes_)
        return self

    def predict(self, X):
        PA, PB = self.a_.predict_proba(X[list(T1_COLS)]), self.b_.predict_proba(X[OPEN])
        P = (PA + PB) / 2
        cls = list(self.classes_)
        lab = self.classes_[P.argmax(axis=1)]
        if self.disclosed:
            lab = quota_assign(P, cls, label_counts(LABELS[np.asarray(X.index)]))
        if self.swap:
            lab, _ = consensus_pair_swap(lab, self.classes_[PB.argmax(axis=1)], PB, cls)
        return lab


class ProductionSwap(BaseEstimator, ClassifierMixin):
    """Production Task 1 labels, swapped against the Task 2 production model's view of the opening (ranked by its SoftVote)."""

    def __init__(self, seed=0):
        self.seed = seed

    @staticmethod
    def _opening(X):
        return X[OPEN].set_axis([c[len("p5_"):] for c in OPEN], axis=1)

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.t1_ = task1_cross_task(self.seed).fit(X, y)
        self.t2_ = task2_model(self.seed).fit(self._opening(X), y)
        self.classes_ = np.asarray(self.t2_.base_.classes_, dtype=object)
        return self

    def predict(self, X):
        lab = np.asarray(self.t1_.predict(X), dtype=object)
        Xo = self._opening(X)
        other = np.asarray(self.t2_.predict(Xo), dtype=object)
        out, _ = consensus_pair_swap(lab, other, self.t2_.base_.predict_proba(Xo), list(self.classes_))
        return out


def factory(arm):
    makers = {"P": task1_cross_task, "V0": lambda s: CrossView(seed=s), "V1": lambda s: CrossView(seed=s, swap=True),
              "V2": lambda s: ProductionSwap(seed=s), "V3M": lambda s: CrossView(seed=s, disclosed=True),
              "V3": lambda s: CrossView(seed=s, swap=True, disclosed=True)}
    if arm == "P":
        return task1_cross_task

    def f(seed):
        return makers[arm](seed)
    f.__name__ = f"pairswap_{arm.lower()}"
    return f


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_105_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    feats, f = TASK_FEATURES[T1], factory(arm)
    t0 = datetime.now(timezone.utc)
    res = {T1: evaluate(T1, feats, f, cv_seed=seed)}
    rid = record_run("105", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id("P", seed),
                     question=f"Task 1 105 {arm} (FlowLens-v9-PairSwap reproduction) on never-used cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed}, started=t0)
    print(rid, flush=True)


def smoke():
    rng = np.random.default_rng(0)
    cls = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
    ok = True
    for _ in range(200):
        lab = rng.choice(cls, 66).astype(object)
        oth = rng.choice(cls, 66).astype(object)
        out, sw = consensus_pair_swap(lab, oth, rng.dirichlet(np.ones(6), 66), cls)
        ok &= Counter(out) == Counter(lab) and all(out[p] == oth[p] and out[q] == oth[q] for p, q in sw)
    print("swap preserves class counts and only moves flows to the other view's label:", bool(ok))
    lab = rng.choice(cls, 66).astype(object)
    print("identical views make no swap:", consensus_pair_swap(lab, lab, rng.dirichlet(np.ones(6), 66), cls)[1] == [])


def oof(arm, seed):
    return pd.read_csv(ROOT / "results" / run_id(arm, seed) / T1 / "oof.csv")


def accounting(new, base):
    """Flows changed between two OOF tables: fixed, broken, wrong either way; per fold: net gain and broken count."""
    ch = new.y_pred.values != base.y_pred.values
    fixed = ch & (new.y_pred.values == new.y_true.values)
    broken = ch & (base.y_pred.values == base.y_true.values)
    folds = []
    for k in np.unique(new.fold.values):
        g = new.fold.values == k
        folds.append((int(ch[g].sum()), int(fixed[g].sum()), int(broken[g].sum())))
    return {"changed": int(ch.sum()), "fixed": int(fixed.sum()), "broken": int(broken.sum()),
            "wrong_either_way": int((ch & ~fixed & ~broken).sum()), "folds": folds}


def analyse():
    f1 = lambda a, s: pd.read_csv(ROOT / "results" / run_id(a, s) / T1 / "folds.csv").macro_f1.values  # noqa: E731
    out = {"means": {a: [round(float(f1(a, s).mean()), 4) for s in SEEDS] for a in ARMS}, "vs_P": {}, "swap_accounting": {}}
    for a in ("V0", "V1", "V2", "V3M", "V3"):
        per = []
        for s in SEEDS:
            d = f1(a, s) - f1("P", s)
            per.append([round(float(d.mean()), 4), int((d > 1e-12).sum()), int((d < -1e-12).sum())])
        out["vs_P"][a] = {"mean_delta": round(float(np.mean([p[0] for p in per])), 4), "per_seed": per}
        print(f"{a} vs P: {out['vs_P'][a]['mean_delta']:+.4f}", per)
    for new, base in (("V1", "V0"), ("V2", "P"), ("V3", "V3M")):
        acc = [accounting(oof(new, s), oof(base, s)) for s in SEEDS]
        folds = [f for a in acc for f in a["folds"]]
        tot = {k: sum(a[k] for a in acc) for k in ("changed", "fixed", "broken", "wrong_either_way")}
        swapped_folds = [f for f in folds if f[0] > 0]
        clean_plus2 = sum(1 for f in folds if f[1] - f[2] >= 2 and f[2] == 0)
        out["swap_accounting"][f"{new} vs {base}"] = tot | {
            "folds": len(folds), "folds_with_a_swap": len(swapped_folds),
            "folds_net_gain_ge_2_nothing_broken": clean_plus2,
            "mean_changed_per_fold": round(float(np.mean([f[0] for f in folds])), 2)}
        print(f"{new} vs {base}:", out["swap_accounting"][f"{new} vs {base}"])
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T1]
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    Xt_raw = load_test(T1)
    Xt = TASK_FEATURES[T1](Xt_raw)
    ids = list(Xt_raw.flow_id)
    submitted = np.array([sub[f] for f in ids], dtype=object)
    out = {}
    for arm in ("V0", "V1", "V2"):
        p = np.asarray(factory(arm)(0).fit(X, yv).predict(Xt), dtype=object)
        ch = p != submitted
        out[arm] = {"changed_vs_submitted": int(ch.sum()), "predicted_counts": dict(Counter(p)),
                    "changes": {ids[i]: f"{submitted[i]} -> {p[i]}" for i in np.flatnonzero(ch)}}
        print(arm, out[arm], flush=True)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2, default=int) + "\n")


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
