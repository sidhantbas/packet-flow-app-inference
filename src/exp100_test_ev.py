"""Experiment 100, decision analysis (outside the frozen protocol; decides nothing): what relabelling the one qualifying test flow
(flow_000223: Task 1 youtube, Task 2 instagram) is worth in leaderboard points, per possible truth and in expectation.

Inputs: the ranked entry's Task 1 predicted counts; expected test counts from the stratified split design (validation count x
81/83); 089's per-class precision on the fresh ordinary seeds (REF runs, 2046-2050); the truth of the cross-task cases on those
seeds (FB runs). No test labels, no metadata label_counts. Writes experiments/100_evidence/test_ev.json.

Usage: .venv/bin/python src/exp100_test_ev.py
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from cv import DATA

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
FLOW, CURRENT = "flow_000223", "youtube"
SEEDS = (2046, 2047, 2048, 2049, 2050)


def run(arm, seed):
    return sorted(p.name for p in (ROOT / "results").glob(f"*_100_{arm}_ordinary_s{seed}"))[-1]


def macro_delta(state, truth, label):
    """Points (50 x macro F1) gained by relabelling one CURRENT-labelled flow to `label` when its true class is `truth`.
    state: {class: (TP, P, T)} expected baseline values."""
    s = {c: list(v) for c, v in state.items()}
    if label == CURRENT:
        return 0.0
    if truth == CURRENT:
        s[CURRENT][0] -= 1
    s[CURRENT][1] -= 1
    s[label][1] += 1
    if truth == label:
        s[label][0] += 1
    f1 = lambda tp, p, t: 2 * tp / (p + t) if p + t else 0.0  # noqa: E731
    return 50 * sum(f1(*s[c]) - f1(*state[c]) for c in LABS) / len(LABS)


def main():
    ranked = json.loads((ROOT / "submissions/production-089-bundle/submission.json").read_text())[T1]
    assert ranked[FLOW] == CURRENT
    pred_n = Counter(ranked.values())
    val = pd.read_csv(DATA / T1 / "validation_labels.csv").app.value_counts()
    exp_n = {c: float(val.get(c, 0)) * 81 / 83 for c in LABS}
    # 089 per-class precision, pooled over the fresh REF runs
    o = pd.concat([pd.read_csv(ROOT / "results" / run("REF", s) / T1 / "oof.csv") for s in SEEDS])
    prec = {c: float(((o.y_pred == c) & (o.y_true == c)).sum() / max((o.y_pred == c).sum(), 1)) for c in LABS}
    state = {c: (min(prec[c] * pred_n[c], exp_n[c]), float(pred_n[c]), exp_n[c]) for c in LABS}
    # truth of the cross-task cases on the fresh seeds (FB arm changes = the cases)
    truth, flows = Counter(), {}
    for s in SEEDS:
        f, r = (pd.read_csv(ROOT / "results" / run(a, s) / T1 / "oof.csv") for a in ("FB", "REF"))
        case = f.y_pred.values != r.y_pred.values
        truth.update(f.y_true.values[case])
        for fl, y in zip(f.flow_id.values[case], f.y_true.values[case]):
            flows[fl] = y
    n = sum(truth.values())
    p_case = {c: truth.get(c, 0) / n for c in LABS}
    fl_truth = Counter(flows.values())
    p_flow = {c: fl_truth.get(c, 0) / len(flows) for c in LABS}
    # cases in folds where 089 predicts fewer instagram flows than expected (the test's situation; frozen descriptive in 100)
    an = json.loads((ROOT / "experiments/100_evidence/analysis.json").read_text())["ordinary"]
    fb_def = sum(an[str(s)]["FB"]["facebook_share_in_ig_deficit_folds"][0] for s in SEEDS)
    n_def = sum(an[str(s)]["FB"]["facebook_share_in_ig_deficit_folds"][1] for s in SEEDS)
    assert set(truth) <= {"facebook", "instagram"}  # every fresh-seed case is Meta, so the rest of a deficit-fold share is instagram
    p_def = {c: 0.0 for c in LABS} | {"facebook": fb_def / n_def, "instagram": 1 - fb_def / n_def}
    table = {label: {truth_c: round(macro_delta(state, truth_c, label), 2) for truth_c in ("instagram", "facebook", CURRENT, "google")}
             for label in ("instagram", "facebook")}
    # break-even precision of a flip when the only alternative truth is the current label: p* = L / (G + L)
    breakeven = {label: round(-table[label][CURRENT] / (table[label][label] - table[label][CURRENT]), 3) for label in table}
    ev = {"break_even_precision_vs_current": breakeven}
    for name, p in (("case_weighted", p_case), ("flow_weighted", p_flow), ("instagram_deficit_folds", p_def)):
        ev[name] = {label: round(sum(p[t] * macro_delta(state, t, label) for t in LABS), 2) for label in ("instagram", "facebook")}
    out = {"flow": FLOW, "current_label": CURRENT, "predicted_counts": dict(pred_n), "expected_counts": {c: round(v, 1) for c, v in exp_n.items()},
           "ref_precision_fresh_seeds": {c: round(v, 3) for c, v in prec.items()},
           "baseline_state_TP_P_T": {c: [round(x, 2) for x in v] for c, v in state.items()},
           "cases_fresh_seeds": {"n": n, "truth": dict(truth), "distinct_flows": len(flows), "distinct_truth": dict(fl_truth)},
           "points_if_truth_is": table, "expected_points": ev,
           "probabilities": {"case_weighted": {c: round(v, 3) for c, v in p_case.items()},
                             "flow_weighted": {c: round(v, 3) for c, v in p_flow.items()},
                             "instagram_deficit_folds": {c: round(v, 3) for c, v in p_def.items()}}}
    ev_dir = ROOT / "experiments/100_evidence"
    ev_dir.mkdir(exist_ok=True)
    (ev_dir / "test_ev.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
