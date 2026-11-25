"""Experiment 048: Facebook diagnostics, Task 1 (measurement only; production model unchanged).

Command: .venv/bin/python src/exp048_facebook_diagnostics.py [1 2 3 4]   (default: all steps)
Features: production's Task 1 set (cv.task1_with_prefix_features: 17 full-flow + 17 prefix-5 `p5_` columns).
Folds: RepeatedStratifiedKFold 5 x 10, cv_seed 2026 (the default CV), unless stated.
1. Facebook vs Instagram only (30 flows: 11 / 19): random forest and logistic regression (production's `models.rf` and
   `models.logreg`, balanced). Facebook F1 per fold (mean, std) and pooled; permutation test: 100 label shuffles of the 30
   flows, same CV re-split on the shuffled labels, p = (1 + #(shuffled mean F1 >= observed)) / 101.
2. Merged class: (a) production's 50-fold held-out predictions with facebook/instagram merged into "meta" afterwards;
   (b) the two-clerks model (production without the Meta gate, which needs both Meta classes) retrained on merged labels,
   same folds. Meta F1, macro F1 over 5 classes, vs production's 6-class macro F1 on the same folds.
3. Facebook vs Instagram random forest: impurity importance averaged over the 50 fold fits; each feature tagged as
   opening (prefix-5) or full flow.
4. Learning curve: production refitted on a stratified 20/40/60/80/100% subsample of each training fold (subsample seed =
   fold index), scored on the full held-out fold. Facebook F1 and macro F1, mean and fold std.
Not recorded with runlog.record_run: these are binary, 5-class and partial-data diagnostics, not 6-class candidates.
"""
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split

from cv import CV_SEED, TASK_FEATURES, load_task
from models import TASK_MODELS, TwoClerks, logreg, rf
from runlog import load_champions, load_oof

TASK, FB, IG = "task1_static", "facebook", "instagram"
Xr, y = load_task(TASK)
X = TASK_FEATURES[TASK](Xr)
yv = np.asarray(y, dtype=object)
FOLDS = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED).split(X, yv))


def kind(c):
    return "opening (prefix-5)" if c.startswith("p5_") else "full flow"


# ------------------------------------------------------------------ 1 + 3: Facebook vs Instagram
M = np.isin(yv, (FB, IG))
XB, yB = X[M].reset_index(drop=True), yv[M]
BIN = {"random forest": rf, "logistic regression": logreg}


def binary_cv(factory, labels, seed=CV_SEED, importances=False):
    f1s, yt, yp, imp = [], [], [], []
    for i, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(XB, labels)):
        m = factory(i).fit(XB.iloc[tr], labels[tr])
        p = m.predict(XB.iloc[te])
        f1s.append(f1_score(labels[te] == FB, p == FB, zero_division=0))
        yt += list(labels[te]); yp += list(p)
        if importances:
            imp.append(m.feature_importances_)
    pooled = f1_score(np.array(yt) == FB, np.array(yp) == FB)
    return np.array(f1s), pooled, (np.mean(imp, axis=0) if importances else None)


def shuffled(factory, k):
    lab = np.random.default_rng(k).permutation(yB)
    return binary_cv(factory, lab)[0].mean()


def step1():
    print("## 1. Facebook vs Instagram only (11 vs 19 flows; facebook = positive class)\n")
    print("| Model | Facebook F1 mean | Fold std | Pooled F1 | Shuffled mean (5th-95th) | p (100 shuffles) |\n|---|---|---|---|---|---|")
    for name, fac in BIN.items():
        f1s, pooled, _ = binary_cv(fac, yB)
        perm = np.array(Parallel(n_jobs=-1)(delayed(shuffled)(fac, k) for k in range(100)))
        p = (1 + np.sum(perm >= f1s.mean())) / 101
        print(f"| {name} | {f1s.mean():.3f} | {f1s.std(ddof=1):.3f} | {pooled:.3f} | "
              f"{perm.mean():.3f} ({np.percentile(perm, 5):.3f}-{np.percentile(perm, 95):.3f}) | {p:.3f} |")


def step3():
    print("\n## 3. Top 10 features, Facebook vs Instagram random forest (impurity importance, mean of 50 fold fits)\n")
    _, _, imp = binary_cv(rf, yB, importances=True)
    s = pd.Series(imp, index=XB.columns).sort_values(ascending=False)
    print("| Rank | Feature | Importance | Part of the flow |\n|---|---|---|---|")
    for r, (c, v) in enumerate(s.head(10).items(), 1):
        print(f"| {r} | {c} | {v:.3f} | {kind(c)} |")
    top = s.head(10)
    print(f"\nTop 10: {sum(kind(c) == 'full flow' for c in top.index)} full-flow, "
          f"{sum(kind(c) != 'full flow' for c in top.index)} opening; importance share of all full-flow columns "
          f"{s[[kind(c) == 'full flow' for c in s.index]].sum():.2f}")


# ------------------------------------------------------------------ 2: merged Meta class
def merge(a):
    return np.where(np.isin(a, (FB, IG)), "meta", a)


def clerks_fold(i, tr, te):
    m = TwoClerks(seed=i, mode="avg_meta_whole").fit(X.iloc[tr], merge(yv[tr]))
    return m.predict(X.iloc[te])


def step2():
    print("\n## 2. Merged Meta class (same 50 folds)\n")
    o = load_oof(load_champions()[TASK]["run_id"], TASK)
    rows = []
    prod6 = [f1_score(g.y_true, g.y_pred, average="macro") for _, g in o.groupby("fold")]
    post = [(f1_score(merge(g.y_true), merge(g.y_pred), average="macro"),
             f1_score(merge(g.y_true) == "meta", merge(g.y_pred) == "meta")) for _, g in o.groupby("fold")]
    preds = Parallel(n_jobs=-1)(delayed(clerks_fold)(i, tr, te) for i, (tr, te) in enumerate(FOLDS))
    retr = [(f1_score(merge(yv[te]), p, average="macro"), f1_score(merge(yv[te]) == "meta", p == "meta"))
            for (tr, te), p in zip(FOLDS, preds)]
    fb6 = [f1_score(g.y_true == FB, g.y_pred == FB, zero_division=0) for _, g in o.groupby("fold")]
    ig6 = [f1_score(g.y_true == IG, g.y_pred == IG, zero_division=0) for _, g in o.groupby("fold")]
    print("| Setup | Classes | Macro F1 | Fold std | Meta F1 (std) | Δ macro vs production |\n|---|---|---|---|---|---|")
    print(f"| production (6 classes) | 6 | {np.mean(prod6):.4f} | {np.std(prod6, ddof=1):.4f} | "
          f"facebook {np.mean(fb6):.3f} ({np.std(fb6, ddof=1):.3f}), instagram {np.mean(ig6):.3f} ({np.std(ig6, ddof=1):.3f}) | — |")
    for name, r in (("(a) production, merged afterwards", post), ("(b) two clerks retrained on merged labels", retr)):
        mac, meta = np.array([x[0] for x in r]), np.array([x[1] for x in r])
        d = mac - np.array(prod6)
        print(f"| {name} | 5 | {mac.mean():.4f} | {mac.std(ddof=1):.4f} | {meta.mean():.3f} ({meta.std(ddof=1):.3f}) | "
              f"{d.mean():+.4f} (higher in {np.sum(d > 0)}/50 folds) |")


# ------------------------------------------------------------------ 4: learning curve
def curve_fold(i, tr, te, frac):
    if frac < 1:
        tr, _ = train_test_split(tr, train_size=frac, stratify=yv[tr], random_state=i)
    p = TASK_MODELS[TASK](i).fit(X.iloc[tr], y.iloc[tr]).predict(X.iloc[te])
    return (f1_score(yv[te] == FB, p == FB, zero_division=0), f1_score(yv[te], p, average="macro"),
            int(np.sum(yv[tr] == FB)))


def step4():
    print("\n## 4. Learning curve (production model, stratified share of each training fold, 50 folds)\n")
    print("| Training share | Facebook flows in training | Facebook F1 | Fold std | Macro F1 | Fold std |\n|---|---|---|---|---|---|")
    for frac in (0.2, 0.4, 0.6, 0.8, 1.0):
        r = np.array(Parallel(n_jobs=-1)(delayed(curve_fold)(i, tr, te, frac) for i, (tr, te) in enumerate(FOLDS)))
        print(f"| {int(frac * 100)}% | {r[:, 2].mean():.1f} | {r[:, 0].mean():.3f} | {r[:, 0].std(ddof=1):.3f} | "
              f"{r[:, 1].mean():.3f} | {r[:, 1].std(ddof=1):.3f} |")


if __name__ == "__main__":
    steps = sys.argv[1:] or ["1", "2", "3", "4"]
    for s in steps:
        {"1": step1, "2": step2, "3": step3, "4": step4}[s]()
