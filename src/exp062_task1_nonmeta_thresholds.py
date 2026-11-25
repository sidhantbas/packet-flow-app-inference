"""Experiment 062: Task 1 F/2 thresholds among the non-Meta apps only (protocol: experiments/062_task1_nonmeta_thresholds.md,
frozen first; post hoc from 061, so BETTER on all five seeds is required).

Usage: python src/exp062_task1_nonmeta_thresholds.py [--seed N --ref RUN_ID]
       python src/exp062_task1_nonmeta_thresholds.py --production --seed N   (production reference on a confirmation seed)
Thresholds come from 061's ThresholdMetaGate.fit (inner 5-fold CV, t_c = F_c / 2). Only flows whose production argmax is a
non-Meta class are re-decided, and only among the non-Meta classes.
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, evaluate
from exp061_task1_f1_threshold_rule import ThresholdMetaGate
from models import TASK_MODELS
from runlog import record_run

TASK = "task1_static"


class NonMetaThresholdMetaGate(ThresholdMetaGate):
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
        pred = cls[q.argmax(axis=1)]
        rest = ~np.isin(pred, self.META)                              # 062: re-decide only non-Meta calls,
        if rest.any():                                                # and only among the non-Meta classes
            nm = np.flatnonzero(~meta)
            pred[rest] = cls[nm][(q[np.ix_(rest, nm)] - self.t_[nm]).argmax(axis=1)]
        in_meta = np.isin(pred, self.META)
        fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
        pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
        whole = c.whole_.predict(X)
        w_meta = np.isin(whole, self.META)
        pred[w_meta] = whole[w_meta]
        first = c.whole_.models_[0].predict(X[c.whole_.cols_[0]])
        pred[first == "facebook"] = "facebook"
        return pred


def nonmeta_model(seed):
    return NonMetaThresholdMetaGate(seed=seed, divisor=2.0)


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
        rid = record_run("062", f"production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"Task 1 production reference on cv_seed {seed} (for 062 confirmation)",
                         config={"model": "task1_meta_gate", "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        res = {TASK: evaluate(TASK, feats, nonmeta_model, cv_seed=seed)}
        rid = record_run("062", f"N2{sfx}", res, model_factory=nonmeta_model, feature_fn=feats, reference=ref,
                         question=f"Task 1 062: F/2 thresholds among non-Meta apps only vs production; cv_seed {seed}",
                         config={"arm": "N2", "divisor": 2.0, "cv_seed": seed, "features": feats.__name__,
                                 "origin": "post hoc from 061; BETTER on all five seeds required"}, started=t0)
    print(rid)
