"""Experiment 097: reliability of Task 1 model 089 vs 084 with component ablations, on ordinary and twin-aware folds
(protocol: experiments/097_reliability_089_vs_084.md, frozen first).

Usage: python src/exp097_reliability.py --arm V089-R --folds ordinary|grouped --seed N [--ref RUN_ID]
       python src/exp097_reliability.py --smoke      (variants with all components off/on reproduce 084/089 on one fold)
       python src/exp097_reliability.py --analyse
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from exp036_twin_aware import twin_splits
from models import (REST_COLS, BundleVerifiers, MetaGate, ScopedH1, SoftVote, TwoClerks, rest_from_columns,
                    task1_bundle, task1_pair_verifiers)
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
ARMS = {"V084": (False, False, False), "V089": (True, True, True), "V089-R": (False, True, True),
        "V089-IG": (True, False, True), "V089-H1": (True, True, False)}
SAVED = {("V084", "ordinary", 2026): "20261009T220447Z_084_ALL", ("V084", "ordinary", 2027): "20261009T220504Z_084_ALL_s2027",
         ("V084", "ordinary", 2028): "20261009T220522Z_084_ALL_s2028",
         ("V089", "ordinary", 2026): "20261010T004051Z_089_production_check_s2026"}


class Gate(MetaGate):
    """MetaGate with the 089 additions as switches: rest = third (rest-of-flow) expert, ig = facebook-only gate rescue."""

    def __init__(self, seed=0, mode="full", rest=True, ig=True):
        super().__init__(seed=seed, mode=mode)
        self.rest, self.ig = rest, ig

    def fit(self, X, y):
        self.base_cols_ = [c for c in X.columns if c not in REST_COLS]
        super().fit(X[self.base_cols_], y)
        if self.rest:
            self.rest_ = SoftVote(seed=self.seed).fit(X[REST_COLS], np.asarray(y))
        return self

    def predict(self, X):
        Xr, X = X[REST_COLS], X[self.base_cols_]
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = (pw + po + self.rest_.predict_proba(Xr)) / 3 if self.rest else (pw + po) / 2
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
        if self.ig:
            tc = np.asarray(c.predict(X), dtype=object)
            m = (pred == "instagram") & ~np.isin(tc, self.META)
            pred[m] = tc[m]
        return pred


class Verifiers(BundleVerifiers):
    def __init__(self, seed=0, rest=True, ig=True):
        super().__init__(seed=seed)
        self.rest, self.ig = rest, ig

    def fit(self, X, y):
        y = np.asarray(y)
        self.cols_ = [c for c in X.columns if c not in REST_COLS]
        self.base_ = Gate(seed=self.seed, rest=self.rest, ig=self.ig).fit(X, y)
        self.ver_ = {}
        for call, pair in self.VERIFIERS.items():
            m = np.isin(y, pair)
            self.ver_[call] = SoftVote(seed=self.seed).fit(X.loc[m, self.cols_], y[m])
        self.classes_ = self.base_.classes_
        return self


class Variant(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0, rest=True, ig=True, h1=True):
        self.seed, self.rest, self.ig, self.h1 = seed, rest, ig, h1

    def _xa(self, X):
        return pd.concat([X, rest_from_columns(X)], axis=1)

    def fit(self, X, y):
        r, g = self.rest, self.ig
        base = lambda s: Verifiers(seed=s, rest=r, ig=g)  # noqa: E731
        self.model_ = (ScopedH1(base_factory=base, seed=self.seed) if self.h1 else base(self.seed)).fit(self._xa(X), y)
        self.classes_ = self.model_.classes_
        return self

    def predict(self, X):
        return self.model_.predict(self._xa(X))


def factory(arm):
    rest, ig, h1 = ARMS[arm]

    def f(seed):
        return Variant(seed=seed, rest=rest, ig=ig, h1=h1)
    f.__name__ = "variant_" + arm.lower().replace("-", "_")
    return f


def splits(folds, seed):
    if folds == "grouped":
        return twin_splits(seed)
    Xr, y = load_task(T1)
    return list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(Xr, y))


def run_id(arm, folds, seed):
    if (arm, folds, seed) in SAVED:
        return SAVED[(arm, folds, seed)]
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_097_{arm}_{folds}_s{seed}"))
    return hits[-1] if hits else None


def analyse():
    Xr, y = load_task(T1)
    X = TASK_FEATURES[T1](Xr).reset_index(drop=True)
    keys = X[list(TwoClerks.OPEN_COLS)].astype(str).agg("|".join, axis=1).values
    out = {}
    for folds in ("ordinary", "grouped"):
        for seed in (2026, 2027, 2028):
            sp = splits(folds, seed)
            match = np.concatenate([np.isin(keys[te], keys[tr]) for tr, te in sp])
            flows = np.concatenate([Xr.flow_id.values[te] for _, te in sp])
            P, F = {}, {}
            for arm in ARMS:
                rid = run_id(arm, folds, seed)
                o = pd.read_csv(ROOT / "results" / rid / T1 / "oof.csv")
                assert (o.flow_id.values == flows).all(), (arm, folds, seed)
                P[arm], F[arm] = o, pd.read_csv(ROOT / "results" / rid / T1 / "folds.csv").macro_f1.values
            yt = P["V084"].y_true.values
            rep = P["V084"].fold.values // 5
            cell = {"opening_match_share": round(float(match.mean()), 3), "arms": {}, "comparisons": {}}
            for arm, o in P.items():
                yp = o.y_pred.values
                cell["arms"][arm] = {
                    "run": run_id(arm, folds, seed), "macro_f1": round(float(F[arm].mean()), 4),
                    "per_class_f1": dict(zip(LABS, np.round(f1_score(yt, yp, labels=LABS, average=None), 3).tolist())),
                    "acc_with_opening_match": round(float((yp[match] == yt[match]).mean()), 4),
                    "acc_without_opening_match": round(float((yp[~match] == yt[~match]).mean()), 4),
                    "macro_with_match": round(float(f1_score(yt[match], yp[match], labels=LABS, average="macro")), 4),
                    "macro_without_match": round(float(f1_score(yt[~match], yp[~match], labels=LABS, average="macro")), 4)}
            for a, b in (("V089", "V084"), ("V089-R", "V089"), ("V089-IG", "V089"), ("V089-H1", "V089")):
                ya, yb = P[a].y_pred.values, P[b].y_pred.values
                d = F[a] - F[b]
                drep = [f1_score(yt[rep == k], ya[rep == k], labels=LABS, average="macro")
                        - f1_score(yt[rep == k], yb[rep == k], labels=LABS, average="macro") for k in range(10)]
                ch = ya != yb
                cell["comparisons"][f"{a} vs {b}"] = {
                    "delta_mean": round(float(d.mean()), 4), "wins": int((d > 1e-12).sum()), "losses": int((d < -1e-12).sum()),
                    "ties": int((np.abs(d) <= 1e-12).sum()), "changed": int(ch.sum()),
                    "corrected": int((ch & (ya == yt)).sum()), "introduced": int((ch & (yb == yt)).sum()),
                    "changed_with_match": int((ch & match).sum()), "changed_without_match": int((ch & ~match).sum()),
                    "delta_per_repeat": [round(v, 4) for v in drep]}
            out[f"{folds}_s{seed}"] = cell
            print(folds, seed, {k: (v["delta_mean"], v["wins"], v["losses"], v["corrected"], v["introduced"])
                                for k, v in cell["comparisons"].items()}, flush=True)
    d = ROOT / "experiments/097_evidence"
    d.mkdir(exist_ok=True)
    (d / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--smoke" in args:
        Xr, y = load_task(T1)
        X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
        tr, te = splits("ordinary", 2026)[0]
        for arm, ref in (("V084", task1_pair_verifiers), ("V089", task1_bundle)):
            a = factory(arm)(0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te])
            b = ref(0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te])
            print(arm, "identical to", ref.__name__, bool((np.asarray(a) == np.asarray(b)).all()))
        sys.exit()
    if "--analyse" in args:
        analyse()
        sys.exit()
    arm, folds = args[args.index("--arm") + 1], args[args.index("--folds") + 1]
    seed = int(args[args.index("--seed") + 1])
    ref = args[args.index("--ref") + 1] if "--ref" in args else None
    f, feats = factory(arm), TASK_FEATURES[T1]
    t0 = datetime.now(timezone.utc)
    sp = splits(folds, seed) if folds == "grouped" else None
    sname = f"twin-aware StratifiedGroupKFold(5) x 10, seed {seed}, 036 groups (17 Task 1 columns, 0.05)" if sp else None
    res = {T1: evaluate(T1, feats, f, cv_seed=seed, splits=sp, split_name=sname)}
    rid = record_run("097", f"{arm}_{folds}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"Task 1 097 {arm} on {folds} folds, seed {seed}",
                     config={"arm": arm, "rest": ARMS[arm][0], "ig": ARMS[arm][1], "h1": ARMS[arm][2], "folds": folds,
                             "cv_seed": seed}, started=t0)
    print(rid)
