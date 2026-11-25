"""Experiment 078: TabPFN v2 (local, CPU) as an extra expert in the Task 1 production model; CHECK ONLY (protocol:
experiments/078_tabpfn_expert_check.md). The team rule "no pretrained models" is unchanged; nothing here enters production.

Usage: python src/exp078_tabpfn_expert_check.py [--seed N --ref RUN_ID]
p = (whole-flow + opening + TabPFN) / 3 inside MetaGate.predict; all later production rules unchanged.
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, evaluate
from models import MetaGate, tabpfn
from runlog import record_run

TASK = "task1_static"


class TabPFNExpertMetaGate(MetaGate):
    def fit(self, X, y):
        super().fit(X, y)
        self.pfn_ = tabpfn(self.seed).fit(X, np.asarray(y))
        assert list(self.pfn_.classes_) == list(self.classes_)
        return self

    def predict(self, X):
        c = self.clerks_
        cls = np.asarray(self.classes_)
        pw = c.whole_.predict_proba(X)
        po = c.opening_.predict_proba(X[list(c.OPEN_COLS)])
        p = (pw + po + self.pfn_.predict_proba(X)) / 3                 # 078: was (pw + po) / 2
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


def pfn_expert(seed):
    return TabPFNExpertMetaGate(seed=seed)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, pfn_expert, cv_seed=seed)}
    rid = record_run("078", "TP" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=pfn_expert, feature_fn=feats,
                     reference=ref, question=f"Task 1 078 (CHECK ONLY): TabPFN v2 as an extra expert; cv_seed {seed}",
                     config={"tabpfn": "9.0.0, model v2, local CPU", "cv_seed": seed, "features": feats.__name__,
                             "rule_status": "pretrained models excluded by team rule; check only (user 2026-10-09)"}, started=t0)
    print(rid)
