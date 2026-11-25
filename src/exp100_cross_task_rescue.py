"""Experiment 100: cross-task Meta rescue for Task 1 (protocol: experiments/100_cross_task_meta_rescue.md, frozen first).

Production 089 plus an inner copy of the Task 2 production model (014) on the 12 no-timing prefix-5 columns; a flow the inner
model calls instagram while 089 calls it non-Meta gets `label` (FB arm: facebook; IG arm: instagram).

Usage: python src/exp100_cross_task_rescue.py --smoke
       python src/exp100_cross_task_rescue.py --arm REF|FB|IG --folds ordinary|grouped --seed N [--ref RUN_ID]
       python src/exp100_cross_task_rescue.py --analyse
       python src/exp100_cross_task_rescue.py --build      (only after a pass; writes submissions/candidate-100-cross-task-fb/)
"""
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, TASKS, TIMING, evaluate, load_task
from exp036_twin_aware import twin_splits
from models import task1_bundle, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T1, T2 = "task1_static", "task2_realtime_prefix5"
LABS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
META = ("facebook", "instagram")
ORDINARY = (2046, 2047, 2048, 2049, 2050)
GROUPED = (2046, 2056, 2066, 2076, 2086)
REPRO = {"ref": "20261010T004051Z_089_production_check_s2026", "delta": 0.0083, "wtl": (8, 3, 39)}
T2_CHAMPION = "20260930T173836Z_014_fi_same_nocw"


def t2_columns(X):
    """The prefix-5 columns the Task 2 production model uses, in Task 2's column order, as (Task 1 name, Task 2 name)."""
    return [(c, c[3:]) for c in X.columns if c.startswith("p5_") and c[3:] not in TIMING]


class CrossTaskRescue(BaseEstimator, ClassifierMixin):
    """089 + inner Task 2 model; inner instagram with 089 outside Meta -> `label`. label=None returns 089 unchanged."""

    def __init__(self, seed=0, label="facebook"):
        self.seed, self.label = seed, label

    def _x2(self, X):
        cols = t2_columns(X)
        return X[[a for a, _ in cols]].set_axis([b for _, b in cols], axis=1)

    def fit(self, X, y):
        y = np.asarray(y, dtype=object)
        self.t1_ = task1_bundle(self.seed).fit(X, y)
        self.classes_ = self.t1_.classes_
        if self.label is not None:
            self.t2_ = task2_model(self.seed).fit(self._x2(X), y)
        return self

    def predict_both(self, X):
        p1 = np.asarray(self.t1_.predict(X), dtype=object)
        p2 = np.asarray(self.t2_.predict(self._x2(X)), dtype=object)
        return p1, p2

    def predict(self, X):
        if self.label is None:
            return np.asarray(self.t1_.predict(X), dtype=object)
        p1, p2 = self.predict_both(X)
        out = p1.copy()
        out[(p2 == "instagram") & ~np.isin(p1, META)] = self.label
        return out


ARMS = {"REF": None, "FB": "facebook", "IG": "instagram"}


def factory(arm):
    def f(seed):
        return CrossTaskRescue(seed=seed, label=ARMS[arm])
    f.__name__ = "cross_task_" + arm.lower()
    return f


def splits(folds, seed):
    if folds == "grouped":
        return twin_splits(seed)
    Xr, y = load_task(T1)
    return list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=seed).split(Xr, y))


def run_id(arm, folds, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_100_{arm}_{folds}_s{seed}"))
    return hits[-1] if hits else None


def smoke():
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    tr, te = splits("ordinary", 2026)[0]
    m = CrossTaskRescue(seed=0).fit(X.iloc[tr], yv[tr])
    p1, p2 = m.predict_both(X.iloc[te])
    ref1 = np.asarray(task1_bundle(0).fit(X.iloc[tr], yv[tr]).predict(X.iloc[te]), dtype=object)
    champ = pd.read_csv(ROOT / "results" / T2_CHAMPION / T2 / "oof.csv")
    c0 = champ[champ.fold == 0]
    assert (c0.flow_id.values == Xr.flow_id.values[te]).all()
    print("REF part identical to task1_bundle:", bool((p1 == ref1).all()))
    print("inner Task 2 identical to the 014 champion (fold 0):", bool((p2 == c0.y_pred.values).all()))
    print("Task 2 columns:", [b for _, b in t2_columns(X)])


def analyse():
    Xr, y = load_task(T1)
    flows = Xr.flow_id.values
    share_ig = float(np.mean(np.asarray(y.values) == "instagram"))
    out = {"ordinary": {}, "grouped": {}}
    for folds, seeds in (("ordinary", ORDINARY), ("grouped", GROUPED)):
        for seed in seeds:
            sp = splits(folds, seed)
            order = np.concatenate([flows[te] for _, te in sp])
            R = {}
            for arm in (("REF", "FB", "IG") if folds == "ordinary" else ("REF", "FB")):
                rid = run_id(arm, folds, seed)
                if rid is None:
                    continue
                o = pd.read_csv(ROOT / "results" / rid / T1 / "oof.csv")
                assert (o.flow_id.values == order).all(), (arm, folds, seed)
                R[arm] = (rid, o, pd.read_csv(ROOT / "results" / rid / T1 / "folds.csv").macro_f1.values)
            if "REF" not in R:
                continue
            ref = R["REF"][1]
            cell = {"REF": R["REF"][0]}
            for arm in [a for a in R if a != "REF"]:
                rid, o, f = R[arm]
                d = f - R["REF"][2]
                case = o.y_pred.values != ref.y_pred.values
                truth = Counter(o.y_true.values[case])
                # instagram-count deficit of REF per held-out fold (descriptive, frozen)
                deficit = np.zeros(len(o), dtype=bool)
                for k in np.unique(o.fold.values):
                    g = o.fold.values == k
                    deficit[g] = (ref.y_pred.values[g] == "instagram").sum() < round(g.sum() * share_ig)
                cell[arm] = {
                    "run": rid, "delta_mean": round(float(d.mean()), 4), "wins": int((d > 1e-12).sum()),
                    "losses": int((d < -1e-12).sum()), "ties": int((np.abs(d) <= 1e-12).sum()),
                    "cases": int(case.sum()), "cases_truth": dict(truth), "cases_right": int((o.y_pred.values[case] == o.y_true.values[case]).sum()),
                    "distinct_flows": dict(Counter(o.flow_id.values[case]).most_common()),
                    "per_class_delta": dict(zip(LABS, np.round(f1_score(o.y_true, o.y_pred, labels=LABS, average=None)
                                                               - f1_score(ref.y_true, ref.y_pred, labels=LABS, average=None), 3).tolist())),
                    "facebook_share_in_ig_deficit_folds": [int((o.y_true.values[case & deficit] == "facebook").sum()), int((case & deficit).sum())],
                    "facebook_share_in_other_folds": [int((o.y_true.values[case & ~deficit] == "facebook").sum()), int((case & ~deficit).sum())]}
            out[folds][str(seed)] = cell
            print(folds, seed, {a: (v["delta_mean"], v["wins"], v["losses"], v["ties"], v["cases"], v["cases_truth"])
                                for a, v in cell.items() if a != "REF"}, flush=True)
    def fold_f1(rid):
        return pd.read_csv(ROOT / "results" / rid / T1 / "folds.csv").macro_f1.values

    d = [fold_f1(c["FB"]["run"]) - fold_f1(c["REF"]) for c in out["grouped"].values() if "FB" in c]
    if d:
        d = np.concatenate(d)
        out["grouped_FB_pooled"] = {"folds": int(len(d)), "delta_mean": round(float(d.mean()), 4),
                                    "wins": int((d > 1e-12).sum()), "losses": int((d < -1e-12).sum())}
    ev = ROOT / "experiments/100_evidence"
    ev.mkdir(exist_ok=True)
    (ev / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def build():
    """After a pass only: Task 1 = FB arm fitted on train + validation (seed 0); Task 2 = the ranked entry's file, unchanged."""
    from make_final_candidate import FORBIDDEN_COLUMNS, sha
    from exp005_checks import official_module
    from make_submission import ALLOWED, load_test, write_submission
    out = ROOT / "submissions/candidate-100-cross-task-fb"
    out.mkdir(parents=True, exist_ok=True)
    ranked = json.loads((ROOT / "submissions/production-089-bundle/submission.json").read_text())
    Xr, y = load_task(T1)
    X, yv = TASK_FEATURES[T1](Xr), np.asarray(y.values, dtype=object)
    Xt_raw = load_test(T1)
    Xt = TASK_FEATURES[T1](Xt_raw)
    preds = []
    for _ in range(2):
        m = CrossTaskRescue(seed=0).fit(X, yv)
        p1, p2 = m.predict_both(Xt)
        preds.append(dict(zip(Xt_raw.flow_id, m.predict(Xt))))
    ids = list(Xt_raw.flow_id)
    checks = {"rebuild_identical": preds[0] == preds[1],
              "ref_part_equals_ranked_task1": all(ranked[T1][f] == a for f, a in zip(ids, p1)),
              "inner_task2_equals_submitted_task2": all(ranked[T2][f] == b for f, b in zip(ids, p2)),
              "forbidden_columns_absent": not any(c in X.columns for c in FORBIDDEN_COLUMNS)}
    sub = {T1: preds[0], T2: ranked[T2]}
    write_submission(sub, out / "submission.json", out / "submission.zip")
    mod = official_module()
    for name in ("submission.json", "submission.zip"):
        s = mod._load_submission(str(out / name))
        checks[f"official_loader_{name}"] = all(set(s[t]) == set(load_test(t).flow_id) and set(s[t].values()) <= ALLOWED for t in TASKS)
    diff = {f: (ranked[T1][f], v) for f, v in preds[0].items() if ranked[T1][f] != v}
    info = {"checks": checks, "changed_vs_ranked_entry": {T1: diff, T2: {}},
            "predicted_label_counts": {T1: dict(Counter(preds[0].values())), T2: dict(Counter(ranked[T2].values()))},
            "output_sha256": {n: sha(out / n) for n in ("submission.json", "submission.zip")},
            "model": "experiment 100 FB: models.task1_bundle + inner models.task2_model (instagram + non-Meta -> facebook)",
            "command": ".venv/bin/python src/exp100_cross_task_rescue.py --build"}
    (out / "validation.json").write_text(json.dumps(info, indent=2, default=str) + "\n")
    print(json.dumps(info, indent=1, default=str))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--smoke" in args:
        smoke()
        sys.exit()
    if "--analyse" in args:
        analyse()
        sys.exit()
    if "--build" in args:
        build()
        sys.exit()
    arm, folds = args[args.index("--arm") + 1], args[args.index("--folds") + 1]
    seed = int(args[args.index("--seed") + 1])
    ref = args[args.index("--ref") + 1] if "--ref" in args else (None if arm == "REF" else run_id("REF", folds, seed))
    f, feats = factory(arm), TASK_FEATURES[T1]
    t0 = datetime.now(timezone.utc)
    sp = splits(folds, seed) if folds == "grouped" else None
    sname = f"twin-aware StratifiedGroupKFold(5) x 10, seed {seed}, 036 groups (17 Task 1 columns, 0.05)" if sp else None
    res = {T1: evaluate(T1, feats, f, cv_seed=seed, splits=sp, split_name=sname)}
    rid = record_run("100", f"{arm}_{folds}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"Task 1 100 {arm} on {folds} folds, seed {seed}",
                     config={"arm": arm, "label": ARMS[arm], "folds": folds, "cv_seed": seed}, started=t0)
    print(rid)
