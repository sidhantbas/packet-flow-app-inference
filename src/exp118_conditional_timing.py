"""Experiment 118 (hypothesis H-T): opening timing in Task 2's facebook/instagram specialist, production routing unchanged
(protocol: experiments/118_conditional_timing.md). Reads only Task 2 files.

Usage (from the repository root):
  .venv/bin/python src/exp118_conditional_timing.py --smoke
  .venv/bin/python src/exp118_conditional_timing.py --all          # end-to-end P2 and T, 3 fold families, seeds 2171-2175
  .venv/bin/python src/exp118_conditional_timing.py --pair         # descriptive and pair-level measurements
  .venv/bin/python src/exp118_conditional_timing.py --analyse
  .venv/bin/python src/exp118_conditional_timing.py --test-effect
Runs go to results/<stamp>_118_<arm>_<family>_s<seed>/; other evidence to experiments/118_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedGroupKFold

from cv import TIMING, TASK_FEATURES, basic_features, evaluate, load_task, no_timing_features
from models import PairSpecialist, SoftVote, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T2 = "task2_realtime_prefix5"
SEEDS = (2171, 2172, 2173, 2174, 2175)
FAMILIES = ("ordinary", "exact", "session")
SESSION_GAP = 30.0
META = ("facebook", "instagram")
APPS = ("facebook", "google", "instagram", "mozilla", "x", "youtube")
EVIDENCE = ROOT / "experiments/118_evidence"


def _data():
    Xr, y = load_task(T2)
    return Xr.reset_index(drop=True), np.asarray(y.values, dtype=object)


BASE12 = list(no_timing_features(_data()[0]).columns)


def task2_timing_specialist(seed):
    return PairSpecialist(base_cols=BASE12, seed=seed, spec_class_weight=None, spec_all_cols=True, pair=META)


ARM = {"P2": (task2_model, TASK_FEATURES[T2]), "T": (task2_timing_specialist, basic_features)}


def exact_groups(Xr):
    k = no_timing_features(Xr).reset_index(drop=True).astype(str).agg("|".join, axis=1)
    return pd.factorize(k)[0]


def session_groups(Xr):
    s = Xr.start_rel.to_numpy()
    o = np.argsort(s, kind="stable")
    g = np.zeros(len(s), int)
    gid = 0
    for i in range(1, len(o)):
        if s[o[i]] - s[o[i - 1]] > SESSION_GAP:
            gid += 1
        g[o[i]] = gid
    return g


def family_groups(family, Xr):
    return {"ordinary": None, "exact": exact_groups(Xr), "session": session_groups(Xr)}[family]


def make_splits(family, seed, y, groups, n_repeats=10):
    if family == "ordinary":
        return list(RepeatedStratifiedKFold(n_splits=5, n_repeats=n_repeats, random_state=seed).split(np.zeros(len(y)), y))
    out = []
    for r in range(n_repeats):
        out += list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed + r).split(np.zeros(len(y)), y, groups))
    return out


def run_id(arm, family, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_118_{arm}_{family}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, family, seed):
    Xr, y = _data()
    f, feats = ARM[arm]
    sp = make_splits(family, seed, y, family_groups(family, Xr))
    t0 = datetime.now(timezone.utc)
    res = {T2: evaluate(T2, feats, f, splits=sp, cv_seed=seed, split_name=f"118 {family} folds (5 x 10)")}
    rid = record_run("118", f"{arm}_{family}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P2" else run_id("P2", family, seed),
                     question=f"Task 2 118 {arm} (H-T, timing in the facebook/instagram specialist) on {family} folds, cv_seed {seed}",
                     config={"arm": arm, "family": family, "cv_seed": seed, "session_gap_s": SESSION_GAP}, started=t0)
    print(rid, flush=True)


def _pair_fold(i, tr, te, X, ym):
    m = SoftVote(seed=i, class_weight=None).fit(X.iloc[tr], ym[tr])
    return te, m.predict_proba(X.iloc[te])[:, list(m.classes_).index("facebook")]


def pair_level():
    Xr, y = _data()
    meta = np.isin(y, META)
    Xm, ym = Xr[meta].reset_index(drop=True), y[meta]
    views = {"P2 (12 columns)": no_timing_features(Xm).reset_index(drop=True), "T (12 + timing)": basic_features(Xm).reset_index(drop=True)}
    desc = {c: round(float(roc_auc_score(ym == "facebook", basic_features(Xm)[c])), 3) for c in TIMING}
    k = no_timing_features(Xm).reset_index(drop=True).astype(str).agg("|".join, axis=1)
    tied = k.isin([v for v, d in pd.DataFrame({"k": k, "y": ym}).groupby("k") if {"facebook", "instagram"} <= set(d.y)])
    tie_auc = {c: round(float(roc_auc_score(ym[tied] == "facebook", basic_features(Xm)[c][tied.values])), 3) for c in TIMING}
    out = {"descriptive_auc_30_meta_flows": desc, "descriptive_auc_10_tied_flows": tie_auc, "pair_level": {}}
    for family in FAMILIES:
        groups = family_groups(family, Xm)
        res = {}
        for name, X in views.items():
            aucs, f1s = [], []
            for s in SEEDS:
                sp = make_splits(family, s, ym, groups)
                outs = Parallel(n_jobs=-1)(delayed(_pair_fold)(i, tr, te, X, ym) for i, (tr, te) in enumerate(sp))
                P = np.zeros((10, len(ym)))
                for i, (te, p) in enumerate(outs):
                    P[i // 5, te] = p
                for p in P:
                    aucs.append(roc_auc_score(ym == "facebook", p))
                    f1s.append(f1_score(ym, np.where(p >= 0.5, "facebook", "instagram"), labels=list(META), average="macro"))
            res[name] = {"auc_mean": round(float(np.mean(aucs)), 3), "auc_sd": round(float(np.std(aucs, ddof=1)), 3),
                         "two_app_macro_f1_mean": round(float(np.mean(f1s)), 3)}
        res["T_minus_P2_auc"] = round(res["T (12 + timing)"]["auc_mean"] - res["P2 (12 columns)"]["auc_mean"], 3)
        out["pair_level"][family] = res
        print(family, res)
    print("descriptive AUC (30 Meta flows):", desc)
    print("descriptive AUC (10 tied flows):", tie_auc)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "pair_level.json").write_text(json.dumps(out, indent=2) + "\n")


def smoke():
    Xr, y = _data()
    for family in ("exact", "session"):
        g = family_groups(family, Xr)
        leak = sum(len(set(g[tr]) & set(g[te])) for s in SEEDS for tr, te in make_splits(family, s, y, g))
        print(f"{family}: {len(set(g))} groups; groups in both training and validation over 250 folds: {leak}")
    tr, te = make_splits("ordinary", SEEDS[0], y, None)[0]
    X12, X17 = TASK_FEATURES[T2](Xr), basic_features(Xr)
    a = np.asarray(task2_model(0).fit(X12.iloc[tr], y[tr]).predict(X12.iloc[te]), dtype=object)
    m = task2_timing_specialist(0).fit(X17.iloc[tr], y[tr])
    b = np.asarray(m.predict(X17.iloc[te]), dtype=object)
    base_meta = np.isin(np.asarray(m.base_.predict(X17.iloc[te][BASE12]), dtype=object), META)
    print("T's base uses exactly the 12 production columns:", m.base_cols_ == BASE12, "| specialist columns:", len(m.spec_cols_))
    print("T equals P2 wherever the routing does not call Meta:", bool((a[~base_meta] == b[~base_meta]).all()),
          f"| Meta-routed {int(base_meta.sum())} | changed {int((a != b).sum())} of {len(te)}")


def analyse():
    Xr, y = _data()
    gmap = {"exact": dict(zip(Xr.flow_id, exact_groups(Xr))), "session": dict(zip(Xr.flow_id, session_groups(Xr)))}
    gmap["ordinary"] = gmap["exact"]
    out = {"per_seed": {}, "summary": {}}
    for family in FAMILIES:
        deltas = []
        net_g, net_f = Counter(), Counter()
        for s in SEEDS:
            rp, rt = run_id("P2", family, s), run_id("T", family, s)
            mp, mt = (json.loads((ROOT / "results" / r / "manifest.json").read_text()) for r in (rp, rt))
            assert mp["tasks"][T2]["fold_signature"] == mt["tasks"][T2]["fold_signature"], "folds differ"
            assert all(k.startswith(T2 + "/") for k in mt["tasks"][T2]["data_sha256"]), "non-Task-2 file read"
            comp = json.loads((ROOT / "results" / rt / "comparison.json").read_text())[T2]
            op, ot = (pd.read_csv(ROOT / "results" / r / T2 / "oof.csv") for r in (rp, rt))
            fp, ft = (pd.read_csv(ROOT / "results" / r / T2 / "folds.csv").macro_f1.mean() for r in (rp, rt))
            pcs = {}
            for name, o in (("P2", op), ("T", ot)):
                p_, r_, f_, _ = precision_recall_fscore_support(o.y_true, o.y_pred, labels=list(APPS), zero_division=0)
                pcs[name] = {c: round(float(v), 3) for c, v in zip(APPS, f_)}
            ch = op.y_pred.values != ot.y_pred.values
            for f_id, t, a, b in zip(ot.flow_id[ch], ot.y_true[ch], op.y_pred[ch], ot.y_pred[ch]):
                d = int(b == t) - int(a == t)
                net_g[gmap[family][f_id]] += d
                net_f[f_id] += d
            deltas.append(ft - fp)
            out["per_seed"][f"{family}_s{s}"] = {"P2": round(float(fp), 4), "T": round(float(ft), 4), "delta": round(float(ft - fp), 4),
                                                 "verdict": comp["verdict"], "wins_losses_ties": [comp["wins"], comp["losses"], comp["ties"]],
                                                 "f1": pcs, "changed_predictions": int(ch.sum()), "changed_distinct_flows": int(ot.flow_id[ch].nunique())}
            r = out["per_seed"][f"{family}_s{s}"]
            print(f"{family:8s} s{s}: P2 {fp:.4f} T {ft:.4f} Δ {ft - fp:+.4f} {comp['verdict']:12s} ({comp['wins']}/{comp['losses']}/{comp['ties']}) | "
                  f"fb {pcs['P2']['facebook']:.2f}->{pcs['T']['facebook']:.2f} ig {pcs['P2']['instagram']:.2f}->{pcs['T']['instagram']:.2f} "
                  f"google {pcs['P2']['google']:.2f}->{pcs['T']['google']:.2f} | changed {r['changed_predictions']} ({r['changed_distinct_flows']} flows)")
        tot = sum(net_g.values())
        out["summary"][family] = {"mean_delta": round(float(np.mean(deltas)), 4), "sd_delta": round(float(np.std(deltas, ddof=1)), 4),
                                  "positive_seeds": int(sum(d > 0 for d in deltas)),
                                  "better_seeds": sum(out["per_seed"][f"{family}_s{s}"]["verdict"] == "BETTER" for s in SEEDS),
                                  "worse_seeds": sum(out["per_seed"][f"{family}_s{s}"]["verdict"] == "WORSE" for s in SEEDS),
                                  "pooled_net_predictions": tot, "flows_net_improved": sum(v > 0 for v in net_f.values()),
                                  "flows_net_worsened": sum(v < 0 for v in net_f.values()),
                                  "largest_group_share": round(max(net_g.values()) / tot, 3) if tot > 0 else None}
        print(family, out["summary"][family])
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "end_to_end.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    Xr, y = _data()
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T2]
    Xt = load_test(T2)
    ids = list(Xt.flow_id)
    p = np.asarray(task2_timing_specialist(0).fit(basic_features(Xr), y).predict(basic_features(Xt)), dtype=object)
    ch = {ids[i]: f"{sub[ids[i]]} -> {p[i]}" for i in range(len(ids)) if p[i] != sub[ids[i]]}
    print("T changes", len(ch), "Task 2 test predictions:", ch)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps({"T_changes_vs_submitted_task2": ch}, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag in ("smoke", "all", "pair", "analyse", "test-effect"):
        ap.add_argument(f"--{flag}", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        smoke()
    elif a.pair:
        pair_level()
    elif a.analyse:
        analyse()
    elif a.test_effect:
        test_effect()
    elif a.all:
        for family in FAMILIES:
            for s in SEEDS:
                run("P2", family, s)
                run("T", family, s)
    else:
        ap.error("choose an action")


if __name__ == "__main__":
    main()
