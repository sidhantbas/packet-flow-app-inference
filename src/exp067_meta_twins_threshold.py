"""Experiment 067: Facebook/Instagram twins (protocol: experiments/067_meta_twins_threshold.md, frozen first).

Usage: python src/exp067_meta_twins_threshold.py --arm TH|THTW [--seed N --ref RUN_ID]
TH: Meta-labelled flows become facebook if r = p_fb / (p_fb + p_ig) of the whole-flow expert >= theta; theta from a nested
    inner 5-fold CV of production (grid 0.20..0.80, ties to 0.5). theta = 0.5 reproduces production.
THTW: TH, then Meta-labelled flows become facebook if their nearest training-fold facebook flow is within distance 1.0
    (16 gate-2 columns, log1p, standardised on the training fold). Each predicted flow is compared only with training
    facebook flows, never with other predicted (test) flows. (TW = twin rule without TH; kept for the smoke test only.)
Both: the production rule "17-column SoftVote calls facebook -> facebook" is applied last.
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from capture_checks import PROX_COLS
from cv import TASK_FEATURES, evaluate
from models import MetaGate
from runlog import record_run

TASK = "task1_static"
GRID = np.round(np.arange(0.20, 0.801, 0.05), 2)
DELTA = 1.0


def production_parts(m, X):
    """MetaGate.predict (mode full), also returning the whole-flow probabilities and the 17-column SoftVote labels."""
    c = m.clerks_
    cls = np.asarray(m.classes_)
    pw = c.whole_.predict_proba(X)
    po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
    p = (pw + po) / 2
    g = m.gate_.predict_proba(X)[:, list(m.gate_.classes_).index("meta")]
    meta = np.isin(cls, m.META)
    pm = p[:, meta].sum(axis=1, keepdims=True)
    pr = p[:, ~meta].sum(axis=1, keepdims=True)
    q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
    pred = cls[q.argmax(axis=1)]
    in_meta = np.isin(pred, m.META)
    fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
    pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
    whole = c.whole_.predict(X)
    w_meta = np.isin(whole, m.META)
    pred[w_meta] = whole[w_meta]
    first = c.whole_.models_[0].predict(X[c.whole_.cols_[0]])
    pred[first == "facebook"] = "facebook"
    r = pw[:, fb] / np.clip(pw[:, fb] + pw[:, ig], 1e-12, None)
    return pred.astype(object), r, first


def apply_threshold(pred, r, first, theta):
    out = pred.copy()
    m = np.isin(out, ("facebook", "instagram"))
    out[m] = np.where(r[m] >= theta, "facebook", "instagram")
    out[first == "facebook"] = "facebook"
    return out


def logz(X, ref):
    f = lambda A: np.log1p(A[PROX_COLS].astype(float).clip(lower=0)).values
    L, R = f(X), f(ref)
    mu, sd = R.mean(0), np.where(R.std(0) > 0, R.std(0), 1)
    return (L - mu) / sd


class TwinsMetaGate(MetaGate):
    def __init__(self, seed=0, mode="full", arm="TH"):
        super().__init__(seed=seed, mode=mode)
        self.arm = arm

    def fit(self, X, y):
        y = np.asarray(y)
        if self.arm in ("TH", "THTW"):
            r_oof, p_oof, f_oof = np.zeros(len(y)), np.empty(len(y), dtype=object), np.empty(len(y), dtype=object)
            for tr, te in StratifiedKFold(5, shuffle=True, random_state=self.seed).split(X, y):
                inner = MetaGate(seed=self.seed).fit(X.iloc[tr], y[tr])
                p_oof[te], r_oof[te], f_oof[te] = production_parts(inner, X.iloc[te])
            scores = [f1_score(y, apply_threshold(p_oof, r_oof, f_oof, t), average="macro") for t in GRID]
            best = max(scores)
            self.theta_ = float(min((t for t, s in zip(GRID, scores) if s == best), key=lambda t: abs(t - 0.5)))
        if self.arm in ("TW", "THTW"):
            self.ref_ = X.copy()
            self.fb_ = np.flatnonzero(y == "facebook")
        super().fit(X, y)
        return self

    def predict(self, X):
        pred, r, first = production_parts(self, X)
        if self.arm in ("TH", "THTW"):
            pred = apply_threshold(pred, r, first, self.theta_)
        if self.arm == "TH":
            return pred
        m = np.isin(pred, ("facebook", "instagram"))
        if m.any():
            Zx, Zr = logz(X, self.ref_), logz(self.ref_, self.ref_)
            d = np.sqrt(((Zx[m][:, None, :] - Zr[self.fb_][None]) ** 2).sum(-1)).min(axis=1)
            sub = pred[m]
            sub[d <= DELTA] = "facebook"
            pred[m] = sub
        pred[first == "facebook"] = "facebook"
        return pred


def make_factory(arm):
    def f(seed):
        return TwinsMetaGate(seed=seed, arm=arm)
    f.__name__ = f"twins_meta_gate_{arm.lower()}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    arm = args[args.index("--arm") + 1]
    feats, f = TASK_FEATURES[TASK], make_factory(arm)
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
    rid = record_run("067", arm + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"Task 1 067 arm {arm} (facebook/instagram twins) vs production; cv_seed {seed}",
                     config={"arm": arm, "grid": GRID.tolist() if "TH" in arm else None, "delta": DELTA if "TW" in arm else None,
                             "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
