"""Experiment 088: exam-savvy clerk; labels of a whole batch chosen jointly to maximise expected macro F1, starting from
production's labels (protocol: experiments/088_exam_savvy_clerk.md, frozen first; rules flag before any submission).

Usage: python src/exp088_exam_savvy.py --task task1_static|task2_realtime_prefix5 [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from cv import TASK_FEATURES, evaluate
from models import TwoClerks, task1_pair_verifiers, task2_model
from runlog import record_run

T1 = "task1_static"


def expected_macro_f1(A, N, S):
    return float(np.mean(2 * A / np.clip(N + S, 1e-12, None)))


def ascend(P, y0, classes, max_passes=20):
    """Coordinate ascent on expected macro F1 (ratio of expectations) from labels y0. P: n x K, columns in `classes`."""
    idx = {c: k for k, c in enumerate(classes)}
    lab = np.array([idx[c] for c in y0])
    K = len(classes)
    S = P.sum(axis=0)
    A = np.array([P[lab == k, k].sum() for k in range(K)])
    N = np.array([(lab == k).sum() for k in range(K)], dtype=float)
    cur = expected_macro_f1(A, N, S)
    for _ in range(max_passes):
        changed = False
        for i in range(len(lab)):
            a = lab[i]
            best, best_k = cur, a
            for b in range(K):
                if b == a:
                    continue
                A2, N2 = A.copy(), N.copy()
                A2[a] -= P[i, a]; N2[a] -= 1; A2[b] += P[i, b]; N2[b] += 1
                v = expected_macro_f1(A2, N2, S)
                if v > best + 1e-9:
                    best, best_k = v, b
            if best_k != a:
                A[a] -= P[i, a]; N[a] -= 1; A[best_k] += P[i, best_k]; N[best_k] += 1
                lab[i], cur, changed = best_k, best, True
        if not changed:
            break
    return np.asarray(classes, dtype=object)[lab]


def split_meta(p, cls, r_fb):
    """Give the Meta mass of p to facebook / instagram in the ratio r_fb : 1 - r_fb."""
    fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
    p = p.copy()
    meta = p[:, fb] + p[:, ig]
    p[:, fb], p[:, ig] = meta * r_fb, meta * (1 - r_fb)
    return p


def task1_proba(model, X):
    mg = model.base_  # 034 MetaGate inside 084 ALL
    c, cls = mg.clerks_, np.asarray(mg.classes_)
    pw = c.whole_.predict_proba(X)
    po = c.opening_.predict_proba(X[list(TwoClerks.OPEN_COLS)])
    p = (pw + po) / 2
    g = mg.gate_.predict_proba(X)[:, list(mg.gate_.classes_).index("meta")]
    meta = np.isin(cls, mg.META)
    pm, pr = p[:, meta].sum(1, keepdims=True), p[:, ~meta].sum(1, keepdims=True)
    q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
    fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
    r = pw[:, fb] / np.clip(pw[:, fb] + pw[:, ig], 1e-12, None)
    return split_meta(q, cls, r), cls


def task2_proba(model, X):
    cls = np.asarray(model.classes_)
    p = model.base_.predict_proba(X[model.base_cols_])
    s = model.spec_.predict_proba(X[model.spec_cols_])
    r = s[:, list(model.spec_.classes_).index("facebook")]
    return split_meta(p, cls, r), cls


class ExamSavvy(BaseEstimator, ClassifierMixin):
    def __init__(self, task=T1, seed=0):
        self.task = task
        self.seed = seed

    def fit(self, X, y):
        # Pinned to the production models when this ran (TASK_MODELS moved to 089 B1 for Task 1 on 2026-10-10).
        self.base_ = (task1_pair_verifiers if self.task == T1 else task2_model)(self.seed).fit(X, y)
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        y0 = np.asarray(self.base_.predict(X), dtype=object)
        P, cls = (task1_proba if self.task == T1 else task2_proba)(self.base_, X)
        return ascend(P, y0, cls)


def factory(task):
    def f(seed):
        return ExamSavvy(task=task, seed=seed)
    f.__name__ = "exam_savvy"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    task = args[args.index("--task") + 1]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats, f = TASK_FEATURES[task], factory(task)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    rid = record_run("088", ("T1" if task == T1 else "T2") + "_ES" + ("" if seed == 2026 else f"_s{seed}"), res,
                     model_factory=f, feature_fn=feats, reference=ref,
                     question=f"{task} 088: exam-savvy batch labelling (expected macro F1) from production labels; cv_seed {seed}",
                     config={"arm": "ES", "batch": "held-out fold", "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
