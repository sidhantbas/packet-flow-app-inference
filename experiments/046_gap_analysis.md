---
title: '046: Where is the gap to the leader? (measurement only)'
created: 2026-10-08
creator: sidhantbas
description: Which task, class and confusion pair hold the 8.6 points between our 84.62 and the leader's 93.19, and is any single fix enough?
experiment:
  id: '046'
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 'Gap to the leader (84.62 vs 93.19): 89% in Task 1; errors involving facebook or instagram are the largest target; no single fix closes it'
---
# 046: Where is the gap to the leader? (measurement only)

- **Date:** 2026-10-08
- **Question:** Which task, class and confusion pair hold the 8.6 points between our 84.62 and the leader's 93.19, and is any single fix enough?
- **Status:** done
- **Script:** `src/exp046_gap_analysis.py` (about 50 s; output not stored as a run, no model is trained)
- **Runs:** none new; reads the held-out predictions of the champions
- **Reference:** production champions `20261001T173854Z_034_meta_gate` (Task 1), `20260930T173836Z_014_fi_same_nocw` (Task 2)

## Hypothesis

Mission waypoint 1: before building anything (captures, new Task 2 ideas), find where the points are. Inputs are only the
champions' 50-fold held-out predictions and the public leaderboard numbers in AGENTS.md; no test labels, no metadata.json counts.

## Setup

1. Leaderboard gap per task, and the Task 1 score needed to pass 93.19 at each Task 2 level.
2. CV points lost per class: $\frac{50}{6}\,(1 - F1_c)$, pooled over the 10 repeats.
3. Pair oracles: macro F1 if every confusion inside one pair were corrected.
4. 20,000 test-sized samples (040's method: 81 flows, class mix from labelled proportions, google 32 / x 18 / youtube 13 /
   mozilla 10 / instagram 5 / facebook 3; the same flows and the same repeat for both tasks): P(total > 93.19) as is and under
   each oracle.

## Results

**1. Leaderboard gap.** 89% of it is Task 1.

| Task | Ours | Leader | Gap (points) |
|---|---|---|---|
| Task 1 | 0.787 | 0.94 | +7.65 |
| Task 2 | 0.905 | 0.92 | +0.75 |
| Total | 84.62 | 93.19 | +8.57 |

| Task 2 holds at | Task 1 needed |
|---|---|
| 0.905 (our test score) | 0.959 |
| 0.92 | 0.944 |
| 0.95 | 0.914 |
| 1.00 | 0.864 |

At 0.905 on Task 2, Task 1 needs about 0.96 on 81 flows: our test accuracy 0.852 means about 12 errors, and 0.96 allows about
3 with every facebook flow right.

**2. CV points lost per class** (pooled; Task 1 0.832, Task 2 0.769):

| Class | Task 1 F1 | Points lost | Task 2 F1 | Points lost |
|---|---|---|---|---|
| facebook | 0.693 | 2.56 | 0.469 | 4.42 |
| instagram | 0.745 | 2.13 | 0.731 | 2.24 |
| youtube | 0.809 | 1.59 | 0.775 | 1.88 |
| google | 0.889 | 0.93 | 0.888 | 0.94 |
| mozilla | 0.919 | 0.67 | 0.849 | 1.26 |
| x | 0.936 | 0.53 | 0.904 | 0.80 |
| **total** | | **8.41** | | **11.53** |

**3. Pair oracles** (points gained per task if one pair's confusions were all corrected; top 6):

| Pair | T1 errors | T1 +points | T2 errors | T2 +points |
|---|---|---|---|---|
| facebook/instagram | 48 | +2.79 | 77 | +5.00 |
| google/youtube | 161 | +1.77 | 189 | +2.09 |
| instagram/youtube | 26 | +0.78 | 23 | +0.69 |
| mozilla/x | 24 | +0.38 | 66 | +1.07 |
| facebook/x | 7 | +0.34 | 17 | +1.01 |
| google/mozilla | 41 | +0.55 | 52 | +0.72 |

**4. Chance of passing 93.19 on test-sized samples:**

| Scenario (both tasks) | T1 median | T2 median | Total median | P(> 93.19) |
|---|---|---|---|---|
| production as is | 0.834 | 0.767 | 80.0 | 0.1% |
| fix facebook/instagram | 0.892 | 0.870 | 88.0 | 4.8% |
| fix google/youtube | 0.870 | 0.809 | 83.8 | 1.5% |
| fix every error involving facebook or instagram | 0.934 | 0.909 | 92.1 | 32.0% |
| fix facebook/instagram + google/youtube | 0.927 | 0.913 | 91.9 | 33.8% |
| fix all Meta errors + google/youtube | 0.969 | 0.951 | 96.0 | 93.8% |

## Caveats

- Section 4 is pessimistic: held-out models train on 264 flows (the final one on 330), and test flows have more near-twins (036).
  It also assumes 3 test facebook flows.
- Task 2's real test score (0.905) is well above its CV level (0.754–0.769); on the fixed test set, Task 2 is close to the
  leader already, so section 4 understates where we stand on Task 2.
- Oracles are upper bounds: they assume a fix with no side effects. They rank targets; they do not say a fix exists.
- Leaderboard numbers are used only to size the gap, never to choose a model.

## Decision

Measurement only, nothing to adopt. Targets, in order:

1. **Task 1, every error involving facebook or instagram** (not only the facebook/instagram pair: instagram/youtube,
   facebook/x, facebook/google, google/instagram too). Worth about 4.7 CV points; fixing these alone already gives about a one in
   three chance.
2. **Task 1, google/youtube** (161 pooled errors, +1.8). Experiment 013 shows the released features separate this pair about as
   well as a dedicated model can, so only new information (labelled captures) can move it.
3. **Task 2** is a low priority: the test gap is 0.75 points, captures are not allowed there, and the model is near what its
   features allow (004 ceiling; 012–017).

No single fix passes 93.19. A real chance needs Task 1 near-perfect on Meta **and** much better on google/youtube. Experiments
013 and 021–043 suggest the released features are exhausted for both, so the remaining lever is waypoint 2: own Task 1 captures,
aimed at the confused types.

## Next

- Capture plan (waypoint 2): weight sessions toward the 7 Facebook/Instagram traffic types from 041 (keep-alive, short TCP,
  short QUIC fetch, QUIC burst, slow trickle; Instagram media download and upload) and toward google/youtube flows of the shapes
  that are confused (031: most errors sit next to a labelled flow of the predicted app; 004: UDP openings of about 2.7 kB shared
  by youtube and google).
- Skip waypoint 4 (Task 2 idea) unless captures stall: the gap analysis shows little room there.
