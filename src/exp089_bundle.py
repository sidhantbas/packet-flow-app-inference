"""Experiment 089: near-miss bundle judged on never-used cv_seeds 2031-2035 (protocol: experiments/089_near_miss_bundle.md,
frozen first).

Usage: python src/exp089_bundle.py --task task1_static|task2_realtime_prefix5 --production --seed N
       python src/exp089_bundle.py --task task1_static|task2_realtime_prefix5 --seed N --ref RUN_ID
B1 (Task 1): 065 R rest-of-flow expert + 087 instagram rule in the 034 base, then the 084 verifiers (34 production columns),
then 036 scoped H1. B2 (Task 2): production + 085 google-vs-mozilla verifier for mozilla calls.
"""
import sys
from datetime import datetime, timezone

import numpy as np

from cv import TASK_FEATURES, evaluate, task1_prefix_rest_features
from exp065_task1_rest_expert import REST, RestExpertMetaGate
from exp085_task2_verifier import verifier as t2_mozilla_verifier
from models import PairVerifiers, ScopedH1, SoftVote, task1_pair_verifiers, task2_model
from runlog import record_run

T1, T2 = "task1_static", "task2_realtime_prefix5"


class RestIGGate(RestExpertMetaGate):
    """065 R; a flow it calls instagram while its two-clerks model calls it non-Meta keeps the two-clerks label (087)."""

    def predict(self, X):
        pred = np.asarray(super().predict(X), dtype=object)
        tc = np.asarray(self.clerks_.predict(X[self.base_cols_]), dtype=object)
        m = (pred == "instagram") & ~np.isin(tc, self.META)
        pred[m] = tc[m]
        return pred


class BundleVerifiers(PairVerifiers):
    """084 verifiers (on the 34 production columns) on top of RestIGGate."""

    def fit(self, X, y):
        y = np.asarray(y)
        self.cols_ = [c for c in X.columns if c not in REST]
        self.base_ = RestIGGate(seed=self.seed, arm="R").fit(X, y)
        self.ver_ = {}
        for call, pair in self.VERIFIERS.items():
            m = np.isin(y, pair)
            self.ver_[call] = SoftVote(seed=self.seed).fit(X.loc[m, self.cols_], y[m])
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        base = np.asarray(self.base_.predict(X), dtype=object)
        p = base.copy()
        for call, ver in self.ver_.items():
            m = base == call
            if m.any():
                p[m] = ver.predict(X.loc[m, self.cols_])
        return p


def bundle_verifiers(seed):
    return BundleVerifiers(seed=seed)


def b1(seed):
    return ScopedH1(base_factory=bundle_verifiers, seed=seed)


ARMS = {T1: (b1, task1_prefix_rest_features, "B1"), T2: (t2_mozilla_verifier, TASK_FEATURES[T2], "B2")}

if __name__ == "__main__":
    args = sys.argv[1:]
    task = args[args.index("--task") + 1]
    seed = int(args[args.index("--seed") + 1])
    assert 2031 <= seed <= 2035, "089 uses only the fresh cv_seeds 2031-2035"
    tag = "T1" if task == T1 else "T2"
    t0 = datetime.now(timezone.utc)
    if "--production" in args:
        # Pinned to the production models when this ran (TASK_MODELS moved to 089 B1 for Task 1 on 2026-10-10).
        f, feats = (task1_pair_verifiers if task == T1 else task2_model), TASK_FEATURES[task]
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("089", f"{tag}_production_s{seed}", res, model_factory=f, feature_fn=feats, reference=None,
                         question=f"{task} production reference on fresh cv_seed {seed} (089)",
                         config={"model": f.__name__, "cv_seed": seed, "features": feats.__name__}, started=t0)
    else:
        f, feats, arm = ARMS[task]
        ref = args[args.index("--ref") + 1]
        res = {task: evaluate(task, feats, f, cv_seed=seed)}
        rid = record_run("089", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                         question=f"{task} 089 bundle {arm} vs production on fresh cv_seed {seed}",
                         config={"arm": arm, "members": "065 R + 087 IG + 084 verifiers + 036 scoped H1" if arm == "B1"
                                 else "production + 085 T2-MG", "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid)
