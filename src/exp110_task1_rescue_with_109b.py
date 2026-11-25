"""Experiment 110: 109 B (facebook/instagram specialist with columns chosen per fold) as the inner Task 2 model of Task 1's
cross-task Meta rescue (100) (protocol: experiments/110_task1_rescue_with_109b.md).

Usage (from the repository root):
  .venv/bin/python src/exp110_task1_rescue_with_109b.py --smoke
  .venv/bin/python src/exp110_task1_rescue_with_109b.py --all          # P, C, D on seeds 2141-2145
  .venv/bin/python src/exp110_task1_rescue_with_109b.py --arm C --seed 2141
  .venv/bin/python src/exp110_task1_rescue_with_109b.py --analyse
  .venv/bin/python src/exp110_task1_rescue_with_109b.py --test-effect
Runs go to results/<stamp>_110_<arm>_s<seed>/; other evidence to experiments/110_evidence/.
"""
import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task
from exp109_task2_first_packet_specialist import BASE_COLS, SELECT_LOG, SelectSpecialist, decoded_sizes, engineered
from models import TwoClerks, task1_bundle, task1_cross_task
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
SEEDS = (2141, 2142, 2143, 2144, 2145)
ARMS = ("P", "C", "D")
META = ("facebook", "instagram")
EVIDENCE = ROOT / "experiments/110_evidence"
UPLOADED = ("best-87.77-frozen-5eb9a8b", "candidate-066-rest-expert", "candidate-083-instagram-verifier",
            "best-88.11-production-084", "production-089-bundle", "production-100-cross-task")


def opening_candidates(X):
    """109's 30 candidate columns, built from the 12 p5_ opening columns of the 34 production Task 1 columns."""
    O = X[list(TwoClerks.OPEN_COLS)].set_axis(BASE_COLS, axis=1).reset_index(drop=True)
    raw = O.assign(transport=np.where(O.transport == 1, "udp", "tcp"))  # cv.basic_features: udp = 1
    return pd.concat([O, engineered(O), decoded_sizes(raw)], axis=1)


class RescueWith109B(BaseEstimator, ClassifierMixin):
    """Task1Bundle (089) + 109 B on the opening; a flow the bundle calls neither facebook nor instagram becomes facebook when the
    inner model calls instagram (trigger "instagram", 100's rule) or either Meta app (trigger "meta")."""

    def __init__(self, seed=0, trigger="instagram"):
        self.seed, self.trigger = seed, trigger

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.t1_ = task1_bundle(self.seed).fit(X, y)
        self.t2_ = SelectSpecialist(seed=self.seed).fit(opening_candidates(X), y)
        self.classes_ = self.t1_.classes_
        return self

    def predict(self, X):
        p1 = np.asarray(self.t1_.predict(X), dtype=object)
        p2 = np.asarray(self.t2_.predict(opening_candidates(X)), dtype=object)
        trig = ("instagram",) if self.trigger == "instagram" else META
        out = p1.copy()
        out[np.isin(p2, trig) & ~np.isin(p1, META)] = "facebook"
        return out


def task1_rescue_109b_ig(seed):
    return RescueWith109B(seed=seed, trigger="instagram")


def task1_rescue_109b_meta(seed):
    return RescueWith109B(seed=seed, trigger="meta")


ARM = {"P": task1_cross_task, "C": task1_rescue_109b_ig, "D": task1_rescue_109b_meta}


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_110_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    f, feats = ARM[arm], TASK_FEATURES[T1]
    t0 = datetime.now(timezone.utc)
    res = {T1: evaluate(T1, feats, f, cv_seed=seed)}
    rid = record_run("110", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id("P", seed),
                     question=f"Task 1 110 {arm} (109 B inside the cross-task Meta rescue) on never-used cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed, "trigger": {"P": "014 instagram", "C": "instagram", "D": "meta"}[arm]},
                     started=t0)
    print(rid, flush=True)


def _data():
    Xr, y = load_task(T1)
    return TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)


def smoke():
    X, y = _data()
    S1 = opening_candidates(X)[[f"s_{c}" for c in ("syn_size", "hello_size", "synack_size", "reply_size",
                                                     "up_min", "up_max", "down_min", "down_max")]]
    X2r, _ = load_task(T2)
    S2 = decoded_sizes(X2r)
    print("decoded sizes from p5_ columns equal those from the Task 2 file:", bool((S1.values == S2.values).all()))
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEEDS[0]).split(X, y))
    p = np.asarray(task1_cross_task(0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), dtype=object)
    for arm in ("C", "D"):
        m = ARM[arm](0).fit(X.iloc[tr], y[tr])
        q = np.asarray(m.predict(X.iloc[te]), dtype=object)
        bundle_meta = np.isin(np.asarray(m.t1_.predict(X.iloc[te]), dtype=object), META)
        print(f"{arm}: equals P where the bundle calls Meta: {bool((q[bundle_meta] == p[bundle_meta]).all())} | "
              f"changed vs P: {int((q != p).sum())} of {len(te)} | inner columns: {m.t2_.spec_cols_}")


def analyse():
    out = {"means": {a: [round(float(pd.read_csv(ROOT / "results" / run_id(a, s) / T1 / "folds.csv").macro_f1.mean()), 4)
                         for s in SEEDS] for a in ARMS}, "vs_P": {}}
    for a in ("C", "D"):
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
    log = EVIDENCE / "selected_columns.jsonl"
    if log.exists():
        rows = [json.loads(l) for l in log.read_text().splitlines()]
        out["inner_selection"] = {"fits_arms_C_and_D_pooled": len(rows),
                                  "column_counts": dict(Counter(c for r in rows for c in r["cols"]).most_common(10))}
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
                  "inner_columns": getattr(getattr(m, "t2_", None), "spec_cols_", None)}
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
    else:
        EVIDENCE.mkdir(exist_ok=True)
        os.environ[SELECT_LOG] = str(EVIDENCE / "selected_columns.jsonl")  # inner selections of arms C and D (identical fits)
        if a.all:
            for s in SEEDS:
                for arm in ARMS:
                    run(arm, s)
        else:
            if not (a.arm and a.seed):
                ap.error("--arm and --seed are required")
            run(a.arm, a.seed)


if __name__ == "__main__":
    main()
