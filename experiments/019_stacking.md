---
title: '019: Stacking'
created: 2026-09-30
creator: sidhantbas
description: Does a learned combination (logistic regression on inner-CV probabilities) beat plain averaging?
experiment:
  id: 019
  tasks:
  - task1
  - task2
  lever: model
  status: rejected
  verdict: 'Stacking with a learned logistic combiner: facebook -0.17 to -0.24 (inner folds hold about 5 facebook flows)'
---
# 019: Stacking

- **Date:** 2026-09-30
- **Question:** Does a learned combination (logistic regression on inner-CV probabilities) beat plain averaging?
- **Status:** done
- **Script:** `src/exp019_stacking.py` (sklearn `StackingClassifier`, inner 5-fold on the training fold only)
- **Runs:** `results/*_019_*` (2)
- **Reference:** champions (task 2 keeps the fb/ig specialist on top)

## Results (cv_seed 2026)

| Variant | Task 1 Δ (W/L/T) | Task 1 facebook | Task 2 Δ (W/L/T) |
|---|---|---|---|
| stack3 (rf, et, lgbm) | −0.027 (13/36/1), WORSE | −0.173 | −0.007 (8/24/18), WORSE |
| stack5 (+ logreg, knn) | −0.044 (14/36/0), WORSE | −0.242 | −0.005 (12/22/16) |

## Interpretation

The meta-model learns its weights from inner folds holding about 5 Facebook flows, so it learns to ignore
Facebook. The same small-data problem made the tuned per-class multipliers hurt in 004. With this little data,
fixed equal averaging is safer than any learned combination.

## Decision

Reject. Do not revisit learned combiners unless the data grows.
