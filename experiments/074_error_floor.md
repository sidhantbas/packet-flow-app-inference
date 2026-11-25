---
title: "074: How many production errors are on flows whose nearest training flow is another app (measurement only)"
created: 2026-10-09
creator: sidhantbas
description: Every production cross-validation error in both tasks classified by the label of its nearest training-fold flow, giving an upper bound on what better modelling of the released features could recover.
source:
  - 068_problem4_facebook_google.md
  - 069_google_youtube_measurement.md
  - 072_instagram_youtube_measurement.md
  - 073_google_mozilla_measurement.md
experiment:
  id: '074'
  tasks:
  - task1
  - task2
  lever: diagnostic
  status: measured
  verdict: 65% (Task 1) and 81% (Task 2) of errors are on flows whose nearest training flow belongs to another app; modelling ceiling about +1.8 / +1.6 CV points
---

# 074: The error floor of the production models (measurement only)

- **Date:** 2026-10-09 · **Status:** done · **Data:** production out-of-fold predictions (Task 1
  `20261001T173854Z_034_meta_gate`, Task 2 `20260930T173836Z_014_fi_same_nocw`; cv_seed 2026, 10 repeats); training labels only.
- **Method:** for every held-out prediction, the nearest flow **in that fold's training rows** (16 gate-2 columns
  `capture_checks.PROX_COLS`, log1p, standardised; folds rebuilt with the same splitter and checked against `oof.csv`).
  Each error is either "has a same-app look-alike" (nearest training flow has the true label) or "look-alike of another
  app". Upper bound: macro F1 if every "same-app look-alike" error were corrected, all else unchanged.

## Results

| | Task 1 | Task 2 |
|---|---:|---:|
| Errors in 10 repeats | 412 | 505 |
| Share on "look-alike of another app" flows | **65%** | **81%** |
| 1-NN accuracy (nearest training label = true label) | 77.8% | 64.5% |
| Macro F1 now / points lost | 0.8323 / 8.39 | 0.7692 / 11.54 |
| Upper bound if all "same-app look-alike" errors were fixed | 0.8683 (**+1.80 points**) | 0.8008 (**+1.58 points**) |
| Points left on "look-alike of another app" flows | 6.59 | 9.96 |

Share of errors on "look-alike of another app" flows, by true class:

| Task | facebook | instagram | google | youtube | mozilla | x |
|---|---:|---:|---:|---:|---:|---:|
| Task 1 | 1.00 (31) | 0.98 (47) | 0.64 (161) | 0.53 (116) | 0.54 (35) | 0.32 (22) |
| Task 2 | 1.00 (64) | 0.83 (47) | 0.72 (148) | 0.80 (137) | 0.79 (78) | 0.94 (31) |

(Numbers in brackets: all errors of that class in 10 repeats.)

## Reading

- Every facebook error and 98% of instagram errors (Task 1) fall on flows whose nearest training flow belongs to another
  app; they cannot be fixed by better use of these features, only by new, matching information (056-063 showed our own
  captures are not that).
- Better modelling of the released features can recover at most about +1.8 Task 1 and +1.6 Task 2 points in CV, and only
  if every recoverable error were fixed without breaking others; the ten model changes of 060-071 (each within ±0.007 macro
  F1, about ±0.35 points) are consistent with that ceiling.
- What remains recoverable sits mostly in google and youtube (Task 1: 58 and 54 errors with a same-app look-alike).

## Decision

No model change. The numbers go into the technical report as the error anatomy of the final models.
