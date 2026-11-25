"""Experiment 063: Android captures and same-label-filtered captures in Task 1 training folds (protocol:
experiments/063_capture_android_filtered.md, frozen first).

Usage: python src/exp063_capture_android_filtered.py --arm AND|FILT [--seed N --ref RUN_ID]
       python src/exp063_capture_android_filtered.py --production --seed N   (production reference on a confirmation seed)
Captured rows enter training folds only (cv.evaluate `resample`); held-out flows are always original. FILT keeps a captured
row only if its nearest original training-fold row (16 gate-2 columns, log1p, standardised on the fold) has the same label.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from capture_checks import PROX_COLS
from cv import TASK_FEATURES, basic_features, evaluate
from exp056_capture_augmentation import captured_rows as iphone_rows
from models import TASK_MODELS
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASK = "task1_static"
ANDROID = ROOT / "data/captures/sid-android-20261009T152334Z-check-macshare"
ANDROID_SESSIONS = {"01-facebook": "facebook", "02-instagram": "instagram"}
META = ("facebook", "instagram")
KEPT_LOG = []


def android_rows():
    rows, labels = [], []
    for s, app in ANDROID_SESSIONS.items():
        T1, T2 = pd.read_csv(ANDROID / s / "task1_features.csv"), pd.read_csv(ANDROID / s / "task2_features.csv")
        L = pd.read_csv(ANDROID / s / "labels.csv")
        assert (T1.flow_id == T2.flow_id).all() and (T1.flow_id == L.flow_id).all() and (L.app == app).all()
        P = basic_features(T2).reset_index(drop=True)
        P.columns = [f"p5_{c}" for c in P.columns]
        rows.append(pd.concat([basic_features(T1).reset_index(drop=True), P], axis=1))
        labels += [app] * len(T1)
    return pd.concat(rows, ignore_index=True), np.array(labels)


def scaled(Xo, Xc):
    f = lambda X: np.log1p(X[PROX_COLS].astype(float).clip(lower=0)).values
    Lo, Lc = f(Xo), f(Xc)
    mu, sd = Lo.mean(0), np.where(Lo.std(0) > 0, Lo.std(0), 1)
    return (Lo - mu) / sd, (Lc - mu) / sd


def make_resample(arm):
    A, ya = android_rows()
    if arm == "AND":
        C, yc = A, ya
    else:
        I, yi = iphone_rows()
        keep = np.isin(yi, META)
        C, yc = pd.concat([I[keep], A], ignore_index=True), np.r_[yi[keep], ya]

    def resample(X_tr, y_tr, seed):
        Cx = C[X_tr.columns].reset_index(drop=True)
        y_c = yc
        if arm == "FILT":
            Zo, Zc = scaled(X_tr, Cx)
            d = ((Zc[:, None, :] - Zo[None, :, :]) ** 2).sum(-1)
            nearest = np.asarray(y_tr)[d.argmin(axis=1)]
            m = nearest == y_c
            Cx, y_c = Cx[m].reset_index(drop=True), y_c[m]
            KEPT_LOG.append({"facebook": int((y_c == "facebook").sum()), "instagram": int((y_c == "instagram").sum())})
        Cx.index = np.arange(len(Cx)) + int(X_tr.index.max()) + 1
        return pd.concat([X_tr, Cx]), pd.concat([pd.Series(np.asarray(y_tr), index=X_tr.index), pd.Series(y_c, index=Cx.index)])
    resample.pool = {a: int((yc == a).sum()) for a in META}
    return resample


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    f, feats = TASK_MODELS[TASK], TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    sfx = "" if seed == 2026 else f"_s{seed}"
    if "--production" in args:
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("063", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 1 production reference on cv_seed {seed} (for 063 confirmation)",
                         config={"model": "task1_meta_gate", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        rs = make_resample(arm)
        res = {TASK: evaluate(TASK, feats, f, resample=rs, cv_seed=seed)}
        rid = record_run("063", f"{arm}{sfx}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"Task 1 063 arm {arm}: captured rows in training folds; cv_seed {seed}",
                         config={"arm": arm, "cv_seed": seed, "features": feats.__name__, "captured_pool": rs.pool,
                                 "filter": "same-label nearest original training-fold row (16 gate-2 cols, log1p, z)" if arm == "FILT" else None,
                                 "user_decision": "2026-10-09 use captured data (056 gate override applies)"}, started=t0)
    print(rid)
