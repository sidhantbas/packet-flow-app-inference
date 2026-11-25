"""Experiment 075: 065 R (rest-of-flow expert) + 062 non-Meta F/2 thresholds (protocol:
experiments/075_rest_expert_plus_nonmeta_thresholds.md, frozen first).

Usage: python src/exp075_rest_expert_plus_nonmeta_thresholds.py [--seed N --ref RUN_ID]
Thresholds t_c = F_c / 2 from an inner 5-fold CV of the 065 R model on the training fold; only flows whose base label is
non-Meta are re-decided, among the four non-Meta classes.
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from cv import evaluate, task1_prefix_rest_features
from exp065_task1_rest_expert import ARMS, RestExpertMetaGate
from runlog import record_run

TASK = "task1_static"


class RestPlusNonMeta(RestExpertMetaGate):
    def __init__(self, seed=0, mode="full", arm="R", divisor=2.0):
        super().__init__(seed=seed, mode=mode, arm=arm)
        self.divisor = divisor

    def fit(self, X, y):
        y = np.asarray(y)
        labels = np.array(sorted(set(y)))
        oof = np.empty(len(y), dtype=object)
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=self.seed).split(X, y):
            oof[te] = RestExpertMetaGate(seed=self.seed, arm=self.arm).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        self.inner_f1_ = dict(zip(labels, f1_score(y, oof, labels=labels, average=None, zero_division=0)))
        super().fit(X, y)
        self.t_ = np.array([self.inner_f1_.get(c, 0.0) / self.divisor for c in self.classes_])
        return self

    def predict(self, X):
        Xr, X = X[ARMS[self.arm]], X[self.base_cols_]
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = (pw + po + self.rest_.predict_proba(Xr)) / 3
        g = self.gate_.predict_proba(X)[:, list(self.gate_.classes_).index("meta")]
        meta = np.isin(cls, self.META)
        pm = p[:, meta].sum(axis=1, keepdims=True)
        pr = p[:, ~meta].sum(axis=1, keepdims=True)
        q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
        pred = cls[q.argmax(axis=1)]
        rest = ~np.isin(pred, self.META)                              # 062 rule on top of 065 R
        if rest.any():
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


def combo_model(seed):
    return RestPlusNonMeta(seed=seed)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = task1_prefix_rest_features
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, combo_model, cv_seed=seed)}
    rid = record_run("075", "RN2" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=combo_model, feature_fn=feats,
                     reference=ref, question=f"Task 1 075: 065 R + 062 non-Meta F/2 thresholds vs production; cv_seed {seed}",
                     config={"base": "065 R", "decision": "062 non-Meta F/2 (inner CV of 065 R)", "cv_seed": seed,
                             "features": feats.__name__}, started=t0)
    print(rid)
