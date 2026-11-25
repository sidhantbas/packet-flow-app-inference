"""Phase 5: self-training with unlabelled rows and monotonic constraints in the Task 1 pairwise verifiers (PROTOCOL.md)."""
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import f1_score

from common import LABS, PROD, T1, TASK_FEATURES, TASKS, SoftVote, data, paired, run, save, splits
from make_submission import load_test
from models import BundleVerifiers, RestIGMetaGate, REST_COLS, ScopedH1, Task1Bundle, et, lgbm, rf

THRESH = 0.9


def st_fold(task, X, y, Xtest, i, tr, te):
    sv = SoftVote(seed=i).fit(X.iloc[tr], y[tr])
    pool = pd.concat([X.iloc[te], Xtest], ignore_index=True)
    P = sv.predict_proba(pool)
    keep = P.max(axis=1) >= THRESH
    Xa = pd.concat([X.iloc[tr].reset_index(drop=True), pool.loc[keep].reset_index(drop=True)], ignore_index=True)
    ya = np.concatenate([y[tr], sv.classes_[P[keep].argmax(axis=1)]])
    m = PROD[task](i).fit(Xa, ya)
    return i, f1_score(y[te], m.predict(X.iloc[te]), average="macro"), int(keep.sum())


# Monotonic constraints (assumed; listed in PROTOCOL.md for the user to verify). Binary LightGBM: +1 = increasing in the
# probability of the second class in sorted order (instagram in google/instagram, x in google/x).
MONO = {"x": {"transport": -1, "p5_mean_pkt_size_up": -1},
        "instagram": {"burst_count": 1, "bytes_down": 1}}


class MonoSoftVote(SoftVote):
    def __init__(self, seed=0, class_weight="balanced", mono=None):
        super().__init__(seed=seed, class_weight=class_weight)
        self.mono = mono

    def fit(self, X, y):
        cons = [int((self.mono or {}).get(c, 0)) for c in X.columns]
        L = lgbm(self.seed, class_weight=self.class_weight)
        L.set_params(monotone_constraints=cons, monotone_constraints_method="basic")
        self.models_ = [rf(self.seed, class_weight=self.class_weight).fit(X, y),
                        et(self.seed, class_weight=self.class_weight).fit(X, y), L.fit(X, y)]
        self.classes_ = self.models_[0].classes_
        return self


class MonoVerifiers(BundleVerifiers):
    def fit(self, X, y):
        y = np.asarray(y)
        self.cols_ = [c for c in X.columns if c not in REST_COLS]
        self.base_ = RestIGMetaGate(seed=self.seed).fit(X, y)
        self.ver_ = {}
        for call, pair in self.VERIFIERS.items():
            m = np.isin(y, pair)
            self.ver_[call] = MonoSoftVote(seed=self.seed, mono=MONO[call]).fit(X.loc[m, self.cols_], y[m])
        self.classes_ = self.base_.classes_
        return self


class MonoBundle(Task1Bundle):
    def fit(self, X, y):
        self.model_ = ScopedH1(base_factory=lambda s: MonoVerifiers(seed=s), seed=self.seed).fit(self._with_rest(X), y)
        self.classes_ = self.model_.classes_
        return self


def mono_bundle(seed):
    return MonoBundle(seed=seed)


def main():
    out = {"self_training": {"threshold": THRESH, "pool": "held-out fold features + 81 test feature rows (no labels)"},
           "monotonic": {"constraints_assumed": MONO, "scope": "LightGBM member of the two Task 1 pairwise verifiers only"}}
    for task in TASKS:
        _, X, y = data(task)
        Xtest = TASK_FEATURES[task](load_test(task)).reset_index(drop=True)[X.columns]
        R = sorted(Parallel(n_jobs=-1)(delayed(st_fold)(task, X, y, Xtest, i, tr, te) for i, (tr, te) in enumerate(splits(task))))
        out["self_training"][task] = {**paired(task, np.array([r[1] for r in R])),
                                      "pseudo_labelled_rows_mean": float(np.mean([r[2] for r in R]))}
        print("self-training", task, out["self_training"][task], flush=True)
    out["monotonic"][T1] = paired(T1, run(T1, factory=mono_bundle))
    print("monotonic", out["monotonic"][T1], flush=True)
    save("phase5_semi_constraints.json", out)


if __name__ == "__main__":
    main()
