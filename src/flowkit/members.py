"""Ensemble members by name, with default settings and Optuna search spaces, plus nested tuning.

Every member exposes fit / predict_proba over a fixed class list, single-threaded (cv.evaluate parallelises folds)."""
import numpy as np
import optuna
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from xgboost import XGBClassifier

optuna.logging.set_verbosity(optuna.logging.WARNING)


class Aligned(BaseEstimator, ClassifierMixin):
    """Wraps a classifier so that labels are encoded as integers and probabilities follow `classes`."""

    def __init__(self, est, classes):
        self.est, self.classes = est, classes

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.seen_ = [c for c in self.classes if c in set(y)]
        self.est.fit(X, np.array([self.seen_.index(v) for v in y]))
        return self

    def predict_proba(self, X):
        P = np.zeros((len(X), len(self.classes)))
        Q = self.est.predict_proba(X)
        for j, c in enumerate(self.seen_):
            P[:, self.classes.index(c)] = Q[:, j]
        return P


def _log1p_nonneg(Z):
    return np.log1p(np.clip(Z, 0, None))


def _log_scaled(est):
    return make_pipeline(FunctionTransformer(_log1p_nonneg), StandardScaler(), est)


def build(name, params, seed):
    p = dict(params)
    if name == "lgbm":
        return LGBMClassifier(random_state=seed, n_jobs=1, verbose=-1, **({"n_estimators": 300} | p))
    if name == "xgb":
        return XGBClassifier(random_state=seed, n_jobs=1, tree_method="hist", verbosity=0, **({"n_estimators": 300} | p))
    if name == "rf":
        return RandomForestClassifier(random_state=seed, n_jobs=1, **({"n_estimators": 300} | p))
    if name == "et":
        return ExtraTreesClassifier(random_state=seed, n_jobs=1, **({"n_estimators": 300} | p))
    if name == "knn_manhattan":
        return _log_scaled(KNeighborsClassifier(metric="manhattan", weights="distance", **({"n_neighbors": 7} | p)))
    raise ValueError(f"unknown member {name!r}")


def space(name, trial):
    if name == "lgbm":
        return {"n_estimators": trial.suggest_int("n_estimators", 100, 600), "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 7, 63), "min_child_samples": trial.suggest_int("min_child_samples", 2, 20),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0), "subsample_freq": 1,
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0)}
    if name == "xgb":
        return {"n_estimators": trial.suggest_int("n_estimators", 100, 600), "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
                "max_depth": trial.suggest_int("max_depth", 2, 8), "min_child_weight": trial.suggest_float("min_child_weight", 0.5, 5.0),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0), "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0)}
    if name in ("rf", "et"):
        return {"max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", 0.5, 1.0]),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5)}
    if name == "knn_manhattan":
        return {"n_neighbors": trial.suggest_int("n_neighbors", 3, 15)}
    raise ValueError(name)


def tune(name, X, y, classes, seed, trials=15, inner=3):
    """Optuna TPE search on inner stratified folds of (X, y), maximising macro F1. Returns the best parameters."""
    y = np.asarray(y, dtype=object)
    folds = list(StratifiedKFold(n_splits=inner, shuffle=True, random_state=seed).split(X, y))

    def objective(trial):
        params = space(name, trial)
        scores = []
        for tr, te in folds:
            m = Aligned(build(name, params, seed), classes).fit(X.iloc[tr], y[tr])
            pred = np.asarray(classes, dtype=object)[m.predict_proba(X.iloc[te]).argmax(axis=1)]
            scores.append(f1_score(y[te], pred, average="macro"))
        return float(np.mean(scores))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=trials)
    best = dict(study.best_params)
    return best | ({"subsample_freq": 1} if name == "lgbm" else {})
