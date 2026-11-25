"""Experiment 057: captured flows only in the facebook-vs-instagram decision, and a low dose (protocol:
experiments/057_capture_meta_pair.md, frozen first).

Usage: python src/exp057_capture_meta_pair.py --arm S0|S1|D10 [--seed N --ref RUN_ID]
       python src/exp057_capture_meta_pair.py --production --seed N   (reference on a confirmation seed)
S0: production, then rows called facebook/instagram re-decided by a balanced SoftVote facebook-vs-instagram specialist
    on 15 columns (gate-2 columns without mean_iat; no min_iat, no p5_ columns). S1: as S0 with the captured facebook and
    instagram rows added to the specialist only. D10: production with a random 10% of the captured rows per class in the
    training fold (new draw per fold). Held-out flows are always original (cv.evaluate `resample` hook).
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

from capture_checks import PROX_COLS
from cv import TASK_FEATURES, evaluate
from exp056_capture_augmentation import captured_rows
from models import TASK_MODELS, SoftVote
from runlog import record_run

TASK = "task1_static"
META = ("facebook", "instagram")
SPEC_COLS = [c for c in PROX_COLS if c != "mean_iat"]
FLAG = "_captured"
DOSE = 0.10


class MetaPairOverride(BaseEstimator, ClassifierMixin):
    """Production Task 1 model; its facebook/instagram calls are re-decided by a pair specialist. Rows with _captured == 1
    train the specialist only (never the production model)."""

    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y)
        cap = X[FLAG].values == 1 if FLAG in X else np.zeros(len(X), bool)
        Xb = X.drop(columns=[FLAG], errors="ignore")
        self.base_ = TASK_MODELS[TASK](self.seed).fit(Xb[~cap], y[~cap])
        rows = np.isin(y, META)
        self.spec_ = SoftVote(seed=self.seed).fit(Xb.loc[rows, SPEC_COLS], y[rows])
        self.classes_ = self.base_.classes_
        self.n_captured_in_specialist_ = int((rows & cap).sum())
        return self

    def predict(self, X):
        Xb = X.drop(columns=[FLAG], errors="ignore")
        p = np.asarray(self.base_.predict(Xb), dtype=object)
        m = np.isin(p, META)
        if m.any():
            p[m] = self.spec_.predict(Xb.loc[m, SPEC_COLS])
        return p


def pair_model(seed):
    return MetaPairOverride(seed=seed)


def resample_s1():
    C, yc = captured_rows()
    keep = np.isin(yc, META)
    C, yc = C[keep], yc[keep]

    def resample(X_tr, y_tr, seed):
        Cx = C[X_tr.columns].copy()
        Cx.index = np.arange(len(Cx)) + int(X_tr.index.max()) + 1
        Xo = X_tr.assign(**{FLAG: 0})
        Cx[FLAG] = 1
        return pd.concat([Xo, Cx]), pd.concat([pd.Series(np.asarray(y_tr), index=X_tr.index), pd.Series(yc, index=Cx.index)])
    resample.n_added = {a: int((yc == a).sum()) for a in META}
    return resample


def resample_d10():
    C, yc = captured_rows()
    idx = {a: np.flatnonzero(yc == a) for a in META}
    k = {a: int(round(DOSE * len(i))) for a, i in idx.items()}

    def resample(X_tr, y_tr, seed):
        rng = np.random.default_rng(seed)
        pick = np.concatenate([rng.choice(idx[a], size=k[a], replace=False) for a in META])
        Cx = C.iloc[pick][X_tr.columns].copy()
        Cx.index = np.arange(len(Cx)) + int(X_tr.index.max()) + 1
        return pd.concat([X_tr, Cx]), pd.concat([pd.Series(np.asarray(y_tr), index=X_tr.index), pd.Series(yc[pick], index=Cx.index)])
    resample.n_added = k
    return resample


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    sfx = "" if seed == 2026 else f"_s{seed}"
    if "--production" in args:
        f = TASK_MODELS[TASK]
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("057", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 1 production reference on cv_seed {seed} (for 057 confirmation)",
                         config={"model": "task1_meta_gate", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        if arm == "S0":
            f, rs, added = pair_model, None, {}
        elif arm == "S1":
            f, rs = pair_model, resample_s1()
            added = rs.n_added
        elif arm == "D10":
            f, rs = TASK_MODELS[TASK], resample_d10()
            added = rs.n_added
        else:
            raise SystemExit("arm must be S0, S1 or D10")
        res = {TASK: evaluate(TASK, feats, f, resample=rs, cv_seed=seed)}
        rid = record_run("057", f"{arm}{sfx}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"Task 1 057 arm {arm}: captured flows only where they cannot compete with non-Meta classes; cv_seed {seed}",
                         config={"arm": arm, "cv_seed": seed, "features": feats.__name__, "captured_rows_added": added,
                                 "specialist_cols": SPEC_COLS if arm != "D10" else None, "dose": DOSE if arm == "D10" else None,
                                 "user_decision": "2026-10-09 run despite gates 1-2 failing (056 override)"}, started=t0)
    print(rid)
