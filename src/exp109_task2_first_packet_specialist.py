"""Experiment 109: the decoded first-packet size (s_up_max, 090) in Task 2's facebook/instagram specialist
(protocol: experiments/109_task2_first_packet_specialist.md). Reads only Task 2 files.

Usage (from the repository root):
  .venv/bin/python src/exp109_task2_first_packet_specialist.py --smoke
  .venv/bin/python src/exp109_task2_first_packet_specialist.py --all          # P, A, B on seeds 2136-2140
  .venv/bin/python src/exp109_task2_first_packet_specialist.py --arm A --seed 2136
  .venv/bin/python src/exp109_task2_first_packet_specialist.py --analyse
  .venv/bin/python src/exp109_task2_first_packet_specialist.py --test-effect
Runs go to results/<stamp>_109_<arm>_s<seed>/; other evidence to experiments/109_evidence/.
"""
import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import TASK_FEATURES, evaluate, load_task, no_timing_features
from exp090_stamp_catalogue import NUM as STAMPS, stamps
from models import PairSpecialist, SoftVote, task2_model
from runlog import record_run

ROOT = Path(__file__).resolve().parent.parent
T2 = "task2_realtime_prefix5"
SEEDS = (2136, 2137, 2138, 2139, 2140)
ARMS = ("P", "A", "B")
META = ("facebook", "instagram")
EVIDENCE = ROOT / "experiments/109_evidence"
SELECT_LOG = "MISSION_P_109_SELECT_LOG"  # if set, SelectSpecialist appends its chosen columns there (fold key + columns)
BASE_COLS = ["transport", "packet_count_up", "packet_count_down", "bytes_up", "bytes_down", "mean_pkt_size_up",
             "mean_pkt_size_down", "std_pkt_size_up", "std_pkt_size_down", "burst_count", "up_down_packet_ratio",
             "up_down_byte_ratio"]


# ---------------------------------------------------------------- features (row-wise, Task 2 columns only)

def _sdiv(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.divide(a, b, out=np.zeros_like(a), where=b != 0)


def decoded_sizes(X_raw):
    """The 8 decoded opening sizes of 090 (−1 where not decodable), prefixed s_."""
    S = pd.DataFrame([stamps(r) for r in X_raw.itertuples()])[STAMPS]
    return S.astype(float).fillna(-1).add_prefix("s_").reset_index(drop=True)


def engineered(B):
    """The 10 engineered Task 2 columns of notebook 5 part 5."""
    tb, tp = B.bytes_up + B.bytes_down, B.packet_count_up + B.packet_count_down
    E = pd.DataFrame({"e_total_bytes": tb, "e_total_pkts": tp,
                      "e_down_byte_share": _sdiv(B.bytes_down, tb), "e_down_pkt_share": _sdiv(B.packet_count_down, tp),
                      "e_size_asym": B.mean_pkt_size_down - B.mean_pkt_size_up,
                      "e_bytes_per_burst": _sdiv(tb, B.burst_count), "e_pkts_per_burst": _sdiv(tp, B.burst_count),
                      "e_cv_size_up": _sdiv(B.std_pkt_size_up, B.mean_pkt_size_up),
                      "e_cv_size_down": _sdiv(B.std_pkt_size_down, B.mean_pkt_size_down)}, index=B.index)
    E["e_open_bytes_per_pkt"] = _sdiv(E.e_total_bytes, E.e_total_pkts)
    return E


def task2_plus_up_max(X_raw):
    """Arm A: the 12 production columns + s_up_max."""
    B = no_timing_features(X_raw).reset_index(drop=True)
    assert list(B.columns) == BASE_COLS
    return pd.concat([B, decoded_sizes(X_raw)[["s_up_max"]]], axis=1)


def task2_candidates(X_raw):
    """Arm B: the 12 production columns + 10 engineered + 8 decoded sizes (30 columns)."""
    B = no_timing_features(X_raw).reset_index(drop=True)
    assert list(B.columns) == BASE_COLS
    return pd.concat([B, engineered(B), decoded_sizes(X_raw)], axis=1)


# ---------------------------------------------------------------- arm B: nested forward selection in the specialist

def _rf(seed):
    return RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=seed, n_jobs=1)


def _p_fb(m, X):
    return m.predict_proba(X)[:, list(m.classes_).index("facebook")]


def uni_rank(X, y):
    a = np.array([roc_auc_score(y == "facebook", X[c]) if X[c].nunique() > 1 else 0.5 for c in X.columns])
    return list(X.columns[np.argsort(-np.abs(a - 0.5), kind="stable")])


def inner_auc(X, y, splits, seed, cols):
    aucs = []
    for r in range(2):
        p = np.zeros(len(y))
        for tr, te in splits[3 * r:3 * r + 3]:
            p[te] = _p_fb(_rf(seed).fit(X.iloc[tr][cols], y[tr]), X.iloc[te][cols])
        aucs.append(roc_auc_score(y == "facebook", p))
    return float(np.mean(aucs))


def forward(X, y, seed, max_feats=5, min_gain=0.005):
    splits = list(RepeatedStratifiedKFold(n_splits=3, n_repeats=2, random_state=seed).split(X, y))
    chosen, best = [], 0.5
    while len(chosen) < max_feats:
        scores = {c: inner_auc(X, y, splits, seed, chosen + [c]) for c in X.columns if c not in chosen}
        c, s = max(scores.items(), key=lambda kv: kv[1])
        if s < best + min_gain:
            break
        chosen.append(c)
        best = s
    return chosen or uni_rank(X, y)[:1]


class SelectSpecialist(BaseEstimator, ClassifierMixin):
    """task2_model's balanced 6-app SoftVote on the 12 production columns; flows it calls facebook/instagram are re-decided by
    an unweighted SoftVote on columns chosen by nested forward selection on the facebook + instagram training rows."""

    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, y):
        y = np.asarray(y)
        self.base_ = SoftVote(seed=self.seed).fit(X[BASE_COLS], y)
        self.classes_ = self.base_.classes_
        m = np.isin(y, META)
        Xm, ym = X.loc[m].reset_index(drop=True), np.asarray(y[m], dtype=object)
        self.spec_cols_ = forward(Xm, ym, self.seed)
        self.spec_ = SoftVote(seed=self.seed, class_weight=None).fit(Xm[self.spec_cols_], ym)
        if os.environ.get(SELECT_LOG):
            key = hashlib.sha256(",".join(map(str, sorted(X.index))).encode()).hexdigest()[:16]
            with open(os.environ[SELECT_LOG], "a") as f:
                f.write(json.dumps({"key": key, "seed": self.seed, "cols": self.spec_cols_}) + "\n")
        return self

    def predict(self, X):
        pred = self.base_.predict(X[BASE_COLS])
        m = np.isin(pred, META)
        if m.any():
            pred[m] = self.spec_.predict(X.loc[m, self.spec_cols_])
        return pred


# ---------------------------------------------------------------- arms and runs

def task2_add_up_max(seed):
    return PairSpecialist(base_cols=BASE_COLS, seed=seed, spec_class_weight=None, spec_all_cols=True, pair=META)


def task2_select_specialist(seed):
    return SelectSpecialist(seed=seed)


ARM = {"P": (task2_model, TASK_FEATURES[T2]), "A": (task2_add_up_max, task2_plus_up_max),
       "B": (task2_select_specialist, task2_candidates)}


def run_id(arm, seed):
    hits = sorted(p.name for p in (ROOT / "results").glob(f"*_109_{arm}_s{seed}"))
    return hits[-1] if hits else None


def run(arm, seed):
    f, feats = ARM[arm]
    t0 = datetime.now(timezone.utc)
    res = {T2: evaluate(T2, feats, f, cv_seed=seed)}
    rid = record_run("109", f"{arm}_s{seed}", res, model_factory=f, feature_fn=feats,
                     reference=None if arm == "P" else run_id("P", seed),
                     question=f"Task 2 109 {arm} (decoded first-packet size in the facebook/instagram specialist) on never-used "
                              f"cv_seed {seed}",
                     config={"arm": arm, "cv_seed": seed, "features": feats.__name__}, started=t0)
    print(rid, flush=True)


def _data(feats):
    Xr, y = load_task(T2)
    return feats(Xr), np.asarray(y.values, dtype=object)


def smoke():
    tr, te = next(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEEDS[0])
                  .split(*_data(TASK_FEATURES[T2])))
    X, y = _data(TASK_FEATURES[T2])
    p = np.asarray(task2_model(0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), dtype=object)
    base_meta = np.isin(SoftVote(seed=0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te]), META)
    for arm in ("A", "B"):
        f, feats = ARM[arm]
        Xa, _ = _data(feats)
        m = f(0).fit(Xa.iloc[tr], y[tr])
        q = np.asarray(m.predict(Xa.iloc[te]), dtype=object)
        cols = getattr(m, "spec_cols_", None) or list(Xa.columns)
        print(f"{arm}: {Xa.shape[1]} columns | equals P where the base is not Meta: {bool((q[~base_meta] == p[~base_meta]).all())}"
              f" | base Meta calls: {int(base_meta.sum())} | changed vs P: {int((q != p).sum())} | specialist columns: {cols}")


def analyse():
    f1 = lambda a, s: pd.read_csv(ROOT / "results" / run_id(a, s) / T2 / "folds.csv")  # noqa: E731
    out = {"means": {a: [round(float(f1(a, s).macro_f1.mean()), 4) for s in SEEDS] for a in ARMS}, "vs_P": {}}
    for a in ("A", "B"):
        per, acc, tr, cls = [], Counter(), Counter(), {}
        for s in SEEDS:
            comp = json.loads((ROOT / "results" / run_id(a, s) / "comparison.json").read_text())[T2]
            per.append({"seed": s, "delta": round(comp["delta_mean"], 4), "wins": comp["wins"], "losses": comp["losses"],
                        "ties": comp["ties"], "verdict": comp["verdict"]})
            for c, v in comp["per_class"].items():
                cls.setdefault(c, []).append(v["delta"])
            new = pd.read_csv(ROOT / "results" / run_id(a, s) / T2 / "oof.csv")
            ref = pd.read_csv(ROOT / "results" / run_id("P", s) / T2 / "oof.csv")
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
        out["B_selection"] = {"fits": len(rows), "column_counts": dict(Counter(c for r in rows for c in r["cols"]).most_common(12)),
                              "columns_per_fit": dict(sorted(Counter(len(r["cols"]) for r in rows).items()))}
        print("B selection:", out["B_selection"])
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")


def test_effect():
    from make_submission import load_test
    sub = json.loads((ROOT / "submissions/production-100-cross-task/submission.json").read_text())[T2]
    Xt_raw = load_test(T2)
    ids = list(Xt_raw.flow_id)
    s = np.array([sub[f] for f in ids], dtype=object)
    out = {}
    for a in ARMS:
        f, feats = ARM[a]
        X, y = _data(feats)
        m = f(0).fit(X, y)
        p = np.asarray(m.predict(feats(Xt_raw)), dtype=object)
        out[a] = {"changed_vs_submitted": int((p != s).sum()),
                  "changes": {ids[i]: f"{s[i]} -> {p[i]}" for i in np.flatnonzero(p != s)},
                  "specialist_columns": getattr(m, "spec_cols_", None)}
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
        os.environ[SELECT_LOG] = str(EVIDENCE / "selected_columns.jsonl")  # set before any worker process starts
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
