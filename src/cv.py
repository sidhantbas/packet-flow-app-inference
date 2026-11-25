"""Repeated stratified K-fold CV on train+validation for one task.

Each task reads only from its own folder under data/official/dataset/.
"""
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

DATA = Path(__file__).resolve().parent.parent / "data" / "official" / "dataset"
TASKS = ["task1_static", "task2_realtime_prefix5"]
DEFAULT_DROP = ["flow_id", "split", "server_port", "start_rel"]
CV_SEED = 2026  # fixes the fold assignment; identical across variants
# Folds run in parallel processes; models are single-threaded (models.MODEL_JOBS). On an M4 Pro one
# SoftVote fold takes 0.5 s single-threaded vs 3.3 s with n_jobs=-1 (experiment 007, step 0).
FOLD_JOBS = int(os.environ.get("MISSION_P_FOLD_JOBS", -1))


def load_task(task, splits=("train", "validation")):
    """Return raw features (with flow_id) and labels for the given splits of ONE task."""
    Xs, ys = [], []
    for split in splits:
        X = pd.read_csv(DATA / task / f"{split}_features.csv")
        y = pd.read_csv(DATA / task / f"{split}_labels.csv")
        assert (X.flow_id.values == y.flow_id.values).all()
        Xs.append(X)
        ys.append(y["app"])
    return pd.concat(Xs, ignore_index=True), pd.concat(ys, ignore_index=True)


def basic_features(X, drop=DEFAULT_DROP):
    X = X.drop(columns=[c for c in drop if c in X.columns])
    X["transport"] = (X["transport"] == "udp").astype(int)
    return X


TIMING = ["duration", "mean_iat", "std_iat", "max_iat", "min_iat"]


def no_timing_features(X):
    """basic_features without the five timing columns (task 2 champion, experiment 007)."""
    return basic_features(X).drop(columns=TIMING)


_PREFIX_FILES = [f"task2_realtime_prefix5/{s}_features.csv" for s in ("train", "validation", "test")]
_prefix_cache = {}


def task1_with_prefix_features(X):
    """Task 1: basic_features + the Task 2 file's 17 basic columns for the same flow_id, prefixed p5_ (experiment 022).

    Task 2 files are used as input to Task 1 only. Condition 2 forbids the reverse (Task 1 features in Task 2),
    which never happens: Task 2 reads only its own folder. Disclosed in the technical report.
    """
    if "table" not in _prefix_cache:
        P = pd.concat([pd.read_csv(DATA / f) for f in _PREFIX_FILES], ignore_index=True)
        T = basic_features(P)
        T.columns = [f"p5_{c}" for c in T.columns]
        T.index = P.flow_id.values
        _prefix_cache["table"] = T
    B = basic_features(X).reset_index(drop=True)
    P = _prefix_cache["table"].loc[X.flow_id.values].reset_index(drop=True)
    return pd.concat([B, P], axis=1)


task1_with_prefix_features.extra_data = _PREFIX_FILES  # recorded (hashed) by runlog

# Feature set used by the submission for each task.
TASK_FEATURES = {"task1_static": task1_with_prefix_features, "task2_realtime_prefix5": no_timing_features}


def rf_factory(seed):
    return RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=seed, n_jobs=1)


def _run_fold(i, tr, te, X, y, model_factory, resample, labels):
    t0 = time.perf_counter()
    X_tr, y_tr = X.iloc[tr], y.iloc[tr]
    if resample is not None:
        X_tr, y_tr = resample(X_tr, y_tr, i)
    pred = np.ravel(model_factory(i).fit(X_tr, y_tr).predict(X.iloc[te]))  # CatBoost returns (n, 1)
    return {"pred": pred, "seconds": time.perf_counter() - t0,
            "macro": f1_score(y.iloc[te], pred, average="macro"),
            "per_class": f1_score(y.iloc[te], pred, average=None, labels=labels, zero_division=0)}


def evaluate(task, features=basic_features, model_factory=rf_factory, resample=None,
             n_splits=5, n_repeats=10, cv_seed=CV_SEED, fold_jobs=FOLD_JOBS, splits=None, split_name=None):
    """Run repeated stratified K-fold CV on train+validation of `task`.

    `features(X_raw) -> DataFrame` (row-wise only), `model_factory(seed) -> estimator`,
    optional `resample(X_tr, y_tr, seed) -> (X_tr, y_tr)` applied to the training fold only.
    The model seed for fold i is i, so variants see identical folds and model seeds.
    Returns a dict with per-fold macro F1, per-fold per-class F1, out-of-fold predictions and summaries.
    """
    X_raw, y = load_task(task)
    X = features(X_raw)
    labels = sorted(y.unique())
    if splits is None:  # default: repeated stratified K-fold; `splits` may supply other folds (e.g. twin-aware, 036)
        splits = list(RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=cv_seed).split(X, y))
    out = Parallel(n_jobs=fold_jobs)(delayed(_run_fold)(i, tr, te, X, y, model_factory, resample, labels)
                                     for i, (tr, te) in enumerate(splits))
    macro = [o["macro"] for o in out]
    per_class = [o["per_class"] for o in out]
    seconds = [o["seconds"] for o in out]
    y_pred = [o["pred"] for o in out]
    y_true = [y.iloc[te].values for _, te in splits]
    flow_ids = [X_raw.flow_id.iloc[te].values for _, te in splits]
    folds = [np.full(len(te), i) for i, (_, te) in enumerate(splits)]
    macro, per_class = np.array(macro), np.array(per_class)
    repeat_means = macro.reshape(n_repeats, n_splits).mean(axis=1)
    return {
        "task": task,
        "n_flows": len(y),
        "features": list(X.columns),
        "labels": labels,
        "fold_macro": macro,
        "fold_per_class": per_class,
        "y_true": np.concatenate(y_true),  # pooled over all folds (each flow appears n_repeats times)
        "y_pred": np.concatenate(y_pred),
        "flow_id": np.concatenate(flow_ids),  # aligned with y_true / y_pred
        "fold": np.concatenate(folds),
        "fold_seconds": np.array(seconds),
        "extra_data": list(getattr(features, "extra_data", [])),  # files outside the task folder read by `features`  # fit + predict wall time per fold
        "cv": {"n_splits": n_splits, "n_repeats": n_repeats, "cv_seed": cv_seed,
               "resample": getattr(resample, "__name__", None) if resample else None,
               "fold_jobs": fold_jobs, "splits": split_name or "RepeatedStratifiedKFold"},
        "macro_mean": macro.mean(),
        "macro_std": macro.std(ddof=1),
        "repeat_std": repeat_means.std(ddof=1),
        "per_class_mean": dict(zip(labels, per_class.mean(axis=0))),
        "per_class_std": dict(zip(labels, per_class.std(axis=0, ddof=1))),
    }


def summarize(res):
    lines = [
        f"{res['task']}: macro F1 {res['macro_mean']:.4f} ± {res['macro_std']:.4f} (fold std), "
        f"repeat-mean std {res['repeat_std']:.4f}, {len(res['fold_macro'])} folds, {res['n_flows']} flows",
    ]
    for c in res["labels"]:
        lines.append(f"  {c:10s} {res['per_class_mean'][c]:.3f} ± {res['per_class_std'][c]:.3f}")
    return "\n".join(lines)


if __name__ == "__main__":
    for task in TASKS:
        print(summarize(evaluate(task)))


def rest_of_flow(X):
    """Exact statistics of packets 6..N (after the 5-packet opening), from the Task 1 row and the Task 2 row of the
    same flow (experiment 030). Totals, means and population stds subtract exactly: count, bytes, mean and std of
    packet size per direction; duration after packet 5; mean and std of the remaining gaps. Valid for all 411 flows
    (no negative counts, bytes or variances). Directions/flows with no remaining packets get 0."""
    if "table" not in _prefix_cache:
        task1_with_prefix_features(X.head(1))
    if "rest" not in _prefix_cache:
        F = pd.concat([pd.read_csv(DATA / f"task1_static/{s}_features.csv") for s in ("train", "validation", "test")])
        F = F.set_index("flow_id")
        P = pd.concat([pd.read_csv(DATA / f) for f in _PREFIX_FILES]).set_index("flow_id").loc[F.index]
        out = {}
        for d in ("up", "down"):
            n = F[f"packet_count_{d}"] - P[f"packet_count_{d}"]
            b = F[f"bytes_{d}"] - P[f"bytes_{d}"]
            ss = (F[f"packet_count_{d}"] * (F[f"std_pkt_size_{d}"] ** 2 + F[f"mean_pkt_size_{d}"] ** 2)
                  - P[f"packet_count_{d}"] * (P[f"std_pkt_size_{d}"] ** 2 + P[f"mean_pkt_size_{d}"] ** 2))
            m = np.where(n > 0, b / np.where(n > 0, n, 1), 0.0)
            v = np.where(n > 0, ss / np.where(n > 0, n, 1) - m ** 2, 0.0)
            out.update({f"r_count_{d}": n, f"r_bytes_{d}": b, f"r_mean_size_{d}": m, f"r_std_size_{d}": np.sqrt(np.clip(v, 0, None))})
        nf = F.packet_count_up + F.packet_count_down
        g = nf - 5
        dur = F.duration - P.duration
        ssg = (nf - 1) * (F.std_iat ** 2 + F.mean_iat ** 2) - 4 * (P.std_iat ** 2 + P.mean_iat ** 2)
        mg = np.where(g > 0, dur / np.where(g > 0, g, 1), 0.0)
        vg = np.where(g > 0, ssg / np.where(g > 0, g, 1) - mg ** 2, 0.0)
        out.update({"r_duration": dur, "r_mean_iat": mg, "r_std_iat": np.sqrt(np.clip(vg, 0, None))})
        _prefix_cache["rest"] = pd.DataFrame(out, index=F.index)
    return _prefix_cache["rest"].loc[X.flow_id.values].reset_index(drop=True)


def task1_prefix_rest_features(X):
    """022 Task 1 features (17 + 17 prefix-5) + 11 rest-of-flow columns (experiment 030, rest_add)."""
    return pd.concat([task1_with_prefix_features(X), rest_of_flow(X)], axis=1)


def task1_rest_features(X):
    """17 Task 1 columns + 11 rest-of-flow columns, no raw prefix-5 columns (experiment 030, rest_swap)."""
    return pd.concat([basic_features(X).reset_index(drop=True), rest_of_flow(X)], axis=1)


task1_prefix_rest_features.extra_data = _PREFIX_FILES
task1_rest_features.extra_data = _PREFIX_FILES
