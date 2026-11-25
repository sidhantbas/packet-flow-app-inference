---
title: '016: Smoother models for never-seen patterns'
created: 2026-09-30
creator: sidhantbas
description: Do regularised trees, or smooth models (logistic regression, kNN) as extra ensemble members, reduce errors on never-seen feature vectors?
experiment:
  id: '016'
  tasks:
  - task1
  - task2
  lever: model
  status: inconclusive
  verdict: Bigger leaves hurt (memorising exact twins is right; Task 2 -0.02); LR + kNN members +0.006 on Task 2 (near-miss); kNN costs Task 1 facebook -0.075
---
# 016: Smoother models for never-seen patterns

- **Date:** 2026-09-30
- **Question:** Do regularised trees, or smooth models (logistic regression, kNN) as extra ensemble members, reduce errors on never-seen feature vectors?
- **Status:** done
- **Script:** `src/exp016_smooth_models.py` (`models.Blend`, `logreg`, `knn`, `rf_leaf`, `et_leaf`; `MultiSpecialist(base_members=...)`)
- **Runs:** `results/*_016_*` (6)
- **Reference:** champions (task 1 SoftVote; task 2 SoftVote + fb/ig specialist)

## Setup

Only the base model changes. On task 2 the facebook/instagram specialist of the champion stays on top.
Logistic regression (C = 1, balanced) and 7-NN (distance-weighted, no class weights) use log1p + standardised
features. `check` (Blend of rf, et, lgbm) ties both champions on every fold.

## Results (cv_seed 2026)

| Variant | Task 1 Δ (W/L/T) | Task 2 Δ (W/L/T) | Task 2 error: seen / unseen vectors |
|---|---|---|---|
| champion (check) | 0 | 0 | 0.063 / 0.415 |
| leaf2 | −0.001 | −0.021, WORSE | 0.087 / 0.431 |
| leaf3 | −0.003, WORSE | −0.022, WORSE | 0.090 / 0.431 |
| plus_lr | +0.001 | +0.001 | 0.063 / 0.410 |
| plus_knn | −0.007 | −0.000 | 0.062 / 0.408 |
| plus_lr_knn | −0.007 (26/20/4), facebook −0.075 | +0.006 (18/9/23), NEAR-MISS | 0.062 / **0.398** |

## Interpretation

- **Memorisation helps.** Larger leaves raise the error on *seen* vectors (0.063 → 0.087–0.090) and do not
  help unseen ones, costing task 2 ~0.02.
- Smooth members lower the unseen error a little (0.415 → 0.398 with both) without hurting seen vectors, but the
  task 2 gain (+0.006, 18/9 = 67% of non-tied folds) misses rule v2. On task 1, kNN hurts Facebook (−0.075),
  because kNN has no class weights.

## Decision

Nothing adopted. Near misses are not confirmed on other seeds, to avoid picking lucky ones.

## Next

Novelty gating: trees for flows whose exact vector appears in training, smooth members only for new vectors.
It uses the two findings above (memorisation is right for seen vectors; smooth models help a little on unseen
ones), and needs only training data.
