"""Experiment 101: test-time averaging for Task 1 (protocol: experiments/101_test_time_averaging.md, frozen first).

Production (models.task1_cross_task) predicts each flow once unchanged and once per time-scale factor s_k = exp(0.1 z_k)
(z_k = standard normal quantiles at (k - 0.5)/10); all ten timing columns are multiplied by s_k; the majority label wins
(ties: the unchanged prediction if tied, else the alphabetically first tied label).

Usage: python src/exp101_test_time_averaging.py --smoke
       python src/exp101_test_time_averaging.py --arm REF|TTA --seed N [--ref RUN_ID]
       python src/exp101_test_time_averaging.py --build      (only after a pass: test predictions and changes vs uploads 1-8)
"""
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import norm
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from models import task1_cross_task
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
SEEDS = (2051, 2052, 2053, 2054, 2055)
BASE_TIMING = ("duration", "mean_iat", "std_iat", "min_iat", "max_iat")
TIMING_COLS = list(BASE_TIMING) + [f"p5_{c}" for c in BASE_TIMING]


def factors(sigma=0.1, k=10):
    return np.exp(sigma * norm.ppf((np.arange(1, k + 1) - 0.5) / k))


class TTA(BaseEstimator, ClassifierMixin):
    """Production Task 1 model with majority voting over time-scaled copies of each flow. unit=True sets every factor to 1."""

    def __init__(self, seed=0, sigma=0.1, k=10, unit=False):
        self.seed, self.sigma, self.k, self.unit = seed, sigma, k, unit

    def fit(self, X, y):
        self.model_ = task1_cross_task(self.seed).fit(X, y)
        self.classes_ = self.model_.classes_
        return self

    def predict_votes(self, X):
        base = np.asarray(self.model_.predict(X), dtype=object)
        votes = [base]
        for s in (np.ones(self.k) if self.unit else factors(self.sigma, self.k)):
            Xs = X.copy()
            Xs[TIMING_COLS] = Xs[TIMING_COLS] * s
            votes.append(np.asarray(self.model_.predict(Xs), dtype=object))
        return base, np.vstack(votes)

    def predict(self, X):
        base, V = self.predict_votes(X)
        out = base.copy()
        for i in range(V.shape[1]):
            c = Counter(V[:, i])
            top = max(c.values())
            tied = sorted(lab for lab, n in c.items() if n == top)
            out[i] = base[i] if base[i] in tied else tied[0]
        return out


def tta(seed):
    return TTA(seed=seed)


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_101_{arm}_s{seed}"))
    return hits[-1] if hits else None


def smoke():
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    tr, te = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(Xr, yv))[0]
    ref = np.asarray(task1_cross_task(0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te]), dtype=object)
    unit = TTA(seed=0, unit=True).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te])
    m = TTA(seed=0).fit(X.iloc[tr], yv[tr])
    base, V = m.predict_votes(X.iloc[te])
    print("unit factors reproduce production:", bool((unit == ref).all()))
    print("factors:", np.round(factors(), 3).tolist())
    print("fold 0: flows whose 11 votes are not unanimous:", int((V != V[0]).any(axis=0).sum()), "of", V.shape[1],
          "| TTA changes:", int((m.predict(X.iloc[te]) != base).sum()))


def uploads():
    """Task 1 predictions of uploads 1-8 (1-2 from Git history, 3-8 from their folders)."""
    out = {}
    for n, ref in ((1, "6b76821"), (2, "0a1e0ba")):
        txt = subprocess.run(["git", "show", f"{ref}:submissions/submission.json"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout
        out[n] = json.loads(txt)
    for n, folder in ((3, "best-87.77-frozen-5eb9a8b"), (4, "candidate-066-rest-expert"), (5, "candidate-083-instagram-verifier"),
                      (6, "best-88.11-production-084"), (7, "production-089-bundle"), (8, "production-100-cross-task")):
        out[n] = json.loads((ROOT / "submissions" / folder / "submission.json").read_text())
    return out


def build():
    from make_submission import load_test
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    Xt_raw = load_test(T1)
    m = TTA(seed=0).fit(X, yv)
    pred = dict(zip(Xt_raw.flow_id, m.predict(TASK_FEATURES[T1](Xt_raw))))
    changes = {}
    for n, sub in uploads().items():
        t1 = sum(sub["task1_static"][f] != v for f, v in pred.items())
        changes[n] = t1  # Task 2 would be the production Task 2 file (identical to uploads 1-8's Task 2 from upload 1 on)
    ev = ROOT / "experiments/101_evidence"
    ev.mkdir(exist_ok=True)
    info = {"task1_changes_vs_upload": changes, "upload_eligible_by_count": min(changes.values()) >= 3,
            "changed_vs_upload_8": {f: (uploads()[8]["task1_static"][f], v) for f, v in pred.items()
                                    if uploads()[8]["task1_static"][f] != v}}
    (ev / "test_changes.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--smoke" in args:
        smoke()
        sys.exit()
    if "--build" in args:
        build()
        sys.exit()
    arm = args[args.index("--arm") + 1]
    seed = int(args[args.index("--seed") + 1])
    assert seed in SEEDS, "101 uses only the never-used cv_seeds 2051-2055"
    f = task1_cross_task if arm == "REF" else tta
    ref = args[args.index("--ref") + 1] if "--ref" in args else (None if arm == "REF" else run_id("REF", seed))
    feats = TASK_FEATURES[T1]
    t0 = datetime.now(timezone.utc)
    res = {T1: evaluate(T1, feats, f, cv_seed=seed)}
    q = (f"Task 1 production reference (task1_cross_task) on never-used cv_seed {seed} (101)" if arm == "REF"
         else f"Task 1 101 test-time averaging vs production on never-used cv_seed {seed}")
    rid = record_run("101", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref, question=q,
                     config={"arm": arm, "cv_seed": seed, "sigma": 0.1, "copies": 10} if arm == "TTA"
                     else {"arm": arm, "model": "task1_cross_task", "cv_seed": seed}, started=t0)
    print(rid)
