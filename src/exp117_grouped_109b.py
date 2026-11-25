"""Experiment 117: 109 B vs production 014 (Task 2) on grouped folds built from Task 2 openings only
(protocol: experiments/117_grouped_109b.md). Reads only Task 2 files; no test data.

Usage (from the repository root):
  .venv/bin/python src/exp117_grouped_109b.py --smoke
  .venv/bin/python src/exp117_grouped_109b.py --all          # P2 and B, exact and near groupings, seeds 2166-2170
  .venv/bin/python src/exp117_grouped_109b.py --analyse
Runs go to results/<stamp>_117_<arm>_<grouping>_s<seed>/; other evidence to experiments/117_evidence/.
"""
import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold

from cv import TASK_FEATURES, evaluate, load_task
from exp109_task2_first_packet_specialist import SELECT_LOG, task2_candidates, task2_select_specialist
from models import task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T2 = "task2_realtime_prefix5"
SEEDS = (2166, 2167, 2168, 2169, 2170)
GROUPINGS = {"exact": 0.0, "near": 0.05}
APPS = ("facebook", "google", "instagram", "mozilla", "x", "youtube")
EVIDENCE = ROOT / "experiments/117_evidence"
ARM = {"P2": (task2_model, TASK_FEATURES[T2]), "B": (task2_select_specialist, task2_candidates)}


def _labelled():
    Xr, y = load_task(T2)
    return Xr, np.asarray(y.values, dtype=object)


def groups(threshold):
    """Connected components of labelled flows whose 12 Task 2 production columns (log1p, standardised over the 330 labelled
    flows) lie within `threshold` (Euclidean) of each other."""
    Xr, _ = _labelled()
    B = np.log1p(TASK_FEATURES[T2](Xr).astype(float).clip(lower=0)).values
    Z = (B - B.mean(0)) / np.where(B.std(0) > 0, B.std(0), 1)
    D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(-1))
    return connected_components(D <= threshold, directed=False)[1]


def grouped_splits(grouping, seed, n_repeats=10):
    g = groups(GROUPINGS[grouping])
    _, y = _labelled()
    out = []
    for r in range(n_repeats):
        out += list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed + r).split(np.zeros(len(y)), y, g))
    return out


def run_id(arm, grouping, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_117_{arm}_{grouping}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, grouping, seed):
    f, feats = ARM[arm]
    sp = grouped_splits(grouping, seed)
    t0 = datetime.now(timezone.utc)
    res = {T2: evaluate(T2, feats, f, splits=sp, cv_seed=seed,
                        split_name=f"grouped-{grouping} (Task 2 openings, threshold {GROUPINGS[grouping]}) StratifiedGroupKFold(5) x 10")}
    rid = record_run("117", f"{arm}_{grouping}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P2" else run_id("P2", grouping, seed),
                     question=f"Task 2 117 {arm} on grouped-{grouping} folds, never-used cv_seed {seed}",
                     config={"arm": arm, "grouping": grouping, "threshold": GROUPINGS[grouping], "cv_seed": seed}, started=t0)
    print(rid, flush=True)


def integrity_folds():
    out = {}
    _, y = _labelled()
    for grouping, thr in GROUPINGS.items():
        g = groups(thr)
        leaks, tr_fb, te_fb, te_ig, sizes = 0, [], [], [], []
        for s in SEEDS:
            for tr, te in grouped_splits(grouping, s):
                leaks += len(set(g[tr]) & set(g[te]))
                tr_fb.append(int((y[tr] == "facebook").sum()))
                te_fb.append(int((y[te] == "facebook").sum()))
                te_ig.append(int((y[te] == "instagram").sum()))
                sizes.append(len(te))
        cs = Counter(g)
        out[grouping] = {"groups": len(cs), "singletons": sum(v == 1 for v in cs.values()),
                         "largest": [n for _, n in cs.most_common(5)],
                         "largest_composition": {str(n): dict(Counter(y[g == k])) for k, n in cs.most_common(3)},
                         "mixed_label_groups": sum(len(set(y[g == k])) > 1 for k in cs),
                         "groups_with_facebook": len(set(g[y == "facebook"])), "groups_with_instagram": len(set(g[y == "instagram"])),
                         "groups_in_train_and_validation": leaks,
                         "facebook_train_min_max": [min(tr_fb), max(tr_fb)], "facebook_validation_min_max": [min(te_fb), max(te_fb)],
                         "instagram_validation_min_max": [min(te_ig), max(te_ig)], "validation_size_min_max": [min(sizes), max(sizes)]}
    return out


def smoke():
    print(json.dumps(integrity_folds(), indent=1))
    Xr, y = _labelled()
    X = TASK_FEATURES[T2](Xr)
    tr, te = grouped_splits("exact", SEEDS[0])[0]
    same = all((np.array_equal(a1, b1) and np.array_equal(a2, b2))
               for (a1, a2), (b1, b2) in zip(grouped_splits("exact", SEEDS[0]), grouped_splits("exact", SEEDS[0])))
    print("grouped split lists are deterministic (identical for both arms):", same)
    print("P2 arm factory is production models.task2_model:", ARM["P2"][0] is task2_model)
    a = np.asarray(task2_model(0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), dtype=object)
    Xc = task2_candidates(Xr)
    m = task2_select_specialist(0).fit(Xc.iloc[tr], y[tr])
    b = np.asarray(m.predict(Xc.iloc[te]), dtype=object)
    print(f"B on grouped fold 0: changed vs P2 {int((a != b).sum())} of {len(te)}; specialist columns {m.spec_cols_}")


def _metrics(o):
    p, r, f, _ = precision_recall_fscore_support(o.y_true, o.y_pred, labels=list(APPS), zero_division=0)
    pc = {c: {"precision": round(float(a), 3), "recall": round(float(b), 3), "f1": round(float(cc), 3)} for c, a, b, cc in zip(APPS, p, r, f)}
    conf = {f"{t}->{q}": round(int(((o.y_true == t) & (o.y_pred == q)).sum()) / 10, 1)
            for t in ("facebook", "instagram", "google") for q in ("facebook", "instagram", "google") if t != q}
    wrong = o[o.y_true != o.y_pred]
    share = o.assign(w=o.y_true != o.y_pred).groupby("flow_id").w.mean()
    return pc, conf, {"distinct_flows_wrong_at_least_once": int(wrong.flow_id.nunique()),
                      "distinct_flows_wrong_in_most_repeats": int((share > 0.5).sum())}


def analyse():
    Xr, y = _labelled()
    gid = {}
    for grouping, thr in GROUPINGS.items():
        gid[grouping] = dict(zip(Xr.flow_id, groups(thr)))
    out = {"integrity": integrity_folds(), "per_seed": {}, "summary": {}}
    for grouping in GROUPINGS:
        deltas = []
        for s in SEEDS:
            rp, rb = run_id("P2", grouping, s), run_id("B", grouping, s)
            mp = json.loads((ROOT / "results" / rp / "manifest.json").read_text())
            mb = json.loads((ROOT / "results" / rb / "manifest.json").read_text())
            assert mp["tasks"][T2]["fold_signature"] == mb["tasks"][T2]["fold_signature"], "folds differ between arms"
            assert all(k.startswith(T2 + "/") for k in mb["tasks"][T2]["data_sha256"]), "a non-Task-2 file was read"
            comp = json.loads((ROOT / "results" / rb / "comparison.json").read_text())[T2]
            op = pd.read_csv(ROOT / "results" / rp / T2 / "oof.csv")
            ob = pd.read_csv(ROOT / "results" / rb / T2 / "oof.csv")
            fp = pd.read_csv(ROOT / "results" / rp / T2 / "folds.csv").macro_f1.mean()
            fb = pd.read_csv(ROOT / "results" / rb / T2 / "folds.csv").macro_f1.mean()
            ch = op.y_pred.values != ob.y_pred.values
            fixed = ch & (ob.y_pred.values == ob.y_true.values)
            broken = ch & (op.y_pred.values == op.y_true.values)
            net = Counter()
            for f_, fx, bk in zip(ob.flow_id.values[ch], fixed[ch], broken[ch]):
                net[gid[grouping][f_]] += int(fx) - int(bk)
            tot = sum(net.values())
            top = max(net.values()) if net else 0
            pcp, cfp, wp = _metrics(op)
            pcb, cfb, wb = _metrics(ob)
            deltas.append(fb - fp)
            out["per_seed"][f"{grouping}_s{s}"] = {
                "macro_f1": {"P2": round(float(fp), 4), "B": round(float(fb), 4)}, "delta": round(float(fb - fp), 4),
                "wins_losses_ties": [comp["wins"], comp["losses"], comp["ties"]], "verdict": comp["verdict"],
                "per_class": {"P2": pcp, "B": pcb}, "confusions_per_repeat": {"P2": cfp, "B": cfb}, "distinct_flows_wrong": {"P2": wp, "B": wb},
                "changed_predictions": int(ch.sum()), "fixed": int(fixed.sum()), "broken": int(broken.sum()),
                "changed_distinct_flows": int(ob.flow_id[ch].nunique()), "changed_distinct_groups": len(net),
                "net_fixed_minus_broken": tot, "largest_single_group_net": top,
                "largest_group_share_of_net_gain": round(top / tot, 3) if tot > 0 else None}
            r = out["per_seed"][f"{grouping}_s{s}"]
            print(f"{grouping:5s} s{s}: P2 {fp:.4f} B {fb:.4f} Δ {fb - fp:+.4f} {comp['verdict']:12s} W/L/T {comp['wins']}/{comp['losses']}/{comp['ties']} | "
                  f"fb F1 {pcp['facebook']['f1']:.2f}->{pcb['facebook']['f1']:.2f} ig {pcp['instagram']['f1']:.2f}->{pcb['instagram']['f1']:.2f} "
                  f"google {pcp['google']['f1']:.2f}->{pcb['google']['f1']:.2f} | changed {r['changed_predictions']} ({r['changed_distinct_flows']} flows, "
                  f"{r['changed_distinct_groups']} groups), net {tot}, top group share {r['largest_group_share_of_net_gain']}")
        out["summary"][grouping] = {"mean_delta": round(float(np.mean(deltas)), 4), "sd_delta": round(float(np.std(deltas, ddof=1)), 4),
                                    "positive_seeds": int(sum(d > 0 for d in deltas)),
                                    "better_seeds": sum(out["per_seed"][f"{grouping}_s{s}"]["verdict"] == "BETTER" for s in SEEDS),
                                    "worse_seeds": sum(out["per_seed"][f"{grouping}_s{s}"]["verdict"] == "WORSE" for s in SEEDS)}
        print(grouping, out["summary"][grouping])
    out["ordinary_folds_109"] = json.loads((ROOT / "experiments/109_evidence/analysis.json").read_text())["vs_P"]["B"]["per_seed"]
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "results.json").write_text(json.dumps(out, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        smoke()
    elif a.analyse:
        analyse()
    elif a.all:
        EVIDENCE.mkdir(exist_ok=True)
        os.environ[SELECT_LOG] = str(EVIDENCE / "selected_columns.jsonl")  # B's per-fold selections, set before workers start
        for grouping in GROUPINGS:
            for s in SEEDS:
                run("P2", grouping, s)
                run("B", grouping, s)
    else:
        ap.error("use --smoke, --all or --analyse")


if __name__ == "__main__":
    main()
