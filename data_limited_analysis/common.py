"""Shared settings for the data-limited analysis (PROTOCOL.md). Production code in src/ is imported, never modified."""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import RepeatedStratifiedKFold

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from cv import TASK_FEATURES, evaluate, load_task  # noqa: E402
from models import SoftVote, task1_bundle, task2_model  # noqa: E402

T1, T2 = "task1_static", "task2_realtime_prefix5"
TASKS = (T1, T2)
PROD = {T1: task1_bundle, T2: task2_model}
CV = {"n_splits": 5, "n_repeats": 5, "cv_seed": 2026}
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)


def splits(task):
    X, y = load_task(task)
    return list(RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=2026).split(X, y))


def data(task):
    Xr, y = load_task(task)
    return Xr, TASK_FEATURES[task](Xr).reset_index(drop=True), np.asarray(y.values, dtype=object)


def run(task, factory=None, features=None, resample=None):
    """Fold macro F1 (25 values) of a variant under the common CV."""
    r = evaluate(task, features or TASK_FEATURES[task], factory or PROD[task], resample=resample, **CV)
    return np.asarray(r["fold_macro"], dtype=float)


def baseline():
    """Per-fold macro F1 of production in both tasks (cached in baseline_folds.json)."""
    p = HERE / "baseline_folds.json"
    if p.exists():
        d = json.loads(p.read_text())
        return {t: np.array(d[t]) for t in TASKS}
    d = {t: run(t) for t in TASKS}
    p.write_text(json.dumps({t: v.tolist() for t, v in d.items()}, indent=1) + "\n")
    return d


def score(t1, t2):
    return 50 * np.asarray(t1) + 50 * np.asarray(t2)


def paired(task, var_folds, base=None):
    """Paired comparison of a one-task variant against production on identical folds (PROTOCOL.md tie rule)."""
    base = base or baseline()
    other = T2 if task == T1 else T1
    sb = score(base[T1], base[T2])
    sv = score(var_folds, base[other]) if task == T1 else score(base[other], var_folds)
    d = sv - sb
    return {"score_mean": round(float(sv.mean()), 3), "score_sd": round(float(sv.std(ddof=1)), 3),
            "delta_mean": round(float(d.mean()), 3), "delta_sd": round(float(d.std(ddof=1)), 3),
            "wins": int((d > 1e-9).sum()), "losses": int((d < -1e-9).sum()),
            "verdict": "BEATS" if d.mean() > d.std(ddof=1) and d.mean() > 0 else
                       ("WORSE" if -d.mean() > d.std(ddof=1) else "TIE")}


def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
