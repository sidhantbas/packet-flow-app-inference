"""Experiment 076: screen candidate views of each flow for complementarity with production (definition:
experiments/076_view_screen.md, frozen first). Measurement only.

Command: .venv/bin/python src/exp076_view_screen.py
For each view: balanced SoftVote on the view's columns (cv_seed 2026, same folds as production), logged with record_run;
then fixes / breaks against production's out-of-fold predictions.
"""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cv import evaluate, task1_prefix_rest_features
from exp070_largest_up_packet_bounds import bounds
from models import SoftVote
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
TASK = "task1_static"
PROD = "20261001T173854Z_034_meta_gate"
REST = ["r_count_up", "r_bytes_up", "r_mean_size_up", "r_std_size_up", "r_count_down", "r_bytes_down", "r_mean_size_down",
        "r_std_size_down", "r_duration", "r_mean_iat", "r_std_iat"]
OPEN12 = ["p5_transport", "p5_packet_count_up", "p5_packet_count_down", "p5_bytes_up", "p5_bytes_down", "p5_mean_pkt_size_up",
          "p5_mean_pkt_size_down", "p5_std_pkt_size_up", "p5_std_pkt_size_down", "p5_burst_count", "p5_up_down_packet_ratio",
          "p5_up_down_byte_ratio"]


def share(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.where(b > 0, a / np.where(b > 0, b, 1), 0.0)


def low_bounds(n, m, s):
    n, m, s = (np.asarray(v, float) for v in (n, m, s))
    k = np.sqrt(np.clip(n - 1, 1, None))
    lo = np.where(n >= 2, m - s * k, np.where(n == 1, m, 0.0))
    hi = np.where(n >= 2, m - s / k, np.where(n == 1, m, 0.0))
    return lo, hi


def view_table(X):
    """All view columns from the production + rest table (Task 1 rows; p5_ = Task 2 row of the same flow)."""
    B = task1_prefix_rest_features(X)
    V = pd.DataFrame(index=B.index)
    n = B.packet_count_up + B.packet_count_down
    pn = B.p5_packet_count_up + B.p5_packet_count_down
    rn = B.r_count_up + B.r_count_down
    V["v2_share_bytes_up"] = share(B.p5_bytes_up, B.bytes_up)
    V["v2_share_bytes_down"] = share(B.p5_bytes_down, B.bytes_down)
    V["v2_share_packets"] = share(pn, n)
    V["v2_share_duration"] = share(B.p5_duration, B.duration)
    V["v2_open_minus_rest_size_up"] = B.p5_mean_pkt_size_up - B.r_mean_size_up
    V["v2_open_minus_rest_size_down"] = B.p5_mean_pkt_size_down - B.r_mean_size_down
    V["v2_open_minus_rest_up_ratio"] = B.p5_up_down_packet_ratio - share(B.r_count_up, np.maximum(B.r_count_down, 1))
    V["v2_transport"] = B.transport
    for d in ("up", "down"):
        nn, m, s = B[f"p5_packet_count_{d}"], B[f"p5_mean_pkt_size_{d}"], B[f"p5_std_pkt_size_{d}"]
        V[f"v3_max_lo_{d}"], V[f"v3_max_hi_{d}"] = bounds(nn, m, s)
        V[f"v3_min_lo_{d}"], V[f"v3_min_hi_{d}"] = low_bounds(nn, m, s)
        V[f"v3_equal_{d}"] = ((s == 0) & (nn > 0)).astype(int)
        V[f"v3_count_{d}"] = nn
    V["v3_transport"] = B.transport
    for c in REST:
        V[c] = B[c]
    for c in OPEN12:
        V["v0_" + c] = B[c]
    for c in ["duration", "mean_iat", "std_iat", "min_iat", "max_iat", "burst_count"]:
        V["v4_" + c] = B[c]
    for c in ["packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "mean_pkt_size_up", "mean_pkt_size_down",
              "std_pkt_size_up", "std_pkt_size_down", "up_down_packet_ratio", "up_down_byte_ratio", "transport"]:
        V["v5_" + c] = B[c]
    return V


VIEWS = {"V0_opening_reference": "v0_", "V1_rest": "r_", "V2_cross_view_shape": "v2_", "V3_opening_fingerprint": "v3_",
         "V4_timing": "v4_", "V5_size": "v5_"}


def view_features(prefix):
    def f(X):
        V = view_table(X)
        return V[[c for c in V.columns if c.startswith(prefix)]]
    f.__name__ = f"view_{prefix.rstrip('_')}"
    f.extra_data = task1_prefix_rest_features.extra_data
    return f


def sv(seed):
    return SoftVote(seed=seed)


def main():
    prod = pd.read_csv(ROOT / "results" / PROD / TASK / "oof.csv")
    rows = []
    for name, prefix in VIEWS.items():
        t0 = datetime.now(timezone.utc)
        feats = view_features(prefix)
        res = {TASK: evaluate(TASK, feats, sv, cv_seed=2026)}
        rid = record_run("076", name, res, model_factory=sv, feature_fn=feats, reference=None,
                         question=f"076 view screen: SoftVote on view {name} alone (measurement only)",
                         config={"view": name, "columns": res[TASK]["features"], "cv_seed": 2026}, started=t0)
        o = pd.read_csv(ROOT / "results" / rid / TASK / "oof.csv")
        assert (o.flow_id.values == prod.flow_id.values).all() and (o.fold.values == prod.fold.values).all()
        pw, vr = prod.y_pred != prod.y_true, o.y_pred == o.y_true
        meta = prod.y_true.isin(["facebook", "instagram"]); gy = prod.y_true.isin(["google", "youtube"])
        rows.append({"view": name, "run": rid, "n_cols": len(res[TASK]["features"]),
                     "macro_f1": round(float(np.mean(res[TASK]["fold_macro"])), 4),
                     "fixes": int((pw & vr).sum()), "fix_share": round(float((pw & vr).sum() / pw.sum()), 3),
                     "breaks": int((~pw & ~vr).sum()), "break_share": round(float((~pw & ~vr).sum() / (~pw).sum()), 3),
                     "fixes_meta": int((pw & vr & meta).sum()), "fixes_google_youtube": int((pw & vr & gy).sum()),
                     "fix_break_ratio": round(float((pw & vr).sum() / max((~pw & ~vr).sum(), 1)), 3)})
    T = pd.DataFrame(rows)
    out = ROOT / "experiments" / "076_evidence"
    out.mkdir(exist_ok=True)
    T.to_csv(out / "view_screen.csv", index=False)
    print(f"production errors (10 repeats): {int((prod.y_pred != prod.y_true).sum())}; right: {int((prod.y_pred == prod.y_true).sum())}")
    print(T.drop(columns="run").to_string(index=False))


if __name__ == "__main__":
    main()
