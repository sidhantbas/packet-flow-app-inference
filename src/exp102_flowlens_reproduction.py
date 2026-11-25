"""Experiment 102: reproduce Infralibre's FlowLens-v8-Mozilla on Task 2 (protocol: experiments/102_flowlens_reproduction.md).
Pipelines are composed from src/flowkit; this runner only maps arm names to specs, runs CV and writes evidence.

Usage (from the repository root):
  .venv/bin/python src/exp102_flowlens_reproduction.py --smoke
  .venv/bin/python src/exp102_flowlens_reproduction.py --arm P --seed 2101            # production reference (run first per seed)
  .venv/bin/python src/exp102_flowlens_reproduction.py --arm F2S-D --seed 2101        # compared with that seed's P run
  .venv/bin/python src/exp102_flowlens_reproduction.py --all                          # every arm on every seed, P first
  .venv/bin/python src/exp102_flowlens_reproduction.py --analyse                      # paired ingredient table -> evidence
  .venv/bin/python src/exp102_flowlens_reproduction.py --test-effect                  # compliant arms on the 81 test flows
  .venv/bin/python src/exp102_flowlens_reproduction.py --spec "base=softvote,cal=isotonic,counts=shares" --seed 2101
                                                                                      # ad-hoc pipeline (not part of the protocol)
Runs go to results/<stamp>_102_<arm>_s<seed>/ through runlog; other evidence to experiments/102_evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cv import TASK_FEATURES, evaluate, load_task
from flowkit import from_spec
from models import task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T2 = "task2_realtime_prefix5"
SEEDS = (2101, 2102, 2103, 2104, 2105)
ARMS = {"F0": "base=softvote", "F1S": "base=softvote,cal=sigmoid", "F1I": "base=softvote,cal=isotonic",
        "F2S-D": "base=softvote,cal=sigmoid,counts=disclosed", "F2S-S": "base=softvote,cal=sigmoid,counts=shares",
        "F2I-D": "base=softvote,cal=isotonic,counts=disclosed", "F2I-S": "base=softvote,cal=isotonic,counts=shares"}
EVIDENCE = ROOT / "experiments/102_evidence"
LABELS = np.asarray(load_task(T2)[1].values, dtype=object)  # train + validation labels, row order of cv.evaluate


def factory(arm_or_spec):
    if arm_or_spec == "P":
        f = task2_model
    else:
        spec = ARMS.get(arm_or_spec, arm_or_spec)

        def f(seed):
            return from_spec(spec, seed=seed, disclosed_labels=LABELS if "disclosed" in spec else None)
        f.__name__ = "flowkit_" + spec.replace("=", "_").replace(",", "__")
    return f


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_102_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed, spec=None):
    name = arm if spec is None else "SPEC"
    f, feats = factory(spec or arm), TASK_FEATURES[T2]
    ref = None if arm == "P" else run_id("P", seed)
    t0 = datetime.now(timezone.utc)
    res = {T2: evaluate(T2, feats, f, cv_seed=seed)}
    rid = record_run("102", f"{name}_s{seed}", res, model_factory=f, feature_fn=feats, reference=ref,
                     question=f"Task 2 102 {name} ({spec or ARMS.get(arm, 'production 014')}) on never-used cv_seed {seed}",
                     config={"arm": name, "spec": spec or ARMS.get(arm, "models.task2_model"), "cv_seed": seed}, started=t0)
    print(rid, flush=True)
    return rid


def smoke():
    import exp095_disclosed_counts as e95
    from flowkit.counts import quota_assign
    rng = np.random.default_rng(0)
    P = rng.dirichlet(np.ones(6), size=66)
    classes = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
    counts = dict(zip(classes, [3, 26, 4, 8, 14, 11]))
    print("quota_assign identical to 095:", bool((quota_assign(P, classes, counts) == e95.quota_assign(P, classes, counts)).all()))
    from sklearn.model_selection import RepeatedStratifiedKFold
    X = TASK_FEATURES[T2](load_task(T2)[0])
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2101).split(X, LABELS))
    a = factory("F0")(0).fit(X.iloc[tr], LABELS[tr]).predict(X.iloc[te])
    b = task2_model(0).fit(X.iloc[tr], LABELS[tr]).base_.predict(X.iloc[te])
    print("F0 identical to the 014 base SoftVote:", bool((np.asarray(a) == np.asarray(b)).all()))
    for arm in ("F1S", "F2S-S", "F2S-D"):
        p = factory(arm)(0).fit(X.iloc[tr], LABELS[tr]).predict(X.iloc[te])
        print(arm, "predicted counts:", dict(Counter(p)), "| true:", dict(Counter(LABELS[te])))


def fold_f1(rid):
    return pd.read_csv(ROOT / "results" / rid / T2 / "folds.csv").macro_f1.values


def analyse():
    pairs = [("F0", "P", "balanced SoftVote alone vs production"), ("F1S", "F0", "sigmoid calibration"),
             ("F1I", "F0", "isotonic calibration"), ("F2S-D", "F1S", "disclosed counts after sigmoid"),
             ("F2S-S", "F1S", "share counts after sigmoid"), ("F2S-D", "F2S-S", "the disclosure itself (sigmoid)"),
             ("F2I-D", "F1I", "disclosed counts after isotonic"), ("F2I-S", "F1I", "share counts after isotonic"),
             ("F2S-D", "P", "the claim (sigmoid) vs production"), ("F2I-D", "P", "the claim (isotonic) vs production"),
             ("F2S-S", "P", "compliant version (sigmoid) vs production"), ("F2I-S", "P", "compliant version (isotonic) vs production")]
    out = {"means": {}, "pairs": []}
    for arm in ["P"] + list(ARMS):
        vals = [fold_f1(run_id(arm, s)).mean() for s in SEEDS]
        out["means"][arm] = [round(float(v), 4) for v in vals]
    for a, b, what in pairs:
        per = []
        for s in SEEDS:
            d = fold_f1(run_id(a, s)) - fold_f1(run_id(b, s))
            per.append({"seed": s, "delta": round(float(d.mean()), 4), "wins": int((d > 1e-12).sum()),
                        "losses": int((d < -1e-12).sum())})
        out["pairs"].append({"a": a, "b": b, "what": what, "mean_delta": round(float(np.mean([p["delta"] for p in per])), 4),
                             "per_seed": per})
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
    for p in out["pairs"]:
        print(f"{p['a']:6s} vs {p['b']:6s} {p['mean_delta']:+.4f}  {p['what']}  "
              + " ".join(f"{q['delta']:+.4f}({q['wins']}/{q['losses']})" for q in p["per_seed"]))


def test_effect():
    from make_submission import load_test
    Xr, y = load_task(T2)
    X, yv = TASK_FEATURES[T2](Xr), np.asarray(y.values, dtype=object)
    Xt_raw = load_test(T2)
    Xt = TASK_FEATURES[T2](Xt_raw)
    submitted = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T2]
    sub = np.array([submitted[f] for f in Xt_raw.flow_id], dtype=object)
    out = {"submitted_task2_counts": dict(Counter(sub))}
    for arm in ("P", "F0", "F1S", "F1I", "F2S-S", "F2I-S"):
        p = np.asarray(factory(arm)(0).fit(X, yv).predict(Xt), dtype=object)
        ch = p != sub
        out[arm] = {"predicted_counts": dict(Counter(p)), "changed_vs_submitted": int(ch.sum()),
                    "transitions": dict(Counter(f"{a} -> {b}" for a, b in zip(sub[ch], p[ch])))}
        print(arm, out[arm])
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "test_effect.json").write_text(json.dumps(out, indent=2, default=int) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=["P"] + list(ARMS))
    ap.add_argument("--spec", help="ad-hoc flowkit spec, e.g. base=softvote,cal=sigmoid,counts=shares")
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--all", action="store_true", help="every arm on every seed (P first for each seed)")
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
            for arm in ["P"] + list(ARMS):
                run(arm, s)
    elif a.spec:
        run("SPEC", a.seed, spec=a.spec)
    else:
        if not (a.arm and a.seed):
            ap.error("--arm and --seed are required")
        run(a.arm, a.seed)


if __name__ == "__main__":
    main()
