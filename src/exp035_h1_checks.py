"""Experiment 035: Facebook/Instagram error checks and a direct H1 test for the Task 1 production model.

Command: .venv/bin/python src/exp035_h1_checks.py
  1. Re-fits the production Task 1 model (models.TASK_MODELS) on the default folds (cv_seed 2026) and records, for every held-out
     row, the final label and the gate-weighted probability vector it starts from (p). Asserts the labels equal the logged
     champion run.
  2. Lists non-facebook flows predicted facebook and misclassified instagram flows (majority label over 10 repeats).
  3. For each facebook<->instagram error: exact / nearest opening match among labelled flows of the true and the predicted class
     (opening = the 12 Task 2 columns without timing, exact values; distance on log1p + standardised values).
     H1 simulation, fixed before running: inside each fold, if a held-out flow's exact opening occurs in the training fold
     with a single label, predict that label; otherwise keep the production label. Counts fixes and breaks; macro F1 per fold.
  4. Twin check: CV with flow_000809 and flow_001168 (near-identical facebook fetches) forced into the same fold of every repeat
     (each repeat: 001168 swapped with a facebook flow of 000809's fold, keeping stratification).
"""
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import CV_SEED, TASK_FEATURES, basic_features, load_task, no_timing_features
from evaluation_metric import macro_f1
from models import T1_COLS, TASK_MODELS
from runlog import load_champions, load_oof

T1, T2 = "task1_static", "task2_realtime_prefix5"
X_raw, y = load_task(T1)
X = TASK_FEATURES[T1](X_raw)
FID = X_raw.flow_id.values
Y = y.values
P_raw, _ = load_task(T2)
assert (P_raw.flow_id.values == FID).all()
OPEN = no_timing_features(P_raw).reset_index(drop=True)
OKEY = OPEN.astype(str).agg("|".join, axis=1).values
CLS = np.array(sorted(set(Y)))


def fold_run(i, tr, te):
    m = TASK_MODELS[T1](i).fit(X.iloc[tr], y.iloc[tr])
    Xt = X.iloc[te]
    pred = np.asarray(m.predict(Xt))
    c, cls = m.clerks_, np.asarray(m.classes_)
    pw = c.whole_.predict_proba(Xt)
    po = c.opening_.predict_proba(Xt[list(c.OPEN_COLS)])
    p = (pw + po) / 2
    g = m.gate_.predict_proba(Xt)[:, list(m.gate_.classes_).index("meta")]
    meta = np.isin(cls, m.META)
    q = np.where(meta, g[:, None] * p / p[:, meta].sum(1, keepdims=True), (1 - g[:, None]) * p / p[:, ~meta].sum(1, keepdims=True))
    return pd.DataFrame({"fold": i, "row": te, "flow": FID[te], "y_true": Y[te], "y_pred": pred,
                         "p_pred": q[np.arange(len(te)), [list(cls).index(v) for v in pred]]})


def oof(splits):
    return pd.concat(Parallel(n_jobs=-1)(delayed(fold_run)(i, tr, te) for i, (tr, te) in enumerate(splits)), ignore_index=True)


def per_flow(o):
    g = o.groupby("flow")
    maj = g.y_pred.agg(lambda s: s.value_counts().idxmax())
    votes = g.y_pred.agg(lambda s: s.value_counts().iloc[0])
    p = pd.Series({f: o[(o.flow == f) & (o.y_pred == maj[f])].p_pred.mean() for f in maj.index})
    return pd.DataFrame({"y_true": g.y_true.first(), "pred": maj, "votes": votes, "p": p})


def scaled(V):
    L = np.log1p(np.clip(V.values.astype(float), 0, None))
    return (L - L.mean(0)) / np.where(L.std(0) > 0, L.std(0), 1)


ZW = scaled(basic_features(X_raw)[list(T1_COLS)])   # whole flow, 17 columns
ZO = scaled(OPEN)                                   # opening, 12 columns


def nearest(Z, j, cls):
    idx = np.where((Y == cls) & (np.arange(len(Y)) != j))[0]
    d = np.sqrt(((Z[idx] - Z[j]) ** 2).sum(1))
    k = idx[np.argmin(d)]
    return FID[k][5:], float(d.min())


def opening_txt(j):
    o = OPEN.iloc[j]
    return f"{int(o.packet_count_up)}/{int(o.packet_count_down)} pkts, {int(o.bytes_up)}/{int(o.bytes_down)} B"


def h1(o, splits):
    """Trust a label-consistent exact opening twin from the training fold; otherwise keep the production label."""
    out = o.copy()
    for i, (tr, te) in enumerate(splits):
        tk = pd.DataFrame({"k": OKEY[tr], "y": Y[tr]}).groupby("k").y.agg(lambda s: s.unique())
        sel = out.fold == i
        for idx in out.index[sel]:
            labs = tk.get(OKEY[out.at[idx, "row"]])
            if labs is not None and len(labs) == 1:
                out.at[idx, "y_pred"] = labs[0]
    return out


def fold_scores(o):
    return o.groupby("fold").apply(lambda g: macro_f1(list(g.y_true), list(g.y_pred)), include_groups=False)


def fb_f1(o):
    def f(g):
        tp = ((g.y_true == "facebook") & (g.y_pred == "facebook")).sum()
        fp = ((g.y_true != "facebook") & (g.y_pred == "facebook")).sum()
        fn = ((g.y_true == "facebook") & (g.y_pred != "facebook")).sum()
        return 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return o.groupby("fold").apply(f, include_groups=False)


def twin_splits(base, a="flow_000809", b="flow_001168", n_splits=5):
    ia, ib = int(np.where(FID == a)[0][0]), int(np.where(FID == b)[0][0])
    out = []
    for r in range(len(base) // n_splits):
        tests = [list(base[r * n_splits + k][1]) for k in range(n_splits)]
        fa = next(k for k in range(n_splits) if ia in tests[k])
        fb = next(k for k in range(n_splits) if ib in tests[k])
        if fa != fb:  # swap b with a facebook flow of a's fold (not a itself), keeping class counts per fold
            swap = next(j for j in tests[fa] if Y[j] == "facebook" and j != ia)
            tests[fa][tests[fa].index(swap)] = ib
            tests[fb][tests[fb].index(ib)] = swap
        allrows = np.arange(len(Y))
        for k in range(n_splits):
            te = np.array(sorted(tests[k]))
            out.append((np.setdiff1d(allrows, te), te))
    return out


def main():
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED).split(X, y))
    o = oof(splits)
    ref = load_oof(load_champions()[T1]["run_id"], T1)
    a = o.sort_values(["fold", "flow"]).y_pred.values
    b = ref.sort_values(["fold", "flow_id"]).y_pred.values
    print(f"reproduces champion {load_champions()[T1]['run_id']}: {(a == b).all()} ({(a != b).sum()} mismatches)")
    pf = per_flow(o)

    print("\n== 1a. non-facebook flows predicted facebook (majority over 10 repeats)")
    for f, r in pf[(pf.pred == "facebook") & (pf.y_true != "facebook")].iterrows():
        j = int(np.where(FID == f)[0][0]); nf, nd = nearest(ZW, j, r.y_true)
        print(f"  {f[5:]} true {r.y_true:9s} pred {r.pred:9s} votes {r.votes}/10 p {r.p:.2f} | opening {opening_txt(j)} | nearest {r.y_true} {nf} ({nd:.2f})")
    anyfb = o[(o.y_pred == "facebook") & (o.y_true != "facebook")]
    print(f"  (any repeat: {anyfb.flow.nunique()} non-facebook flows predicted facebook at least once; {len(anyfb)} predictions)")
    print("\n== 1b. misclassified instagram flows (majority)")
    for f, r in pf[(pf.y_true == "instagram") & (pf.pred != "instagram")].iterrows():
        j = int(np.where(FID == f)[0][0]); nf, nd = nearest(ZW, j, "instagram")
        print(f"  {f[5:]} true instagram pred {r.pred:9s} votes {r.votes}/10 p {r.p:.2f} | opening {opening_txt(j)} | nearest instagram {nf} ({nd:.2f})")

    print("\n== 2. facebook<->instagram errors (majority) vs openings of the true / predicted class")
    meta_err = pf[pf.y_true.isin(["facebook", "instagram"]) & pf.pred.isin(["facebook", "instagram"]) & (pf.y_true != pf.pred)]
    flips = 0
    for f, r in meta_err.iterrows():
        j = int(np.where(FID == f)[0][0])
        twins = [(FID[k][5:], Y[k]) for k in np.where(OKEY == OKEY[j])[0] if k != j]
        nt, dt = nearest(ZO, j, r.y_true); npd, dp = nearest(ZO, j, r.pred)
        labs = {lab for _, lab in twins}
        flip = len(labs) == 1 and r.y_true in labs
        flips += flip
        print(f"  {f[5:]} true {r.y_true} pred {r.pred} ({r.votes}/10) | opening {opening_txt(j)} | exact twins {twins or 'none'} | "
              f"nearest opening: true-class {nt} {dt:.2f}, predicted-class {npd} {dp:.2f} | flips if exact twin trusted: {flip}")
    print(f"  facebook<->instagram errors: {len(meta_err)}, would flip to correct by a label-consistent exact twin: {flips}")

    print("\n== H1 simulation (exact, label-consistent opening twin in the training fold overrides; all classes)")
    oh = h1(o, splits)
    base_s, h1_s = fold_scores(o), fold_scores(oh)
    d = h1_s.values - base_s.values
    changed = oh.y_pred != o.y_pred
    fixed = (changed & (oh.y_pred == oh.y_true)).sum(); broken = (changed & (o.y_pred == o.y_true)).sum()
    print(f"  predictions changed {changed.sum()} of {len(o)}: fixed {fixed}, broken {broken}, wrong->wrong {changed.sum() - fixed - broken}")
    print(f"  macro F1 {base_s.mean():.4f} -> {h1_s.mean():.4f} (Δ {d.mean():+.4f}); folds won {(d > 1e-12).sum()}, lost {(d < -1e-12).sum()}, tied {(abs(d) <= 1e-12).sum()}")
    ch = oh[changed].assign(was=o.y_pred[changed])
    print("  changes by true class -> (was, now):")
    print(ch.groupby(["y_true", "was", "y_pred"]).size().rename("n").reset_index().to_string(index=False))

    print("\n== 3. twins 000809 + 001168 forced into the same fold")
    ts = twin_splits(splits)
    for k, (tr, te) in enumerate(ts):
        assert not set(tr) & set(te) and len(te) == len(splits[k][1])
    ot = oof(ts)
    print(f"  facebook F1: original folds {fb_f1(o).mean():.3f} -> twins together {fb_f1(ot).mean():.3f}")
    print(f"  macro F1:    original folds {base_s.mean():.4f} -> twins together {fold_scores(ot).mean():.4f}")
    for f in ("flow_000809", "flow_001168"):
        r0, r1 = per_flow(o).loc[f], per_flow(ot).loc[f]
        print(f"  {f}: original {r0.pred} {r0.votes}/10 -> twins together {r1.pred} {r1.votes}/10")


if __name__ == "__main__":
    main()
