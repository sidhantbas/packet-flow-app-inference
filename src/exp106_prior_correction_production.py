"""Experiment 106: prior correction (beta = 0.25, as claimed by LLM_ops) inside our Task 1 production
(protocol: experiments/106_prior_correction_production.md). The only change to production (models.task1_cross_task) is one line
in the Meta gate: the three experts' averaged probabilities are prior-corrected (flowkit.postprocess.prior_correct) before the
gate decides. Every other production rule is reused unchanged.

Usage (from the repository root):
  .venv/bin/python src/exp106_prior_correction_production.py --smoke          # beta = 0 reproduces production on one fold
  .venv/bin/python src/exp106_prior_correction_production.py --all            # P then B25 on seeds 2121-2125
  .venv/bin/python src/exp106_prior_correction_production.py --arm B25 --seed 2121
  .venv/bin/python src/exp106_prior_correction_production.py --analyse
  .venv/bin/python src/exp106_prior_correction_production.py --test-effect
Runs go to results/<stamp>_106_<arm>_s<seed>/; other evidence to experiments/106_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cv import TASK_FEATURES, evaluate, load_task
from flowkit.counts import label_counts
from flowkit.postprocess import prior_correct
from models import (REST_COLS, BundleVerifiers, CrossTaskMetaRescue, RestIGMetaGate, ScopedH1, SoftVote, Task1Bundle,
                    task1_bundle, task1_cross_task, task2_model)
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
SEEDS = (2121, 2122, 2123, 2124, 2125)
EVIDENCE = ROOT / "experiments/106_evidence"


class PriorGate(RestIGMetaGate):
    """089's gate with the experts' average prior-corrected before gating. beta = 0 is the production gate."""

    def __init__(self, seed=0, mode="full", beta=0.25):
        super().__init__(seed=seed, mode=mode)
        self.beta = beta

    def fit(self, X, y):
        super().fit(X, y)
        self.shares_ = {c: n / len(y) for c, n in label_counts(np.asarray(y, dtype=object)).items()}
        return self

    def predict(self, X):  # RestIGMetaGate.predict with one added line (marked)
        Xr, X = X[REST_COLS], X[self.base_cols_]
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = (pw + po + self.rest_.predict_proba(Xr)) / 3
        p = prior_correct(p, list(cls), self.shares_, self.beta)  # experiment 106
        g = self.gate_.predict_proba(X)[:, list(self.gate_.classes_).index("meta")]
        meta = np.isin(cls, self.META)
        pm = p[:, meta].sum(axis=1, keepdims=True)
        pr = p[:, ~meta].sum(axis=1, keepdims=True)
        q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
        pred = cls[q.argmax(axis=1)]
        in_meta = np.isin(pred, self.META)
        fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
        pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
        whole = c.whole_.predict(X)
        w_meta = np.isin(whole, self.META)
        pred[w_meta] = whole[w_meta]
        first = c.whole_.models_[0].predict(X[c.whole_.cols_[0]])
        pred[first == "facebook"] = "facebook"
        pred = np.asarray(pred, dtype=object)
        tc = np.asarray(c.predict(X), dtype=object)
        m = (pred == "instagram") & ~np.isin(tc, self.META)
        pred[m] = tc[m]
        return pred


class PriorVerifiers(BundleVerifiers):
    def __init__(self, seed=0, beta=0.25):
        super().__init__(seed=seed)
        self.beta = beta

    def fit(self, X, y):  # BundleVerifiers.fit with PriorGate as the base
        y = np.asarray(y)
        self.cols_ = [c for c in X.columns if c not in REST_COLS]
        self.base_ = PriorGate(seed=self.seed, beta=self.beta).fit(X, y)
        self.ver_ = {}
        for call, pair in self.VERIFIERS.items():
            m = np.isin(y, pair)
            self.ver_[call] = SoftVote(seed=self.seed).fit(X.loc[m, self.cols_], y[m])
        self.classes_ = self.base_.classes_
        return self


class PriorBundle(Task1Bundle):
    def __init__(self, seed=0, beta=0.25):
        super().__init__(seed=seed)
        self.beta = beta

    def fit(self, X, y):
        beta = self.beta
        self.model_ = ScopedH1(base_factory=lambda s: PriorVerifiers(seed=s, beta=beta), seed=self.seed).fit(self._with_rest(X), y)
        self.classes_ = self.model_.classes_
        return self


class PriorProduction(CrossTaskMetaRescue):
    """task1_cross_task with PriorBundle in place of task1_bundle."""

    def __init__(self, seed=0, beta=0.25):
        super().__init__(seed=seed)
        self.beta = beta

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.t1_ = PriorBundle(seed=self.seed, beta=self.beta).fit(X, y)
        self.t2_ = task2_model(self.seed).fit(self._opening(X), y)
        self.classes_ = self.t1_.classes_
        return self


def b25(seed):
    return PriorProduction(seed=seed, beta=0.25)


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_106_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    f, feats = (task1_cross_task if arm == "P" else b25), TASK_FEATURES[T1]
    t0 = datetime.now(timezone.utc)
    res = {T1: evaluate(T1, feats, f, cv_seed=seed)}
    rid = record_run("106", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id("P", seed),
                     question=f"Task 1 106 {arm} (prior correction beta=0.25 inside production) on never-used cv_seed {seed}",
                     config={"arm": arm, "beta": None if arm == "P" else 0.25, "cv_seed": seed}, started=t0)
    print(rid, flush=True)


def smoke():
    from sklearn.model_selection import RepeatedStratifiedKFold
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2121).split(X, yv))
    a = PriorProduction(seed=0, beta=0.0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te])
    b = task1_cross_task(0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te])
    c = PriorProduction(seed=0, beta=0.25).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te])
    print("beta = 0 reproduces production:", bool((np.asarray(a) == np.asarray(b)).all()),
          "| beta = 0.25 changes", int((np.asarray(c) != np.asarray(b)).sum()), "of", len(te), "predictions on fold 0")


def analyse():
    f1 = lambda a, s: pd.read_csv(ROOT / "results" / run_id(a, s) / T1 / "folds.csv").macro_f1.values  # noqa: E731
    per, cls_d = [], []
    for s in SEEDS:
        d = f1("B25", s) - f1("P", s)
        per.append([round(float(d.mean()), 4), int((d > 1e-12).sum()), int((d < -1e-12).sum())])
        a = pd.read_csv(ROOT / "results" / run_id("B25", s) / T1 / "oof.csv")
        b = pd.read_csv(ROOT / "results" / run_id("P", s) / T1 / "oof.csv")
        ch = a.y_pred.values != b.y_pred.values
        cls_d.append({"changed": int(ch.sum()), "fixed": int((ch & (a.y_pred.values == a.y_true.values)).sum()),
                      "broken": int((ch & (b.y_pred.values == b.y_true.values)).sum()),
                      "transitions": dict(Counter(f"{x} -> {z}" for x, z in zip(b.y_pred.values[ch], a.y_pred.values[ch])).most_common(5))})
    out = {"means": {a: [round(float(f1(a, s).mean()), 4) for s in SEEDS] for a in ("P", "B25")},
           "B25_vs_P": {"mean_delta": round(float(np.mean([p[0] for p in per])), 4), "per_seed": per}, "changes": cls_d}
    print(json.dumps(out, indent=1))
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T1]
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    Xt_raw = load_test(T1)
    p = np.asarray(b25(0).fit(X, yv).predict(TASK_FEATURES[T1](Xt_raw)), dtype=object)
    ids = list(Xt_raw.flow_id)
    s = np.array([sub[f] for f in ids], dtype=object)
    out = {"changed_vs_submitted": int((p != s).sum()), "changes": {ids[i]: f"{s[i]} -> {p[i]}" for i in np.flatnonzero(p != s)},
           "predicted_counts": dict(Counter(p))}
    print(out)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2, default=int) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=("P", "B25"))
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
            run("P", s)
            run("B25", s)
    else:
        if not (a.arm and a.seed):
            ap.error("--arm and --seed are required")
        run(a.arm, a.seed)


if __name__ == "__main__":
    main()
