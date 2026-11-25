---
title: '044: Facebook sub-type classes (Task 1)'
created: 2026-10-08
creator: sidhantbas
description: Does training the frozen Task 1 production model on Facebook sub-type classes (041's traffic types), merged back to facebook at prediction, beat production under rule v2?
experiment:
  id: '044'
  tasks:
  - task1
  lever: imbalance
  status: rejected
  verdict: 'Facebook sub-type classes merged at prediction: -0.0126 (9/23), facebook -0.066'
---
# 044: Facebook sub-type classes (Task 1)

- **Date:** 2026-10-08
- **Question:** Does training the frozen Task 1 production model on Facebook sub-type classes (041's traffic types), merged back to facebook at prediction, beat production under rule v2?
- **Status:** done
- **Script:** `src/exp044_facebook_subtypes.py` (`Subtyped` wraps `models.TASK_MODELS`; production code unchanged)
- **Runs:** `results/20261008T003620Z_044_fb_subtypes` (cv_seed 2026)
- **Reference:** Task 1 champion `20261001T173854Z_034_meta_gate`

## Hypothesis

Facebook is 5 different traffic types (041: TCP keep-alive 3, slow QUIC trickle 3, QUIC burst 2, short QUIC fetch 2, short
TCP 1). One scattered class may be harder for the trees than tight sub-classes (BACKLOG.md Ready #1).
046 ranks errors involving facebook or instagram as the largest Task 1 target.

## Setup

Settings fixed before running:

- Training facebook flows are relabelled `facebook:<type>` by 041's rule (transport, duration, bytes_up, bytes_down; same
  thresholds). Training rows only; prediction needs no type.
- Every SoftVote inside `task1_meta_gate` (both whole-run experts and the opening expert) trains on sub-type labels;
  `predict_proba` sums the sub-types back into facebook, so every production rule sees 6 classes. The Meta gate (meta/rest)
  is unaffected. Checked on a full fit: all three experts carry the 5 sub-classes, the gate does not.
- Each sub-class gets facebook's "balanced" weight on the original labels, so facebook's total weight is unchanged.
- CV 5×10, cv_seed 2026, features `task1_with_prefix_features`.

## Results

| Run | Macro F1 | facebook | google | instagram | mozilla | x | youtube |
|---|---|---|---|---|---|---|---|
| production (034) | 0.8277 | 0.674 | 0.888 | 0.741 | 0.919 | 0.936 | 0.808 |
| 044 sub-types | 0.8151 | 0.609 | 0.886 | 0.735 | 0.921 | 0.936 | 0.804 |

**WORSE**: Δ −0.0126 (paired std 0.0432), wins 9, losses 23, ties 18.

| Class | Δ F1 | Wins | Losses |
|---|---|---|---|
| facebook | −0.066 | 4 | 13 |
| google | −0.002 | 5 | 9 |
| instagram | −0.006 | 5 | 11 |
| mozilla | +0.002 | 3 | 2 |
| x | −0.001 | 3 | 7 |
| youtube | −0.004 | 4 | 7 |

Flows (majority vote): fixed 2 (flow_000866 youtube, flow_001145 facebook), broken 2 (flow_001324 facebook → x,
flow_001331 facebook → instagram). More facebook → instagram (22 → 30), google → facebook (10 → 13), facebook → x (6 → 9).

## Caveats

- One seed only; a WORSE result is not confirmed on other seeds (rule v2 confirms passes only).
- A training fold holds about 9 facebook flows, so each sub-class has 0–3 rows. LightGBM's `min_child_samples=5` and the
  forests' purity splits cannot learn classes that small; splitting facebook spreads its little evidence thinner.

## Decision

Rejected. Facebook loses 0.066 and more facebook flows go to instagram: with 9 training flows per fold, one facebook class
pools evidence better than five tiny ones.

## Next

- 045 (synthetic Facebook flows) attacks the same shortage from the other side, by adding points instead of splitting them.
- The same argument makes BACKLOG Ready #5 (google/youtube sub-types) less promising, though those classes are large enough
  for sub-classes of useful size.
