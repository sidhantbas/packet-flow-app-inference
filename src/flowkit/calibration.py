"""Probability calibration. The calibrator is fitted on cross-validated probabilities of the whole training set and the base is
then refitted on all of it (`ensemble=False`), so no training rows are lost to a held-out calibration slice."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold

METHODS = ("none", "sigmoid", "isotonic")


def calibrated(estimator, method, seed, folds=5):
    if method not in METHODS:
        raise ValueError(f"unknown calibration {method!r}; choose from {METHODS}")
    if method == "none":
        return estimator
    return CalibratedClassifierCV(estimator, method=method, ensemble=False,
                                  cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed))
