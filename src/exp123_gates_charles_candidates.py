"""Experiment 123: capture gates 1 and 2 (src/capture_checks.py, unchanged) on Charles's 364 provisional capture candidates
(protocol: experiments/123_gates_on_charles_candidates.md).

Command: .venv/bin/python src/exp123_gates_charles_candidates.py   (needs `git fetch upstream`: reads commit d3189ba)
Writes experiments/123_evidence/gates_<profile>_<scope>.txt, family_auc.json and summary.json.
"""
import contextlib
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from capture_checks import T1, T2, gate1, gate2, opening_report
from cv import basic_features, load_task
from models import T1_COLS

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = "d3189ba"
BASE = "experiments/charles-003-capture-audit/evidence/20261020-flow-aggregates"
PROFILES = ["observed", "split-mtu1514-sensitivity"]
SCOPES = {"all": None, "iphone_pilot": "sid-iphone-20261008T233855Z", "iphone_long": "sid-iphone-20261009T115620Z-long-cellular"}
TIMING = ["duration", "mean_iat", "std_iat", "min_iat", "max_iat", "burst_count"]
FAMILIES = {"all 17": list(T1_COLS), "sizes and counts (no timing)": [c for c in T1_COLS if c not in TIMING],
            "timing only": TIMING, "min_iat alone": ["min_iat"]}
EVIDENCE = ROOT / "experiments/123_evidence"


def show(path):
    return pd.read_csv(io.StringIO(subprocess.run(["git", "show", f"{UPSTREAM}:{path}"], cwd=ROOT, capture_output=True,
                                                  text=True, check=True).stdout))


def load(profile):
    A = show(f"{BASE}/{profile}/candidate_task1_features.csv")
    P = show(f"{BASE}/{profile}/candidate_task2_features.csv")
    L = show(f"{BASE}/{profile}/candidate_labels.csv")
    assert (A.flow_id == P.flow_id).all() and (A.flow_id == L.flow_id).all()
    return A, P, L


def run(A, P, L, Ao, yo, Po):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"{len(A)} candidate flows; apps {L.app.value_counts().to_dict()}")
        g1 = gate1(A, P)
        opening_report(P, Po)
        g2 = gate2(A, L, Ao, yo)
    text = buf.getvalue()
    auc = re.search(r"adversarial AUC original vs captured: ([0-9.]+)", text)
    rows = re.findall(r"  (app \w+)\s+n=\s*(\d+)\s+median NN distance ([0-9.]+) \(orig 90th pct ([0-9.]+)\)\s+same-label 5-NN ([0-9.]+) \(orig ([0-9.]+)\)\s+(ok|FAR)", text)
    disc = dict(re.findall(r"^    (\w+)\s+-> (.*)$", text, re.M))
    fails = re.findall(r"  FAIL (task\d): (.*)", text)
    return text, {"flows": len(A), "apps": L.app.value_counts().to_dict(), "gate1": bool(g1), "gate1_failures": fails, "gate2": bool(g2),
                  "adversarial_auc": float(auc.group(1)) if auc else None,
                  "per_app": {r[0]: {"n": int(r[1]), "median_nn": float(r[2]), "orig_p90": float(r[3]), "same_label_5nn": float(r[4]),
                                     "orig_same_label": float(r[5]), "verdict": r[6]} for r in rows},
                  "nearest_original_label": disc}


def family_auc(Ao, A):
    out = {}
    for name, cols in FAMILIES.items():
        L = lambda X: np.log1p(basic_features(X)[cols].astype(float).clip(lower=0)).values
        Lo, Ln = L(Ao), L(A)
        mu, sd = Lo.mean(0), np.where(Lo.std(0) > 0, Lo.std(0), 1)
        X = np.vstack([(Lo - mu) / sd, (Ln - mu) / sd])
        t = np.r_[np.zeros(len(Lo)), np.ones(len(Ln))]
        p = cross_val_predict(RandomForestClassifier(300, random_state=0, class_weight="balanced"), X, t,
                              cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
        out[name] = round(float(roc_auc_score(t, p)), 3)
    return out


def main():
    Ao, yo = load_task(T1)
    Po, _ = load_task(T2)
    yo = yo.values
    EVIDENCE.mkdir(exist_ok=True)
    summary = {"upstream_commit": UPSTREAM}
    for profile in PROFILES:
        A, P, L = load(profile)
        grp = A.flow_id.str.split("__").str[0]
        for scope, g in SCOPES.items():
            m = (grp == g).values if g else np.ones(len(A), bool)
            if not m.any():
                continue
            text, res = run(A[m].reset_index(drop=True), P[m].reset_index(drop=True), L[m].reset_index(drop=True), Ao, yo, Po)
            (EVIDENCE / f"gates_{profile}_{scope}.txt").write_text(text)
            summary[f"{profile} / {scope}"] = res
            print(f"{profile:26s} {scope:13s} flows {res['flows']:4d} | gate 1 {'PASS' if res['gate1'] else 'FAIL'} | gate 2 "
                  f"{'PASS' if res['gate2'] else 'FAIL'} | AUC {res['adversarial_auc']} | " +
                  "; ".join(f"{k.split()[1]} {v['median_nn']:.2f}/{v['orig_p90']:.2f} {v['same_label_5nn']:.2f}/{v['orig_same_label']:.2f} {v['verdict']}"
                            for k, v in res["per_app"].items()))
    A, _, _ = load("observed")
    fam = family_auc(Ao, A)
    print("family AUC (observed, all):", fam)
    (EVIDENCE / "family_auc.json").write_text(json.dumps({"profile": "observed", "scope": "all", "adversarial_auc": fam}, indent=2) + "\n")
    (EVIDENCE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
