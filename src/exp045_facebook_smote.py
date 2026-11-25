"""Experiment 045: formula-respecting synthetic Facebook flows in Task 1 training folds (BACKLOG Ready #1 after 044).

Settings fixed before running (2026-10-08):
- Training folds only (cv.evaluate `resample` hook); held-out flows are always real.
- For each training facebook flow: its k = 3 nearest training facebook flows with the same transport (Euclidean distance on
  z-scored log1p of the 17 Task 1 columns, z-scored within the fold). 2 synthetic flows per real one, each with a random
  neighbour among those k and lambda ~ U(0, 1). Flows without a same-transport facebook neighbour get none.
- Interpolation in log1p space, one lambda for all columns of a synthetic flow (so min <= mean <= max and similar orderings
  survive), for the free columns of both the full flow and the prefix-5 part:
  packet counts, mean and std packet sizes per direction, mean/std/min/max IAT, burst_count.
- Then the released formulas are re-imposed (041): counts are integers >= 1 (prefix: up in 1..5, down = 5 - up);
  bytes = count x mean size; duration = mean_iat x (packets - 1); ratios = up / max(down, 1); std size = 0 for a direction
  with <= 1 packet, mean and std = 0 for an empty direction; burst_count in 1..packets, 1 if max_iat < 1.0 s, >= 2 otherwise;
  transport copied (same in both flows).
- Production model unchanged (`models.TASK_MODELS`, balanced class weights): the synthetic rows share facebook's
  unchanged total weight, so they add new points, not extra weight.
Decision: rule v2 vs the Task 1 champion on cv_seed 2026; only a pass is confirmed on 2027-2030.
Usage: python src/exp045_facebook_smote.py [--seed N --ref RUN_ID] [--check]
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cv import TASK_FEATURES, evaluate
from models import T1_COLS, TASK_MODELS
from runlog import record_run

TASK = "task1_static"
FB, K, PER_FLOW, BURST_GAP = "facebook", 3, 2, 1.0
FREE = ("packet_count_up", "packet_count_down", "mean_pkt_size_up", "mean_pkt_size_down", "std_pkt_size_up",
        "std_pkt_size_down", "mean_iat", "std_iat", "min_iat", "max_iat", "burst_count")


def impose(r, p, prefix_total=None):
    """Re-impose the released formulas on one synthetic flow `r` (dict), for column prefix `p` ("" or "p5_")."""
    if prefix_total:
        up = int(np.clip(round(r[p + "packet_count_up"]), 1, prefix_total))
        dn = prefix_total - up
    else:
        up, dn = (max(1, int(round(r[p + c]))) for c in ("packet_count_up", "packet_count_down"))
    r[p + "packet_count_up"], r[p + "packet_count_down"] = up, dn
    for d, n in (("up", up), ("down", dn)):
        if n == 0:
            r[p + f"mean_pkt_size_{d}"] = r[p + f"std_pkt_size_{d}"] = 0.0
        elif n == 1:
            r[p + f"std_pkt_size_{d}"] = 0.0
        r[p + f"bytes_{d}"] = n * r[p + f"mean_pkt_size_{d}"]
    n = up + dn
    r[p + "duration"] = r[p + "mean_iat"] * (n - 1)
    b = int(np.clip(round(r[p + "burst_count"]), 1, n))
    r[p + "burst_count"] = 1 if r[p + "max_iat"] < BURST_GAP else max(b, 2)
    r[p + "up_down_packet_ratio"] = up / max(dn, 1)
    r[p + "up_down_byte_ratio"] = r[p + "bytes_up"] / max(r[p + "bytes_down"], 1)
    return r


def synth_facebook(X_tr, y_tr, seed):
    rng = np.random.default_rng(seed)
    y = np.asarray(y_tr)
    F = X_tr[y == FB]
    Z = np.log1p(F[list(T1_COLS)].clip(lower=0))
    Z = (Z - Z.mean()) / Z.std(ddof=0).replace(0, 1)
    free = [p + c for p in ("", "p5_") for c in FREE]
    rows = []
    for i in range(len(F)):
        same = np.flatnonzero((F.transport.values == F.transport.values[i]) & (np.arange(len(F)) != i))
        if not len(same):
            continue
        d = np.linalg.norm(Z.values[same] - Z.values[i], axis=1)
        nbrs = same[np.argsort(d, kind="stable")[:K]]
        for _ in range(PER_FLOW):
            j, lam = rng.choice(nbrs), rng.uniform()
            a, b = F.iloc[i], F.iloc[j]
            r = a.to_dict()
            for c in free:
                r[c] = float(np.expm1((1 - lam) * np.log1p(a[c]) + lam * np.log1p(b[c])))
            rows.append(impose(impose(r, ""), "p5_", prefix_total=5))
    if not rows:
        return X_tr, y_tr
    S = pd.DataFrame(rows, columns=X_tr.columns)
    S.index = np.arange(len(S)) + int(X_tr.index.max()) + 1
    return pd.concat([X_tr, S]), pd.concat([pd.Series(y, index=X_tr.index), pd.Series([FB] * len(S), index=S.index)])


def check():
    """Formula checks on the synthetic rows of one full-data resample (run before the CV, as a sanity test)."""
    from cv import load_task
    Xr, y = load_task(TASK)
    X = TASK_FEATURES[TASK](Xr)
    Xs, ys = synth_facebook(X, y, 0)
    S = Xs.iloc[len(X):]
    print(f"real facebook {int((y == FB).sum())}, synthetic {len(S)}")
    for p in ("", "p5_"):
        n = S[p + "packet_count_up"] + S[p + "packet_count_down"]
        print(p or "full", {
            "bytes": bool(np.allclose(S[p + "bytes_up"], S[p + "packet_count_up"] * S[p + "mean_pkt_size_up"])),
            "duration": bool(np.allclose(S[p + "duration"], S[p + "mean_iat"] * (n - 1))),
            "min<=mean<=max": bool(((S[p + "min_iat"] <= S[p + "mean_iat"] + 1e-9) & (S[p + "mean_iat"] <= S[p + "max_iat"] + 1e-9)).all()),
            "burst rule": bool(((S[p + "burst_count"] == 1) == (S[p + "max_iat"] < BURST_GAP)).all()),
            "packets": sorted(n.unique())[:5] if p else sorted(n.unique())})
    print(S[["transport", "duration", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "mean_iat", "burst_count"]]
          .describe().loc[["min", "50%", "max"]].round(2).to_string())


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--check" in args:
        check()
        sys.exit()
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    t0 = datetime.now(timezone.utc)
    f = TASK_MODELS[TASK]
    res = {TASK: evaluate(TASK, TASK_FEATURES[TASK], f, resample=synth_facebook, cv_seed=seed)}
    record_run("045", "fb_smote" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f,
               feature_fn=TASK_FEATURES[TASK], reference=ref,
               question=f"Task 1: do formula-respecting synthetic facebook flows in training folds beat production? cv_seed {seed}",
               config={"model": "task1_meta_gate + synth_facebook (k=3, 2 per flow)", "cv_seed": seed,
                       "features": TASK_FEATURES[TASK].__name__}, started=t0)
