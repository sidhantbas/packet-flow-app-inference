"""DecisionPipeline: base model -> optional calibration -> labels by argmax or by count-constrained assignment.

counts="shares"    : each batch gets the training class shares x batch size (compliant).
counts="disclosed" : each batch gets its own true class counts. Simulation only, for cross-validation: the true labels are looked
                     up by row index in `disclosed_labels` (train + validation labels). It refuses to run without them, so it can
                     never be applied to the test set.
"""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from .bases import make_base
from .calibration import calibrated
from .counts import KINDS, label_counts, quota_assign, share_counts


class DecisionPipeline(BaseEstimator, ClassifierMixin):
    def __init__(self, base="softvote", calibration="none", counts="none", seed=0, disclosed_labels=None):
        self.base, self.calibration, self.counts, self.seed = base, calibration, counts, seed
        self.disclosed_labels = disclosed_labels

    def fit(self, X, y):
        if self.counts not in KINDS:
            raise ValueError(f"unknown counts {self.counts!r}; choose from {KINDS}")
        y = np.asarray(y, dtype=object)
        self.model_ = calibrated(make_base(self.base, self.seed), self.calibration, self.seed).fit(X, y)
        self.classes_ = np.asarray(self.model_.classes_, dtype=object)
        self.shares_ = {c: n / len(y) for c, n in label_counts(y).items()}
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X)

    def predict(self, X):
        if self.counts == "none":
            if self.calibration == "none":  # the base's own decision (e.g. 014 keeps its facebook/instagram stage)
                return np.asarray(self.model_.predict(X), dtype=object)
            return self.classes_[self.predict_proba(X).argmax(axis=1)]
        P = self.predict_proba(X)
        if self.counts == "shares":
            counts = share_counts(list(self.classes_), self.shares_, len(X))
        else:
            if self.disclosed_labels is None:
                raise ValueError("counts='disclosed' needs disclosed_labels (cross-validation simulation only)")
            counts = label_counts(np.asarray(self.disclosed_labels, dtype=object)[np.asarray(X.index)])
        return quota_assign(P, list(self.classes_), counts)


def from_spec(spec, seed=0, disclosed_labels=None):
    """Build from "base=softvote,cal=sigmoid,counts=shares" (keys: base, cal, counts)."""
    kw = dict(part.split("=", 1) for part in spec.split(",") if part)
    unknown = set(kw) - {"base", "cal", "counts"}
    if unknown:
        raise ValueError(f"unknown spec keys {sorted(unknown)}")
    return DecisionPipeline(base=kw.get("base", "softvote"), calibration=kw.get("cal", "none"), counts=kw.get("counts", "none"),
                            seed=seed, disclosed_labels=disclosed_labels)
