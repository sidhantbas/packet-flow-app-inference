"""Experiment 112: leave-one-layer-out audit of production Task 1 (100 FB) and Task 2 (014)
(protocol: experiments/112_layer_audit.md).

Usage (from the repository root):
  .venv/bin/python src/exp112_layer_audit.py --smoke
  .venv/bin/python src/exp112_layer_audit.py --all          # every arm on seeds 2151-2155
  .venv/bin/python src/exp112_layer_audit.py --arm -087 --seed 2151
  .venv/bin/python src/exp112_layer_audit.py --analyse
  .venv/bin/python src/exp112_layer_audit.py --test-effect
Runs go to results/<stamp>_112_<arm>_s<seed>/ (arm names without the minus sign: drop028 ...); evidence to
experiments/112_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from models import (REST_COLS, PairVerifiers, SoftVote, TwoClerks, rest_from_columns, task1_cross_task, task1_model,
                    task2_model)
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
SEEDS = (2151, 2152, 2153, 2154, 2155)
LAYERS = ("028", "034", "065", "087", "084", "036", "100")
T1_ARMS = ("P",) + tuple(f"drop{l}" for l in LAYERS)
T2_ARMS = ("P2", "drop014")
META = ("facebook", "instagram")
OPEN = list(TwoClerks.OPEN_COLS)
EVIDENCE = ROOT / "experiments/112_evidence"


class Task1Configurable(BaseEstimator, ClassifierMixin):
    """Rebuild of models.task1_cross_task with one optional layer dropped (drop = "" keeps every layer)."""

    def __init__(self, seed=0, drop=""):
        self.seed, self.drop = seed, drop

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        s, d = self.seed, self.drop
        Xr = pd.concat([X, rest_from_columns(X)], axis=1)
        self.cols_ = list(X.columns)
        self.whole_ = task1_model(s).fit(X, y)
        self.opening_ = None if d == "028" else SoftVote(seed=s).fit(X[OPEN], y)
        self.gate_ = None if d == "034" else SoftVote(seed=s).fit(X, np.where(np.isin(y, META), "meta", "rest"))
        self.rest_ = None if d == "065" else SoftVote(seed=s).fit(Xr[REST_COLS], y)
        self.ver_ = {} if d == "084" else {call: SoftVote(seed=s).fit(Xr.loc[np.isin(y, pair), self.cols_], y[np.isin(y, pair)])
                                         for call, pair in PairVerifiers.VERIFIERS.items()}
        if d != "036":
            t = pd.DataFrame({"k": self._keys(Xr), "y": y}).groupby("k").y.agg(lambda v: v.unique())
            self.table_ = {k: v[0] for k, v in t.items() if len(v) == 1}
        self.t2_ = None if d == "100" else task2_model(s).fit(self._opening(X), y)
        self.classes_ = self.whole_.classes_
        return self

    @staticmethod
    def _keys(Xr):
        return Xr[OPEN].astype(str).agg("|".join, axis=1).values

    @staticmethod
    def _opening(X):
        return X[OPEN].set_axis([c[len("p5_"):] for c in OPEN], axis=1)

    def predict(self, X):
        Xr = pd.concat([X, rest_from_columns(X)], axis=1)
        X34 = Xr[self.cols_]
        cls = np.asarray(self.classes_)
        w = self.whole_
        pw = w.predict_proba(X34)
        whole = w.predict(X34)
        first = w.models_[0].predict(X34[w.cols_[0]])
        po = self.opening_.predict_proba(X34[OPEN]) if self.opening_ is not None else None
        # two clerks (028); without the opening expert it reduces to the whole-run expert
        p_tc = (pw + po) / 2 if po is not None else pw
        tc = cls[p_tc.argmax(axis=1)]
        m = np.isin(tc, META) | np.isin(whole, META)
        tc[m] = whole[m]
        tc[first == "facebook"] = "facebook"
        # gate stage (034 gate, 065 rest-of-flow expert, 087 rule), as models.RestIGMetaGate
        experts = [pw] + ([po] if po is not None else []) + ([self.rest_.predict_proba(Xr[REST_COLS])] if self.rest_ else [])
        p = sum(experts) / len(experts)
        fb, ig = list(cls).index("facebook"), list(cls).index("instagram")
        if self.gate_ is not None:
            g = self.gate_.predict_proba(X34)[:, list(self.gate_.classes_).index("meta")]
            meta = np.isin(cls, META)
            pm = p[:, meta].sum(axis=1, keepdims=True)
            pr = p[:, ~meta].sum(axis=1, keepdims=True)
            q = np.where(meta, g[:, None] * p / np.clip(pm, 1e-12, None), (1 - g[:, None]) * p / np.clip(pr, 1e-12, None))
            pred = cls[q.argmax(axis=1)]
            in_meta = np.isin(pred, META)
            pred[in_meta] = np.where(pw[in_meta, fb] >= pw[in_meta, ig], "facebook", "instagram")
        else:
            pred = cls[p.argmax(axis=1)]
        w_meta = np.isin(whole, META)
        pred[w_meta] = whole[w_meta]
        pred[first == "facebook"] = "facebook"
        pred = np.asarray(pred, dtype=object)
        if self.drop != "087":
            m = (pred == "instagram") & ~np.isin(tc, META)
            pred[m] = np.asarray(tc, dtype=object)[m]
        # 084 verifiers act on the gate stage's original calls
        base = pred.copy()
        for call, ver in self.ver_.items():
            m = base == call
            if m.any():
                pred[m] = ver.predict(Xr.loc[m, self.cols_])
        # 036 exact-opening rule
        if self.drop != "036":
            for i, k in enumerate(self._keys(Xr)):
                lab = self.table_.get(k)
                if lab is not None and lab not in META and pred[i] not in META:
                    pred[i] = lab
        # 100 cross-task rescue
        if self.t2_ is not None:
            p2 = np.asarray(self.t2_.predict(self._opening(X)), dtype=object)
            pred[(p2 == "instagram") & ~np.isin(pred, META)] = "facebook"
        return pred


def _drop_factory(layer):
    def f(seed):
        return Task1Configurable(seed=seed, drop=layer)
    f.__name__ = f"task1_drop{layer}"
    return f


def task2_base_only(seed):
    return SoftVote(seed=seed)


ARM = {"P": (T1, task1_cross_task), **{f"drop{l}": (T1, _drop_factory(l)) for l in LAYERS},
       "P2": (T2, task2_model), "drop014": (T2, task2_base_only)}


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_112_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    task, f = ARM[arm]
    feats = TASK_FEATURES[task]
    ref = None if arm in ("P", "P2") else run_id("P" if task == T1 else "P2", seed)
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    rid = record_run("112", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"{task} 112 {arm} (leave-one-layer-out audit) on never-used cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed}, started=t0)
    print(rid, flush=True)


def _data(task):
    Xr, y = load_task(task)
    return TASK_FEATURES[task](Xr), np.asarray(y.values, dtype=object)


def smoke():
    X, y = _data(T1)
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEEDS[0]).split(X, y))
    p = np.asarray(task1_cross_task(0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), dtype=object)
    q = Task1Configurable(seed=0, drop="").fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
    print("rebuild with no layer dropped equals production:", bool((q == p).all()), f"({len(te)} flows)")
    for l in LAYERS:
        r = Task1Configurable(seed=0, drop=l).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        print(f"drop {l}: changes {int((r != p).sum())} of {len(te)} predictions")


def analyse():
    out = {}
    for arm in T1_ARMS[1:] + T2_ARMS[1:]:
        task = ARM[arm][0]
        per, acc, cls = [], Counter(), {}
        for s in SEEDS:
            comp = json.loads((ROOT / "results" / run_id(arm, s) / "comparison.json").read_text())[task]
            per.append({"seed": s, "delta": round(comp["delta_mean"], 4), "wins": comp["wins"], "losses": comp["losses"],
                        "ties": comp["ties"], "verdict": comp["verdict"]})
            for c, v in comp["per_class"].items():
                cls.setdefault(c, []).append(v["delta"])
            ref = "P" if task == T1 else "P2"
            new = pd.read_csv(ROOT / "results" / run_id(arm, s) / task / "oof.csv")
            old = pd.read_csv(ROOT / "results" / run_id(ref, s) / task / "oof.csv")
            ch = new.y_pred.values != old.y_pred.values
            acc.update({"changed": int(ch.sum()), "fixed": int((ch & (new.y_pred.values == new.y_true.values)).sum()),
                        "broken": int((ch & (old.y_pred.values == old.y_true.values)).sum())})
        d = [p["delta"] for p in per]
        better = sum(p["verdict"] == "BETTER" for p in per)
        reading = ("simplification candidate" if better == 5 else "earns its place" if sum(x < 0 for x in d) >= 4
                   else "dead weight" if abs(np.mean(d)) < 0.002 else "inconclusive")
        out[arm] = {"task": task, "mean_delta_removal": round(float(np.mean(d)), 4), "negative_seeds": sum(x < 0 for x in d),
                    "better_seeds": better, "reading": reading, "per_seed": per,
                    "per_class_mean_delta": {c: round(float(np.mean(v)), 4) for c, v in cls.items()},
                    "changes_5_seeds": dict(acc)}
        print(f"{arm:8s} {task[:5]} removal Δ {np.mean(d):+.4f} | Δ<0 on {out[arm]['negative_seeds']}/5 | BETTER {better}/5 | "
              f"{reading} | {dict(acc)}")
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())
    out = {}
    for arm in T1_ARMS + T2_ARMS:
        task, f = ARM[arm]
        X, y = _data(task)
        Xt_raw = load_test(task)
        ids = list(Xt_raw.flow_id)
        p = np.asarray(f(0).fit(X, y).predict(TASK_FEATURES[task](Xt_raw)), dtype=object)
        out[arm] = {"task": task, "changed_vs_production_file": int(sum(p[i] != sub[task][ids[i]] for i in range(len(ids)))),
                    "changes": {ids[i]: f"{sub[task][ids[i]]} -> {p[i]}" for i in range(len(ids)) if p[i] != sub[task][ids[i]]}}
        print(arm, out[arm]["changed_vs_production_file"], out[arm]["changes"])
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=list(ARM))
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--test-effect", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        smoke()
    elif a.analyse:
        analyse()
    elif a.test_effect:
        test_effect()
    elif a.all:
        for s in SEEDS:
            for arm in T1_ARMS + T2_ARMS:
                run(arm, s)
    else:
        if not (a.arm and a.seed):
            ap.error("--arm and --seed are required")
        run(a.arm, a.seed)


if __name__ == "__main__":
    main()
