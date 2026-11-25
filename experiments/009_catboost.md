---
title: '009: CatBoost (TODO #9, #10)'
created: 2026-09-30
creator: sidhantbas
description: Does CatBoost, alone or as a 4th SoftVote member, beat the champions?
experiment:
  id: 009
  tasks:
  - task1
  - task2
  lever: model
  status: inconclusive
  verdict: 'CatBoost alone, categorical, or as a 4th member: inconclusive; unweighted CatBoost best on Task 2 (+0.015, 27/50), a lead that class weights may hurt Task 2'
---
# 009: CatBoost (TODO #9, #10)

- **Date:** 2026-09-30
- **Question:** Does CatBoost, alone or as a 4th SoftVote member, beat the champions?
- **Status:** done
- **Script:** `src/exp009_catboost.py` (CatBoost 1.2.10, same as Charles; added to `requirements.txt`)
- **Runs:** `results/*_009_*` (4)
- **Reference:** champions (task 2 without timing)

## Results (vs champion, cv_seed 2026)

| Variant | Task 1 | Δ (wins) | Task 2 | Δ (wins) |
|---|---|---|---|---|
| cb (balanced weights) | 0.766 | −0.004 (23) | 0.729 | −0.007 (11) |
| cb_plain (no weights, like Charles) | 0.765 | −0.006 (26) | **0.752** | **+0.015 (27)** |
| cb_cat (`transport` categorical, #10) | 0.769 | −0.001 (26) | 0.729 | −0.007 (10) |
| softvote4 (+ CatBoost) | 0.770 | −0.001 (24) | 0.736 | −0.000 (6) |

All inconclusive. Native categorical handling changes nothing (two transport values).

## Caveats

CatBoost fits take ~35 s per run on this Mac (vs ~4 s for SoftVote).

## Decision

Reject all. Lead: on task 2 the unweighted CatBoost is the best single variant (+0.015, 27/50), and every
balanced variant is slightly worse, so **class weighting may hurt task 2**. Test SoftVote without
`class_weight="balanced"` next.
