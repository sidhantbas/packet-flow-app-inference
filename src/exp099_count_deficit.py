"""Experiment 099 (measurement): class-count deficits on the test set and a count-aware instagram rescue
(protocol: experiments/099_class_count_deficit.md, frozen first). No test labels, no metadata label_counts.

Usage: .venv/bin/python src/exp099_count_deficit.py     (writes experiments/099_evidence/)
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import DATA, TASK_FEATURES, load_task
from make_submission import load_test
from models import REST_COLS, task1_bundle, task2_model

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments/099_evidence"
T1, T2 = "task1_static", "task2_realtime_prefix5"
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
IG = "instagram"


def splits(task):
    X, y = load_task(task)
    return list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(X, y))


# ---------- probabilities ----------
def t1_test_scores():
    """Fit production Task 1 on all labelled flows; instagram score = mean of the three experts' instagram probabilities."""
    Xr, y = load_task(T1)
    X = TASK_FEATURES[T1](Xr)
    Xt_raw = load_test(T1)
    Xt = TASK_FEATURES[T1](Xt_raw)
    m = task1_bundle(0).fit(X, np.asarray(y.values, dtype=object))
    Xa = m._with_rest(Xt)
    gt = m.model_.model_.base_
    c = gt.clerks_
    cls = list(gt.classes_)
    Xb = Xa[gt.base_cols_]
    pw = c.whole_.predict_proba(Xb)
    po = c.opening_.predict_proba(Xb[list(c.OPEN_COLS)])
    pr = gt.rest_.predict_proba(Xa[REST_COLS])
    p = (pw + po + pr) / 3
    pred = np.asarray(m.predict(Xt), dtype=object)
    return pd.DataFrame({"flow_id": Xt_raw.flow_id.values, "pred": pred, "s_ig": p[:, cls.index(IG)],
                         "s_fb": p[:, cls.index("facebook")], **{f"p_{k}": p[:, cls.index(k)] for k in LABS}})


def t2_fold(i, tr, te, X, y):
    m = task2_model(i).fit(X.iloc[tr], y[tr])
    pr = m.base_.predict_proba(X.iloc[te][m.base_cols_])
    return te, np.asarray(m.predict(X.iloc[te]), dtype=object), pr[:, list(m.base_.classes_).index(IG)]


def t2_oof():
    Xr, y = load_task(T2)
    X = TASK_FEATURES[T2](Xr)
    yv = np.asarray(y.values, dtype=object)
    sp = splits(T2)
    R = Parallel(n_jobs=-1)(delayed(t2_fold)(i, tr, te, X, yv) for i, (tr, te) in enumerate(sp))
    rows = []
    for i, ((tr, te), (_, pred, s)) in enumerate(zip(sp, R)):
        for j, r in enumerate(te):
            rows.append({"fold": i, "row": int(r), "y": yv[r], "pred": pred[j], "s_ig": float(s[j])})
    T = pd.DataFrame(rows)
    champ = pd.read_csv(ROOT / "results/20260930T173836Z_014_fi_same_nocw" / T2 / "oof.csv")
    assert (champ.y_pred.values == T.pred.values).all(), "refit does not reproduce the Task 2 champion"
    return T


def t2_test_scores():
    Xr, y = load_task(T2)
    X = TASK_FEATURES[T2](Xr)
    Xt_raw = load_test(T2)
    Xt = TASK_FEATURES[T2](Xt_raw)
    m = task2_model(0).fit(X, np.asarray(y.values, dtype=object))
    pr = m.base_.predict_proba(Xt[m.base_cols_])
    return pd.DataFrame({"flow_id": Xt_raw.flow_id.values, "pred": np.asarray(m.predict(Xt), dtype=object),
                         "s_ig": pr[:, list(m.base_.classes_).index(IG)]})


# ---------- analyses ----------
def analyse(task, T, yv, sp):
    """T: held-out rows (fold, row, y, pred, s_ig) in fold order."""
    res = {}
    # B: per-fold count deviations scaled to 81
    dev = {c: [] for c in LABS}
    for i, (tr, te) in enumerate(sp):
        g = T[T.fold == i]
        for c in LABS:
            dev[c].append(((g.pred == c).sum() - (g.y == c).sum()) * 81 / len(g))
    res["B_count_deviation_per_81"] = {c: {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v, ddof=1)), 2),
                                           "p5": round(float(np.percentile(v, 5)), 2), "p95": round(float(np.percentile(v, 95)), 2)}
                                       for c, v in dev.items()}
    res["B_folds_instagram_deficit_ge_3_per_81"] = int(sum(d <= -3 for d in dev[IG]))
    res["B_folds_instagram_deficit_ge_1_per_81"] = int(sum(d <= -1 for d in dev[IG]))
    # C: calibration of s_ig among flows not called instagram
    top = {1: [], 2: [], 3: []}
    for i in range(len(sp)):
        g = T[(T.fold == i) & (T.pred != IG)].sort_values("s_ig", ascending=False)
        for k in top:
            top[k] += list(g.y.values[:k] == IG)
    res["C_top_k_instagram_rate"] = {k: round(float(np.mean(v)), 3) for k, v in top.items()}
    nn = T[T.pred != IG]
    bins = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.01]
    res["C_bins"] = {f"{lo:.2f}-{hi:.2f}": {"n": int(((nn.s_ig >= lo) & (nn.s_ig < hi)).sum()),
                                            "instagram_rate": round(float((nn.y[(nn.s_ig >= lo) & (nn.s_ig < hi)] == IG).mean()), 3)
                                            if ((nn.s_ig >= lo) & (nn.s_ig < hi)).any() else None}
                     for lo, hi in zip(bins[:-1], bins[1:])}
    # D: count-aware rescue
    for name in ("rule", "oracle"):
        d_macro, flips, correct, k_hist = [], 0, 0, Counter()
        new_pred = T.pred.values.copy()
        for i, (tr, te) in enumerate(sp):
            idx = np.flatnonzero(T.fold.values == i)
            g = T.iloc[idx]
            n_pred = int((g.pred == IG).sum())
            E = int(round(len(g) * float(np.mean(yv[tr] == IG)))) if name == "rule" else int((g.y == IG).sum())
            k = max(0, E - n_pred)
            k_hist[k] += 1
            cand = g[g.pred != IG].sort_values("s_ig", ascending=False).index[:k]
            p_new = g.pred.copy()
            p_new.loc[cand] = IG
            flips += len(cand)
            correct += int((g.y.loc[cand] == IG).sum())
            new_pred[idx] = p_new.values
            d_macro.append(f1_score(g.y, p_new, average="macro") - f1_score(g.y, g.pred, average="macro"))
        d = np.array(d_macro)
        y_all = T.y.values

        def pr_rc(p):
            tp = ((p == IG) & (y_all == IG)).sum()
            return round(float(tp / max((p == IG).sum(), 1)), 3), round(float(tp / (y_all == IG).sum()), 3)
        res[f"D_{name}"] = {"k_per_fold": dict(sorted(k_hist.items())), "flips": flips, "flips_correct": correct,
                            "flip_precision": round(correct / flips, 3) if flips else None,
                            "delta_macro_mean": round(float(d.mean()), 4), "delta_macro_sd": round(float(d.std(ddof=1)), 4),
                            "wins": int((d > 1e-12).sum()), "losses": int((d < -1e-12).sum()), "ties": int((np.abs(d) <= 1e-12).sum()),
                            "instagram_precision_recall_before": pr_rc(T.pred.values), "instagram_precision_recall_after": pr_rc(new_pred)}
    return res


def main():
    OUT.mkdir(exist_ok=True)
    out = {}
    # A: expected vs predicted counts
    val = {t: pd.read_csv(DATA / t / "validation_labels.csv").app.value_counts() for t in (T1, T2)}
    tv = pd.concat([pd.read_csv(DATA / T1 / f"{s}_labels.csv") for s in ("train", "validation")]).app.value_counts()
    cand = json.loads((ROOT / "submissions/final-2026-10-12-089-014/submission.json").read_text())
    out["A_counts"] = {c: {"expected_from_validation": round(float(val[T1].get(c, 0) * 81 / 83), 1),
                           "expected_from_training_share": round(float(tv.get(c, 0) * 81 / 330), 1),
                           "task1_predicted": sum(v == c for v in cand[T1].values()),
                           "task2_predicted": sum(v == c for v in cand[T2].values())} for c in LABS}
    # Task 1
    Xr, y = load_task(T1)
    yv = np.asarray(y.values, dtype=object)
    tr1 = pd.read_csv(ROOT / "experiments/098_evidence/trace_all.csv")
    T = pd.DataFrame({"fold": tr1.fold, "row": tr1.row, "y": tr1.y, "pred": tr1.h1_final,
                      "s_ig": (tr1.pw_ig + tr1.po_ig + tr1.pr_ig) / 3})
    out["task1"] = analyse(T1, T, yv, splits(T1))
    # Task 2
    Xr2, y2 = load_task(T2)
    out["task2"] = analyse(T2, t2_oof(), np.asarray(y2.values, dtype=object), splits(T2))
    # E: test application
    share = float((tv.get(IG, 0)) / 330)
    E = int(round(81 * share))
    for task, S in ((T1, t1_test_scores()), (T2, t2_test_scores())):
        assert (S.pred.values == np.array([cand[task][f] for f in S.flow_id])).all(), task
        k = max(0, E - int((S.pred == IG).sum()))
        top = S[S.pred != IG].sort_values("s_ig", ascending=False)
        out[f"E_{task}"] = {"E": E, "predicted_instagram": int((S.pred == IG).sum()), "k": k,
                            "would_relabel": top.head(k)[["flow_id", "pred", "s_ig"]].round(3).to_dict(orient="records"),
                            "next_candidates": top.iloc[k:k + 4][["flow_id", "pred", "s_ig"]].round(3).to_dict(orient="records"),
                            "current_instagram_calls": S[S.pred == IG][["flow_id", "s_ig"]].round(3).to_dict(orient="records")}
        S.to_csv(OUT / f"test_scores_{task}.csv", index=False)
    (OUT / "analysis.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
