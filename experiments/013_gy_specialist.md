---
title: '013: Google-vs-YouTube specialist'
created: 2026-09-30
creator: sidhantbas
description: Does a second-stage model trained only on google + youtube improve either task?
experiment:
  id: '013'
  tasks:
  - task1
  - task2
  lever: hierarchy
  status: rejected
  verdict: 'Google-vs-youtube specialist: |delta| <= 0.005; the 6-class model already separates the pair about as well as a dedicated one (AUC 0.89 / 0.92)'
---
# 013: Google-vs-YouTube specialist

- **Date:** 2026-09-30
- **Question:** Does a second-stage model trained only on google + youtube improve either task?
- **Status:** done
- **Script:** `src/exp013_gy_specialist.py` (`PairSpecialist`)
- **Runs:** `results/*_013_*` (3)
- **Reference:** champions

## Hypothesis

Google/youtube is the largest share of task 2 errors on unseen vectors (011). A pair-only model could focus on
the features that separate the two, including ratio features that did not help the 6-class model (008).

## Setup

The champion SoftVote predicts; flows it calls google or youtube are re-decided by a SoftVote trained only on
the google + youtube flows of the training fold (131 google, 55 youtube in train+validation).
Variants: specialist on the champion columns; plus ratio families (task 1: reltiming, rates, direction,
sizecv; task 2: direction, sizecv); plus ratio families without class weights.

## Results (vs champion, cv_seed 2026)

| Variant | Task 1 Δ (wins) | Task 2 Δ (wins) |
|---|---|---|
| spec_same | −0.004 (10) | −0.000 (10) |
| spec_extra | −0.003 (15) | +0.000 (12) |
| spec_extra_nocw | −0.005 (17) | −0.001 (11) |

All inconclusive, essentially zero.

## Why: the pair is hard with these features

A standalone google-vs-youtube SoftVote (5-fold × 3 repeats, google + youtube flows only):

| Task | Columns | AUC | Balanced accuracy |
|---|---|---|---|
| task 1 | champion | 0.894 | 0.815 |
| task 1 | + ratio families | 0.902 | 0.820 |
| task 2 | champion | 0.915 | 0.860 |
| task 2 | + ratio families | 0.917 | 0.860 |

The 6-class model already separates the pair about as well as a dedicated model does, so neither other classes
nor missing ratios are the bottleneck. Both apps talk to Google infrastructure over the same transports, so their
flow statistics overlap. Some flows may be genuinely ambiguous: a YouTube app loads Google services, and the
Google app plays video.

## Decision

Reject. Champions unchanged.

## Next

- Stop spending effort on google/youtube features; look for gains elsewhere (Facebook/Instagram, mozilla/x).
- The pair's limit (~0.82–0.86 balanced accuracy in CV) caps google and youtube F1, and therefore macro F1.
