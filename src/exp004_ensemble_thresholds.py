"""Experiment 004 parts B-D: soft-voting ensemble, nested-CV class multipliers, google vs youtube.

Usage: python src/exp004_ensemble_thresholds.py [B|C|D ...]   (default: all parts)
Part C wraps the chosen base model in MultiplierClassifier, whose fit() learns the multipliers
by inner CV on the training data it is given. evaluate() only ever passes the outer training
fold, so the outer held-out fold is never used to pick them.
"""
import sys

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from ceilings import identical_groups, size_count_features
from cv import TASKS, evaluate
from exp003_confusion_variants import separation_report
from models import SoftVote, rf

GRID = np.geomspace(0.25, 4.0, 17)


def fit_multipliers(proba, y, classes, passes=3):
    """Coordinate ascent over per-class multipliers on GRID, maximising macro F1. Starts at 1; ties keep the current value."""
    w = np.ones(len(classes))
    score = lambda w: f1_score(y, classes[(proba * w).argmax(axis=1)], average="macro")
    best = score(w)
    for _ in range(passes):
        improved = False
        for k in range(len(classes)):
            for g in GRID:
                cand = w.copy()
                cand[k] = g
                s = score(cand)
                if s > best + 1e-12:
                    best, w, improved = s, cand, True
        if not improved:
            break
    return w


class MultiplierClassifier(BaseEstimator, ClassifierMixin):
    """Base model + per-class probability multipliers learned by inner stratified CV on the training data only."""

    def __init__(self, base_factory=rf, seed=0, inner_splits=5):
        self.base_factory, self.seed, self.inner_splits = base_factory, seed, inner_splits

    def fit(self, X, y):
        y = np.asarray(y)
        self.classes_ = np.unique(y)
        oof = np.zeros((len(y), len(self.classes_)))
        inner = StratifiedKFold(self.inner_splits, shuffle=True, random_state=self.seed)
        for tr, te in inner.split(X, y):
            m = self.base_factory(self.seed).fit(X.iloc[tr], y[tr])
            assert (m.classes_ == self.classes_).all()
            oof[te] = m.predict_proba(X.iloc[te])
        self.multipliers_ = fit_multipliers(oof, y, self.classes_)
        self.model_ = self.base_factory(self.seed).fit(X, y)
        return self

    def predict(self, X):
        return self.classes_[(self.model_.predict_proba(X) * self.multipliers_).argmax(axis=1)]


class LoggedMultiplierFactory:
    """model_factory for evaluate() that also records the multipliers learned in each outer fold."""

    def __init__(self, base_factory):
        self.base_factory, self.models = base_factory, []

    def __call__(self, seed):
        m = MultiplierClassifier(self.base_factory, seed)
        self.models.append(m)
        return m


def compare(name, res, base):
    diff = res["fold_macro"] - base["fold_macro"]
    wins, losses = int((diff > 0).sum()), int((diff < 0).sum())
    verdict = "BETTER" if diff.mean() > 0 and wins >= 35 else "not better"
    pc = res["fold_per_class"].mean(0)
    print(f"{name:22s} macro {res['macro_mean']:.4f} ± {res['macro_std']:.4f} | Δ {diff.mean():+.4f} "
          f"(paired std {diff.std(ddof=1):.4f}) | W/T/L {wins}/{50 - wins - losses}/{losses} | "
          + " ".join(f"{c} {v:.3f}" for c, v in zip(res["labels"], pc)) + f" | {verdict}")
    return verdict == "BETTER"


def part_b(task):
    base = evaluate(task, model_factory=rf)
    ens = evaluate(task, model_factory=lambda s: SoftVote(s))
    compare("a_rf_baseline", base, base)
    better = compare("b_softvote_rf_et_lgbm", ens, base)
    return base, ens, better


def part_c(task, base_name, base_factory, base_res):
    fac = LoggedMultiplierFactory(base_factory)
    res = evaluate(task, model_factory=fac)
    compare(f"{base_name}", base_res, base_res)
    compare(f"{base_name}+multipliers", res, base_res)
    W = np.array([m.multipliers_ for m in fac.models])
    print("learned multipliers across 50 outer folds (median [min–max]):")
    for c, col in zip(fac.models[0].classes_, W.T):
        print(f"  {c:10s} {np.median(col):.2f} [{col.min():.2f}–{col.max():.2f}]  (≠1 in {int((col != 1).sum())}/50)")


def part_d(task):
    separation_report(task, pair=["google", "youtube"])
    for mode, feats in [("all 17 model columns", None), ("size/count columns only", size_count_features)]:
        g, _ = identical_groups(task, feats) if feats else identical_groups(task)
        c = g.groupby("key").app.value_counts().unstack(fill_value=0)
        gy = c[(c.get("google", 0) > 0) & (c.get("youtube", 0) > 0)]
        print(f"[{mode}] identical-vector groups containing both google and youtube: {len(gy)}")
        if len(gy):
            print(gy.loc[:, (gy > 0).any()].reset_index(drop=True).to_string())


if __name__ == "__main__":
    parts = sys.argv[1:] or ["B", "C", "D"]
    for task in TASKS:
        print(f"\n################ {task}")
        if "B" in parts or "C" in parts:
            print("--- Part B")
            base, ens, ens_better = part_b(task)
        if "C" in parts:
            print("--- Part C")
            # Primary: the base chosen by the CLAUDE.md verdict rule (ensemble only if confirmed better).
            # Secondary: the other base too, since the ensemble has the higher mean in both tasks.
            primary = [("softvote", lambda s: SoftVote(s), ens), ("rf", rf, base)]
            if not ens_better:
                primary.reverse()
            for i, (name, fac, res) in enumerate(primary):
                print(f"[{'primary' if i == 0 else 'secondary'} base: {name}]")
                part_c(task, name, fac, res)
        if "D" in parts:
            print("--- Part D")
            part_d(task)
