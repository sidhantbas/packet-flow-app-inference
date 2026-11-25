"""Experiment 087: production Task 1 (084 ALL) whose Meta gate may rescue flows into facebook but not into instagram
(protocol: experiments/087_doorman_protects_instagram.md, frozen first).

Usage: python src/exp087_doorman_ig.py [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, evaluate
from models import MetaGate, PairVerifiers, SoftVote
from runlog import record_run

TASK = "task1_static"


class ProtectIGGate(MetaGate):
    """034 Meta gate; a flow it calls instagram while its two-clerks model calls it non-Meta keeps the two-clerks label."""

    def predict(self, X):
        pred = np.asarray(super().predict(X), dtype=object)
        tc = np.asarray(self.clerks_.predict(X), dtype=object)
        m = (pred == "instagram") & ~np.isin(tc, self.META)
        pred[m] = tc[m]
        return pred


class ProtectIG(PairVerifiers):
    """084 ALL with ProtectIGGate as its base."""

    def fit(self, X, y):
        y = np.asarray(y)
        self.base_ = ProtectIGGate(seed=self.seed).fit(X, y)
        self.ver_ = {}
        for call, pair in self.VERIFIERS.items():
            m = np.isin(y, pair)
            self.ver_[call] = SoftVote(seed=self.seed).fit(X.loc[m], y[m])
        self.classes_ = self.base_.classes_
        return self


def protect_ig(seed):
    return ProtectIG(seed=seed)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats = TASK_FEATURES[TASK]
    t0 = datetime.now(timezone.utc)
    res = {TASK: evaluate(TASK, feats, protect_ig, cv_seed=seed)}
    rid = record_run("087", "IG" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=protect_ig, feature_fn=feats,
                     reference=ref, question=f"Task 1 087: Meta gate rescues into facebook only (084 ALL otherwise); cv_seed {seed}",
                     config={"arm": "IG", "base": "084 ALL", "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
