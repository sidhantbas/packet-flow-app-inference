"""Experiment 096: Task 2 timing as a tie-breaker only inside ambiguous 12-feature signature groups (protocol:
experiments/096_task2_timing_tiebreaker.md, frozen first). Task 2 files only.

Usage: python src/exp096_timing_tiebreak.py --seed N --ref RUN_ID          candidate on default folds
       python src/exp096_timing_tiebreak.py --grouped                       baseline + candidate on grouped folds
       python src/exp096_timing_tiebreak.py --analyse                       routing counts, corrected/introduced errors
"""
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from cv import TIMING, basic_features, evaluate, load_task, no_timing_features
from models import task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T2 = "task2_realtime_prefix5"
MIN_ROWS = 2
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]


def signature(X12):
    return X12.astype(str).agg("|".join, axis=1).values


def eligible_groups(X12, y):
    """Signature -> supported labels, for training signatures with >= 2 labels of >= MIN_ROWS rows each."""
    out = {}
    for k, labs in pd.DataFrame({"k": signature(X12), "y": np.asarray(y, dtype=object)}).groupby("k").y:
        c = Counter(labs)
        sup = sorted(l for l, n in c.items() if n >= MIN_ROWS)
        if len(c) >= 2 and len(sup) >= 2:
            out[k] = sup
    return out


def _log1p0(A):
    return np.log1p(np.clip(np.asarray(A, dtype=float), 0, None))


class TimingTieBreak(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.nt_ = [c for c in X.columns if c not in TIMING]
        self.base_ = task2_model(self.seed).fit(X[self.nt_], y)
        self.groups_ = eligible_groups(X[self.nt_], y)
        keys = signature(X[self.nt_])
        rows = np.array([k in self.groups_ and lab in self.groups_[k] for k, lab in zip(keys, y)])
        self.tb_ = None
        if rows.any():
            self.tb_ = make_pipeline(FunctionTransformer(_log1p0), StandardScaler(),
                                     LogisticRegression(C=0.1, max_iter=5000)).fit(X.loc[rows, TIMING], y[rows])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        p = np.asarray(self.base_.predict(X[self.nt_]), dtype=object)
        if self.tb_ is None:
            return p
        P = self.tb_.predict_proba(X[TIMING])
        cls = list(self.tb_.classes_)
        for i, k in enumerate(signature(X[self.nt_])):
            sup = self.groups_.get(k)
            if sup:
                idx = [cls.index(c) for c in sup]
                p[i] = cls[idx[int(np.argmax(P[i, idx]))]]
        return p


def candidate(seed):
    return TimingTieBreak(seed=seed)


def grouped_splits(seed=2026, n_repeats=10):
    Xr, y = load_task(T2)
    B = np.log1p(basic_features(Xr).astype(float).clip(lower=0)).values
    Z = (B - B.mean(0)) / np.where(B.std(0) > 0, B.std(0), 1)
    D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(-1))
    _, groups = connected_components(D <= 0.05, directed=False)
    out = []
    for r in range(n_repeats):
        out += list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed + r).split(np.zeros(len(y)), y, groups))
    return out, groups


def analyse(cand_run, base_run, splits):
    """Routing per fold (training rows only), corrected/introduced errors, eligible vs other flows."""
    Xr, y = load_task(T2)
    X12 = no_timing_features(Xr).reset_index(drop=True)
    yv = np.asarray(y.values, dtype=object)
    c = pd.read_csv(ROOT / "results" / cand_run / T2 / "oof.csv")
    b = pd.read_csv(ROOT / "results" / base_run / T2 / "oof.csv")
    flows = np.concatenate([Xr.flow_id.values[te] for _, te in splits])
    assert (c.flow_id.values == flows).all() and (b.flow_id.values == flows).all()
    elig = []
    for tr, te in splits:
        g = eligible_groups(X12.iloc[tr], yv[tr])
        keys = signature(X12.iloc[te])
        elig.append(np.array([k in g for k in keys]))
    E = np.concatenate(elig)
    yt, yb, yc = c.y_true.values, b.y_pred.values.astype(object), c.y_pred.values.astype(object)
    rep = c.fold.values // 5
    other_same = bool((yb[~E] == yc[~E]).all())
    d_rep = [f1_score(yt[rep == k], yc[rep == k], labels=LABS, average="macro") - f1_score(yt[rep == k], yb[rep == k], labels=LABS, average="macro")
             for k in range(rep.max() + 1)]
    res = {"eligible_predictions": int(E.sum()), "eligible_per_fold": [int(e.sum()) for e in elig],
           "folds_with_eligible": int(sum(e.any() for e in elig)),
           "eligible_by_true_label": dict(Counter(yt[E])), "other_flows_identical_to_baseline": other_same,
           "changed": int((yb != yc).sum()), "corrected": int(((yb != yt) & (yc == yt)).sum()),
           "introduced": int(((yb == yt) & (yc != yt)).sum()),
           "eligible_accuracy": {"baseline": float((yb[E] == yt[E]).mean()) if E.any() else None,
                                 "candidate": float((yc[E] == yt[E]).mean()) if E.any() else None},
           "eligible_changes_by_pair": dict(Counter(f"{t}: {a}->{bb}" for t, a, bb in zip(yt[E & (yb != yc)], yb[E & (yb != yc)], yc[E & (yb != yc)]))),
           "delta_macro_per_repeat": [round(v, 4) for v in d_rep],
           "delta_macro_repeat_mean": round(float(np.mean(d_rep)), 4), "delta_macro_repeat_sd": round(float(np.std(d_rep, ddof=1)), 4)}
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    t0 = datetime.now(timezone.utc)
    if "--grouped" in args:
        sp, groups = grouped_splits()
        name = "StratifiedGroupKFold(5) x 10, seed 2026, groups = Task 2 17-column near-twins within 0.05"
        rb = record_run("096", "baseline_grouped", {T2: evaluate(T2, no_timing_features, task2_model, splits=sp, split_name=name)},
                        model_factory=task2_model, feature_fn=no_timing_features, reference=None,
                        question="Task 2 production on grouped folds (096 robustness)",
                        config={"model": "task2_model", "splits": name, "n_groups": int(groups.max() + 1)}, started=t0)
        rc = record_run("096", "TB_grouped", {T2: evaluate(T2, basic_features, candidate, splits=sp, split_name=name)},
                        model_factory=candidate, feature_fn=basic_features, reference=rb,
                        question="Task 2 096 TB on grouped folds", config={"arm": "TB", "splits": name}, started=t0)
        print(rb, rc)
    elif "--analyse" in args:
        out = {}
        for seed, base in ((2026, "20260930T173836Z_014_fi_same_nocw"), (2027, "20260930T173928Z_014_fi_same_nocw_s2027"),
                           (2028, "20260930T173952Z_014_fi_same_nocw_s2028")):
            cand = sorted(p.name for p in (ROOT / "results").glob(f"*_096_TB{'' if seed == 2026 else f'_s{seed}'}"))[-1]
            Xr, y = load_task(T2)
            sp = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(Xr, y))
            out[str(seed)] = {"candidate_run": cand, "baseline_run": base, **analyse(cand, base, sp)}
        gb = sorted(p.name for p in (ROOT / "results").glob("*_096_baseline_grouped"))
        gc = sorted(p.name for p in (ROOT / "results").glob("*_096_TB_grouped"))
        if gb and gc:
            out["grouped"] = {"candidate_run": gc[-1], "baseline_run": gb[-1], **analyse(gc[-1], gb[-1], grouped_splits()[0])}
        d = ROOT / "experiments/096_evidence"
        d.mkdir(exist_ok=True)
        (d / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps(out, indent=1))
    else:
        seed = int(args[args.index("--seed") + 1])
        ref = args[args.index("--ref") + 1]
        rid = record_run("096", "TB" + ("" if seed == 2026 else f"_s{seed}"),
                         {T2: evaluate(T2, basic_features, candidate, cv_seed=seed)}, model_factory=candidate,
                         feature_fn=basic_features, reference=ref,
                         question=f"Task 2 096 TB: timing tie-breaker inside ambiguous 12-feature signature groups; cv_seed {seed}",
                         config={"arm": "TB", "min_rows_per_label": MIN_ROWS, "tie_breaker": "LogisticRegression(C=0.1, unweighted) on log1p timing, standardised",
                                 "cv_seed": seed, "features": "basic_features (Task 2 file only)"}, started=t0)
        print(rid)
