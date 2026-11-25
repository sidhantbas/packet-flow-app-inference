---
title: '012: Class weighting in SoftVote'
created: 2026-09-30
creator: sidhantbas
description: Does SoftVote do better without balanced class weights (lead from 009), or with a middle setting?
experiment:
  id: '012'
  tasks:
  - task1
  - task2
  lever: imbalance
  status: measured
  verdict: 'No class weights: Task 1 -0.014 (facebook -0.090) so balanced weights stay; Task 2 +0.012 (24/5/21, instagram +0.075), the lead for 014'
---
# 012: Class weighting in SoftVote

- **Date:** 2026-09-30
- **Question:** Does SoftVote do better without balanced class weights (lead from 009), or with a middle setting?
- **Status:** done
- **Script:** `src/exp012_class_weights.py`
- **Runs:** `results/*_012_*` (3)
- **Reference:** champions (task 1 `006_softvote`, task 2 `007_t2_drop_timing5`)

## Setup

`models.SoftVote` now takes `class_weight` ("balanced" = default, None, or "sqrt" = square root of the balanced
weights) and passes it to RF, ExtraTrees and LightGBM. The default reproduces both champions on all 50 folds
(`012_check_balanced`, flagged `identical`), so the refactor changed nothing.

## Results (vs champion, cv_seed 2026)

| Variant | Task 1 | Δ (W/L/T) | Task 2 | Δ (W/L/T) |
|---|---|---|---|---|
| none | 0.757 | −0.014 (21/23/6) | 0.748 | +0.012 (**24/5/21**) |
| sqrt | 0.769 | −0.001 (19/…) | 0.733 | −0.003 (7/…) |

Per class, no weights:
- Task 1: facebook −0.090. Balanced weights are what keep Facebook alive on task 1.
- Task 2: **instagram +0.075 (19 wins, 0 losses)**, all other classes within ±0.005.

## Caveats

On task 2, no weights wins 24 folds, loses 5, and ties 21. The 35-win rule counts ties as non-wins, so this
is **inconclusive**. We do not change the rule after seeing the result. Mechanism: 13 Instagram and 2 Facebook
flows share one exact task 2 pattern (CLAUDE.md), and balanced weights push that pattern toward Facebook.
Removing the weights gives it back to Instagram.

## Decision

Nothing adopted; champions unchanged. Task 1 must keep balanced weights (Facebook).

## Next

- Record the task 2 Instagram effect as a lead for a Facebook/Instagram-specific fix. It should not become a global weight change.
- Next TODO item: google-vs-youtube specialist (the largest share of task 2 errors, 011).
