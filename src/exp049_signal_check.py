"""Experiment 049: is the facebook vs instagram full-flow signal app behaviour or session length? (measurement only)

Command: .venv/bin/python src/exp049_signal_check.py
Task 1 labelled flows (330), production unchanged. Folds: RepeatedStratifiedKFold 5 x 10, cv_seed 2026, on the 30 Meta flows.
1. Length vs rate: median and IQR per class of duration, packet counts, bytes and their per-second rates; Mann-Whitney U
   (two-sided) and rank-biserial effect size r for facebook vs instagram, and for the two other confused pairs.
2. Facebook vs instagram random forest (`models.rf`, balanced) on three column sets, 100-shuffle permutation test each:
   original (17 full-flow + 17 prefix-5 columns); rates (duration, packet counts, bytes and burst_count replaced by
   packets/s, bytes/s per direction and bursts/min; duration floored at 1 ms); length only (duration, counts, bytes).
3. Truncation: the released files hold only full-flow and first-5-packet aggregates, so features over the first 10/30/60/
   120 s cannot be computed. Measured instead: prefix-5 columns only vs full-flow columns only vs both; and the duration
   distribution of facebook and instagram flows (for the capture protocol).
4. Importance stability: how often each of 048's top 10 features is in a fold's top 10 (impurity importance, 50 folds).
Not recorded with runlog.record_run (binary diagnostics). No test data used.
"""
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import mannwhitneyu
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import CV_SEED, TASK_FEATURES, load_task
from models import rf

TASK, FB, IG = "task1_static", "facebook", "instagram"
Xr, y = load_task(TASK)
X = TASK_FEATURES[TASK](Xr)
yv = np.asarray(y, dtype=object)
TOP10_048 = ["packet_count_up", "packet_count_down", "bytes_down", "bytes_up", "burst_count", "std_iat", "mean_iat",
             "p5_std_pkt_size_down", "std_pkt_size_down", "mean_pkt_size_down"]
LENGTH = ["duration", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "burst_count"]


def with_rates(D):
    R = D.copy()
    d = R.duration.clip(lower=1e-3)
    for c in ("packet_count_up", "packet_count_down", "bytes_up", "bytes_down"):
        R[c.replace("packet_count", "pkts") + "_per_s"] = R[c] / d
    R["bursts_per_min"] = R.burst_count / d * 60
    return R


A = with_rates(X)


def step1():
    print("## 1. Session length vs rate (median [IQR])\n")
    cols = ["duration", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down",
            "pkts_up_per_s", "pkts_down_per_s", "bytes_up_per_s", "bytes_down_per_s", "bursts_per_min"]
    apps = [FB, IG, "google", "youtube", "mozilla", "x"]

    def cell(v):
        q1, m, q3 = np.percentile(v, [25, 50, 75])
        f = (lambda z: f"{z:.0f}") if m >= 10 else (lambda z: f"{z:.2f}")
        return f"{f(m)} [{f(q1)}-{f(q3)}]"

    print("| Column | " + " | ".join(apps) + " |\n|---|" + "---|" * len(apps))
    for c in cols:
        print(f"| {c} | " + " | ".join(cell(A.loc[yv == a, c]) for a in apps) + " |")
    print("\nMann-Whitney U, two-sided; r = rank-biserial effect size (positive: first app larger)\n")
    pairs = [(FB, IG), ("google", "youtube"), ("mozilla", "x")]
    print("| Column | " + " | ".join(f"{a} vs {b}: r (p)" for a, b in pairs) + " |\n|---|" + "---|" * len(pairs))
    for c in cols:
        out = []
        for a, b in pairs:
            u, p = mannwhitneyu(A.loc[yv == a, c], A.loc[yv == b, c], alternative="two-sided")
            r = 2 * u / ((yv == a).sum() * (yv == b).sum()) - 1
            out.append(f"{r:+.2f} ({p:.3f})")
        print(f"| {c} | " + " | ".join(out) + " |")


M = np.isin(yv, (FB, IG))
yB = yv[M]


def cv_rf(D, labels, importances=False):
    f1s, imps = [], []
    for i, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED).split(D, labels)):
        m = rf(i).fit(D.iloc[tr], labels[tr])
        f1s.append(f1_score(labels[te] == FB, m.predict(D.iloc[te]) == FB, zero_division=0))
        if importances:
            imps.append(pd.Series(m.feature_importances_, index=D.columns))
    return np.array(f1s), imps


def perm_test(D, n=100):
    obs, _ = cv_rf(D, yB)
    perm = np.array(Parallel(n_jobs=-1)(delayed(lambda k: cv_rf(D, np.random.default_rng(k).permutation(yB))[0].mean())(k)
                                        for k in range(n)))
    return obs, perm, (1 + np.sum(perm >= obs.mean())) / (n + 1)


def row(name, D, perm=True):
    if perm:
        obs, sh, p = perm_test(D)
        print(f"| {name} | {D.shape[1]} | {obs.mean():.3f} | {obs.std(ddof=1):.3f} | {sh.mean():.3f} | {p:.3f} |")
    else:
        obs, _ = cv_rf(D, yB)
        print(f"| {name} | {D.shape[1]} | {obs.mean():.3f} | {obs.std(ddof=1):.3f} | not run | not run |")


def step2():
    print("\n## 2. Facebook vs Instagram random forest: rates instead of length (50 folds, 100 shuffles)\n")
    B = A[M].reset_index(drop=True)
    orig = list(X.columns)
    rates = [c for c in orig if c not in LENGTH] + ["pkts_up_per_s", "pkts_down_per_s", "bytes_up_per_s",
                                                   "bytes_down_per_s", "bursts_per_min"]
    print("| Column set | Columns | Facebook F1 | Fold std | Shuffled mean | p |\n|---|---|---|---|---|---|")
    row("original (048)", B[orig])
    row("rates (length columns replaced)", B[rates])
    row("length only", B[LENGTH])


def step3():
    print("\n## 3. Truncation proxy: opening vs full flow (50 folds)\n")
    B = A[M].reset_index(drop=True)
    p5 = [c for c in X.columns if c.startswith("p5_")]
    full = [c for c in X.columns if not c.startswith("p5_")]
    print("| Column set | Columns | Facebook F1 | Fold std | Shuffled mean | p |\n|---|---|---|---|---|---|")
    row("first 5 packets only", B[p5])
    row("full flow only", B[full])
    row("both (original)", B[list(X.columns)], perm=False)
    print("\nFlow duration (s) of the labelled Meta flows\n")
    print("| App | n | min | 25% | median | 75% | 90% | max | share > 60 s | share > 300 s |\n|---|---|---|---|---|---|---|---|---|---|")
    for a in (FB, IG):
        d = X.loc[yv == a, "duration"]
        q = np.percentile(d, [0, 25, 50, 75, 90, 100])
        print(f"| {a} | {len(d)} | " + " | ".join(f"{v:.0f}" for v in q) +
              f" | {np.mean(d > 60):.2f} | {np.mean(d > 300):.2f} |")
    print("\nPer flow (sorted):", {a: sorted(X.loc[yv == a, "duration"].round(0).astype(int).tolist()) for a in (FB, IG)})


def step4():
    print("\n## 4. Importance stability: folds (of 50) in which each 048 top-10 feature is in the fold's top 10\n")
    B = X[M].reset_index(drop=True)
    _, imps = cv_rf(B, yB, importances=True)
    top = [set(s.sort_values(ascending=False).index[:10]) for s in imps]
    mean = pd.concat(imps, axis=1).mean(axis=1)
    rank = mean.rank(ascending=False).astype(int)
    print("| Feature | 048 rank | Folds in top 10 | Part of the flow |\n|---|---|---|---|")
    for c in TOP10_048:
        print(f"| {c} | {rank[c]} | {sum(c in t for t in top)}/50 | {'opening' if c.startswith('p5_') else 'full flow'} |")
    others = pd.Series({c: sum(c in t for t in top) for c in B.columns if c not in TOP10_048}).sort_values(ascending=False)
    print("\nMost frequent others:", ", ".join(f"{c} {v}/50" for c, v in others.head(3).items()))


if __name__ == "__main__":
    for s in (step1, step2, step3, step4):
        s()
