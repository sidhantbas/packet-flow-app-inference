"""Experiment 098, stage 1 (diagnostic only): stage-by-stage trace of production Task 1 (089) for every held-out facebook flow
and every flow predicted facebook. The frozen production pipeline is refitted on the original training folds of its champion run
(cv_seed 2026, 5 x 10); the traced final labels must equal the saved out-of-fold predictions.

Usage: python src/exp098_facebook_audit.py      (writes experiments/098_evidence/trace.csv, flows.csv, summary.json)
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, basic_features, load_task
from models import REST_COLS, T1_COLS, TwoClerks, task1_bundle

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
CHAMP = "20261010T004051Z_089_production_check_s2026"
GROUPED = "20261011T230759Z_097_V089_grouped_s2026"
META = ("facebook", "instagram")
STAGES = ["avg", "gate", "whole_meta", "fb_keep", "ig_revert", "verifiers", "h1_final"]


def trace_fold(i, tr, te, X, y):
    m = task1_bundle(i).fit(X.iloc[tr], y[tr])
    Xa = m._with_rest(X.iloc[te])
    sh1 = m.model_
    bv = sh1.model_
    gt = bv.base_
    c = gt.clerks_
    cls = np.asarray(gt.classes_)
    Xb, Xr = Xa[gt.base_cols_], Xa[REST_COLS]
    pw = c.whole_.predict_proba(Xb)
    po = c.opening_.predict_proba(Xb[list(c.OPEN_COLS)])
    pr = gt.rest_.predict_proba(Xr)
    e_whole = np.asarray(c.whole_.predict(Xb), dtype=object)
    e_open, e_rest = cls[po.argmax(1)], cls[pr.argmax(1)]
    p = (pw + po + pr) / 3
    s = {"avg": cls[p.argmax(1)].astype(object)}
    g = gt.gate_.predict_proba(Xb)[:, list(gt.gate_.classes_).index("meta")]
    meta = np.isin(cls, META)
    pm, prr = p[:, meta].sum(1, keepdims=True), p[:, ~meta].sum(1, keepdims=True)
    q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(prr, 1e-12, None))
    pred = cls[q.argmax(1)].astype(object)
    fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
    im = np.isin(pred, META)
    pred[im] = np.where(pw[im, fb] >= pw[im, ig], "facebook", "instagram")
    s["gate"] = pred.copy()
    whole = c.whole_.predict(Xb)
    wm = np.isin(whole, META)
    pred[wm] = whole[wm]
    s["whole_meta"] = pred.copy()
    first = c.whole_.models_[0].predict(Xb[c.whole_.cols_[0]])
    pred[first == "facebook"] = "facebook"
    s["fb_keep"] = pred.copy()
    tc = np.asarray(c.predict(Xb), dtype=object)
    mm = (pred == "instagram") & ~np.isin(tc, META)
    pred[mm] = tc[mm]
    s["ig_revert"] = pred.copy()
    for call, ver in bv.ver_.items():
        k = s["ig_revert"] == call
        if k.any():
            pred[k] = ver.predict(Xa.loc[k, bv.cols_])
    s["verifiers"] = pred.copy()
    keys = sh1._keys(Xa)
    for j, k in enumerate(keys):
        lab = sh1.table_.get(k)
        if lab is not None and lab not in META and pred[j] not in META:
            pred[j] = lab
    s["h1_final"] = pred.copy()
    final = np.asarray(m.predict(X.iloc[te]), dtype=object)
    assert (final == s["h1_final"]).all()
    okeys = X.iloc[te][list(TwoClerks.OPEN_COLS)].astype(str).agg("|".join, axis=1).values
    trk = set(X.iloc[tr][list(TwoClerks.OPEN_COLS)].astype(str).agg("|".join, axis=1).values)
    rows = []
    for j, idx in enumerate(te):
        rows.append({"fold": i, "row": int(idx), "y": y[idx], "e_whole": e_whole[j], "e_open": e_open[j], "e_rest": e_rest[j],
                     "p_whole_fb": round(float(pw[j, fb]), 3), "gate_meta": round(float(g[j]), 3),
                     "pw_fb": float(pw[j, fb]), "pw_ig": float(pw[j, ig]), "po_fb": float(po[j, fb]), "po_ig": float(po[j, ig]),
                     "pr_fb": float(pr[j, fb]), "pr_ig": float(pr[j, ig]),
                     "opening_match": okeys[j] in trk, **{k: v[j] for k, v in s.items()}})
    return rows


def main():
    Xr, y = load_task(T1)
    X = TASK_FEATURES[T1](Xr).reset_index(drop=True)
    yv = np.asarray(y.values, dtype=object)
    sp = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(X, y))
    rows = sum(Parallel(n_jobs=-1)(delayed(trace_fold)(i, tr, te, X, yv) for i, (tr, te) in enumerate(sp)), [])
    T = pd.DataFrame(rows)
    T["flow_id"] = Xr.flow_id.values[T.row]
    oof = pd.read_csv(ROOT / "results" / CHAMP / T1 / "oof.csv")
    assert (oof.flow_id.values == T.flow_id.values).all() and (oof.y_pred.values == T.h1_final.values).all()
    # whole-flow near-twins (036 definition) present in the training fold
    B = np.log1p(basic_features(Xr)[list(T1_COLS)].astype(float).clip(lower=0)).values
    Z = (B - B.mean(0)) / np.where(B.std(0) > 0, B.std(0), 1)
    D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(-1))
    np.fill_diagonal(D, np.inf)
    train_sets = {i: set(tr) for i, (tr, _) in enumerate(sp)}
    T["near_twin"] = [bool((D[r, list(train_sets[f])] <= 0.05).any()) for f, r in zip(T.fold, T.row)]
    T["nn_dist"] = [float(D[r, list(train_sets[f])].min()) for f, r in zip(T.fold, T.row)]
    T["nn_label"] = [yv[list(train_sets[f])[int(np.argmin(D[r, list(train_sets[f])]))]] for f, r in zip(T.fold, T.row)]
    grouped = pd.read_csv(ROOT / "results" / GROUPED / T1 / "oof.csv")
    gacc = grouped.assign(ok=grouped.y_true == grouped.y_pred).groupby("flow_id").ok.mean()
    gpred = grouped.groupby("flow_id").y_pred.agg(lambda s: dict(Counter(s)))
    focus = T[(T.y == "facebook") | (T.h1_final == "facebook")].copy()
    d = ROOT / "experiments/098_evidence"
    d.mkdir(exist_ok=True)
    focus.to_csv(d / "trace.csv", index=False)
    T.to_csv(d / "trace_all.csv", index=False)

    def first_change(r):
        prev = None
        for st in STAGES:
            ok = r[st] == r["y"]
            if prev is not None and ok != prev:
                return f"{st}: {'corrects' if ok else 'introduces error'}"
            prev = ok
        return "none (avg label kept)" if True else ""
    focus["first_change"] = focus.apply(first_change, axis=1)
    wrong = focus[focus.h1_final != focus.y]

    def cat(r):
        experts_right = r.y in (r.e_whole, r.e_open, r.e_rest)
        stage_right = any(r[st] == r.y for st in STAGES[:-1])
        if not experts_right:
            return "C all experts wrong"
        return "A correct evidence lost by decision logic" if stage_right else "B experts disagree, production picks wrong"
    wrong = wrong.assign(category=wrong.apply(cat, axis=1))
    flows = []
    for fid, g in focus.groupby("flow_id"):
        true = g.y.iloc[0]
        fin = Counter(g.h1_final)
        wrong_g = g[g.h1_final != g.y]
        flows.append({"flow_id": fid, "true": true, "held_out": int((T.flow_id == fid).sum()),
                      "in_focus_rows": len(g), "final_preds": dict(fin), "error_rate": round(float((g.h1_final != g.y).mean()), 2),
                      "competing": Counter(wrong_g.h1_final).most_common(1)[0][0] if len(wrong_g) else "-",
                      "opening_match": round(float(g.opening_match.mean()), 2), "near_twin_in_train": round(float(g.near_twin.mean()), 2),
                      "nn_label": Counter(g.nn_label).most_common(1)[0][0], "nn_dist_median": round(float(g.nn_dist.median()), 3),
                      "whole": dict(Counter(g.e_whole)), "opening": dict(Counter(g.e_open)), "rest": dict(Counter(g.e_rest)),
                      **{f"after_{st}": Counter(g[st]).most_common(1)[0][0] for st in STAGES},
                      "first_change": Counter(g.first_change).most_common(2),
                      "expert_right_when_wrong": int(sum(r.y in (r.e_whole, r.e_open, r.e_rest) for _, r in wrong_g.iterrows())),
                      "grouped_acc": round(float(gacc.get(fid, np.nan)), 2), "grouped_preds": gpred.get(fid, {})})
    F = pd.DataFrame(flows)
    F.to_csv(d / "flows.csv", index=False)
    fbt = focus[focus.y == "facebook"]
    fp = focus[(focus.y != "facebook") & (focus.h1_final == "facebook")]
    summary = {
        "trace_matches_saved_oof": True,
        "facebook_held_out_predictions": int(len(fbt)), "facebook_correct": int((fbt.h1_final == "facebook").sum()),
        "facebook_errors_by_category": dict(Counter(wrong[wrong.y == "facebook"].category)),
        "facebook_errors_first_change": dict(Counter(wrong[wrong.y == "facebook"].first_change)),
        "false_positive_predictions": int(len(fp)), "false_positive_by_true": dict(Counter(fp.y)),
        "false_positive_first_change": dict(Counter(fp.first_change)),
        "false_positives_by_category": dict(Counter(wrong[wrong.y != "facebook"].category)),
        "facebook_expert_right_rate": {e: round(float((fbt[e] == "facebook").mean()), 3) for e in ("e_whole", "e_open", "e_rest")},
        "facebook_stage_right_rate": {st: round(float((fbt[st] == "facebook").mean()), 3) for st in STAGES},
        "facebook_acc_by_near_twin": {str(k): round(float((g.h1_final == "facebook").mean()), 3) for k, g in fbt.groupby("near_twin")},
        "facebook_acc_by_opening_match": {str(k): round(float((g.h1_final == "facebook").mean()), 3) for k, g in fbt.groupby("opening_match")}}
    (d / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    pd.set_option("display.width", 250)
    print(F[["flow_id", "true", "final_preds", "error_rate", "competing", "opening_match", "near_twin_in_train", "nn_label",
             "whole", "opening", "rest", "after_gate", "after_fb_keep", "after_ig_revert", "after_verifiers", "after_h1_final",
             "first_change", "expert_right_when_wrong", "grouped_acc"]].to_string())


if __name__ == "__main__":
    main()
