"""Experiment 116: fingerprint masking and fingerprint-jitter augmentation for the facebook/instagram decision
(protocol: experiments/116_fingerprint_masking_and_jitter.md).

Usage (from the repository root):
  .venv/bin/python src/exp116_fingerprint_masking_and_jitter.py --smoke
  .venv/bin/python src/exp116_fingerprint_masking_and_jitter.py --all          # P, M, MK, J, P2, J2 on seeds 2161-2165
  .venv/bin/python src/exp116_fingerprint_masking_and_jitter.py --arm M --seed 2161
  .venv/bin/python src/exp116_fingerprint_masking_and_jitter.py --analyse
  .venv/bin/python src/exp116_fingerprint_masking_and_jitter.py --test-effect
Runs go to results/<stamp>_116_<arm>_s<seed>/; other evidence to experiments/116_evidence/.
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
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from cv import TASK_FEATURES, evaluate, load_task
from models import T1_COLS, SoftVote, task1_cross_task, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
SEEDS = (2161, 2162, 2163, 2164, 2165)
META = ("facebook", "instagram")
EVIDENCE = ROOT / "experiments/116_evidence"
UPLOADED = ("best-87.77-frozen-5eb9a8b", "candidate-066-rest-expert", "candidate-083-instagram-verifier",
            "best-88.11-production-084", "production-089-bundle", "production-100-cross-task")
COPIES, AMP = 5, 8


def jitter(X, prefix, seed):
    """Original rows plus COPIES copies whose opening mean packet sizes get U{-AMP..AMP} bytes per direction (bytes and the byte
    ratio recomputed with the decoded formulas; counts, spreads and everything else unchanged)."""
    rng = np.random.default_rng(seed)
    out = [X]
    for _ in range(COPIES):
        C = X.copy()
        for d in ("up", "down"):
            n = C[f"{prefix}packet_count_{d}"].to_numpy(float)
            m = C[f"{prefix}mean_pkt_size_{d}"].to_numpy(float)
            m2 = np.where(n > 0, np.clip(m + rng.integers(-AMP, AMP + 1, len(C)), 0, None), m)
            C[f"{prefix}mean_pkt_size_{d}"] = m2
            C[f"{prefix}bytes_{d}"] = n * m2
        C[f"{prefix}up_down_byte_ratio"] = C[f"{prefix}bytes_up"] / np.maximum(C[f"{prefix}bytes_down"], 1)
        out.append(C)
    return pd.concat(out, ignore_index=True)


def _log1p(A):
    return np.log1p(np.clip(A, 0, None))


class PairRedecide(BaseEstimator, ClassifierMixin):
    """Production Task 1 (100 FB); flows its 089 bundle calls facebook or instagram are re-decided by a pair decider."""

    def __init__(self, seed=0, kind="M"):
        self.seed, self.kind = seed, kind

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.prod_ = task1_cross_task(self.seed).fit(X, y)
        m = np.isin(y, META)
        Xm, ym = X.loc[m].reset_index(drop=True), y[m]
        if self.kind == "M":
            self.cols_ = list(T1_COLS)
            self.pair_ = SoftVote(seed=self.seed, class_weight=None).fit(Xm[self.cols_], ym)
        elif self.kind == "MK":
            self.cols_ = list(T1_COLS)
            self.pair_ = make_pipeline(FunctionTransformer(_log1p), StandardScaler(),
                                       KNeighborsClassifier(n_neighbors=1)).fit(Xm[self.cols_], ym)
        else:
            self.cols_ = list(X.columns)
            Xa = jitter(Xm[self.cols_], "p5_", self.seed)
            self.pair_ = SoftVote(seed=self.seed, class_weight=None).fit(Xa, np.tile(ym, COPIES + 1))
        self.classes_ = self.prod_.classes_
        return self

    def predict(self, X):
        out = np.asarray(self.prod_.predict(X), dtype=object).copy()
        bundle = np.asarray(self.prod_.t1_.predict(X), dtype=object)
        idx = np.isin(bundle, META)
        if idx.any():
            out[idx] = self.pair_.predict(X.loc[idx, self.cols_])
        return out


class Task2Jitter(BaseEstimator, ClassifierMixin):
    """models.task2_model with its facebook/instagram specialist trained on jittered copies of the pair rows."""

    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.base_ = SoftVote(seed=self.seed).fit(X, y)
        m = np.isin(y, META)
        Xa = jitter(X.loc[m].reset_index(drop=True), "", self.seed)
        self.spec_ = SoftVote(seed=self.seed, class_weight=None).fit(Xa, np.tile(y[m], COPIES + 1))
        self.classes_ = self.base_.classes_
        return self

    def predict(self, X):
        pred = np.asarray(self.base_.predict(X), dtype=object).copy()
        m = np.isin(pred, META)
        if m.any():
            pred[m] = self.spec_.predict(X.loc[m])
        return pred


def _factory(name, fn):
    fn.__name__ = name
    return fn


ARM = {"P": (T1, task1_cross_task),
       "M": (T1, _factory("task1_pair_mask_softvote", lambda s: PairRedecide(seed=s, kind="M"))),
       "MK": (T1, _factory("task1_pair_mask_1nn", lambda s: PairRedecide(seed=s, kind="MK"))),
       "J": (T1, _factory("task1_pair_jitter", lambda s: PairRedecide(seed=s, kind="J"))),
       "P2": (T2, task2_model),
       "J2": (T2, _factory("task2_specialist_jitter", lambda s: Task2Jitter(seed=s)))}
REF = {"M": "P", "MK": "P", "J": "P", "J2": "P2"}


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_116_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    task, f = ARM[arm]
    feats = TASK_FEATURES[task]
    t0 = datetime.now(timezone.utc)
    res = {task: evaluate(task, feats, f, cv_seed=seed)}
    rid = record_run("116", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=run_id(REF[arm], seed) if arm in REF else None,
                     question=f"{task} 116 {arm} (fingerprint masking / jitter for facebook vs instagram) on never-used cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed, "copies": COPIES, "amp_bytes": AMP}, started=t0)
    print(rid, flush=True)


def _data(task):
    Xr, y = load_task(task)
    return TASK_FEATURES[task](Xr), np.asarray(y.values, dtype=object)


def smoke():
    for task, ref, arms in ((T1, "P", ("M", "MK", "J")), (T2, "P2", ("J2",))):
        X, y = _data(task)
        tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEEDS[0]).split(X, y))
        p = np.asarray(ARM[ref][1](0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), dtype=object)
        for arm in arms:
            m = ARM[arm][1](0).fit(X.iloc[tr], y[tr])
            q = m.predict(X.iloc[te])
            gate = (np.asarray(m.prod_.t1_.predict(X.iloc[te]), dtype=object) if task == T1
                    else np.asarray(m.base_.predict(X.iloc[te]), dtype=object))
            out = ~np.isin(gate, META)
            print(f"{arm}: equals {ref} where not Meta: {bool((q[out] == p[out]).all())} | Meta-routed flows {int((~out).sum())} | "
                  f"changed vs {ref}: {int((q != p).sum())} of {len(te)}")
    Xm = _data(T1)[0].head(20)
    J = jitter(Xm, "p5_", 0)
    ok = all(np.allclose(J[f"p5_bytes_{d}"], J[f"p5_packet_count_{d}"] * J[f"p5_mean_pkt_size_{d}"]) for d in ("up", "down"))
    print("jittered copies satisfy bytes = count × mean:", ok, f"({len(J)} rows from 20)")


def analyse():
    out = {}
    for arm, ref in REF.items():
        task = ARM[arm][0]
        per, acc, cls = [], Counter(), {}
        for s in SEEDS:
            comp = json.loads((ROOT / "results" / run_id(arm, s) / "comparison.json").read_text())[task]
            per.append({"seed": s, "delta": round(comp["delta_mean"], 4), "wins": comp["wins"], "losses": comp["losses"],
                        "ties": comp["ties"], "verdict": comp["verdict"]})
            for c, v in comp["per_class"].items():
                cls.setdefault(c, []).append(v["delta"])
            new = pd.read_csv(ROOT / "results" / run_id(arm, s) / task / "oof.csv")
            old = pd.read_csv(ROOT / "results" / run_id(ref, s) / task / "oof.csv")
            ch = new.y_pred.values != old.y_pred.values
            acc.update({"changed": int(ch.sum()), "fixed": int((ch & (new.y_pred.values == new.y_true.values)).sum()),
                        "broken": int((ch & (old.y_pred.values == old.y_true.values)).sum())})
        d = [p["delta"] for p in per]
        out[arm] = {"task": task, "mean_delta": round(float(np.mean(d)), 4), "positive_seeds": sum(x > 0 for x in d),
                    "better_seeds": sum(p["verdict"] == "BETTER" for p in per), "per_seed": per,
                    "per_class_mean_delta": {c: round(float(np.mean(v)), 4) for c, v in cls.items()}, "changes_5_seeds": dict(acc)}
        print(f"{arm:3s} {task[:5]} Δ {np.mean(d):+.4f} | positive {out[arm]['positive_seeds']}/5 | BETTER {out[arm]['better_seeds']}/5 | "
              f"fb {out[arm]['per_class_mean_delta'].get('facebook', 0):+.3f} ig {out[arm]['per_class_mean_delta'].get('instagram', 0):+.3f} | {dict(acc)}")
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    out = {}
    for arm, (task, f) in ARM.items():
        X, y = _data(task)
        Xt_raw = load_test(task)
        ids = list(Xt_raw.flow_id)
        p = np.asarray(f(0).fit(X, y).predict(TASK_FEATURES[task](Xt_raw)), dtype=object)
        files = {d: json.loads((ROOT / "submissions" / d / "submission.json").read_text())[task] for d in UPLOADED}
        vs = {d: int(sum(p[i] != fl[ids[i]] for i in range(len(ids)))) for d, fl in files.items()}
        prod = files["production-100-cross-task"]
        out[arm] = {"task": task, "min_vs_any_upload": min(vs.values()), "changed_vs_each_uploaded_file": vs,
                    "changes_vs_production_100": {ids[i]: f"{prod[ids[i]]} -> {p[i]}" for i in range(len(ids)) if p[i] != prod[ids[i]]}}
        print(arm, out[arm]["min_vs_any_upload"], out[arm]["changes_vs_production_100"])
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
            for arm in ("P", "M", "MK", "J", "P2", "J2"):
                run(arm, s)
    else:
        if not (a.arm and a.seed):
            ap.error("--arm and --seed are required")
        run(a.arm, a.seed)


if __name__ == "__main__":
    main()
