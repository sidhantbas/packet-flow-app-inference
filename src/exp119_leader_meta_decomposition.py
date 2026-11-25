"""Experiment 119 (measurement only): Meta-specific decomposition of the levers the top leaderboard entries describe
(protocol: experiments/119_leader_meta_decomposition.md). No test labels; test label_counts values never read.

Usage (from the repository root):
  .venv/bin/python src/exp119_leader_meta_decomposition.py
Writes experiments/119_evidence/decomposition.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from cv import CV_SEED, TASK_FEATURES, load_task
from models import SoftVote

ROOT = Path(__file__).resolve().parent.parent
TASKS = ("task1_static", "task2_realtime_prefix5")
APPS = np.array(["facebook", "google", "instagram", "mozilla", "x", "youtube"])
FB, IG = 0, 2
SIGMA = 1.0
EVIDENCE = ROOT / "experiments/119_evidence"


def _fold(i, tr, te, X, y):
    m = SoftVote(seed=i).fit(X.iloc[tr], y[tr])
    assert list(m.classes_) == list(APPS)
    return m.predict_proba(X.iloc[te])


def oof_proba(task, y, splits):
    Xr, _ = load_task(task)
    X = TASK_FEATURES[task](Xr).reset_index(drop=True)
    out = Parallel(n_jobs=-1)(delayed(_fold)(i, tr, te, X, y) for i, (tr, te) in enumerate(splits))
    P = np.zeros((10, len(y), len(APPS)))
    for i, ((_, te), p) in enumerate(zip(splits, out)):
        P[i // 5, te] = p
    return P, Xr.start_rel.to_numpy()


def production_labels(task, flow_ids, splits):
    champ = json.loads((ROOT / "results/champions.json").read_text())[task]["run_id"]
    o = pd.read_csv(ROOT / "results" / champ / task / "oof.csv")
    pos = pd.Series(range(len(flow_ids)), index=flow_ids)
    L = np.empty((10, len(flow_ids)), dtype=object)
    for i, (_, te) in enumerate(splits):
        g = o[o.fold == i]
        idx = pos[g.flow_id.values].values
        assert set(idx) == set(te), "production folds differ"
        L[i // 5, idx] = g.y_pred.values
    return L


def counts_oracle(y_te):
    return np.array([(y_te == a).sum() for a in APPS])


def counts_training(y_tr, n):
    share = np.array([(y_tr == a).mean() for a in APPS]) * n
    k = np.floor(share).astype(int)
    k[np.argsort(-(share - k))[: n - k.sum()]] += 1
    return k


def assign(p, k):
    slots = np.repeat(np.arange(len(APPS)), k)
    cost = -np.log(np.clip(p[:, slots], 1e-9, None))
    r, c = linear_sum_assignment(cost)
    out = np.empty(len(p), dtype=object)
    out[r] = APPS[slots[c]]
    return out


def meta_count_fix(prod, p, k_fb):
    out = prod.copy()
    m = np.isin(prod, ["facebook", "instagram"])
    if m.any():
        ratio = p[m, FB] / np.clip(p[m, FB] + p[m, IG], 1e-12, None)
        k = min(int(k_fb), int(m.sum()))
        lab = np.full(int(m.sum()), "instagram", dtype=object)
        lab[np.argsort(-ratio)[:k]] = "facebook"
        out[m] = lab
    return out


def meta_by_proba(prod, p):
    out = prod.copy()
    m = np.isin(prod, ["facebook", "instagram"])
    out[m] = np.where(p[m, FB] >= p[m, IG], "facebook", "instagram")
    return out


def smooth(P_r, t):
    W = np.exp(-((t[:, None] - t[None, :]) ** 2) / (2 * SIGMA ** 2))
    return (W @ P_r) / W.sum(1, keepdims=True)


def score(y, labels, splits):
    macro = [f1_score(y[te], labels[i // 5, te], average="macro") for i, (_, te) in enumerate(splits)]
    cls = {a: float(np.mean([f1_score(y, labels[r], labels=[a], average=None, zero_division=0)[0] for r in range(10)]))
           for a in ("facebook", "instagram")}
    return {"macro": round(float(np.mean(macro)), 4), "facebook_f1": round(cls["facebook"], 3), "instagram_f1": round(cls["instagram"], 3)}


def leaderboard():
    lb = json.loads((ROOT / "submissions/raw/leaderboard-final-test-2026-10-16.json").read_text())["entries"]
    out = {}
    for e in lb[:4] + [x for x in lb if x["team"] == "Telex"]:
        r = {}
        for t in (1, 2):
            err = 81 - round(e[f"Task {t} Accuracy"] * 81)
            lost = 50 * (1 - e[f"Task {t} Macro F1"])
            r[f"task{t}"] = {"errors": int(err), "points_lost": round(lost, 2), "points_per_error": round(lost / err, 2) if err else None}
        out[e["team"]] = r
    notes = []
    for f in sorted((ROOT / "submissions/raw").glob("leaderboard-final-test-2026-10-13*.txt")):
        notes += [l.strip() for l in f.read_text().splitlines() if l.strip().startswith(("method_name", "method_description"))]
    return out, notes


def main():
    _, y_series = load_task(TASKS[0])
    y = np.asarray(y_series.values, dtype=object)
    flow_ids = load_task(TASKS[0])[0].flow_id.values
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=CV_SEED).split(np.zeros(len(y)), y))
    P, T, PROD = {}, {}, {}
    for task in TASKS:
        P[task], T[task] = oof_proba(task, y, splits)
        PROD[task] = production_labels(task, flow_ids, splits)
    res = {}
    for task in TASKS:
        Pk, prod = P[task], PROD[task]
        other = P[TASKS[1] if task == TASKS[0] else TASKS[0]]
        S = np.stack([smooth(Pk[r], T[task]) for r in range(10)])
        J = np.sqrt(Pk * other)
        J = J / J.sum(-1, keepdims=True)
        arms = {k: np.empty((10, len(y)), dtype=object) for k in
                ("A0", "P", "L1", "L1m", "L1b", "L1b-m", "L2", "L3", "L3m", "L1+L3")}
        for i, (tr, te) in enumerate(splits):
            r = i // 5
            k_or, k_tr = counts_oracle(y[te]), counts_training(y[tr], len(te))
            arms["A0"][r, te] = APPS[Pk[r, te].argmax(1)]
            arms["P"][r, te] = prod[r, te]
            arms["L1"][r, te] = assign(Pk[r, te], k_or)
            arms["L1m"][r, te] = meta_count_fix(prod[r, te], Pk[r, te], k_or[FB])
            arms["L1b"][r, te] = assign(Pk[r, te], k_tr)
            arms["L1b-m"][r, te] = meta_count_fix(prod[r, te], Pk[r, te], k_tr[FB])
            arms["L2"][r, te] = APPS[J[r, te].argmax(1)]
            arms["L3"][r, te] = APPS[S[r, te].argmax(1)]
            arms["L3m"][r, te] = meta_by_proba(prod[r, te], S[r, te])
            arms["L1+L3"][r, te] = assign(S[r, te], k_or)
        res[task] = {k: score(y, v, splits) for k, v in arms.items()}
        base = res[task]["P"]
        for k, v in res[task].items():
            v["delta_macro_vs_production"] = round(v["macro"] - base["macro"], 4)
            v["delta_fb_vs_production"] = round(v["facebook_f1"] - base["facebook_f1"], 3)
            v["delta_ig_vs_production"] = round(v["instagram_f1"] - base["instagram_f1"], 3)
        print(f"\n{task}")
        for k, v in res[task].items():
            print(f"  {k:6s} macro {v['macro']:.4f} ({v['delta_macro_vs_production']:+.4f}) | facebook {v['facebook_f1']:.3f} "
                  f"({v['delta_fb_vs_production']:+.3f}) | instagram {v['instagram_f1']:.3f} ({v['delta_ig_vs_production']:+.3f})")
    lb, notes = leaderboard()
    print("\nleaderboard error budget:", json.dumps(lb))
    print("method notes:", notes)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "decomposition.json").write_text(json.dumps({"levers": res, "leaderboard": lb, "method_notes": notes}, indent=2) + "\n")


if __name__ == "__main__":
    main()
