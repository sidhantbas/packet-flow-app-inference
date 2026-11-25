"""Experiment 064: a third, different expert inside the Task 1 production model (protocol: experiments/064_task1_third_expert.md,
frozen first).

Usage: python src/exp064_task1_third_expert.py --arm KNN|LR|KL [--seed N --ref RUN_ID]
Production MetaGate with one change: the class probabilities p are the mean of the whole-flow expert, the opening expert
and the extra expert(s) (kNN and/or logistic regression on all 34 columns, log1p + standardised). All later rules unchanged.
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, evaluate
from models import MetaGate, knn, logreg
from runlog import record_run

TASK = "task1_static"
EXTRA = {"KNN": (knn,), "LR": (logreg,), "KL": (knn, logreg)}


class ThirdExpertMetaGate(MetaGate):
    def __init__(self, seed=0, mode="full", extra=("KNN",)):
        super().__init__(seed=seed, mode=mode)
        self.extra = extra

    def fit(self, X, y):
        super().fit(X, y)
        self.extra_ = [f(self.seed).fit(X, np.asarray(y)) for arm in self.extra for f in EXTRA[arm]]
        assert all(list(m.classes_) == list(self.classes_) for m in self.extra_)
        return self

    def predict(self, X):
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = np.mean([pw, po] + [m.predict_proba(X) for m in self.extra_], axis=0)   # 064: was (pw + po) / 2
        g = self.gate_.predict_proba(X)[:, list(self.gate_.classes_).index("meta")]
        meta = np.isin(cls, self.META)
        pm = p[:, meta].sum(axis=1, keepdims=True)
        pr = p[:, ~meta].sum(axis=1, keepdims=True)
        q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
        pred = cls[q.argmax(axis=1)]
        in_meta = np.isin(pred, self.META)
        fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
        pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
        whole = c.whole_.predict(X)
        w_meta = np.isin(whole, self.META)
        pred[w_meta] = whole[w_meta]
        first = c.whole_.models_[0].predict(X[c.whole_.cols_[0]])
        pred[first == "facebook"] = "facebook"
        return pred


def make_factory(arm):
    def f(seed):
        return ThirdExpertMetaGate(seed=seed, extra=(arm,))
    f.__name__ = f"third_expert_{arm.lower()}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    arm = args[args.index("--arm") + 1]
    feats, f = TASK_FEATURES[TASK], make_factory(arm)
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
    rid = record_run("064", f"{arm}" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats,
                     reference=ref, question=f"Task 1 064 arm {arm}: third expert inside the Meta-gate model; cv_seed {seed}",
                     config={"arm": arm, "experts": ["whole-flow", "opening"] + [g.__name__ for g in EXTRA[arm]],
                             "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
