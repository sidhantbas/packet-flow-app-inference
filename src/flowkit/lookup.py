"""Exact-signature lookup: the label distribution of training flows whose key columns (for example the first-5-packet
opening) are identical. Training rows get leave-one-out values, so a row never sees its own label."""
from collections import Counter

import numpy as np
import pandas as pd


def keys_of(X, cols):
    return X[list(cols)].astype(str).agg("|".join, axis=1).values


class ExactLookup:
    def __init__(self, cols, classes):
        self.cols, self.classes = list(cols), list(classes)

    def fit(self, X, y):
        self.table_ = {}
        for k, lab in zip(keys_of(X, self.cols), np.asarray(y, dtype=object)):
            self.table_.setdefault(k, Counter())[lab] += 1
        return self

    def _frame(self, rows, index):
        cols = [f"lookup_{c}" for c in self.classes] + ["lookup_n"]
        return pd.DataFrame(rows, columns=cols, index=index)

    def transform(self, X, y=None):
        """Fractions per class and the match count; with y (training rows), leave each row's own label out."""
        rows = []
        ys = None if y is None else np.asarray(y, dtype=object)
        for i, k in enumerate(keys_of(X, self.cols)):
            cnt = Counter(self.table_.get(k, Counter()))
            if ys is not None:
                cnt[ys[i]] -= 1
            n = sum(v for v in cnt.values() if v > 0)
            rows.append([cnt.get(c, 0) / n if n else 0.0 for c in self.classes] + [n])
        return self._frame(rows, X.index)
