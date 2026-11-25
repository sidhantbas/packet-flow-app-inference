"""Baseline reproduction for the data-limited analysis brief (2026-10-10).

Repeated stratified CV, 5 folds x 5 repeats, cv_seed 2026, model seed = fold index (cv.evaluate). Both tasks use the same
330 labelled flows in the same order, so fold i is the same split in both tasks and the challenge score of a fold is
50 * macro F1 (Task 1) + 50 * macro F1 (Task 2).

Usage: .venv/bin/python data_limited_analysis/baseline_repro.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from cv import TASK_FEATURES, evaluate, load_task  # noqa: E402
from models import task1_bundle, task1_pair_verifiers, task2_model  # noqa: E402

T1, T2 = "task1_static", "task2_realtime_prefix5"
CV = {"n_splits": 5, "n_repeats": 5, "cv_seed": 2026}
PIPELINES = {"leaderboard_88.11_file (Task 1 084 ALL, Task 2 014)": task1_pair_verifiers,
             "current_production (Task 1 089 bundle, Task 2 014)": task1_bundle}


def main():
    _, y1 = load_task(T1)
    _, y2 = load_task(T2)
    assert (y1.values == y2.values).all()
    t2 = evaluate(T2, TASK_FEATURES[T2], task2_model, **CV)
    out = {"cv": CV, "task2_macro_mean": float(t2["macro_mean"]), "task2_macro_std": float(t2["macro_std"]), "pipelines": {}}
    for name, f in PIPELINES.items():
        t1 = evaluate(T1, TASK_FEATURES[T1], f, **CV)
        score = 50 * t1["fold_macro"] + 50 * t2["fold_macro"]
        out["pipelines"][name] = {
            "task1_macro_mean": float(t1["macro_mean"]), "task1_macro_std": float(t1["macro_std"]),
            "score_mean": float(score.mean()), "score_std": float(score.std(ddof=1)),
            "score_min": float(score.min()), "score_max": float(score.max()),
            "within_1sd_of_88.11": bool(abs(score.mean() - 88.11) <= score.std(ddof=1))}
    (Path(__file__).parent / "baseline.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
