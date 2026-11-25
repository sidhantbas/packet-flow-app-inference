---
title: '008: Engineered feature families, one at a time'
created: 2026-09-30
creator: sidhantbas
description: 'Does any of the five ratio families (TODO #1–#5) improve either task over its champion?'
experiment:
  id: 008
  tasks:
  - task1
  - task2
  lever: features
  status: rejected
  verdict: 'Five ratio families: no effect on Task 1; Task 2 -0.05 to -0.06 for relative timing, rates and burst density'
---
# 008: Engineered feature families, one at a time

- **Date:** 2026-09-30
- **Question:** Does any of the five ratio families (TODO #1–#5) improve either task over its champion?
- **Status:** done
- **Script:** `src/exp008_feature_families.py`
- **Runs:** `results/*_008_*` (10)
- **Reference:** task 1 `20260930T161714Z_006_softvote`, task 2 `20260930T170446Z_007_t2_drop_timing5`

## Hypothesis

Trees cannot form ratios of two columns, so ratio features add real information (#1 relative timing,
#2 bytes/s, #3 burst density, #4 downstream share, #5 packet-size CV). Only one zero denominator exists
(one task 2 flow with no downstream bytes); safe division returns 0.

## Results (SoftVote, cv_seed 2026)

| Family | Task 1 Δ (wins) | Task 2 Δ (wins) |
|---|---|---|
| reltiming | +0.004 (26) | **−0.049 (11), WORSE** |
| rates | +0.003 (25) | **−0.060 (6), WORSE** |
| burst | −0.007 (25) | **−0.058 (4), WORSE** |
| direction | −0.001 (20) | +0.001 (7) |
| sizecv | −0.006 (24) | +0.001 (14) |

No family passes, so no confirmation run was needed.

## Caveats

On task 2 the timing-based families re-add timing information in ratio form; each costs ~0.05, the same size
as the 007 gain. This is a second, independent confirmation that prefix-5 timing hurts.

## Decision

Reject all five. Champions unchanged.

## Next

Model-side tests (009) and permutation importance (010).
