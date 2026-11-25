"""Experiment 086: drawers (google/youtube sub-types) and courier desks (TCP/UDP) that re-decide the production model's
non-Meta calls (protocol: experiments/086_drawers_courier_desks.md, frozen first).

Usage: python src/exp086_desks.py --stage1                                   (cv_seed 2026 screen, both tasks, all arms)
       python src/exp086_desks.py --task task1_static --arm DR [--seed N --ref RUN_ID]
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.cluster import KMeans
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from models import SoftVote, task1_pair_verifiers, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
NONMETA = ("google", "mozilla", "x", "youtube")
DRAWERS = {"google": 3, "youtube": 2}
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
BASE_OOF = {T1: "results/20261009T220447Z_084_ALL/task1_static/oof.csv",
            T2: "results/20260930T173836Z_014_fi_same_nocw/task2_realtime_prefix5/oof.csv"}
OOF_034 = "results/20261001T173854Z_034_meta_gate/task1_static/oof.csv"


class Desk(BaseEstimator, ClassifierMixin):
    """Re-decides among google, mozilla, x and youtube. arm N0: one balanced SoftVote on the non-Meta rows; DR: as N0 with
    google / youtube split into KMeans drawers (app-level balanced weights); CO: one balanced SoftVote per transport."""

    def __init__(self, arm="N0", seed=0):
        self.arm = arm
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        m = np.isin(y, NONMETA)
        Xn, yn = X.loc[m], y[m]
        if self.arm == "N0":
            self.desks_ = {None: SoftVote(seed=self.seed).fit(Xn, yn)}
        elif self.arm == "DR":
            lab = yn.copy()
            for app, k in DRAWERS.items():
                r = yn == app
                L = np.log1p(Xn.loc[r].astype(float).clip(lower=0)).values
                sd = L.std(0)
                Z = (L - L.mean(0)) / np.where(sd > 0, sd, 1)
                km = KMeans(n_clusters=k, n_init=10, random_state=self.seed).fit(Z)
                lab[r] = [f"{app}#{c}" for c in km.labels_]
            apps, counts = np.unique(yn, return_counts=True)
            w_app = {a: len(yn) / (len(apps) * n) for a, n in zip(apps, counts)}
            w = {d: w_app[d.split("#")[0]] for d in np.unique(lab)}
            self.desks_ = {None: SoftVote(seed=self.seed, class_weight=w).fit(Xn, lab)}
        elif self.arm == "CO":
            self.desks_ = {t: SoftVote(seed=self.seed).fit(Xn.loc[Xn.transport.values == t], yn[Xn.transport.values == t])
                           for t in (0, 1)}
        return self

    def predict(self, X):
        if None in self.desks_:
            p = self.desks_[None].predict(X)
        else:
            p = np.empty(len(X), dtype=object)
            for t, d in self.desks_.items():
                r = X.transport.values == t
                if r.any():
                    p[r] = d.predict(X.loc[r])
        return np.array([str(s).split("#")[0] for s in p], dtype=object)


class DeskModel(BaseEstimator, ClassifierMixin):
    """Production model of `task`; its non-Meta calls are re-decided by a Desk. In Task 1, calls changed by a 084 verifier
    (084 call differs from the wrapped 034 call) are left alone."""

    def __init__(self, task=T1, arm="N0", seed=0):
        self.task = task
        self.arm = arm
        self.seed = seed

    def fit(self, X, y):
        # Pinned to the production models when this ran (TASK_MODELS moved to 089 B1 for Task 1 on 2026-10-10).
        self.base_ = (task1_pair_verifiers if self.task == T1 else task2_model)(self.seed).fit(X, y)
        self.desk_ = Desk(arm=self.arm, seed=self.seed).fit(X, y)
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        p = np.asarray(self.base_.predict(X), dtype=object)
        ok = np.isin(p, NONMETA)
        if self.task == T1:
            ok &= p == np.asarray(self.base_.base_.predict(X), dtype=object)
        if ok.any():
            p[ok] = self.desk_.predict(X.loc[ok])
        return p


def factory(task, arm):
    def f(seed):
        return DeskModel(task=task, arm=arm, seed=seed)
    f.__name__ = f"desk_{arm}"
    return f


def stage1():
    out = {}
    for task in (T1, T2):
        Xr, y = load_task(task)
        X, yv = TASK_FEATURES[task](Xr), np.asarray(y.values, dtype=object)
        splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(X, y))
        oof = pd.read_csv(ROOT / BASE_OOF[task])
        assert (oof.flow_id.values == np.concatenate([Xr.flow_id.values[te] for _, te in splits])).all()
        pp, yt, rep = oof.y_pred.values.astype(object), oof.y_true.values.astype(object), oof.fold.values // 5
        elig = np.isin(pp, NONMETA)
        if task == T1:
            o34 = pd.read_csv(ROOT / OOF_034)
            assert (o34.flow_id.values == oof.flow_id.values).all()
            elig &= pp == o34.y_pred.values.astype(object)
        macro = lambda p: float(np.mean([f1_score(yt[rep == k], p[rep == k], labels=LABS, average="macro") for k in range(10)]))
        base = macro(pp)
        jobs, pos = [], 0
        for i, (tr, te) in enumerate(splits):
            jobs.append((i, tr, te, slice(pos, pos + len(te))))
            pos += len(te)
        for arm in ("N0", "DR", "CO"):
            def fold(i, tr, te, sl):
                o, e = pp[sl].copy(), elig[sl]
                if e.any():
                    o[e] = Desk(arm=arm, seed=i).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te[e]])
                return sl, o
            q = pp.copy()
            for sl, o in Parallel(n_jobs=-1)(delayed(fold)(*j) for j in jobs):
                q[sl] = o
            ch = q != pp
            rem, brk, mq = int((ch & (q == yt)).sum()), int((ch & (pp == yt)).sum()), macro(q)
            out[f"{task}:{arm}"] = {"base_macro": round(base, 4), "macro": round(mq, 4), "delta": round(mq - base, 4),
                                    "changed": int(ch.sum()), "removed": rem, "broken": brk,
                                    "gate": bool(mq > base and rem >= 2 * brk)}
            print(task, arm, out[f"{task}:{arm}"], flush=True)
    d = ROOT / "experiments/086_evidence"
    d.mkdir(exist_ok=True)
    (d / "stage1.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--stage1" in args:
        stage1()
        sys.exit()
    task, arm = args[args.index("--task") + 1], args[args.index("--arm") + 1]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 2026
    ref = args[args.index("--ref") + 1] if "--ref" in args else "champion"
    feats, f = TASK_FEATURES[task], factory(task, arm)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    tag = "T1" if task == T1 else "T2"
    rid = record_run("086", f"{tag}_{arm}" + ("" if seed == 2026 else f"_s{seed}"), res, model_factory=f, feature_fn=feats,
                     reference=ref, question=f"{task} 086 arm {arm}: desk re-decides non-Meta calls; cv_seed {seed}",
                     config={"arm": arm, "drawers": DRAWERS if arm == "DR" else None, "cv_seed": seed,
                             "features": feats.__name__}, started=t0)
    print(rid)
