"""Experiment 005 checks: official-scorer validation run, seed stability on test, compute cost.

Usage: python src/exp005_checks.py [scorer|stability|cost ...]   (default: all)
"""
import importlib.util
import json
import pickle
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

from cv import DATA, TASKS, basic_features, load_task
from make_submission import ROOT, check, fit_predict, load_test, write_submission
from models import SoftVote

N_SEEDS = 10


def official_module():
    """Import data/official/evaluation_script/main.py unchanged."""
    spec = importlib.util.spec_from_file_location("official_eval", ROOT / "data/official/evaluation_script/main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scorer_check():
    """Train on train only, predict validation, and score with the official evaluate() in both formats."""
    evaluate = official_module().evaluate
    preds, truth = {}, {}
    for task in TASKS:
        preds[task], _ = fit_predict(task, train_splits=("train",), predict_split="validation")
        check(preds[task], task, split="validation")
        X, y = load_task(task, ("validation",))
        truth[task] = dict(zip(X.flow_id, y))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "annotations.json").write_text(json.dumps({"tasks": truth}))
        write_submission(preds, tmp / "val_submission.json", tmp / "val_submission.zip")
        for fmt in ["json", "zip"]:
            out = evaluate(str(tmp / "annotations.json"), str(tmp / f"val_submission.{fmt}"), "dev")
            print(f"official evaluate() on validation ({fmt} submission):")
            print(json.dumps(out["submission_result"], indent=2))


def official_loader_check():
    """Parse the written test submission files with the official loader and check IDs and labels."""
    mod = official_module()
    for name in ["submission.json", "submission.zip"]:
        sub = mod._load_submission(str(ROOT / "submissions" / name))
        for task in TASKS:
            check(sub[task], task)
            ids = set(load_test(task).flow_id)
            sample = set(pd.read_csv(DATA / task / "sample_submission.csv").flow_id)
            assert ids == sample
        print(f"{name}: parsed by official loader, 81/81 test IDs per task, all labels valid")


def stability():
    for task in TASKS:
        X_tr, y = load_task(task)
        X_te = load_test(task)
        preds = np.array([SoftVote(s).fit(basic_features(X_tr), y).predict(basic_features(X_te)) for s in range(N_SEEDS)])
        changed = (preds != preds[0]).any(axis=0)
        final = pd.Series(preds[0], index=X_te.flow_id)
        print(f"=== {task}: {int(changed.sum())}/{len(X_te)} test flows change label across {N_SEEDS} seeds")
        if changed.any():
            detail = pd.DataFrame(preds[:, changed].T, index=X_te.flow_id[changed])
            print(" flows that change (predicted label per seed 0-9):")
            for fid, row in detail.iterrows():
                print(f"   {fid}: {row.value_counts().to_dict()}")
        # per predicted class (seed 0 = submitted model): how many of its flows are unstable
        per_class = pd.DataFrame({"pred": preds[0], "changed": changed}).groupby("pred").changed.agg(["size", "sum"])
        # No comparison with metadata.json test label_counts: they derive from test labels (condition 1, removed 2026-09-30).
        dist = pd.DataFrame({"predicted (seed 0)": final.value_counts()}).fillna(0).astype(int)
        dist["unstable flows"] = per_class["sum"].reindex(dist.index).fillna(0).astype(int)
        # distribution range across seeds
        counts = pd.DataFrame([pd.Series(p).value_counts() for p in preds]).fillna(0)
        dist["min–max over seeds"] = [f"{int(counts[c].min())}–{int(counts[c].max())}" if c in counts else "0–0" for c in dist.index]
        print(dist.to_string())


def cost(repeats=3):
    for task in TASKS:
        X_tr, y = load_task(task)
        X_tr = basic_features(X_tr)
        X_te = basic_features(load_test(task))
        fit_t, pred_t = [], []
        for r in range(repeats):
            t0 = time.perf_counter()
            m = SoftVote(r).fit(X_tr, y)
            t1 = time.perf_counter()
            m.predict(X_te)
            t2 = time.perf_counter()
            fit_t.append(t1 - t0)
            pred_t.append(t2 - t1)
        size = {type(sub).__name__: len(pickle.dumps(sub)) for sub in m.models_}
        print(f"=== {task}: train {len(X_tr)} flows x {X_tr.shape[1]} features, predict {len(X_te)} flows")
        print(f"  training time   median {np.median(fit_t):.2f} s  (runs {np.round(fit_t, 2).tolist()})")
        print(f"  inference time  median {np.median(pred_t) * 1000:.0f} ms for {len(X_te)} flows "
              f"({np.median(pred_t) / len(X_te) * 1000:.2f} ms/flow, batch)")
        print(f"  model size (pickle): total {sum(size.values()) / 1e6:.1f} MB; "
              + ", ".join(f"{k} {v / 1e6:.1f} MB" for k, v in size.items()))


if __name__ == "__main__":
    parts = sys.argv[1:] or ["scorer", "stability", "cost"]
    if "scorer" in parts:
        scorer_check()
        official_loader_check()
    if "stability" in parts:
        stability()
    if "cost" in parts:
        cost()
