"""Experiment 046: where is the gap to the leader? (measurement only, mission waypoint 1)

Command: .venv/bin/python src/exp046_gap_analysis.py
Inputs: held-out predictions of the two champion runs (Task 1 034, Task 2 014; cv_seed 2026, 10 repeats) and the public
leaderboard numbers recorded in AGENTS.md. No test labels and no metadata.json label counts.
1. Leaderboard gap per task, and the Task 1 score needed for each Task 2 level to pass the leader's 93.19.
2. CV points lost per class: (50 / 6) x (1 - F1_c) per task.
3. Pair oracles: macro F1 if every confusion inside one pair of apps were corrected (pooled 50-fold predictions).
4. 81-flow test-sized samples (040's method; same flows and same repeat for both tasks): P(total > 93.19) for production
   as is and with each pair oracle applied.
"""
from itertools import combinations

import numpy as np
import pandas as pd

from evaluation_metric import macro_f1
from runlog import load_champions, load_oof

N, SEED = 20000, 2026
LEADER = 93.19
OURS = {"task1_static": 0.787, "task2_realtime_prefix5": 0.905}  # second Final Test Phase submission (022 Task 1 model)
TOP = {"task1_static": 0.94, "task2_realtime_prefix5": 0.92}  # HeriTech, rounded on the leaderboard
TASKS = list(OURS)
rng = np.random.default_rng(SEED)
champs = load_champions()


def oof(task):
    o = load_oof(champs[task]["run_id"], task).copy()
    o["repeat"] = o.groupby("flow_id").cumcount()
    return o


def f1_per_class(yt, yp, apps):
    out = {}
    for a in apps:
        tp = sum((t == a) & (p == a) for t, p in zip(yt, yp))
        fp = sum((t != a) & (p == a) for t, p in zip(yt, yp))
        fn = sum((t == a) & (p != a) for t, p in zip(yt, yp))
        out[a] = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return out


def fix_pair(yt, yp, pair):
    """Correct confusions inside one pair, or inside any of several pairs (a list of pairs)."""
    prs = [set(x) for x in (pair if isinstance(pair[0], tuple) else [pair])]
    return [t if any({t, p} <= q for q in prs) else p for t, p in zip(yt, yp)]


O = {t: oof(t) for t in TASKS}
apps = sorted(O[TASKS[0]].y_true.unique())
pairs = list(combinations(apps, 2))

print("## 1. Leaderboard gap (public numbers)\n")
print("| Task | Ours | Leader | Gap (points) |\n|---|---|---|---|")
for t in TASKS:
    print(f"| {t} | {OURS[t]:.3f} | {TOP[t]:.2f} | {50 * (TOP[t] - OURS[t]):+.2f} |")
print(f"| total | {50 * sum(OURS.values()):.2f} | {LEADER} | {LEADER - 50 * sum(OURS.values()):+.2f} |\n")
print("Task 1 needed to pass 93.19, by Task 2 level:\n")
print("| Task 2 | Task 1 needed |\n|---|---|")
for t2 in (0.85, 0.905, 0.92, 0.95, 1.0):
    print(f"| {t2:.3f} | {LEADER / 50 - t2:.3f} |")

print("\n## 2. CV points lost per class (pooled held-out predictions)\n")
print("| Class | " + " | ".join(f"{t} F1 | lost" for t in TASKS) + " |\n|---|" + "---|---|" * len(TASKS))
f1s = {t: f1_per_class(O[t].y_true.tolist(), O[t].y_pred.tolist(), apps) for t in TASKS}
for a in apps:
    print(f"| {a} | " + " | ".join(f"{f1s[t][a]:.3f} | {50 / 6 * (1 - f1s[t][a]):.2f}" for t in TASKS) + " |")
print("| macro | " + " | ".join(f"{np.mean(list(f1s[t].values())):.3f} | {50 * (1 - np.mean(list(f1s[t].values()))):.2f}"
                                  for t in TASKS) + " |")

print("\n## 3. Pair oracles: points gained if one pair's confusions were all corrected\n")
print("| Pair | " + " | ".join(f"{t} errors | +points" for t in TASKS) + " |\n|---|" + "---|---|" * len(TASKS))
rows = []
for pr in pairs:
    r = [pr]
    for t in TASKS:
        yt, yp = O[t].y_true.tolist(), O[t].y_pred.tolist()
        n = sum({a, b} == set(pr) for a, b in zip(yt, yp))
        r += [n, 50 * (macro_f1(yt, fix_pair(yt, yp, pr)) - macro_f1(yt, yp))]
    rows.append(r)
for r in sorted(rows, key=lambda r: -(r[2] + r[4])):
    if r[1] + r[3]:
        print(f"| {r[0][0]}/{r[0][1]} | {r[1]} | {r[2]:+.2f} | {r[3]} | {r[4]:+.2f} |")

print("\n## 4. 81-flow samples: chance of passing 93.19\n")
truth = O[TASKS[0]].groupby("flow_id").y_true.first()
pred = {t: O[t].pivot(index="flow_id", columns="repeat", values="y_pred") for t in TASKS}
counts = truth.value_counts()
raw = counts / counts.sum() * 81
m = np.floor(raw).astype(int)
for a in (raw - m).sort_values(ascending=False).index[: 81 - m.sum()]:
    m[a] += 1
samples = []
for _ in range(N):
    flows = np.concatenate([rng.choice(truth.index[truth == a], size=n, replace=False) for a, n in m.items()])
    reps = rng.integers(10, size=len(flows))
    samples.append((truth[flows].tolist(), {t: [pred[t].at[f, r] for f, r in zip(flows, reps)] for t in TASKS}))

meta = [pr for pr in pairs if {"facebook", "instagram"} & set(pr)]
scen = {"production as is": None, **{f"fix {a}/{b}": (a, b) for a, b in pairs},
        "fix facebook/instagram + google/youtube": [("facebook", "instagram"), ("google", "youtube")],
        "fix every error involving facebook or instagram": meta,
        "fix all Meta errors + google/youtube": meta + [("google", "youtube")]}
res = []
for name, pr in scen.items():
    tot, s1, s2 = [], [], []
    for yt, yp in samples:
        a = macro_f1(yt, yp[TASKS[0]] if pr is None else fix_pair(yt, yp[TASKS[0]], pr))
        b = macro_f1(yt, yp[TASKS[1]] if pr is None else fix_pair(yt, yp[TASKS[1]], pr))
        s1.append(a); s2.append(b); tot.append(50 * (a + b))
    tot = np.array(tot)
    res.append((name, np.median(s1), np.median(s2), np.median(tot), (tot > LEADER).mean()))
print("| Scenario (both tasks) | T1 median | T2 median | Total median | P(total > 93.19) |\n|---|---|---|---|---|")
for r in [res[0]] + sorted(res[1:], key=lambda r: -r[4])[:7]:
    print(f"| {r[0]} | {r[1]:.3f} | {r[2]:.3f} | {r[3]:.1f} | {100 * r[4]:.1f}% |")
print(f"\nClass mix: {dict(m)}; {N} samples; seed {SEED}.")
