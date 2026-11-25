"""Experiment 124: low-dose capture training in Charles's design (protocol: experiments/124_low_dose_capture_training.md,
frozen first).

Usage: python src/exp124_low_dose_capture_training.py --seed 2181|2182|2183   (needs `git fetch upstream`: reads d3189ba)
Per seed: P (production, original flows only), then B10 and B25 (production with k_c = round(budget * n_c) of Charles's 364
process-supported candidates per captured class added to each training fold; new draw per fold), each compared with P on the same
folds. Held-out flows are always original (cv.evaluate `resample` hook).
"""
import io
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cv import TASK_FEATURES, basic_features, evaluate
from models import TASK_MODELS
from runlog import record_run

TASK = "task1_static"
UPSTREAM = "d3189ba"
BASE = "experiments/charles-003-capture-audit/evidence/20261020-flow-aggregates/observed"
APPS = ("facebook", "instagram", "youtube")
BUDGETS = {"B10": 0.10, "B25": 0.25}


def show(name):
    out = subprocess.run(["git", "show", f"{UPSTREAM}:{BASE}/{name}"], capture_output=True, text=True, check=True).stdout
    return pd.read_csv(io.StringIO(out))


def captured_rows():
    """Charles's candidates as production Task 1 columns (basic Task 1 columns + p5_ Task 2 columns) and their labels."""
    T1, T2, L = show("candidate_task1_features.csv"), show("candidate_task2_features.csv"), show("candidate_labels.csv")
    assert (T1.flow_id == T2.flow_id).all() and (T1.flow_id == L.flow_id).all()
    P = basic_features(T2).reset_index(drop=True)
    P.columns = [f"p5_{c}" for c in P.columns]
    return pd.concat([basic_features(T1).reset_index(drop=True), P], axis=1), L.app.values


def make_resample(budget, cv_seed):
    C, yc = captured_rows()
    idx = {a: np.flatnonzero(yc == a) for a in APPS}
    added = []

    def resample(X_tr, y_tr, seed):
        rng = np.random.default_rng(cv_seed * 1000 + seed)
        y_arr = np.asarray(y_tr)
        pick = np.concatenate([rng.choice(idx[a], size=min(len(idx[a]), int(round(budget * (y_arr == a).sum()))), replace=False)
                               for a in APPS]).astype(int)
        Cx = C.iloc[pick][X_tr.columns].copy()
        Cx.index = np.arange(len(Cx)) + int(X_tr.index.max()) + 1
        added.append({a: int((yc[pick] == a).sum()) for a in APPS})
        return pd.concat([X_tr, Cx]), pd.concat([pd.Series(y_arr, index=X_tr.index), pd.Series(yc[pick], index=Cx.index)])
    resample.__name__ = f"charles_low_dose_{budget}"
    resample.n_captured = {a: len(i) for a, i in idx.items()}
    return resample


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1])
    f, feats = TASK_MODELS[TASK], TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
    ref = record_run("124", f"P_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                     question=f"Task 1 production reference on never-used cv_seed {seed} (124)",
                     config={"arm": "P", "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(ref)
    for arm, budget in BUDGETS.items():
        t0 = datetime.now(timezone.utc)
        rs = make_resample(budget, seed)
        res = {TASK: evaluate(TASK, feats, f, resample=rs, cv_seed=seed)}
        rid = record_run("124", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"Task 1 124 arm {arm}: Charles's 364 capture candidates at budget {budget} of each class's "
                                  f"training count, training folds only; cv_seed {seed}",
                         config={"arm": arm, "budget": budget, "cv_seed": seed, "features": feats.__name__,
                                 "captured_source": f"charles-003 observed candidates at {UPSTREAM}", "captured_available": rs.n_captured,
                                 "user_decision": "2026-10-20 run despite gate 2 failing (121, 123); measurement only"}, started=t0)
        print(rid)
