"""Experiment 111: a logistic-regression stacker, fitted inside each training fold on out-of-fold base-model outputs, in place of
Task 1's hand-coded cross-task Meta rescue (100) (protocol: experiments/111_task1_learned_rescue_stacker.md).

Usage (from the repository root):
  .venv/bin/python src/exp111_task1_learned_rescue_stacker.py --smoke
  .venv/bin/python src/exp111_task1_learned_rescue_stacker.py --all          # P, S14, S on seeds 2146-2150
  .venv/bin/python src/exp111_task1_learned_rescue_stacker.py --arm S14 --seed 2146
  .venv/bin/python src/exp111_task1_learned_rescue_stacker.py --analyse
  .venv/bin/python src/exp111_task1_learned_rescue_stacker.py --test-effect
Runs go to results/<stamp>_111_<arm>_s<seed>/; other evidence to experiments/111_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cv import TASK_FEATURES, evaluate, load_task
from exp109_task2_first_packet_specialist import BASE_COLS, SelectSpecialist
from exp110_task1_rescue_with_109b import UPLOADED, opening_candidates
from models import TwoClerks, task1_bundle, task1_cross_task, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1 = "task1_static"
SEEDS = (2146, 2147, 2148, 2149, 2150)
ARMS = ("P", "S14", "S")
META = ("facebook", "instagram")
APPS = ("facebook", "google", "instagram", "mozilla", "x", "youtube")
EVIDENCE = ROOT / "experiments/111_evidence"


def opening(X):
    """The 12 p5_ opening columns under their Task 2 names (as models.CrossTaskMetaRescue)."""
    return X[list(TwoClerks.OPEN_COLS)].set_axis(BASE_COLS, axis=1)


def _col(m, cls):
    return list(m.classes_).index(cls)


class LearnedRescue(BaseEstimator, ClassifierMixin):
    """089 bundle; flows it calls neither facebook nor instagram become facebook when a logistic-regression stacker, fitted on
    out-of-fold base outputs of the training fold, gives P(facebook) > 0.5."""

    def __init__(self, seed=0, use_109b=False, inner_folds=4):
        self.seed, self.use_109b, self.inner_folds = seed, use_109b, inner_folds

    def _fit_bases(self, X, y):
        b = {"bundle": task1_bundle(self.seed).fit(X, y), "m014": task2_model(self.seed).fit(opening(X), y)}
        if self.use_109b:
            b["m109b"] = SelectSpecialist(seed=self.seed).fit(opening_candidates(X), y)
        return b

    def _features(self, b, X):
        O = opening(X)
        base, spec = b["m014"].base_, b["m014"].spec_
        pb = base.predict_proba(O[b["m014"].base_cols_])
        F = {"p_meta": pb[:, _col(base, "facebook")] + pb[:, _col(base, "instagram")],
             "p_fb_014": spec.predict_proba(O[b["m014"].spec_cols_])[:, _col(spec, "facebook")]}
        if self.use_109b:
            s = b["m109b"]
            F["p_fb_109b"] = s.spec_.predict_proba(opening_candidates(X)[s.spec_cols_])[:, _col(s.spec_, "facebook")]
        lab = np.asarray(b["bundle"].predict(X), dtype=object)
        for a in APPS:
            F[f"b_{a}"] = (lab == a).astype(float)
        return pd.DataFrame(F), lab

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        parts, order = [], []
        for itr, ite in StratifiedKFold(self.inner_folds, shuffle=True, random_state=self.seed).split(X, y):
            F, _ = self._features(self._fit_bases(X.iloc[itr], y[itr]), X.iloc[ite])
            parts.append(F)
            order.append(ite)
        F = pd.concat(parts, ignore_index=True)
        t = (y[np.concatenate(order)] == "facebook").astype(int)
        self.n_oof_, self.n_fb_oof_ = len(F), int(t.sum())
        self.lr_ = (make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000)).fit(F, t)
                    if 0 < t.sum() < len(t) else None)
        self.feature_names_ = list(F.columns)
        self.bases_ = self._fit_bases(X, y)
        self.classes_ = self.bases_["bundle"].classes_
        return self

    def predict(self, X):
        F, lab = self._features(self.bases_, X)
        out = lab.copy()
        if self.lr_ is not None:
            p = self.lr_.predict_proba(F[self.feature_names_])[:, 1]
            out[~np.isin(lab, META) & (p > 0.5)] = "facebook"
        return out


def task1_learned_rescue_014(seed):
    return LearnedRescue(seed=seed, use_109b=False)


def task1_learned_rescue_014_109b(seed):
    return LearnedRescue(seed=seed, use_109b=True)


ARM = {"P": task1_cross_task, "S14": task1_learned_rescue_014, "S": task1_learned_rescue_014_109b}


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_111_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    f, feats = ARM[arm], TASK_FEATURES[T1]
    t0 = datetime.now(timezone.utc)
    res = {T1: evaluate(T1, feats, f, cv_seed=seed)}
    rid = record_run("111", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id("P", seed),
                     question=f"Task 1 111 {arm} (jointly fitted rescue stacker) on never-used cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed, "inner_folds": 4, "C": 1.0, "cutoff": 0.5}, started=t0)
    print(rid, flush=True)


def _data():
    Xr, y = load_task(T1)
    return TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)


def smoke():
    X, y = _data()
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEEDS[0]).split(X, y))
    p = np.asarray(task1_cross_task(0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), dtype=object)
    for arm in ("S14", "S"):
        m = ARM[arm](0).fit(X.iloc[tr], y[tr])
        q = np.asarray(m.predict(X.iloc[te]), dtype=object)
        lab = np.asarray(m.bases_["bundle"].predict(X.iloc[te]), dtype=object)
        meta = np.isin(lab, META)
        coef = dict(zip(m.feature_names_, np.round(m.lr_[-1].coef_[0], 2))) if m.lr_ is not None else None
        print(f"{arm}: OOF rows {m.n_oof_} of {len(tr)} (facebook {m.n_fb_oof_}) | keeps bundle label on Meta calls: "
              f"{bool((q[meta] == lab[meta]).all())} | rescues: {int((q != lab).sum())} | changed vs P: {int((q != p).sum())} "
              f"of {len(te)}\n   coefficients: {coef}")


def analyse():
    out = {"means": {a: [round(float(pd.read_csv(ROOT / "results" / run_id(a, s) / T1 / "folds.csv").macro_f1.mean()), 4)
                         for s in SEEDS] for a in ARMS}, "vs_P": {}}
    for a in ("S14", "S"):
        per, acc, tr, cls = [], Counter(), Counter(), {}
        for s in SEEDS:
            comp = json.loads((ROOT / "results" / run_id(a, s) / "comparison.json").read_text())[T1]
            per.append({"seed": s, "delta": round(comp["delta_mean"], 4), "wins": comp["wins"], "losses": comp["losses"],
                        "ties": comp["ties"], "verdict": comp["verdict"]})
            for c, v in comp["per_class"].items():
                cls.setdefault(c, []).append(v["delta"])
            new = pd.read_csv(ROOT / "results" / run_id(a, s) / T1 / "oof.csv")
            ref = pd.read_csv(ROOT / "results" / run_id("P", s) / T1 / "oof.csv")
            ch = new.y_pred.values != ref.y_pred.values
            acc.update({"changed": int(ch.sum()), "fixed": int((ch & (new.y_pred.values == new.y_true.values)).sum()),
                        "broken": int((ch & (ref.y_pred.values == ref.y_true.values)).sum())})
            tr.update(f"{t}: {x} -> {z}" for t, x, z in zip(new.y_true.values[ch], ref.y_pred.values[ch], new.y_pred.values[ch]))
        out["vs_P"][a] = {"mean_delta": round(float(np.mean([p["delta"] for p in per])), 4), "per_seed": per,
                          "per_class_mean_delta": {c: round(float(np.mean(v)), 4) for c, v in cls.items()},
                          "changes_5_seeds": dict(acc), "transitions_true_was_now": dict(tr.most_common(10))}
        print(a, json.dumps(out["vs_P"][a], indent=1))
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    Xt_raw = load_test(T1)
    ids = list(Xt_raw.flow_id)
    Xt = TASK_FEATURES[T1](Xt_raw)
    X, y = _data()
    files = {d: json.loads((ROOT / "submissions" / d / "submission.json").read_text())[T1] for d in UPLOADED}
    out = {}
    for a in ARMS:
        m = ARM[a](0).fit(X, y)
        p = np.asarray(m.predict(Xt), dtype=object)
        vs = {d: int(sum(p[i] != f[ids[i]] for i in range(len(ids)))) for d, f in files.items()}
        prod = files["production-100-cross-task"]
        out[a] = {"changed_vs_each_uploaded_file": vs, "min_vs_any_upload": min(vs.values()),
                  "changes_vs_production_100": {ids[i]: f"{prod[ids[i]]} -> {p[i]}" for i in range(len(ids)) if p[i] != prod[ids[i]]},
                  "stacker_coefficients": (dict(zip(m.feature_names_, [round(float(c), 3) for c in m.lr_[-1].coef_[0]]))
                                           if getattr(m, "lr_", None) is not None else None)}
    print(json.dumps(out, indent=1))
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=ARMS)
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
            for arm in ARMS:
                run(arm, s)
    else:
        if not (a.arm and a.seed):
            ap.error("--arm and --seed are required")
        run(a.arm, a.seed)


if __name__ == "__main__":
    main()
