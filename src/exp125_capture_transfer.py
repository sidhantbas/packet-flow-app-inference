"""Experiment 125: does the facebook/instagram contrast learned from our captures transfer to the organisers' flows?
(protocol: experiments/125_capture_transfer_test.md, frozen first)

Command: .venv/bin/python src/exp125_capture_transfer.py   (needs `git fetch upstream`: reads d3189ba)
Six arms ({iPhone, Android} x {ALL, SIZE, RANK}): SoftVote(seed=0) fitted on captured facebook/instagram rows only, scored on the
30 original labelled Meta flows (train + validation, Task 1): AUC, bootstrap interval, permutation p; in-domain reference by
repeated 5-fold x 10 on the 30 flows; model-free direction check per column. Writes experiments/125_evidence/transfer.json.
"""
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import basic_features, load_task
from models import T1_COLS, SoftVote

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = "d3189ba"
BASE = "experiments/charles-003-capture-audit/evidence/20261020-flow-aggregates/observed"
ANDROID = ROOT / "data/captures/clean-v2/sid-android-20261009T152334Z-check-macshare"
OUT = ROOT / "experiments/125_evidence"
META = ["facebook", "instagram"]
TIMING = ["duration", "mean_iat", "std_iat", "min_iat", "max_iat", "burst_count"]
COLS = {"ALL": list(T1_COLS), "SIZE": [c for c in T1_COLS if c not in TIMING], "RANK": list(T1_COLS)}
N_BOOT = N_PERM = 2000


def show(name):
    out = subprocess.run(["git", "show", f"{UPSTREAM}:{BASE}/{name}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return pd.read_csv(io.StringIO(out))


def iphone():
    T, L = show("candidate_task1_features.csv"), show("candidate_labels.csv")
    assert (T.flow_id == L.flow_id).all()
    m = L.app.isin(META).values
    return basic_features(T[m])[list(T1_COLS)].reset_index(drop=True), L.app.values[m]


def android():
    X, y = [], []
    for d in sorted(p for p in ANDROID.iterdir() if p.is_dir()):
        T, L = pd.read_csv(d / "task1_features.csv"), pd.read_csv(d / "labels.csv")
        assert (T.flow_id == L.flow_id).all()
        m = (L.keep.astype(str).str.lower() == "true").values & L.app.isin(META).values
        X.append(basic_features(T[m])[list(T1_COLS)]), y.append(L.app.values[m])
    return pd.concat(X, ignore_index=True), np.concatenate(y)


def originals():
    X, y = load_task("task1_static")
    m = y.isin(META).values
    return basic_features(X[m])[list(T1_COLS)].reset_index(drop=True), y.values[m]


def prepare(X, arm):
    X = X[COLS[arm]].astype(float)
    return X.rank(pct=True) if arm == "RANK" else X


def auc_stats(y, p):
    t = (y == "facebook").astype(int)
    auc = roc_auc_score(t, p)
    rng = np.random.default_rng(0)
    boot = []
    while len(boot) < N_BOOT:
        i = rng.integers(0, len(t), len(t))
        if 0 < t[i].sum() < len(i):
            boot.append(roc_auc_score(t[i], p[i]))
    rng = np.random.default_rng(0)
    perm = np.array([roc_auc_score(rng.permutation(t), p) for _ in range(N_PERM)])
    return {"auc": round(float(auc), 3), "ci95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
            "perm_p": round(float(((perm >= auc).sum() + 1) / (N_PERM + 1)), 4)}


def in_domain(Xo, yo, arm):
    X = prepare(Xo, arm).values
    t = (yo == "facebook").astype(int)
    aucs = []
    for k, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=2026).split(X, t)):
        m = SoftVote(seed=k).fit(X[tr], yo[tr])
        p = m.predict_proba(X[te])[:, list(m.classes_).index("facebook")]
        if 0 < t[te].sum() < len(te):
            aucs.append(roc_auc_score(t[te], p))
    return round(float(np.mean(aucs)), 3)


def direction(Xa, ya, Xb, yb):
    s = lambda X, y, c: np.sign(np.median(X.loc[y == "facebook", c]) - np.median(X.loc[y == "instagram", c]))
    per = {c: {"original": int(s(Xa, ya, c)), "captured": int(s(Xb, yb, c))} for c in T1_COLS}
    agree = sum(1 for v in per.values() if v["original"] == v["captured"] and v["original"] != 0)
    return {"agree": agree, "of": len(T1_COLS), "per_column": per}


def main():
    Xo, yo = originals()
    domains = {"iPhone": iphone(), "Android": android()}
    res = {"originals": {a: int((yo == a).sum()) for a in META},
           "domains": {d: {a: int((y == a).sum()) for a in META} for d, (_, y) in domains.items()},
           "arms": {}, "in_domain_reference": {}, "direction": {}}
    for arm in COLS:
        res["in_domain_reference"][arm] = in_domain(Xo, yo, arm)
    for d, (Xc, yc) in domains.items():
        res["direction"][d] = direction(Xo, yo, Xc, yc)
        for arm in COLS:
            m = SoftVote(seed=0).fit(prepare(Xc, arm).values, yc)
            p = m.predict_proba(prepare(Xo, arm).values)[:, list(m.classes_).index("facebook")]
            r = auc_stats(yo, p)
            r["transfers"] = bool(r["auc"] >= 0.65 and r["perm_p"] < 0.05 / 6)
            res["arms"][f"{d} / {arm}"] = r
            print(f"{d:8s} {arm:5s} AUC {r['auc']:.3f} CI {r['ci95']} p {r['perm_p']:.4f} transfers {r['transfers']} "
                  f"(in-domain {res['in_domain_reference'][arm]})")
        print(f"{d}: direction agrees on {res['direction'][d]['agree']} of 17 columns")
    OUT.mkdir(exist_ok=True)
    (OUT / "transfer.json").write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
