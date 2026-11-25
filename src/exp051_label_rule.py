"""Experiment 051: which labelling rule did the organisers use? Where do facebook flows sit in capture time? (measurement only)

Command: .venv/bin/python src/exp051_label_rule.py
Hypotheses (from the 046-049 discussion, 2026-10-08):
  A/B  label = app in use (session) or socket owner: each app's flows sit in that app's own time blocks.
  C    label = destination service: "service" labels (facebook, maybe google) sit inside OTHER apps' blocks
       (facebook inside instagram blocks), app labels sit in their own.
Data: the 330 labelled flows of Task 1 (labels + start_rel only). start_rel is used to understand the labels, never as a
model input (039). Test flows (unlabelled, 20% of the capture) are left out, so blocks have small gaps.
Method, fixed before running:
  context of a flow = labels of the OTHER labelled flows starting within +-W s (W = 60; sensitivity 30 and 120);
  block app = the most common context label (ties: "mixed"; no neighbours: "isolated").
  Per class: share of its flows in its own block, and in each other app's block. Baseline: 1,000 shuffles of the labels over
  the same start times (keeps class sizes and timing); p = share of shuffles with own-block share <= observed (low tail).
Decision rule, fixed before running (W = 60):
  C supported if facebook's own-block share is at or below its shuffle median AND instagram is facebook's most common
  block AND facebook's instagram-block share beats the shuffles (p < 0.05, high tail), while instagram, youtube, mozilla and
  x each sit in their own blocks more than in shuffles (p < 0.05, high tail).
  A/B supported if facebook's own-block share is >= 0.5.
  Otherwise: unclear.
"""
from collections import Counter

import numpy as np
import pandas as pd

from cv import load_task

APPS = ["facebook", "google", "instagram", "mozilla", "x", "youtube"]
N_SHUFFLE, SEED = 1000, 2026
Xr, y = load_task("task1_static")
T = Xr.start_rel.values.astype(float)
Y = np.asarray(y, dtype=object)
order = np.argsort(T, kind="stable")
print(f"start_rel range {T.min():.1f}-{T.max():.1f} (units as released); {len(T)} labelled flows")


def blocks(labels, w):
    out = []
    for i in range(len(T)):
        m = (np.abs(T - T[i]) <= w)
        m[i] = False
        c = Counter(labels[m])
        if not c:
            out.append("isolated")
            continue
        top = c.most_common()
        out.append("mixed" if len(top) > 1 and top[0][1] == top[1][1] else top[0][0])
    return np.array(out, dtype=object)


def table(labels, b):
    return {a: {k: np.mean(b[labels == a] == k) for k in APPS + ["mixed", "isolated"]} for a in APPS}


def run(w, verbose=True):
    b = blocks(Y, w)
    obs = table(Y, b)
    rng = np.random.default_rng(SEED)
    sh_own = {a: [] for a in APPS}
    sh_fb_ig = []
    for _ in range(N_SHUFFLE):
        L = rng.permutation(Y)
        tb = table(L, blocks(L, w))
        for a in APPS:
            sh_own[a].append(tb[a][a])
        sh_fb_ig.append(tb["facebook"]["instagram"])
    res = {}
    if verbose:
        print(f"\n## Window +-{w} s: share of each class's flows by the block it sits in\n")
        print("| Class | n | " + " | ".join(f"in {k} block" for k in APPS) + " | mixed | isolated | own: shuffled median | p low | p high |")
        print("|---|---|" + "---|" * (len(APPS) + 5))
    for a in APPS:
        s = np.array(sh_own[a])
        p_low, p_high = np.mean(s <= obs[a][a]), np.mean(s >= obs[a][a])
        res[a] = (obs[a][a], np.median(s), p_low, p_high)
        if verbose:
            cells = " | ".join((f"**{obs[a][k]:.2f}**" if k == a else f"{obs[a][k]:.2f}") for k in APPS)
            print(f"| {a} | {(Y == a).sum()} | {cells} | {obs[a]['mixed']:.2f} | {obs[a]['isolated']:.2f} | "
                  f"{np.median(s):.2f} | {p_low:.3f} | {p_high:.3f} |")
    fi = obs["facebook"]["instagram"]
    p_fi = np.mean(np.array(sh_fb_ig) >= fi)
    if verbose:
        print(f"\nfacebook inside instagram blocks: {fi:.2f} (shuffled median {np.median(sh_fb_ig):.2f}, p high {p_fi:.3f})")
    return obs, res, p_fi, b


obs, res, p_fi, b60 = run(60)
fb_blocks = {k: v for k, v in obs["facebook"].items() if v > 0}
own, med = res["facebook"][0], res["facebook"][1]
top_block = max((k for k in APPS if k != "facebook"), key=lambda k: obs["facebook"][k])
apps_own = all(res[a][3] < 0.05 for a in ("instagram", "youtube", "mozilla", "x"))
if own >= 0.5:
    verdict = "A/B supported (facebook sits in its own blocks)"
elif own <= med and top_block == "instagram" and p_fi < 0.05 and apps_own:
    verdict = "C supported (facebook sits inside instagram blocks; app classes sit in their own)"
else:
    verdict = "unclear"
print(f"\nVerdict (W = 60, rule fixed before running): {verdict}")
print(f"  facebook own-block {own:.2f} vs shuffled median {med:.2f}; most common other block {top_block}; "
      f"instagram-block p {p_fi:.3f}; app classes own-block p high: "
      + ", ".join(f"{a} {res[a][3]:.3f}" for a in ("instagram", "youtube", "mozilla", "x")))

print("\n## Each facebook flow: context within +-60 s (labelled flows only)\n")
print("| flow_id | start_rel | block | context labels (count) | nearest labelled flow |\n|---|---|---|---|---|")
for i in order:
    if Y[i] != "facebook":
        continue
    m = np.abs(T - T[i]) <= 60
    m[i] = False
    ctx = Counter(Y[m])
    d = np.abs(T - T[i]); d[i] = np.inf
    j = int(np.argmin(d))
    print(f"| {Xr.flow_id[i]} | {T[i]:.1f} | {b60[i]} | {dict(ctx.most_common())} | {Y[j]} ({d[j]:.1f} s away) |")

print("\n## Sensitivity: own-block share (shuffled median) by window\n")
print("| Class | +-30 s | +-60 s | +-120 s |\n|---|---|---|---|")
sens = {w: run(w, verbose=False)[1] for w in (30, 120)}
sens[60] = res
for a in APPS:
    print(f"| {a} | " + " | ".join(f"{sens[w][a][0]:.2f} ({sens[w][a][1]:.2f})" for w in (30, 60, 120)) + " |")

# ---------------------------------------------------------------- post hoc (designed after seeing the result above)
# The block test is dominated by google (dense everywhere), so small classes can never "own" a block. Post hoc question:
# which classes START TOGETHER more often than chance? Same-moment starts suggest one trigger opening several connections.
# For each ordered pair (a, b): share of a's flows with at least one b flow starting within +-w s (excluding itself),
# vs 1,000 label shuffles over the same start times; enrichment = observed / shuffled mean; p = share of shuffles >= observed.
print("\n## Post hoc: which classes start together? (share of row-class flows with a column-class flow within +-w s)\n")
for w in (2, 10):
    def co(labels):
        m = {}
        for a in APPS:
            ia = np.flatnonzero(labels == a)
            for bb in APPS:
                ib = np.flatnonzero(labels == bb)
                hit = [np.any((np.abs(T[ib] - T[i]) <= w) & (ib != i)) for i in ia]
                m[a, bb] = np.mean(hit)
        return m
    ob = co(Y)
    rng = np.random.default_rng(SEED)
    sh = [co(rng.permutation(Y)) for _ in range(N_SHUFFLE)]
    print(f"### Within +-{w} s: observed share (enrichment x, p)\n")
    print("| Row class | " + " | ".join(APPS) + " |\n|---|" + "---|" * len(APPS))
    for a in APPS:
        cells = []
        for bb in APPS:
            s = np.array([d[a, bb] for d in sh])
            e = ob[a, bb] / s.mean() if s.mean() > 0 else float("nan")
            p = np.mean(s >= ob[a, bb])
            mark = "**" if p < 0.05 and e > 1 else ""
            cells.append(f"{mark}{ob[a, bb]:.2f} ({e:.1f}x, {p:.3f}){mark}")
        print(f"| {a} | " + " | ".join(cells) + " |")
    print()
