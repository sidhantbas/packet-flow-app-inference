"""Experiment 115 (measurement only): identifiability of facebook vs instagram from per-flow statistics, and benchmark artefacts
(protocol: experiments/115_identifiability_and_artefacts.md). No test labels, no metadata counts, no identifiers.

Usage (from the repository root):
  .venv/bin/python src/exp115_identifiability_and_artefacts.py
Writes experiments/115_evidence/measurements.json.
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from cv import TASK_FEATURES, load_task
from make_submission import load_test
from models import T1_COLS

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
META = ("facebook", "instagram")
EVIDENCE = ROOT / "experiments/115_evidence"
LN2 = np.log(2)


def logstd(X):
    return StandardScaler().fit_transform(np.log1p(np.clip(np.asarray(X, float), 0, None)))


def knn_loo_error(X, y, k):
    pred = cross_val_predict(KNeighborsClassifier(n_neighbors=k), logstd(X), y, cv=LeaveOneOut())
    return float((pred != y).mean())


def cover_hart(r1, m):
    """Asymptotic bounds on the Bayes error from the 1-NN error r1 with m classes."""
    lower = (m - 1) / m * (1 - np.sqrt(max(0.0, 1 - m / (m - 1) * r1)))
    return float(lower), float(r1)


def b1_b2(X1, X2, y):
    out = {"B1": {}, "B2": {}}
    meta = np.isin(y, META)
    views = {"fb_vs_ig / Task 1 (34 columns)": (X1[meta], y[meta], 2),
             "fb_vs_ig / Task 1 whole-flow (17 columns)": (X1[meta][list(T1_COLS)], y[meta], 2),
             "fb_vs_ig / Task 2 (12 columns)": (X2[meta], y[meta], 2),
             "6 apps / Task 1 (34 columns)": (X1, y, 6), "6 apps / Task 2 (12 columns)": (X2, y, 6)}
    for name, (X, yy, m) in views.items():
        r1 = knn_loo_error(X, yy, 1)
        lo, hi = cover_hart(r1, m)
        out["B1"][name] = {"n": len(yy), "loo_1nn_error": round(r1, 3), "bayes_lower": round(lo, 3), "bayes_upper": round(hi, 3),
                           "loo_3nn_error": round(knn_loo_error(X, yy, 3), 3), "loo_5nn_error": round(knn_loo_error(X, yy, 5), 3)}
    for name, (X, yy) in {"fb_vs_ig / Task 1": (X1[meta], y[meta]), "fb_vs_ig / Task 2": (X2[meta], y[meta]),
                          "6 apps / Task 1": (X1, y), "6 apps / Task 2": (X2, y)}.items():
        mi = mutual_info_classif(np.log1p(np.clip(X.values.astype(float), 0, None)), yy, n_neighbors=3, random_state=0) / LN2
        s = pd.Series(mi, index=X.columns).sort_values(ascending=False)
        out["B2"][name] = {"top": {c: round(float(v), 3) for c, v in s.head(8).items()}, "max_bits": round(float(s.max()), 3)}
    return out


def b3():
    f = lambda n, a, b, c: a - b * n ** (-c)  # noqa: E731
    out = {}
    for name, n, y in (("048 production curve", [2.0, 3.8, 5.4, 7.0, 8.8], [0.174, 0.398, 0.513, 0.575, 0.674]),
                       ("Charles afe-002 (3 points, comparison only)", [2, 4, 6], [0.036, 0.181, 0.367])):
        try:
            (a, b, c), _ = curve_fit(f, np.array(n), np.array(y), p0=[0.9, 1.0, 0.5], bounds=([0, 0, 0.01], [1, 50, 5]), maxfev=20000)
            need = {str(t): (round(float((b / (a - t)) ** (1 / c)), 1) if a > t else "never (asymptote below target)")
                    for t in (0.8, 0.9)}
            out[name] = {"asymptote_a": round(float(a), 3), "b": round(float(b), 3), "c": round(float(c), 3),
                         "facebook_training_flows_needed": need}
        except Exception as e:  # noqa: BLE001
            out[name] = {"fit_failed": str(e)}
    return out


def a1(X, Xt):
    Z = pd.concat([X, Xt], ignore_index=True)
    t = np.r_[np.zeros(len(X)), np.ones(len(Xt))]
    p = cross_val_predict(RandomForestClassifier(n_estimators=500, random_state=0, n_jobs=-1), Z, t,
                          cv=StratifiedKFold(5, shuffle=True, random_state=2026), method="predict_proba")[:, 1]
    return round(float(roc_auc_score(t, p)), 3)


def keys(X):
    return X.astype(str).agg("|".join, axis=1).values


def single_label_table(k, y):
    t = pd.DataFrame({"k": k, "y": y}).groupby("k").y.agg(lambda v: set(v))
    return {kk: next(iter(v)) for kk, v in t.items() if len(v) == 1}, set(t.index)


def a2(X2, y, X2t, ids, sub2):
    k, kt = keys(X2), keys(X2t)
    table, seen = single_label_table(k, y)
    test_meta = np.isin([sub2[f] for f in ids], META)
    out = {"test": {"n": len(kt), "seen_any_label": round(float(np.mean([x in seen for x in kt])), 3),
                    "single_label_twin": round(float(np.mean([x in table for x in kt])), 3),
                    "single_label_twin_among_production_meta_calls": round(float(np.mean([x in table for x in kt[test_meta]])), 3)
                    if test_meta.any() else None, "production_meta_calls": int(test_meta.sum())}}
    champ = json.loads((ROOT / "results/champions.json").read_text())[T2]["run_id"]
    oof = pd.read_csv(ROOT / "results" / champ / T2 / "oof.csv")
    fid = pd.Series(range(len(y)), index=load_task(T2)[0].flow_id.values)
    reach, correct, meta_reach, meta_n = [], [], [], 0
    for f, g in oof.groupby("fold"):
        te = fid[g.flow_id.values].values
        tr = np.setdiff1d(np.arange(len(y)), te)
        tab, _ = single_label_table(k[tr], y[tr])
        r = np.array([x in tab for x in k[te]])
        reach.append(r.mean())
        correct += [tab[x] == yy for x, yy in zip(k[te][r], y[te][r])]
        m = np.isin(g.y_pred.values, META)
        meta_n += int(m.sum())
        meta_reach += list(r[m])
    out["cv"] = {"single_label_twin": round(float(np.mean(reach)), 3),
                 "lookup_accuracy_when_reachable": round(float(np.mean(correct)), 3),
                 "single_label_twin_among_production_meta_calls": round(float(np.mean(meta_reach)), 3) if meta_n else None}
    out["test_minus_cv_points"] = round(100 * (out["test"]["single_label_twin"] - out["cv"]["single_label_twin"]), 1)
    return out


def a3(X1_raw, y):
    order = np.argsort(X1_raw.start_rel.values)
    s, lab = X1_raw.start_rel.values[order], y[order]
    agree = np.zeros(len(s), bool)
    for i in range(len(s)):
        cands = [j for j in (i - 1, i + 1) if 0 <= j < len(s)]
        j = min(cands, key=lambda j: abs(s[j] - s[i]))
        agree[i] = lab[j] == lab[i]
    freq = pd.Series(y).value_counts(normalize=True)
    out = {"overall_agreement": round(float(agree.mean()), 3), "chance_agreement": round(float((freq ** 2).sum()), 3)}
    for c in META:
        out[f"{c}_agreement"] = round(float(agree[lab == c].mean()), 3)
        out[f"{c}_chance"] = round(float(freq[c]), 3)
    return out


def a4(task, X, y):
    champ = json.loads((ROOT / "results/champions.json").read_text())[task]["run_id"]
    oof = pd.read_csv(ROOT / "results" / champ / task / "oof.csv")
    maj = oof.groupby("flow_id").y_pred.agg(lambda s: s.value_counts().idxmax())
    target = maj.reindex(load_task(task)[0].flow_id.values).values
    tree = DecisionTreeClassifier(max_depth=4, random_state=0)
    cv_fid = float((cross_val_predict(tree, X, target, cv=StratifiedKFold(5, shuffle=True, random_state=2026)) == target).mean())
    tree.fit(X, target)
    used = [X.columns[i] for i in tree.tree_.feature if i >= 0]
    kind = Counter("opening (p5_ / first 5 packets)" if (c.startswith("p5_") or task == T2) else "whole flow" for c in used)
    return {"fidelity_in_sample": round(float((tree.predict(X) == target).mean()), 3), "fidelity_cv": round(cv_fid, 3),
            "tree_accuracy_vs_truth": round(float((tree.predict(X) == y).mean()), 3),
            "split_columns": dict(Counter(used).most_common()), "split_kind": dict(kind),
            "rules": export_text(tree, feature_names=list(X.columns), max_depth=4)}


def main():
    X1_raw, y = load_task(T1)
    X2_raw, y2 = load_task(T2)
    y = np.asarray(y, dtype=object)
    assert (y == np.asarray(y2, dtype=object)).all()
    X1, X2 = TASK_FEATURES[T1](X1_raw).reset_index(drop=True), TASK_FEATURES[T2](X2_raw).reset_index(drop=True)
    X1t_raw, X2t_raw = load_test(T1), load_test(T2)
    X1t, X2t = TASK_FEATURES[T1](X1t_raw), TASK_FEATURES[T2](X2t_raw)
    sub2 = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T2]

    out = b1_b2(X1, X2, y)
    out["B3"] = b3()
    out["A1_adversarial_auc"] = {"task1": a1(X1, X1t), "task2": a1(X2, X2t)}
    out["A2_exact_twins"] = a2(X2, y, X2t, list(X2t_raw.flow_id), sub2)
    out["A3_capture_adjacency"] = a3(X1_raw, y)
    out["A4_shortcut_audit"] = {"task1": a4(T1, X1, y), "task2": a4(T2, X2, y)}
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "measurements.json").write_text(json.dumps(out, indent=2) + "\n")
    show = {k: v for k, v in out.items() if k != "A4_shortcut_audit"}
    show["A4_shortcut_audit"] = {t: {k: v for k, v in d.items() if k != "rules"} for t, d in out["A4_shortcut_audit"].items()}
    print(json.dumps(show, indent=1))
    print(out["A4_shortcut_audit"]["task1"]["rules"])


if __name__ == "__main__":
    main()
