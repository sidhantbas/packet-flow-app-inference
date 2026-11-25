---
title: '045: Formula-respecting synthetic Facebook flows (Task 1)'
created: 2026-10-08
creator: sidhantbas
description: Do synthetic facebook flows, interpolated between same-transport facebook neighbours with the released formulas re-imposed, added to Task 1 training folds only, beat production under rule v2?
experiment:
  id: '045'
  tasks:
  - task1
  lever: imbalance
  status: rejected
  verdict: 'Formula-respecting synthetic facebook flows (SMOTE-style): -0.0108, facebook -0.058 (precision falls, recall unchanged)'
---
# 045: Formula-respecting synthetic Facebook flows (Task 1)

- **Date:** 2026-10-08
- **Question:** Do synthetic facebook flows, interpolated between same-transport facebook neighbours with the released formulas re-imposed, added to Task 1 training folds only, beat production under rule v2?
- **Status:** done
- **Script:** `src/exp045_facebook_smote.py` (`synth_facebook` is a `cv.evaluate` resample hook; production model unchanged)
- **Runs:** `results/20261008T003954Z_045_fb_smote` (cv_seed 2026)
- **Reference:** Task 1 champion `20261001T173854Z_034_meta_gate`

## Hypothesis

Facebook has about 9 training flows per fold. 003's duplicate oversampling did nothing because copies add weight but no new
points; interpolated flows add new points (BACKLOG.md Ready #2). 044 showed that splitting the few flows
hurts, so adding points is the opposite test.

## Setup

Settings fixed before running:

- Per training facebook flow: k = 3 nearest training facebook flows with the same transport (z-scored log1p of the 17 Task 1
  columns, within the fold); 2 synthetic flows each, random neighbour, $\lambda \sim U(0, 1)$, one $\lambda$ per flow.
- Interpolated in log1p space: counts, mean/std sizes per direction, mean/std/min/max IAT, burst_count, for both the full
  flow and the prefix-5 columns.
- Re-imposed (041): integer counts (prefix up + down = 5), bytes = count × mean size, duration = mean_iat × (packets − 1),
  ratios = up / max(down, 1), zero std for ≤ 1 packet, burst_count = 1 iff max_iat < 1.0 s, transport copied.
- Checked on a full-data resample: 11 real → 22 synthetic flows, every formula holds, every prefix has 5 packets.
- Balanced class weights unchanged, so facebook's total weight stays the same; only the number of points grows.

## Results

| Run | Macro F1 | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|---|
| production (034) | 0.8277 | 0.674 | 0.888 | 0.741 | 0.919 | 0.936 | 0.808 |
| 045 synthetic facebook | 0.8169 | 0.617 | 0.885 | 0.738 | 0.921 | 0.931 | 0.810 |

**INCONCLUSIVE** (negative): Δ −0.0108 (paired std 0.0372), wins 17, losses 22, ties 11.

| Class | Δ F1 | Wins | Losses |
|---|---|---|---|
| facebook | −0.058 | 6 | 20 |
| google | −0.003 | 10 | 18 |
| instagram | −0.003 | 11 | 10 |
| mozilla | +0.002 | 7 | 5 |
| x | −0.006 | 5 | 13 |
| youtube | +0.002 | 11 | 6 |

Facebook recall barely moves (facebook → instagram 22 → 21) while false facebook calls jump: google → facebook 10 → 23,
x → facebook 1 → 7, instagram → facebook 26 → 32. Flows: fixed 2 (flow_000240, flow_001145), broken 1 (flow_000535 x → facebook).

## Caveats

- One seed; Δ < 0, so no confirmation runs.
- One setting (k = 3, 2 per flow). Fewer synthetic flows would sit closer to production, but there is no sign of a gain to
  chase: recall did not improve at all.

## Decision

Rejected. The interpolated flows fill the space between dissimilar facebook flows, which is where other apps' flows live
(046 and 031: Task 1 errors sit among other apps' flows). Facebook's region grows into google, x and instagram and its
precision falls, with no gain in recall.

## Next

With 044 and 045 both negative, the Facebook ideas on the released data are used up (W3). The remaining lever is new real
flows: the capture pipeline (mission waypoint 2, W4).
