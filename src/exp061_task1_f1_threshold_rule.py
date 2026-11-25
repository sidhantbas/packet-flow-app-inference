"""Experiment 061: Task 1 decision rule aimed at macro F1 (protocol: experiments/061_task1_f1_threshold_rule.md, frozen first).

Usage: python src/exp061_task1_f1_threshold_rule.py --arm T2|T4 [--seed N --ref RUN_ID]
       python src/exp061_task1_f1_threshold_rule.py --production --seed N   (production reference on a confirmation seed)
Production MetaGate with one change: the final argmax over the gate-weighted probabilities q becomes argmax(q - t), where
t_c = F_c / divisor and F_c is the per-class F1 of production on an inner 5-fold CV of the training fold (nothing searched).
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from cv import TASK_FEATURES, evaluate
from models import TASK_MODELS, MetaGate
from runlog import record_run

TASK = "task1_static"
DIVISORS = {"T2": 2.0, "T4": 4.0}


class ThresholdMetaGate(MetaGate):
    def __init__(self, seed=0, mode="full", divisor=2.0):
        super().__init__(seed=seed, mode=mode)
        self.divisor = divisor

    def fit(self, X, y):
        y = np.asarray(y)
        labels = np.array(sorted(set(y)))
        oof = np.empty(len(y), dtype=object)
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=self.seed).split(X, y):
            oof[te] = MetaGate(seed=self.seed).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        self.inner_f1_ = dict(zip(labels, f1_score(y, oof, labels=labels, average=None, zero_division=0)))
        super().fit(X, y)
        self.t_ = np.array([self.inner_f1_.get(c, 0.0) / self.divisor for c in self.classes_])
        return self

    def predict(self, X):
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = (pw + po) / 2
        g = self.gate_.predict_proba(X)[:, list(self.gate_.classes_).index("meta")]
        meta = np.isin(cls, self.META)
        pm = p[:, meta].sum(axis=1, keepdims=True)
        pr = p[:, ~meta].sum(axis=1, keepdims=True)
        q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
        pred = cls[(q - self.t_).argmax(axis=1)]                      # 061: was cls[q.argmax(axis=1)]
        in_meta = np.isin(pred, self.META)
        fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
        pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
        whole = c.whole_.predict(X)
        w_meta = np.isin(whole, self.META)
        pred[w_meta] = whole[w_meta]
        first = c.whole_.models_[0].predict(X[c.whole_.cols_[0]])
        pred[first == "facebook"] = "facebook"
        return pred


def make_factory(divisor):
    def f(seed):
        return ThresholdMetaGate(seed=seed, divisor=divisor)
    f.__name__ = f"threshold_meta_gate_div{divisor:g}"
    return f


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    sfx = "" if seed == 2026 else f"_s{seed}"
    if "--production" in args:
        f = TASK_MODELS[TASK]
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("061", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 1 production reference on cv_seed {seed} (for 061 confirmation)",
                         config={"model": "task1_meta_gate", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        arm = args[args.index("--arm") + 1]
        f = make_factory(DIVISORS[arm])
        res = {TASK: evaluate(TASK, feats, f, cv_seed=seed)}
        rid = record_run("061", f"{arm}{sfx}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"Task 1 061 arm {arm}: argmax(q - F_inner/{DIVISORS[arm]:g}) vs production; cv_seed {seed}",
                         config={"arm": arm, "divisor": DIVISORS[arm], "cv_seed": seed, "features": feats.__name__,
                                 "inner_cv": "StratifiedKFold(5, shuffle, random_state=model seed)"}, started=t0)
    print(rid)
