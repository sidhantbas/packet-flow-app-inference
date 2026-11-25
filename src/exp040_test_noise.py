"""Experiment 040: how much of the leaderboard gap is noise? (measurement only)

Command: .venv/bin/python src/exp040_test_noise.py
Sampling: 20,000 synthetic 81-flow test sets. Class mix = the labelled proportions scaled to 81 flows (largest remainder), because
the official split is stratified 60/20/20; metadata.json is not used. For each set, flows are drawn per class without replacement
from the 330 labelled flows, and each drawn flow takes one of its 10 held-out predictions from the production Task 1 run
(cv_seed 2026) at random. Score = the organisers' macro F1.
Flip analysis: in each sample, one or two facebook flows are switched from wrong to right (or right to wrong, as instagram), and
the macro F1 change is recorded; also repeated for a 2-facebook test mix.
"""
import numpy as np
import pandas as pd

from evaluation_metric import macro_f1
from runlog import load_champions, load_oof

N, SEED = 20000, 2026
rng = np.random.default_rng(SEED)
oof = load_oof(load_champions()["task1_static"]["run_id"], "task1_static")
preds = oof.groupby("flow_id").y_pred.apply(list)
truth = oof.groupby("flow_id").y_true.first()
apps = sorted(truth.unique())
counts = truth.value_counts()


def mix(total=81):
    raw = counts / counts.sum() * total
    base = np.floor(raw).astype(int)
    for a in (raw - base).sort_values(ascending=False).index[: total - base.sum()]:
        base[a] += 1
    return base


def sample(m):
    yt, yp = [], []
    for a, n in m.items():
        for f in rng.choice(truth.index[truth == a], size=n, replace=False):
            yt.append(a); yp.append(preds[f][rng.integers(10)])
    return yt, yp


def run(m, label):
    scores, d1, d2, w1, w2 = [], [], [], [], []
    for _ in range(N):
        yt, yp = sample(m)
        s = macro_f1(yt, yp); scores.append(s)
        fb = [i for i, t in enumerate(yt) if t == "facebook"]
        wrong = [i for i in fb if yp[i] != "facebook"]; right = [i for i in fb if yp[i] == "facebook"]
        for k, store in ((1, d1), (2, d2)):
            if len(wrong) >= k:
                p = list(yp)
                for i in rng.choice(wrong, k, replace=False): p[i] = "facebook"
                store.append(macro_f1(yt, p) - s)
        for k, store in ((1, w1), (2, w2)):
            if len(right) >= k:
                p = list(yp)
                for i in rng.choice(right, k, replace=False): p[i] = "instagram"
                store.append(macro_f1(yt, p) - s)
    sc = np.array(scores)
    print(f"\n== {label}: mix {dict(m)}")
    print(f"  macro F1 over {N} samples: median {np.median(sc):.3f}, 5th {np.percentile(sc, 5):.3f}, 95th {np.percentile(sc, 95):.3f}, "
          f"min {sc.min():.3f}, max {sc.max():.3f}")
    for name, v in (("our leaderboard Task 1", 0.787393), ("leader HeriTech Task 1", 0.94), ("4th place Task 1", 0.88)):
        print(f"  {name} {v:.3f}: at percentile {(sc < v).mean() * 100:.1f}  (P(sample >= {v:.3f}) = {(sc >= v).mean():.4f})")
    for name, v in (("1 facebook wrong -> right", d1), ("2 facebook wrong -> right", d2), ("1 facebook right -> wrong", w1), ("2 facebook right -> wrong", w2)):
        v = np.array(v)
        print(f"  {name}: mean Δ {v.mean():+.3f} (= {50 * v.mean():+.1f} points), 5th-95th {np.percentile(v, 5):+.3f} to {np.percentile(v, 95):+.3f}; "
              f"possible in {len(v) / N:.0%} of samples")
    return sc


if __name__ == "__main__":
    m = mix()
    run(m, "test-sized mix from labelled proportions")
    m2 = m.copy(); m2["facebook"] -= 1; m2["google"] += 1
    run(m2, "same, with 2 facebook flows")
