"""Experiment 079: pipeline audit, diagnostic only (definitions: experiments/079_pipeline_audit.md, frozen first).

Command: .venv/bin/python src/exp079_pipeline_audit.py [step ...]   (steps 1-8; default all)
Uses production out-of-fold predictions only (Task 1: 5 seeds, Task 2: 3 seeds), train+validation labels only, no test
features. Writes CSV tables to experiments/079_evidence/ and prints a short summary per step.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict

from capture_checks import PROX_COLS
from cv import TASK_FEATURES, load_task, no_timing_features
from models import TASK_MODELS, SoftVote, knn

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "079_evidence"
T1, T2 = "task1_static", "task2_realtime_prefix5"
RUNS = {T1: ["20261001T173854Z_034_meta_gate", "20261009T172902Z_062_production_s2027", "20261009T173025Z_062_production_s2028",
             "20261009T173146Z_062_production_s2029", "20261009T173307Z_062_production_s2030"],
        T2: ["20260930T173836Z_014_fi_same_nocw", "20260930T173928Z_014_fi_same_nocw_s2027",
             "20260930T173952Z_014_fi_same_nocw_s2028"]}
NEAR = 0.10
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]


def oof(task):
    frames = []
    for s, r in enumerate(RUNS[task]):
        o = pd.read_csv(ROOT / "results" / r / task / "oof.csv")
        frames.append(o.assign(seed=s, rep=s * 10 + o.fold // 5))
    return pd.concat(frames, ignore_index=True)


def macro(df, pred="y_pred"):
    per_seed = [np.mean([f1_score(g.y_true, g[pred], labels=LABS, average="macro") for _, g in d.groupby("rep")])
                for _, d in df.groupby("seed")]
    return float(np.mean(per_seed))


def per_class(df, pred="y_pred"):
    return np.mean([f1_score(g.y_true, g[pred], labels=LABS, average=None, zero_division=0) for _, g in df.groupby("rep")], axis=0)


def space(task):
    X, y = load_task(task)
    if task == T1:
        B = X.assign(transport=(X.transport == "tcp").astype(int))[PROX_COLS]
    else:
        B = no_timing_features(X)
    Z = np.log1p(B.astype(float).clip(lower=0))
    Z = ((Z - Z.mean()) / Z.std(ddof=0).replace(0, 1)).values
    D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(-1))
    return X, np.asarray(y.values, dtype=object), D


def mixed_groups(task):
    X, y, D = space(task)
    n = len(y)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in zip(*np.where(np.triu(D <= NEAR, 1))):
        parent[find(i)] = find(j)
    comp = np.array([find(i) for i in range(n)])
    rows, unavoidable = [], np.zeros(n, bool)
    for c in np.unique(comp):
        idx = np.flatnonzero(comp == c)
        if len(idx) < 2:
            continue
        labs = pd.Series(y[idx]).value_counts()
        exact = bool((D[np.ix_(idx, idx)] == 0).sum() > len(idx))
        if len(labs) > 1:
            maj = labs.index[0]
            unavoidable[idx[y[idx] != maj]] = True
        rows.append({"group": int(c), "size": len(idx), "labels": dict(labs), "mixed": len(labs) > 1,
                     "has_exact_duplicate": exact, "flows": ",".join(X.flow_id.values[idx])})
    G = pd.DataFrame(rows)
    in_mixed = np.zeros(n, bool)
    for _, r in G[G.mixed].iterrows() if len(G) else []:
        for f in r.flows.split(","):
            in_mixed[np.flatnonzero(X.flow_id.values == f)[0]] = True
    return X, y, D, G, in_mixed, unavoidable


def step1(task, o):
    base = macro(o)
    lost = 50 * (1 - base)
    rows = []
    for a in LABS:
        for b in LABS:
            if a == b:
                continue
            m = (o.y_true == a) & (o.y_pred == b)
            if not m.any():
                continue
            fixed = o.assign(fx=np.where(m, o.y_true, o.y_pred))
            pts = 50 * (macro(fixed, "fx") - base)
            rows.append({"true": a, "predicted": b, "errors_per_repeat": round(m.sum() / o.rep.nunique(), 2),
                         "points": round(pts, 3), "share_of_gap": round(pts / lost, 3)})
    T = pd.DataFrame(rows).sort_values("points", ascending=False)
    T.to_csv(OUT / f"step1_point_map_{task}.csv", index=False)
    return base, lost, T


def step2(task, o):
    X, y, D, G, in_mixed, unavoidable = mixed_groups(task)
    G.to_csv(OUT / f"step2_groups_{task}.csv", index=False)
    floor = o.assign(fl=np.where(o.flow_id.map(dict(zip(X.flow_id, unavoidable))), "__wrong__", o.y_true))
    floor_macro = macro(floor, "fl")
    err = o[o.y_true != o.y_pred]
    on_mixed = err.flow_id.map(dict(zip(X.flow_id, in_mixed))).mean()
    return {"groups": int(len(G)), "mixed_groups": int(G.mixed.sum()) if len(G) else 0,
            "flows_in_mixed": int(in_mixed.sum()), "unavoidable_flows": int(unavoidable.sum()),
            "exact_dup_groups": int(G.has_exact_duplicate.sum()) if len(G) else 0,
            "floor_points_lost": round(50 * (1 - floor_macro), 2), "share_of_errors_on_mixed": round(float(on_mixed), 3)}, in_mixed, X


def separability(task, a, b):
    X, y = load_task(task)
    F = TASK_FEATURES[task](X)
    m = np.isin(y.values, [a, b])
    Xa, ya = F[m].reset_index(drop=True), (y.values[m] == b).astype(int)
    cv = StratifiedKFold(5, shuffle=True, random_state=2026)
    out = {}
    for name, model in (("knn", knn(0)), ("softvote", SoftVote(seed=0))):
        p = cross_val_predict(model, Xa, ya, cv=cv, method="predict_proba")[:, 1]
        out[name] = round(float(roc_auc_score(ya, p)), 3)
    return out


def subsample(tr, y, frac, seed):
    rng = np.random.default_rng(seed)
    keep = []
    for c in np.unique(y[tr]):
        idx = tr[y[tr] == c]
        k = max(1, int(round(frac * len(idx))))
        keep.append(rng.choice(idx, size=k, replace=False))
    return np.sort(np.concatenate(keep))


def step4(task):
    X, y = load_task(task)
    F = TASK_FEATURES[task](X)
    yv = y.values
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(F, y))

    def run(i, tr, te, frac):
        sub = subsample(tr, yv, frac, i)
        return i, te, TASK_MODELS[task](i).fit(F.iloc[sub], yv[sub]).predict(F.iloc[te])
    rows = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        res = Parallel(n_jobs=-1)(delayed(run)(i, tr, te, frac) for i, (tr, te) in enumerate(splits))
        yt = np.concatenate([yv[te] for _, te, _ in res])
        yp = np.concatenate([np.ravel(p) for *_, p in res])
        f1 = f1_score(yt, yp, labels=LABS, average=None, zero_division=0)
        rows.append({"fraction": frac, **dict(zip(LABS, np.round(f1, 3))), "macro": round(float(f1.mean()), 4)})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / f"step4_learning_curves_{task}.csv", index=False)
    return T


def step5(task, o):
    fold = o.groupby(["seed", "fold"]).apply(lambda g: pd.Series(f1_score(g.y_true, g.y_pred, labels=LABS, average=None,
                                                                          zero_division=0), index=LABS))
    seed_means = fold.groupby(level=0).mean()
    T = pd.DataFrame({"fold_sd": fold.std().round(3), "seed_mean_min": seed_means.min().round(3),
                      "seed_mean_max": seed_means.max().round(3), "flows_per_fold": (o.y_true.value_counts() / (len(RUNS[task]) * 50)).round(1)})
    T["detectable_per_fold_gain(0.52*fold_sd)"] = (0.52 * T.fold_sd).round(3)
    T.to_csv(OUT / f"step5_cv_reliability_{task}.csv")
    return T


def step6(task):
    X, y, D = space(task)
    Dn = D.copy()
    np.fill_diagonal(Dn, np.inf)
    nn = np.argsort(Dn, axis=1)[:, :5]
    disagree = (y[nn] != y[:, None]).sum(axis=1)
    m = disagree >= 4
    cols = ["flow_id", "transport", "duration", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down",
            "mean_pkt_size_up", "mean_pkt_size_down"]
    T = X.loc[m, [c for c in cols if c in X.columns]].assign(label=y[m], disagreeing_of_5=disagree[m],
                                                             neighbour_labels=[",".join(y[nn[i]]) for i in np.flatnonzero(m)])
    T.to_csv(OUT / f"step6_label_consistency_{task}.csv", index=False)
    return T


def step7():
    a = oof(T1)
    b = oof(T2)
    a = a[a.seed < 3].reset_index(drop=True)
    assert (a.flow_id.values == b.flow_id.values).all() and (a.fold.values == b.fold.values).all()
    r1, r2 = a.y_true == a.y_pred, b.y_true == b.y_pred
    T = pd.DataFrame({"task2_right_task1_wrong": (~r1 & r2).groupby(a.y_true).sum(),
                      "task1_right_task2_wrong": (r1 & ~r2).groupby(a.y_true).sum(),
                      "both_wrong": (~r1 & ~r2).groupby(a.y_true).sum()})
    T.loc["total"] = T.sum()
    T.to_csv(OUT / f"step7_task1_vs_task2.csv")
    either = a.assign(best=np.where(r1 | r2, a.y_true, a.y_pred))
    return T, macro(a), macro(b), macro(either, "best")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    steps = [int(s) for s in sys.argv[1:]] or list(range(1, 9))
    for task in (T1, T2):
        o = oof(task)
        if 1 in steps or 3 in steps or 8 in steps:
            base, lost, P = step1(task, o)
            print(f"\n[1] {task}: CV macro F1 {base:.4f} ({50*base:.2f} pts; lost {lost:.2f}); top 10 cells:")
            print(P.head(10).to_string(index=False))
        if 2 in steps or 3 in steps or 8 in steps:
            s2, in_mixed, X = step2(task, o)
            print(f"\n[2] {task}: {s2}")
        if 4 in steps or 3 in steps or 8 in steps:
            L = step4(task)
            print(f"\n[4] {task} learning curves (pooled per-class F1, cv_seed 2026):"); print(L.to_string(index=False))
        if 3 in steps or 8 in steps:
            mixed_of = dict(zip(X.flow_id, in_mixed))
            rows = []
            for _, r in P.head(10).iterrows():
                m = (o.y_true == r.true) & (o.y_pred == r.predicted)
                share_irr = float(o[m].flow_id.map(mixed_of).mean())
                sep = separability(task, r.true, r.predicted)
                rise = {c: float(L.loc[L.fraction == 1.0, c].iloc[0] - L.loc[L.fraction == 0.75, c].iloc[0]) for c in (r.true, r.predicted)}
                starved = any(v >= 0.03 for v in rise.values())
                cat = ("irreducible" if share_irr >= 0.5 else "data-starved" if starved else
                       "model-limited" if sep["softvote"] >= 0.90 else "can't tell")
                rows.append({"cell": f"{r.true} -> {r.predicted}", "points": r.points, "share_on_mixed_groups": round(share_irr, 2),
                             "auc_knn": sep["knn"], "auc_softvote": sep["softvote"],
                             "f1_rise_75_to_100": {k: round(v, 3) for k, v in rise.items()}, "category": cat})
            C = pd.DataFrame(rows)
            C.to_csv(OUT / f"step3_categories_{task}.csv", index=False)
            print(f"\n[3] {task} categories:"); print(C.to_string(index=False))
            fix_model = o.copy()
            fx = fix_model.y_pred.copy()
            for _, r in C[C.category == "model-limited"].iterrows():
                a_, b_ = r.cell.split(" -> ")
                m = (o.y_true == a_) & (o.y_pred == b_)
                fx[m] = o.y_true[m]
            ceil_model = macro(fix_model.assign(fx=fx), "fx")
            nonmixed = o.assign(fx=np.where(~o.flow_id.map(mixed_of).astype(bool), o.y_true, o.y_pred))
            ceil_all = macro(nonmixed, "fx")
            print(f"\n[8] {task}: CV now {50*macro(o):.2f} pts; fix model-limited cells -> {50*ceil_model:.2f}; "
                  f"fix every error not on a mixed near-identical flow -> {50*ceil_all:.2f}; floor from step 2: "
                  f"{50 - s2['floor_points_lost']:.2f}")
        if 5 in steps:
            print(f"\n[5] {task} CV reliability:"); print(step5(task, o).to_string())
        if 6 in steps:
            T = step6(task)
            print(f"\n[6] {task}: {len(T)} flows disagree with >= 4 of 5 nearest neighbours; by class: {T.label.value_counts().to_dict()}")
    if 7 in steps:
        T, m1, m2, both = step7()
        print(f"\n[7] seeds 2026-2028: Task 1 CV {m1:.4f}, Task 2 CV {m2:.4f}; oracle 'either right' (not usable) {both:.4f}")
        print(T.to_string())
