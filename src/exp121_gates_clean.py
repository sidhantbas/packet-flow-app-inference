"""Experiment 121: capture gates 1 and 2 (src/capture_checks.py, unchanged) on the clean extraction (120) vs the original
(protocol: experiments/121_gates_on_clean_captures.md).

Command: .venv/bin/python src/exp121_gates_clean.py
Writes experiments/121_evidence/gates_<version>_<scope>.txt (the gate printouts) and summary.json.
"""
import contextlib
import io
import json
import re
from pathlib import Path

import pandas as pd

from capture_checks import T1, T2, gate1, gate2, opening_report
from cv import load_task

ROOT = Path(__file__).resolve().parent.parent
V1, V2 = ROOT / "data/captures", ROOT / "data/captures/clean-v2"
GROUPS = {"iphone_pilot": "sid-iphone-20261008T233855Z", "iphone_long": "sid-iphone-20261009T115620Z-long-cellular",
          "android": "sid-android-20261009T152334Z-check-macshare"}
EVIDENCE = ROOT / "experiments/121_evidence"


def sessions(group):
    """Sessions with flows in both extractions."""
    out = []
    for d in sorted((V2 / group).iterdir()):
        if d.is_dir() and (V1 / group / d.name / "labels.csv").exists() and len(pd.read_csv(d / "labels.csv")):
            out.append(d.name)
    return out


def load(version, groups):
    A, P, L = [], [], []
    for g in groups:
        for s in sessions(GROUPS[g]):
            base = (V1 if version == "V1" else V2) / GROUPS[g] / s
            a, p = pd.read_csv(base / "task1_features.csv"), pd.read_csv(base / "task2_features.csv")
            lab = pd.read_csv(base / "labels.csv").fillna("")
            if version != "V1":
                keep = lab.keep.astype(str).str.lower().eq("true").values
                a, p, lab = a[keep], p[keep], lab[keep]
            A.append(a), P.append(p), L.append(lab[["flow_id", "app"]])
    A, P, L = (pd.concat(x, ignore_index=True) for x in (A, P, L))
    assert (A.flow_id == P.flow_id).all() and (A.flow_id == L.flow_id).all()
    return A, P, L


def run(version, groups, Ao, yo, Po):
    A, P, L = load(version, groups)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"{version} on {'+'.join(groups)}: {len(A)} captured flows; apps {L.app.value_counts().to_dict()}")
        g1 = gate1(A, P)
        opening_report(P, Po)
        g2 = gate2(A, L, Ao, yo)
    text = buf.getvalue()
    auc = re.search(r"adversarial AUC original vs captured: ([0-9.]+)", text)
    rows = re.findall(r"  (app \w+)\s+n=\s*(\d+)\s+median NN distance ([0-9.]+) \(orig 90th pct ([0-9.]+)\)\s+same-label 5-NN ([0-9.]+) \(orig ([0-9.]+)\)\s+(ok|FAR)", text)
    return text, {"flows": len(A), "apps": L.app.value_counts().to_dict(), "gate1": bool(g1), "gate2": bool(g2),
                  "adversarial_auc": float(auc.group(1)) if auc else None,
                  "per_app": {r[0]: {"n": int(r[1]), "median_nn": float(r[2]), "orig_p90": float(r[3]),
                                     "same_label_5nn": float(r[4]), "orig_same_label": float(r[5]), "verdict": r[6]} for r in rows}}


def main():
    Ao, yo = load_task(T1)
    Po, _ = load_task(T2)
    yo = yo.values
    EVIDENCE.mkdir(exist_ok=True)
    scopes = {"iphone_pilot": ["iphone_pilot"], "iphone_long": ["iphone_long"], "android": ["android"],
              "all": ["iphone_pilot", "iphone_long", "android"], "iphone_all": ["iphone_pilot", "iphone_long"]}
    plan = [("V1", s) for s in scopes] + [("V2", s) for s in scopes] + [("V2-process", "iphone_all")]
    summary = {}
    for version, scope in plan:
        text, res = run("V1" if version == "V1" else "V2", scopes[scope], Ao, yo, Po)
        (EVIDENCE / f"gates_{version}_{scope}.txt").write_text(text)
        summary[f"{version} / {scope}"] = res
        print(f"{version:10s} {scope:13s} flows {res['flows']:4d} | gate 1 {'PASS' if res['gate1'] else 'FAIL'} | gate 2 "
              f"{'PASS' if res['gate2'] else 'FAIL'} | AUC {res['adversarial_auc']} | " +
              "; ".join(f"{k.split()[1]} {v['median_nn']:.2f}/{v['orig_p90']:.2f} {v['same_label_5nn']:.2f}/{v['orig_same_label']:.2f} {v['verdict']}"
                        for k, v in res["per_app"].items()))
    (EVIDENCE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
