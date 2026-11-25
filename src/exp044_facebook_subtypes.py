"""Experiment 044: Facebook sub-type classes inside the frozen Task 1 production model (BACKLOG Ready #1).

Settings fixed before running (2026-10-08):
- Each training facebook flow is relabelled facebook:<type> using 041's traffic-type rule (Task 1 columns only: transport,
  duration, bytes_up, bytes_down; thresholds unchanged). Other apps keep their label. The rule needs the training label,
  so it is applied to training rows only; prediction never needs a type.
- Every SoftVote inside production (`models.task1_meta_gate`: whole-run experts, opening expert, Meta gate) trains on the
  sub-type labels; predict_proba sums the facebook:* columns back into facebook, so every production rule ("keep facebook",
  Meta decisions, gate) sees the usual 6 classes. The gate trains on meta/rest and is unaffected.
- Class weights: each facebook:* class gets the weight facebook would get under "balanced" on the original 6 labels, so
  facebook's total weight is unchanged and only the split into sub-types differs from production.
- Production code is unchanged: `models.SoftVote` is swapped for the sub-type version only while the wrapper fits.
Decision: rule v2 vs the Task 1 champion on cv_seed 2026; only a pass is confirmed on 2027-2030.
Usage: python src/exp044_facebook_subtypes.py [--seed N --ref RUN_ID]
"""
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

import models
from cv import TASK_FEATURES, evaluate
from runlog import record_run

TASK = "task1_static"
FB = "facebook"


def traffic_type(r):
    """041's rule (src/exp041_capture_feasibility.py), with transport encoded as udp = 1 by cv.basic_features."""
    if r.transport == 0:
        return "TCP keep-alive" if r.duration >= 100 else "short TCP"
    if r.duration < 1:
        return "short QUIC fetch"
    if r.duration < 60:
        return "QUIC burst"
    if r.bytes_down >= 1e6:
        return "QUIC media download"
    if r.bytes_up >= 250e3 and r.bytes_up > r.bytes_down:
        return "QUIC upload-heavy"
    return "slow QUIC trickle"


class SubtypeSoftVote(models.SoftVote):
    """SoftVote trained on facebook:<type> labels, reporting the usual classes (sub-type probabilities summed)."""

    types = None  # pd.Series: traffic type per row index of the current training set, set by Subtyped.fit

    def fit(self, X, y):
        y = np.asarray(y).astype(object)
        fb = y == FB
        if not fb.any():  # e.g. the Meta gate (meta/rest labels)
            return super().fit(X, y)
        missing = ~X.index[fb].isin(self.types.index)
        assert not missing.any(), "row index lost inside production; types cannot be looked up"
        sub = y.copy()
        sub[fb] = FB + ":" + self.types.loc[X.index[fb]].values
        if self.class_weight == "balanced":  # facebook's original weight, shared by every sub-type
            classes, counts = np.unique(y, return_counts=True)
            w = {c: len(y) / (len(classes) * n) for c, n in zip(classes, counts)}
            cw = {c: w[FB if c.startswith(FB + ":") else c] for c in np.unique(sub)}
        else:
            cw = self.class_weight
        self.models_ = [f(self.seed, class_weight=cw).fit(X, sub) for f in self.member_factories]
        sub_classes = self.models_[0].classes_
        self.classes_ = np.array(sorted({FB if c.startswith(FB + ":") else c for c in sub_classes}))
        self.merge_ = np.array([[(FB if s.startswith(FB + ":") else s) == c for c in self.classes_]
                                for s in sub_classes], dtype=float)
        return self

    def predict_proba(self, X):
        p = np.mean([m.predict_proba(X) for m in self.models_], axis=0)
        return p @ self.merge_ if hasattr(self, "merge_") else p


class Subtyped(BaseEstimator, ClassifierMixin):
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        SubtypeSoftVote.types = X.apply(traffic_type, axis=1)
        original = models.SoftVote
        models.SoftVote = SubtypeSoftVote
        try:
            self.model_ = models.TASK_MODELS[TASK](self.seed).fit(X, y)
        finally:
            models.SoftVote = original
        self.classes_ = self.model_.classes_
        return self

    def predict(self, X):
        return self.model_.predict(X)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    if "--types" in args:  # show the sub-type counts of the labelled facebook flows, then stop
        from cv import load_task
        Xr, y = load_task(TASK)
        X = TASK_FEATURES[TASK](Xr)
        print(X[y.values == FB].apply(traffic_type, axis=1).value_counts().to_string())
        sys.exit()
    t0 = datetime.now(timezone.utc)
    f = lambda s: Subtyped(seed=s)
    res = {TASK: evaluate(TASK, TASK_FEATURES[TASK], f, cv_seed=seed)}
    record_run("044", "fb_subtypes" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f,
               feature_fn=TASK_FEATURES[TASK], reference=ref,
               question=f"Task 1: does training production on facebook sub-type classes (041 types) beat it? cv_seed {seed}",
               config={"model": "Subtyped(task1_meta_gate)", "cv_seed": seed,
                       "features": TASK_FEATURES[TASK].__name__}, started=t0)
