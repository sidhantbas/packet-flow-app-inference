"""Experiment 038: is there unused information? Task 2 outputs as a signal for Task 1.

Command: .venv/bin/python src/exp038_task2_signal.py
  2. Overlap between the tasks (IDs, splits, start_rel, transport, server_port, labels) and agreement of the two production
     models' held-out predictions on the same folds (logged runs 034 for Task 1 and 014 for Task 2, cv_seed 2026), split by who
     is right on facebook/instagram and google/youtube; disagreement on the submitted test predictions.
  3. Two uses of Task 2 outputs in Task 1, fixed before running:
     (a) features: one-hot Task 2 production label added to the Task 1 input. Training rows get inner 5-fold out-of-fold Task 2
         labels (fitted inside the outer training fold); held-out rows get the label of a Task 2 model fitted on the outer
         training fold. Task 2 is fitted on the 12 Task 2 columns of the same flows (from the Task 2 files).
     (b) tiebreaker: where the production gate-weighted probabilities have a top-two margin < 0.1 and the Task 2 label is one of
         those two classes and differs from the production label, use the Task 2 label. Task 2 labels come from the logged
         Task 2 run on the same folds (fitted on the outer training fold only).
     Both compared with production under rule v2; confirmation on cv_seeds 2027/2028 only after a pass at 2026.
"""
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold

from cv import DATA, TASK_FEATURES, evaluate, load_task
from models import TASK_MODELS, TwoClerks, task2_model
from runlog import ROOT, load_index, load_oof, record_run

T1, T2 = "task1_static", "task2_realtime_prefix5"
X_raw, y = load_task(T1)
XF = TASK_FEATURES[T1](X_raw)
FID, Y = X_raw.flow_id.values, y.values
LABELS = sorted(set(Y))
OPEN = list(TwoClerks.OPEN_COLS)
META = ("facebook", "instagram")


def run_id(suffix):
    return next(e["run_id"] for e in load_index() if e["run_id"].endswith(suffix))


class Task2AsFeatures(BaseEstimator, ClassifierMixin):
    """Production Task 1 model on its input + one-hot Task 2 labels (inner out-of-fold for the training rows)."""

    def __init__(self, seed=0):
        self.seed = seed

    def _onehot(self, labels):
        return pd.DataFrame({f"t2_{c}": (np.asarray(labels) == c).astype(int) for c in LABELS})

    def fit(self, X, y):
        y = np.asarray(y)
        X = X.reset_index(drop=True)
        inner = np.empty(len(y), dtype=object)
        for tr, va in StratifiedKFold(5, shuffle=True, random_state=self.seed).split(X, y):
            inner[va] = task2_model(self.seed).fit(X.loc[tr, OPEN], y[tr]).predict(X.loc[va, OPEN])
        self.t2_ = task2_model(self.seed).fit(X[OPEN], y)
        self.model_ = TASK_MODELS[T1](self.seed).fit(pd.concat([X, self._onehot(inner)], axis=1), y)
        self.classes_ = self.model_.classes_
        return self

    def predict(self, X):
        X = X.reset_index(drop=True)
        return self.model_.predict(pd.concat([X, self._onehot(self.t2_.predict(X[OPEN]))], axis=1))


def production_margins(i, tr, te):
    m = TASK_MODELS[T1](i).fit(XF.iloc[tr], y.iloc[tr])
    Xt = XF.iloc[te]
    pred = np.asarray(m.predict(Xt))
    c, cls = m.clerks_, np.asarray(m.classes_)
    p = (c.whole_.predict_proba(Xt) + c.opening_.predict_proba(Xt[OPEN])) / 2
    g = m.gate_.predict_proba(Xt)[:, list(m.gate_.classes_).index("meta")]
    meta = np.isin(cls, m.META)
    q = np.where(meta, g[:, None] * p / p[:, meta].sum(1, keepdims=True), (1 - g[:, None]) * p / p[:, ~meta].sum(1, keepdims=True))
    o = np.argsort(-q, 1)
    return pd.DataFrame({"fold": i, "flow_id": FID[te], "y_true": Y[te], "y_pred": pred, "top1": cls[o[:, 0]], "top2": cls[o[:, 1]],
                         "margin": q[np.arange(len(te)), o[:, 0]] - q[np.arange(len(te)), o[:, 1]]})


def as_result(o, seed):
    folds = sorted(o.fold.unique())
    macro = np.array([f1_score(o[o.fold == i].y_true, o[o.fold == i].y_pred, average="macro") for i in folds])
    pc = np.array([f1_score(o[o.fold == i].y_true, o[o.fold == i].y_pred, average=None, labels=LABELS, zero_division=0) for i in folds])
    return {"task": T1, "n_flows": len(Y), "features": list(XF.columns), "labels": LABELS, "fold_macro": macro, "fold_per_class": pc,
            "y_true": o.y_true.values, "y_pred": o.y_pred.values, "flow_id": o.flow_id.values, "fold": o.fold.values,
            "fold_seconds": np.zeros(len(folds)), "extra_data": [],
            "cv": {"n_splits": 5, "n_repeats": 10, "cv_seed": seed, "resample": None, "fold_jobs": None, "splits": "RepeatedStratifiedKFold"},
            "macro_mean": macro.mean(), "macro_std": macro.std(ddof=1), "repeat_std": macro.reshape(10, 5).mean(1).std(ddof=1),
            "per_class_mean": dict(zip(LABELS, pc.mean(0))), "per_class_std": dict(zip(LABELS, pc.std(0, ddof=1)))}


def tiebreak(seed, t1_ref, t2_ref):
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(XF, y))
    o = pd.concat(Parallel(n_jobs=-1)(delayed(production_margins)(i, tr, te) for i, (tr, te) in enumerate(splits)), ignore_index=True)
    logged = load_oof(t1_ref, T1).sort_values(["fold", "flow_id"]).y_pred.values
    assert (o.sort_values(["fold", "flow_id"]).y_pred.values == logged).all(), "production does not reproduce"
    t2 = load_oof(t2_ref, T2).rename(columns={"y_pred": "t2"})[["fold", "flow_id", "t2"]]
    o = o.merge(t2, on=["fold", "flow_id"], how="left")
    assert o.t2.notna().all(), "Task 2 folds differ"
    new = o.copy()
    use = (o.margin < 0.1) & (o.t2 != o.y_pred) & ((o.t2 == o.top1) | (o.t2 == o.top2))
    new.loc[use, "y_pred"] = o.loc[use, "t2"]
    return o, new, int(use.sum())


def main():
    # 2. overlap and agreement
    F = {s: pd.read_csv(DATA / T1 / f"{s}_features.csv") for s in ("train", "validation", "test")}
    P = {s: pd.read_csv(DATA / T2 / f"{s}_features.csv") for s in ("train", "validation", "test")}
    for s in F:
        a, b = F[s].set_index("flow_id"), P[s].set_index("flow_id")
        print(f"{s}: same flow_ids {set(a.index) == set(b.index)}; split, start_rel, transport, server_port identical: "
              f"{all((a[c] == b.loc[a.index, c]).all() for c in ('split', 'start_rel', 'transport', 'server_port'))}")
    for s in ("train", "validation"):
        l1, l2 = pd.read_csv(DATA / T1 / f"{s}_labels.csv").set_index("flow_id").app, pd.read_csv(DATA / T2 / f"{s}_labels.csv").set_index("flow_id").app
        print(f"{s}: labels identical across tasks: {(l1 == l2.loc[l1.index]).all()}")
    o1 = load_oof(run_id("034_meta_gate"), T1)
    o2 = load_oof(run_id("014_fi_same_nocw"), T2)
    m = o1.merge(o2, on=["fold", "flow_id", "y_true"], suffixes=("_t1", "_t2"))
    assert len(m) == len(o1) == len(o2), "folds differ between tasks"
    dis = m[m.y_pred_t1 != m.y_pred_t2]
    print(f"\nheld-out predictions (cv_seed 2026): {len(m)}; tasks disagree on {len(dis)} ({len(dis) / len(m):.1%})")
    print(f"  when they disagree: Task 1 right {int((dis.y_pred_t1 == dis.y_true).sum())}, Task 2 right {int((dis.y_pred_t2 == dis.y_true).sum())}, both wrong {int(((dis.y_pred_t1 != dis.y_true) & (dis.y_pred_t2 != dis.y_true)).sum())}")
    for pair in (("facebook", "instagram"), ("google", "youtube")):
        d = dis[dis.y_true.isin(pair)]
        print(f"  true {'/'.join(pair)}: disagreements {len(d)}; Task 1 right {int((d.y_pred_t1 == d.y_true).sum())}, Task 2 right {int((d.y_pred_t2 == d.y_true).sum())}")
        for c in pair:
            r = m[m.y_true == c]
            print(f"    {c}: Task 1 recall {(r.y_pred_t1 == c).mean():.3f}, Task 2 recall {(r.y_pred_t2 == c).mean():.3f}")
    sub = json.load(open(ROOT / "submissions/submission.json"))
    td = [f for f in sub[T1] if sub[T1][f] != sub[T2][f]]
    print(f"\ntest: Task 1 and Task 2 submitted labels differ on {len(td)} of 81 flows")

    # 3a. Task 2 outputs as features
    t0 = datetime.now(timezone.utc)
    f = lambda s: Task2AsFeatures(seed=s)
    record_run("038", "t2_as_features", {T1: evaluate(T1, TASK_FEATURES[T1], f)}, model_factory=f, feature_fn=TASK_FEATURES[T1],
               question="Task 1 production + one-hot Task 2 labels (inner OOF), cv_seed 2026", config={"model": "Task2AsFeatures"}, started=t0)
    # 3b. Task 2 as a tiebreaker
    base, new, n = tiebreak(2026, run_id("034_meta_gate"), run_id("014_fi_same_nocw"))
    print(f"\ntiebreaker (cv_seed 2026): applied to {n} held-out predictions")
    t0 = datetime.now(timezone.utc)
    record_run("038", "t2_tiebreak", {T1: as_result(new, 2026)}, reference=run_id("034_meta_gate"),
               question="Task 1 production with Task 2 as tiebreaker (margin < 0.1), cv_seed 2026",
               config={"rule": "t2 tiebreak, margin < 0.1, t2 in top two"}, started=t0)


if __name__ == "__main__":
    main()
